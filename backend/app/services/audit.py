import logging
from datetime import datetime, timezone
from typing import Optional, Any, Dict
from fastapi import Request
from app.core.mongo import get_mongo_db, is_mongo_available

logger = logging.getLogger("trustshare.audit")

def log_event(
    actor_id: Optional[int] = None,
    action: str = "",
    resource_type: str = "system",
    resource_id: Optional[Any] = None,
    request: Optional[Request] = None,
    metadata: Optional[Dict[str, Any]] = None,
):
    """
    Log structured audit events to MongoDB activity_logs collection.
    Automatically captures client IP, User-Agent, and Request-ID when request object is supplied.
    """
    if not is_mongo_available():
        return

    db = get_mongo_db()
    if db is None:
        return

    ip = None
    user_agent = None
    request_id = None

    if request is not None:
        ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        request_id = getattr(request.state, "request_id", None) or request.headers.get("x-request-id")

    now = datetime.now(timezone.utc)

    event_doc = {
        "actor_id": actor_id,
        "action": action,
        "resource_type": resource_type,
        "resource_id": str(resource_id) if resource_id is not None else None,
        "ip": ip,
        "user_agent": user_agent,
        "request_id": request_id,
        "metadata": metadata or {},
        "created_at": now,
    }

    try:
        # Canonical activity_logs collection per spec
        db["activity_logs"].insert_one(event_doc)

        # Legacy activity collection mirror for backward compatibility with existing tests
        legacy_doc = {
            "event": action,
            "user_id": actor_id,
            "details": metadata or {},
            "timestamp": now,
        }
        if resource_id is not None and "file_id" not in legacy_doc["details"]:
            legacy_doc["details"]["file_id"] = resource_id
        db["activity"].insert_one(legacy_doc)
    except Exception as exc:
        logger.warning(f"MongoDB log_event failed for action '{action}': {exc}")
