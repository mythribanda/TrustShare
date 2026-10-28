import io
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from jose import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.db import Base
from app.core.deps import get_db
from app.core.security import create_access_token, generate_refresh_token, hash_token
from app.main import app
from app.models.user import User
from app.models.file import StoredFile
from app.models.refresh_token import RefreshToken
from app.services.audit import log_event

client = TestClient(app)

@pytest.fixture(autouse=True, scope="session")
def setup_test_db():
    from app.core.db import engine
    Base.metadata.create_all(bind=engine)


# 1. Subprocess Fail-Fast Test
def test_startup_fails_with_weak_jwt_secret():
    """Verify backend fails fast in any environment when JWT_SECRET is weak or default."""
    test_script = """
import os
os.environ['JWT_SECRET'] = 'weak-secret'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
from app.core.config import Settings
Settings()
"""
    result = subprocess.run(
        [sys.executable, "-c", test_script],
        cwd=os.path.join(os.path.dirname(__file__), ".."),
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, "Settings must fail fast with weak JWT_SECRET"
    assert "Security violation: JWT_SECRET" in result.stderr

def test_startup_fails_with_known_default_jwt_secret():
    """Verify backend fails fast when JWT_SECRET is a known placeholder default."""
    test_script = """
import os
os.environ['JWT_SECRET'] = 'replace-with-a-long-random-secret-before-running'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
from app.core.config import Settings
Settings()
"""
    result = subprocess.run(
        [sys.executable, "-c", test_script],
        cwd=os.path.join(os.path.dirname(__file__), ".."),
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, "Settings must fail fast with placeholder JWT_SECRET"
    assert "Security violation" in result.stderr

# 2. Access Token TTL Test
def test_access_token_lifetime_is_15_minutes():
    """Verify access token lifetime is exactly 15 minutes (900 seconds)."""
    settings = get_settings()
    token = create_access_token(user_id=123, role="user")
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    ttl_seconds = payload["exp"] - payload["iat"]
    assert ttl_seconds == 15 * 60, f"Expected 900 seconds (15m), got {ttl_seconds}"

# 3. Security Headers and Request-ID Test
def test_security_headers_and_request_id():
    """Verify security headers and request-ID propagation on API responses."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert "X-Request-ID" in resp.headers
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Referrer-Policy"] == "no-referrer"

    # API routes must include Cache-Control no-store and CSP
    resp_api = client.get("/api/auth/me")
    assert "X-Request-ID" in resp_api.headers
    assert resp_api.headers["Cache-Control"] == "no-store"
    assert "default-src 'none'" in resp_api.headers["Content-Security-Policy"]

# 4. Alembic Migration Test
def test_alembic_upgrade_creates_all_seven_tables():
    """Verify alembic upgrade head on an empty DB creates all 7 specified tables."""
    db_file = os.path.abspath("test_foundation_alembic.db")
    if os.path.exists(db_file):
        os.remove(db_file)

    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_file}"
    cmd = [sys.executable, "-m", "alembic", "upgrade", "head"]
    res = subprocess.run(cmd, cwd=os.path.join(os.path.dirname(__file__), ".."), capture_output=True, text=True, env=env)
    assert res.returncode == 0, f"Alembic upgrade failed: {res.stderr}\n{res.stdout}"

    eng = create_engine(f"sqlite:///{db_file}")
    inspector = inspect(eng)
    tables = set(inspector.get_table_names())
    expected = {"users", "folders", "files", "refresh_tokens", "file_keys", "permissions", "share_links"}
    missing = expected - tables
    eng.dispose()

    if os.path.exists(db_file):
        os.remove(db_file)

    assert not missing, f"Alembic migration failed to create expected tables: {missing}"

# 5. Refresh Happy Path & Rotation Test
def test_refresh_happy_path():
    """Verify login issues httpOnly cookie and POST /api/auth/refresh rotates the token."""
    email = f"refresh.test.{datetime.now().timestamp()}@example.com"
    reg_resp = client.post("/api/auth/register", json={
        "name": "Refresh Tester",
        "email": email,
        "password": "Password123!"
    })
    assert reg_resp.status_code == 201
    assert "refresh_token" in reg_resp.cookies
    token1 = reg_resp.cookies["refresh_token"]

    # Call refresh endpoint with cookie
    ref_resp = client.post("/api/auth/refresh", cookies={"refresh_token": token1})
    assert ref_resp.status_code == 200
    ref_json = ref_resp.json()
    assert "access_token" in ref_json
    assert "refresh_token" in ref_resp.cookies
    token2 = ref_resp.cookies["refresh_token"]
    assert token1 != token2, "Refresh token must rotate upon usage"

# 6. Refresh Reuse Revocation Test
def test_refresh_reuse_revokes_family():
    """Verify reusing an already-rotated refresh token revokes the entire token family."""
    email = f"reuse.test.{datetime.now().timestamp()}@example.com"
    reg_resp = client.post("/api/auth/register", json={
        "name": "Reuse Tester",
        "email": email,
        "password": "Password123!"
    })
    assert reg_resp.status_code == 201
    token1 = reg_resp.cookies["refresh_token"]

    # Rotate token1 -> produces token2
    ref1 = client.post("/api/auth/refresh", cookies={"refresh_token": token1})
    assert ref1.status_code == 200
    token2 = ref1.cookies["refresh_token"]

    # Replay token1 (already rotated)
    reuse_resp = client.post("/api/auth/refresh", cookies={"refresh_token": token1})
    assert reuse_resp.status_code == 401
    assert "reuse detected" in reuse_resp.json()["detail"].lower()

    # Now attempt to use token2 -> must be rejected because entire family was revoked
    subsequent_resp = client.post("/api/auth/refresh", cookies={"refresh_token": token2})
    assert subsequent_resp.status_code == 401

# 7. Expired Refresh Token Rejection Test
def test_expired_refresh_rejected():
    """Verify that an expired refresh token returns HTTP 401."""
    from app.core.db import SessionLocal
    db = SessionLocal()
    try:
        # Create a user and manually inject an expired refresh token
        user = User(
            name="Expired Tester",
            email=f"expired.{datetime.now().timestamp()}@example.com",
            password_hash="mockhash",
            role="user"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        raw_expired = generate_refresh_token()
        expired_rec = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw_expired),
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        db.add(expired_rec)
        db.commit()

        resp = client.post("/api/auth/refresh", cookies={"refresh_token": raw_expired})
        assert resp.status_code == 401
        assert "expired" in resp.json()["detail"].lower()
    finally:
        db.close()

# 8. Cross-User File Access Returns 404 Test
def test_cross_user_file_access_returns_404():
    """Verify authz hygiene: cross-user file metadata, download, and delete return 404."""
    user_a_email = f"usera.{datetime.now().timestamp()}@example.com"
    user_b_email = f"userb.{datetime.now().timestamp()}@example.com"

    reg_a = client.post("/api/auth/register", json={"name": "User A", "email": user_a_email, "password": "Password123!"})
    token_a = reg_a.json()["access_token"]

    reg_b = client.post("/api/auth/register", json={"name": "User B", "email": user_b_email, "password": "Password123!"})
    token_b = reg_b.json()["access_token"]

    # Upload file as User A
    up = client.post(
        "/api/files/upload",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"file": ("secret.txt", io.BytesIO(b"Confidential user A data"), "text/plain")},
    )
    assert up.status_code == 201
    file_id = up.json()["id"]

    # User B attempts to access User A's file
    auth_b = {"Authorization": f"Bearer {token_b}"}
    assert client.get(f"/api/files/{file_id}/metadata", headers=auth_b).status_code == 404
    assert client.get(f"/api/files/{file_id}/download", headers=auth_b).status_code == 404
    assert client.delete(f"/api/files/{file_id}", headers=auth_b).status_code == 404

# 9. No storage_key Exposed in API Responses Test
def test_responses_never_contain_storage_key():
    """Verify that storage_key is never exposed in upload, list, or metadata responses."""
    email = f"keytest.{datetime.now().timestamp()}@example.com"
    reg = client.post("/api/auth/register", json={"name": "Key Tester", "email": email, "password": "Password123!"})
    token = reg.json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    # Upload
    up = client.post(
        "/api/files/upload",
        headers=auth,
        files={"file": ("safe.txt", io.BytesIO(b"Safe content"), "text/plain")},
    )
    assert up.status_code == 201
    assert "storage_key" not in up.json()
    assert "storage_key" not in up.text
    file_id = up.json()["id"]

    # List
    ls = client.get("/api/files", headers=auth)
    assert ls.status_code == 200
    assert "storage_key" not in ls.text

    # Metadata
    meta = client.get(f"/api/files/{file_id}/metadata", headers=auth)
    assert meta.status_code == 200
    assert "storage_key" not in meta.json().get("metadata", {})
    assert "storage_key" not in meta.text

# 10. Audit Events Land in activity_logs Test
def test_audit_events_land_in_activity_logs():
    """Verify audit.log_event writes structured events to MongoDB activity_logs."""
    from app.core.mongo import get_mongo_db, is_mongo_available
    if not is_mongo_available():
        pytest.skip("MongoDB is not available in local environment")

    db = get_mongo_db()
    if db is None:
        pytest.skip("MongoDB database not connected")

    log_event(
        actor_id=777,
        action="spec_test_action",
        resource_type="document",
        resource_id="doc-999",
        metadata={"verified": True},
    )

    doc = db["activity_logs"].find_one({"action": "spec_test_action", "actor_id": 777})
    assert doc is not None
    assert doc["resource_type"] == "document"
    assert doc["resource_id"] == "doc-999"
    assert "created_at" in doc
