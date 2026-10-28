import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_db, current_user
from app.models.user import User
from app.models.folder import Folder
from app.schemas.file import FolderIn, FolderOut, FolderUpdate
from app.services.audit import log_event

logger = logging.getLogger("trustshare.api.folders")
router = APIRouter(prefix="/api/folders", tags=["folders"])
v1_router = APIRouter(prefix="/api/v1/folders", tags=["folders-v1"])

def folder_dict(f: Folder) -> dict:
    return {
        "id": f.id,
        "name": f.name,
        "parent_id": f.parent_id,
        "created_at": f.created_at.isoformat() if f.created_at else None,
    }

@router.get("", response_model=List[FolderOut])
def list_folders(user: User = Depends(current_user), db: Session = Depends(get_db)):
    items = db.scalars(
        select(Folder)
        .where(Folder.owner_id == user.id)
        .order_by(Folder.name)
    ).all()
    return [folder_dict(f) for f in items]

@router.post("", response_model=FolderOut, status_code=status.HTTP_201_CREATED)
def create_folder(
    data: FolderIn,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Folder name is required")

    parent_id = data.parent_id
    if parent_id is not None:
        parent = db.scalar(select(Folder).where(Folder.id == parent_id, Folder.owner_id == user.id))
        if not parent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent folder not found")

    folder = Folder(name=name, owner_id=user.id, parent_id=parent_id)
    db.add(folder)
    db.commit()
    db.refresh(folder)

    log_event(
        actor_id=user.id,
        action="folder_created",
        resource_type="folder",
        resource_id=folder.id,
        request=request,
        metadata={"name": name, "parent_id": parent_id},
    )

    return folder_dict(folder)

@router.patch("/{folder_id}", response_model=FolderOut)
def update_folder(
    folder_id: int,
    data: FolderUpdate,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    folder = db.scalar(select(Folder).where(Folder.id == folder_id, Folder.owner_id == user.id))
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")

    if data.name is not None:
        name = data.name.strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Folder name cannot be empty")
        folder.name = name

    if data.parent_id is not None:
        if data.parent_id == folder.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cycle detected: folder cannot be its own parent")

        target_parent = db.scalar(select(Folder).where(Folder.id == data.parent_id, Folder.owner_id == user.id))
        if not target_parent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target parent folder not found")

        # Cycle detection: traverse ancestors of target parent
        curr = target_parent
        while curr:
            if curr.id == folder.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cycle detected in folder hierarchy")
            if curr.parent_id is None:
                break
            curr = db.scalar(select(Folder).where(Folder.id == curr.parent_id, Folder.owner_id == user.id))

        folder.parent_id = data.parent_id

    db.commit()
    db.refresh(folder)

    log_event(
        actor_id=user.id,
        action="folder_updated",
        resource_type="folder",
        resource_id=folder.id,
        request=request,
        metadata={"name": folder.name, "parent_id": folder.parent_id},
    )

    return folder_dict(folder)

@router.delete("/{folder_id}", status_code=status.HTTP_200_OK)
def delete_folder(
    folder_id: int,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    folder = db.scalar(select(Folder).where(Folder.id == folder_id, Folder.owner_id == user.id))
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")

    db.delete(folder)
    db.commit()

    log_event(
        actor_id=user.id,
        action="folder_deleted",
        resource_type="folder",
        resource_id=folder_id,
        request=request,
    )

    return {"message": "Folder deleted"}

# Register routes on v1_router
v1_router.add_api_route("", list_folders, methods=["GET"], response_model=List[FolderOut])
v1_router.add_api_route("", create_folder, methods=["POST"], response_model=FolderOut, status_code=status.HTTP_201_CREATED)
v1_router.add_api_route("/{folder_id}", update_folder, methods=["PATCH"], response_model=FolderOut)
v1_router.add_api_route("/{folder_id}", delete_folder, methods=["DELETE"], status_code=status.HTTP_200_OK)
