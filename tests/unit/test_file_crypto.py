import os
import secrets
import struct
import sys
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

src_dir = Path(__file__).resolve().parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from cryptosafe.crypto.chacha20 import (
    chacha20_poly1305_encrypt,
    chacha20_poly1305_decrypt,
)
from cryptosafe.crypto.file_envelope import (
    HEADER_MAGIC,
    HEADER_VERSION,
    HEADER_SIZE,
    HEADER_STRUCT_FORMAT,
    CHUNK_HEADER_FORMAT,
    CHUNK_HEADER_SIZE,
    TAG_LENGTH_BYTES,
    KDF_ID_PBKDF2,
    KDF_ID_DIRECT,
    MIN_PBKDF2_ITERATIONS,
    MAX_PBKDF2_ITERATIONS,
    MAX_CHUNK_INDEX,
    DEFAULT_CHUNK_SIZE,
    MIN_CHUNK_SIZE,
    serialize_file_header,
    deserialize_file_header,
    compute_chunk_nonce,
    compute_chunk_ad,
    validate_chunk_header,
)
from cryptosafe.crypto.file_crypto_service import FileCryptoService
from cryptosafe.crypto.key_manager import generate_random_aes_key
from cryptosafe.common.errors import ValidationError, CryptoOperationError


class TestChaCha20Poly1305(unittest.TestCase):
    def setUp(self):
        self.key = secrets.token_bytes(32)
        self.nonce = secrets.token_bytes(12)
        self.plaintext = b"Payload rahasia ChaCha20-Poly1305."
        self.ad = b"metadata-terautentikasi"

    def test_encrypt_decrypt_round_trip(self):
        ciphertext = chacha20_poly1305_encrypt(self.plaintext, self.key, self.nonce, self.ad)
        self.assertEqual(len(ciphertext), len(self.plaintext) + 16)
        recovered = chacha20_poly1305_decrypt(ciphertext, self.key, self.nonce, self.ad)
        self.assertEqual(recovered, self.plaintext)

    def test_wrong_key_fails(self):
        ciphertext = chacha20_poly1305_encrypt(self.plaintext, self.key, self.nonce, self.ad)
        with self.assertRaises(CryptoOperationError):
            chacha20_poly1305_decrypt(ciphertext, secrets.token_bytes(32), self.nonce, self.ad)

    def test_tampered_ciphertext_fails(self):
        ciphertext = bytearray(chacha20_poly1305_encrypt(self.plaintext, self.key, self.nonce, self.ad))
        ciphertext[0] ^= 0x01
        with self.assertRaises(CryptoOperationError):
            chacha20_poly1305_decrypt(bytes(ciphertext), self.key, self.nonce, self.ad)

    def test_tampered_ad_fails(self):
        ciphertext = chacha20_poly1305_encrypt(self.plaintext, self.key, self.nonce, self.ad)
        with self.assertRaises(CryptoOperationError):
            chacha20_poly1305_decrypt(ciphertext, self.key, self.nonce, b"wrong-ad")

    def test_invalid_key_or_nonce_length(self):
        with self.assertRaises(ValidationError):
            chacha20_poly1305_encrypt(self.plaintext, b"short-key", self.nonce)
        with self.assertRaises(ValidationError):
            chacha20_poly1305_encrypt(self.plaintext, self.key, b"short-nonce")


