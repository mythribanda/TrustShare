import logging
from typing import Optional
import redis
from app.core.config import get_settings

logger = logging.getLogger("trustshare.redis")

_redis_client: Optional[redis.Redis] = None

def init_redis() -> Optional[redis.Redis]:
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    settings = get_settings()
    url = settings.REDIS_URL
    candidates = list(dict.fromkeys([
        url,
        url.replace("://redis:", "://localhost:"),
        "redis://localhost:6379/0"
    ]))

    for u in candidates:
        try:
            r = redis.Redis.from_url(u, decode_responses=True, socket_connect_timeout=1)
            r.ping()
            _redis_client = r
            logger.info(f"Redis connected successfully via {u}")
            return _redis_client
        except Exception:
            pass

    logger.warning("Redis is currently unavailable.")
    return None

def get_redis() -> Optional[redis.Redis]:
    global _redis_client
    if _redis_client is None:
        _redis_client = init_redis()
    return _redis_client
