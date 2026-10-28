from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.files import router as files_router, v1_router as v1_files_router
from app.api.folders import router as folders_router, v1_router as v1_folders_router
from app.api.admin import router as admin_router, v1_admin_router

__all__ = [
    "health_router",
    "auth_router",
    "files_router",
    "v1_files_router",
    "folders_router",
    "v1_folders_router",
    "admin_router",
    "v1_admin_router",
]


