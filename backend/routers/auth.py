import os
import secrets
from pathlib import Path

import jwt
from datetime import datetime, timedelta
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

# In-memory users for demo
USERS = {
    "admin": {"password": "admin", "role": "admin"},
    "analyst": {"password": "analyst", "role": "analyst"}
}

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=24)
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
    if not user or user["password"] != req.password:
        raise HTTPException(401, "Invalid credentials")
    
    token = create_access_token({"sub": req.username, "role": user["role"]})
    return {"access_token": token, "token_type": "bearer", "role": user["role"], "username": req.username}

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
