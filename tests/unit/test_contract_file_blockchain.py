"""Unit tests for ContractFileService with Blockchain SHA-256 integration."""

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

src_dir = Path(__file__).resolve().parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from cryptosafe.common.errors import CryptoOperationError, ValidationError
from cryptosafe.crypto.blockchain_service import BlockchainService
from cryptosafe.crypto.file_crypto_service import FileCryptoService
from cryptosafe.database.blockchain_repository import BlockchainRepository
from cryptosafe.database.connection import get_connection
from cryptosafe.database.contract_file_repository import ContractFileRepository
from cryptosafe.database.contract_file_service import ContractFileService
from cryptosafe.database.contract_repository import ContractRepository
from cryptosafe.database.schema import init_db
from cryptosafe.database.user_repository import UserRepository


class TestContractFileBlockchain(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_dir = Path(self.temp_dir.name) / "vault"
        self.work_dir = Path(self.temp_dir.name) / "work"
        self.work_dir.mkdir(parents=True, exist_ok=True)

        self.conn = get_connection(":memory:")
        init_db(self.conn)

        user_repo = UserRepository(self.conn)
        self.alice = user_repo.create_user("alice", "hash-alice")
        self.bob = user_repo.create_user("bob", "hash-bob")

        contract_repo = ContractRepository(self.conn)
        self.contract = contract_repo.create_contract(
            contract_number="CTR-TEST-VAULT-001",
            title="Perjanjian Kerja Sama Teknologi",
            parties="Alice & Partner Corp",
            status="Draft",
            created_by=self.alice.id,
        )

        self.blockchain_repo = BlockchainRepository(self.conn)
        self.blockchain_service = BlockchainService(self.blockchain_repo)
        self.file_repo = ContractFileRepository(self.conn)
        self.crypto_service = FileCryptoService()

        self.service = ContractFileService(
            repository=self.file_repo,
            crypto_service=self.crypto_service,
            storage_dir=self.storage_dir,
            blockchain_service=self.blockchain_service,
        )

        self.sample_file = self.work_dir / "sample_doc.pdf"
        self.file_content = b"%PDF-1.5 Confidential Content for CryptoSafe Audit Testing 12345"
        self.sample_file.write_bytes(self.file_content)
        self.passphrase = "UltraSecurePassphrase2026!"

    def tearDown(self):
        self.conn.close()
        self.temp_dir.cleanup()

    def test_attach_file_produces_event_and_matching_hash(self):
        """Verify attaching a file writes block with SHA-256 matching stored ciphertext."""
        record = self.service.attach_file(
            contract_id=self.contract.id,
            user_id=self.alice.id,
            source_path=self.sample_file,
            key_material=self.passphrase,
        )

        # User's original file must remain intact
        self.assertTrue(self.sample_file.is_file())
        self.assertEqual(self.sample_file.read_bytes(), self.file_content)

        # Check blockchain block
        blocks = self.blockchain_repo.find_by_asset_id(f"file:{record.id}")
        self.assertEqual(len(blocks), 1)

        block = blocks[0]
        self.assertEqual(block.event_type, "FILE_ATTACHED")
        self.assertEqual(block.created_by, self.alice.id)

        # Verify asset_hash strictly matches the encrypted vault file on disk
        vault_path = Path(record.encrypted_path)
        self.assertTrue(vault_path.is_file())
        expected_hash = hashlib.sha256(vault_path.read_bytes()).hexdigest().lower()
        self.assertEqual(block.asset_hash.lower(), expected_hash)

        # Verify payload metadata (zero-knowledge: no original_filename)
        payload = json.loads(block.payload_json)
        self.assertEqual(payload["action"], "ATTACHED")
        self.assertEqual(payload["file_id"], record.id)
        self.assertEqual(payload["contract_id"], self.contract.id)
        self.assertNotIn("original_filename", payload)
        self.assertNotIn("sample_doc.pdf", block.payload_json)
        self.assertEqual(payload["size_bytes"], len(self.file_content))
        self.assertEqual(payload["algorithm"], "ChaCha20-Poly1305")

        # Verify chain integrity
        ver = self.blockchain_service.verify_chain_integrity()
        self.assertTrue(ver.is_valid)

    def test_delete_file_produces_event_with_last_hash(self):
        """Verify deleting a file writes block with last ciphertext hash before removal."""
        record = self.service.attach_file(
            contract_id=self.contract.id,
            user_id=self.alice.id,
            source_path=self.sample_file,
            key_material=self.passphrase,
        )
        vault_path = Path(record.encrypted_path)
        last_ciphertext_hash = hashlib.sha256(vault_path.read_bytes()).hexdigest().lower()

        deleted = self.service.delete_file(record.id, self.alice.id)
        self.assertTrue(deleted)

        # Metadata deleted
        self.assertIsNone(self.file_repo.get_by_id(record.id, self.alice.id))
        # Physical file unlinked
        self.assertFalse(vault_path.exists())

        # Check blockchain blocks
        blocks = self.blockchain_repo.find_by_asset_id(f"file:{record.id}")
        self.assertEqual(len(blocks), 2)

        del_block = blocks[1]
        self.assertEqual(del_block.event_type, "FILE_DELETED")
        self.assertEqual(del_block.created_by, self.alice.id)
        self.assertEqual(del_block.asset_hash.lower(), last_ciphertext_hash)

        del_payload = json.loads(del_block.payload_json)
        self.assertEqual(del_payload["action"], "DELETED")
        self.assertEqual(del_payload["file_id"], record.id)
        self.assertEqual(del_payload["contract_id"], self.contract.id)
        self.assertNotIn("original_filename", del_payload)
        self.assertNotIn("sample_doc.pdf", del_block.payload_json)

        # Verify chain integrity
        ver = self.blockchain_service.verify_chain_integrity()
        self.assertTrue(ver.is_valid)

    def test_attach_append_failure_rolls_back_db_and_unlinks_vault_file(self):
        """Verify failure in append_block rolls back SQLite and unlinks new vault file."""
        initial_blocks = self.blockchain_repo.get_blocks_count()

        with patch.object(
            self.blockchain_service,
            "append_block",
            side_effect=CryptoOperationError("Blockchain disk full"),
        ):
            with self.assertRaises(CryptoOperationError):
                self.service.attach_file(
                    contract_id=self.contract.id,
                    user_id=self.alice.id,
                    source_path=self.sample_file,
                    key_material=self.passphrase,
                )

        # No block added
        self.assertEqual(self.blockchain_repo.get_blocks_count(), initial_blocks)

        # No records in database
        files = self.file_repo.list_by_contract(self.contract.id, self.alice.id)
        self.assertEqual(len(files), 0)

        # Vault directory has no orphan files
        vault_files = list(self.storage_dir.glob("*.enc"))
        self.assertEqual(len(vault_files), 0)

        # User's source file is preserved
        self.assertTrue(self.sample_file.is_file())

    def test_delete_append_failure_rolls_back_db_and_preserves_vault_file(self):
        """Verify failure in append_block preserves metadata and the physical vault file."""
        record = self.service.attach_file(
            contract_id=self.contract.id,
            user_id=self.alice.id,
            source_path=self.sample_file,
            key_material=self.passphrase,
        )
        vault_path = Path(record.encrypted_path)
        self.assertTrue(vault_path.is_file())

        with patch.object(
            self.blockchain_service,
            "append_block",
            side_effect=CryptoOperationError("Simulated ledger error"),
        ):
            with self.assertRaises(CryptoOperationError):
                self.service.delete_file(record.id, self.alice.id)

        # Metadata must STILL exist in database
        fresh_record = self.file_repo.get_by_id(record.id, self.alice.id)
        self.assertIsNotNone(fresh_record)

        # Physical file must STILL exist in vault
        self.assertTrue(vault_path.is_file())

    def test_post_commit_unlink_failure_preserves_block_and_identifies_orphan(self):
        """Verify post-commit physical unlink failure leaves block intact and can be cleaned up."""
        record = self.service.attach_file(
            contract_id=self.contract.id,
            user_id=self.alice.id,
            source_path=self.sample_file,
            key_material=self.passphrase,
        )
        vault_path = Path(record.encrypted_path)

        # Simulate unlink failure (e.g. file lock or permission error)
        with patch.object(Path, "unlink", side_effect=OSError("Access denied by antivirus")):
            deleted = self.service.delete_file(record.id, self.alice.id)
            self.assertTrue(deleted)

        # Database record is deleted
        self.assertIsNone(self.file_repo.get_by_id(record.id, self.alice.id))

        # Blockchain FILE_DELETED block is recorded
        blocks = self.blockchain_repo.find_by_asset_id(f"file:{record.id}")
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[1].event_type, "FILE_DELETED")

        # Physical file is still on disk as orphan
        self.assertTrue(vault_path.exists())

        # find_orphan_vault_files detects it
        orphans = self.service.find_orphan_vault_files()
        self.assertIn(vault_path.resolve(), orphans)

        # cleanup_orphan_vault_files cleans it up safely
        cleaned = self.service.cleanup_orphan_vault_files()
        self.assertIn(vault_path.resolve(), cleaned)
        self.assertFalse(vault_path.exists())

    def test_ownership_enforcement(self):
        """Verify Bob cannot decrypt or delete Alice's file attachment."""
        record = self.service.attach_file(
            contract_id=self.contract.id,
            user_id=self.alice.id,
            source_path=self.sample_file,
            key_material=self.passphrase,
        )
        initial_blocks = self.blockchain_repo.get_blocks_count()

        # Bob attempts export
        bob_export = self.work_dir / "bob_stolen.pdf"
        with self.assertRaises(ValidationError):
            self.service.export_decrypted_file(
                file_id=record.id,
                user_id=self.bob.id,
                destination_path=bob_export,
                key_material=self.passphrase,
            )
        self.assertFalse(bob_export.exists())

        # Bob attempts delete
        with self.assertRaises(ValidationError):
            self.service.delete_file(record.id, self.bob.id)

        # No new blocks added
        self.assertEqual(self.blockchain_repo.get_blocks_count(), initial_blocks)

        # Alice's file remains intact
        self.assertIsNotNone(self.file_repo.get_by_id(record.id, self.alice.id))

    def test_delete_fails_when_physical_file_missing(self):
        """Verify delete_file aborts before DB transaction if physical file is missing."""
        record = self.service.attach_file(
            contract_id=self.contract.id,
            user_id=self.alice.id,
            source_path=self.sample_file,
            key_material=self.passphrase,
        )
        vault_path = Path(record.encrypted_path)
        vault_path.unlink()  # Manually delete physical vault file

        initial_blocks = self.blockchain_repo.get_blocks_count()

        with self.assertRaises(ValidationError) as ctx:
            self.service.delete_file(record.id, self.alice.id)
        self.assertIn("tidak ditemukan", str(ctx.exception).lower())

        # No block added
        self.assertEqual(self.blockchain_repo.get_blocks_count(), initial_blocks)

        # Database record must still exist
        self.assertIsNotNone(self.file_repo.get_by_id(record.id, self.alice.id))

    def test_delete_fails_when_file_unreadable(self):
        """Verify delete_file aborts before DB transaction if file cannot be read/hashed."""
        record = self.service.attach_file(
            contract_id=self.contract.id,
            user_id=self.alice.id,
            source_path=self.sample_file,
            key_material=self.passphrase,
        )
        initial_blocks = self.blockchain_repo.get_blocks_count()

        with patch.object(self.service, "_hash_file", side_effect=ValidationError("Read I/O error")):
            with self.assertRaises(ValidationError) as ctx:
                self.service.delete_file(record.id, self.alice.id)
            self.assertIn("gagal menghitung hash", str(ctx.exception).lower())

        # No block added
        self.assertEqual(self.blockchain_repo.get_blocks_count(), initial_blocks)

        # Database record and physical file must both still exist
        self.assertIsNotNone(self.file_repo.get_by_id(record.id, self.alice.id))
        self.assertTrue(Path(record.encrypted_path).is_file())

    def test_orphan_cleanup_security_symlinks_and_traversal(self):
        """Verify orphan detection and cleanup ignores registered files and paths outside vault."""
        # 1. Registered file (must NEVER be deleted)
        record = self.service.attach_file(
            contract_id=self.contract.id,
            user_id=self.alice.id,
            source_path=self.sample_file,
            key_material=self.passphrase,
        )
        registered_vault_file = Path(record.encrypted_path)

        # 2. Legitimate orphan file in vault
        orphan_vault_file = self.storage_dir / "legit_orphan.enc"
        orphan_vault_file.write_bytes(b"Orphan encrypted data")

        # 3. External sensitive file outside vault
        external_file = self.work_dir / "critical_system_file.enc"
        external_file.write_bytes(b"DO NOT DELETE EXTERNAL DATA")

        orphans = self.service.find_orphan_vault_files()

        # Registered file must NOT be in orphans
        self.assertNotIn(registered_vault_file.resolve(), orphans)

        # External file must NOT be in orphans
        self.assertNotIn(external_file.resolve(), orphans)

        # Legit orphan must be in orphans
        self.assertIn(orphan_vault_file.resolve(), orphans)

        # Run cleanup
        cleaned = self.service.cleanup_orphan_vault_files()

        # Legit orphan is cleaned
        self.assertIn(orphan_vault_file.resolve(), cleaned)
        self.assertFalse(orphan_vault_file.exists())

        # Registered file is STILL intact
        self.assertTrue(registered_vault_file.exists())
        self.assertIsNotNone(self.file_repo.get_by_id(record.id, self.alice.id))

        # External file is STILL intact
        self.assertTrue(external_file.exists())

    def test_payload_contains_no_sensitive_or_plaintext_data(self):
        """Verify blockchain payloads never leak plaintext file content, filename, or passphrases."""
        record = self.service.attach_file(
            contract_id=self.contract.id,
            user_id=self.alice.id,
            source_path=self.sample_file,
            key_material=self.passphrase,
        )
        self.service.delete_file(record.id, self.alice.id)

        blocks = self.blockchain_repo.find_by_asset_id(f"file:{record.id}")
        self.assertEqual(len(blocks), 2)

        for b in blocks:
            raw_payload = b.payload_json
            payload = json.loads(raw_payload)

            self.assertNotIn("plaintext", payload)
            self.assertNotIn("content", payload)
            self.assertNotIn("key", payload)
            self.assertNotIn("passphrase", payload)
            self.assertNotIn("password", payload)
            self.assertNotIn("original_filename", payload)
            self.assertNotIn(self.sample_file.name, raw_payload)
            self.assertNotIn(self.passphrase, raw_payload)
            self.assertNotIn(self.file_content.decode("latin1"), raw_payload)


if __name__ == "__main__":
    unittest.main()
