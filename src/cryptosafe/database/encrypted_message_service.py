"""Application service for encrypted contract notes with blockchain audit trail."""

from contextlib import nullcontext
import hashlib
import logging

from cryptosafe.common.errors import ValidationError
from cryptosafe.crypto.blockchain_service import BlockchainService
from cryptosafe.crypto.text_crypto_service import TextCryptoService
from cryptosafe.database.connection import transaction
from cryptosafe.database.encrypted_message_repository import (
    EncryptedMessage,
    EncryptedMessageRepository,
)

logger = logging.getLogger("cryptosafe.encrypted_message_service")


class EncryptedMessageService:
    """Coordinates text encryption, persistence, and blockchain audit trail."""

    def __init__(
        self,
        repository: EncryptedMessageRepository,
        crypto_service: TextCryptoService | None = None,
        blockchain_service: BlockchainService | None = None,
    ):
        self._repository = repository
        self._crypto_service = crypto_service or TextCryptoService()
        self._blockchain_service = blockchain_service
        self._conn = getattr(repository, "conn", None) or getattr(repository, "_conn", None)

    @property
    def repository(self) -> EncryptedMessageRepository:
        """Return the underlying repository."""
        return self._repository

    @property
    def blockchain_service(self) -> BlockchainService | None:
        """Return the blockchain service if configured."""
        return self._blockchain_service

    @property
    def crypto_service(self) -> TextCryptoService:
        """Return the cryptographic text service."""
        return self._crypto_service

    def create_encrypted_message(
        self,
        contract_id: int,
        user_id: int,
        content_type: str,
        label: str,
        plaintext: str,
        vigenere_key: str,
        aes_key_material: str,
    ) -> EncryptedMessage:
        """Encrypt plaintext, persist ciphertext, and record NOTE_CREATED block atomically."""
        if not isinstance(plaintext, str) or not plaintext.strip():
            raise ValidationError("Isi catatan tidak boleh kosong.")

        ciphertext = self._crypto_service.encrypt(
            plaintext=plaintext,
            vigenere_key=vigenere_key,
            aes_key_material=aes_key_material,
        )

        ctx = transaction(self._conn) if self._conn is not None else nullcontext()
        with ctx:
            message = self._repository.create_message(
                contract_id=contract_id,
                user_id=user_id,
                content_type=content_type,
                label=label,
                ciphertext=ciphertext,
            )

            if self._blockchain_service:
                asset_hash = hashlib.sha256(ciphertext.encode("utf-8")).hexdigest().lower()
                msg_id = getattr(message, "id", None)
                payload = {
                    "contract_id": contract_id,
                    "note_id": msg_id,
                    "content_type": content_type,
                    "label": label,
                    "action": "CREATED",
                }
                self._blockchain_service.append_block(
                    event_type="NOTE_CREATED",
                    asset_id=f"note:{msg_id}",
                    asset_hash=asset_hash,
                    payload=payload,
                    created_by=user_id,
                    external_transaction=True,
                )

        logger.info(
            "Created encrypted note (id=%s) for contract %d with blockchain audit",
            getattr(message, "id", "?"), contract_id,
        )
        return message

    def get_decrypted_message(
        self,
        message_id: int,
        user_id: int,
        vigenere_key: str,
        aes_key_material: str,
    ) -> tuple[EncryptedMessage, str]:
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

    def list_by_contract(self, contract_id: int, user_id: int) -> list[EncryptedMessage]:
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
    ) -> EncryptedMessage:
        """Encrypt updated plaintext, update ciphertext, and record NOTE_UPDATED block atomically."""
        if not isinstance(plaintext, str) or not plaintext.strip():
            raise ValidationError("Isi catatan tidak boleh kosong.")

        ciphertext = self._crypto_service.encrypt(
            plaintext=plaintext,
            vigenere_key=vigenere_key,
            aes_key_material=aes_key_material,
        )

        ctx = transaction(self._conn) if self._conn is not None else nullcontext()
        with ctx:
            message = self._repository.update_message(
                message_id=message_id,
                user_id=user_id,
                content_type=content_type,
                label=label,
                ciphertext=ciphertext,
            )

            if self._blockchain_service:
                asset_hash = hashlib.sha256(ciphertext.encode("utf-8")).hexdigest().lower()
                cid = getattr(message, "contract_id", None)
                payload = {
                    "contract_id": cid,
                    "note_id": message_id,
                    "content_type": content_type,
                    "label": label,
                    "action": "UPDATED",
                }
                self._blockchain_service.append_block(
                    event_type="NOTE_UPDATED",
                    asset_id=f"note:{message_id}",
                    asset_hash=asset_hash,
                    payload=payload,
                    created_by=user_id,
                    external_transaction=True,
                )

        logger.info("Updated encrypted note %d with blockchain audit", message_id)
        return message

    def delete_message(self, message_id: int, user_id: int) -> bool:
        """Delete an encrypted message and record NOTE_DELETED block with last ciphertext hash."""
        ctx = transaction(self._conn) if self._conn is not None else nullcontext()
        with ctx:
            existing = self._repository.get_by_id(message_id, user_id)
            if existing is None:
                return False

            if self._blockchain_service:
                raw_cipher = getattr(existing, "ciphertext", "") or ""
                asset_hash = hashlib.sha256(str(raw_cipher).encode("utf-8")).hexdigest().lower()
                cid = getattr(existing, "contract_id", None)
                ctype = getattr(existing, "content_type", "note")
                lbl = getattr(existing, "label", "")

                payload = {
                    "contract_id": cid,
                    "note_id": message_id,
                    "content_type": ctype,
                    "label": lbl,
                    "action": "DELETED",
                }
                self._blockchain_service.append_block(
                    event_type="NOTE_DELETED",
                    asset_id=f"note:{message_id}",
                    asset_hash=asset_hash,
                    payload=payload,
                    created_by=user_id,
                    external_transaction=True,
                )

            deleted = self._repository.delete_message(message_id, user_id)

        logger.info("Deleted encrypted note %d with blockchain audit", message_id)
        return deleted
