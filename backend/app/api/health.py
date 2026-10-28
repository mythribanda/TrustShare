import logging
from fastapi import APIRouter, Response, status
from sqlalchemy import select
from app.core.config import get_settings
from app.core.db import engine, db_backend
from app.core.mongo import get_mongo_client
from app.core.redis import get_redis

logger = logging.getLogger("trustshare.api.health")
router = APIRouter(tags=["health"])

@router.get("/health")
def health():
    return {"status": "ok"}

@router.get("/health/ready")
def health_ready(response: Response):
    settings = get_settings()

    db_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(select(1))
            db_ok = True
    except Exception as e:
        logger.warning(f"Database readiness check failed: {e}")

    mongo_ok = False
    client = get_mongo_client()
    if client:
        try:
            client.admin.command("ping")
            mongo_ok = True
        except Exception:
            pass

    redis_ok = False
    cache = get_redis()
    if cache:
        try:
            redis_ok = bool(cache.ping())
        except Exception:
            pass

    pg_status = (
        "connected" if (db_ok and db_backend == "postgres")
        else ("fallback_sqlite" if (db_ok and db_backend == "sqlite_fallback") else "disconnected")
    )

    is_ready = db_ok and mongo_ok and redis_ok and not (settings.IS_PRODUCTION and db_backend == "sqlite_fallback")
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ok" if is_ready else "degraded",
        "environment": settings.APP_ENV,
        "database": db_backend,
        "postgres": pg_status,
        "mongodb": "connected" if mongo_ok else "disconnected",
        "redis": "connected" if redis_ok else "disconnected",
    }
