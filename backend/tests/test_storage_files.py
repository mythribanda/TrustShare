import base64
import io
import os
import secrets
import boto3
import pytest
from moto import mock_aws
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.core.config import get_settings
from app.core.db import SessionLocal, Base, engine, is_db_reachable
from app.core.redis import get_redis
from app.core.security import create_access_token, get_session_key
from app.models.user import User
from app.models.folder import Folder
from app.models.file import StoredFile
from app.models.file_key import FileKey
from app.models.version import FileVersion
from app.services.crypto import decrypt_bytes
from app.services.keys import get_key_manager
from app.services.storage import StorageService
import app.services.storage as storage_module

client = TestClient(app)

@pytest.fixture(autouse=True, scope="session")
def setup_test_db():
    Base.metadata.create_all(bind=engine)

@pytest.fixture(autouse=True)
def s3_moto_setup(monkeypatch):
    """Setup mock AWS S3 with an initialized trustshare bucket."""
    with mock_aws():
        settings = get_settings()
        old_endpoint = settings.S3_ENDPOINT_URL
        settings.S3_ENDPOINT_URL = None

        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="trustshare")

        st = StorageService(endpoint_url=None, bucket="trustshare", region="us-east-1")
        storage_module._storage_service = st
        yield st
        storage_module._storage_service = None
        settings.S3_ENDPOINT_URL = old_endpoint


def create_test_user(db, prefix="user", role="user"):
    user = User(
        name=f"Test {prefix}",
        email=f"{prefix}.{secrets.token_hex(4)}@example.com",
        password_hash="mock_hash",
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, role)
    cache = get_redis()
    if cache:
        cache.setex(get_session_key(user.id, token), 900, "active")
    return user, token

# 1. Upload stores ciphertext in S3 that differs from and does not contain plaintext
def test_upload_stores_ciphertext_differing_from_plaintext(s3_moto_setup):
    if not is_db_reachable():
        pytest.skip("Database is not reachable")

    db = SessionLocal()
    try:
        user, token = create_test_user(db, "crypto_check")
        plaintext = b"Sensitive confidential financial document payload 123456"

        resp = client.post(
            "/api/v1/files",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("report.txt", io.BytesIO(plaintext), "text/plain")},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        file_id = data["id"]

        # Check DB record
        file_rec = db.scalar(select(StoredFile).where(StoredFile.id == file_id))
        s3_key = file_rec.storage_key
        assert s3_key == f"files/{user.id}/{file_id}/v1"

        # Check S3 object directly
        s3_client = boto3.client("s3", region_name="us-east-1")
        s3_obj = s3_client.get_object(Bucket="trustshare", Key=s3_key)
        ciphertext = s3_obj["Body"].read()

        # Ciphertext must differ from and NOT contain plaintext
        assert ciphertext != plaintext
        assert plaintext not in ciphertext

        # Verify decryption using DB wrapped DEK works
        km = get_key_manager()
        fk = db.scalar(select(FileKey).where(FileKey.file_id == file_id))
        wrapped_dek = base64.b64decode(fk.wrapped_dek)
        nonce = base64.b64decode(fk.nonce)
        unwrapped_dek = km.unwrap_dek(wrapped_dek, fk.key_version, file_id)

        decrypted = decrypt_bytes(ciphertext, unwrapped_dek, nonce, file_id)
        assert decrypted == plaintext
    finally:
        db.close()

# 2. DB has no plaintext key; file_keys row exists with key_version = current
def test_db_has_no_plaintext_key_and_file_keys_has_current_version(s3_moto_setup):
    if not is_db_reachable():
        pytest.skip("Database is not reachable")

    db = SessionLocal()
    try:
        user, token = create_test_user(db, "key_check")
        plaintext = b"Check no plaintext DEK stored in DB"

        resp = client.post(
            "/api/v1/files",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("data.txt", io.BytesIO(plaintext), "text/plain")},
        )
        assert resp.status_code == 201
        data = resp.json()
        file_id = data["id"]

        # Never exposed in API response
        assert "storage_key" not in data
        assert "stored_name" not in data
        assert "wrapped_dek" not in data
        assert "nonce" not in data

        # Check file_keys row
        km = get_key_manager()
        fk = db.scalar(select(FileKey).where(FileKey.file_id == file_id))
        assert fk is not None
        assert str(fk.key_version) == str(km.current_version)

        # Ensure wrapped_dek in DB is not plaintext (length is 12 nonce + 32 dek + 16 tag = 60 bytes raw)
        raw_wrapped = base64.b64decode(fk.wrapped_dek)
        assert len(raw_wrapped) == 60
    finally:
        db.close()

