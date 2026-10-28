import base64
import hashlib
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, status
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import get_db, current_user, check_rate_limit
from app.core.mongo import get_mongo_db, is_mongo_available
from app.models.user import User
from app.models.folder import Folder
from app.models.file import StoredFile
from app.models.file_key import FileKey
from app.models.permission import Permission
from app.models.version import FileVersion
from app.schemas.file import FileOut, FileUpdate, FileVersionOut
from app.services.audit import log_event
from app.services.crypto import encrypt_bytes, decrypt_bytes, zero_bytearray
from app.services.keys import get_key_manager
from app.services.storage import get_storage

logger = logging.getLogger("trustshare.api.files")
router = APIRouter(prefix="/api/files", tags=["files"])
v1_router = APIRouter(prefix="/api/v1/files", tags=["files-v1"])

def sanitize_filename(filename: Optional[str]) -> str:
    """Sanitize original filename, stripping directory path traversal components."""
    if not filename:
        return "unnamed_file"
    # Convert windows and posix separators to pure basename
    name = Path(filename.replace("\\", "/")).name
    # Strip any remaining leading periods or whitespace
    cleaned = name.strip()
    return cleaned if cleaned else "unnamed_file"

def get_file_or_404(
    file_id: int,
    user: User,
    db: Session,
    required_role: Optional[str] = None,
) -> StoredFile:
    """
    Owner/permission check that returns 404 (NEVER 403) for files the user cannot see.
    """
    file_rec = db.scalar(
        select(StoredFile)
        .where(StoredFile.id == file_id, StoredFile.deleted_at.is_(None), StoredFile.status != "deleted")
    )
    if not file_rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    is_owner = file_rec.owner_id == user.id
    is_admin = user.role == "admin"

    if is_owner or is_admin:
        if required_role == "owner" and not is_owner and not is_admin:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        return file_rec

    # Check permissions table for shared access
    perm = db.scalar(
        select(Permission).where(Permission.file_id == file_id, Permission.user_id == user.id)
    )
    if not perm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    if required_role == "owner":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    if required_role == "editor" and perm.role not in ("editor", "owner"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    return file_rec

def file_dict(f: StoredFile) -> dict:
    """Sanitized file response dictionary. storage_key and keys are strictly excluded."""
    return {
        "id": f.id,
        "name": f.original_name,
        "content_type": f.content_type,
        "size": f.size,
        "sha256": f.sha256,
        "owner_id": f.owner_id,
        "folder_id": f.folder_id,
        "category": f.category,
        "status": f.status,
        "version": f.version,
        "meta_synced": getattr(f, "meta_synced", True),
        "uploaded_at": f.uploaded_at.isoformat() if f.uploaded_at else None,
    }

@router.get("", response_model=List[FileOut])
def list_files(
    folder_id: Optional[int] = None,
    category: Optional[str] = None,
    q: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    stmt = (
        select(StoredFile)
        .where(
            StoredFile.owner_id == user.id,
            StoredFile.status == "ready",
            StoredFile.deleted_at.is_(None),
        )
    )
    if folder_id is not None:
        stmt = stmt.where(StoredFile.folder_id == folder_id)
    if category is not None:
        stmt = stmt.where(StoredFile.category == category)
    if q:
        stmt = stmt.where(StoredFile.original_name.ilike(f"%{q[:100]}%"))

    files = db.scalars(
        stmt.order_by(StoredFile.uploaded_at.desc())
        .offset(max(0, skip))
        .limit(min(max(1, limit), 100))
    ).all()
    return [file_dict(f) for f in files]

@router.post("", response_model=FileOut, status_code=status.HTTP_201_CREATED)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    folder_id: Optional[int] = Form(None),
    category: Optional[str] = Form(None),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    check_rate_limit(f"ratelimit:upload:{user.id}", limit=30, window=60)

    # 1. Validation: sanitize filename
    sanitized_name = sanitize_filename(file.filename)
    suffix = Path(sanitized_name).suffix.lower()

    if suffix not in settings.ALLOWED_EXTENSIONS_SET:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File extension '{suffix}' is not allowed.",
        )

    if settings.ALLOWED_CONTENT_TYPES_SET and file.content_type:
        if file.content_type.lower() not in settings.ALLOWED_CONTENT_TYPES_SET:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Content-Type '{file.content_type}' is not allowed.",
            )

    if folder_id is not None:
        folder = db.scalar(select(Folder).where(Folder.id == folder_id, Folder.owner_id == user.id))
        if not folder:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")

    # 2. Stream read while checking size limit (don't read unbounded into memory)
    chunk_size = 64 * 1024
    total_bytes = bytearray()
    digest = hashlib.sha256()

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        if len(total_bytes) + len(chunk) > settings.MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum upload size of {settings.MAX_UPLOAD_MB} MiB.",
            )
        total_bytes.extend(chunk)
        digest.update(chunk)

    if len(total_bytes) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty files are not allowed.")

    total_size = len(total_bytes)
    sha256_hex = digest.hexdigest()
    content_type = file.content_type or "application/octet-stream"

    # 3. Create initial pending row
    file_rec = StoredFile(
        original_name=sanitized_name,
        storage_key=f"pending_{uuid.uuid4().hex}",
        content_type=content_type,
        size=total_size,
        sha256=sha256_hex,
        owner_id=user.id,
        folder_id=folder_id,
        category=category,
        status="pending",
        version=1,
        meta_synced=True,
    )
    db.add(file_rec)
    db.commit()
    db.refresh(file_rec)

    storage = get_storage()
    km = get_key_manager()
    s3_key = f"files/{user.id}/{file_rec.id}/v1"
    file_rec.storage_key = s3_key
    written_to_s3 = False

    try:
        # 4. Generate random DEK and encrypt in memory
        raw_dek = km.generate_dek()
        wrapped_dek, kek_ver = km.wrap_dek(bytearray(raw_dek), file_rec.id)
        ciphertext, nonce = encrypt_bytes(bytes(total_bytes), bytearray(raw_dek), file_rec.id)
        zero_bytearray(raw_dek)

        # 5. Upload ciphertext to S3
        await storage.put_object(s3_key, ciphertext, content_type="application/octet-stream")
        written_to_s3 = True

        # 6. Store wrapped DEK in file_keys
        fk = FileKey(
            file_id=file_rec.id,
            wrapped_dek=base64.b64encode(wrapped_dek).decode("ascii"),
            key_version=int(kek_ver) if str(kek_ver).isdigit() else kek_ver,
            file_version=1,
            nonce=base64.b64encode(nonce).decode("ascii"),
        )
        db.add(fk)

        # 7. Create initial FileVersion
        fv = FileVersion(
            file_id=file_rec.id,
            version=1,
            storage_key=s3_key,
            size=total_size,
            sha256=sha256_hex,
        )
        db.add(fv)

        # 8. Create owner permission row
        owner_perm = Permission(
            file_id=file_rec.id,
            user_id=user.id,
            role="owner",
            granted_by=user.id,
        )
        db.add(owner_perm)

        # 9. Mark status ready
        file_rec.status = "ready"
        db.commit()
        db.refresh(file_rec)

        # 10. Audit log
        log_event(
            actor_id=user.id,
            action="file_uploaded",
            resource_type="file",
            resource_id=file_rec.id,
            request=request,
            metadata={"name": sanitized_name, "size": total_size, "category": category},
        )

        return file_dict(file_rec)

    except Exception:
        # Failure compensation: clean up S3 and mark deleted
        if written_to_s3:
            try:
                await storage.delete_object(s3_key)
            except Exception as del_exc:
                logger.error(f"Failed to delete S3 object {s3_key} during rollback: {del_exc}")

        try:
            file_rec.status = "deleted"
            file_rec.deleted_at = datetime.now(timezone.utc)
            db.commit()
        except Exception as db_exc:
            logger.error(f"Failed to mark file {file_rec.id} as deleted on error: {db_exc}")
            db.rollback()

        raise
    finally:
        await file.close()

