import base64
import json
import os
import secrets
from typing import Dict, Optional, Tuple, Union
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.services.crypto import DecryptionError, zero_bytearray

def _normalize_aad(file_id: Union[int, str, bytes]) -> bytes:
    if isinstance(file_id, bytes):
        return file_id
    return str(file_id).encode("utf-8")

class KeyManager:
    """
    Manages Key Encryption Keys (KEK) and envelope encryption of Data Encryption Keys (DEK).
    - Loads versioned KEKs from JSON mapping in environment.
    - Fails fast at initialization if keys are missing, invalid, or not exactly 32 bytes.
    - Generates random 256-bit DEKs per file.
    - Wraps/unwraps DEKs using AES-256-GCM bound to file_id AAD.
    - Re-wraps existing DEKs under current KEK version.
    """

    def __init__(
        self,
        kek_keys_raw: Optional[Union[str, Dict[str, str]]] = None,
        current_version: Optional[Union[str, int]] = None,
    ):
        if kek_keys_raw is None:
            from app.core.config import get_settings
            settings = get_settings()
            kek_keys_raw = settings.KEK_KEYS
            current_version = current_version or settings.KEK_CURRENT_VERSION

        if not kek_keys_raw:
            raise ValueError("Security violation: KEK_KEYS environment variable must not be empty.")

        if isinstance(kek_keys_raw, str):
            try:
                keys_dict = json.loads(kek_keys_raw)
            except Exception as e:
                raise ValueError(f"Security violation: KEK_KEYS must be valid JSON: {e}") from None
        elif isinstance(kek_keys_raw, dict):
            keys_dict = kek_keys_raw
        else:
            raise ValueError("Security violation: KEK_KEYS must be a JSON string or dict.")

        if not keys_dict:
            raise ValueError("Security violation: KEK_KEYS must contain at least one key version.")

        self.keys: Dict[str, bytes] = {}
        for ver, b64_key in keys_dict.items():
            str_ver = str(ver).strip()
            try:
                decoded = base64.b64decode(b64_key, validate=True)
            except Exception as e:
                raise ValueError(f"Security violation: KEK version '{str_ver}' is not valid base64: {e}") from None

            if len(decoded) != 32:
                raise ValueError(
                    f"Security violation: KEK version '{str_ver}' must decode to exactly 32 bytes (256 bits), got {len(decoded)} bytes."
                )
            self.keys[str_ver] = decoded

        curr_ver_str = str(current_version if current_version is not None else "1").strip()
        if curr_ver_str not in self.keys:
            raise ValueError(
                f"Security violation: KEK_CURRENT_VERSION '{curr_ver_str}' not found in configured KEK_KEYS {list(self.keys.keys())}."
            )

        self.current_version: str = curr_ver_str

    def generate_dek(self) -> bytearray:
        """Generate a cryptographically secure random 256-bit (32-byte) Data Encryption Key."""
        return bytearray(secrets.token_bytes(32))

    def wrap_dek(
        self,
        dek: Union[bytes, bytearray],
        file_id: Union[int, str, bytes],
    ) -> Tuple[bytes, str]:
        """
        Wrap a plaintext DEK using current KEK version.
        Format: wrap_nonce(12) || ciphertext + tag.
        AAD: file_id bytes.
        Returns: (wrapped_blob, current_version).
        """
        if len(dek) != 32:
            raise ValueError("DEK to wrap must be exactly 32 bytes")

        nonce = os.urandom(12)
        aad = _normalize_aad(file_id)
        kek = self.keys[self.current_version]

        aesgcm = AESGCM(kek)
        ciphertext = aesgcm.encrypt(nonce, bytes(dek), aad)
        wrapped_blob = nonce + ciphertext
        return wrapped_blob, self.current_version

    def unwrap_dek(
        self,
        wrapped_blob: bytes,
        key_version: Union[str, int],
        file_id: Union[int, str, bytes],
    ) -> bytearray:
        """
        Unwrap a wrapped DEK using specified KEK version.
        AAD: file_id bytes.
        Returns plaintext DEK as a bytearray for best-effort clearing.
        """
        ver_str = str(key_version).strip()
        if ver_str not in self.keys:
            raise DecryptionError(f"KEK version '{ver_str}' not configured")

        if len(wrapped_blob) < 28:  # 12 bytes nonce + 16 bytes auth tag
            raise DecryptionError("Invalid wrapped DEK length")

        nonce = wrapped_blob[:12]
        ciphertext = wrapped_blob[12:]
        aad = _normalize_aad(file_id)
        kek = self.keys[ver_str]

        try:
            aesgcm = AESGCM(kek)
            raw_dek = aesgcm.decrypt(nonce, ciphertext, aad)
            return bytearray(raw_dek)
        except Exception:
            raise DecryptionError("Failed to unwrap DEK") from None

    def rewrap(
        self,
        wrapped_blob: bytes,
        old_version: Union[str, int],
        file_id: Union[int, str, bytes],
    ) -> Tuple[bytes, str]:
        """
        Re-encrypt an existing wrapped DEK from old_version to current KEK version.
        Zeroes out intermediate plaintext DEK immediately after wrapping.
        """
        dek = self.unwrap_dek(wrapped_blob, old_version, file_id)
        try:
            return self.wrap_dek(dek, file_id)
        finally:
            zero_bytearray(dek)

_key_manager: Optional[KeyManager] = None

def get_key_manager() -> KeyManager:
    global _key_manager
    if _key_manager is None:
        _key_manager = KeyManager()
    return _key_manager