# 3. Oversize and disallowed type rejected; filename path traversal sanitized
def test_oversize_and_disallowed_type_rejected_and_path_sanitized(s3_moto_setup):
    if not is_db_reachable():
        pytest.skip("Database is not reachable")

    db = SessionLocal()
    try:
        user, token = create_test_user(db, "validation_user")

        # Disallowed extension
        resp_disallowed = client.post(
            "/api/v1/files",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("malware.exe", io.BytesIO(b"binary"), "application/octet-stream")},
        )
        assert resp_disallowed.status_code == 415

        # Path traversal sanitized
        traversal_name = "../../etc/passwd.txt"
        resp_traversal = client.post(
            "/api/v1/files",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": (traversal_name, io.BytesIO(b"safe content"), "text/plain")},
        )
        assert resp_traversal.status_code == 201
        data_traversal = resp_traversal.json()
        assert data_traversal["name"] == "passwd.txt"
        assert "/" not in data_traversal["name"]
        assert "\\" not in data_traversal["name"]

        # Oversize rejected while streaming
        settings = get_settings()
        old_limit = settings.MAX_UPLOAD_MB
        try:
            settings.MAX_UPLOAD_MB = 1  # 1 MiB
            oversize_payload = os.urandom(2 * 1024 * 1024)  # 2 MiB
            resp_oversize = client.post(
                "/api/v1/files",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": ("large.txt", io.BytesIO(oversize_payload), "text/plain")},
            )
            assert resp_oversize.status_code == 413
        finally:
            settings.MAX_UPLOAD_MB = old_limit
    finally:
        db.close()

# 4. Failed storage write leaves no ready row
def test_failed_storage_write_leaves_no_ready_row(s3_moto_setup, monkeypatch):
    if not is_db_reachable():
        pytest.skip("Database is not reachable")

    db = SessionLocal()
    try:
        user, token = create_test_user(db, "failure_user")

        # Mock put_object to simulate storage write failure
        async def failing_put_object(*args, **kwargs):
            raise RuntimeError("Simulated S3 connection dropout")

        monkeypatch.setattr(storage_module._storage_service, "put_object", failing_put_object)

        with pytest.raises(RuntimeError, match="Simulated S3 connection dropout"):
            client.post(
                "/api/v1/files",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": ("failed.txt", io.BytesIO(b"will fail to store"), "text/plain")},
            )

        # Inspect database: no row with status='ready' exists for this file
        file_rec = db.scalar(
            select(StoredFile).where(
                StoredFile.owner_id == user.id,
                StoredFile.original_name == "failed.txt"
            )
        )
        if file_rec is not None:
            assert file_rec.status == "deleted"
            assert file_rec.deleted_at is not None

        # Verify no orphaned file_keys row
        if file_rec is not None:
            fk = db.scalar(select(FileKey).where(FileKey.file_id == file_rec.id))
            assert fk is None
    finally:
        db.close()