@router.get("/{file_id}", response_model=FileOut)
def get_file(
    file_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    file_rec = get_file_or_404(file_id, user, db)
    return file_dict(file_rec)

@router.patch("/{file_id}", response_model=FileOut)
def update_file(
    file_id: int,
    data: FileUpdate,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    file_rec = get_file_or_404(file_id, user, db, required_role="owner")

    if data.name is not None:
        sanitized = sanitize_filename(data.name)
        if not sanitized:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="File name cannot be empty")
        file_rec.original_name = sanitized

    if data.folder_id is not None:
        if data.folder_id != 0:
            folder = db.scalar(select(Folder).where(Folder.id == data.folder_id, Folder.owner_id == user.id))
            if not folder:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target folder not found")
            file_rec.folder_id = data.folder_id
        else:
            file_rec.folder_id = None

    if data.category is not None:
        file_rec.category = data.category.strip() if data.category.strip() else None

    db.commit()
    db.refresh(file_rec)

    log_event(
        actor_id=user.id,
        action="file_updated",
        resource_type="file",
        resource_id=file_id,
        request=request,
        metadata={"name": file_rec.original_name, "folder_id": file_rec.folder_id, "category": file_rec.category},
    )

    return file_dict(file_rec)

@router.delete("/{file_id}", status_code=status.HTTP_200_OK)
async def delete_file(
    file_id: int,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    file_rec = get_file_or_404(file_id, user, db, required_role="owner")
    storage = get_storage()

    # 1. Soft delete status
    file_rec.status = "deleted"
    file_rec.deleted_at = datetime.now(timezone.utc)

    # 2. Delete main S3 object and all version objects
    try:
        await storage.delete_object(file_rec.storage_key)
    except Exception as exc:
        logger.warning(f"Error removing main S3 object {file_rec.storage_key}: {exc}")

    for v in file_rec.versions:
        try:
            await storage.delete_object(v.storage_key)
        except Exception as exc:
            logger.warning(f"Error removing version S3 object {v.storage_key}: {exc}")

    # 3. Delete file_keys row so data is cryptographically unrecoverable
    db.execute(delete(FileKey).where(FileKey.file_id == file_id))

    db.commit()

    log_event(
        actor_id=user.id,
        action="file_deleted",
        resource_type="file",
        resource_id=file_id,
        request=request,
    )

    return {"message": "File deleted"}

@router.post("/{file_id}/versions", response_model=FileVersionOut, status_code=status.HTTP_201_CREATED)
async def upload_file_version(
    file_id: int,
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    file_rec = get_file_or_404(file_id, user, db, required_role="owner")
    settings = get_settings()

    # Validation
    sanitized_name = sanitize_filename(file.filename)
    suffix = Path(sanitized_name).suffix.lower()
    if suffix not in settings.ALLOWED_EXTENSIONS_SET:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File extension '{suffix}' is not allowed.",
        )

    # Stream read
    chunk_size = 64 * 1024
    total_bytes = bytearray()
    digest = hashlib.sha256()

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        if len(total_bytes) + len(chunk) > settings.MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum upload size of {settings.MAX_UPLOAD_MB} MiB.",
            )
        total_bytes.extend(chunk)
        digest.update(chunk)

    if len(total_bytes) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty files are not allowed.")

    total_size = len(total_bytes)
    sha256_hex = digest.hexdigest()

    storage = get_storage()
    km = get_key_manager()
    new_version = file_rec.version + 1
    new_s3_key = f"files/{user.id}/{file_rec.id}/v{new_version}"
    written_to_s3 = False

    try:
        raw_dek = km.generate_dek()
        wrapped_dek, kek_ver = km.wrap_dek(bytearray(raw_dek), file_rec.id)
        ciphertext, nonce = encrypt_bytes(bytes(total_bytes), bytearray(raw_dek), file_rec.id)
        zero_bytearray(raw_dek)

        await storage.put_object(new_s3_key, ciphertext, content_type="application/octet-stream")
        written_to_s3 = True

        fk = FileKey(
            file_id=file_rec.id,
            wrapped_dek=base64.b64encode(wrapped_dek).decode("ascii"),
            key_version=int(kek_ver) if str(kek_ver).isdigit() else kek_ver,
            file_version=new_version,
            nonce=base64.b64encode(nonce).decode("ascii"),
        )
        db.add(fk)

        fv = FileVersion(
            file_id=file_rec.id,
            version=new_version,
            storage_key=new_s3_key,
            size=total_size,
            sha256=sha256_hex,
        )
        db.add(fv)

        file_rec.version = new_version
        file_rec.size = total_size
        file_rec.sha256 = sha256_hex
        file_rec.storage_key = new_s3_key
        db.commit()
        db.refresh(fv)

        log_event(
            actor_id=user.id,
            action="file_version_created",
            resource_type="file",
            resource_id=file_rec.id,
            request=request,
            metadata={"version": new_version, "size": total_size},
        )

        return {
            "version": fv.version,
            "size": fv.size,
            "sha256": fv.sha256,
            "created_at": fv.created_at.isoformat() if fv.created_at else None,
        }

    except Exception:
        if written_to_s3:
            try:
                await storage.delete_object(new_s3_key)
            except Exception:
                pass
        db.rollback()
        raise
    finally:
        await file.close()

@router.get("/{file_id}/versions", response_model=List[FileVersionOut])
def list_file_versions(
    file_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    file_rec = get_file_or_404(file_id, user, db)
    versions = db.scalars(
        select(FileVersion)
        .where(FileVersion.file_id == file_rec.id)
        .order_by(FileVersion.version.asc())
    ).all()
    return [
        {
            "version": v.version,
            "size": v.size,
            "sha256": v.sha256,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in versions
    ]

@router.get("/{file_id}/metadata")
def get_file_metadata(
    file_id: int,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    file_rec = get_file_or_404(file_id, user, db)
    return {"source": "postgres", "synced": True, "metadata": file_dict(file_rec)}

@router.get("/{file_id}/download")
async def download_file(
    file_id: int,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    from fastapi.responses import Response

    file_rec = get_file_or_404(file_id, user, db)
    storage = get_storage()
    km = get_key_manager()

    try:
        ciphertext = await storage.get_object(file_rec.storage_key)
        fk = db.scalar(select(FileKey).where(FileKey.file_id == file_id, FileKey.file_version == file_rec.version))
        if not fk:
            fk = db.scalar(select(FileKey).where(FileKey.file_id == file_id))
        if fk:
            wrapped_dek = base64.b64decode(fk.wrapped_dek)
            nonce = base64.b64decode(fk.nonce)
            unwrapped_dek = km.unwrap_dek(wrapped_dek, fk.key_version, file_id)
            decrypted = decrypt_bytes(ciphertext, unwrapped_dek, nonce, file_id)
        else:
            decrypted = ciphertext
    except Exception:
        settings = get_settings()
        path = settings.RESOLVED_STORAGE_DIR / file_rec.storage_key
        if path.is_file():
            decrypted = path.read_bytes()
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored file content not found")

    file_rec.download_count += 1
    db.commit()

    log_event(
        actor_id=user.id,
        action="file_downloaded",
        resource_type="file",
        resource_id=file_id,
        request=request,
    )

    return Response(
        content=decrypted,
        media_type=file_rec.content_type,
        headers={"Content-Disposition": f'attachment; filename="{file_rec.original_name}"'}
    )

# Backward-compatibility alias for /api/files/upload
router.add_api_route("/upload", upload_file, methods=["POST"], response_model=FileOut, status_code=status.HTTP_201_CREATED)

# Dual-mount v1 routes matching both /api/files and /api/v1/files
v1_router.add_api_route("", list_files, methods=["GET"], response_model=List[FileOut])
v1_router.add_api_route("", upload_file, methods=["POST"], response_model=FileOut, status_code=status.HTTP_201_CREATED)
v1_router.add_api_route("/{file_id}", get_file, methods=["GET"], response_model=FileOut)
v1_router.add_api_route("/{file_id}/metadata", get_file_metadata, methods=["GET"])
v1_router.add_api_route("/{file_id}/download", download_file, methods=["GET"])
v1_router.add_api_route("/{file_id}", update_file, methods=["PATCH"], response_model=FileOut)
v1_router.add_api_route("/{file_id}", delete_file, methods=["DELETE"], status_code=status.HTTP_200_OK)
v1_router.add_api_route("/{file_id}/versions", upload_file_version, methods=["POST"], response_model=FileVersionOut, status_code=status.HTTP_201_CREATED)
v1_router.add_api_route("/{file_id}/versions", list_file_versions, methods=["GET"], response_model=List[FileVersionOut])