class TestChunkNonce(unittest.TestCase):
    def test_unique_nonces_across_indices(self):
        base_nonce = secrets.token_bytes(12)
        n0 = compute_chunk_nonce(base_nonce, 0)
        n1 = compute_chunk_nonce(base_nonce, 1)
        n2 = compute_chunk_nonce(base_nonce, 2)
        self.assertEqual(len(n0), 12)
        self.assertNotEqual(n0, n1)
        self.assertNotEqual(n1, n2)

    def test_negative_index_rejected(self):
        base_nonce = secrets.token_bytes(12)
        with self.assertRaises(ValidationError):
            compute_chunk_nonce(base_nonce, -1)
        with self.assertRaises(ValidationError):
            compute_chunk_nonce(base_nonce, -100)

    def test_index_exceeds_max_chunk_index_rejected(self):
        base_nonce = secrets.token_bytes(12)
        with self.assertRaises(ValidationError):
            compute_chunk_nonce(base_nonce, MAX_CHUNK_INDEX + 1)

    def test_nonce_overflow_rejected(self):
        # Craft a base_nonce whose integer value leaves no room for even chunk_index=1.
        # Set base_nonce to 2**96 - 1 (all 0xFF bytes) so adding 1 wraps.
        overflow_base = (2**96 - 1).to_bytes(12, "big")
        # chunk_index 0 is fine (base + 0 = 2**96 - 1, still fits in 96 bits)
        nonce0 = compute_chunk_nonce(overflow_base, 0)
        self.assertEqual(len(nonce0), 12)
        # chunk_index 1 would overflow: base + 1 = 2**96
        with self.assertRaises(OverflowError):
            compute_chunk_nonce(overflow_base, 1)

    def test_no_modulo_wrapping(self):
        # Verify the implementation does not silently wrap (modulo).
        # Choose base = 2**96 - 2; index 2 would wrap to 0 if modulo were used.
        base_int = (2**96 - 2)
        base_nonce = base_int.to_bytes(12, "big")

        n0 = compute_chunk_nonce(base_nonce, 0)  # base + 0 = 2**96 - 2 (OK)
        n1 = compute_chunk_nonce(base_nonce, 1)  # base + 1 = 2**96 - 1 (OK)
        self.assertNotEqual(n0, n1)

        # base + 2 = 2**96 → must raise, NOT silently produce nonce=0
        with self.assertRaises(OverflowError):
            compute_chunk_nonce(base_nonce, 2)


class TestChunkHeaderValidation(unittest.TestCase):
    CHUNK_SIZE = 64 * 1024

    def test_valid_intermediate_chunk(self):
        # Non-last chunk must have exactly chunk_size + TAG plaintext
        ct_len = self.CHUNK_SIZE + TAG_LENGTH_BYTES
        result = validate_chunk_header(ct_len, 0, self.CHUNK_SIZE)
        self.assertFalse(result)

    def test_valid_final_chunk(self):
        # Final chunk can be smaller
        ct_len = 100 + TAG_LENGTH_BYTES
        result = validate_chunk_header(ct_len, 1, self.CHUNK_SIZE)
        self.assertTrue(result)

    def test_valid_final_chunk_full_size(self):
        # Final chunk at full size is also valid
        ct_len = self.CHUNK_SIZE + TAG_LENGTH_BYTES
        result = validate_chunk_header(ct_len, 1, self.CHUNK_SIZE)
        self.assertTrue(result)

    def test_invalid_is_last_flag_rejected(self):
        ct_len = self.CHUNK_SIZE + TAG_LENGTH_BYTES
        with self.assertRaises(ValidationError):
            validate_chunk_header(ct_len, 2, self.CHUNK_SIZE)
        with self.assertRaises(ValidationError):
            validate_chunk_header(ct_len, 255, self.CHUNK_SIZE)

    def test_ct_len_below_tag_minimum_rejected(self):
        with self.assertRaises(ValidationError):
            validate_chunk_header(TAG_LENGTH_BYTES - 1, 1, self.CHUNK_SIZE)
        with self.assertRaises(ValidationError):
            validate_chunk_header(0, 1, self.CHUNK_SIZE)

    def test_ct_len_exceeds_maximum_rejected(self):
        too_big = self.CHUNK_SIZE + TAG_LENGTH_BYTES + 1
        with self.assertRaises(ValidationError):
            validate_chunk_header(too_big, 1, self.CHUNK_SIZE)
        with self.assertRaises(ValidationError):
            validate_chunk_header(too_big, 0, self.CHUNK_SIZE)

    def test_non_final_chunk_wrong_size_rejected(self):
        # Intermediate chunk that is too small (not full chunk_size)
        too_small = TAG_LENGTH_BYTES + 100  # less than chunk_size + TAG
        with self.assertRaises(ValidationError):
            validate_chunk_header(too_small, 0, self.CHUNK_SIZE)


