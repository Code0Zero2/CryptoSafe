"""Contract service coordinating contract lifecycle, blockchain audit events, and cascading file cleanup."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
import sqlite3

from cryptosafe.common.errors import ValidationError
from cryptosafe.crypto.blockchain_service import BlockchainService
from cryptosafe.database.connection import transaction
from cryptosafe.database.contract_repository import Contract, ContractRepository
from cryptosafe.database.contract_file_repository import ContractFileRepository
from cryptosafe.database.contract_file_service import ContractFileService
from cryptosafe.database.encrypted_message_service import EncryptedMessageService

logger = logging.getLogger("cryptosafe.contract_service")


def calculate_contract_metadata_hash(contract: Contract) -> str:
    """Calculate deterministic SHA-256 digest of contract metadata via canonical JSON.

    Excludes plaintext notes, credentials, keys, or biometric data.
    """
    metadata = {
        "contract_id": contract.id,
        "contract_number": contract.contract_number,
        "created_at": contract.created_at,
        "created_by": contract.created_by,
        "end_date": contract.end_date,
        "parties": contract.parties,
        "start_date": contract.start_date,
        "status": contract.status,
        "title": contract.title,
    }
    canonical_json = json.dumps(
        metadata,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest().lower()


class ContractService:
    """Coordinates contract management with atomic blockchain audit events."""

    def __init__(
        self,
        contract_repository: ContractRepository,
        blockchain_service: BlockchainService,
        contract_file_repository: ContractFileRepository | None = None,
        file_service: ContractFileService | None = None,
        message_service: EncryptedMessageService | None = None,
    ):
        self._contract_repository = contract_repository
        self._blockchain_service = blockchain_service
        self._file_service = file_service
        self._contract_file_repository = contract_file_repository or getattr(file_service, "_repository", None)
        self._message_service = message_service
        self._conn = contract_repository.conn

    @property
    def repository(self) -> ContractRepository:
        """Return the underlying contract repository."""
        return self._contract_repository

    @property
    def blockchain_service(self) -> BlockchainService:
        """Return the associated blockchain service."""
        return self._blockchain_service

    def get_by_id(self, contract_id: int, user_id: int) -> Contract | None:
        """Retrieve contract by ID for the authorized user."""
        return self._contract_repository.get_by_id(contract_id, user_id)

    def list_by_user(self, user_id: int) -> list[Contract]:
        """List all contracts belonging to user."""
        return self._contract_repository.list_by_user(user_id)

    def create_contract(
        self,
        contract_number: str,
        title: str,
        parties: str,
        created_by: int,
        start_date: str | None = None,
        end_date: str | None = None,
        status: str = "Draft",
    ) -> Contract:
        """Create a contract and record CONTRACT_CREATED event on blockchain atomically."""
        with transaction(self._conn):
            contract = self._contract_repository.create_contract(
                contract_number=contract_number,
                title=title,
                parties=parties,
                created_by=created_by,
                start_date=start_date,
                end_date=end_date,
                status=status,
            )

            asset_hash = calculate_contract_metadata_hash(contract)
            payload = {
                "contract_id": contract.id,
                "contract_number": contract.contract_number,
                "title": contract.title,
                "parties": contract.parties,
                "status": contract.status,
                "start_date": contract.start_date,
                "end_date": contract.end_date,
            }

            self._blockchain_service.append_block(
                event_type="CONTRACT_CREATED",
                asset_id=f"contract:{contract.id}",
                asset_hash=asset_hash,
                payload=payload,
                created_by=created_by,
                external_transaction=True,
            )

        logger.info("Created contract %d with blockchain audit block", contract.id)
        return contract

    def update_status(
        self,
        contract_id: int,
        user_id: int,
        status: str,
    ) -> Contract:
        """Update contract status and record CONTRACT_STATUS_UPDATED on blockchain atomically."""
        with transaction(self._conn):
            old_contract = self._contract_repository.get_by_id(contract_id, user_id)
            if old_contract is None:
                raise ValidationError("Kontrak tidak ditemukan.")

            old_status = old_contract.status

            updated_contract = self._contract_repository.update_status(
                contract_id=contract_id,
                user_id=user_id,
                status=status,
            )

            asset_hash = calculate_contract_metadata_hash(updated_contract)
            payload = {
                "contract_id": contract_id,
                "contract_number": updated_contract.contract_number,
                "previous_status": old_status,
                "new_status": status,
            }

            self._blockchain_service.append_block(
                event_type="CONTRACT_STATUS_UPDATED",
                asset_id=f"contract:{contract_id}",
                asset_hash=asset_hash,
                payload=payload,
                created_by=user_id,
                external_transaction=True,
            )

        logger.info(
            "Updated contract %d status from %s to %s with blockchain audit block",
            contract_id, old_status, status,
        )
        return updated_contract

    def delete_contract(
        self,
        contract_id: int,
        user_id: int,
    ) -> bool:
        """Delete contract and record CONTRACT_DELETED block, then clean up physical vault files."""
        # 1. Verify existence and ownership
        contract = self._contract_repository.get_by_id(contract_id, user_id)
        if contract is None:
            raise ValidationError("Kontrak tidak ditemukan.")

        # 2. Inspect attachments to unlink physical files after DB transaction
        physical_files_to_unlink: list[Path] = []
        files_count = 0
        if self._contract_file_repository:
            attached_files = self._contract_file_repository.list_by_contract(contract_id, user_id)
            files_count = len(attached_files)
            for f in attached_files:
                p = Path(f.encrypted_path)
                if not p.is_absolute() and self._file_service:
                    p = self._file_service.storage_dir / p
                physical_files_to_unlink.append(p)

        # 3. Inspect notes count
        notes_count = 0
        if self._message_service:
            notes = self._message_service.list_by_contract(contract_id, user_id)
            notes_count = len(notes)

        # 4. Canonical deletion snapshot
        deletion_metadata = {
            "contract_id": contract.id,
            "contract_number": contract.contract_number,
            "title": contract.title,
            "parties": contract.parties,
            "status": contract.status,
            "created_by": contract.created_by,
            "action": "DELETED",
        }
        canonical_json = json.dumps(
            deletion_metadata,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        asset_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest().lower()

        # 5. Atomic DB operations: append block and delete contract record
        with transaction(self._conn):
            self._blockchain_service.append_block(
                event_type="CONTRACT_DELETED",
                asset_id=f"contract:{contract_id}",
                asset_hash=asset_hash,
                payload={
                    "contract_id": contract.id,
                    "contract_number": contract.contract_number,
                    "title": contract.title,
                    "action": "DELETED",
                    "cascaded_files_count": files_count,
                    "cascaded_notes_count": notes_count,
                },
                created_by=user_id,
                external_transaction=True,
            )

            deleted = self._contract_repository.delete_contract(contract_id, user_id)
            if not deleted:
                raise ValidationError("Gagal menghapus kontrak.")

        # 6. Post-transaction file cleanup: unlink physical files ONLY after commit succeeded
        for path in physical_files_to_unlink:
            try:
                if path.exists():
                    path.unlink(missing_ok=True)
            except OSError as err:
                logger.warning("Gagal menghapus berkas fisik vault %s: %s", path, err)

        logger.info(
            "Deleted contract %d (files=%d, notes=%d) and cleaned up vault files",
            contract_id, files_count, notes_count,
        )
        return True
