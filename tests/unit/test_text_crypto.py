import json
import sys
import unittest
from pathlib import Path

src_dir = Path(__file__).resolve().parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from cryptosafe.crypto.key_manager import (
    DEFAULT_PBKDF2_ITERATIONS,
    DEFAULT_VIGENERE_KEY_LENGTH,
    SALT_LENGTH_BYTES,
    KDF_PBKDF2,
    KDF_DIRECT,
    generate_random_aes_key,
    generate_vigenere_key,
    generate_super_encryption_keys,
    generate_salt,
    is_direct_hex_key,
    derive_key_from_passphrase,
    resolve_encryption_key,
    resolve_decryption_key,
    resolve_aes_key,
)
from cryptosafe.crypto.aes_gcm import (
    aes_gcm_encrypt,
    aes_gcm_decrypt,
)
from cryptosafe.crypto.text_envelope import (
    serialize_text_envelope,
    deserialize_text_envelope,
    ENVELOPE_MAGIC,
    ENVELOPE_VERSION,
    ALGORITHM_IDENTIFIER,
    TextEnvelope,
)
from cryptosafe.crypto.text_crypto_service import TextCryptoService
from cryptosafe.common.errors import ValidationError, CryptoOperationError


class TestKeyManager(unittest.TestCase):
    def test_default_pbkdf2_iterations_is_600000(self):
        self.assertEqual(DEFAULT_PBKDF2_ITERATIONS, 600_000)

    def test_derive_key_from_passphrase_deterministic(self):
        salt = b"0123456789abcdef"
        k1 = derive_key_from_passphrase("mypassword", salt, iterations=1000)
        k2 = derive_key_from_passphrase("mypassword", salt, iterations=1000)
        self.assertEqual(len(k1), 32)
        self.assertEqual(k1, k2)

        # Different salt produces different key
        diff_salt = b"fedcba9876543210"
        k3 = derive_key_from_passphrase("mypassword", diff_salt, iterations=1000)
        self.assertNotEqual(k1, k3)

    def test_resolve_encryption_key_passphrase(self):
        key, kdf, salt, iters = resolve_encryption_key("strong-passphrase")
        self.assertEqual(len(key), 32)
        self.assertEqual(kdf, KDF_PBKDF2)
        self.assertEqual(len(salt), SALT_LENGTH_BYTES)
        self.assertEqual(iters, 600_000)

    def test_resolve_encryption_key_direct_hex(self):
        hex_key = generate_random_aes_key()
        key, kdf, salt, iters = resolve_encryption_key(hex_key)
        self.assertEqual(key, bytes.fromhex(hex_key))
        self.assertEqual(kdf, KDF_DIRECT)
        self.assertEqual(salt, b"")
        self.assertIsNone(iters)

    def test_resolve_decryption_key_direct_hex_requires_64_hex(self):
        hex_key = generate_random_aes_key()
        resolved = resolve_decryption_key(hex_key, KDF_DIRECT, b"")
        self.assertEqual(resolved, bytes.fromhex(hex_key))

        with self.assertRaises(ValidationError):
            resolve_decryption_key("not-a-64-hex-key", KDF_DIRECT, b"")

    def test_resolve_decryption_key_pbkdf2_reconstructs_with_iterations(self):
        salt = b"0123456789abcdef"
        iters = 5000
        expected = derive_key_from_passphrase("pass", salt, iters)
        resolved = resolve_decryption_key("pass", KDF_PBKDF2, salt, iters)
        self.assertEqual(resolved, expected)

    def test_resolve_aes_key_compatibility_helper(self):
        hex_key = generate_random_aes_key()
        self.assertEqual(resolve_aes_key(hex_key), bytes.fromhex(hex_key))
        salt = b"0123456789abcdef"
        self.assertEqual(len(resolve_aes_key("passphrase", salt, iterations=1000)), 32)

    def test_invalid_key_input(self):
        with self.assertRaises(ValidationError):
            resolve_encryption_key("")
        with self.assertRaises(ValidationError):
            resolve_encryption_key("   ")

    def test_generate_vigenere_key(self):
        # Default length 16
        key = generate_vigenere_key()
        self.assertEqual(len(key), 16)
        self.assertTrue(key.isalpha())
        self.assertTrue(key.isupper())

        # Custom length
        key24 = generate_vigenere_key(length=24)
        self.assertEqual(len(key24), 24)
        self.assertTrue(key24.isalpha())
        self.assertTrue(key24.isupper())

        # Randomness: two consecutive keys should not be equal
        key_b = generate_vigenere_key()
        self.assertNotEqual(key, key_b)

        # Invalid length
        with self.assertRaises(ValidationError):
            generate_vigenere_key(0)
        with self.assertRaises(ValidationError):
            generate_vigenere_key(-5)

    def test_generate_super_encryption_keys(self):
        vig_key, aes_key = generate_super_encryption_keys()
        self.assertEqual(len(vig_key), 16)
        self.assertTrue(vig_key.isalpha())
        self.assertTrue(vig_key.isupper())

        self.assertEqual(len(aes_key), 64)
        self.assertTrue(is_direct_hex_key(aes_key))

        # Keys must be distinct
        self.assertNotEqual(vig_key, aes_key)

        # Randomness across calls
        vig_key2, aes_key2 = generate_super_encryption_keys()
        self.assertNotEqual(vig_key, vig_key2)
        self.assertNotEqual(aes_key, aes_key2)


