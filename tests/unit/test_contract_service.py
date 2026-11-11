"""Unit tests for ContractService and its Blockchain SHA-256 integration."""

import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

src_dir = Path(__file__).resolve().parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from cryptosafe.common.errors import CryptoOperationError, ValidationError
from cryptosafe.crypto.blockchain_service import BlockchainService
from cryptosafe.database.blockchain_repository import BlockchainRepository
from cryptosafe.database.connection import get_connection
from cryptosafe.database.contract_file_repository import ContractFileRepository
from cryptosafe.database.contract_file_service import ContractFileService
from cryptosafe.database.contract_repository import ContractRepository
from cryptosafe.database.contract_service import (
    ContractService,
    calculate_contract_metadata_hash,
)
from cryptosafe.database.encrypted_message_repository import EncryptedMessageRepository
from cryptosafe.database.encrypted_message_service import EncryptedMessageService
from cryptosafe.database.schema import init_db
from cryptosafe.database.user_repository import UserRepository


class TestContractService(unittest.TestCase):
    def setUp(self):
        self.conn = get_connection(":memory:")
        init_db(self.conn)

        self.temp_dir = tempfile.TemporaryDirectory()
        self.vault_dir = Path(self.temp_dir.name) / "vault"
        self.vault_dir.mkdir(parents=True, exist_ok=True)

        self.user_repo = UserRepository(self.conn)
        self.alice = self.user_repo.create_user("alice", "hash_alice")
        self.bob = self.user_repo.create_user("bob", "hash_bob")

        self.contract_repo = ContractRepository(self.conn)
        self.blockchain_repo = BlockchainRepository(self.conn)
        self.blockchain_service = BlockchainService(self.blockchain_repo)
        self.blockchain_service.ensure_genesis_block()

        self.file_repo = ContractFileRepository(self.conn)
        self.file_service = ContractFileService(
            repository=self.file_repo,
            storage_dir=self.vault_dir,
        )

        self.message_repo = EncryptedMessageRepository(self.conn)
        self.message_service = EncryptedMessageService(self.message_repo)

        self.contract_service = ContractService(
            contract_repository=self.contract_repo,
            blockchain_service=self.blockchain_service,
            contract_file_repository=self.file_repo,
            file_service=self.file_service,
            message_service=self.message_service,
        )

    def tearDown(self):
        self.conn.close()
        self.temp_dir.cleanup()

    def test_create_contract_generates_blockchain_event(self):
        """Verify creating a contract atomically records CONTRACT_CREATED on blockchain."""
        contract = self.contract_service.create_contract(
            contract_number="CTR-2026-001",
            title="NDA Kerjasama Riset",
            parties="PT Alpha & PT Beta",
            created_by=self.alice.id,
            start_date="2026-01-01",
            end_date="2026-12-31",
            status="Draft",
        )

        self.assertEqual(contract.contract_number, "CTR-2026-001")
        self.assertEqual(contract.status, "Draft")

        # Check blockchain block
        blocks = self.blockchain_repo.find_by_asset_id(f"contract:{contract.id}")
        self.assertEqual(len(blocks), 1)

        block = blocks[0]
        self.assertEqual(block.event_type, "CONTRACT_CREATED")
        self.assertEqual(block.created_by, self.alice.id)

        # Verify asset_hash matches canonical metadata hash
        expected_hash = calculate_contract_metadata_hash(contract)
        self.assertEqual(block.asset_hash, expected_hash)

        # Verify payload contents
        payload = json.loads(block.payload_json)
        self.assertEqual(payload["contract_id"], contract.id)
        self.assertEqual(payload["contract_number"], "CTR-2026-001")
        self.assertEqual(payload["title"], "NDA Kerjasama Riset")
        self.assertEqual(payload["status"], "Draft")

        # Verify full chain integrity
        ver = self.blockchain_service.verify_chain_integrity()
        self.assertTrue(ver.is_valid)

    def test_update_status_records_old_and_new_status_event(self):
        """Verify updating status records CONTRACT_STATUS_UPDATED with old and new status."""
        contract = self.contract_service.create_contract(
            contract_number="CTR-2026-002",
            title="Perjanjian Pengadaan",
            parties="Alice & Bob Corp",
            created_by=self.alice.id,
            status="Draft",
        )

        # Update 1: Draft -> Review
        c1 = self.contract_service.update_status(contract.id, self.alice.id, "Review")
        self.assertEqual(c1.status, "Review")

        # Update 2: Review -> Approved
        c2 = self.contract_service.update_status(contract.id, self.alice.id, "Approved")
        self.assertEqual(c2.status, "Approved")

        blocks = self.blockchain_repo.find_by_asset_id(f"contract:{contract.id}")
        # 1 create + 2 status updates = 3 blocks
        self.assertEqual(len(blocks), 3)

        b_create, b_up1, b_up2 = blocks

        self.assertEqual(b_create.event_type, "CONTRACT_CREATED")

        self.assertEqual(b_up1.event_type, "CONTRACT_STATUS_UPDATED")
        payload1 = json.loads(b_up1.payload_json)
        self.assertEqual(payload1["previous_status"], "Draft")
        self.assertEqual(payload1["new_status"], "Review")

        self.assertEqual(b_up2.event_type, "CONTRACT_STATUS_UPDATED")
        payload2 = json.loads(b_up2.payload_json)
        self.assertEqual(payload2["previous_status"], "Review")
        self.assertEqual(payload2["new_status"], "Approved")

        # Verify chain integrity
        ver = self.blockchain_service.verify_chain_integrity()
        self.assertTrue(ver.is_valid)
        self.assertEqual(ver.total_blocks, 4)  # 1 genesis + 3 contract blocks

    def test_blockchain_append_failure_rolls_back_contract_creation(self):
        """Verify if blockchain append fails, contract creation is completely rolled back."""
        with patch.object(
            self.blockchain_service,
            "append_block",
            side_effect=CryptoOperationError("Disk write failed"),
        ):
            with self.assertRaises(CryptoOperationError):
                self.contract_service.create_contract(
                    contract_number="CTR-FAIL-001",
                    title="Gagal Dibuat",
                    parties="Alice & Charlie",
                    created_by=self.alice.id,
                )

        # Contract must NOT exist in DB
        contracts = self.contract_service.list_by_user(self.alice.id)
        self.assertEqual(len(contracts), 0)

        # No block created (except genesis)
        self.assertEqual(self.blockchain_repo.get_blocks_count(), 1)

    def test_blockchain_append_failure_rolls_back_status_update(self):
        """Verify if blockchain append fails during update, status remains unchanged."""
        contract = self.contract_service.create_contract(
            contract_number="CTR-2026-ROLLBACK",
            title="Rollback Test",
            parties="Alice & Partner",
            created_by=self.alice.id,
            status="Draft",
        )

        with patch.object(
            self.blockchain_service,
            "append_block",
            side_effect=CryptoOperationError("Blockchain unavailable"),
        ):
            with self.assertRaises(CryptoOperationError):
                self.contract_service.update_status(contract.id, self.alice.id, "Signed")

        # Status must STILL be Draft
        fresh = self.contract_service.get_by_id(contract.id, self.alice.id)
        self.assertIsNotNone(fresh)
        self.assertEqual(fresh.status, "Draft")

    def test_contract_creation_validation_failure_produces_no_block(self):
        """Verify validation errors (e.g. empty title, invalid status) do not write to blockchain."""
        initial_blocks = self.blockchain_repo.get_blocks_count()

        with self.assertRaises(ValidationError):
            self.contract_service.create_contract(
                contract_number="",
                title="",
                parties="",
                created_by=self.alice.id,
            )

        with self.assertRaises(ValidationError):
            self.contract_service.create_contract(
                contract_number="CTR-VALID",
                title="Title",
                parties="Parties",
                created_by=self.alice.id,
                status="InvalidStatusName",
            )

        self.assertEqual(self.blockchain_repo.get_blocks_count(), initial_blocks)

    def test_ownership_enforcement(self):
        """Verify non-owner cannot update or delete contracts, producing no blockchain blocks."""
        contract = self.contract_service.create_contract(
            contract_number="CTR-ALICE-OWNER",
            title="Alice Private Contract",
            parties="Alice & Bob",
            created_by=self.alice.id,
        )

        initial_blocks = self.blockchain_repo.get_blocks_count()

        # Bob attempts to update Alice's contract
        with self.assertRaises(ValidationError):
            self.contract_service.update_status(contract.id, self.bob.id, "Signed")

        # Bob attempts to delete Alice's contract
        with self.assertRaises(ValidationError):
            self.contract_service.delete_contract(contract.id, self.bob.id)

        # No new blocks added
        self.assertEqual(self.blockchain_repo.get_blocks_count(), initial_blocks)

        # Alice's contract remains untouched
        fresh = self.contract_service.get_by_id(contract.id, self.alice.id)
        self.assertEqual(fresh.status, "Draft")

    def test_delete_contract_with_cascaded_file_cleanup_and_event(self):
        """Verify contract deletion records CONTRACT_DELETED and unlinks physical vault files."""
        contract = self.contract_service.create_contract(
            contract_number="CTR-DELETE-ME",
            title="Kontrak Dihapus",
            parties="Alice & Eve",
            created_by=self.alice.id,
        )

        # Create a sample source file and attach to contract
        src_file = Path(self.temp_dir.name) / "sample_doc.txt"
        src_file.write_text("Rahasia Perjanjian", encoding="utf-8")

        attached = self.file_service.attach_file(
            contract_id=contract.id,
            user_id=self.alice.id,
            source_path=src_file,
            key_material="SecretKey123",
        )

        physical_enc_path = Path(attached.encrypted_path)
        self.assertTrue(physical_enc_path.is_file(), "Vault encrypted file must exist")

        # Delete contract
        deleted = self.contract_service.delete_contract(contract.id, self.alice.id)
        self.assertTrue(deleted)

        # Contract must be gone from DB
        self.assertIsNone(self.contract_service.get_by_id(contract.id, self.alice.id))

        # Attached file DB record must be gone (cascade)
        self.assertIsNone(self.file_repo.get_by_id(attached.id, self.alice.id))

        # Physical vault file must be unlinked!
        self.assertFalse(physical_enc_path.exists(), "Vault file must be unlinked upon contract deletion")

        # Check CONTRACT_DELETED block
        blocks = self.blockchain_repo.find_by_asset_id(f"contract:{contract.id}")
        self.assertEqual(len(blocks), 2)  # 1 created + 1 deleted

        del_block = blocks[1]
        self.assertEqual(del_block.event_type, "CONTRACT_DELETED")
        payload = json.loads(del_block.payload_json)
        self.assertEqual(payload["action"], "DELETED")
        self.assertEqual(payload["cascaded_files_count"], 1)

        # Chain verification
        ver = self.blockchain_service.verify_chain_integrity()
        self.assertTrue(ver.is_valid)

    def test_delete_contract_failure_preserves_physical_files(self):
        """Verify that if DB delete fails, physical files in vault are not deleted."""
        contract = self.contract_service.create_contract(
            contract_number="CTR-FAIL-DEL",
            title="Gagal Hapus",
            parties="Alice & Eve",
            created_by=self.alice.id,
        )

        src_file = Path(self.temp_dir.name) / "doc2.txt"
        src_file.write_text("Data penting", encoding="utf-8")

        attached = self.file_service.attach_file(
            contract_id=contract.id,
            user_id=self.alice.id,
            source_path=src_file,
            key_material="Key456",
        )

        physical_enc_path = Path(attached.encrypted_path)
        self.assertTrue(physical_enc_path.is_file())

        with patch.object(
            self.blockchain_service,
            "append_block",
            side_effect=CryptoOperationError("Ledger error"),
        ):
            with self.assertRaises(CryptoOperationError):
                self.contract_service.delete_contract(contract.id, self.alice.id)

        # Physical file must still be present!
        self.assertTrue(physical_enc_path.is_file())

        # DB records must still exist
        self.assertIsNotNone(self.contract_service.get_by_id(contract.id, self.alice.id))
        self.assertIsNotNone(self.file_repo.get_by_id(attached.id, self.alice.id))

    def test_payload_contains_no_sensitive_or_plaintext_data(self):
        """Verify blockchain payloads never leak sensitive credentials, passwords, or keys."""
        contract = self.contract_service.create_contract(
            contract_number="CTR-AUDIT-SAFE",
            title="Safe Contract",
            parties="Party A & B",
            created_by=self.alice.id,
        )

        blocks = self.blockchain_repo.find_by_asset_id(f"contract:{contract.id}")
        for b in blocks:
            p = json.loads(b.payload_json)
            self.assertNotIn("password", p)
            self.assertNotIn("password_hash", p)
            self.assertNotIn("key", p)
            self.assertNotIn("biometric", p)
            self.assertNotIn("plaintext", p)


if __name__ == "__main__":
    unittest.main()
