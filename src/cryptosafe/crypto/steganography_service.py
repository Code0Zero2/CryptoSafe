"""LSB Steganography service for embedding and extracting encrypted payloads in PNG images."""

import logging
import struct
from pathlib import Path
import numpy as np
from PIL import Image

from cryptosafe.common.errors import CryptoOperationError, ValidationError
from cryptosafe.crypto.text_crypto_service import TextCryptoService

logger = logging.getLogger("cryptosafe.crypto.stego")

MAGIC_BYTES = b"CSLSB\x01"  # CryptoSafe LSB v1 header
HEADER_LENGTH_BYTES = len(MAGIC_BYTES) + 4  # 6 + 4 = 10 bytes (80 bits)


class SteganographyService:
    """Service embedding and extracting AES-GCM + Vigenère encrypted payloads into PNG images via LSB."""

    def __init__(self, text_crypto_service: TextCryptoService | None = None):
        self._text_crypto = text_crypto_service or TextCryptoService()

    def generate_keys(self) -> tuple[str, str]:
        """Generate distinct cryptographically secure Vigenère and AES keys."""
        return self._text_crypto.generate_keys()

    def get_image_capacity(self, image_path: str | Path) -> int:
        """Calculate maximum payload capacity in bytes for a given PNG image.

        Capacity = (Width * Height * 3) // 8 - HEADER_LENGTH_BYTES
        """
        path = Path(image_path)
        if not path.is_file():
            raise ValidationError(f"Berkas citra tidak ditemukan: {path}")

        try:
            with Image.open(path) as img:
                if img.format != "PNG":
                    raise ValidationError("Berkas citra harus berformat PNG.")
                if img.mode not in ("RGB", "RGBA"):
                    raise ValidationError(
                        f"Mode citra '{img.mode}' tidak didukung. Hanya mode RGB dan RGBA yang didukung."
                    )
                w, h = img.size
                total_rgb_bytes = (w * h * 3) // 8
                return max(0, total_rgb_bytes - HEADER_LENGTH_BYTES)
        except (ValidationError, CryptoOperationError):
            raise
        except Exception as err:
            raise ValidationError(f"Gagal membaca berkas citra: {err}")

    def embed_payload(
        self,
        image_path: str | Path,
        output_path: str | Path,
        payload: bytes,
    ) -> Path:
        """Embed raw payload bytes into a PNG image using LSB on RGB channels only.

        Original image is never modified. Output is always written to output_path.
        """
        src = Path(image_path).resolve()
        dst = Path(output_path).resolve()

        if not src.is_file():
            raise ValidationError(f"Berkas citra sumber tidak ditemukan: {src}")

        if dst.is_dir():
            raise ValidationError(f"Jalur berkas output tidak boleh berupa direktori: {dst}")

        is_same = (src == dst)
        if not is_same and dst.exists():
            try:
                is_same = src.samefile(dst)
            except OSError:
                is_same = False

        if is_same:
            raise ValidationError("Jalur berkas output tidak boleh sama dengan berkas citra asli.")

        if not isinstance(payload, (bytes, bytearray)) or len(payload) == 0:
            raise ValidationError("Payload tidak boleh kosong.")

        try:
            with Image.open(src) as img:
                if img.format != "PNG":
                    raise ValidationError("Berkas citra harus berformat PNG.")
                if img.mode not in ("RGB", "RGBA"):
                    raise ValidationError(
                        f"Mode citra '{img.mode}' tidak didukung. Hanya mode RGB dan RGBA yang didukung."
                    )

                w, h = img.size
                available_bits = w * h * 3
                available_bytes = available_bits // 8

                # Frame payload: MAGIC + length (4-byte big-endian) + payload
                header = MAGIC_BYTES + struct.pack(">I", len(payload))
                framed_data = header + payload

                required_bits = len(framed_data) * 8
                if required_bits > available_bits:
                    max_payload_cap = max(0, available_bytes - HEADER_LENGTH_BYTES)
                    raise ValidationError(
                        f"Ukuran payload ({len(payload)} byte) melebihi kapasitas citra ({max_payload_cap} byte)."
                    )

                # Load image array
                img_array = np.array(img, dtype=np.uint8)

                # Extract RGB channels (channels 0, 1, 2)
                # Channel 3 (Alpha), if present, is completely untouched!
                flat_rgb = img_array[:, :, :3].flatten()

                # Convert framed bytes into bit array (0 or 1)
                data_bytes_array = np.frombuffer(framed_data, dtype=np.uint8)
                bits = np.unpackbits(data_bytes_array)

                # Clear LSB and embed bit
                flat_rgb[: len(bits)] = (flat_rgb[: len(bits)] & 0xFE) | bits
                img_array[:, :, :3] = flat_rgb.reshape(h, w, 3)

                # Create output directory if needed
                dst.parent.mkdir(parents=True, exist_ok=True)

                # Construct and save stego image losslessly as PNG
                stego_img = Image.fromarray(img_array, mode=img.mode)
                stego_img.save(dst, format="PNG")

                logger.info(
                    "Successfully embedded %d bytes payload into %s (Dimensions: %dx%d, Mode: %s)",
                    len(payload),
                    dst.name,
                    w,
                    h,
                    img.mode,
                )
                return dst

        except (ValidationError, CryptoOperationError):
            raise
        except Exception as err:
            raise CryptoOperationError(f"Gagal melakukan embedding steganografi: {err}")

    def extract_payload(self, image_path: str | Path) -> bytes:
        """Extract raw payload bytes from a stego PNG image.

        Raises CryptoOperationError if magic header is missing or payload is corrupted.
        """
        src = Path(image_path).resolve()
        if not src.is_file():
            raise ValidationError(f"Berkas citra tidak ditemukan: {src}")

        try:
            with Image.open(src) as img:
                if img.format != "PNG":
                    raise ValidationError("Berkas citra harus berformat PNG.")
                if img.mode not in ("RGB", "RGBA"):
                    raise ValidationError(
                        f"Mode citra '{img.mode}' tidak didukung. Hanya mode RGB dan RGBA yang didukung."
                    )

                img_array = np.array(img, dtype=np.uint8)
                flat_rgb = img_array[:, :, :3].reshape(-1)

                # Need at least HEADER_LENGTH_BYTES (80 bits) to inspect header
                header_bits_count = HEADER_LENGTH_BYTES * 8
                if len(flat_rgb) < header_bits_count:
                    raise CryptoOperationError("Ukuran citra terlalu kecil untuk memuat header steganografi.")

                # Extract first 80 bits for header
                header_bits = flat_rgb[:header_bits_count] & 1
                header_bytes = np.packbits(header_bits).tobytes()

                magic = header_bytes[: len(MAGIC_BYTES)]
                if magic != MAGIC_BYTES:
                    raise CryptoOperationError(
                        "Citra tidak mengandung data steganografi CryptoSafe yang valid."
                    )

                payload_len = struct.unpack(">I", header_bytes[len(MAGIC_BYTES) : HEADER_LENGTH_BYTES])[0]
                total_bits_needed = (HEADER_LENGTH_BYTES + payload_len) * 8

                if payload_len <= 0 or total_bits_needed > len(flat_rgb):
                    raise CryptoOperationError(
                        f"Panjang payload steganografi ({payload_len} byte) tidak valid atau melebihi kapasitas citra."
                    )

                # Extract payload bits
                payload_bits = flat_rgb[header_bits_count:total_bits_needed] & 1
                payload_bytes = np.packbits(payload_bits).tobytes()

                logger.info(
                    "Successfully extracted %d bytes payload from %s",
                    len(payload_bytes),
                    src.name,
                )
                return payload_bytes

        except (ValidationError, CryptoOperationError):
            raise
        except Exception as err:
            raise CryptoOperationError(f"Gagal mengekstrak data steganografi dari citra: {err}")

    def embed_message(
        self,
        image_path: str | Path,
        output_path: str | Path,
        plaintext: str,
        vigenere_key: str,
        aes_key_material: str,
    ) -> Path:
        """Encrypt plaintext with TextCryptoService (Vigenère + AES-GCM) and embed into PNG."""
        if not plaintext or not plaintext.strip():
            raise ValidationError("Pesan teks yang ingin disisipkan tidak boleh kosong.")

        # Super-encrypt plaintext using TextCryptoService
        envelope_str = self._text_crypto.encrypt(
            plaintext=plaintext,
            vigenere_key=vigenere_key,
            aes_key_material=aes_key_material,
        )
        payload_bytes = envelope_str.encode("utf-8")

        return self.embed_payload(
            image_path=image_path,
            output_path=output_path,
            payload=payload_bytes,
        )

    def extract_message(
        self,
        image_path: str | Path,
        vigenere_key: str,
        aes_key_material: str,
    ) -> str:
        """Extract encrypted payload from PNG and decrypt with TextCryptoService."""
        payload_bytes = self.extract_payload(image_path)

        try:
            envelope_str = payload_bytes.decode("utf-8")
        except UnicodeDecodeError as err:
            raise CryptoOperationError(f"Payload steganografi rusak atau bukan teks UTF-8 valid: {err}")

        # Decrypt envelope; raises CryptoOperationError if AES-GCM tag verification fails
        return self._text_crypto.decrypt(
            envelope_str=envelope_str,
            vigenere_key=vigenere_key,
            aes_key_material=aes_key_material,
        )
