"""ChaCha20-Poly1305 authenticated encryption and decryption."""

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.exceptions import InvalidTag
from cryptosafe.common.errors import CryptoOperationError, ValidationError

KEY_LENGTH_BYTES = 32   # 256 bits
NONCE_LENGTH_BYTES = 12 # 96 bits
TAG_LENGTH_BYTES = 16   # 128 bits


def chacha20_poly1305_encrypt(
    plaintext_bytes: bytes,
    key_bytes: bytes,
    nonce_bytes: bytes,
    associated_data: bytes | None = None,
) -> bytes:
    """Encrypt plaintext with ChaCha20-Poly1305.

    Returns:
        bytes: Ciphertext with 16-byte Poly1305 authentication tag appended.
    """
    if len(key_bytes) != KEY_LENGTH_BYTES:
        raise ValidationError(f"Panjang kunci ChaCha20-Poly1305 harus {KEY_LENGTH_BYTES} bytes (256 bit).")
    if len(nonce_bytes) != NONCE_LENGTH_BYTES:
        raise ValidationError(f"Panjang nonce ChaCha20-Poly1305 harus {NONCE_LENGTH_BYTES} bytes (96 bit).")

    chacha = ChaCha20Poly1305(key_bytes)
    return chacha.encrypt(nonce_bytes, plaintext_bytes, associated_data)


def chacha20_poly1305_decrypt(
    ciphertext_with_tag: bytes,
    key_bytes: bytes,
    nonce_bytes: bytes,
    associated_data: bytes | None = None,
) -> bytes:
    """Decrypt and authenticate ciphertext with ChaCha20-Poly1305.

    Raises:
        ValidationError: If key or nonce length is invalid.
        CryptoOperationError: If authentication tag verification fails (wrong key or tampering).
    """
    if len(key_bytes) != KEY_LENGTH_BYTES:
        raise ValidationError(f"Panjang kunci ChaCha20-Poly1305 harus {KEY_LENGTH_BYTES} bytes (256 bit).")
    if len(nonce_bytes) != NONCE_LENGTH_BYTES:
        raise ValidationError(f"Panjang nonce ChaCha20-Poly1305 harus {NONCE_LENGTH_BYTES} bytes (96 bit).")
    if len(ciphertext_with_tag) < TAG_LENGTH_BYTES:
        raise CryptoOperationError("Ciphertext terlalu pendek untuk memuat tag autentikasi Poly1305.")

    chacha = ChaCha20Poly1305(key_bytes)
    try:
        return chacha.decrypt(nonce_bytes, ciphertext_with_tag, associated_data)
    except InvalidTag:
        raise CryptoOperationError("Verifikasi autentikasi ChaCha20-Poly1305 gagal: kunci salah atau data rusak.")

