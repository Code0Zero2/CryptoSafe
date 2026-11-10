import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image
import numpy as np

src_dir = Path(__file__).resolve().parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from cryptosafe.crypto.steganography_service import (
    SteganographyService,
    MAGIC_BYTES,
    HEADER_LENGTH_BYTES,
)
from cryptosafe.crypto.text_crypto_service import TextCryptoService
from cryptosafe.common.errors import ValidationError, CryptoOperationError


class TestSteganographyService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.service = SteganographyService()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _create_rgb_image(self, width: int = 100, height: int = 100) -> Path:
        img_path = self.temp_path / f"test_rgb_{width}x{height}.png"
        arr = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
        img = Image.fromarray(arr, mode="RGB")
        img.save(img_path, format="PNG")
        return img_path

    def _create_rgba_image(self, width: int = 100, height: int = 100) -> Path:
        img_path = self.temp_path / f"test_rgba_{width}x{height}.png"
        arr = np.random.randint(0, 256, (height, width, 4), dtype=np.uint8)
        # Ensure alpha has distinctive non-trivial values
        arr[:, :, 3] = np.random.randint(100, 255, (height, width), dtype=np.uint8)
        img = Image.fromarray(arr, mode="RGBA")
        img.save(img_path, format="PNG")
        return img_path

    def test_image_capacity_rgb(self):
        width, height = 64, 64
        img_path = self._create_rgb_image(width, height)
        capacity = self.service.get_image_capacity(img_path)
        expected = (width * height * 3) // 8 - HEADER_LENGTH_BYTES
        self.assertEqual(capacity, expected)

    def test_image_capacity_rgba(self):
        width, height = 64, 64
        img_path = self._create_rgba_image(width, height)
        capacity = self.service.get_image_capacity(img_path)
        # RGBA only uses RGB channels for capacity, alpha is not used
        expected = (width * height * 3) // 8 - HEADER_LENGTH_BYTES
        self.assertEqual(capacity, expected)

    def test_image_capacity_non_png_raises(self):
        jpg_path = self.temp_path / "test.jpg"
        img = Image.new("RGB", (50, 50), color=(255, 0, 0))
        img.save(jpg_path, format="JPEG")
        with self.assertRaises(ValidationError) as ctx:
            self.service.get_image_capacity(jpg_path)
        self.assertIn("berformat PNG", str(ctx.exception))

    def test_image_capacity_grayscale_raises(self):
        gray_path = self.temp_path / "gray.png"
        img = Image.new("L", (50, 50), color=128)
        img.save(gray_path, format="PNG")
        with self.assertRaises(ValidationError) as ctx:
            self.service.get_image_capacity(gray_path)
        self.assertIn("Hanya mode RGB dan RGBA", str(ctx.exception))

    def test_embed_and_extract_payload_raw(self):
        img_path = self._create_rgb_image(80, 80)
        out_path = self.temp_path / "stego_raw.png"
        payload = b"Hello, Steganography Raw Payload Test 12345!"

        self.service.embed_payload(img_path, out_path, payload)
        self.assertTrue(out_path.exists())

        extracted = self.service.extract_payload(out_path)
        self.assertEqual(extracted, payload)

    def test_original_image_unmodified(self):
        img_path = self._create_rgb_image(50, 50)
        out_path = self.temp_path / "stego_out.png"
        payload = b"Payload integrity test"

        with open(img_path, "rb") as f:
            original_hash = hashlib.sha256(f.read()).hexdigest()

        self.service.embed_payload(img_path, out_path, payload)

        with open(img_path, "rb") as f:
            after_hash = hashlib.sha256(f.read()).hexdigest()

        self.assertEqual(original_hash, after_hash)

    def test_alpha_channel_preserved(self):
        img_path = self._create_rgba_image(60, 60)
        out_path = self.temp_path / "stego_rgba.png"
        payload = b"Testing Alpha channel preservation!"

        with Image.open(img_path) as orig_img:
            orig_alpha = np.array(orig_img)[:, :, 3].copy()

        self.service.embed_payload(img_path, out_path, payload)

        with Image.open(out_path) as stego_img:
            stego_arr = np.array(stego_img)
            self.assertEqual(stego_img.mode, "RGBA")
            stego_alpha = stego_arr[:, :, 3]

        np.testing.assert_array_equal(orig_alpha, stego_alpha)

    def test_embed_capacity_exceeded_raises(self):
        # 10x10 RGB = 300 bits = 37 bytes. Capacity = 37 - 10 = 27 bytes.
        img_path = self._create_rgb_image(10, 10)
        out_path = self.temp_path / "stego_overflow.png"
        oversized_payload = b"X" * 100

        with self.assertRaises(ValidationError) as ctx:
            self.service.embed_payload(img_path, out_path, oversized_payload)
        self.assertIn("melebihi kapasitas", str(ctx.exception))

    def test_output_equals_input_raises(self):
        img_path = self._create_rgb_image(50, 50)
        with self.assertRaises(ValidationError) as ctx:
            self.service.embed_payload(img_path, img_path, b"data")
        self.assertIn("tidak boleh sama", str(ctx.exception))

    def test_output_samefile_hardlink_raises(self):
        img_path = self._create_rgb_image(50, 50)
        hardlink_path = self.temp_path / "hardlink.png"
        try:
            import os
            os.link(img_path, hardlink_path)
        except (OSError, NotImplementedError):
            self.skipTest("Filesystem does not support hard links.")

        with self.assertRaises(ValidationError) as ctx:
            self.service.embed_payload(img_path, hardlink_path, b"data")
        self.assertIn("tidak boleh sama", str(ctx.exception))

    def test_output_samefile_relative_path_raises(self):
        img_path = self._create_rgb_image(50, 50)
        import os
        rel_path = os.path.relpath(img_path)
        with self.assertRaises(ValidationError) as ctx:
            self.service.embed_payload(img_path, rel_path, b"data")
        self.assertIn("tidak boleh sama", str(ctx.exception))

    def test_output_is_directory_raises(self):
        img_path = self._create_rgb_image(50, 50)
        with self.assertRaises(ValidationError) as ctx:
            self.service.embed_payload(img_path, self.temp_path, b"data")
        self.assertIn("tidak boleh berupa direktori", str(ctx.exception))

    def test_fake_png_extension_rejected(self):
        fake_png = self.temp_path / "fake.png"
        img = Image.new("RGB", (50, 50), color=(0, 255, 0))
        img.save(fake_png, format="JPEG")
        with self.assertRaises(ValidationError) as ctx:
            self.service.embed_payload(fake_png, self.temp_path / "out.png", b"data")
        self.assertIn("berformat PNG", str(ctx.exception))

    def test_extract_clean_image_raises_crypto_error(self):
        img_path = self._create_rgb_image(50, 50)
        with self.assertRaises(CryptoOperationError) as ctx:
            self.service.extract_payload(img_path)
        self.assertIn("tidak mengandung data steganografi CryptoSafe", str(ctx.exception))

    def test_roundtrip_embed_extract_message_rgb(self):
        img_path = self._create_rgb_image(120, 120)
        out_path = self.temp_path / "stego_msg_rgb.png"
        plaintext = "Pesan rahasia CryptoSafe: Dokumen rahasia disimpan di brankas!"
        vigenere_key = "RAHASIANEGARA"
        aes_key = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"

        result_path = self.service.embed_message(
            image_path=img_path,
            output_path=out_path,
            plaintext=plaintext,
            vigenere_key=vigenere_key,
            aes_key_material=aes_key,
        )
        self.assertEqual(result_path, out_path)
        self.assertTrue(out_path.exists())

        decrypted = self.service.extract_message(
            image_path=out_path,
            vigenere_key=vigenere_key,
            aes_key_material=aes_key,
        )
        self.assertEqual(decrypted, plaintext)

    def test_roundtrip_embed_extract_message_rgba(self):
        img_path = self._create_rgba_image(120, 120)
        out_path = self.temp_path / "stego_msg_rgba.png"
        plaintext = "Pesan rahasia dalam format RGBA dengan transparansi!"
        vigenere_key = "SECRETKEY"
        aes_key = "kuncipassphraseyangkuat123"

        self.service.embed_message(
            image_path=img_path,
            output_path=out_path,
            plaintext=plaintext,
            vigenere_key=vigenere_key,
            aes_key_material=aes_key,
        )

        decrypted = self.service.extract_message(
            image_path=out_path,
            vigenere_key=vigenere_key,
            aes_key_material=aes_key,
        )
        self.assertEqual(decrypted, plaintext)

    def test_extract_with_wrong_vigenere_key_fails(self):
        img_path = self._create_rgb_image(100, 100)
        out_path = self.temp_path / "stego_wrong_vig.png"
        plaintext = "Pesan rahasia!"
        vigenere_key = "CORRECTKEY"
        aes_key = "kuncipassphrase123"

        self.service.embed_message(
            image_path=img_path,
            output_path=out_path,
            plaintext=plaintext,
            vigenere_key=vigenere_key,
            aes_key_material=aes_key,
        )

        # Extraction with wrong Vigenere key produces corrupted plaintext or error
        decrypted = self.service.extract_message(
            image_path=out_path,
            vigenere_key="WRONGKEYXX",
            aes_key_material=aes_key,
        )
        self.assertNotEqual(decrypted, plaintext)

    def test_extract_with_wrong_aes_key_raises(self):
        img_path = self._create_rgb_image(100, 100)
        out_path = self.temp_path / "stego_wrong_aes.png"
        plaintext = "Pesan rahasia!"
        vigenere_key = "CORRECTKEY"
        aes_key = "kuncipassphrase123"

        self.service.embed_message(
            image_path=img_path,
            output_path=out_path,
            plaintext=plaintext,
            vigenere_key=vigenere_key,
            aes_key_material=aes_key,
        )

        with self.assertRaises(CryptoOperationError):
            self.service.extract_message(
                image_path=out_path,
                vigenere_key=vigenere_key,
                aes_key_material="kuncisalah456",
            )

    def test_embed_empty_message_raises(self):
        img_path = self._create_rgb_image(50, 50)
        out_path = self.temp_path / "stego_empty.png"
        with self.assertRaises(ValidationError) as ctx:
            self.service.embed_message(
                image_path=img_path,
                output_path=out_path,
                plaintext="",
                vigenere_key="KEY",
                aes_key_material="AESKEY",
            )
        self.assertIn("tidak boleh kosong", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