class TestAesGcm(unittest.TestCase):
    def setUp(self):
        hex_key = generate_random_aes_key()
        self.key = bytes.fromhex(hex_key)
        self.plaintext = b"Pesan rahasia super aman."

    def test_encrypt_decrypt_round_trip(self):
        nonce, ciphertext = aes_gcm_encrypt(self.plaintext, self.key)
        self.assertEqual(len(nonce), 12)
        decrypted = aes_gcm_decrypt(ciphertext, self.key, nonce)
        self.assertEqual(decrypted, self.plaintext)

    def test_nonce_uniqueness(self):
        nonce1, ct1 = aes_gcm_encrypt(self.plaintext, self.key)
        nonce2, ct2 = aes_gcm_encrypt(self.plaintext, self.key)
        self.assertNotEqual(nonce1, nonce2)
        self.assertNotEqual(ct1, ct2)

    def test_wrong_key_fails(self):
        nonce, ciphertext = aes_gcm_encrypt(self.plaintext, self.key)
        wrong_key = bytes.fromhex(generate_random_aes_key())
        with self.assertRaises(CryptoOperationError):
            aes_gcm_decrypt(ciphertext, wrong_key, nonce)

    def test_tampered_ciphertext_fails(self):
        nonce, ciphertext = aes_gcm_encrypt(self.plaintext, self.key)
        tampered_ct = bytearray(ciphertext)
        tampered_ct[0] ^= 0x01
        with self.assertRaises(CryptoOperationError):
            aes_gcm_decrypt(bytes(tampered_ct), self.key, nonce)

    def test_tampered_nonce_fails(self):
        nonce, ciphertext = aes_gcm_encrypt(self.plaintext, self.key)
        tampered_nonce = bytearray(nonce)
        tampered_nonce[0] ^= 0x01
        with self.assertRaises(CryptoOperationError):
            aes_gcm_decrypt(ciphertext, self.key, bytes(tampered_nonce))


