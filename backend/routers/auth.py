import os
import secrets
from pathlib import Path

import jwt
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Depends, WebSocket
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel


def _load_secret_key() -> str:
    """Resolve the JWT signing key.

    Priority: NETRUNNER_SECRET_KEY env var, else a random key persisted to
    data/.jwt_secret (so tokens survive restarts without a hardcoded secret).
    """
    env = os.environ.get("NETRUNNER_SECRET_KEY")
    if env:
        return env
    key_file = Path("data") / ".jwt_secret"
    key_file.parent.mkdir(parents=True, exist_ok=True)
    if key_file.exists():
        existing = key_file.read_text().strip()
        if existing:
            return existing
    key = secrets.token_urlsafe(48)
    key_file.write_text(key)
    try:
        key_file.chmod(0o600)
    except OSError:
        pass
    return key


SECRET_KEY = _load_secret_key()
ALGORITHM = "HS256"

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

class LoginRequest(BaseModel):
    username: str
    password: str


# --- credentials ---------------------------------------------------------- #
# Users live in the database (see UserModel). Passwords are never stored in
# plaintext: each user has a random salt and a PBKDF2-HMAC-SHA256 hash, verified
# in constant time. Default admin/analyst are seeded on first startup; override
# their initial passwords via NETRUNNER_ADMIN_PASSWORD / NETRUNNER_ANALYST_PASSWORD.
import hashlib
import hmac as _hmac
from datetime import date

from ..core.db import load_users_db, get_user_db, save_user_db, delete_user_db

_PBKDF2_ROUNDS = 200_000
ROLES = ("admin", "analyst")
_DEFAULT_CREDS = {"admin": "admin", "analyst": "analyst"}


def _hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ROUNDS)


def _make_hash(password: str) -> tuple[str, str]:
    """Return (password_hash_hex, salt_hex) for a fresh random salt."""
    salt = secrets.token_bytes(16)
    return _hash_password(password, salt).hex(), salt.hex()


def _verify(user: dict, password: str) -> bool:
    try:
        expected = bytes.fromhex(user["password_hash"])
        salt = bytes.fromhex(user["salt"])
    except (ValueError, KeyError, TypeError):
        return False
    return _hmac.compare_digest(expected, _hash_password(password, salt))


async def seed_default_users():
    """Create default admin/analyst on first run (idempotent)."""
    using_defaults = []
    for username, default in _DEFAULT_CREDS.items():
        if await get_user_db(username):
            continue
        env_pw = os.environ.get(f"NETRUNNER_{username.upper()}_PASSWORD")
        pw = env_pw or default
        if not env_pw:
            using_defaults.append(username)
        h, s = _make_hash(pw)
        await save_user_db({
            "username": username, "password_hash": h, "salt": s,
            "role": "admin" if username == "admin" else "analyst",
            "created": date.today().isoformat(),
        })
    if using_defaults:
        print(
            "WARNING: Netrunner seeded DEFAULT login passwords for "
            f"{using_defaults}. Change them (or set NETRUNNER_<USER>_PASSWORD "
            "before first run) before exposing this service."
        )

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None:
            raise HTTPException(401, "Invalid token")
        return {"username": username, "role": role}
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid token")

def require_admin(user: dict = Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(403, "Insufficient permissions. Admin role required.")
    return user

@router.post("/auth/login")
async def login(req: LoginRequest):
    user = await get_user_db(req.username)
    if not user or not _verify(user, req.password):
        raise HTTPException(401, "Invalid credentials")

    token = create_access_token({"sub": req.username, "role": user["role"]})
    return {"access_token": token, "token_type": "bearer", "role": user["role"], "username": req.username}

@router.get("/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    return user


# --- user management (admin only) ----------------------------------------- #
class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "analyst"

@router.get("/auth/users")
async def list_users(admin: dict = Depends(require_admin)):
    users = await load_users_db()
    # never expose hashes/salts
    return {"users": [{"username": u["username"], "role": u["role"], "created": u.get("created")} for u in users]}

@router.post("/auth/users")
async def create_user(req: CreateUserRequest, admin: dict = Depends(require_admin)):
    username = req.username.strip()
    if not username or not req.password:
        raise HTTPException(400, "Username and password are required")
    if req.role not in ROLES:
        raise HTTPException(400, f"Role must be one of {ROLES}")
    if await get_user_db(username):
        raise HTTPException(409, "User already exists")
    h, s = _make_hash(req.password)
    await save_user_db({
        "username": username, "password_hash": h, "salt": s,
        "role": req.role, "created": date.today().isoformat(),
    })
    return {"status": "ok", "username": username, "role": req.role}

@router.delete("/auth/users/{username}")
async def remove_user(username: str, admin: dict = Depends(require_admin)):
    if username == admin["username"]:
        raise HTTPException(400, "You cannot delete your own account")
    target = await get_user_db(username)
    if not target:
        raise HTTPException(404, "User not found")
    if target["role"] == "admin":
        users = await load_users_db()
        admins = [u for u in users if u["role"] == "admin"]
        if len(admins) <= 1:
            raise HTTPException(400, "Cannot delete the last admin")
    await delete_user_db(username)
    return {"status": "ok"}


async def authenticate_ws(websocket: WebSocket) -> dict | None:
    """Validate a WebSocket connection via a `?token=` query parameter.

    Browsers can't set Authorization headers on WebSocket handshakes, so the
    JWT is passed as a query parameter. Returns the user dict on success.
    On failure it accepts then immediately closes the socket (policy violation)
    and returns None — callers should `return` when they get None.
    """
    token = websocket.query_params.get("token")
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("sub"):
                return {"username": payload.get("sub"), "role": payload.get("role")}
        except jwt.PyJWTError:
            pass
    await websocket.accept()
    await websocket.close(code=4401)  # 4401: unauthorized (app-defined)
    return None
