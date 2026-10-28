from pathlib import Path
from typing import List, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

KNOWN_INSECURE_SECRETS = {
    "local-only-change-me",
    "change-me",
    "secret",
    "jwt-secret",
    "CHANGE_ME_generate_with_openssl_rand_hex_32",
    "replace-with-a-long-random-secret-before-running",
}

class Settings(BaseSettings):
    APP_ENV: str = "development"
    DATABASE_URL: str
    MONGO_URL: str = "mongodb://localhost:27017"
    MONGO_DB: str = "trustshare"
    REDIS_URL: str = "redis://localhost:6379/0"

    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    MAX_UPLOAD_MB: int = 50
    ALLOWED_EXTENSIONS: str = ".pdf,.docx,.xlsx,.csv,.txt,.png,.jpg,.jpeg,.webp"
    ALLOWED_CONTENT_TYPES: str = "*"
    FRONTEND_ORIGIN: str = "http://localhost:5173"
    STORAGE_DIR: str = ""

    # S3 / MinIO settings
    S3_ENDPOINT_URL: Optional[str] = None
    S3_ACCESS_KEY: Optional[str] = None
    S3_SECRET_KEY: Optional[str] = None
    S3_BUCKET: str = "trustshare"
    S3_REGION: str = "us-east-1"

    # Key Encryption Keys (KEK) envelope settings
    # Test fixture key provided as default (base64 32 bytes)
    KEK_KEYS: str = '{"1":"MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="}'
    KEK_CURRENT_VERSION: str = "1"

    model_config = SettingsConfigDict(
        env_file=(
            Path(__file__).resolve().parent.parent.parent.parent / ".env",
            Path(__file__).resolve().parent.parent.parent / ".env",
            ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("JWT_SECRET")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        val = (v or "").strip()
        if not val:
            raise ValueError("Security violation: JWT_SECRET must not be empty.")
        if len(val) < 32:
            raise ValueError("Security violation: JWT_SECRET must be at least 32 characters long.")
        if val in KNOWN_INSECURE_SECRETS:
            raise ValueError(f"Security violation: JWT_SECRET cannot be a known insecure default '{val}'.")
        return val

    @field_validator("KEK_KEYS")
    @classmethod
    def validate_kek_keys(cls, v: str) -> str:
        val = (v or "").strip()
        if not val:
            raise ValueError("Security violation: KEK_KEYS must not be empty.")
        import json, base64
        try:
            mapping = json.loads(val)
        except Exception as e:
            raise ValueError(f"Security violation: KEK_KEYS must be valid JSON: {e}") from None
        if not isinstance(mapping, dict) or not mapping:
            raise ValueError("Security violation: KEK_KEYS must contain at least one version mapping.")
        for ver, b64_key in mapping.items():
            try:
                decoded = base64.b64decode(b64_key, validate=True)
            except Exception as e:
                raise ValueError(f"Security violation: KEK key '{ver}' is not valid base64: {e}") from None
            if len(decoded) != 32:
                raise ValueError(f"Security violation: KEK key '{ver}' must decode to exactly 32 bytes, got {len(decoded)}.")
        return val


    @property
    def IS_PRODUCTION(self) -> bool:
        return self.APP_ENV.lower() == "production"

    @property
    def MAX_UPLOAD_BYTES(self) -> int:
        return self.MAX_UPLOAD_MB * 1024 * 1024

    @property
    def ALLOWED_EXTENSIONS_SET(self) -> set[str]:
        return {
            ext.strip().lower() if ext.strip().startswith(".") else f".{ext.strip().lower()}"
            for ext in self.ALLOWED_EXTENSIONS.split(",")
            if ext.strip()
        }

    @property
    def ALLOWED_CONTENT_TYPES_SET(self) -> set[str]:
        val = self.ALLOWED_CONTENT_TYPES.strip()
        if not val or val == "*":
            return set()
        return {ct.strip().lower() for ct in val.split(",") if ct.strip()}

    @property
    def FRONTEND_ORIGINS_LIST(self) -> List[str]:
        origins = {self.FRONTEND_ORIGIN, "http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"}
        return list(origins)

    @property
    def RESOLVED_STORAGE_DIR(self) -> Path:
        if self.STORAGE_DIR:
            p = Path(self.STORAGE_DIR)
        elif Path("/app/storage").exists():
            p = Path("/app/storage")
        else:
            proj_storage = Path(__file__).resolve().parent.parent.parent.parent / "storage"
            p = proj_storage if proj_storage.parent.exists() else Path("storage")
        p.mkdir(parents=True, exist_ok=True)
        return p

_settings: Optional[Settings] = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
