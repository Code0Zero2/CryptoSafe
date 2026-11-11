"""Unit tests for EncryptedMessageService Blockchain SHA-256 integration."""

import hashlib
import json
import sqlite3
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

src_dir = Path(__file__).resolve().parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from cryptosafe.common.errors import CryptoOperationError, ValidationError
from cryptosafe.crypto.blockchain_service import BlockchainService
from cryptosafe.crypto.text_crypto_service import TextCryptoService
from cryptosafe.database.blockchain_repository import BlockchainRepository
from cryptosafe.database.connection import get_connection
from cryptosafe.database.contract_repository import ContractRepository
from cryptosafe.database.encrypted_message_repository import EncryptedMessageRepository
from cryptosafe.database.encrypted_message_service import EncryptedMessageService
from cryptosafe.database.schema import init_db
from cryptosafe.database.user_repository import UserRepository


class TestEncryptedMessageBlockchain(unittest.TestCase):
    def setUp(self):
        self.conn = get_connection(":memory:")
        init_db(self.conn)

        self.user_repo = UserRepository(self.conn)
        self.alice = self.user_repo.create_user("alice", "hash_alice")
        self.bob = self.user_repo.create_user("bob", "hash_bob")

        self.contract_repo = ContractRepository(self.conn)
        self.contract = self.contract_repo.create_contract(
            contract_number="CTR-NOTE-001",
            title="Kontrak Catatan Rahasia",
            parties="Alice & Mitra",
            created_by=self.alice.id,
            status="Draft",
        )

        self.blockchain_repo = BlockchainRepository(self.conn)
        self.blockchain_service = BlockchainService(self.blockchain_repo)
        self.blockchain_service.ensure_genesis_block()

        self.text_crypto = TextCryptoService()
        self.message_repo = EncryptedMessageRepository(self.conn)
        self.service = EncryptedMessageService(
            repository=self.message_repo,
            crypto_service=self.text_crypto,
            blockchain_service=self.blockchain_service,
        )

        self.vigenere_key = "KUNCI_VIGENERE"
        self.aes_key = "correct-horse-battery-staple-passphrase"
        self.plaintext = "Klausul kerahasiaan tingkat tinggi: dilarang membocorkan data."

    def tearDown(self):
        self.conn.close()

    def test_create_encrypted_message_generates_note_created_event(self):
        """Verify creating an encrypted note records NOTE_CREATED block with ciphertext hash."""
        message = self.service.create_encrypted_message(
            contract_id=self.contract.id,
            user_id=self.alice.id,
            content_type="clause",
            label="Klausul Kerahasiaan",
            plaintext=self.plaintext,
            vigenere_key=self.vigenere_key,
            aes_key_material=self.aes_key,
        )

        self.assertIsNotNone(message)
        self.assertEqual(message.label, "Klausul Kerahasiaan")

        # Check blockchain block
        blocks = self.blockchain_repo.find_by_asset_id(f"note:{message.id}")
        self.assertEqual(len(blocks), 1)

        block = blocks[0]
        self.assertEqual(block.event_type, "NOTE_CREATED")
        self.assertEqual(block.created_by, self.alice.id)

        # Verify asset_hash matches SHA-256 of the stored ciphertext (NOT plaintext)
        expected_hash = hashlib.sha256(message.ciphertext.encode("utf-8")).hexdigest().lower()
        self.assertEqual(block.asset_hash, expected_hash)

        # Ensure plaintext is definitely NOT the hashed content
        plaintext_hash = hashlib.sha256(self.plaintext.encode("utf-8")).hexdigest().lower()
        self.assertNotEqual(block.asset_hash, plaintext_hash)

        # Check payload
        payload = json.loads(block.payload_json)
        self.assertEqual(payload["contract_id"], self.contract.id)
        self.assertEqual(payload["note_id"], message.id)
        self.assertEqual(payload["content_type"], "clause")
        self.assertEqual(payload["label"], "Klausul Kerahasiaan")
        self.assertEqual(payload["action"], "CREATED")

        # Verify chain integrity
        ver = self.blockchain_service.verify_chain_integrity()
        self.assertTrue(ver.is_valid)

    def test_update_encrypted_message_records_note_updated_event(self):
        """Verify updating an encrypted note records NOTE_UPDATED with the new ciphertext hash."""
        msg1 = self.service.create_encrypted_message(
            contract_id=self.contract.id,
            user_id=self.alice.id,
            content_type="draft",
            label="Draft Awal",
            plaintext=self.plaintext,
            vigenere_key=self.vigenere_key,
            aes_key_material=self.aes_key,
        )

        old_cipher = msg1.ciphertext
        new_plaintext = "Klausul revisi final yang disetujui bersama."

        msg2 = self.service.update_encrypted_message(
            message_id=msg1.id,
            user_id=self.alice.id,
            content_type="clause",
            label="Klausul Final",
            plaintext=new_plaintext,
            vigenere_key=self.vigenere_key,
            aes_key_material=self.aes_key,
        )

        self.assertNotEqual(msg2.ciphertext, old_cipher)
        self.assertEqual(msg2.label, "Klausul Final")

        # Check blockchain blocks for this note
        blocks = self.blockchain_repo.find_by_asset_id(f"note:{msg1.id}")
        self.assertEqual(len(blocks), 2)  # 1 created + 1 updated

        b_created, b_updated = blocks
        self.assertEqual(b_created.event_type, "NOTE_CREATED")
        self.assertEqual(b_updated.event_type, "NOTE_UPDATED")

        # Updated asset_hash must match new ciphertext
        expected_new_hash = hashlib.sha256(msg2.ciphertext.encode("utf-8")).hexdigest().lower()
        self.assertEqual(b_updated.asset_hash, expected_new_hash)

        payload = json.loads(b_updated.payload_json)
        self.assertEqual(payload["action"], "UPDATED")
        self.assertEqual(payload["label"], "Klausul Final")

        ver = self.blockchain_service.verify_chain_integrity()
        self.assertTrue(ver.is_valid)

    def test_delete_message_records_last_ciphertext_hash(self):
        """Verify deleting an encrypted note records NOTE_DELETED with the last ciphertext hash."""
        msg = self.service.create_encrypted_message(
            contract_id=self.contract.id,
            user_id=self.alice.id,
            content_type="note",
            label="Catatan Sementara",
            plaintext="Catatan yang akan dihapus.",
            vigenere_key=self.vigenere_key,
            aes_key_material=self.aes_key,
        )

        last_ciphertext = msg.ciphertext
        expected_hash = hashlib.sha256(last_ciphertext.encode("utf-8")).hexdigest().lower()

        deleted = self.service.delete_message(msg.id, self.alice.id)
        self.assertTrue(deleted)

        # Message must no longer exist in repository
        self.assertIsNone(self.message_repo.get_by_id(msg.id, self.alice.id))

        # Check blockchain blocks
        blocks = self.blockchain_repo.find_by_asset_id(f"note:{msg.id}")
        self.assertEqual(len(blocks), 2)  # 1 created + 1 deleted

        b_del = blocks[1]
        self.assertEqual(b_del.event_type, "NOTE_DELETED")
        self.assertEqual(b_del.asset_hash, expected_hash)

        payload = json.loads(b_del.payload_json)
        self.assertEqual(payload["action"], "DELETED")
        self.assertEqual(payload["note_id"], msg.id)

        ver = self.blockchain_service.verify_chain_integrity()
        self.assertTrue(ver.is_valid)

    def test_append_failure_rolls_back_note_creation(self):
        """Verify if append_block fails, note insertion is completely rolled back."""
        with patch.object(
            self.blockchain_service,
            "append_block",
            side_effect=CryptoOperationError("Blockchain full"),
        ):
            with self.assertRaises(CryptoOperationError):
                self.service.create_encrypted_message(
                    contract_id=self.contract.id,
                    user_id=self.alice.id,
                    content_type="note",
                    label="Gagal Simpan",
                    plaintext=self.plaintext,
                    vigenere_key=self.vigenere_key,
                    aes_key_material=self.aes_key,
                )

        # Note must NOT exist in DB
        messages = self.service.list_by_contract(self.contract.id, self.alice.id)
        self.assertEqual(len(messages), 0)

    def test_append_failure_rolls_back_note_update(self):
        """Verify if append_block fails during update, note retains old ciphertext."""
        msg = self.service.create_encrypted_message(
            contract_id=self.contract.id,
            user_id=self.alice.id,
            content_type="note",
            label="Versi Asli",
            plaintext=self.plaintext,
            vigenere_key=self.vigenere_key,
            aes_key_material=self.aes_key,
        )
        orig_cipher = msg.ciphertext

        with patch.object(
            self.blockchain_service,
            "append_block",
            side_effect=CryptoOperationError("Append error"),
        ):
            with self.assertRaises(CryptoOperationError):
                self.service.update_encrypted_message(
                    message_id=msg.id,
                    user_id=self.alice.id,
                    content_type="clause",
                    label="Versi Gagal",
                    plaintext="Teks Baru Gagal",
                    vigenere_key=self.vigenere_key,
                    aes_key_material=self.aes_key,
                )

        # Message must retain original ciphertext and label
        fresh = self.message_repo.get_by_id(msg.id, self.alice.id)
        self.assertEqual(fresh.ciphertext, orig_cipher)
        self.assertEqual(fresh.label, "Versi Asli")

    def test_append_failure_rolls_back_note_deletion(self):
        """Verify if append_block fails during deletion, note is NOT deleted from DB."""
        msg = self.service.create_encrypted_message(
            contract_id=self.contract.id,
            user_id=self.alice.id,
            content_type="note",
            label="Pertahankan",
            plaintext=self.plaintext,
            vigenere_key=self.vigenere_key,
            aes_key_material=self.aes_key,
        )

        with patch.object(
            self.blockchain_service,
            "append_block",
            side_effect=CryptoOperationError("Disk failure"),
        ):
            with self.assertRaises(CryptoOperationError):
                self.service.delete_message(msg.id, self.alice.id)

        # Note must STILL exist in database
        fresh = self.message_repo.get_by_id(msg.id, self.alice.id)
        self.assertIsNotNone(fresh)

    def test_validation_failure_produces_no_block(self):
        """Verify empty plaintext or invalid inputs do not produce blockchain blocks."""
        initial_blocks = self.blockchain_repo.get_blocks_count()

        with self.assertRaises(ValidationError):
            self.service.create_encrypted_message(
                contract_id=self.contract.id,
                user_id=self.alice.id,
                content_type="note",
                label="Kosong",
                plaintext="   ",
                vigenere_key=self.vigenere_key,
                aes_key_material=self.aes_key,
            )

        with self.assertRaises(ValidationError):
            self.service.create_encrypted_message(
                contract_id=self.contract.id,
                user_id=self.alice.id,
                content_type="invalid_type",
                label="Bad Type",
                plaintext="Valid Text",
                vigenere_key=self.vigenere_key,
                aes_key_material=self.aes_key,
            )

        self.assertEqual(self.blockchain_repo.get_blocks_count(), initial_blocks)

    def test_ownership_enforcement(self):
        """Verify non-owner cannot decrypt, update, or delete note, producing no blocks."""
        msg = self.service.create_encrypted_message(
            contract_id=self.contract.id,
            user_id=self.alice.id,
            content_type="note",
            label="Alice Secret",
            plaintext=self.plaintext,
            vigenere_key=self.vigenere_key,
            aes_key_material=self.aes_key,
        )
        initial_blocks = self.blockchain_repo.get_blocks_count()

        # Bob attempts to decrypt Alice's note
        with self.assertRaises(ValidationError):
            self.service.get_decrypted_message(
                msg.id, self.bob.id, self.vigenere_key, self.aes_key,
            )

        # Bob attempts to update Alice's note
        with self.assertRaises(ValidationError):
            self.service.update_encrypted_message(
                msg.id, self.bob.id, "note", "Hacked", "Fake text", self.vigenere_key, self.aes_key,
            )

        # Bob attempts to delete Alice's note
        result = self.service.delete_message(msg.id, self.bob.id)
        self.assertFalse(result)

        # No new blocks added
        self.assertEqual(self.blockchain_repo.get_blocks_count(), initial_blocks)

    def test_payload_contains_no_sensitive_or_plaintext_data(self):
        """Verify blockchain payloads never leak plaintext notes, passwords, or keys."""
        msg = self.service.create_encrypted_message(
            contract_id=self.contract.id,
            user_id=self.alice.id,
            content_type="note",
            label="Audit Zero Knowledge",
            plaintext=self.plaintext,
            vigenere_key=self.vigenere_key,
            aes_key_material=self.aes_key,
        )

        blocks = self.blockchain_repo.find_by_asset_id(f"note:{msg.id}")
        self.assertGreater(len(blocks), 0)

        for b in blocks:
            raw_payload = b.payload_json
            payload = json.loads(raw_payload)

            self.assertNotIn("plaintext", payload)
            self.assertNotIn(self.plaintext, raw_payload)
            self.assertNotIn(self.vigenere_key, raw_payload)
            self.assertNotIn(self.aes_key, raw_payload)
            self.assertNotIn("password", payload)
            self.assertNotIn("key", payload)


if __name__ == "__main__":
    unittest.main()
