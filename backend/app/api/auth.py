import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import get_db, current_user, check_rate_limit, bearer_scheme
from app.core.redis import get_redis
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    generate_refresh_token,
    hash_token,
    get_session_key,
)
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.schemas.auth import RegisterIn, LoginIn
from app.services.audit import log_event

logger = logging.getLogger("trustshare.api.auth")
router = APIRouter(prefix="/api/auth", tags=["auth"])

def user_dict(u: User):
    return {
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "role": u.role,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }

def set_refresh_cookie(response: Response, raw_token: str):
    settings = get_settings()
    response.set_cookie(
        key="refresh_token",
        value=raw_token,
        httponly=True,
        samesite="strict",
        secure=settings.IS_PRODUCTION,
        path="/api/auth",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, request: Request, response: Response, db: Session = Depends(get_db)):
    settings = get_settings()
    client_ip = request.client.host if request.client else "127.0.0.1"
    check_rate_limit(f"ratelimit:register:{client_ip}", limit=10, window=60)

    email = data.email.lower().strip()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")

    user = User(
        name=data.name.strip(),
        email=email,
        password_hash=hash_password(data.password),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Access Token (15 min)
    access_token = create_access_token(user.id, user.role)

    # Refresh Token (7 days)
    raw_refresh = generate_refresh_token()
    refresh_rec = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw_refresh),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(refresh_rec)
    db.commit()

    set_refresh_cookie(response, raw_refresh)

    cache = get_redis()
    session_stored = False
    if cache:
        try:
            cache.setex(
                get_session_key(user.id, access_token),
                settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                "active",
            )
            session_stored = True
        except Exception as e:
            logger.warning(f"Redis session write failed on register: {e}")

    if settings.IS_PRODUCTION and not session_stored:
        raise HTTPException(status_code=503, detail="Unable to store active session in production. Registration aborted.")

    log_event(
        actor_id=user.id,
        action="register",
        resource_type="user",
        resource_id=user.id,
        request=request,
        metadata={"email": email},
    )

    return {"user": user_dict(user), "access_token": access_token, "token_type": "bearer"}

@router.post("/login")
def login(data: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    settings = get_settings()
    client_ip = request.client.host if request.client else "127.0.0.1"
    check_rate_limit(f"ratelimit:login:{client_ip}", limit=5, window=60)

    email = data.email.lower().strip()
    user = db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(data.password, user.password_hash):
        log_event(
            actor_id=None,
            action="login_failed",
            resource_type="user",
            resource_id=None,
            request=request,
            metadata={"email": email},
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    access_token = create_access_token(user.id, user.role)

    # Generate and store refresh token
    raw_refresh = generate_refresh_token()
    refresh_rec = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw_refresh),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(refresh_rec)
    db.commit()

    set_refresh_cookie(response, raw_refresh)

    cache = get_redis()
    session_stored = False
    if cache:
        try:
            cache.setex(
                get_session_key(user.id, access_token),
                settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                "active",
            )
            session_stored = True
        except Exception as e:
            logger.warning(f"Redis session write failed on login: {e}")

    if settings.IS_PRODUCTION and not session_stored:
        raise HTTPException(status_code=503, detail="Unable to store active session in production. Login aborted.")

    log_event(
        actor_id=user.id,
        action="login",
        resource_type="user",
        resource_id=user.id,
        request=request,
    )

    return {"user": user_dict(user), "access_token": access_token, "token_type": "bearer"}

@router.post("/refresh")
def refresh_token_endpoint(request: Request, response: Response, db: Session = Depends(get_db)):
    settings = get_settings()
    client_ip = request.client.host if request.client else "127.0.0.1"
    check_rate_limit(f"ratelimit:refresh:{client_ip}", limit=20, window=60)

    raw_token = request.cookies.get("refresh_token")
    if not raw_token:
        # Fallback to Authorization header or JSON payload if cookie absent
        try:
            body = request.json() if hasattr(request, "json") else {}
            if isinstance(body, dict):
                raw_token = body.get("refresh_token")
        except Exception:
            pass

    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token required")

    tok_hash = hash_token(raw_token)
    token_record = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == tok_hash))
    if not token_record:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    # Reuse detection: If token was already revoked or replaced, invalidate the entire token family
    if token_record.revoked_at is not None or token_record.replaced_by is not None:
        logger.warning(f"Refresh token reuse detected for user {token_record.user_id}! Revoking all refresh tokens and sessions.")
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == token_record.user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )
        db.commit()

        # Revoke all Redis sessions for this user
        cache = get_redis()
        if cache:
            try:
                for k in cache.scan_iter(f"session:{token_record.user_id}:*"):
                    cache.delete(k)
            except Exception as e:
                logger.warning(f"Failed to clear Redis sessions on token reuse: {e}")

        response.delete_cookie(key="refresh_token", path="/api/auth")
        log_event(
            actor_id=token_record.user_id,
            action="token_reuse_revoked_family",
            resource_type="refresh_token",
            resource_id=token_record.id,
            request=request,
            metadata={"token_id": token_record.id},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token reuse detected. All sessions have been revoked. Please log in again."
        )

    # Check expiration
    now = datetime.now(timezone.utc)
    expires_at = token_record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now:
        token_record.revoked_at = now
        db.commit()
        response.delete_cookie(key="refresh_token", path="/api/auth")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has expired")

    user = db.get(User, token_record.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account not found")

    # Single-use rotation: mark current token replaced and create new refresh token
    new_raw_refresh = generate_refresh_token()
    new_hash = hash_token(new_raw_refresh)

    token_record.revoked_at = now
    token_record.replaced_by = new_hash

    new_refresh_rec = RefreshToken(
        user_id=user.id,
        token_hash=new_hash,
        expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(new_refresh_rec)
    db.commit()

    # Issue new 15-minute access token
    new_access_token = create_access_token(user.id, user.role)
    cache = get_redis()
    if cache:
        try:
            cache.setex(
                get_session_key(user.id, new_access_token),
                settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                "active",
            )
        except Exception as e:
            logger.warning(f"Redis session update failed on refresh: {e}")

    set_refresh_cookie(response, new_raw_refresh)

    log_event(
        actor_id=user.id,
        action="token_refreshed",
        resource_type="refresh_token",
        resource_id=new_refresh_rec.id,
        request=request,
    )

    return {"access_token": new_access_token, "token_type": "bearer"}

@router.get("/me")
def me(user: User = Depends(current_user)):
    return {"user": user_dict(user)}

@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    # Revoke refresh token in database if cookie present
    raw_refresh = request.cookies.get("refresh_token")
    if raw_refresh:
        tok_hash = hash_token(raw_refresh)
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == tok_hash, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )
        db.commit()

    # Clear cookie
    response.delete_cookie(key="refresh_token", path="/api/auth")

    # Clear access token session in Redis
    cache = get_redis()
    if cache and creds:
        try:
            cache.delete(get_session_key(user.id, creds.credentials))
        except Exception as e:
            logger.warning(f"Redis session deletion failed on logout: {e}")

    log_event(actor_id=user.id, action="logout", resource_type="user", resource_id=user.id, request=request)
    return {"message": "Logged out. Session revoked."}
