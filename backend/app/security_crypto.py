import base64
import json
import os
import secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"TSENC1"

def _master_key():
    value = os.getenv("ENCRYPTION_MASTER_KEY", "")
    try:
        key = base64.b64decode(value, validate=True)
    except Exception as exc:
        raise RuntimeError("ENCRYPTION_MASTER_KEY must be base64 for a 32-byte key") from exc
    if len(key) != 32:
        raise RuntimeError("ENCRYPTION_MASTER_KEY must decode to exactly 32 bytes")
    return key

def encrypt_bytes(plaintext: bytes, file_id: str) -> bytes:
    data_key = AESGCM.generate_key(bit_length=256)
    data_nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(data_key).encrypt(data_nonce, plaintext, file_id.encode())
    wrap_nonce = secrets.token_bytes(12)
    wrapped_key = AESGCM(_master_key()).encrypt(wrap_nonce, data_key, file_id.encode())
    header = json.dumps({"id": file_id, "nonce": base64.b64encode(data_nonce).decode(),
        "wrap_nonce": base64.b64encode(wrap_nonce).decode(),
        "wrapped_key": base64.b64encode(wrapped_key).decode()}, separators=(",", ":")).encode()
    return MAGIC + len(header).to_bytes(4, "big") + header + ciphertext

def decrypt_bytes(blob: bytes, file_id: str) -> bytes:
    if not blob.startswith(MAGIC) or len(blob) < 10:
        raise ValueError("Stored object is not an encrypted TrustShare file")
    size = int.from_bytes(blob[6:10], "big")
    header = json.loads(blob[10:10 + size])
    if header.get("id") != file_id:
        raise ValueError("Encrypted file identifier mismatch")
    decode = lambda key: base64.b64decode(header[key])
    data_key = AESGCM(_master_key()).decrypt(decode("wrap_nonce"), decode("wrapped_key"), file_id.encode())
    return AESGCM(data_key).decrypt(decode("nonce"), blob[10 + size:], file_id.encode())
