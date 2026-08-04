import os
import secrets
import time
from pathlib import Path
from collections import defaultdict

import jwt
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Depends, WebSocket, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from ..core.logger import log as logger
from ..core.limiter import limiter


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
# in constant time. Server deployments seed all built-in roles from deployment
# secrets. Student deployments seed only student and reject every privileged
# account or token, including accounts left in a copied database.
import hashlib
import hmac as _hmac
from datetime import date

from ..core.db import load_users_db, get_user_db, save_user_db, delete_user_db

_PBKDF2_ROUNDS = 200_000
ROLES = ("admin", "analyst", "student")


def _deployment_mode() -> str:
    """Return the deployment mode, failing closed for invalid values.

    Existing installations predate this setting and therefore remain server
    deployments. Newly generated .env files set the mode explicitly.
    """
    mode = os.environ.get("NETRUNNER_DEPLOYMENT_MODE", "server").strip().lower()
    return mode if mode in ("server", "student") else "student"


def _role_enabled(role: str | None) -> bool:
    return _deployment_mode() == "server" or role == "student"


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


# --- Rate limiting for login ------------------------------------------------ #
# Simple in-memory rate limiter: max 5 failed attempts per IP per 15 minutes
_LOGIN_ATTEMPTS: dict[tuple[str, str], list[float]] = defaultdict(list)
_MAX_ATTEMPTS = 5
_WINDOW_SECONDS = 15 * 60  # 15 minutes


def _check_rate_limit(key: tuple[str, str]) -> tuple[bool, int]:
    """Check if IP is rate limited. Returns (allowed, remaining_attempts)."""
    now = time.time()
    attempts = _LOGIN_ATTEMPTS[key]
    # Remove old attempts outside the window
    while attempts and attempts[0] < now - _WINDOW_SECONDS:
        attempts.pop(0)
    if len(attempts) >= _MAX_ATTEMPTS:
        return False, 0
    return True, _MAX_ATTEMPTS - len(attempts)


def _record_failed_attempt(key: tuple[str, str]) -> None:
    _LOGIN_ATTEMPTS[key].append(time.time())


def _clear_attempts(key: tuple[str, str]) -> None:
    """Clear failed attempts for one account and client on successful login."""
    _LOGIN_ATTEMPTS.pop(key, None)


async def seed_default_users():
    """Create or synchronize the built-in deployment accounts.

    Student deployments seed only the student account. Server deployments seed
    all three built-in accounts. Passwords must come from the environment and
    are never generated or printed by the backend. When
    NETRUNNER_SYNC_DEFAULT_PASSWORDS=1, existing built-in accounts are
    synchronized with the deployment environment.
    """
    sync_passwords = os.environ.get("NETRUNNER_SYNC_DEFAULT_PASSWORDS") == "1"
    usernames = (
        ("admin", "analyst", "student")
        if _deployment_mode() == "server"
        else ("student",)
    )
    for username in usernames:
        existing = await get_user_db(username)
        env_pw = os.environ.get(f"NETRUNNER_{username.upper()}_PASSWORD")

        if existing:
            if sync_passwords and env_pw and not _verify(existing, env_pw):
                password_hash, salt = _make_hash(env_pw)
                existing["password_hash"] = password_hash
                existing["salt"] = salt
                await save_user_db(existing)
                logger.info(
                    f"Synchronized built-in '{username}' password from deployment environment"
                )
            continue

        if not env_pw:
            raise RuntimeError(
                f"NETRUNNER_{username.upper()}_PASSWORD is required for "
                f"{_deployment_mode()} deployment"
            )
        pw = env_pw
        source = f"NETRUNNER_{username.upper()}_PASSWORD"
        h, s = _make_hash(pw)
        await save_user_db(
            {
                "username": username,
                "password_hash": h,
                "salt": s,
                "role": "student" if username == "student" else ("admin" if username == "admin" else "analyst"),
                "created": date.today().isoformat(),
            }
        )
        logger.info(f"Created default '{username}' user (source: {source})")


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Validate a JWT and return the normalized authenticated user."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        role = payload.get("role")
        if not username or role not in ROLES or not _role_enabled(role):
            raise HTTPException(401, "Invalid token")
        return {"username": username, "role": role}
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid token")


async def get_current_user(token: str = Depends(oauth2_scheme)):
    return decode_access_token(token)


def require_admin(user: dict = Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(403, "Insufficient permissions. Admin role required.")
    return user


def require_non_student(user: dict = Depends(get_current_user)):
    if user.get("role") not in ("admin", "analyst"):
        raise HTTPException(403, "Insufficient permissions. Admin or analyst role required.")
    return user


@router.post("/auth/login")
@limiter.limit("60/minute")
async def login(req: LoginRequest, request: Request):
    # Failed-attempt lockout is scoped to account + client so one mistyped
    # classroom login cannot lock out every account behind the same NAT/proxy.
    # The broader SlowAPI limit still caps username-spraying from one client.
    client_ip = request.client.host if request.client else "unknown"
    attempt_key = (client_ip, req.username.strip().casefold())
    allowed, remaining = _check_rate_limit(attempt_key)
    if not allowed:
        raise HTTPException(
            429, "Too many login attempts. Please try again in 15 minutes."
        )

    user = await get_user_db(req.username)
    if not user or not _role_enabled(user.get("role")) or not _verify(user, req.password):
        _record_failed_attempt(attempt_key)
        raise HTTPException(401, "Invalid credentials")

    _clear_attempts(attempt_key)
    token = create_access_token({"sub": req.username, "role": user["role"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user["role"],
        "username": req.username,
    }


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
    return {
        "users": [
            {"username": u["username"], "role": u["role"], "created": u.get("created")}
            for u in users
        ]
    }


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
    await save_user_db(
        {
            "username": username,
            "password_hash": h,
            "salt": s,
            "role": req.role,
            "created": date.today().isoformat(),
        }
    )
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


async def authenticate_ws(
    websocket: WebSocket, allowed_roles: tuple[str, ...] | None = None
) -> dict | None:
    """Validate a WebSocket connection via a `?token=` query parameter.

    Browsers can't set Authorization headers on WebSocket handshakes, so the
    JWT is passed as a query parameter. Returns the user dict on success.
    On failure it accepts then immediately closes the socket (policy violation)
    and returns None — callers should `return` when they get None.
    """
    token = websocket.query_params.get("token")
    if token:
        try:
            user = decode_access_token(token)
            if allowed_roles is None or user["role"] in allowed_roles:
                return user
            await websocket.accept()
            await websocket.close(code=4403)
            return None
        except HTTPException:
            pass
    await websocket.accept()
    await websocket.close(code=4401)  # 4401: unauthorized (app-defined)
    return None
