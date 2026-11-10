"""File envelope header format and chunk framing for ChaCha20-Poly1305."""

import hashlib
import struct
from dataclasses import dataclass
from typing import BinaryIO
from cryptosafe.common.errors import ValidationError

HEADER_MAGIC = b"CSAFE_FL"
HEADER_VERSION = 1

KDF_ID_PBKDF2 = 1
KDF_ID_DIRECT = 2

HEADER_STRUCT_FORMAT = ">8sHHI16s12sI"
HEADER_SIZE = struct.calcsize(HEADER_STRUCT_FORMAT)  # 48 bytes

CHUNK_HEADER_FORMAT = ">IB"
CHUNK_HEADER_SIZE = struct.calcsize(CHUNK_HEADER_FORMAT)  # 5 bytes

DEFAULT_CHUNK_SIZE = 64 * 1024    # 64 KB
MIN_CHUNK_SIZE = 1024              # 1 KB
MAX_CHUNK_SIZE = 16 * 1024 * 1024  # 16 MB

# PBKDF2 iteration limits applied during both serialisation and deserialisation
MIN_PBKDF2_ITERATIONS = 100_000
MAX_PBKDF2_ITERATIONS = 10_000_000

# Nonce space: 96-bit counter, so at most 2**96 - 1 chunks per file.
# In practice the maximum addressable chunk index is bounded by the 32-bit
# uint32 ct_len field and chunk_size, so the realistic limit is far smaller.
# We use 2**64 as a practical ceiling that still fits comfortably in 96 bits.
MAX_CHUNK_INDEX = (2**64) - 1

TAG_LENGTH_BYTES = 16  # Poly1305 authentication tag


@dataclass(frozen=True)
class FileHeader:
    """Parsed file envelope header."""

    version: int
    kdf_id: int
    iterations: int
    salt: bytes
    base_nonce: bytes
    chunk_size: int
    header_bytes: bytes
    header_digest: bytes


