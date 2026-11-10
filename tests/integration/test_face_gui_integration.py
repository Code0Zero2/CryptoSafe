"""Integration tests for Face Recognition GUI workflows (Enrollment, Login MFA, and Security Hardening)."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import numpy as np

os.environ["QT_QPA_PLATFORM"] = "offscreen"

src_dir = Path(__file__).resolve().parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
from cryptosafe.database.connection import get_connection
from cryptosafe.database.schema import init_db
from cryptosafe.database.user_repository import UserRepository
from cryptosafe.database.usb_repository import UsbRepository
from cryptosafe.database.face_repository import FaceRepository
from cryptosafe.auth.password_service import PasswordService
from cryptosafe.auth.usb_token_service import UsbTokenService
from cryptosafe.auth.face_service import FaceService
from cryptosafe.auth.rate_limiter import LoginRateLimiter
from cryptosafe.auth.session_manager import SessionManager
from cryptosafe.auth.auth_service import AuthService
from cryptosafe.gui.main_window import MainWindow
from cryptosafe.gui.face_capture_dialog import FaceCaptureDialog
from tests.unit.test_face_recognition import make_synthetic_face

class TestFaceGuiIntegration(unittest.TestCase):
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
        self.face_repo = FaceRepository(self.conn)

        self.pwd_service = PasswordService(time_cost=1, memory_cost=8192, parallelism=1)
        self.usb_service = UsbTokenService(self.usb_repo)
        self.face_service = FaceService(self.face_repo)
        self.rate_limiter = LoginRateLimiter(max_attempts=3, lockout_seconds=2)
        self.session_manager = SessionManager()

        self.auth_service = AuthService(
            user_repo=self.user_repo,
            password_service=self.pwd_service,
            usb_service=self.usb_service,
            face_service=self.face_service,
            rate_limiter=self.rate_limiter,
            session_manager=self.session_manager,
        )

        self.user_alice = self.auth_service.register_user("alice", "PassAlice123!", "PassAlice123!")
        self.user_bob = self.auth_service.register_user("bob", "PassBob123!", "PassBob123!")

        self.face_alice = make_synthetic_face(seed=42)
        self.face_bob = make_synthetic_face(seed=999)

        self.window = MainWindow(
            auth_service=self.auth_service,
            usb_service=self.usb_service,
            face_service=self.face_service,
        )

        self.info_patcher = patch("cryptosafe.gui.main_window.QMessageBox.information")
        self.warn_patcher = patch("cryptosafe.gui.main_window.QMessageBox.warning")
        self.mock_info = self.info_patcher.start()
        self.mock_warn = self.warn_patcher.start()

    def tearDown(self):
        self.info_patcher.stop()
        self.warn_patcher.stop()
        self.window.close()
        self.conn.close()

    @patch("cryptosafe.gui.main_window.QMessageBox.question", return_value=QMessageBox.Yes)
    @patch("cryptosafe.gui.main_window.QInputDialog.getText", return_value=("PassAlice123!", True))
    @patch("cryptosafe.gui.main_window.FaceCaptureDialog")
    def test_enrollment_flow_success(self, mock_dialog_cls, mock_get_text, mock_question):
        """Verifies full enrollment flow: consent -> password -> dialog capture -> profile stored."""
        self.window._current_user = self.user_alice

        mock_dialog_instance = MagicMock()
        mock_dialog_instance.exec.return_value = QDialog.DialogCode.Accepted
        mock_dialog_instance.captured_frame = self.face_alice
        mock_dialog_cls.return_value = mock_dialog_instance

        self.window._on_enroll_face_requested()

        mock_question.assert_called_once()
        mock_get_text.assert_called_once()
        mock_dialog_cls.assert_called_once_with(self.face_service, mode="enroll", parent=self.window)

        # Profile must be saved in database and active
        profile = self.face_repo.get_active_by_user_id(self.user_alice.id)
        self.assertIsNotNone(profile)
        self.assertTrue(self.face_service.has_active_profile(self.user_alice.id))
        self.assertIn("Terdaftar", self.window.dashboard_page.face_status_label.text())

    @patch("cryptosafe.gui.main_window.QMessageBox.question", return_value=QMessageBox.Yes)
    @patch("cryptosafe.gui.main_window.QInputDialog.getText", return_value=("WrongPass!", True))
    @patch("cryptosafe.gui.main_window.FaceCaptureDialog")
    def test_enrollment_aborts_on_invalid_password_without_opening_camera(
        self, mock_dialog_cls, mock_get_text, mock_question
    ):
        """Verifies enrollment aborts before camera viewfinder opens when password is wrong."""
        self.window._current_user = self.user_alice

        self.window._on_enroll_face_requested()

        mock_dialog_cls.assert_not_called()
        self.assertFalse(self.face_service.has_active_profile(self.user_alice.id))

    @patch("cryptosafe.gui.main_window.QMessageBox.question", return_value=QMessageBox.Yes)
    @patch("cryptosafe.gui.main_window.QInputDialog.getText", return_value=("PassAlice123!", True))
    @patch("cryptosafe.gui.main_window.FaceCaptureDialog")
    def test_enrollment_aborts_when_camera_dialog_cancelled(
        self, mock_dialog_cls, mock_get_text, mock_question
    ):
        """Verifies cancellation of FaceCaptureDialog does not store profile."""
        self.window._current_user = self.user_alice

        mock_dialog_instance = MagicMock()
        mock_dialog_instance.exec.return_value = QDialog.DialogCode.Rejected
        mock_dialog_instance.captured_frame = None
        mock_dialog_cls.return_value = mock_dialog_instance

        self.window._on_enroll_face_requested()

        self.assertFalse(self.face_service.has_active_profile(self.user_alice.id))

    def test_login_flow_without_face_mfa(self):
        """Verifies login proceeds directly without camera dialog for accounts without face biometrics."""
        with patch("cryptosafe.gui.main_window.FaceCaptureDialog") as mock_dialog_cls:
            self.window._on_login_requested("bob", "PassBob123!")
            mock_dialog_cls.assert_not_called()
            self.assertEqual(self.window._current_user.id, self.user_bob.id)
            self.assertEqual(self.window.stack.currentIndex(), 1)

    @patch("cryptosafe.gui.main_window.FaceCaptureDialog")
    def test_login_flow_with_face_mfa_success_single_factor_verifications(self, mock_dialog_cls):
        """Verifies each MFA factor (Password, USB, Face) is verified exactly ONCE."""
        # Enroll USB and Face for Alice
        temp_dir = tempfile.TemporaryDirectory()
        usb_dir = Path(temp_dir.name) / "alice_drive"
        usb_dir.mkdir(parents=True, exist_ok=True)
        _, token_file = self.usb_service.enroll_token(self.user_alice.id, usb_dir)

        self.face_service.enroll_face(
            self.user_alice.id,
            self.face_alice,
            user_consent=True,
            password="PassAlice123!",
        )

        mock_dialog_instance = MagicMock()
        mock_dialog_instance.exec.return_value = QDialog.DialogCode.Accepted
        mock_dialog_instance.captured_frame = self.face_alice
        mock_dialog_cls.return_value = mock_dialog_instance

        # Spy on verify_password, verify_token, and verify_face
        with patch.object(self.pwd_service, "verify_password", wraps=self.pwd_service.verify_password) as spy_pwd, \
             patch.object(self.usb_service, "detect_token_file", return_value=token_file), \
             patch.object(self.usb_service, "verify_token", wraps=self.usb_service.verify_token) as spy_usb, \
             patch.object(self.face_service, "verify_face", wraps=self.face_service.verify_face) as spy_face:

            self.window._on_login_requested("alice", "PassAlice123!")

            # Assert password verified exactly once
            self.assertEqual(spy_pwd.call_count, 1, "Password (Argon2id) must be verified exactly once")
            # Assert USB challenge verified exactly once
            self.assertEqual(spy_usb.call_count, 1, "USB challenge must be verified exactly once")
            # Assert Face verified exactly once
            self.assertEqual(spy_face.call_count, 1, "Face biometrics must be verified exactly once")

        mock_dialog_cls.assert_called_once_with(self.face_service, mode="login", parent=self.window)
        self.assertIsNotNone(self.window._current_user)
        self.assertEqual(self.window._current_user.username, "alice")
        self.assertEqual(self.window.stack.currentIndex(), 1)
        temp_dir.cleanup()

    @patch("cryptosafe.gui.main_window.FaceCaptureDialog")
    def test_login_flow_with_face_mfa_cancelled_does_not_increment_rate_limiter(self, mock_dialog_cls):
        """Verifies voluntary dialog cancellation creates no session and does NOT count as rate limiter failure."""
        self.face_service.enroll_face(
            self.user_alice.id,
            self.face_alice,
            user_consent=True,
            password="PassAlice123!",
        )

        mock_dialog_instance = MagicMock()
        mock_dialog_instance.exec.return_value = QDialog.DialogCode.Rejected
        mock_dialog_instance.captured_frame = None
        mock_dialog_cls.return_value = mock_dialog_instance

        self.assertEqual(self.rate_limiter._trackers["alice"].failure_count, 0)
        self.window._on_login_requested("alice", "PassAlice123!")

        self.assertIsNone(self.window._current_user)
        self.assertIn("dibatalkan", self.window.login_page.error_label.text().lower())
        self.assertEqual(self.window.stack.currentIndex(), 0)
        # Voluntary cancellation must not record credential failure on rate limiter
        self.assertEqual(
            self.rate_limiter._trackers["alice"].failure_count, 0,
            "Voluntary cancellation must not increment rate limiter failure count"
        )

    @patch("cryptosafe.gui.main_window.FaceCaptureDialog")
    def test_login_flow_with_face_mfa_mismatched_face_records_failure(self, mock_dialog_cls):
        """Verifies rejected face match increments rate limiter by exactly one."""
        self.face_service.enroll_face(
            self.user_alice.id,
            self.face_alice,
            user_consent=True,
            password="PassAlice123!",
        )

        mock_dialog_instance = MagicMock()
        mock_dialog_instance.exec.return_value = QDialog.DialogCode.Accepted
        # Provide Bob's face instead of Alice's
        mock_dialog_instance.captured_frame = self.face_bob
        mock_dialog_cls.return_value = mock_dialog_instance

        self.assertEqual(self.rate_limiter._trackers["alice"].failure_count, 0)
        self.window._on_login_requested("alice", "PassAlice123!")

        self.assertIsNone(self.window._current_user)
        self.assertIn("gagal", self.window.login_page.error_label.text().lower())
        self.assertEqual(self.window.stack.currentIndex(), 0)
        self.assertEqual(
            self.rate_limiter._trackers["alice"].failure_count, 1,
            "Mismatched face must record exactly 1 failure"
        )

    @patch("cryptosafe.gui.main_window.FaceCaptureDialog")
    def test_login_flow_aborts_on_invalid_password_before_camera(self, mock_dialog_cls):
        """Verifies camera dialog is never shown when password is wrong, and Argon2id checked once."""
        self.face_service.enroll_face(
            self.user_alice.id,
            self.face_alice,
            user_consent=True,
            password="PassAlice123!",
        )

        with patch.object(self.pwd_service, "verify_password", wraps=self.pwd_service.verify_password) as spy_pwd:
            self.window._on_login_requested("alice", "WrongPassword123!")
            self.assertEqual(spy_pwd.call_count, 1, "Password must be verified only once on failure")

        mock_dialog_cls.assert_not_called()
        self.assertIsNone(self.window._current_user)
        self.assertIn("salah", self.window.login_page.error_label.text().lower())
        self.assertEqual(self.rate_limiter._trackers["alice"].failure_count, 1)

    @patch("cryptosafe.gui.main_window.FaceCaptureDialog")
    def test_login_flow_aborts_on_missing_usb_before_camera(self, mock_dialog_cls):
        """Verifies camera dialog is never shown when USB token is missing."""
        temp_dir = tempfile.TemporaryDirectory()
        usb_dir = Path(temp_dir.name) / "alice_drive"
        usb_dir.mkdir(parents=True, exist_ok=True)
        self.usb_service.enroll_token(self.user_alice.id, usb_dir)

        self.face_service.enroll_face(
            self.user_alice.id,
            self.face_alice,
            user_consent=True,
            password="PassAlice123!",
        )

        # Ensure no USB token file is detected
        with patch.object(self.usb_service, "detect_token_file", return_value=None):
            self.window._on_login_requested("alice", "PassAlice123!")

        # Dialog must not have been shown
        mock_dialog_cls.assert_not_called()
        self.assertIsNone(self.window._current_user)
        self.assertIn("usb token", self.window.login_page.error_label.text().lower())
        self.assertEqual(self.rate_limiter._trackers["alice"].failure_count, 1)
        temp_dir.cleanup()

if __name__ == "__main__":
    unittest.main()
