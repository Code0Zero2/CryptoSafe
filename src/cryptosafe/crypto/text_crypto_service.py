"""Super-encryption text service combining Vigenère and AES-256-GCM."""

import logging
from cryptosafe.common.errors import CryptoOperationError, ValidationError
from cryptosafe.crypto.vigenere import vigenere_encrypt, vigenere_decrypt
from cryptosafe.crypto.key_manager import (
    DEFAULT_PBKDF2_ITERATIONS,
    DEFAULT_VIGENERE_KEY_LENGTH,
    generate_super_encryption_keys,
    resolve_encryption_key,
    resolve_decryption_key,
)
from cryptosafe.crypto.aes_gcm import aes_gcm_encrypt, aes_gcm_decrypt
from cryptosafe.crypto.text_envelope import serialize_text_envelope, deserialize_text_envelope

logger = logging.getLogger("cryptosafe.crypto.text")


class TextCryptoService:
    """Service orchestrating Vigenère + AES-256-GCM super-encryption for text messages."""

    def generate_keys(
        self,
        vigenere_length: int = DEFAULT_VIGENERE_KEY_LENGTH,
    ) -> tuple[str, str]:
        """Generate distinct cryptographically secure Vigenère and AES keys."""
        return generate_super_encryption_keys(vigenere_length=vigenere_length)

    def encrypt(
        self,
        plaintext: str,
        vigenere_key: str,
        aes_key_material: str,
        iterations: int = DEFAULT_PBKDF2_ITERATIONS,
    ) -> str:
        """Encrypt text using sequential Vigenère and AES-256-GCM.

        Returns:
            str: Structured JSON envelope string containing ciphertext and metadata.
        """
        if not isinstance(plaintext, str):
            raise ValidationError("Plaintext harus berupa string teks.")

        # Step 1: Classical educational layer (Vigenère)
        vigenere_transformed = vigenere_encrypt(plaintext, vigenere_key)

        # Step 2: Prepare key, salt, and KDF for modern AEAD layer
        aes_key, kdf, salt, used_iterations = resolve_encryption_key(
            aes_key_material, iterations=iterations
        )

        # Step 3: Modern AEAD layer (AES-256-GCM) with fresh 96-bit nonce
        plaintext_bytes = vigenere_transformed.encode("utf-8")
        nonce, ciphertext = aes_gcm_encrypt(plaintext_bytes, aes_key)

        logger.info(
            "Text super-encryption completed successfully (length=%d, kdf=%s).",
            len(plaintext),
            kdf,
        )

        # Step 4: Serialize envelope
        return serialize_text_envelope(
            salt=salt,
            nonce=nonce,
            ciphertext=ciphertext,
            kdf=kdf,
            iterations=used_iterations,
        )

    def decrypt(self, envelope_str: str, vigenere_key: str, aes_key_material: str) -> str:
        """Decrypt text reversing the pipeline: AES-256-GCM authentication/decrypt, then Vigenère inverse.

        Raises:
            ValidationError: If envelope format or keys are invalid.
            CryptoOperationError: If ciphertext integrity check fails (wrong key or tampering).
        """
        # Step 1: Parse and validate envelope
        env = deserialize_text_envelope(envelope_str)

        # Step 2: Resolve AES key using the envelope's KDF, salt, and stored iterations
        aes_key = resolve_decryption_key(
            key_material=aes_key_material,
            kdf=env.kdf,
            salt=env.salt,
            iterations=env.iterations,
        )

        # Step 3: Modern AEAD layer decryption & authentication verification
        # aes_gcm_decrypt raises CryptoOperationError if tag mismatch occurs
        vigenere_bytes = aes_gcm_decrypt(env.ciphertext, aes_key, env.nonce)

        try:
            vigenere_transformed = vigenere_bytes.decode("utf-8")
        except UnicodeDecodeError as err:
            raise CryptoOperationError(f"Gagal mendecode hasil dekripsi teks sebagai UTF-8: {err}")

        # Step 4: Classical educational inverse (Vigenère decrypt)
        plaintext = vigenere_decrypt(vigenere_transformed, vigenere_key)

        logger.info("Text super-decryption completed successfully.")
        return plaintext
