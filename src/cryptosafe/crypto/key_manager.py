"""Key management and derivation policies for AES-256."""

import secrets
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptosafe.common.errors import ValidationError

DEFAULT_PBKDF2_ITERATIONS = 600_000
SALT_LENGTH_BYTES = 16
KEY_LENGTH_BYTES = 32  # 256 bits

KDF_PBKDF2 = "PBKDF2-HMAC-SHA256"
KDF_DIRECT = "DIRECT-AES-256"


def generate_random_aes_key() -> str:
    """Generate a cryptographically secure 256-bit AES key as a 64-character hex string."""
    return secrets.token_hex(KEY_LENGTH_BYTES)


def generate_salt() -> bytes:
    """Generate a cryptographically secure 16-byte salt for KDF."""
    return secrets.token_bytes(SALT_LENGTH_BYTES)


def is_direct_hex_key(key_material: str) -> bool:
    """Check if the provided input is a valid 64-character hexadecimal string (256 bits)."""
    if not key_material or not isinstance(key_material, str):
        return False
    clean = key_material.strip()
    if len(clean) == 64:
        try:
            return len(bytes.fromhex(clean)) == KEY_LENGTH_BYTES
        except ValueError:
            return False
    return False


def derive_key_from_passphrase(
    passphrase: str,
    salt: bytes,
    iterations: int = DEFAULT_PBKDF2_ITERATIONS,
) -> bytes:
    """Derive a 256-bit key from a passphrase using standard PBKDF2-HMAC-SHA256."""
    if not passphrase:
        raise ValidationError("Kunci atau passphrase AES tidak boleh kosong.")
    if not salt or len(salt) < SALT_LENGTH_BYTES:
        raise ValidationError(f"Salt untuk derivasi kunci tidak valid (minimal {SALT_LENGTH_BYTES} bytes).")
    if not isinstance(iterations, int) or iterations <= 0:
        raise ValidationError("Jumlah iterasi PBKDF2 harus berupa bilangan bulat positif.")

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LENGTH_BYTES,
        salt=salt,
        iterations=iterations,
    )
    return kdf.derive(passphrase.encode("utf-8"))


def resolve_encryption_key(
    key_material: str,
    salt: bytes | None = None,
    iterations: int = DEFAULT_PBKDF2_ITERATIONS,
) -> tuple[bytes, str, bytes, int | None]:
    """Resolve key input for encryption and determine appropriate KDF metadata.

    Returns:
        tuple[bytes, str, bytes, int | None]:
            (aes_key_bytes, kdf_identifier, salt_bytes, iterations_count)
    """
    clean_input = key_material.strip() if key_material else ""
    if not clean_input:
        raise ValidationError("Kunci AES atau passphrase tidak boleh kosong.")

    if is_direct_hex_key(clean_input):
        raw_key = bytes.fromhex(clean_input)
        return raw_key, KDF_DIRECT, b"", None

    used_salt = salt if (salt and len(salt) >= SALT_LENGTH_BYTES) else generate_salt()
    derived_key = derive_key_from_passphrase(clean_input, used_salt, iterations=iterations)
    return derived_key, KDF_PBKDF2, used_salt, iterations


def resolve_decryption_key(
    key_material: str,
    kdf: str,
    salt: bytes,
    iterations: int | None = None,
) -> bytes:
    """Resolve key input for decryption according to the envelope's KDF metadata."""
    clean_input = key_material.strip() if key_material else ""
    if not clean_input:
        raise ValidationError("Kunci AES atau passphrase tidak boleh kosong.")

    if kdf in (KDF_DIRECT, "Direct AES-256 key", "DIRECT"):
        if not is_direct_hex_key(clean_input):
            raise ValidationError("Kunci AES harus berupa 64 karakter hexadesimal untuk KDF direct.")
        return bytes.fromhex(clean_input)

    elif kdf == KDF_PBKDF2:
        if iterations is None or not isinstance(iterations, int) or iterations <= 0:
            raise ValidationError("Parameter iterasi PBKDF2 tidak valid pada amplop.")
        if not salt or len(salt) < SALT_LENGTH_BYTES:
            raise ValidationError(f"Salt PBKDF2 tidak valid (minimal {SALT_LENGTH_BYTES} bytes).")
        return derive_key_from_passphrase(clean_input, salt, iterations=iterations)

    else:
        raise ValidationError(f"KDF '{kdf}' tidak didukung.")


def resolve_aes_key(
    key_material: str,
    salt: bytes | None = None,
    iterations: int = DEFAULT_PBKDF2_ITERATIONS,
    kdf: str | None = None,
) -> bytes:
    """Resolve key input into a 32-byte AES key (compatibility helper)."""
    clean_input = key_material.strip() if key_material else ""
    if not clean_input:
        raise ValidationError("Kunci AES atau passphrase tidak boleh kosong.")

    if kdf is not None:
        return resolve_decryption_key(clean_input, kdf, salt or b"", iterations)

    if is_direct_hex_key(clean_input):
        return bytes.fromhex(clean_input)

    used_salt = salt if (salt and len(salt) >= SALT_LENGTH_BYTES) else generate_salt()
    return derive_key_from_passphrase(clean_input, used_salt, iterations=iterations)
