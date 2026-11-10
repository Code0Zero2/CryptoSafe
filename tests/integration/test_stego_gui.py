import os
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image
import numpy as np

os.environ["QT_QPA_PLATFORM"] = "offscreen"

src_dir = Path(__file__).resolve().parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from PySide6.QtWidgets import QApplication
from cryptosafe.gui.main_window import MainWindow
from cryptosafe.gui.dashboard_page import DashboardPage
from cryptosafe.gui.stego_page import StegoPage
from cryptosafe.database.connection import get_connection
from cryptosafe.database.schema import init_db
from cryptosafe.database.user_repository import UserRepository
from cryptosafe.auth.password_service import PasswordService
from cryptosafe.auth.auth_service import AuthService


class TestStegoGuiIntegration(unittest.TestCase):
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

        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        self.window = MainWindow(auth_service=self.auth_service)
        self.window.show()

        # Switch to dashboard page
        self.window.dashboard_page.set_user("alice")
        self.window.stack.setCurrentIndex(1)

    def tearDown(self):
        self.window.close()
        self.conn.close()
        self.temp_dir.cleanup()

    def _create_png(self, name: str, width: int = 100, height: int = 100, mode: str = "RGB") -> Path:
        img_path = self.temp_path / name
        channels = 4 if mode == "RGBA" else 3
        arr = np.random.randint(0, 256, (height, width, channels), dtype=np.uint8)
        img = Image.fromarray(arr, mode=mode)
        img.save(img_path, format="PNG")
        return img_path

    def test_navigation_to_stego_page_and_back(self):
        # Starts on Dashboard
        self.assertIsInstance(self.window.stack.currentWidget(), DashboardPage)

        # Trigger navigation to Steganography page
        self.window.dashboard_page.btn_open_steganography.click()
        self.assertIsInstance(self.window.stack.currentWidget(), StegoPage)
        self.assertEqual(self.window.stack.currentIndex(), 6)

        # Trigger back to Dashboard
        self.window.stego_page.back_button.click()
        self.assertIsInstance(self.window.stack.currentWidget(), DashboardPage)
        self.assertEqual(self.window.stack.currentIndex(), 1)

    def test_key_generator_and_copy(self):
        page = self.window.stego_page
        self.window.dashboard_page.btn_open_steganography.click()

        # Initially keys are empty
        self.assertEqual(page.embed_vig_key.text(), "")
        self.assertEqual(page.embed_aes_key.text(), "")

        # Click Generate Keys
        page.embed_gen_key_btn.click()
        vig_key = page.embed_vig_key.text()
        aes_key = page.embed_aes_key.text()

        self.assertTrue(len(vig_key) >= 8)
        self.assertEqual(len(aes_key), 64)

        # Click Copy Keys (should not raise)
        page.embed_copy_vig_btn.click()
        page.embed_copy_aes_btn.click()

    def test_embed_and_extract_gui_flow(self):
        page = self.window.stego_page
        self.window.dashboard_page.btn_open_steganography.click()

        in_png = self._create_png("source.png", 120, 120)
        out_png = self.temp_path / "stego_output.png"
        secret_msg = "Rahasia Integritas GUI Steganografi CryptoSafe 2026"

        # Fill Embed fields
        page.embed_src_input.setText(str(in_png))
        page.embed_msg_input.setPlainText(secret_msg)
        page.embed_gen_key_btn.click()
        vig_key = page.embed_vig_key.text()
        aes_key = page.embed_aes_key.text()
        page.embed_dst_input.setText(str(out_png))

        # Perform embedding
        page.embed_action_btn.click()

        # Verify output created and feedback shown
        self.assertTrue(out_png.exists())
        self.assertIn("disisipkan", page.message_label.text())

        # Switch to Extract tab
        page.tabs.setCurrentIndex(1)
        page.extract_src_input.setText(str(out_png))
        page.extract_vig_key.setText(vig_key)
        page.extract_aes_key.setText(aes_key)

        # Perform extraction
        page.extract_action_btn.click()

        # Verify extracted text and feedback
        self.assertEqual(page.extract_output.toPlainText(), secret_msg)
        self.assertIn("berhasil diekstrak", page.message_label.text())

    def test_embed_validation_error_feedback(self):
        page = self.window.stego_page
        self.window.dashboard_page.btn_open_steganography.click()

        # Leave everything empty and click embed
        page.embed_action_btn.click()
        self.assertIn("berkas citra sumber dan berkas output", page.message_label.text())

    def test_extract_validation_error_feedback(self):
        page = self.window.stego_page
        self.window.dashboard_page.btn_open_steganography.click()
        page.tabs.setCurrentIndex(1)

        # Leave everything empty and click extract
        page.extract_action_btn.click()
        self.assertIn("berkas citra stego", page.message_label.text())


if __name__ == "__main__":
    unittest.main()