class TestFileEnvelope(unittest.TestCase):
    def setUp(self):
        self.salt = secrets.token_bytes(16)
        self.base_nonce = secrets.token_bytes(12)

    def test_header_serialize_deserialize_pbkdf2(self):
        raw = serialize_file_header(
            kdf_id=KDF_ID_PBKDF2,
            iterations=600_000,
            salt=self.salt,
            base_nonce=self.base_nonce,
            chunk_size=65536,
        )
        self.assertEqual(len(raw), HEADER_SIZE)

        header = deserialize_file_header(BytesIO(raw))
        self.assertEqual(header.version, HEADER_VERSION)
        self.assertEqual(header.kdf_id, KDF_ID_PBKDF2)
        self.assertEqual(header.iterations, 600_000)
        self.assertEqual(header.salt, self.salt)
        self.assertEqual(header.base_nonce, self.base_nonce)
        self.assertEqual(header.chunk_size, 65536)

    def test_header_serialize_deserialize_direct(self):
        salt_placeholder = b"\x00" * 16
        raw = serialize_file_header(
            kdf_id=KDF_ID_DIRECT,
            iterations=0,
            salt=salt_placeholder,
            base_nonce=self.base_nonce,
        )
        header = deserialize_file_header(BytesIO(raw))
        self.assertEqual(header.kdf_id, KDF_ID_DIRECT)
        self.assertEqual(header.iterations, 0)

    def test_invalid_magic_rejected(self):
        raw = bytearray(serialize_file_header(KDF_ID_PBKDF2, 600_000, self.salt, self.base_nonce))
        raw[:8] = b"WRONGMAG"
        with self.assertRaises(ValidationError):
            deserialize_file_header(BytesIO(raw))

    def test_pbkdf2_iterations_too_small_rejected(self):
        # iterations below MIN_PBKDF2_ITERATIONS must be rejected on serialize AND deserialize
        with self.assertRaises(ValidationError):
            serialize_file_header(KDF_ID_PBKDF2, MIN_PBKDF2_ITERATIONS - 1, self.salt, self.base_nonce)

        # Craft raw header bypassing serialize to test deserialize path
        raw = struct.pack(
            HEADER_STRUCT_FORMAT,
            HEADER_MAGIC,
            HEADER_VERSION,
            KDF_ID_PBKDF2,
            MIN_PBKDF2_ITERATIONS - 1,  # too small
            self.salt,
            self.base_nonce,
            DEFAULT_CHUNK_SIZE,
        )
        with self.assertRaises(ValidationError):
            deserialize_file_header(BytesIO(raw))

    def test_pbkdf2_iterations_too_large_rejected(self):
        with self.assertRaises(ValidationError):
            serialize_file_header(KDF_ID_PBKDF2, MAX_PBKDF2_ITERATIONS + 1, self.salt, self.base_nonce)

        raw = struct.pack(
            HEADER_STRUCT_FORMAT,
            HEADER_MAGIC,
            HEADER_VERSION,
            KDF_ID_PBKDF2,
            MAX_PBKDF2_ITERATIONS + 1,
            self.salt,
            self.base_nonce,
            DEFAULT_CHUNK_SIZE,
        )
        with self.assertRaises(ValidationError):
            deserialize_file_header(BytesIO(raw))

    def test_direct_key_nonzero_iterations_rejected(self):
        # For DIRECT KDF, iterations must be 0 in the header
        raw = struct.pack(
            HEADER_STRUCT_FORMAT,
            HEADER_MAGIC,
            HEADER_VERSION,
            KDF_ID_DIRECT,
            1,              # non-zero iterations on DIRECT key → invalid
            b"\x00" * 16,
            self.base_nonce,
            DEFAULT_CHUNK_SIZE,
        )
        with self.assertRaises(ValidationError):
            deserialize_file_header(BytesIO(raw))

    def test_chunk_ad_uniqueness(self):
        digest = b"X" * 32
        ad0_int = compute_chunk_ad(digest, 0, is_last=False)
        ad0_last = compute_chunk_ad(digest, 0, is_last=True)
        ad1 = compute_chunk_ad(digest, 1, is_last=False)
        self.assertNotEqual(ad0_int, ad0_last)
        self.assertNotEqual(ad0_int, ad1)


