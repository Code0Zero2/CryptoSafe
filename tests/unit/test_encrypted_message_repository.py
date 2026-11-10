
import unittest

from cryptosafe.database.connection import get_connection
from cryptosafe.database.schema import init_db
from cryptosafe.database.user_repository import UserRepository
from cryptosafe.database.contract_repository import ContractRepository
from cryptosafe.database.encrypted_message_repository import (
    EncryptedMessageRepository,
)
from cryptosafe.common.errors import ValidationError


class TestEncryptedMessageRepository(unittest.TestCase):
    def setUp(self):
        self.conn = get_connection(":memory:")
        init_db(self.conn)

        users = UserRepository(self.conn)
        self.user = users.create_user("alice", "fake-hash")
        self.other_user = users.create_user("bob", "fake-hash")

        contracts = ContractRepository(self.conn)
        self.contract = contracts.create_contract(
            contract_number="CTR-001",
            title="Perjanjian Kerja Sama",
            parties="PT Alpha dan PT Beta",
            start_date="2026-11-10",
            end_date="2027-11-10",
            status="Draft",
            created_by=self.user.id,
        )

        self.messages = EncryptedMessageRepository(self.conn)

    def tearDown(self):
        self.conn.close()

    def _create_message(self):
        return self.messages.create_message(
            contract_id=self.contract.id,
            user_id=self.user.id,
            content_type="note",
            label="Catatan awal",
            ciphertext='{"magic":"CRYPTOSAFE_TEXT","ciphertext":"encrypted-data"}',
        )

    def test_create_encrypted_message(self):
        message = self._create_message()

        self.assertEqual(message.contract_id, self.contract.id)
        self.assertEqual(message.user_id, self.user.id)
        self.assertEqual(message.content_type, "note")
        self.assertEqual(message.label, "Catatan awal")
        self.assertIn("encrypted-data", message.ciphertext)
        self.assertEqual(message.algorithm, "VIGENERE+AES-256-GCM")

    def test_list_messages_by_contract(self):
        self._create_message()
        self.messages.create_message(
            contract_id=self.contract.id,
            user_id=self.user.id,
            content_type="clause",
            label="Klausul kerahasiaan",
            ciphertext="encrypted-clause",
        )

        result = self.messages.list_by_contract(
            self.contract.id, self.user.id
        )

        self.assertEqual(len(result), 2)

    def test_get_message_by_id(self):
        message = self._create_message()

        result = self.messages.get_by_id(message.id, self.user.id)

        self.assertIsNotNone(result)
        self.assertEqual(result.id, message.id)

    def test_other_user_cannot_read_message(self):
        message = self._create_message()

        result = self.messages.get_by_id(
            message.id, self.other_user.id
        )

        self.assertIsNone(result)

    def test_other_user_cannot_create_message_for_contract(self):
        with self.assertRaises(ValidationError):
            self.messages.create_message(
                contract_id=self.contract.id,
                user_id=self.other_user.id,
                content_type="note",
                label="Catatan ilegal",
                ciphertext="encrypted-data",
            )

    def test_update_message(self):
        message = self._create_message()

        updated = self.messages.update_message(
            message_id=message.id,
            user_id=self.user.id,
            content_type="draft",
            label="Draf revisi",
            ciphertext="updated-encrypted-data",
        )

        self.assertEqual(updated.content_type, "draft")
        self.assertEqual(updated.label, "Draf revisi")
        self.assertEqual(updated.ciphertext, "updated-encrypted-data")

    def test_invalid_content_type_rejected(self):
        with self.assertRaises(ValidationError):
            self.messages.create_message(
                contract_id=self.contract.id,
                user_id=self.user.id,
                content_type="unknown",
                label="Catatan",
                ciphertext="encrypted-data",
            )

    def test_empty_ciphertext_rejected(self):
        with self.assertRaises(ValidationError):
            self.messages.create_message(
                contract_id=self.contract.id,
                user_id=self.user.id,
                content_type="note",
                label="Catatan",
                ciphertext="",
            )

    def test_delete_message(self):
        message = self._create_message()

        deleted = self.messages.delete_message(
            message.id, self.user.id
        )

        self.assertTrue(deleted)
        self.assertIsNone(
            self.messages.get_by_id(message.id, self.user.id)
        )


if __name__ == "__main__":
    unittest.main()
