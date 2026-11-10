"""File encryption and decryption service using ChaCha20-Poly1305."""

import hashlib
import logging
import secrets
import struct
from pathlib import Path
from cryptosafe.common.errors import CryptoOperationError, ValidationError
from cryptosafe.crypto.chacha20 import chacha20_poly1305_encrypt, chacha20_poly1305_decrypt
from cryptosafe.crypto.file_envelope import (
    DEFAULT_CHUNK_SIZE,
    CHUNK_HEADER_FORMAT,
    CHUNK_HEADER_SIZE,
    MAX_CHUNK_INDEX,
    KDF_ID_PBKDF2,
    KDF_ID_DIRECT,
    serialize_file_header,
    deserialize_file_header,
    compute_chunk_nonce,
    compute_chunk_ad,
    validate_chunk_header,
)
from cryptosafe.crypto.key_manager import (
    DEFAULT_PBKDF2_ITERATIONS,
    generate_salt,
    is_direct_hex_key,
    derive_key_from_passphrase,
)

logger = logging.getLogger("cryptosafe.crypto.file")


class FileCryptoService:
    """Service orchestrating chunked authenticated file encryption with ChaCha20-Poly1305."""

    def encrypt_file(
        self,
        source_path: Path | str,
        destination_path: Path | str,
        key_material: str,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
    ) -> None:
        """Encrypt a file using ChaCha20-Poly1305 with versioned envelope framing.

        Supports binary files and large files using memory-efficient streaming chunks.
        Each chunk has a unique nonce derived from base_nonce + chunk_index (no modulo).
        """
        src = Path(source_path).resolve()
        dst = Path(destination_path).resolve()

        if not src.is_file():
            raise ValidationError(f"File sumber tidak ditemukan atau bukan file valid: {src}")
        if src == dst:
            raise ValidationError("File tujuan tidak boleh sama dengan file sumber.")
        if not key_material or not key_material.strip():
            raise ValidationError("Kunci atau passphrase tidak boleh kosong.")

        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp_dst = dst.with_name(f"{dst.name}.tmp_enc_{secrets.token_hex(4)}")

        # 1. Resolve key material
        clean_key = key_material.strip()
        if is_direct_hex_key(clean_key):
            raw_key = bytes.fromhex(clean_key)
            kdf_id = KDF_ID_DIRECT
            iterations = 0
            salt = b"\x00" * 16
        else:
            salt = generate_salt()
            iterations = DEFAULT_PBKDF2_ITERATIONS
            raw_key = derive_key_from_passphrase(clean_key, salt, iterations=iterations)
            kdf_id = KDF_ID_PBKDF2

        # 2. Generate random 12-byte base nonce and envelope header
        base_nonce = secrets.token_bytes(12)
        header_bytes = serialize_file_header(
            kdf_id=kdf_id,
            iterations=iterations,
            salt=salt,
            base_nonce=base_nonce,
            chunk_size=chunk_size,
        )
        header_digest = hashlib.sha256(header_bytes).digest()

        try:
            with open(src, "rb") as in_f, open(tmp_dst, "wb") as out_f:
                # Write 48-byte header
                out_f.write(header_bytes)

                chunk_index = 0
                current_chunk = in_f.read(chunk_size)

                while True:
                    next_chunk = in_f.read(chunk_size)
                    is_last = (len(next_chunk) == 0)

                    # Reject overflow before constructing nonce (raises OverflowError/ValidationError)
                    nonce = compute_chunk_nonce(base_nonce, chunk_index)
                    ad = compute_chunk_ad(header_digest, chunk_index, is_last)

                    ct_chunk = chacha20_poly1305_encrypt(
                        plaintext_bytes=current_chunk,
                        key_bytes=raw_key,
                        nonce_bytes=nonce,
                        associated_data=ad,
                    )

                    chunk_hdr = struct.pack(CHUNK_HEADER_FORMAT, len(ct_chunk), 1 if is_last else 0)
                    out_f.write(chunk_hdr)
                    out_f.write(ct_chunk)

                    if is_last:
                        break

                    current_chunk = next_chunk
                    chunk_index += 1

                    if chunk_index > MAX_CHUNK_INDEX:
                        raise ValidationError(
                            f"File melebihi batas chunk maksimum ({MAX_CHUNK_INDEX}). "
                            "Gunakan chunk_size yang lebih besar."
                        )

            # Atomically replace destination file on complete success
            tmp_dst.replace(dst)
            logger.info(
                "File encryption completed: %s -> %s (chunks=%d)",
                src.name, dst.name, chunk_index + 1,
            )
        except Exception:
            if tmp_dst.exists():
                tmp_dst.unlink(missing_ok=True)
            raise

    def decrypt_file(
        self,
        source_path: Path | str,
        destination_path: Path | str,
        key_material: str,
    ) -> None:
        """Decrypt a file using ChaCha20-Poly1305, verifying envelope and all chunk tags.

        Plaintext is only committed to destination if all chunks and header authenticate completely.
        No partial plaintext is exposed on failure.
        """
        src = Path(source_path).resolve()
        dst = Path(destination_path).resolve()

        if not src.is_file():
            raise ValidationError(f"File terenkripsi tidak ditemukan: {src}")
        if src == dst:
            raise ValidationError("File tujuan tidak boleh sama dengan file sumber.")
        if not key_material or not key_material.strip():
            raise ValidationError("Kunci atau passphrase tidak boleh kosong.")

        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp_dst = dst.with_name(f"{dst.name}.tmp_dec_{secrets.token_hex(4)}")

        try:
            with open(src, "rb") as in_f:
                # 1. Parse and validate header (raises ValidationError on bad input)
                header = deserialize_file_header(in_f)

                # 2. Resolve key material using envelope KDF metadata
                clean_key = key_material.strip()
                if header.kdf_id == KDF_ID_DIRECT:
                    if not is_direct_hex_key(clean_key):
                        raise ValidationError("Kunci file ini harus berupa 64 karakter hexadesimal.")
                    raw_key = bytes.fromhex(clean_key)
                else:
                    # iterations already validated in deserialize_file_header
                    raw_key = derive_key_from_passphrase(
                        clean_key,
                        header.salt,
                        iterations=header.iterations,
                    )

                # 3. Decrypt chunks into temporary file
                with open(tmp_dst, "wb") as out_f:
                    chunk_index = 0
                    saw_last_chunk = False

                    while True:
                        chunk_hdr_raw = in_f.read(CHUNK_HEADER_SIZE)
                        if not chunk_hdr_raw:
                            break
                        if len(chunk_hdr_raw) < CHUNK_HEADER_SIZE:
                            raise CryptoOperationError(
                                "File terenkripsi terpotong: header chunk tidak lengkap."
                            )

                        ct_len, is_last_byte = struct.unpack(CHUNK_HEADER_FORMAT, chunk_hdr_raw)

                        # Validate chunk header fields before reading payload
                        is_last = validate_chunk_header(
                            ct_len=ct_len,
                            is_last_byte=is_last_byte,
                            chunk_size=header.chunk_size,
                        )

                        # Guard against chunk index overflow before nonce derivation
                        if chunk_index > MAX_CHUNK_INDEX:
                            raise CryptoOperationError(
                                f"Jumlah chunk melebihi batas maksimum ({MAX_CHUNK_INDEX}). "
                                "File rusak atau tidak valid."
                            )

                        ct_chunk = in_f.read(ct_len)
                        if len(ct_chunk) < ct_len:
                            raise CryptoOperationError(
                                "File terenkripsi terpotong: data chunk tidak lengkap."
                            )

                        nonce = compute_chunk_nonce(header.base_nonce, chunk_index)
                        ad = compute_chunk_ad(header.header_digest, chunk_index, is_last)

                        pt_chunk = chacha20_poly1305_decrypt(
                            ciphertext_with_tag=ct_chunk,
                            key_bytes=raw_key,
                            nonce_bytes=nonce,
                            associated_data=ad,
                        )
                        out_f.write(pt_chunk)

                        if is_last:
                            saw_last_chunk = True
                            break

                        chunk_index += 1

                    if not saw_last_chunk:
                        raise CryptoOperationError(
                            "File terenkripsi terpotong: penanda akhir file tidak ditemukan."
                        )

                    # Ensure no trailing data exists after the last chunk
                    trailing = in_f.read(1)
                    if trailing:
                        raise CryptoOperationError(
                            "File terenkripsi rusak: ditemukan data tambahan setelah chunk terakhir."
                        )

            # Atomically replace destination ONLY after full verification
            tmp_dst.replace(dst)
            logger.info(
                "File decryption verified and completed: %s -> %s", src.name, dst.name
            )
        except Exception:
            if tmp_dst.exists():
                tmp_dst.unlink(missing_ok=True)
            raise
