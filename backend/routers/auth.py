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
# Passwords are never stored in plaintext. Each user's password is hashed with
# PBKDF2-HMAC-SHA256 at startup and verified in constant time. Override the
# defaults via env vars NETRUNNER_ADMIN_PASSWORD / NETRUNNER_ANALYST_PASSWORD.
import hashlib
import hmac as _hmac

_PBKDF2_ROUNDS = 200_000
_DEFAULT_CREDS = {"admin": "admin", "analyst": "analyst"}


def _hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ROUNDS)


class _User:
    def __init__(self, role: str, password: str):
        self.role = role
        self._salt = secrets.token_bytes(16)
        self._hash = _hash_password(password, self._salt)

    def verify(self, password: str) -> bool:
        return _hmac.compare_digest(self._hash, _hash_password(password, self._salt))


def _build_users() -> dict:
    users, using_defaults = {}, []
    for username, default in _DEFAULT_CREDS.items():
        env_pw = os.environ.get(f"NETRUNNER_{username.upper()}_PASSWORD")
        pw = env_pw or default
        if not env_pw:
            using_defaults.append(username)
        role = "admin" if username == "admin" else "analyst"
        users[username] = _User(role, pw)
    if using_defaults:
        print(
            "WARNING: Netrunner is using DEFAULT login passwords for "
            f"{using_defaults}. Set NETRUNNER_<USER>_PASSWORD env vars before "
            "exposing this service."
        )
    return users


USERS = _build_users()

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
    user = USERS.get(req.username)
    if not user or not user.verify(req.password):
        raise HTTPException(401, "Invalid credentials")

    token = create_access_token({"sub": req.username, "role": user.role})
    return {"access_token": token, "token_type": "bearer", "role": user.role, "username": req.username}

@router.get("/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    return user


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
