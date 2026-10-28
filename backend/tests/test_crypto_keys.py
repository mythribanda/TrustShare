import base64
import os
import secrets
from datetime import datetime
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.db import SessionLocal, is_db_reachable, Base, engine
from app.core.deps import current_user
from app.core.redis import get_redis
from app.core.security import create_access_token, get_session_key
from app.main import app
from app.models.file import StoredFile
from app.models.file_key import FileKey
from app.models.user import User
from app.services.crypto import DecryptionError, encrypt_bytes, decrypt_bytes, zero_bytearray
from app.services.keys import KeyManager

client = TestClient(app)

@pytest.fixture(autouse=True, scope="session")
def setup_test_db():
    Base.metadata.create_all(bind=engine)

# Helper to generate a valid 32-byte base64-encoded key
def make_b64_key() -> str:
    return base64.b64encode(os.urandom(32)).decode("ascii")

# 1. Encrypt / Decrypt Roundtrip Tests
def test_encrypt_decrypt_roundtrip_empty_and_normal():
    dek = bytearray(secrets.token_bytes(32))
    dek_copy = bytearray(dek)
    file_id = 12345

    # Empty bytes file
    empty_data = b""
    ciphertext, nonce = encrypt_bytes(empty_data, dek, file_id)
    assert len(nonce) == 12
    assert len(ciphertext) == 16  # 16-byte GCM authentication tag
    decrypted = decrypt_bytes(ciphertext, dek_copy, nonce, file_id)
    assert decrypted == empty_data

    # Standard data
    data = b"TrustShare AES-256-GCM test plaintext payload"
    ciphertext, nonce = encrypt_bytes(data, dek_copy, file_id)
    decrypted = decrypt_bytes(ciphertext, dek_copy, nonce, file_id)
    assert decrypted == data

def test_encrypt_decrypt_roundtrip_10mb_file():
    dek = bytearray(secrets.token_bytes(32))
    dek_copy = bytearray(dek)
    file_id = "file-large-10mb"

    # Exactly 10 MiB payload
    large_payload = os.urandom(10 * 1024 * 1024)
    ciphertext, nonce = encrypt_bytes(large_payload, dek, file_id)
    assert len(nonce) == 12
    assert len(ciphertext) == len(large_payload) + 16

    decrypted = decrypt_bytes(ciphertext, dek_copy, nonce, file_id)
    assert decrypted == large_payload

# 2. Tampered & Invalid Inputs Tests
def test_tampered_ciphertext_raises_decryption_error():
    dek = bytearray(secrets.token_bytes(32))
    dek_copy = bytearray(dek)
    file_id = 999
    data = b"Sensitive document content"

    ciphertext, nonce = encrypt_bytes(data, dek, file_id)

    # Flip one byte in ciphertext
    tampered = bytearray(ciphertext)
    tampered[0] ^= 0xFF

    with pytest.raises(DecryptionError):
        decrypt_bytes(bytes(tampered), dek_copy, nonce, file_id)

def test_wrong_nonce_raises_decryption_error():
    dek = bytearray(secrets.token_bytes(32))
    dek_copy = bytearray(dek)
    file_id = 999
    data = b"Sensitive document content"

    ciphertext, nonce = encrypt_bytes(data, dek, file_id)

    # Wrong nonce bytes
    wrong_nonce = bytearray(nonce)
    wrong_nonce[0] ^= 0x01

    with pytest.raises(DecryptionError):
        decrypt_bytes(ciphertext, dek_copy, bytes(wrong_nonce), file_id)

    # Wrong nonce length
    with pytest.raises(DecryptionError):
        decrypt_bytes(ciphertext, dek_copy, nonce[:8], file_id)

def test_wrong_dek_raises_decryption_error():
    dek1 = bytearray(secrets.token_bytes(32))
    dek2 = bytearray(secrets.token_bytes(32))
    file_id = 999
    data = b"Sensitive document content"

    ciphertext, nonce = encrypt_bytes(data, dek1, file_id)

    with pytest.raises(DecryptionError):
        decrypt_bytes(ciphertext, dek2, nonce, file_id)

def test_wrong_file_id_aad_raises_decryption_error():
    dek = bytearray(secrets.token_bytes(32))
    dek_copy = bytearray(dek)
    file_id_correct = 101
    file_id_wrong = 102
    data = b"Bound to file_id 101"

    ciphertext, nonce = encrypt_bytes(data, dek, file_id_correct)

    with pytest.raises(DecryptionError):
        decrypt_bytes(ciphertext, dek_copy, nonce, file_id_wrong)

# 3. Nonce Uniqueness Test
def test_nonces_are_unique_across_1000_encryptions():
    dek = bytearray(secrets.token_bytes(32))
    file_id = "test-uniqueness"
    payload = b"constant content"

    seen_nonces = set()
    for _ in range(1000):
        # Pass copy since encrypt_bytes zeroes bytearray
        _, nonce = encrypt_bytes(payload, bytearray(dek), file_id)
        assert nonce not in seen_nonces, "Collision detected in 96-bit AESGCM nonces!"
        seen_nonces.add(nonce)

    assert len(seen_nonces) == 1000

