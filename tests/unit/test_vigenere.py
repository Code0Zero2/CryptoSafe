import sys
import unittest
from pathlib import Path

src_dir = Path(__file__).resolve().parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from cryptosafe.crypto.vigenere import (
    vigenere_encrypt,
    vigenere_decrypt,
    clean_key,
)
from cryptosafe.common.errors import ValidationError


class TestVigenereCipher(unittest.TestCase):
    def test_known_vector_uppercase(self):
        plaintext = "ATTACKATDAWN"
        key = "LEMON"
        expected = "LXFOPVEFRNHR"
        self.assertEqual(vigenere_encrypt(plaintext, key), expected)
        self.assertEqual(vigenere_decrypt(expected, key), plaintext)

    def test_case_preservation(self):
        plaintext = "Attack At Dawn!"
        key = "lemon"
        encrypted = vigenere_encrypt(plaintext, key)
        self.assertEqual(encrypted, "Lxfopv Ef Rnhr!")
        decrypted = vigenere_decrypt(encrypted, key)
        self.assertEqual(decrypted, plaintext)

    def test_non_alphabetic_characters_and_spacing(self):
        plaintext = "Hello, World! 123 @#$ \n\t Selamat Pagi: 2026."
        key = "KUNCI"
        encrypted = vigenere_encrypt(plaintext, key)
        self.assertNotEqual(encrypted, plaintext)
        decrypted = vigenere_decrypt(encrypted, key)
        self.assertEqual(decrypted, plaintext)

    def test_unicode_character_preservation(self):
        plaintext = "Kriptografi 🔒 aman & rahasia: naïve café façade."
        key = "SECRET"
        encrypted = vigenere_encrypt(plaintext, key)
        decrypted = vigenere_decrypt(encrypted, key)
        self.assertEqual(decrypted, plaintext)

    def test_empty_plaintext(self):
        key = "KEYWORD"
        self.assertEqual(vigenere_encrypt("", key), "")
        self.assertEqual(vigenere_decrypt("", key), "")

    def test_clean_key_validation(self):
        self.assertEqual(clean_key("secret"), "SECRET")
        self.assertEqual(clean_key("  SECRET  "), "SECRET")

        with self.assertRaises(ValidationError):
            clean_key("")

        with self.assertRaises(ValidationError):
            clean_key("   ")

        with self.assertRaises(ValidationError):
            clean_key("12345")

        with self.assertRaises(ValidationError):
            clean_key("!@#$%^&*")

        with self.assertRaises(ValidationError):
            vigenere_encrypt("Hello", "")

        with self.assertRaises(ValidationError):
            vigenere_decrypt("Rijvs", "123")


if __name__ == "__main__":
    unittest.main()
