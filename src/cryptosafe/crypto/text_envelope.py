"""Structured envelope serialization for encrypted text payloads."""

import json
from dataclasses import dataclass
from cryptosafe.common.errors import ValidationError
from cryptosafe.crypto.key_manager import (
    DEFAULT_PBKDF2_ITERATIONS,
    SALT_LENGTH_BYTES,
    KDF_PBKDF2,
    KDF_DIRECT,
)

ENVELOPE_MAGIC = "CRYPTOSAFE_TEXT"
ENVELOPE_VERSION = 1
ALGORITHM_IDENTIFIER = "VIGENERE+AES-256-GCM"

NONCE_LENGTH_BYTES = 12
GCM_TAG_LENGTH_BYTES = 16
SUPPORTED_KDF = {KDF_PBKDF2, KDF_DIRECT, "Direct AES-256 key", "DIRECT"}


@dataclass(frozen=True)
class TextEnvelope:
    """Parsed structured envelope for text cryptography."""

    algorithm: str
    kdf: str
    salt: bytes
    nonce: bytes
    ciphertext: bytes
    iterations: int | None = None

    def __iter__(self):
        """Allow tuple unpacking (salt, nonce, ciphertext) for backward compatibility."""
        return iter((self.salt, self.nonce, self.ciphertext))


def serialize_text_envelope(
    salt: bytes,
    nonce: bytes,
    ciphertext: bytes,
    kdf: str = KDF_PBKDF2,
    iterations: int | None = DEFAULT_PBKDF2_ITERATIONS,
    algorithm: str = ALGORITHM_IDENTIFIER,
) -> str:
    """Pack cryptographic components and metadata into a structured, versioned JSON envelope."""
    payload = {
        "magic": ENVELOPE_MAGIC,
        "version": ENVELOPE_VERSION,
        "algorithm": algorithm,
        "kdf": kdf,
        "salt": salt.hex() if salt else "",
        "nonce": nonce.hex(),
        "ciphertext": ciphertext.hex(),
    }
    if kdf == KDF_PBKDF2:
        payload["iterations"] = iterations if iterations is not None else DEFAULT_PBKDF2_ITERATIONS

    return json.dumps(payload, indent=2)


def deserialize_text_envelope(envelope_str: str) -> TextEnvelope:
    """Parse and validate a structured envelope.

    Validates:
        - magic identifier ("CRYPTOSAFE_TEXT")
        - envelope version (1)
        - algorithm ("VIGENERE+AES-256-GCM")
        - kdf (supported KDF identifiers)
        - salt (hex string, >= 16 bytes for PBKDF2)
        - iterations (> 0 for PBKDF2)
        - nonce (hex string, exactly 12 bytes)
        - ciphertext (hex string, >= 16 bytes for AES-GCM tag)

    Returns:
        TextEnvelope: Validated structured envelope object.
    """
    if not envelope_str or not isinstance(envelope_str, str):
        raise ValidationError("Format amplop ciphertext tidak boleh kosong.")

    try:
        data = json.loads(envelope_str.strip())
    except (json.JSONDecodeError, ValueError) as err:
        raise ValidationError(f"Format amplop ciphertext bukan JSON yang valid: {err}")

    if not isinstance(data, dict):
        raise ValidationError("Struktur amplop ciphertext tidak valid.")

    if data.get("magic") != ENVELOPE_MAGIC:
        raise ValidationError("Pengenal format amplop tidak cocok (bukan format CRYPTOSAFE_TEXT).")

    if data.get("version") != ENVELOPE_VERSION:
        raise ValidationError(f"Versi amplop tidak didukung: {data.get('version')}.")

    # 1. Validate algorithm
    algorithm = data.get("algorithm")
    if not algorithm or algorithm != ALGORITHM_IDENTIFIER:
        raise ValidationError(f"Algoritma '{algorithm}' tidak didukung atau tidak valid.")

    # 2. Validate kdf
    kdf = data.get("kdf")
    if not kdf or not isinstance(kdf, str) or kdf not in SUPPORTED_KDF:
        raise ValidationError(f"KDF '{kdf}' tidak didukung atau tidak valid.")

    # 3. Validate salt
    if "salt" not in data or not isinstance(data["salt"], str):
        raise ValidationError("Field 'salt' hilang atau tidak valid pada amplop.")

    try:
        salt = bytes.fromhex(data["salt"]) if data["salt"] else b""
    except ValueError as err:
        raise ValidationError(f"Nilai hexadecimal salt tidak valid: {err}")

    # 4. Validate iterations (if PBKDF2)
    iterations = data.get("iterations")
    if kdf == KDF_PBKDF2:
        if len(salt) < SALT_LENGTH_BYTES:
            raise ValidationError(
                f"Salt PBKDF2 tidak valid (panjang {len(salt)} bytes, minimal {SALT_LENGTH_BYTES} bytes)."
            )
        if not isinstance(iterations, int) or iterations <= 0:
            raise ValidationError("Jumlah iterasi PBKDF2 hilang atau tidak valid pada amplop.")
    else:
        iterations = None

    # 5. Validate nonce
    if "nonce" not in data or not isinstance(data["nonce"], str):
        raise ValidationError("Field 'nonce' hilang atau tidak valid pada amplop.")

    try:
        nonce = bytes.fromhex(data["nonce"])
    except ValueError as err:
        raise ValidationError(f"Nilai hexadecimal nonce tidak valid: {err}")

    if len(nonce) != NONCE_LENGTH_BYTES:
        raise ValidationError(
            f"Panjang nonce tidak valid: {len(nonce)} bytes (harus tepat {NONCE_LENGTH_BYTES} bytes)."
        )

    # 6. Validate ciphertext
    if "ciphertext" not in data or not isinstance(data["ciphertext"], str) or not data["ciphertext"]:
        raise ValidationError("Field 'ciphertext' hilang atau kosong pada amplop.")

    try:
        ciphertext = bytes.fromhex(data["ciphertext"])
    except ValueError as err:
        raise ValidationError(f"Nilai hexadecimal ciphertext tidak valid: {err}")

    if len(ciphertext) < GCM_TAG_LENGTH_BYTES:
        raise ValidationError(
            f"Panjang ciphertext tidak valid: {len(ciphertext)} bytes (minimal {GCM_TAG_LENGTH_BYTES} bytes untuk tag AEAD)."
        )

    return TextEnvelope(
        algorithm=algorithm,
        kdf=kdf,
        salt=salt,
        nonce=nonce,
        ciphertext=ciphertext,
        iterations=iterations,
    )
