import logging
from typing import Optional, Any
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError, EndpointConnectionError, ConnectTimeoutError
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings

logger = logging.getLogger("trustshare.storage")

_DEFAULT = object()

class StorageService:
    def __init__(
        self,
        endpoint_url: Any = _DEFAULT,
        bucket: Any = _DEFAULT,
        access_key: Any = _DEFAULT,
        secret_key: Any = _DEFAULT,
        region: Any = _DEFAULT,
    ):
        settings = get_settings()
        self.endpoint_url = settings.S3_ENDPOINT_URL if endpoint_url is _DEFAULT else endpoint_url
        self.bucket = settings.S3_BUCKET if bucket is _DEFAULT else bucket
        self.access_key = settings.S3_ACCESS_KEY if access_key is _DEFAULT else access_key
        self.secret_key = settings.S3_SECRET_KEY if secret_key is _DEFAULT else secret_key
        self.region = settings.S3_REGION if region is _DEFAULT else region

        self._client = None

    @property
    def client(self):
        if self._client is None:
            kwargs = {
                "service_name": "s3",
                "endpoint_url": self.endpoint_url,
                "aws_access_key_id": self.access_key or "minioadmin",
                "aws_secret_access_key": self.secret_key or "minioadmin",
                "region_name": self.region or "us-east-1",
                "config": Config(
                    signature_version="s3v4",
                    s3={"addressing_style": "path"},
                    connect_timeout=3,
                    read_timeout=5,
                    retries={"max_attempts": 1},
                ),
            }
            self._client = boto3.client(**kwargs)
        return self._client

    def _ensure_bucket_exists_sync(self) -> None:
        """Create bucket on startup if missing (dev). Never make objects public."""
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError as e:
            error_code = str(e.response.get("Error", {}).get("Code", ""))
            if error_code in ("404", "NoSuchBucket"):
                try:
                    if self.region and self.region != "us-east-1":
                        self.client.create_bucket(
                            Bucket=self.bucket,
                            CreateBucketConfiguration={"LocationConstraint": self.region},
                        )
                    else:
                        self.client.create_bucket(Bucket=self.bucket)
                    logger.info(f"Created S3 bucket '{self.bucket}' in region '{self.region}'")
                except Exception as create_exc:
                    logger.warning(f"Failed to create S3 bucket '{self.bucket}': {create_exc}")
            else:
                logger.warning(f"head_bucket failed for '{self.bucket}': {e}")
        except Exception as e:
            logger.warning(f"Could not verify S3 bucket '{self.bucket}': {e}")

    async def ensure_bucket_exists(self) -> None:
        await run_in_threadpool(self._ensure_bucket_exists_sync)

    def _put_object_sync(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        # Never make objects public (no public ACL)
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
        except (EndpointConnectionError, ConnectTimeoutError) as exc:
            settings = get_settings()
            if settings.IS_PRODUCTION:
                raise
            logger.warning(f"S3 endpoint unreachable ({exc}); falling back to local storage for dev/testing.")
            local_path = settings.RESOLVED_STORAGE_DIR / key
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(data)

    async def put_object(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        await run_in_threadpool(self._put_object_sync, key, data, content_type)

    def _get_object_sync(self, key: str) -> bytes:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()
        except (EndpointConnectionError, ConnectTimeoutError) as exc:
            settings = get_settings()
            local_path = settings.RESOLVED_STORAGE_DIR / key
            if local_path.is_file():
                return local_path.read_bytes()
            raise

    async def get_object(self, key: str) -> bytes:
        return await run_in_threadpool(self._get_object_sync, key)

    def _delete_object_sync(self, key: str) -> None:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except (EndpointConnectionError, ConnectTimeoutError):
            settings = get_settings()
            local_path = settings.RESOLVED_STORAGE_DIR / key
            if local_path.exists():
                local_path.unlink()

    async def delete_object(self, key: str) -> None:
        await run_in_threadpool(self._delete_object_sync, key)



_storage_service: Optional[StorageService] = None

def get_storage() -> StorageService:
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
