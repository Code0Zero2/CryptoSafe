"""Application service for encrypted contract notes."""

from cryptosafe.common.errors import ValidationError
from cryptosafe.crypto.text_crypto_service import TextCryptoService
from cryptosafe.database.encrypted_message_repository import EncryptedMessageRepository


class EncryptedMessageService:
    """Coordinates text encryption and encrypted-message persistence."""

    def __init__(
        self,
        repository: EncryptedMessageRepository,
        crypto_service: TextCryptoService | None = None,
    ):
        self._repository = repository
        self._crypto_service = crypto_service or TextCryptoService()

    def create_encrypted_message(
        self,
        contract_id: int,
        user_id: int,
        content_type: str,
        label: str,
        plaintext: str,
        vigenere_key: str,
        aes_key_material: str,
    ):
        """Encrypt plaintext and persist only its ciphertext."""
        if not isinstance(plaintext, str) or not plaintext.strip():
            raise ValidationError("Isi catatan tidak boleh kosong.")

        ciphertext = self._crypto_service.encrypt(
            plaintext=plaintext,
            vigenere_key=vigenere_key,
            aes_key_material=aes_key_material,
        )

        return self._repository.create_message(
            contract_id=contract_id,
            user_id=user_id,
            content_type=content_type,
            label=label,
            ciphertext=ciphertext,
        )

    def get_decrypted_message(
        self,
        message_id: int,
        user_id: int,
        vigenere_key: str,
        aes_key_material: str,
    ):
        """Retrieve an owned message and decrypt its ciphertext."""
        message = self._repository.get_by_id(message_id, user_id)

        if message is None:
            raise ValidationError("Catatan tidak ditemukan atau akses ditolak.")

        plaintext = self._crypto_service.decrypt(
            envelope_str=message.ciphertext,
            vigenere_key=vigenere_key,
            aes_key_material=aes_key_material,
        )

        return message, plaintext

    def list_by_contract(self, contract_id: int, user_id: int):
        """List encrypted-message records belonging to a user's contract."""
        return self._repository.list_by_contract(contract_id, user_id)

    def update_encrypted_message(
        self,
        message_id: int,
        user_id: int,
        content_type: str,
        label: str,
        plaintext: str,
        vigenere_key: str,
        aes_key_material: str,
    ):
        """Encrypt updated plaintext before replacing the stored ciphertext."""
        if not isinstance(plaintext, str) or not plaintext.strip():
            raise ValidationError("Isi catatan tidak boleh kosong.")

        ciphertext = self._crypto_service.encrypt(
            plaintext=plaintext,
            vigenere_key=vigenere_key,
            aes_key_material=aes_key_material,
        )

        return self._repository.update_message(
            message_id=message_id,
            user_id=user_id,
            content_type=content_type,
            label=label,
            ciphertext=ciphertext,
        )

    def delete_message(self, message_id: int, user_id: int):
        """Delete an encrypted message belonging to the specified user."""
        return self._repository.delete_message(message_id, user_id)