def serialize_file_header(
    kdf_id: int,
    iterations: int,
    salt: bytes,
    base_nonce: bytes,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> bytes:
    """Pack file metadata into a 48-byte binary envelope header."""
    if kdf_id not in (KDF_ID_PBKDF2, KDF_ID_DIRECT):
        raise ValidationError(f"ID KDF file envelope tidak didukung: {kdf_id}")
    if len(salt) != 16:
        raise ValidationError("Panjang salt file envelope harus tepat 16 bytes.")
    if len(base_nonce) != 12:
        raise ValidationError("Panjang base nonce file envelope harus tepat 12 bytes.")
    if not (MIN_CHUNK_SIZE <= chunk_size <= MAX_CHUNK_SIZE):
        raise ValidationError(f"Ukuran chunk {chunk_size} di luar batas yang diizinkan.")

    if kdf_id == KDF_ID_PBKDF2:
        if not (MIN_PBKDF2_ITERATIONS <= iterations <= MAX_PBKDF2_ITERATIONS):
            raise ValidationError(
                f"Jumlah iterasi PBKDF2 harus antara {MIN_PBKDF2_ITERATIONS} "
                f"dan {MAX_PBKDF2_ITERATIONS}, diterima: {iterations}."
            )
    # For DIRECT key: iterations field is stored as 0, salt is all-zero placeholder.
    # We do not validate the numeric value for DIRECT since it is not used.

    header_bytes = struct.pack(
        HEADER_STRUCT_FORMAT,
        HEADER_MAGIC,
        HEADER_VERSION,
        kdf_id,
        iterations,
        salt,
        base_nonce,
        chunk_size,
    )
    return header_bytes


def deserialize_file_header(stream: BinaryIO) -> FileHeader:
    """Read and validate the 48-byte binary envelope header from a stream."""
    raw = stream.read(HEADER_SIZE)
    if len(raw) < HEADER_SIZE:
        raise ValidationError("File terenkripsi rusak atau terlalu pendek: header tidak lengkap.")

    magic, version, kdf_id, iterations, salt, base_nonce, chunk_size = struct.unpack(
        HEADER_STRUCT_FORMAT, raw
    )

    if magic != HEADER_MAGIC:
        raise ValidationError("Pengenal file envelope tidak valid (bukan file terenkripsi CRYPTOSAFE).")
    if version != HEADER_VERSION:
        raise ValidationError(f"Versi file envelope tidak didukung: {version}.")
    if kdf_id not in (KDF_ID_PBKDF2, KDF_ID_DIRECT):
        raise ValidationError(f"Metode derivasi kunci KDF ({kdf_id}) tidak didukung.")

    if kdf_id == KDF_ID_PBKDF2:
        if len(salt) != 16:
            raise ValidationError("Salt PBKDF2 pada header file envelope tidak valid (harus 16 bytes).")
        if not (MIN_PBKDF2_ITERATIONS <= iterations <= MAX_PBKDF2_ITERATIONS):
            raise ValidationError(
                f"Jumlah iterasi PBKDF2 pada header tidak valid: {iterations}. "
                f"Harus antara {MIN_PBKDF2_ITERATIONS} dan {MAX_PBKDF2_ITERATIONS}."
            )
    else:
        # KDF_ID_DIRECT: iterations field must be 0
        if iterations != 0:
            raise ValidationError(
                f"Header file envelope dengan KDF direct tidak boleh memiliki nilai iterasi ({iterations} != 0)."
            )

    if not (MIN_CHUNK_SIZE <= chunk_size <= MAX_CHUNK_SIZE):
        raise ValidationError(f"Ukuran chunk pada header ({chunk_size}) tidak valid.")

    header_digest = hashlib.sha256(raw).digest()
    return FileHeader(
        version=version,
        kdf_id=kdf_id,
        iterations=iterations,
        salt=salt,
        base_nonce=base_nonce,
        chunk_size=chunk_size,
        header_bytes=raw,
        header_digest=header_digest,
    )


def compute_chunk_nonce(base_nonce: bytes, chunk_index: int) -> bytes:
    """Compute a unique 96-bit nonce for chunk_index by adding the index to base_nonce.

    Raises:
        ValidationError: If chunk_index is negative.
        OverflowError: If the addition would overflow the 96-bit nonce space.
    """
    if chunk_index < 0:
        raise ValidationError(f"Chunk index tidak boleh negatif: {chunk_index}.")
    if chunk_index > MAX_CHUNK_INDEX:
        raise ValidationError(
            f"Chunk index {chunk_index} melebihi batas maksimum yang diizinkan ({MAX_CHUNK_INDEX})."
        )

    base_int = int.from_bytes(base_nonce, "big")
    result = base_int + chunk_index

    # Reject wrap-around: the sum must still fit in 96 bits without modulo.
    if result >= (2**96):
        raise OverflowError(
            f"Penambahan chunk_index {chunk_index} ke base_nonce menyebabkan overflow 96-bit. "
            "File terlalu besar atau base_nonce terlalu besar untuk enkripsi chunked yang aman."
        )

    return result.to_bytes(12, "big")


def compute_chunk_ad(header_digest: bytes, chunk_index: int, is_last: bool) -> bytes:
    """Compute authenticated associated data for chunk_index."""
    return header_digest + chunk_index.to_bytes(8, "big") + (b"\x01" if is_last else b"\x00")


def validate_chunk_header(
    ct_len: int,
    is_last_byte: int,
    chunk_size: int,
    is_first_read: bool = False,
) -> bool:
    """Validate a parsed chunk header fields before reading payload.

    Returns True if this is the last chunk.
    Raises ValidationError for any malformed value.
    """
    if is_last_byte not in (0, 1):
        raise ValidationError(
            f"Nilai flag chunk final tidak valid: {is_last_byte}. Harus 0 atau 1."
        )

    # Every ciphertext chunk must carry at least the 16-byte Poly1305 tag.
    if ct_len < TAG_LENGTH_BYTES:
        raise ValidationError(
            f"Panjang ciphertext chunk terlalu kecil: {ct_len} bytes "
            f"(minimal {TAG_LENGTH_BYTES} bytes untuk tag autentikasi)."
        )

    max_ct_len = chunk_size + TAG_LENGTH_BYTES
    if ct_len > max_ct_len:
        raise ValidationError(
            f"Panjang ciphertext chunk terlalu besar: {ct_len} bytes "
            f"(maksimal {max_ct_len} bytes untuk chunk_size={chunk_size})."
        )

    is_last = bool(is_last_byte)

    # Non-final chunks must carry exactly chunk_size plaintext bytes.
    if not is_last:
        expected_ct_len = chunk_size + TAG_LENGTH_BYTES
        if ct_len != expected_ct_len:
            raise ValidationError(
                f"Chunk non-final harus memiliki panjang ciphertext tepat {expected_ct_len} bytes, "
                f"diterima: {ct_len} bytes."
            )

    return is_last
