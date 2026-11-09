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
from cryptosafe.gui.main_window import MainWindow
from cryptosafe.gui.login_page import LoginPage
from cryptosafe.gui.register_page import RegisterPage
from cryptosafe.gui.dashboard_page import DashboardPage
from cryptosafe.database.connection import get_connection
from cryptosafe.database.schema import init_db
from cryptosafe.database.user_repository import UserRepository
from cryptosafe.auth.password_service import PasswordService
from cryptosafe.auth.auth_service import AuthService

class TestM1GuiPrototype(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def setUp(self):
        # Isolate database in memory for testing
        self.conn = get_connection(":memory:")
        init_db(self.conn)
        self.user_repo = UserRepository(self.conn)
        self.pwd_service = PasswordService(time_cost=1, memory_cost=8192, parallelism=1)
        self.auth_service = AuthService(self.user_repo, self.pwd_service)

        # Pre-seed test user
        self.auth_service.register_user("alice", "Secret123!", "Secret123!")

        self.window = MainWindow(auth_service=self.auth_service)
        self.window.show()

    def tearDown(self):
        self.window.close()
        self.conn.close()

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

    def test_failed_login_shows_error(self):
        """Verifies wrong password displays error and remains on login page."""
        login_page = self.window.login_page
        login_page.username_input.setText("alice")
        login_page.password_input.setText("WrongPassword!")
        login_page.login_button.click()

        self.assertEqual(self.window.stack.currentIndex(), 0)
        self.assertTrue(login_page.error_label.isVisible())
        self.assertEqual(login_page.error_label.text(), "Username atau password salah.")

    def test_registration_and_login_flow(self):
        """Verifies registering a new account and then logging in."""
        login_page = self.window.login_page
        register_page = self.window.register_page
        dashboard_page = self.window.dashboard_page

        # Switch to register
        login_page.register_switch_button.click()
        self.assertEqual(self.window.stack.currentIndex(), 2)

        # Register new user bob
        register_page.username_input.setText("bob")
        register_page.password_input.setText("BobSecret123")
        register_page.confirm_password_input.setText("BobSecret123")
        register_page.register_button.click()

        # Should redirect back to Login with username prefilled
        self.assertEqual(self.window.stack.currentIndex(), 0)
        self.assertEqual(login_page.username_input.text(), "bob")

        # Login with bob's password
        login_page.password_input.setText("BobSecret123")
        login_page.login_button.click()

        # Should navigate to Dashboard
        self.assertEqual(self.window.stack.currentIndex(), 1)
        self.assertIn("bob", dashboard_page.user_label.text())

        # Click Logout
        dashboard_page.logout_button.click()
        self.assertEqual(self.window.stack.currentIndex(), 0)
        self.assertEqual(login_page.username_input.text(), "")

    def test_navigation_to_dashboard_and_logout(self):
        """Verifies demo navigation to dashboard with pre-seeded user and logout."""
        login_page = self.window.login_page
        dashboard_page = self.window.dashboard_page

        login_page.username_input.setText("alice")
        login_page.password_input.setText("Secret123!")
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
