import os
from typing import Tuple, Union
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class DecryptionError(Exception):
    """Raised when AES-256-GCM decryption fails. No internal details leaked."""
    pass

def zero_bytearray(b: Union[bytearray, memoryview]) -> None:
    """Best-effort in-place zeroing of sensitive key material."""
    if isinstance(b, (bytearray, memoryview)):
        for i in range(len(b)):
            b[i] = 0

def _normalize_aad(file_id: Union[int, str, bytes]) -> bytes:
    if isinstance(file_id, bytes):
        return file_id
    return str(file_id).encode("utf-8")

def encrypt_bytes(
    plaintext: bytes,
    dek: Union[bytes, bytearray],
    file_id: Union[int, str, bytes],
) -> Tuple[bytes, bytes]:
    """
    Encrypt plaintext bytes using AES-256-GCM.
    - Generates a fresh random 96-bit (12-byte) nonce per encryption.
    - Binds Additional Authenticated Data (AAD) to file_id.
    - Returns (ciphertext_with_tag, nonce).
    """
    if len(dek) != 32:
        raise ValueError("DEK must be exactly 32 bytes (256 bits)")

    nonce = os.urandom(12)
    aad = _normalize_aad(file_id)

    dek_bytes = bytes(dek)
    try:
        aesgcm = AESGCM(dek_bytes)
        ciphertext = aesgcm.encrypt(nonce, plaintext, aad)
        return ciphertext, nonce
    finally:
        # Zero temporary copy if dek was bytearray
        if isinstance(dek, bytearray):
            zero_bytearray(dek)

def decrypt_bytes(
    ciphertext: bytes,
    dek: Union[bytes, bytearray],
    nonce: bytes,
    file_id: Union[int, str, bytes],
) -> bytes:
    """
    Decrypt ciphertext bytes using AES-256-GCM.
    - Verifies authentication tag and AAD bound to file_id.
    - Raises DecryptionError on tampered ciphertext, invalid nonce, wrong DEK, or mismatching AAD.
    """
    if len(dek) != 32:
        raise DecryptionError("Decryption failed")
    if len(nonce) != 12:
        raise DecryptionError("Decryption failed")

    aad = _normalize_aad(file_id)
    dek_bytes = bytes(dek)

    try:
        aesgcm = AESGCM(dek_bytes)
        plaintext = aesgcm.decrypt(nonce, ciphertext, aad)
        return plaintext
    except Exception:
        # Strictly catch any crypto error and raise generic DecryptionError with zero detail leakage
        raise DecryptionError("Decryption failed") from None
    finally:
        if isinstance(dek, bytearray):
            zero_bytearray(dek)
