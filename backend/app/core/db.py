import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import get_settings

logger = logging.getLogger("trustshare.db")

class Base(DeclarativeBase):
    pass

def init_engine():
    settings = get_settings()
    url = settings.DATABASE_URL
    if url.startswith("postgresql+psycopg://"):
        try:
            import psycopg
        except ImportError:
            url = url.replace("postgresql+psycopg://", "postgresql+psycopg2://", 1)
    
    try:
        connect_args = {"connect_timeout": 5} if "postgres" in url else {}
        eng = create_engine(url, pool_pre_ping=True, connect_args=connect_args)
        with eng.connect():
            pass
        return eng, "postgres"
    except Exception as exc:
        if settings.IS_PRODUCTION:
            logger.error(f"Production database connection failed ({url}): {exc}")
            raise RuntimeError(f"Database connection failed in production mode: {exc}")
        logger.warning(f"PostgreSQL ({url}) not reachable: {exc}")
        sqlite_file = (settings.RESOLVED_STORAGE_DIR / "trustshare.db").resolve()
        logger.info(f"Using SQLite fallback at: {sqlite_file}")
        eng = create_engine(
            f"sqlite:///{sqlite_file}",
            connect_args={"check_same_thread": False, "timeout": 10}
        )
        return eng, "sqlite_fallback"

engine, db_backend = init_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def is_db_reachable() -> bool:
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning(f"Database reachability check failed: {exc}")
        return False