# 5. User B gets 404 on User A's file; list only shows own files
def test_user_b_gets_404_on_user_a_file_and_list_only_shows_own(s3_moto_setup):
    if not is_db_reachable():
        pytest.skip("Database is not reachable")

    db = SessionLocal()
    try:
        user_a, token_a = create_test_user(db, "user_a")
        user_b, token_b = create_test_user(db, "user_b")

        # User A uploads a file
        resp_a = client.post(
            "/api/v1/files",
            headers={"Authorization": f"Bearer {token_a}"},
            files={"file": ("private_a.txt", io.BytesIO(b"User A Private File"), "text/plain")},
        )
        assert resp_a.status_code == 201
        file_a_id = resp_a.json()["id"]

        # User B requests User A's file metadata: MUST RETURN 404, NOT 403
        resp_b_get = client.get(
            f"/api/v1/files/{file_a_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp_b_get.status_code == 404

        # User B requests file list: User A's file must not appear
        resp_b_list = client.get(
            "/api/v1/files",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp_b_list.status_code == 200
        b_files = resp_b_list.json()
        assert not any(f["id"] == file_a_id for f in b_files)
    finally:
        db.close()

# 6. Delete removes S3 object and key row
def test_delete_removes_s3_object_and_key_row(s3_moto_setup):
    if not is_db_reachable():
        pytest.skip("Database is not reachable")

    db = SessionLocal()
    try:
        user, token = create_test_user(db, "delete_user")

        resp = client.post(
            "/api/v1/files",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("to_delete.txt", io.BytesIO(b"File to be deleted"), "text/plain")},
        )
        assert resp.status_code == 201
        file_id = resp.json()["id"]

        file_rec = db.scalar(select(StoredFile).where(StoredFile.id == file_id))
        s3_key = file_rec.storage_key

        s3_client = boto3.client("s3", region_name="us-east-1")
        # S3 object exists prior to delete
        s3_client.head_object(Bucket="trustshare", Key=s3_key)

        # Delete file
        del_resp = client.delete(
            f"/api/v1/files/{file_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert del_resp.status_code == 200

        # S3 object is removed
        with pytest.raises(Exception):
            s3_client.head_object(Bucket="trustshare", Key=s3_key)

        # file_keys row is deleted
        fk = db.scalar(select(FileKey).where(FileKey.file_id == file_id))
        assert fk is None

        # Subsequent GET returns 404
        get_resp = client.get(
            f"/api/v1/files/{file_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_resp.status_code == 404
    finally:
        db.close()

# 7. Folder cycle rejected; versions create distinct keys and S3 objects
def test_folder_cycle_rejected(s3_moto_setup):
    if not is_db_reachable():
        pytest.skip("Database is not reachable")

    db = SessionLocal()
    try:
        user, token = create_test_user(db, "folder_user")

        # Create Folder A
        resp_a = client.post(
            "/api/v1/folders",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Folder A"},
        )
        assert resp_a.status_code == 201
        folder_a_id = resp_a.json()["id"]

        # Create Folder B with parent A
        resp_b = client.post(
            "/api/v1/folders",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Folder B", "parent_id": folder_a_id},
        )
        assert resp_b.status_code == 201
        folder_b_id = resp_b.json()["id"]

        # Attempt to make Folder A's parent Folder B (cycle A -> B -> A)
        resp_cycle = client.patch(
            f"/api/v1/folders/{folder_a_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"parent_id": folder_b_id},
        )
        assert resp_cycle.status_code == 400
        assert "Cycle detected" in resp_cycle.json()["detail"]

        # Attempt to make Folder A its own parent (A -> A)
        resp_self = client.patch(
            f"/api/v1/folders/{folder_a_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"parent_id": folder_a_id},
        )
        assert resp_self.status_code == 400
        assert "Cycle detected" in resp_self.json()["detail"]
    finally:
        db.close()

def test_versions_create_distinct_keys_and_s3_objects(s3_moto_setup):
    if not is_db_reachable():
        pytest.skip("Database is not reachable")

    db = SessionLocal()
    try:
        user, token = create_test_user(db, "version_user")

        # Version 1 upload
        resp_v1 = client.post(
            "/api/v1/files",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("doc.txt", io.BytesIO(b"Version 1 text"), "text/plain")},
        )
        assert resp_v1.status_code == 201
        file_id = resp_v1.json()["id"]

        # Version 2 upload
        resp_v2 = client.post(
            f"/api/v1/files/{file_id}/versions",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("doc.txt", io.BytesIO(b"Version 2 updated text"), "text/plain")},
        )
        assert resp_v2.status_code == 201
        assert resp_v2.json()["version"] == 2

        # Check S3: both objects exist
        s3_client = boto3.client("s3", region_name="us-east-1")
        k1 = f"files/{user.id}/{file_id}/v1"
        k2 = f"files/{user.id}/{file_id}/v2"
        obj1 = s3_client.get_object(Bucket="trustshare", Key=k1)
        obj2 = s3_client.get_object(Bucket="trustshare", Key=k2)
        assert obj1["Body"].read() != obj2["Body"].read()

        # Check file_keys: 2 distinct rows
        keys = db.scalars(
            select(FileKey).where(FileKey.file_id == file_id)
        ).all()
        assert len(keys) == 2
        # Different wrapped DEKs
        assert keys[0].wrapped_dek != keys[1].wrapped_dek

        # List versions endpoint
        list_v_resp = client.get(
            f"/api/v1/files/{file_id}/versions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_v_resp.status_code == 200
        versions_list = list_v_resp.json()
        assert len(versions_list) == 2
        assert versions_list[0]["version"] == 1
        assert versions_list[1]["version"] == 2
    finally:
        db.close()
