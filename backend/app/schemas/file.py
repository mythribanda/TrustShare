from typing import Optional, Any, Dict
from pydantic import BaseModel, Field

class FolderIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    parent_id: Optional[int] = None

class FolderUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    parent_id: Optional[int] = None

class FolderOut(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None
    created_at: Optional[str] = None

class FileOut(BaseModel):
    id: int
    name: str
    content_type: str
    size: int
    sha256: Optional[str] = None
    owner_id: int
    folder_id: Optional[int] = None
    category: Optional[str] = None
    status: str = "ready"
    version: int = 1
    meta_synced: bool = True
    uploaded_at: Optional[str] = None

class FileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    folder_id: Optional[int] = None
    category: Optional[str] = Field(None, max_length=64)

class FileVersionOut(BaseModel):
    version: int
    size: int
    sha256: Optional[str] = None
    created_at: Optional[str] = None

class FileMetadataOut(BaseModel):
    source: str
    synced: bool
    metadata: Dict[str, Any]
