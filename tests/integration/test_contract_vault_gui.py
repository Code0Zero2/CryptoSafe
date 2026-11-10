"""Integration tests for Contract File Vault GUI."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"

src_dir = Path(__file__).resolve().parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from PySide6.QtWidgets import QApplication, QMessageBox
from cryptosafe.auth.auth_service import AuthService
from cryptosafe.auth.password_service import PasswordService
from cryptosafe.crypto.file_crypto_service import FileCryptoService
from cryptosafe.crypto.text_crypto_service import TextCryptoService
from cryptosafe.database.connection import get_connection
from cryptosafe.database.contract_file_repository import ContractFileRepository
from cryptosafe.database.contract_file_service import ContractFileService
from cryptosafe.database.contract_repository import ContractRepository
from cryptosafe.database.encrypted_message_repository import EncryptedMessageRepository
from cryptosafe.database.encrypted_message_service import EncryptedMessageService
from cryptosafe.database.schema import init_db
from cryptosafe.database.user_repository import UserRepository
from cryptosafe.gui.main_window import MainWindow


class TestContractVaultGuiIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.vault_dir = Path(self.temp_dir.name) / "vault"
        self.work_dir = Path(self.temp_dir.name) / "work"
        self.work_dir.mkdir(parents=True, exist_ok=True)

        self.conn = get_connection(":memory:")
        init_db(self.conn)

        self.user_repo = UserRepository(self.conn)
        self.contract_repo = ContractRepository(self.conn)
        self.message_repo = EncryptedMessageRepository(self.conn)
        self.file_repo = ContractFileRepository(self.conn)

        self.pwd_service = PasswordService(time_cost=1, memory_cost=8192, parallelism=1)
        self.auth_service = AuthService(self.user_repo, self.pwd_service)
        self.text_crypto = TextCryptoService()
        self.file_crypto = FileCryptoService()
        self.message_service = EncryptedMessageService(self.message_repo, self.text_crypto)
        self.file_service = ContractFileService(
            repository=self.file_repo,
            crypto_service=self.file_crypto,
            storage_dir=self.vault_dir,
        )

        self.alice = self.auth_service.register_user("alice", "Secret123!", "Secret123!")
        self.bob = self.auth_service.register_user("bob", "Secret123!", "Secret123!")

        self.contract_alice = self.contract_repo.create_contract(
            contract_number="CTR-ALICE-VAULT",
            title="Alice Contract",
            parties="Alice & Co",
            created_by=self.alice.id,
            status="Draft",
        )
        self.contract_bob = self.contract_repo.create_contract(
            contract_number="CTR-BOB-VAULT",
            title="Bob Contract",
            parties="Bob & Inc",
            created_by=self.bob.id,
            status="Signed",
        )

        self.window = MainWindow(
            auth_service=self.auth_service,
            text_crypto_service=self.text_crypto,
            file_crypto_service=self.file_crypto,
            contract_repository=self.contract_repo,
            message_service=self.message_service,
            contract_file_service=self.file_service,
            conn=self.conn,
        )
        self.window.show()

    def tearDown(self):
        self.window.close()
        self.conn.close()
        self.temp_dir.cleanup()

    def _login(self, username: str = "alice", password: str = "Secret123!"):
        self.window.login_page.username_input.setText(username)
        self.window.login_page.password_input.setText(password)
        self.window.login_page.login_button.click()

    def test_vault_gui_controls_present_and_isolated(self):
        self._login("alice")
        page = self.window.contract_page

        # Ensure UI controls exist
        self.assertIsNotNone(page.file_table)
        self.assertIsNotNone(page.add_file_button)
        self.assertIsNotNone(page.download_file_button)
        self.assertIsNotNone(page.delete_file_button)

        self.assertEqual(page.file_table.columnCount(), 5)
        headers = [page.file_table.horizontalHeaderItem(i).text() for i in range(5)]
        self.assertIn("Nama Berkas", headers)
        self.assertIn("Ukuran", headers)
        self.assertIn("Algoritma", headers)

    def test_selection_populates_contract_vault_files(self):
        # Attach a file for Alice's contract programmatically
        doc_path = self.work_dir / "attachment_test.txt"
        doc_path.write_text("Rahasia perjanjian tingkat satu.")
        self.file_service.attach_file(
            contract_id=self.contract_alice.id,
            user_id=self.alice.id,
            source_path=doc_path,
            key_material="AlicePassKey1!",
        )

        self._login("alice")
        page = self.window.contract_page

        # Select Alice's contract row in contract_table
        self.assertEqual(page.contract_table.rowCount(), 1)
        page.contract_table.selectRow(0)

        # File table should now display the attached file
        self.assertEqual(page.file_table.rowCount(), 1)
        self.assertEqual(page.file_table.item(0, 1).text(), "attachment_test.txt")
        self.assertEqual(page.file_table.item(0, 3).text(), "ChaCha20-Poly1305")

    def test_add_download_and_delete_vault_file_gui(self):
        self._login("alice")
        page = self.window.contract_page
        page.contract_table.selectRow(0)

        test_file = self.work_dir / "invoice.pdf"
        test_file_content = b"%PDF-1.4\nConfidential invoice data"
        test_file.write_bytes(test_file_content)

        # 1. Add file attachment through GUI
        with patch("cryptosafe.gui.contract_page.QFileDialog.getOpenFileName", return_value=(str(test_file), "")), \
             patch("cryptosafe.gui.contract_page.QInputDialog.getText", return_value=("SecretPass123", True)), \
             patch("cryptosafe.gui.contract_page.QMessageBox.information"):
            page.add_file_button.click()

        self.assertEqual(page.file_table.rowCount(), 1)
        self.assertEqual(page.file_table.item(0, 1).text(), "invoice.pdf")

        # 2. Download / Decrypt file through GUI
        download_target = self.work_dir / "downloaded_invoice.pdf"
        page.file_table.selectRow(0)

        with patch("cryptosafe.gui.contract_page.QFileDialog.getSaveFileName", return_value=(str(download_target), "")), \
             patch("cryptosafe.gui.contract_page.QInputDialog.getText", return_value=("SecretPass123", True)), \
             patch("cryptosafe.gui.contract_page.QMessageBox.information"):
            page.download_file_button.click()

        self.assertTrue(download_target.is_file())
        self.assertEqual(download_target.read_bytes(), test_file_content)

        # 3. Delete file through GUI
        page.file_table.selectRow(0)
        with patch("cryptosafe.gui.contract_page.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes), \
             patch("cryptosafe.gui.contract_page.QMessageBox.information"):
            page.delete_file_button.click()

        self.assertEqual(page.file_table.rowCount(), 0)

    def test_user_switching_isolates_vault_files(self):
        # Alice has an attachment
        doc = self.work_dir / "alice_exclusive.txt"
        doc.write_text("Top secret Alice only")
        self.file_service.attach_file(
            contract_id=self.contract_alice.id,
            user_id=self.alice.id,
            source_path=doc,
            key_material="AliceSecret!",
        )

        # Alice logs in
        self._login("alice")
        page = self.window.contract_page
        page.contract_table.selectRow(0)
        self.assertEqual(page.file_table.rowCount(), 1)

        # Alice logs out
        self.window.dashboard_page.logout_button.click()
        self.assertEqual(page.file_table.rowCount(), 0)

        # Bob logs in
        self._login("bob")
        self.assertEqual(page.contract_table.rowCount(), 1)
        page.contract_table.selectRow(0)

        # Bob has no attachments on his contract, cannot see Alice's
        self.assertEqual(page.file_table.rowCount(), 0)


if __name__ == "__main__":
    unittest.main()

