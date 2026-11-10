import os
import sys
import unittest
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

src_dir = Path(__file__).resolve().parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from PySide6.QtWidgets import QApplication
from cryptosafe.gui.main_window import MainWindow
from cryptosafe.gui.dashboard_page import DashboardPage
from cryptosafe.gui.text_page import TextPage
from cryptosafe.database.connection import get_connection
from cryptosafe.database.schema import init_db
from cryptosafe.database.user_repository import UserRepository
from cryptosafe.auth.password_service import PasswordService
from cryptosafe.auth.auth_service import AuthService
from cryptosafe.crypto.key_manager import generate_random_aes_key


class TestTextCryptoGuiIntegration(unittest.TestCase):
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

        # Switch to dashboard page
        self.window.dashboard_page.set_user("alice")
        self.window.stack.setCurrentIndex(1)

    def tearDown(self):
        self.window.close()
        self.conn.close()

    def test_navigation_to_text_crypto_page_and_back(self):
        # Starts on Dashboard
        self.assertIsInstance(self.window.stack.currentWidget(), DashboardPage)

        # Trigger navigation to Text Crypto page
        self.window.dashboard_page.btn_open_text_crypto.click()
        self.assertIsInstance(self.window.stack.currentWidget(), TextPage)

        # Trigger back to Dashboard
        self.window.text_page.back_button.click()
        self.assertIsInstance(self.window.stack.currentWidget(), DashboardPage)

    def test_direct_hex_key_workflow(self):
        # Navigate to TextPage
        self.window.dashboard_page.btn_open_text_crypto.click()
        text_page = self.window.text_page

        # Fill encryption inputs
        original_text = "Dokumen Rahasia Operasi Alpha 2026!"
        vig_key = "KUNCI"
        text_page.enc_plaintext_input.setPlainText(original_text)
        text_page.enc_vig_key_input.setText(vig_key)

        # Input direct 64-hex AES key manually
        aes_key = generate_random_aes_key()
        text_page.enc_aes_key_input.setText(aes_key)
        self.assertEqual(len(aes_key), 64)

        # Perform encryption
        text_page.encrypt_button.click()
        ciphertext_json = text_page.enc_result_output.toPlainText()
        self.assertIn("CRYPTOSAFE_TEXT", ciphertext_json)
        self.assertIn("VIGENERE+AES-256-GCM", ciphertext_json)
        self.assertIn("DIRECT-AES-256", ciphertext_json)

        # Switch to Decryption tab
        text_page.tabs.setCurrentIndex(1)
        text_page.dec_envelope_input.setPlainText(ciphertext_json)
        text_page.dec_vig_key_input.setText(vig_key)
        text_page.dec_aes_key_input.setText(aes_key)

        # Perform decryption
        text_page.decrypt_button.click()
        recovered_text = text_page.dec_result_output.toPlainText()
        self.assertEqual(recovered_text, original_text)

        # Test failure on wrong AES key
        text_page.dec_aes_key_input.setText("WrongPassphrase123")
        text_page.decrypt_button.click()
        self.assertTrue(text_page.message_label.isVisible())
        self.assertEqual(text_page.dec_result_output.toPlainText(), "")

    def test_passphrase_workflow(self):
        # Navigate to TextPage
        self.window.dashboard_page.btn_open_text_crypto.click()
        text_page = self.window.text_page

        original_text = "Pesan teks dengan passphrase biasa"
        vig_key = "ALPHA"
        passphrase = "PasswordUserKuat2026!"

        text_page.enc_plaintext_input.setPlainText(original_text)
        text_page.enc_vig_key_input.setText(vig_key)
        text_page.enc_aes_key_input.setText(passphrase)

        # Perform encryption
        text_page.encrypt_button.click()
        ciphertext_json = text_page.enc_result_output.toPlainText()
        self.assertIn("PBKDF2-HMAC-SHA256", ciphertext_json)
        self.assertIn("iterations", ciphertext_json)

        # Switch to Decryption tab
        text_page.tabs.setCurrentIndex(1)
        text_page.dec_envelope_input.setPlainText(ciphertext_json)
        text_page.dec_vig_key_input.setText(vig_key)
        text_page.dec_aes_key_input.setText(passphrase)

        # Perform decryption
        text_page.decrypt_button.click()
        recovered_text = text_page.dec_result_output.toPlainText()
        self.assertEqual(recovered_text, original_text)

    def test_generate_key_button_workflow(self):
        # Navigate to TextPage
        self.window.dashboard_page.btn_open_text_crypto.click()
        text_page = self.window.text_page

        # Verify single button presence and label; old duplicate button is removed
        self.assertIsNotNone(text_page.generate_key_button)
        self.assertEqual(text_page.generate_key_button.text(), "Generate Key")
        self.assertFalse(hasattr(text_page, "gen_key_btn"))

        # Initial fields are empty
        text_page.clear_fields()
        self.assertEqual(text_page.enc_vig_key_input.text(), "")
        self.assertEqual(text_page.enc_aes_key_input.text(), "")

        # Click Generate Key button
        text_page.generate_key_button.click()

        vig_key = text_page.enc_vig_key_input.text()
        aes_key = text_page.enc_aes_key_input.text()

        # Both keys must be populated and distinct
        self.assertEqual(len(vig_key), 16)
        self.assertTrue(vig_key.isalpha())
        self.assertTrue(vig_key.isupper())

        self.assertEqual(len(aes_key), 64)
        self.assertNotEqual(vig_key, aes_key)

        # Warning message displayed informing user to save keys
        self.assertTrue(text_page.message_label.isVisible())
        self.assertIn("PERINGATAN", text_page.message_label.text().upper())

        # Test encryption using the generated keys
        secret_message = "Data Perjanjian Rahasia Bisnis 2026!"
        text_page.enc_plaintext_input.setPlainText(secret_message)
        text_page.encrypt_button.click()

        ciphertext = text_page.enc_result_output.toPlainText()
        self.assertIn("CRYPTOSAFE_TEXT", ciphertext)

        # Test decryption using the same keys
        text_page.tabs.setCurrentIndex(1)
        text_page.dec_envelope_input.setPlainText(ciphertext)
        text_page.dec_vig_key_input.setText(vig_key)
        text_page.dec_aes_key_input.setText(aes_key)
        text_page.decrypt_button.click()

        self.assertEqual(text_page.dec_result_output.toPlainText(), secret_message)

    def test_copy_key_buttons_workflow(self):
        self.window.dashboard_page.btn_open_text_crypto.click()
        text_page = self.window.text_page

        # Generate keys
        text_page.generate_key_button.click()
        vig_key = text_page.enc_vig_key_input.text()
        aes_key = text_page.enc_aes_key_input.text()

        # Copy Vigenere key
        text_page.copy_vig_key_button.click()
        clipboard = QApplication.clipboard()
        self.assertEqual(clipboard.text(), vig_key)
        self.assertIn("Vigenère", text_page.message_label.text())

        # Copy AES key
        text_page.copy_aes_key_button.click()
        self.assertEqual(clipboard.text(), aes_key)
        self.assertIn("AES", text_page.message_label.text())

        # When key input is empty
        text_page.enc_vig_key_input.clear()
        text_page.copy_vig_key_button.click()
        self.assertTrue(text_page.message_label.isVisible())


if __name__ == "__main__":
    unittest.main()
