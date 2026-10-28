import logging
from typing import Optional, Tuple
from pymongo import MongoClient, ASCENDING, DESCENDING
from app.core.config import get_settings

logger = logging.getLogger("trustshare.mongo")

_mongo_client: Optional[MongoClient] = None
_mongo_available: bool = False

def init_mongo() -> Tuple[MongoClient, bool]:
    global _mongo_client, _mongo_available
    if _mongo_client is not None:
        return _mongo_client, _mongo_available

    settings = get_settings()
    url = settings.MONGO_URL
    candidates = list(dict.fromkeys([
        url,
        url.replace("://mongo:", "://localhost:"),
        "mongodb://localhost:27017"
    ]))

    for u in candidates:
        try:
            client = MongoClient(u, serverSelectionTimeoutMS=500)
            client.admin.command("ping")
            _mongo_client = client
            _mongo_available = True
            logger.info(f"MongoDB connected successfully via {u}")
            return _mongo_client, True
        except Exception:
            pass

    _mongo_client = MongoClient(url, serverSelectionTimeoutMS=500)
    _mongo_available = False
    logger.warning("MongoDB is currently unavailable.")
    return _mongo_client, False

def get_mongo_client() -> MongoClient:
    client, _ = init_mongo()
    return client

def is_mongo_available() -> bool:
    global _mongo_available
    if not _mongo_available:
        init_mongo()
    return _mongo_available

def get_mongo_db():
    if not is_mongo_available():
        return None
    settings = get_settings()
    return get_mongo_client()[settings.MONGO_DB]

def init_mongo_indexes():
    """Ensure indexes on activity_logs and files collections."""
    db = get_mongo_db()
    if db is None:
        return
    try:
        activity_logs = db["activity_logs"]
        activity_logs.create_index([("actor_id", ASCENDING), ("created_at", DESCENDING)])
        activity_logs.create_index([("action", ASCENDING), ("created_at", DESCENDING)])
        activity_logs.create_index([("resource_id", ASCENDING)])
        logger.info("MongoDB indexes verified on activity_logs collection.")

        # Secondary index on files
        db["files"].create_index([("id", ASCENDING)], unique=True)
    except Exception as e:
        logger.warning(f"Could not create MongoDB indexes: {e}")
