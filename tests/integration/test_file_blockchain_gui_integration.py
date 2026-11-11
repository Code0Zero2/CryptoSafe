"""Integration tests for Contract File Vault with Blockchain SHA-256 via GUI."""

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"

src_dir = Path(__file__).resolve().parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from PySide6.QtWidgets import QApplication, QFileDialog, QInputDialog, QMessageBox
from cryptosafe.auth.auth_service import AuthService
from cryptosafe.auth.password_service import PasswordService
from cryptosafe.crypto.blockchain_service import BlockchainService
from cryptosafe.crypto.file_crypto_service import FileCryptoService
from cryptosafe.crypto.text_crypto_service import TextCryptoService
from cryptosafe.database.blockchain_repository import BlockchainRepository
from cryptosafe.database.connection import get_connection
from cryptosafe.database.contract_file_repository import ContractFileRepository
from cryptosafe.database.contract_file_service import ContractFileService
from cryptosafe.database.contract_repository import ContractRepository
from cryptosafe.database.contract_service import ContractService
from cryptosafe.database.encrypted_message_repository import EncryptedMessageRepository
from cryptosafe.database.encrypted_message_service import EncryptedMessageService
from cryptosafe.database.schema import init_db
from cryptosafe.database.user_repository import UserRepository
from cryptosafe.gui.main_window import MainWindow


class TestFileBlockchainGuiIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_dir = Path(self.temp_dir.name) / "vault"
        self.work_dir = Path(self.temp_dir.name) / "work"
        self.work_dir.mkdir(parents=True, exist_ok=True)

        self.conn = get_connection(":memory:")
        init_db(self.conn)

        self.user_repo = UserRepository(self.conn)
        self.pwd_service = PasswordService(time_cost=1, memory_cost=8192, parallelism=1)
        self.auth_service = AuthService(self.user_repo, self.pwd_service)

        self.alice = self.auth_service.register_user("alice", "Secret123!", "Secret123!")

        self.blockchain_repo = BlockchainRepository(self.conn)
        self.blockchain_service = BlockchainService(self.blockchain_repo)
        self.blockchain_service.ensure_genesis_block()

        self.contract_repo = ContractRepository(self.conn)
        self.contract_service = ContractService(
            contract_repository=self.contract_repo,
            blockchain_service=self.blockchain_service,
        )

        self.text_crypto = TextCryptoService()
        self.message_repo = EncryptedMessageRepository(self.conn)
        self.message_service = EncryptedMessageService(
            repository=self.message_repo,
            crypto_service=self.text_crypto,
            blockchain_service=self.blockchain_service,
        )

        self.file_repo = ContractFileRepository(self.conn)
        self.file_crypto = FileCryptoService()
        self.contract_file_service = ContractFileService(
            repository=self.file_repo,
            crypto_service=self.file_crypto,
            storage_dir=self.storage_dir,
            blockchain_service=self.blockchain_service,
        )

        # Create contract for Alice
        self.contract = self.contract_service.create_contract(
            contract_number="CTR-GUI-VAULT-1",
            title="Kontrak GUI Vault",
            parties="Alice & Partner Corp",
            created_by=self.alice.id,
            status="Draft",
        )

        self.window = MainWindow(
            auth_service=self.auth_service,
            contract_service=self.contract_service,
            message_service=self.message_service,
            contract_file_service=self.contract_file_service,
            blockchain_service=self.blockchain_service,
            text_crypto_service=self.text_crypto,
            file_crypto_service=self.file_crypto,
            conn=self.conn,
        )
        self.window.show()

        # Log in Alice and navigate to contract page
        self.window._on_login_requested("alice", "Secret123!")
        self.window.dashboard_page.btn_open_contract.click()

        # Create sample document to attach
        self.sample_file = self.work_dir / "attachment_test.docx"
        self.sample_content = b"Binary PKZIP contract docx payload byte content 998877"
        self.sample_file.write_bytes(self.sample_content)
        self.vault_key = "VaultSecretKey2026"

    def tearDown(self):
        self.window.close()
        self.conn.close()
        self.temp_dir.cleanup()

    def test_gui_attach_decrypt_and_delete_file_records_blockchain(self):
        """Verify attaching, decrypting, and deleting files via ContractPage creates valid blocks."""
        page = self.window.contract_page
        page.refresh_contracts()
        self.assertEqual(page.contract_table.rowCount(), 1)
        page.contract_table.selectRow(0)
        page.contract_table.setCurrentCell(0, 0)

        # 1. Attach File via GUI
        with patch.object(QFileDialog, "getOpenFileName", return_value=(str(self.sample_file), "")), \
             patch.object(QInputDialog, "getText", return_value=(self.vault_key, True)), \
             patch.object(QMessageBox, "information"):
            page.add_file_button.click()

        # File table must now have 1 row
        self.assertEqual(page.file_table.rowCount(), 1)
        file_id = page.file_table.item(0, 0).data(0x0100)

        # Blockchain must contain FILE_ATTACHED block
        blocks = self.blockchain_repo.find_by_asset_id(f"file:{file_id}")
        self.assertEqual(len(blocks), 1)

        attach_block = blocks[0]
        self.assertEqual(attach_block.event_type, "FILE_ATTACHED")
        payload = json.loads(attach_block.payload_json)
        self.assertNotIn("original_filename", payload)
        self.assertNotIn("attachment_test.docx", attach_block.payload_json)
        self.assertEqual(payload["action"], "ATTACHED")

        # 2. Export / Decrypt File via GUI
        page.file_table.selectRow(0)
        page.file_table.setCurrentCell(0, 0)
        exported_path = self.work_dir / "decrypted_output.docx"

        with patch.object(QFileDialog, "getSaveFileName", return_value=(str(exported_path), "")), \
             patch.object(QInputDialog, "getText", return_value=(self.vault_key, True)), \
             patch.object(QMessageBox, "information"):
            page.download_file_button.click()

        self.assertTrue(exported_path.is_file())
        self.assertEqual(exported_path.read_bytes(), self.sample_content)

        # 3. Delete File via GUI
        page.file_table.selectRow(0)
        page.file_table.setCurrentCell(0, 0)

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes), \
             patch.object(QMessageBox, "information"):
            page.delete_file_button.click()

        # File table must now be empty
        self.assertEqual(page.file_table.rowCount(), 0)

        # Blockchain must contain FILE_DELETED block
        blocks_after = self.blockchain_repo.find_by_asset_id(f"file:{file_id}")
        self.assertEqual(len(blocks_after), 2)

        del_block = blocks_after[1]
        self.assertEqual(del_block.event_type, "FILE_DELETED")
        del_payload = json.loads(del_block.payload_json)
        self.assertNotIn("original_filename", del_payload)
        self.assertNotIn("attachment_test.docx", del_block.payload_json)
        self.assertEqual(del_payload["action"], "DELETED")

        # Verify chain integrity
        ver = self.blockchain_service.verify_chain_integrity()
        self.assertTrue(ver.is_valid)


if __name__ == "__main__":
    unittest.main()
