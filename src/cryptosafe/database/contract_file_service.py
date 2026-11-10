"""Service coordinating file encryption and contract attachment storage."""

import logging
import mimetypes
import uuid
from pathlib import Path

from cryptosafe.common.errors import ValidationError
from cryptosafe.config import DATA_DIR
from cryptosafe.crypto.file_crypto_service import FileCryptoService
from cryptosafe.database.contract_file_repository import (
    ContractFile,
    ContractFileRepository,
)

logger = logging.getLogger("cryptosafe.contract_file_service")


class ContractFileService:
    """Manages secure contract file vault attachments."""

    def __init__(
        self,
        repository: ContractFileRepository,
        crypto_service: FileCryptoService | None = None,
        storage_dir: Path | str | None = None,
    ):
        self._repository = repository
        self._crypto_service = crypto_service or FileCryptoService()
        if storage_dir is None:
            self._storage_dir = Path(DATA_DIR) / "vault"
        else:
            self._storage_dir = Path(storage_dir)

        self._storage_dir.mkdir(parents=True, exist_ok=True)

    @property
    def storage_dir(self) -> Path:
        return self._storage_dir

    def attach_file(
        self,
        contract_id: int,
        user_id: int,
        source_path: Path | str,
        key_material: str,
    ) -> ContractFile:
        """Encrypt source file into vault and persist contract attachment metadata."""
        src = Path(source_path).resolve()
        if not src.is_file():
            raise ValidationError(f"Berkas sumber tidak ditemukan: {src}")

        if not key_material or not key_material.strip():
            raise ValidationError("Kunci atau passphrase tidak boleh kosong.")

        original_filename = src.name
        size_bytes = src.stat().st_size
        mime_type, _ = mimetypes.guess_type(original_filename)

        # Unique UUID-based storage filename to prevent path traversal and collision
        vault_filename = f"{uuid.uuid4().hex}.enc"
        encrypted_target = (self._storage_dir / vault_filename).resolve()

        # Path traversal guard
        if encrypted_target.parent != self._storage_dir.resolve():
            raise ValidationError("Jalur penyimpanan file tidak valid.")

        # Encrypt to storage
        self._crypto_service.encrypt_file(
            source_path=src,
            destination_path=encrypted_target,
            key_material=key_material,
        )

        try:
            record = self._repository.create_file(
                contract_id=contract_id,
                user_id=user_id,
                original_filename=original_filename,
                encrypted_path=str(encrypted_target),
                size_bytes=size_bytes,
                mime_type=mime_type,
            )
            logger.info(
                "Attached encrypted file %s (id=%d) to contract %d",
                original_filename, record.id, contract_id,
            )
            return record
        except Exception:
            # Transactional safety: remove encrypted file on metadata failure
            if encrypted_target.exists():
                encrypted_target.unlink(missing_ok=True)
            raise

    def export_decrypted_file(
        self,
        file_id: int,
        user_id: int,
        destination_path: Path | str,
        key_material: str,
    ) -> Path:
        """Decrypt attachment from vault into user-specified destination path."""
        file_record = self._repository.get_by_id(file_id, user_id)
        if file_record is None:
            raise ValidationError("Lampiran berkas tidak ditemukan atau akses ditolak.")

        enc_path = Path(file_record.encrypted_path)
        if not enc_path.is_absolute():
            enc_path = self._storage_dir / enc_path

        if not enc_path.is_file():
            raise ValidationError("Berkas fisik terenkripsi tidak ditemukan di storage.")

        dst = Path(destination_path).resolve()
        if dst == enc_path.resolve():
            raise ValidationError("Tujuan ekspor tidak boleh sama dengan file vault.")

        self._crypto_service.decrypt_file(
            source_path=enc_path,
            destination_path=dst,
            key_material=key_material,
        )

        logger.info(
            "Exported decrypted file %s (id=%d) to %s",
            file_record.original_filename, file_id, dst.name,
        )
        return dst

    def delete_file(self, file_id: int, user_id: int) -> bool:
        """Delete attachment record and unlink the physical encrypted vault file."""
        file_record = self._repository.get_by_id(file_id, user_id)
        if file_record is None:
            raise ValidationError("Lampiran berkas tidak ditemukan atau akses ditolak.")

        enc_path = Path(file_record.encrypted_path)
        if not enc_path.is_absolute():
            enc_path = self._storage_dir / enc_path

        # Delete database record first
        deleted = self._repository.delete_file(file_id, user_id)

        # Remove physical file if it exists (gracefully handle missing files)
        if enc_path.exists():
            enc_path.unlink(missing_ok=True)

        logger.info("Deleted file attachment id=%d for user=%d", file_id, user_id)
        return deleted

    def list_by_contract(self, contract_id: int, user_id: int) -> list[ContractFile]:
        """List attachments for contract owned by user."""
        return self._repository.list_by_contract(contract_id, user_id)

    def get_file(self, file_id: int, user_id: int) -> ContractFile | None:
        """Get attachment metadata by id."""
        return self._repository.get_by_id(file_id, user_id)