class TestFileCryptoService(unittest.TestCase):
    def setUp(self):
        self.service = FileCryptoService()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.work_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_small_file_round_trip_passphrase(self):
        src = self.work_path / "hello.txt"
        enc = self.work_path / "hello.txt.enc"
        dec = self.work_path / "hello_dec.txt"

        content = b"Halo dunia kriptografi CRYPTOSAFE 2026!\nLine 2.\n"
        src.write_bytes(content)

        self.service.encrypt_file(src, enc, "KunciPassphraseFileKuat123!")
        self.assertTrue(enc.exists())
        self.assertNotEqual(enc.read_bytes(), content)

        self.service.decrypt_file(enc, dec, "KunciPassphraseFileKuat123!")
        self.assertEqual(dec.read_bytes(), content)

    def test_small_file_round_trip_direct_hex_key(self):
        src = self.work_path / "data.bin"
        enc = self.work_path / "data.bin.enc"
        dec = self.work_path / "data_dec.bin"

        content = b"\x00\xFF" * 500
        src.write_bytes(content)

        raw_hex = generate_random_aes_key()
        self.service.encrypt_file(src, enc, raw_hex)
        self.service.decrypt_file(enc, dec, raw_hex)
        self.assertEqual(dec.read_bytes(), content)

    def test_empty_file_round_trip(self):
        src = self.work_path / "empty.bin"
        enc = self.work_path / "empty.bin.enc"
        dec = self.work_path / "empty_dec.bin"

        src.write_bytes(b"")
        self.service.encrypt_file(src, enc, "passphrase123Kuat!")
        self.assertTrue(enc.exists())

        self.service.decrypt_file(enc, dec, "passphrase123Kuat!")
        self.assertEqual(dec.read_bytes(), b"")

    def test_binary_multi_chunk_large_file_round_trip(self):
        src = self.work_path / "dataset.dat"
        enc = self.work_path / "dataset.dat.enc"
        dec = self.work_path / "dataset_dec.dat"

        # 160 KB with 32 KB chunk → 5 full chunks
        data = secrets.token_bytes(160 * 1024)
        src.write_bytes(data)

        raw_hex = generate_random_aes_key()
        self.service.encrypt_file(src, enc, raw_hex, chunk_size=32 * 1024)
        self.service.decrypt_file(enc, dec, raw_hex)
        self.assertEqual(dec.read_bytes(), data)

    def test_wrong_key_fails_and_no_plaintext_file(self):
        src = self.work_path / "secret.txt"
        enc = self.work_path / "secret.txt.enc"
        dec = self.work_path / "secret_dec.txt"

        src.write_bytes(b"Data rahasia penting.")
        self.service.encrypt_file(src, enc, "PassphraseBenar123!")

        with self.assertRaises(CryptoOperationError):
            self.service.decrypt_file(enc, dec, "PassphraseSalah999!")

        self.assertFalse(dec.exists())
        self.assertEqual(list(self.work_path.glob("*.tmp*")), [])

    def test_tampered_ciphertext_fails_and_cleans_up(self):
        src = self.work_path / "data.txt"
        enc = self.work_path / "data.txt.enc"
        dec = self.work_path / "data_dec.txt"

        src.write_bytes(b"Data yang akan dimodifikasi di tengah.")
        self.service.encrypt_file(src, enc, "Passphrase123Kuat")

        # Tamper one byte in ciphertext payload (after 48-byte header + 5-byte chunk header)
        enc_bytes = bytearray(enc.read_bytes())
        enc_bytes[48 + 5 + 2] ^= 0xFF
        enc.write_bytes(enc_bytes)

        with self.assertRaises(CryptoOperationError):
            self.service.decrypt_file(enc, dec, "Passphrase123Kuat")

        self.assertFalse(dec.exists())
        self.assertEqual(list(self.work_path.glob("*.tmp*")), [])

    def test_truncated_file_fails_and_cleans_up(self):
        src = self.work_path / "multi.dat"
        enc = self.work_path / "multi.dat.enc"
        dec = self.work_path / "multi_dec.dat"

        # 5-chunk file; truncate to remove last chunk entirely
        src.write_bytes(secrets.token_bytes(64 * 1024))
        self.service.encrypt_file(src, enc, "Passphrase123Kuat", chunk_size=8 * 1024)

        full_len = enc.stat().st_size
        enc.write_bytes(enc.read_bytes()[: full_len - 1000])

        with self.assertRaises(CryptoOperationError):
            self.service.decrypt_file(enc, dec, "Passphrase123Kuat")

        self.assertFalse(dec.exists())
        self.assertEqual(list(self.work_path.glob("*.tmp*")), [])

    def test_appended_data_fails_and_cleans_up(self):
        src = self.work_path / "file.dat"
        enc = self.work_path / "file.dat.enc"
        dec = self.work_path / "file_dec.dat"

        src.write_bytes(b"File utuh.")
        self.service.encrypt_file(src, enc, "Passphrase123Kuat")

        with open(enc, "ab") as f:
            f.write(b"MALICIOUS_EXTRA_BYTES")

        with self.assertRaises(CryptoOperationError):
            self.service.decrypt_file(enc, dec, "Passphrase123Kuat")

        self.assertFalse(dec.exists())

    def test_validation_errors_before_any_crypto(self):
        src = self.work_path / "test.txt"
        src.write_bytes(b"content")

        with self.assertRaises(ValidationError):
            self.service.encrypt_file(self.work_path / "not_found.txt", self.work_path / "out.enc", "key123!")

        with self.assertRaises(ValidationError):
            self.service.encrypt_file(src, src, "key123!")

        with self.assertRaises(ValidationError):
            self.service.encrypt_file(src, self.work_path / "out.enc", "")

    def test_invalid_chunk_flag_in_encrypted_file_rejected(self):
        """Craft a file whose chunk flag is 2 (invalid); decryption must reject it."""
        src = self.work_path / "craft_flag.txt"
        enc = self.work_path / "craft_flag.enc"
        dec = self.work_path / "craft_flag_dec.txt"

        src.write_bytes(b"Content to craft.")
        self.service.encrypt_file(src, enc, "PassKuat123!")

        enc_bytes = bytearray(enc.read_bytes())
        # Chunk header starts at byte 48 (header size).
        # Format ">IB" → bytes 48-51 = ct_len, byte 52 = is_last flag.
        flag_offset = 48 + 4  # offset of the is_last byte in chunk header
        enc_bytes[flag_offset] = 2  # invalid: neither 0 nor 1
        enc.write_bytes(enc_bytes)

        with self.assertRaises(ValidationError):
            self.service.decrypt_file(enc, dec, "PassKuat123!")

        self.assertFalse(dec.exists())

    def test_pbkdf2_iterations_outside_bounds_rejected_at_decrypt(self):
        """Craft a file header with PBKDF2 iterations below minimum; decrypt must reject before KDF."""
        src = self.work_path / "craft_iter.txt"
        enc = self.work_path / "craft_iter.enc"
        dec = self.work_path / "craft_iter_dec.txt"

        src.write_bytes(b"Some content.")
        self.service.encrypt_file(src, enc, "PassKuat123!")

        # Read and modify the iterations field in the header (offset within struct):
        # Format ">8sHHI..." → magic(8) + version(2) + kdf_id(2) + iterations(4) → offset 12
        enc_bytes = bytearray(enc.read_bytes())
        import struct as _struct
        iterations_offset = 8 + 2 + 2  # = 12
        # Write a too-small iterations value (e.g., 1000) in big-endian uint32
        _struct.pack_into(">I", enc_bytes, iterations_offset, 1000)
        enc.write_bytes(enc_bytes)

        with self.assertRaises(ValidationError):
            self.service.decrypt_file(enc, dec, "PassKuat123!")

        self.assertFalse(dec.exists())


if __name__ == "__main__":
    unittest.main()
