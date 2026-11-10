"""Authenticated encryption and decryption using AES-256-GCM."""

import secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
from cryptosafe.common.errors import CryptoOperationError, ValidationError

NONCE_LENGTH_BYTES = 12  # 96 bits for standard GCM
KEY_LENGTH_BYTES = 32    # 256 bits

def aes_gcm_encrypt(
    plaintext_bytes: bytes,
    key_bytes: bytes,
    associated_data: bytes | None = None,
) -> tuple[bytes, bytes]:
    """Encrypt plaintext bytes with AES-256-GCM using a fresh 96-bit CSPRNG nonce.

    Returns:
        tuple[bytes, bytes]: (nonce_bytes, ciphertext_with_tag_bytes)
    """
    if len(key_bytes) != KEY_LENGTH_BYTES:
        raise ValidationError(f"Panjang kunci AES-256 harus tepat {KEY_LENGTH_BYTES} bytes (256 bit).")

    # Generate a fresh 96-bit nonce using cryptographically secure random generation
    nonce = secrets.token_bytes(NONCE_LENGTH_BYTES)

    aesgcm = AESGCM(key_bytes)
    ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext_bytes, associated_data)
    return nonce, ciphertext_with_tag

def aes_gcm_decrypt(
    ciphertext_with_tag: bytes,
    key_bytes: bytes,
    nonce_bytes: bytes,
    associated_data: bytes | None = None,
) -> bytes:
    """Decrypt and verify ciphertext with AES-256-GCM.

    Raises:
        CryptoOperationError: If authentication tag check fails (tampered or wrong key).
    """
    if len(key_bytes) != KEY_LENGTH_BYTES:
        raise ValidationError(f"Panjang kunci AES-256 harus tepat {KEY_LENGTH_BYTES} bytes (256 bit).")
    if len(nonce_bytes) != NONCE_LENGTH_BYTES:
        raise ValidationError(f"Panjang nonce harus tepat {NONCE_LENGTH_BYTES} bytes (96 bit).")

    aesgcm = AESGCM(key_bytes)
    try:
        return aesgcm.decrypt(nonce_bytes, ciphertext_with_tag, associated_data)
    except InvalidTag:
        raise CryptoOperationError(
            "Dekripsi AES-GCM gagal: tag autentikasi tidak cocok. Ciphertext telah dimodifikasi atau kunci salah."
        )