class TestTextEnvelope(unittest.TestCase):
    def test_serialize_and_deserialize_pbkdf2(self):
        salt = b"0123456789abcdef"
        nonce = b"112233445566"
        ct = b"sample_ciphertext_with_tag_16"
        envelope_str = serialize_text_envelope(
            salt=salt,
            nonce=nonce,
            ciphertext=ct,
            kdf=KDF_PBKDF2,
            iterations=600_000,
        )

        data = json.loads(envelope_str)
        self.assertEqual(data["magic"], ENVELOPE_MAGIC)
        self.assertEqual(data["version"], ENVELOPE_VERSION)
        self.assertEqual(data["algorithm"], ALGORITHM_IDENTIFIER)
        self.assertEqual(data["kdf"], KDF_PBKDF2)
        self.assertEqual(data["iterations"], 600_000)
        self.assertEqual(data["salt"], salt.hex())
        self.assertEqual(data["nonce"], nonce.hex())
        self.assertEqual(data["ciphertext"], ct.hex())

        env = deserialize_text_envelope(envelope_str)
        self.assertEqual(env.algorithm, ALGORITHM_IDENTIFIER)
        self.assertEqual(env.kdf, KDF_PBKDF2)
        self.assertEqual(env.iterations, 600_000)
        self.assertEqual(env.salt, salt)
        self.assertEqual(env.nonce, nonce)
        self.assertEqual(env.ciphertext, ct)

        # Backward compatibility unpacking
        salt_out, nonce_out, ct_out = env
        self.assertEqual(salt_out, salt)
        self.assertEqual(nonce_out, nonce)
        self.assertEqual(ct_out, ct)

    def test_serialize_and_deserialize_direct_hex(self):
        nonce = b"112233445566"
        ct = b"sample_ciphertext_with_tag_16"
        envelope_str = serialize_text_envelope(
            salt=b"",
            nonce=nonce,
            ciphertext=ct,
            kdf=KDF_DIRECT,
            iterations=None,
        )

        data = json.loads(envelope_str)
        self.assertEqual(data["kdf"], KDF_DIRECT)
        self.assertNotIn("iterations", data)
        self.assertEqual(data["salt"], "")

        env = deserialize_text_envelope(envelope_str)
        self.assertEqual(env.kdf, KDF_DIRECT)
        self.assertIsNone(env.iterations)
        self.assertEqual(env.salt, b"")

    def test_invalid_magic_rejected(self):
        bad_json = json.dumps({"magic": "WRONG_MAGIC", "version": 1})
        with self.assertRaises(ValidationError):
            deserialize_text_envelope(bad_json)

    def test_invalid_version_rejected(self):
        bad_json = json.dumps({"magic": ENVELOPE_MAGIC, "version": 999})
        with self.assertRaises(ValidationError):
            deserialize_text_envelope(bad_json)

    def test_invalid_algorithm_rejected(self):
        env_dict = {
            "magic": ENVELOPE_MAGIC,
            "version": 1,
            "algorithm": "DES_EDE3_CBC",
            "kdf": KDF_PBKDF2,
            "iterations": 1000,
            "salt": "0123456789abcdef0123456789abcdef",
            "nonce": "11223344556677889900aabb",
            "ciphertext": "00112233445566778899aabbccddeeff",
        }
        with self.assertRaises(ValidationError):
            deserialize_text_envelope(json.dumps(env_dict))

    def test_invalid_kdf_rejected(self):
        env_dict = {
            "magic": ENVELOPE_MAGIC,
            "version": 1,
            "algorithm": ALGORITHM_IDENTIFIER,
            "kdf": "UNSUPPORTED_KDF",
            "iterations": 1000,
            "salt": "0123456789abcdef0123456789abcdef",
            "nonce": "11223344556677889900aabb",
            "ciphertext": "00112233445566778899aabbccddeeff",
        }
        with self.assertRaises(ValidationError):
            deserialize_text_envelope(json.dumps(env_dict))

    def test_invalid_salt_rejected(self):
        # Non-hex salt
        env_dict = {
            "magic": ENVELOPE_MAGIC,
            "version": 1,
            "algorithm": ALGORITHM_IDENTIFIER,
            "kdf": KDF_PBKDF2,
            "iterations": 1000,
            "salt": "invalid-hex-salt!",
            "nonce": "11223344556677889900aabb",
            "ciphertext": "00112233445566778899aabbccddeeff",
        }
        with self.assertRaises(ValidationError):
            deserialize_text_envelope(json.dumps(env_dict))

        # Too short salt for PBKDF2 (< 16 bytes = < 32 hex chars)
        env_dict["salt"] = "01020304"
        with self.assertRaises(ValidationError):
            deserialize_text_envelope(json.dumps(env_dict))

    def test_invalid_iterations_rejected(self):
        env_dict = {
            "magic": ENVELOPE_MAGIC,
            "version": 1,
            "algorithm": ALGORITHM_IDENTIFIER,
            "kdf": KDF_PBKDF2,
            "iterations": 0,
            "salt": "0123456789abcdef0123456789abcdef",
            "nonce": "11223344556677889900aabb",
            "ciphertext": "00112233445566778899aabbccddeeff",
        }
        with self.assertRaises(ValidationError):
            deserialize_text_envelope(json.dumps(env_dict))

        del env_dict["iterations"]
        with self.assertRaises(ValidationError):
            deserialize_text_envelope(json.dumps(env_dict))

    def test_invalid_nonce_rejected(self):
        env_dict = {
            "magic": ENVELOPE_MAGIC,
            "version": 1,
            "algorithm": ALGORITHM_IDENTIFIER,
            "kdf": KDF_PBKDF2,
            "iterations": 1000,
            "salt": "0123456789abcdef0123456789abcdef",
            "nonce": "1122",  # Only 2 bytes instead of 12
            "ciphertext": "00112233445566778899aabbccddeeff",
        }
        with self.assertRaises(ValidationError):
            deserialize_text_envelope(json.dumps(env_dict))

    def test_invalid_ciphertext_rejected(self):
        env_dict = {
            "magic": ENVELOPE_MAGIC,
            "version": 1,
            "algorithm": ALGORITHM_IDENTIFIER,
            "kdf": KDF_PBKDF2,
            "iterations": 1000,
            "salt": "0123456789abcdef0123456789abcdef",
            "nonce": "11223344556677889900aabb",
            "ciphertext": "1122",  # Less than 16 bytes
        }
        with self.assertRaises(ValidationError):
            deserialize_text_envelope(json.dumps(env_dict))


