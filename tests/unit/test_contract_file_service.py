"""Unit tests for ContractFileService."""

import os
import secrets
import tempfile
import unittest
from pathlib import Path

from cryptosafe.common.errors import CryptoOperationError, ValidationError
from cryptosafe.crypto.file_crypto_service import FileCryptoService
from cryptosafe.crypto.key_manager import generate_random_aes_key
from cryptosafe.database.connection import get_connection
from cryptosafe.database.contract_file_repository import ContractFileRepository
from cryptosafe.database.contract_file_service import ContractFileService
from cryptosafe.database.contract_repository import ContractRepository
from cryptosafe.database.schema import init_db
from cryptosafe.database.user_repository import UserRepository


class TestContractFileService(unittest.TestCase):
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
        self.contract_alice = contract_repo.create_contract(
            contract_number="CTR-ALICE-VAULT-1",
            title="Perjanjian Akuisisi Rahasia",
            parties="Alice & Alpha Holdings",
            status="Draft",
            created_by=self.alice.id,
        )

        self.file_repo = ContractFileRepository(self.conn)
        self.crypto_service = FileCryptoService()
        self.vault_service = ContractFileService(
            repository=self.file_repo,
            crypto_service=self.crypto_service,
            storage_dir=self.storage_dir,
        )

    def tearDown(self):
        self.conn.close()
        self.temp_dir.cleanup()

    def test_attach_and_export_round_trip_passphrase(self):
        # Create sample document
        sample_path = self.work_dir / "confidential_agreement.pdf"
        sample_content = b"%PDF-1.4\nSecret contract text payload with bytes " + secrets.token_bytes(4096)
        sample_path.write_bytes(sample_content)

        passphrase = "SuperSecurePassphrase2026!"
        record = self.vault_service.attach_file(
            contract_id=self.contract_alice.id,
            user_id=self.alice.id,
            source_path=sample_path,
            key_material=passphrase,
        )

        self.assertEqual(record.original_filename, "confidential_agreement.pdf")
        self.assertEqual(record.size_bytes, len(sample_content))
        self.assertEqual(record.algorithm, "ChaCha20-Poly1305")

        # Verify vault storage file exists and is encrypted (does not contain raw plaintext)
        vault_file = Path(record.encrypted_path)
        self.assertTrue(vault_file.is_file())
        raw_vault_bytes = vault_file.read_bytes()
        self.assertNotIn(b"Secret contract text payload", raw_vault_bytes)
        self.assertTrue(raw_vault_bytes.startswith(b"CSAFE_FL"))

        # Verify source file is untouched
        self.assertTrue(sample_path.is_file())
        self.assertEqual(sample_path.read_bytes(), sample_content)

        # Export and decrypt
        export_path = self.work_dir / "decrypted_agreement.pdf"
        result_path = self.vault_service.export_decrypted_file(
            file_id=record.id,
            user_id=self.alice.id,
            destination_path=export_path,
            key_material=passphrase,
        )

        self.assertEqual(result_path, export_path)
        self.assertTrue(export_path.is_file())
        self.assertEqual(export_path.read_bytes(), sample_content)

    def test_attach_and_export_round_trip_direct_hex_key(self):
        sample_path = self.work_dir / "raw_data.bin"
        sample_content = secrets.token_bytes(65536 + 2048)  # Multi-chunk size
        sample_path.write_bytes(sample_content)

        hex_key = generate_random_aes_key()
        record = self.vault_service.attach_file(
            contract_id=self.contract_alice.id,
            user_id=self.alice.id,
            source_path=sample_path,
            key_material=hex_key,
        )

        export_path = self.work_dir / "decrypted_raw.bin"
        self.vault_service.export_decrypted_file(
            file_id=record.id,
            user_id=self.alice.id,
            destination_path=export_path,
            key_material=hex_key,
        )

        self.assertEqual(export_path.read_bytes(), sample_content)

    def test_export_with_wrong_key_fails(self):
        sample_path = self.work_dir / "secret.txt"
        sample_path.write_text("Rahasia tingkat tinggi.")
        record = self.vault_service.attach_file(
            contract_id=self.contract_alice.id,
            user_id=self.alice.id,
            source_path=sample_path,
            key_material="CorrectPass123",
        )

        export_path = self.work_dir / "should_not_exist.txt"
        with self.assertRaises(CryptoOperationError):
            self.vault_service.export_decrypted_file(
                file_id=record.id,
                user_id=self.alice.id,
                destination_path=export_path,
                key_material="WrongPass456",
            )

        # Plaintext destination should not exist
        self.assertFalse(export_path.exists())

    def test_attach_missing_source_file_fails(self):
        missing = self.work_dir / "non_existent_file.pdf"
        with self.assertRaises(ValidationError):
            self.vault_service.attach_file(
                contract_id=self.contract_alice.id,
                user_id=self.alice.id,
                source_path=missing,
                key_material="SomePass123",
            )

    def test_attach_rollback_on_metadata_failure(self):
        sample_path = self.work_dir / "note.txt"
        sample_path.write_text("Attachment on invalid contract")

        initial_vault_files = list(self.storage_dir.glob("*.enc"))
        self.assertEqual(len(initial_vault_files), 0)

        # Attempt attaching to non-existent contract ID 99999
        with self.assertRaises(ValidationError):
            self.vault_service.attach_file(
                contract_id=99999,
                user_id=self.alice.id,
                source_path=sample_path,
                key_material="Pass123",
            )

        # Ensure no orphan file left in vault storage
        remaining_vault_files = list(self.storage_dir.glob("*.enc"))
        self.assertEqual(len(remaining_vault_files), 0)

    def test_delete_attachment_cleans_up_db_and_disk(self):
        sample_path = self.work_dir / "to_delete.txt"
        sample_path.write_text("Delete me later.")
        record = self.vault_service.attach_file(
            contract_id=self.contract_alice.id,
            user_id=self.alice.id,
            source_path=sample_path,
            key_material="Pass123",
        )

        vault_file = Path(record.encrypted_path)
        self.assertTrue(vault_file.is_file())

        deleted = self.vault_service.delete_file(record.id, self.alice.id)
        self.assertTrue(deleted)

        # Database record should be gone
        self.assertIsNone(self.file_repo.get_by_id(record.id, self.alice.id))
        # Encrypted file on disk should be removed
        self.assertFalse(vault_file.exists())

    def test_delete_attachment_gracefully_handles_missing_physical_file(self):
        sample_path = self.work_dir / "missing_physical.txt"
        sample_path.write_text("Delete me.")
        record = self.vault_service.attach_file(
            contract_id=self.contract_alice.id,
            user_id=self.alice.id,
            source_path=sample_path,
            key_material="Pass123",
        )

        vault_file = Path(record.encrypted_path)
        vault_file.unlink()  # Manually delete disk file

        # Deletion from service should still succeed
        deleted = self.vault_service.delete_file(record.id, self.alice.id)
        self.assertTrue(deleted)
        self.assertIsNone(self.file_repo.get_by_id(record.id, self.alice.id))

    def test_user_isolation(self):
        sample_path = self.work_dir / "alice_only.txt"
        sample_path.write_text("Alice confidential file.")
        record = self.vault_service.attach_file(
            contract_id=self.contract_alice.id,
            user_id=self.alice.id,
            source_path=sample_path,
            key_material="Pass123",
        )

        # Bob attempts export
        bob_export = self.work_dir / "bob_leaked.txt"
        with self.assertRaises(ValidationError):
            self.vault_service.export_decrypted_file(
                file_id=record.id,
                user_id=self.bob.id,
                destination_path=bob_export,
                key_material="Pass123",
            )
        self.assertFalse(bob_export.exists())

        # Bob attempts delete
        with self.assertRaises(ValidationError):
            self.vault_service.delete_file(record.id, self.bob.id)

        # Alice file is still intact
        self.assertIsNotNone(self.file_repo.get_by_id(record.id, self.alice.id))


if __name__ == "__main__":
    unittest.main()
