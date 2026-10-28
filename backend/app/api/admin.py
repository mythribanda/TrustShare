import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_roles
from app.core.mongo import get_mongo_db, is_mongo_available
from app.models.user import User
from app.models.file import StoredFile
from app.api.auth import user_dict
from app.api.files import file_dict
from app.services.audit import log_event

logger = logging.getLogger("trustshare.api.admin")
router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/users")
def list_users(user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    users = db.scalars(select(User).order_by(User.id.desc())).all()
    return [user_dict(u) for u in users]

@router.post("/reconcile-metadata")
def reconcile_metadata(
    request: Request,
    user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    if not is_mongo_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MongoDB is unavailable. Cannot reconcile metadata."
        )

    db_mongo = get_mongo_db()
    if db_mongo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MongoDB is unavailable. Cannot reconcile metadata."
        )

    files = db.scalars(select(StoredFile)).all()
    scanned = len(files)
    fixed = 0
    failed = 0

    for f in files:
        needs_sync = not getattr(f, "meta_synced", True)
        if not needs_sync:
            try:
                existing = db_mongo.files.find_one({"id": f.id})
                if not existing:
                    needs_sync = True
            except Exception as e:
                logger.warning(f"MongoDB check failed during reconciliation for file {f.id}: {e}")
                failed += 1
                continue

        if needs_sync:
            metadata = {
                **file_dict(f),
                "event": "file_uploaded",
                "reconciled": True,
                "timestamp": f.uploaded_at or datetime.now(timezone.utc),
            }
            try:
                db_mongo.files.replace_one({"id": f.id}, metadata, upsert=True)
                f.meta_synced = True
                db.commit()
                fixed += 1
            except Exception as e:
                logger.warning(f"Failed to reconcile metadata for file {f.id}: {e}")
                failed += 1

    log_event(
        actor_id=user.id,
        action="metadata_reconciled",
        resource_type="system",
        resource_id=None,
        request=request,
        metadata={"scanned": scanned, "fixed": fixed, "failed": failed},
    )

    return {
        "message": f"Reconciliation complete: {fixed} fixed, {failed} failed out of {scanned} records.",
        "scanned": scanned,
        "fixed": fixed,
        "failed": failed,
    }

@router.post("/keys/rewrap")
def rewrap_keys(
    request: Request,
    user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """
    Admin-only: rewraps all file_keys not on the current KEK version.
    Processes in batches of 100 with a database transaction per batch.
    Returns rewrapped count only.
    """
    import base64
    from app.models.file_key import FileKey
    from app.services.keys import get_key_manager

    km = get_key_manager()
    curr_ver_val = int(km.current_version) if str(km.current_version).isdigit() else km.current_version

    batch_size = 100
    total_rewrapped = 0
    seen_ids = set()

    while True:
        query = select(FileKey).where(FileKey.key_version != curr_ver_val)
        if seen_ids:
            query = query.where(~FileKey.id.in_(seen_ids))
        batch = db.scalars(query.limit(batch_size)).all()

        if not batch:
            break

        for fk in batch:
            seen_ids.add(fk.id)
            raw_blob = None
            if isinstance(fk.wrapped_dek, str):
                try:
                    raw_blob = base64.b64decode(fk.wrapped_dek, validate=True)
                except Exception:
                    raw_blob = fk.wrapped_dek.encode("latin1")
            else:
                raw_blob = fk.wrapped_dek

            try:
                new_blob, new_ver = km.rewrap(raw_blob, str(fk.key_version), fk.file_id)
                fk.wrapped_dek = base64.b64encode(new_blob).decode("ascii")
                fk.key_version = int(new_ver) if str(new_ver).isdigit() else new_ver
                total_rewrapped += 1
            except Exception as exc:
                logger.warning(f"Failed to rewrap file_key {fk.id} for file {fk.file_id}: {exc}")

        db.commit()

    log_event(
        actor_id=user.id,
        action="keys_rewrapped",
        resource_type="key_management",
        resource_id=None,
        request=request,
        metadata={"count": total_rewrapped, "current_version": str(km.current_version)},
    )

    return {"count": total_rewrapped, "rewrapped_count": total_rewrapped}

v1_admin_router = APIRouter(prefix="/api/v1/admin", tags=["admin-v1"])
v1_admin_router.add_api_route("/keys/rewrap", rewrap_keys, methods=["POST"])


