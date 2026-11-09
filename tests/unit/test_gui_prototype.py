import os
import sys
import unittest
from pathlib import Path

# Ensure offscreen rendering for headless testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

src_dir = Path(__file__).resolve().parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from PySide6.QtWidgets import QApplication
from cryptosafe.app import create_app
from cryptosafe.gui.main_window import MainWindow
from cryptosafe.gui.login_page import LoginPage
from cryptosafe.gui.dashboard_page import DashboardPage

class TestM1GuiPrototype(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def setUp(self):
        self.window = MainWindow()
        self.window.show()

    def tearDown(self):
        self.window.close()

    def test_initial_page_is_login(self):
        """Verifies app opens to login page."""
        self.assertEqual(self.window.stack.currentIndex(), 0)
        self.assertIsInstance(self.window.stack.currentWidget(), LoginPage)

    def test_login_fields_and_demo_labels_exist(self):
        """Verifies inputs and simulated status indicators with DEMO labels exist."""
        login_page = self.window.login_page
        self.assertIsNotNone(login_page.username_input)
        self.assertIsNotNone(login_page.password_input)
        self.assertIn("SIMULASI", login_page.usb_status_label.text().upper())
        self.assertIn("SIMULASI", login_page.face_status_label.text().upper())
        self.assertIn("DEMO", login_page.usb_status_label.text().upper())
        self.assertIn("DEMO", login_page.face_status_label.text().upper())

    def test_empty_credentials_rejected(self):
        """Verifies empty username/password inputs are rejected."""
        login_page = self.window.login_page
        login_page.username_input.setText("")
        login_page.password_input.setText("")
        login_page.login_button.click()

        self.assertEqual(self.window.stack.currentIndex(), 0)
        self.assertTrue(login_page.error_label.isVisible())
        self.assertIn("tidak boleh kosong", login_page.error_label.text())

    def test_navigation_to_dashboard_and_logout(self):
        """Verifies demo navigation to dashboard and logout navigation."""
        login_page = self.window.login_page
        dashboard_page = self.window.dashboard_page

        login_page.username_input.setText("alice")
        login_page.password_input.setText("secret123")
        login_page.login_button.click()

        # Should navigate to Dashboard
        self.assertEqual(self.window.stack.currentIndex(), 1)
        self.assertIsInstance(self.window.stack.currentWidget(), DashboardPage)
        self.assertIn("alice", dashboard_page.user_label.text())

        # Click Logout
        dashboard_page.logout_button.click()

        # Should return to Login page
        self.assertEqual(self.window.stack.currentIndex(), 0)
        self.assertEqual(login_page.username_input.text(), "")
        self.assertEqual(login_page.password_input.text(), "")

if __name__ == "__main__":
    unittest.main()
