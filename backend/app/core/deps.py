import logging
from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.redis import get_redis
from app.core.security import get_session_key
from app.models.user import User

logger = logging.getLogger("trustshare.deps")
bearer_scheme = HTTPBearer(auto_error=False)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_rate_limit(key: str, limit: int, window: int = 60):
    settings = get_settings()
    cache = get_redis()
    if not cache:
        if settings.IS_PRODUCTION:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Rate limiter unavailable. Request rejected in production."
            )
        logger.warning("Redis rate limiting bypassed (cache unavailable) in development.")
        return

    try:
        count = cache.incr(key)
        if count == 1:
            cache.expire(key, window)
        if count > limit:
            ttl = cache.ttl(key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Too many requests. Please wait {max(ttl, 1)} seconds before trying again."
            )
    except HTTPException:
        raise
    except Exception as e:
        if settings.IS_PRODUCTION:
            logger.error(f"Redis rate limiting error in production: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Rate limiter error. Request rejected in production."
            )
        logger.warning(f"Redis rate limiting bypassed due to error: {e}")

def current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> User:
    if not creds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    settings = get_settings()
    token = creds.credentials

    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        uid = int(payload["sub"])
    except (JWTError, ValueError, KeyError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    cache = get_redis()
    if not cache:
        if settings.IS_PRODUCTION:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Session store is unavailable. Cannot validate session in production."
            )
        logger.warning("Redis session check bypassed in development: Redis is not available.")
    else:
        try:
            session_key = get_session_key(uid, token)
            if not cache.exists(session_key):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session has expired or was revoked")
        except HTTPException:
            raise
        except Exception as e:
            if settings.IS_PRODUCTION:
                logger.error(f"Redis session lookup failed in production: {e}")
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Session validation error in production")
            logger.warning(f"Redis session lookup failed: {e}")

    user = db.get(User, uid)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account not found")
    return user

def require_roles(*roles: str):
    def check(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user
    return check