# 4. KeyManager Wrap / Unwrap Roundtrip & Failures
def test_wrap_unwrap_roundtrip_and_failures():
    k1 = make_b64_key()
    km = KeyManager(kek_keys_raw={"1": k1}, current_version="1")

    dek = km.generate_dek()
    dek_copy = bytearray(dek)
    file_id = 42

    wrapped_blob, ver = km.wrap_dek(dek, file_id)
    assert ver == "1"
    assert len(wrapped_blob) == 12 + 32 + 16  # nonce(12) + dek(32) + tag(16)

    # Unwrap
    unwrapped = km.unwrap_dek(wrapped_blob, ver, file_id)
    assert unwrapped == dek_copy

    # Unwrap with wrong version
    with pytest.raises(DecryptionError):
        km.unwrap_dek(wrapped_blob, "999", file_id)

    # Unwrap with wrong file_id
    with pytest.raises(DecryptionError):
        km.unwrap_dek(wrapped_blob, ver, file_id=999)

    # Tampered wrapped blob
    tampered = bytearray(wrapped_blob)
    tampered[15] ^= 0x42
    with pytest.raises(DecryptionError):
        km.unwrap_dek(bytes(tampered), ver, file_id)

# 5. Startup Validation Failures on Missing/Short/Invalid KEK
def test_keymanager_fails_on_missing_kek():
    with pytest.raises(ValueError, match="KEK_KEYS"):
        KeyManager(kek_keys_raw="")

def test_keymanager_fails_on_short_kek():
    # Only 16 bytes decoded
    short_b64 = base64.b64encode(os.urandom(16)).decode("ascii")
    with pytest.raises(ValueError, match="must decode to exactly 32 bytes"):
        KeyManager(kek_keys_raw={"1": short_b64}, current_version="1")

def test_keymanager_fails_on_invalid_base64_kek():
    with pytest.raises(ValueError, match="not valid base64"):
        KeyManager(kek_keys_raw={"1": "invalid-base64-!!!"}, current_version="1")

def test_keymanager_fails_on_missing_current_version():
    k1 = make_b64_key()
    with pytest.raises(ValueError, match="KEK_CURRENT_VERSION"):
        KeyManager(kek_keys_raw={"1": k1}, current_version="2")

# 6. Rewrap Moves Records and Files Still Decrypt
def test_rewrap_moves_records_and_files_still_decrypt():
    if not is_db_reachable():
        pytest.skip("Database is not reachable; skipping DB-dependent rewrap test.")

    from app.services.keys import _key_manager
    import app.services.keys as keys_module

    k1 = make_b64_key()
    k2 = make_b64_key()

    # Create multi-version KeyManager where version 2 is current
    km = KeyManager(kek_keys_raw={"1": k1, "2": k2}, current_version="2")
    keys_module._key_manager = km

    db = SessionLocal()
    try:
        # Create test user and file
        user = User(
            name="Rewrap Admin",
            email=f"admin.rewrap.{datetime.now().timestamp()}@example.com",
            password_hash="mock",
            role="admin",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        file_rec = StoredFile(
            original_name="rewrap_test.txt",
            storage_key=f"test_rewrap_{secrets.token_hex(8)}.txt",
            content_type="text/plain",
            size=100,
            owner_id=user.id,
            version=1,
        )
        db.add(file_rec)
        db.commit()
        db.refresh(file_rec)

        # Generate a DEK and encrypt test payload
        original_dek = km.generate_dek()
        file_content = b"Content to verify rewrapped decryption"
        ciphertext, nonce = encrypt_bytes(file_content, bytearray(original_dek), file_rec.id)

        # Wrap DEK under old version 1
        km_v1 = KeyManager(kek_keys_raw={"1": k1}, current_version="1")
        wrapped_v1, _ = km_v1.wrap_dek(bytearray(original_dek), file_rec.id)

        file_key_rec = FileKey(
            file_id=file_rec.id,
            wrapped_dek=base64.b64encode(wrapped_v1).decode("ascii"),
            key_version=1,
            nonce=base64.b64encode(nonce).decode("ascii"),
        )
        db.add(file_key_rec)
        db.commit()

        # Execute rewrap endpoint as admin
        admin_token = create_access_token(user.id, "admin")
        cache = get_redis()
        if cache:
            cache.setex(get_session_key(user.id, admin_token), 900, "active")

        resp = client.post(
            "/api/v1/admin/keys/rewrap",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["rewrapped_count"] >= 1

        # Check DB record updated to key_version 2
        db.refresh(file_key_rec)
        assert file_key_rec.key_version == 2

        # Unwrap updated DEK with version 2
        raw_wrapped_v2 = base64.b64decode(file_key_rec.wrapped_dek)
        unwrapped_dek_v2 = km.unwrap_dek(raw_wrapped_v2, file_key_rec.key_version, file_rec.id)
        assert unwrapped_dek_v2 == original_dek

        # Verify file still decrypts cleanly
        decrypted_content = decrypt_bytes(ciphertext, unwrapped_dek_v2, nonce, file_rec.id)
        assert decrypted_content == file_content
    finally:
        db.close()
        # Restore default key manager
        keys_module._key_manager = None

# 7. Non-Admin Gets 403 on Rewrap Test
def test_non_admin_gets_403_on_rewrap():
    if not is_db_reachable():
        pytest.skip("Database is not reachable; skipping DB-dependent rewrap permissions test.")

    db = SessionLocal()
    try:
        user = User(
            name="Regular User",
            email=f"regular.{datetime.now().timestamp()}@example.com",
            password_hash="mock",
            role="user",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        user_token = create_access_token(user.id, "user")
        cache = get_redis()
        if cache:
            cache.setex(get_session_key(user.id, user_token), 900, "active")

        # Regular user attempt
        resp = client.post(
            "/api/v1/admin/keys/rewrap",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 403

        # Unauthenticated attempt
        resp_unauth = client.post("/api/v1/admin/keys/rewrap")
        assert resp_unauth.status_code == 401
    finally:
        db.close()
