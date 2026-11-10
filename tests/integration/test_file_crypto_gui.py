import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

src_dir = Path(__file__).resolve().parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from PySide6.QtWidgets import QApplication
from cryptosafe.gui.main_window import MainWindow
from cryptosafe.gui.dashboard_page import DashboardPage
from cryptosafe.gui.file_page import FilePage
from cryptosafe.database.connection import get_connection
from cryptosafe.database.schema import init_db
from cryptosafe.database.user_repository import UserRepository
from cryptosafe.auth.password_service import PasswordService
from cryptosafe.auth.auth_service import AuthService


class TestFileCryptoGuiIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def setUp(self):
        self.conn = get_connection(":memory:")
        init_db(self.conn)
        self.user_repo = UserRepository(self.conn)
        self.pwd_service = PasswordService(time_cost=1, memory_cost=8192, parallelism=1)
        self.auth_service = AuthService(self.user_repo, self.pwd_service)
        self.auth_service.register_user("alice", "Secret123!", "Secret123!")

        self.window = MainWindow(auth_service=self.auth_service)
        self.window.show()

        # Switch to dashboard
        self.window.dashboard_page.set_user("alice")
        self.window.stack.setCurrentIndex(1)

        self.temp_dir = tempfile.TemporaryDirectory()
        self.work_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.window.close()
        self.conn.close()
        self.temp_dir.cleanup()

    def test_navigation_to_file_page_and_back(self):
        # Starts on Dashboard
        self.assertIsInstance(self.window.stack.currentWidget(), DashboardPage)

        # Trigger navigation to File Crypto page
        self.window.dashboard_page.btn_open_file_crypto.click()
        self.assertIsInstance(self.window.stack.currentWidget(), FilePage)

        # Trigger back to Dashboard
        self.window.file_page.back_button.click()
        self.assertIsInstance(self.window.stack.currentWidget(), DashboardPage)

    def test_file_encryption_and_decryption_gui_workflow(self):
        # Navigate to FilePage
        self.window.dashboard_page.btn_open_file_crypto.click()
        file_page = self.window.file_page

        src_file = self.work_path / "original_doc.pdf"
        enc_file = self.work_path / "original_doc.pdf.enc"
        dec_file = self.work_path / "recovered_doc.pdf"

        original_bytes = b"%PDF-1.4 binary content demo data 12345" * 100
        src_file.write_bytes(original_bytes)

        # 1. Fill Encrypt tab inputs
        file_page.enc_source_input.setText(str(src_file))
        file_page.enc_dest_input.setText(str(enc_file))
        file_page._generate_random_key_clicked()

        aes_key = file_page.enc_key_input.text()
        self.assertEqual(len(aes_key), 64)

        # Click Encrypt
        file_page.encrypt_button.click()
        self.assertTrue(enc_file.exists())
        self.assertTrue(file_page.message_label.isVisible())

        # 2. Switch to Decrypt tab
        file_page.tabs.setCurrentIndex(1)
        file_page.dec_source_input.setText(str(enc_file))
        file_page.dec_dest_input.setText(str(dec_file))
        file_page.dec_key_input.setText(aes_key)

        # Click Decrypt
        file_page.decrypt_button.click()
        self.assertTrue(dec_file.exists())
        self.assertEqual(dec_file.read_bytes(), original_bytes)

        # 3. Test wrong key failure
        if dec_file.exists():
            dec_file.unlink()

        file_page.dec_key_input.setText("WrongKeyPassphrase123")
        file_page.decrypt_button.click()
        self.assertTrue(file_page.message_label.isVisible())
        self.assertFalse(dec_file.exists())


if __name__ == "__main__":
    unittest.main()

