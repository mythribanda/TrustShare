import logging
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.mongo import init_mongo_indexes
from app.api import (
    health_router,
    auth_router,
    files_router,
    v1_files_router,
    folders_router,
    v1_folders_router,
    admin_router,
    v1_admin_router,
)


logger = logging.getLogger("trustshare")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize MongoDB indexes on activity_logs and files
    init_mongo_indexes()
    yield

def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="TrustShare API",
        version="1.0.0",
        description="TrustShare Secure File Management & Sharing API",
        lifespan=lifespan,
    )

    # 1. Request ID Middleware
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        req_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = req_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response

    # 2. Security Headers Middleware
    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"

        if settings.IS_PRODUCTION:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        if request.url.path.startswith("/api"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"

        return response

    # 3. CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.FRONTEND_ORIGINS_LIST,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 4. Include Routers
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(files_router)
    app.include_router(v1_files_router)
    app.include_router(folders_router)
    app.include_router(v1_folders_router)
    app.include_router(admin_router)
    app.include_router(v1_admin_router)

    return app

app = create_app()
