"""Integration tests for USB Flashdisk Authentication, Enrollment, and Revocation Workflow."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

os.environ["QT_QPA_PLATFORM"] = "offscreen"

src_dir = Path(__file__).resolve().parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
from cryptosafe.gui.main_window import MainWindow
from cryptosafe.gui.dashboard_page import DashboardPage
from cryptosafe.gui.usb_dialog import UsbEnrollDialog
from cryptosafe.database.connection import get_connection
from cryptosafe.database.schema import init_db
from cryptosafe.database.user_repository import UserRepository
from cryptosafe.database.usb_repository import UsbRepository
from cryptosafe.auth.password_service import PasswordService
from cryptosafe.auth.usb_token_service import (
    UsbTokenService,
    TOKEN_DIR_NAME,
    TOKEN_FILENAME,
    UsbDriveInfo,
)
from cryptosafe.auth.auth_service import AuthService
from cryptosafe.auth.session_manager import SessionManager
from cryptosafe.common.errors import AuthenticationError


class TestUsbFlashdiskIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def setUp(self):
        self.conn = get_connection(":memory:")
        init_db(self.conn)
        self.user_repo = UserRepository(self.conn)
        self.usb_repo = UsbRepository(self.conn)
        self.pwd_service = PasswordService(time_cost=1, memory_cost=8192, parallelism=1)
        self.usb_service = UsbTokenService(self.usb_repo)
        self.session_manager = SessionManager()
        self.auth_service = AuthService(
            user_repo=self.user_repo,
            password_service=self.pwd_service,
            usb_service=self.usb_service,
            session_manager=self.session_manager,
        )

        self.alice = self.auth_service.register_user("alice", "AlicePass123!", "AlicePass123!")
        self.bob = self.auth_service.register_user("bob", "BobPass123!", "BobPass123!")

        self.temp_dir = tempfile.TemporaryDirectory()
        self.flashdisk_alice = Path(self.temp_dir.name) / "flashdisk_alice"
        self.flashdisk_alice.mkdir(parents=True, exist_ok=True)

        self.window = MainWindow(
            auth_service=self.auth_service,
            usb_service=self.usb_service,
            conn=self.conn,
        )
        self.window.show()

    def tearDown(self):
        self.window.close()
        self.conn.close()
        self.temp_dir.cleanup()

    def test_user_without_usb_logs_in_normally(self):
        """Verifies that an account without USB enrolled logs in with password only."""
        self.assertFalse(self.usb_service.has_active_token(self.bob.id))

        user = self.auth_service.authenticate_user("bob", "BobPass123!")
        self.assertEqual(user.username, "bob")
        session = self.session_manager.get_current_session()
        self.assertIsNotNone(session)
        self.assertEqual(session.user_id, self.bob.id)

    def test_flashdisk_enrollment_dialog_and_non_destructive_creation(self):
        """Verifies enrollment creates .cryptosafe/token.dat without touching existing files."""
        # 1. Place pre-existing user files on the flashdisk
        existing_doc = self.flashdisk_alice / "rencana_kerja.pdf"
        existing_doc.write_bytes(b"%PDF-1.4 sample content")
        existing_note = self.flashdisk_alice / "catatan.txt"
        existing_note.write_text("Catatan pribadi pengguna flashdisk", encoding="utf-8")

        # 2. Switch window to Alice's dashboard
        self.window._current_user = self.alice
        self.window.dashboard_page.set_user("alice")
        self.window.stack.setCurrentIndex(1)

        # 3. Test dialog interaction directly
        mock_drives = [
            UsbDriveInfo(
                root_path=self.flashdisk_alice,
                label="KINGSTON_16GB",
                drive_type="USB Removable",
                is_removable=True,
                has_token=False,
            )
        ]

        with patch.object(self.usb_service, "get_available_drives", return_value=mock_drives):
            dialog = UsbEnrollDialog(self.usb_service, "alice", parent=self.window)
            dialog.pwd_input.setText("AlicePass123!")
            dialog._on_submit()
            self.assertEqual(dialog.selected_path, self.flashdisk_alice)
            self.assertEqual(dialog.confirmed_password, "AlicePass123!")

        # 4. Perform enrollment through MainWindow handler with mocks for dialog and message box
        with patch("cryptosafe.gui.main_window.UsbEnrollDialog") as MockDialog, \
             patch.object(QMessageBox, "information") as mock_info:

            mock_instance = MagicMock()
            mock_instance.exec.return_value = QDialog.DialogCode.Accepted
            mock_instance.selected_path = self.flashdisk_alice
            mock_instance.confirmed_password = "AlicePass123!"
            MockDialog.return_value = mock_instance

            self.window._on_enroll_usb_requested()

            # Verify dialog was triggered and success box shown
            mock_info.assert_called_once()
            self.assertIn("berhasil", mock_info.call_args[0][2].lower())

        # 5. Check token file and existing files
        token_path = self.flashdisk_alice / TOKEN_DIR_NAME / TOKEN_FILENAME
        self.assertTrue(token_path.exists())
        self.assertTrue(existing_doc.exists())
        self.assertEqual(existing_doc.read_bytes(), b"%PDF-1.4 sample content")
        self.assertTrue(existing_note.exists())
        self.assertEqual(existing_note.read_text(encoding="utf-8"), "Catatan pribadi pengguna flashdisk")

        # 6. Verify Alice now has active USB token
        self.assertTrue(self.usb_service.has_active_token(self.alice.id))
        self.assertIn("Terdaftar", self.window.dashboard_page.usb_token_status_label.text())
        self.assertEqual(self.window.dashboard_page.enroll_usb_btn.text(), "Ganti Token (Re-enroll)")

    def test_flashdisk_enrollment_rejected_with_wrong_password(self):
        """Verifies enrollment is rejected when user enters incorrect password."""
        self.window._current_user = self.alice

        with patch("cryptosafe.gui.main_window.UsbEnrollDialog") as MockDialog, \
             patch.object(QMessageBox, "warning") as mock_warn:

            mock_instance = MagicMock()
            mock_instance.exec.return_value = QDialog.DialogCode.Accepted
            mock_instance.selected_path = self.flashdisk_alice
            mock_instance.confirmed_password = "WrongPassword999!"
            MockDialog.return_value = mock_instance

            self.window._on_enroll_usb_requested()

            mock_warn.assert_called_once()
            self.assertIn("kata sandi", mock_warn.call_args[0][2].lower())

        self.assertFalse(self.usb_service.has_active_token(self.alice.id))

    def test_login_flow_enforces_usb_when_enrolled(self):
        """Verifies login succeeds with USB and fails when flashdisk is missing/unplugged."""
        # Enroll USB for Alice
        _, token_path = self.usb_service.enroll_token(self.alice.id, self.flashdisk_alice)
        self.assertTrue(self.usb_service.has_active_token(self.alice.id))

        # 1. Login with valid token succeeds
        user = self.auth_service.authenticate_user(
            "alice",
            "AlicePass123!",
            usb_token_path=token_path,
        )
        self.assertEqual(user.username, "alice")
        session = self.session_manager.get_current_session()
        self.assertIsNotNone(session)
        self.assertEqual(session.user_id, self.alice.id)

        # 2. Login without token or missing token fails
        missing_token = self.flashdisk_alice / "unplugged_token.dat"
        with self.assertRaises(AuthenticationError) as ctx:
            self.auth_service.authenticate_user(
                "alice",
                "AlicePass123!",
                usb_token_path=missing_token,
            )
        self.assertIn("memerlukan usb token", str(ctx.exception).lower())

    def test_revocation_requires_password_and_deactivates_token(self):
        """Verifies revocation requires password confirmation and updates state."""
        self.usb_service.enroll_token(self.alice.id, self.flashdisk_alice)
        self.assertTrue(self.usb_service.has_active_token(self.alice.id))

        self.window._current_user = self.alice
        self.window.dashboard_page.set_user("alice")
        self.window.dashboard_page.set_usb_token_status(True, "Token ID: test")

        # 1. Attempt revocation with incorrect password
        with patch("PySide6.QtWidgets.QInputDialog.getText", return_value=("WrongPass!", True)), \
             patch.object(QMessageBox, "warning") as mock_warn:

            self.window._on_revoke_usb_requested()
            mock_warn.assert_called_once()
            self.assertIn("kata sandi", mock_warn.call_args[0][2].lower())

        # Still active
        self.assertTrue(self.usb_service.has_active_token(self.alice.id))

        # 2. Revoke with correct password
        with patch("PySide6.QtWidgets.QInputDialog.getText", return_value=("AlicePass123!", True)), \
             patch.object(QMessageBox, "information") as mock_info:

            self.window._on_revoke_usb_requested()
            mock_info.assert_called_once()
            self.assertIn("berhasil dicabut", mock_info.call_args[0][2].lower())

        # Now inactive
        self.assertFalse(self.usb_service.has_active_token(self.alice.id))
        self.assertIn("Belum Terdaftar", self.window.dashboard_page.usb_token_status_label.text())
        self.assertEqual(self.window.dashboard_page.enroll_usb_btn.text(), "Enroll USB")


if __name__ == "__main__":
    unittest.main()
