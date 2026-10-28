import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
from jose import jwt
from app.core.config import get_settings

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def create_access_token(user_id: int, role: str, expires_delta: Optional[timedelta] = None) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)

def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

def get_session_key(user_id: int, token: str) -> str:
    token_hash = hash_token(token)[:16]
    return f"session:{user_id}:{token_hash}"
