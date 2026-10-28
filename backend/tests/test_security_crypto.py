import base64
import os

import pytest
from cryptography.exceptions import InvalidTag

from app.security_crypto import CHUNK_SIZE, decrypt_bytes, encrypt_bytes, rewrap_key

def test_chunked_roundtrip(monkeypatch):
    monkeypatch.delenv("MASTER_KEYS", raising=False)
    monkeypatch.setenv("ACTIVE_MASTER_KEY_VERSION", "1")
    monkeypatch.setenv("ENCRYPTION_MASTER_KEY", base64.b64encode(os.urandom(32)).decode())
    plaintext = (b"TrustShare encrypted payload " * ((CHUNK_SIZE // 29) + 100))[:CHUNK_SIZE + 811]
    blob, wrapped, nonce, version = encrypt_bytes(plaintext, "file-123.bin")
    assert blob != plaintext
    assert plaintext not in blob
    assert decrypt_bytes(blob, "file-123.bin", wrapped, nonce, version) == plaintext

def test_context_binding_rejects_wrong_file_id(monkeypatch):
    monkeypatch.delenv("MASTER_KEYS", raising=False)
    monkeypatch.setenv("ACTIVE_MASTER_KEY_VERSION", "1")
    monkeypatch.setenv("ENCRYPTION_MASTER_KEY", base64.b64encode(os.urandom(32)).decode())
    blob, wrapped, nonce, version = encrypt_bytes(b"private content", "owner-file-a")
    with pytest.raises(InvalidTag):
        decrypt_bytes(blob, "owner-file-b", wrapped, nonce, version)

def test_tampered_ciphertext_is_rejected(monkeypatch):
    monkeypatch.delenv("MASTER_KEYS", raising=False)
    monkeypatch.setenv("ACTIVE_MASTER_KEY_VERSION", "1")
    monkeypatch.setenv("ENCRYPTION_MASTER_KEY", base64.b64encode(os.urandom(32)).decode())
    blob, wrapped, nonce, version = encrypt_bytes(b"sensitive data", "file-x")
    damaged = bytearray(blob)
    damaged[-1] ^= 1
    with pytest.raises(InvalidTag):
        decrypt_bytes(bytes(damaged), "file-x", wrapped, nonce, version)

def test_rewrap_keeps_payload_decryptable_during_key_rotation(monkeypatch):
    old_key = base64.b64encode(os.urandom(32)).decode()
    new_key = base64.b64encode(os.urandom(32)).decode()
    monkeypatch.setenv("MASTER_KEYS", f"1:{old_key},2:{new_key}")
    monkeypatch.setenv("ACTIVE_MASTER_KEY_VERSION", "1")
    plaintext = b"rotation should not require rewriting ciphertext"
    blob, wrapped, nonce, version = encrypt_bytes(plaintext, "file-key-1")
    monkeypatch.setenv("ACTIVE_MASTER_KEY_VERSION", "2")
    wrapped2, nonce2, version2 = rewrap_key(wrapped, nonce, version, "file-key-1")
    assert version2 == 2
    assert decrypt_bytes(blob, "file-key-1", wrapped2, nonce2, version2) == plaintext
