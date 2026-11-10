"""Unit tests for ContractFileRepository."""

import unittest

from cryptosafe.common.errors import ValidationError
from cryptosafe.database.connection import get_connection
from cryptosafe.database.contract_file_repository import ContractFileRepository
from cryptosafe.database.contract_repository import ContractRepository
from cryptosafe.database.schema import init_db
from cryptosafe.database.user_repository import UserRepository


class TestContractFileRepository(unittest.TestCase):
    def setUp(self):
        self.conn = get_connection(":memory:")
        init_db(self.conn)

        users = UserRepository(self.conn)
        self.user_alice = users.create_user("alice", "fake-hash-alice")
        self.user_bob = users.create_user("bob", "fake-hash-bob")

        contracts = ContractRepository(self.conn)
        self.contract_alice = contracts.create_contract(
            contract_number="CTR-ALICE-101",
            title="Perjanjian Rahasia Alice",
            parties="Alice & Alpha Corp",
            status="Draft",
            created_by=self.user_alice.id,
        )
        self.contract_bob = contracts.create_contract(
            contract_number="CTR-BOB-201",
            title="Perjanjian Rahasia Bob",
            parties="Bob & Beta Ltd",
            status="Approved",
            created_by=self.user_bob.id,
        )

        self.repo = ContractFileRepository(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_create_and_get_contract_file(self):
        file_record = self.repo.create_file(
            contract_id=self.contract_alice.id,
            user_id=self.user_alice.id,
            original_filename="nda_document.pdf",
            encrypted_path="vault/12345abcdef.enc",
            size_bytes=10240,
            mime_type="application/pdf",
        )

        self.assertIsNotNone(file_record.id)
        self.assertEqual(file_record.original_filename, "nda_document.pdf")
        self.assertEqual(file_record.encrypted_path, "vault/12345abcdef.enc")
        self.assertEqual(file_record.size_bytes, 10240)
        self.assertEqual(file_record.mime_type, "application/pdf")
        self.assertEqual(file_record.algorithm, "ChaCha20-Poly1305")
        self.assertEqual(file_record.envelope_version, 1)

        fetched = self.repo.get_by_id(file_record.id, self.user_alice.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.id, file_record.id)
        self.assertEqual(fetched.original_filename, "nda_document.pdf")

    def test_list_by_contract(self):
        f1 = self.repo.create_file(
            contract_id=self.contract_alice.id,
            user_id=self.user_alice.id,
            original_filename="doc1.docx",
            encrypted_path="vault/enc1.enc",
            size_bytes=5000,
        )
        f2 = self.repo.create_file(
            contract_id=self.contract_alice.id,
            user_id=self.user_alice.id,
            original_filename="doc2.pdf",
            encrypted_path="vault/enc2.enc",
            size_bytes=8000,
        )

        files = self.repo.list_by_contract(self.contract_alice.id, self.user_alice.id)
        self.assertEqual(len(files), 2)
        self.assertEqual([f.id for f in files], [f1.id, f2.id])

    def test_user_cannot_access_other_users_files(self):
        file_record = self.repo.create_file(
            contract_id=self.contract_alice.id,
            user_id=self.user_alice.id,
            original_filename="secret_alice.txt",
            encrypted_path="vault/alice.enc",
            size_bytes=120,
        )

        # Bob attempts to get Alice's file
        bob_view = self.repo.get_by_id(file_record.id, self.user_bob.id)
        self.assertIsNone(bob_view)

        # Bob attempts to list files of Alice's contract
        bob_list = self.repo.list_by_contract(self.contract_alice.id, self.user_bob.id)
        self.assertEqual(len(bob_list), 0)

        # Bob attempts to delete Alice's file
        deleted = self.repo.delete_file(file_record.id, self.user_bob.id)
        self.assertFalse(deleted)

        # Alice's file is still present
        still_there = self.repo.get_by_id(file_record.id, self.user_alice.id)
        self.assertIsNotNone(still_there)

    def test_attach_file_to_unowned_contract_rejected(self):
        # Alice tries to attach file to Bob's contract
        with self.assertRaises(ValidationError):
            self.repo.create_file(
                contract_id=self.contract_bob.id,
                user_id=self.user_alice.id,
                original_filename="malicious.exe",
                encrypted_path="vault/bad.enc",
                size_bytes=100,
            )

    def test_invalid_arguments_rejected(self):
        # Empty filename
        with self.assertRaises(ValidationError):
            self.repo.create_file(
                contract_id=self.contract_alice.id,
                user_id=self.user_alice.id,
                original_filename="",
                encrypted_path="vault/x.enc",
                size_bytes=100,
            )

        # Empty encrypted path
        with self.assertRaises(ValidationError):
            self.repo.create_file(
                contract_id=self.contract_alice.id,
                user_id=self.user_alice.id,
                original_filename="file.txt",
                encrypted_path="   ",
                size_bytes=100,
            )

        # Negative size
        with self.assertRaises(ValidationError):
            self.repo.create_file(
                contract_id=self.contract_alice.id,
                user_id=self.user_alice.id,
                original_filename="file.txt",
                encrypted_path="vault/x.enc",
                size_bytes=-5,
            )

    def test_delete_file_success(self):
        f = self.repo.create_file(
            contract_id=self.contract_alice.id,
            user_id=self.user_alice.id,
            original_filename="todelete.txt",
            encrypted_path="vault/del.enc",
            size_bytes=20,
        )

        deleted = self.repo.delete_file(f.id, self.user_alice.id)
        self.assertTrue(deleted)

        fetched = self.repo.get_by_id(f.id, self.user_alice.id)
        self.assertIsNone(fetched)

    def test_cascade_delete_on_contract_deletion(self):
        f = self.repo.create_file(
            contract_id=self.contract_alice.id,
            user_id=self.user_alice.id,
            original_filename="cascade.txt",
            encrypted_path="vault/casc.enc",
            size_bytes=50,
        )

        # Delete contract
        contract_repo = ContractRepository(self.conn)
        contract_repo.delete_contract(self.contract_alice.id, self.user_alice.id)

        # Check file record is gone by cascade
        cursor = self.conn.execute("SELECT * FROM contract_files WHERE id = ?", (f.id,))
        self.assertIsNone(cursor.fetchone())


if __name__ == "__main__":
    unittest.main()