class TestTextCryptoService(unittest.TestCase):
    def setUp(self):
        self.service = TextCryptoService()
        self.plaintext = "Pesan rahasia CRYPTOSAFE 2026! @#$."
        self.vig_key = "LEMON"
        self.passphrase = "KunciRahasiaAES256SuperKuat"

    def test_passphrase_encryption_decryption_round_trip(self):
        env_str = self.service.encrypt(self.plaintext, self.vig_key, self.passphrase)
        env_data = json.loads(env_str)
        self.assertEqual(env_data["kdf"], KDF_PBKDF2)
        self.assertEqual(env_data["iterations"], 600_000)
        self.assertEqual(len(env_data["salt"]), 32)  # 16 bytes in hex

        recovered = self.service.decrypt(env_str, self.vig_key, self.passphrase)
        self.assertEqual(recovered, self.plaintext)

    def test_direct_random_aes_key_encryption_decryption_round_trip(self):
        raw_hex_key = generate_random_aes_key()
        env_str = self.service.encrypt(self.plaintext, self.vig_key, raw_hex_key)
        env_data = json.loads(env_str)
        self.assertEqual(env_data["kdf"], KDF_DIRECT)
        self.assertEqual(env_data["salt"], "")
        self.assertNotIn("iterations", env_data)

        recovered = self.service.decrypt(env_str, self.vig_key, raw_hex_key)
        self.assertEqual(recovered, self.plaintext)

    def test_stored_pbkdf2_parameters_reused_during_decryption(self):
        # Encrypt with custom iterations
        custom_iters = 2500
        env_str = self.service.encrypt(
            self.plaintext, self.vig_key, self.passphrase, iterations=custom_iters
        )
        env_data = json.loads(env_str)
        self.assertEqual(env_data["iterations"], custom_iters)

        # Standard decrypt() automatically reads and uses custom_iters
        recovered = self.service.decrypt(env_str, self.vig_key, self.passphrase)
        self.assertEqual(recovered, self.plaintext)

        # If iterations in envelope metadata are altered, key derivation differs and tag verification fails
        env_data["iterations"] = custom_iters + 1
        tampered_env = json.dumps(env_data)
        with self.assertRaises(CryptoOperationError):
            self.service.decrypt(tampered_env, self.vig_key, self.passphrase)

    def test_nonce_uniqueness_super_encryption(self):
        env1 = self.service.encrypt(self.plaintext, self.vig_key, self.passphrase)
        env2 = self.service.encrypt(self.plaintext, self.vig_key, self.passphrase)
        self.assertNotEqual(env1, env2)

    def test_decrypt_wrong_aes_key_fails(self):
        env_str = self.service.encrypt(self.plaintext, self.vig_key, self.passphrase)
        with self.assertRaises(CryptoOperationError):
            self.service.decrypt(env_str, self.vig_key, "WrongPassword123")

    def test_decrypt_wrong_vigenere_key_produces_scrambled_text(self):
        env_str = self.service.encrypt(self.plaintext, self.vig_key, self.passphrase)
        recovered = self.service.decrypt(env_str, "WRONGKEY", self.passphrase)
        self.assertNotEqual(recovered, self.plaintext)

    def test_modified_ciphertext_fails_decryption(self):
        env_str = self.service.encrypt(self.plaintext, self.vig_key, self.passphrase)
        envelope_data = json.loads(env_str)
        ct = envelope_data["ciphertext"]
        tampered_ct = ("0" if ct[0] != "0" else "1") + ct[1:]
        envelope_data["ciphertext"] = tampered_ct
        tampered_json = json.dumps(envelope_data)

        with self.assertRaises(CryptoOperationError):
            self.service.decrypt(tampered_json, self.vig_key, self.passphrase)

    def test_empty_plaintext(self):
        res = self.service.encrypt("", self.vig_key, self.passphrase)
        recovered = self.service.decrypt(res, self.vig_key, self.passphrase)
        self.assertEqual(recovered, "")

    def test_auto_generated_keys_encryption_decryption_round_trip(self):
        vig_key, aes_key = generate_super_encryption_keys()
        self.assertNotEqual(vig_key, aes_key)

        env_str = self.service.encrypt(self.plaintext, vig_key, aes_key)
        env_data = json.loads(env_str)
        self.assertEqual(env_data["kdf"], KDF_DIRECT)

        # Successful decryption with the same keys
        recovered = self.service.decrypt(env_str, vig_key, aes_key)
        self.assertEqual(recovered, self.plaintext)

        # Wrong AES key fails AEAD authentication
        with self.assertRaises(CryptoOperationError):
            self.service.decrypt(env_str, vig_key, generate_random_aes_key())

        # Wrong Vigenere key returns scrambled plaintext
        scrambled = self.service.decrypt(env_str, generate_vigenere_key(), aes_key)
        self.assertNotEqual(scrambled, self.plaintext)

    def test_service_generate_keys_convenience_method(self):
        vig_key, aes_key = self.service.generate_keys()
        self.assertEqual(len(vig_key), 16)
        self.assertEqual(len(aes_key), 64)
        self.assertNotEqual(vig_key, aes_key)


if __name__ == "__main__":
    unittest.main()
