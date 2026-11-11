"""Service coordinating file encryption and contract attachment storage."""

import hashlib
import logging
import mimetypes
from pathlib import Path
import uuid

from cryptosafe.common.errors import ValidationError
from cryptosafe.config import DATA_DIR
from cryptosafe.crypto.blockchain_service import BlockchainService
from cryptosafe.crypto.file_crypto_service import FileCryptoService
from cryptosafe.database.connection import transaction
from cryptosafe.database.contract_file_repository import (
    ContractFile,
    ContractFileRepository,
)

logger = logging.getLogger("cryptosafe.contract_file_service")


class ContractFileService:
    """Manages secure contract file vault attachments with blockchain audit trails."""

    def __init__(
        self,
        repository: ContractFileRepository,
        crypto_service: FileCryptoService | None = None,
        storage_dir: Path | str | None = None,
        blockchain_service: BlockchainService | None = None,
    ):
        self._repository = repository
        self._crypto_service = crypto_service or FileCryptoService()
        self._blockchain_service = blockchain_service
        self._conn = getattr(repository, "conn", getattr(repository, "_conn", None))
        if storage_dir is None:
            self._storage_dir = Path(DATA_DIR) / "vault"
        else:
            self._storage_dir = Path(storage_dir)

        self._storage_dir.mkdir(parents=True, exist_ok=True)

    @property
    def storage_dir(self) -> Path:
        return self._storage_dir

    @property
    def blockchain_service(self) -> BlockchainService | None:
        return self._blockchain_service

    @blockchain_service.setter
    def blockchain_service(self, service: BlockchainService | None) -> None:
        self._blockchain_service = service

    def _hash_file(self, file_path: Path | str) -> str:
        """Calculate SHA-256 digest of file via streaming chunks."""
        if self._blockchain_service is not None:
            return self._blockchain_service.hash_file_streaming(file_path)
        path = Path(file_path).resolve()
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest().lower()

    def attach_file(
        self,
        contract_id: int,
        user_id: int,
        source_path: Path | str,
        key_material: str,
    ) -> ContractFile:
        """Encrypt source file into vault and persist contract attachment metadata atomically with blockchain audit."""
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
        try:
            encrypted_target.relative_to(self._storage_dir.resolve())
        except ValueError:
            raise ValidationError("Jalur penyimpanan file tidak valid.")

        # Encrypt to storage (user source file is never modified or removed)
        self._crypto_service.encrypt_file(
            source_path=src,
            destination_path=encrypted_target,
            key_material=key_material,
        )

        # Calculate asset_hash from actual stored ciphertext bytes
        asset_hash = self._hash_file(encrypted_target)

        try:
            with transaction(self._conn):
                record = self._repository.create_file(
                    contract_id=contract_id,
                    user_id=user_id,
                    original_filename=original_filename,
                    encrypted_path=str(encrypted_target),
                    size_bytes=size_bytes,
                    mime_type=mime_type,
                )

                if self._blockchain_service is not None:
                    payload = {
                        "action": "ATTACHED",
                        "algorithm": record.algorithm,
                        "contract_id": contract_id,
                        "file_id": record.id,
                        "mime_type": record.mime_type,
                        "size_bytes": record.size_bytes,
                    }
                    self._blockchain_service.append_block(
                        event_type="FILE_ATTACHED",
                        asset_id=f"file:{record.id}",
                        asset_hash=asset_hash,
                        payload=payload,
                        created_by=user_id,
                        external_transaction=True,
                    )

            logger.info(
                "Attached encrypted file %s (id=%d) to contract %d",
                original_filename, record.id, contract_id,
            )
            return record
        except Exception:
            # Transactional safety: remove newly created encrypted file on metadata or blockchain failure
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
        enc_path = enc_path.resolve()

        # Path traversal guard for stored path
        try:
            enc_path.relative_to(self._storage_dir.resolve())
        except ValueError:
            raise ValidationError("Jalur berkas vault tidak valid.")

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
        """Delete attachment record and blockchain block atomically, then unlink physical vault file."""
        file_record = self._repository.get_by_id(file_id, user_id)
        if file_record is None:
            raise ValidationError("Lampiran berkas tidak ditemukan atau akses ditolak.")

        enc_path = Path(file_record.encrypted_path)
        if not enc_path.is_absolute():
            enc_path = self._storage_dir / enc_path
        enc_path = enc_path.resolve()

        # Path traversal guard
        try:
            enc_path.relative_to(self._storage_dir.resolve())
        except ValueError:
            raise ValidationError("Jalur berkas vault tidak valid.")

        # Ensure physical file exists and compute asset hash before starting transaction
        if not enc_path.is_file():
            raise ValidationError("Berkas fisik terenkripsi tidak ditemukan di storage vault.")

        try:
            asset_hash = self._hash_file(enc_path)
        except Exception as err:
            raise ValidationError(f"Gagal menghitung hash berkas terenkripsi: {err}") from err

        payload = {
            "action": "DELETED",
            "algorithm": file_record.algorithm,
            "contract_id": file_record.contract_id,
            "file_id": file_record.id,
            "mime_type": file_record.mime_type,
            "size_bytes": file_record.size_bytes,
        }

        with transaction(self._conn):
            deleted = self._repository.delete_file(file_id, user_id)
            if not deleted:
                raise ValidationError("Gagal menghapus metadata lampiran berkas.")

            if self._blockchain_service is not None:
                self._blockchain_service.append_block(
                    event_type="FILE_DELETED",
                    asset_id=f"file:{file_id}",
                    asset_hash=asset_hash,
                    payload=payload,
                    created_by=user_id,
                    external_transaction=True,
                )

        # Post-commit physical file deletion: only unlink after SQLite commit succeeds
        if enc_path.exists():
            try:
                enc_path.unlink()
            except OSError as err:
                logger.error(
                    "CRITICAL: Failed to unlink physical vault file %s after DB deletion commit: %s. "
                    "The file is now an orphan in vault storage.",
                    enc_path, err,
                )

        logger.info("Deleted file attachment id=%d for user=%d", file_id, user_id)
        return True

    def find_orphan_vault_files(self) -> list[Path]:
        """Find encrypted files in vault storage that have no corresponding database record.

        Guards against symlinks and path traversal targeting files outside the vault.
        """
        if not self._storage_dir.exists():
            return []

        vault_dir = self._storage_dir.resolve()
        cursor = self._conn.execute("SELECT encrypted_path FROM contract_files")
        recorded_paths = {Path(row[0]).resolve() for row in cursor.fetchall()}

        orphans: list[Path] = []
        for file_path in self._storage_dir.glob("*.enc"):
            try:
                if file_path.is_symlink():
                    logger.warning(
                        "Security notice: Symlink detected in vault: %s", file_path
                    )
                resolved = file_path.resolve()
                resolved.relative_to(vault_dir)
            except (ValueError, OSError) as err:
                logger.warning(
                    "Security alert: Skipping suspicious vault entry %s: %s",
                    file_path, err,
                )
                continue

            if not resolved.is_file():
                continue

            if resolved not in recorded_paths:
                orphans.append(resolved)

        return orphans

    def cleanup_orphan_vault_files(self) -> list[Path]:
        """Safely delete unreferenced orphan vault files from storage."""
        orphans = self.find_orphan_vault_files()
        cleaned: list[Path] = []
        vault_dir = self._storage_dir.resolve()

        for path in orphans:
            try:
                resolved = path.resolve()
                resolved.relative_to(vault_dir)
                if resolved.is_file():
                    resolved.unlink()
                    cleaned.append(resolved)
                    logger.info("Cleaned up orphan vault file: %s", resolved)
            except ValueError:
                logger.error(
                    "Security alert: Prevented attempted cleanup of path outside vault: %s",
                    path,
                )
            except OSError as err:
                logger.error("Failed to cleanup orphan vault file %s: %s", path, err)

        return cleaned

    def list_by_contract(self, contract_id: int, user_id: int) -> list[ContractFile]:
        """List attachments for contract owned by user."""
        return self._repository.list_by_contract(contract_id, user_id)

    def get_file(self, file_id: int, user_id: int) -> ContractFile | None:
        """Get attachment metadata by id."""
        return self._repository.get_by_id(file_id, user_id)
