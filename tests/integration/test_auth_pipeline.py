"""Integration tests for Milestone M5: Sequential Multi-Factor Authentication Pipeline, Throttling, and Sessions."""

import sys
import tempfile
import unittest
from pathlib import Path
import numpy as np

src_dir = Path(__file__).resolve().parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

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
from cryptosafe.common.errors import AuthenticationError
from tests.unit.test_face_recognition import make_synthetic_face

class TestM5AuthenticationPipeline(unittest.TestCase):
    def setUp(self):
        self.conn = get_connection(":memory:")
        init_db(self.conn)
        self.user_repo = UserRepository(self.conn)
        self.usb_repo = UsbRepository(self.conn)
        self.face_repo = FaceRepository(self.conn)

        self.password_service = PasswordService(time_cost=1, memory_cost=8192, parallelism=1)
        self.usb_service = UsbTokenService(self.usb_repo)
        self.face_service = FaceService(self.face_repo)
        self.rate_limiter = LoginRateLimiter(max_attempts=3, lockout_seconds=2)
        self.session_manager = SessionManager()

        self.auth_service = AuthService(
            user_repo=self.user_repo,
            password_service=self.password_service,
            usb_service=self.usb_service,
            face_service=self.face_service,
            rate_limiter=self.rate_limiter,
            session_manager=self.session_manager,
        )

        self.temp_dir = tempfile.TemporaryDirectory()
        self.usb_dir_alice = Path(self.temp_dir.name) / "alice_drive"
        self.usb_dir_alice.mkdir(parents=True, exist_ok=True)
        self.usb_dir_bob = Path(self.temp_dir.name) / "bob_drive"
        self.usb_dir_bob.mkdir(parents=True, exist_ok=True)

        # Register users
        self.user_alice = self.auth_service.register_user("alice", "PassAlice123!", "PassAlice123!")
        self.user_bob = self.auth_service.register_user("bob", "PassBob123!", "PassBob123!")

        # Enroll Factor 2 (USB) and Factor 3 (Face) for Alice
        _, self.token_alice = self.usb_service.enroll_token(self.user_alice.id, self.usb_dir_alice)
        self.face_alice = make_synthetic_face(seed=101)
        self.face_alice_probe = np.clip(self.face_alice.astype(int) + np.random.randint(-3, 4, (64, 64)), 0, 255).astype(np.uint8)
        self.face_service.enroll_face(self.user_alice.id, self.face_alice, user_consent=True)

        # Enroll Bob with distinct USB and Face
        _, self.token_bob = self.usb_service.enroll_token(self.user_bob.id, self.usb_dir_bob)
        self.face_bob = make_synthetic_face(seed=202)
        self.face_service.enroll_face(self.user_bob.id, self.face_bob, user_consent=True)

    def tearDown(self):
        self.conn.close()
        self.temp_dir.cleanup()

    def test_full_mfa_success(self):
        """Verifies full 3-factor sequence (Password -> USB -> Face) passes and creates session."""
        self.assertFalse(self.auth_service.session_manager.is_authenticated())

        user = self.auth_service.authenticate_user(
            username="alice",
            password="PassAlice123!",
            usb_token_path=self.token_alice,
            face_image=self.face_alice_probe,
        )

        self.assertEqual(user.username, "alice")
        self.assertTrue(self.auth_service.session_manager.is_authenticated())
        session = self.auth_service.session_manager.get_current_session()
        self.assertEqual(session.username, "alice")
        self.assertEqual(session.user_id, self.user_alice.id)

    def test_step1_wrong_password_fails_early(self):
        """Verifies wrong password fails at step 1 without creating session."""
        with self.assertRaises(AuthenticationError) as ctx:
            self.auth_service.authenticate_user(
                username="alice",
                password="WrongPassword!",
                usb_token_path=self.token_alice,
                face_image=self.face_alice_probe,
            )
        self.assertEqual(str(ctx.exception), "Username atau password salah.")
        self.assertFalse(self.auth_service.session_manager.is_authenticated())

    def test_step2_missing_or_wrong_usb_fails(self):
        """Verifies step 2 fails when USB token is missing or from wrong drive."""
        with self.assertRaises(AuthenticationError) as ctx:
            self.auth_service.authenticate_user(
                username="alice",
                password="PassAlice123!",
                usb_token_path=self.usb_dir_alice / "non_existent.key",
                face_image=self.face_alice_probe,
            )
        self.assertFalse(self.auth_service.session_manager.is_authenticated())

    def test_step3_mismatched_face_fails(self):
        """Verifies step 3 fails when face does not match enrolled template."""
        with self.assertRaises(AuthenticationError) as ctx:
            self.auth_service.authenticate_user(
                username="alice",
                password="PassAlice123!",
                usb_token_path=self.token_alice,
                face_image=self.face_bob,  # Using Bob's face for Alice
            )
        self.assertIn("gagal", str(ctx.exception).lower())
        self.assertFalse(self.auth_service.session_manager.is_authenticated())

    def test_cross_account_factors_rejected(self):
        """Verifies Alice cannot use Bob's USB token or Bob's face."""
        # Alice tries using Bob's USB token
        with self.assertRaises(AuthenticationError):
            self.auth_service.authenticate_user(
                username="alice",
                password="PassAlice123!",
                usb_token_path=self.token_bob,
                face_image=self.face_alice_probe,
            )

        # Bob tries using Alice's USB token
        with self.assertRaises(AuthenticationError):
            self.auth_service.authenticate_user(
                username="bob",
                password="PassBob123!",
                usb_token_path=self.token_alice,
                face_image=self.face_bob,
            )

    def test_login_throttling_and_lockout(self):
        """Verifies repeated login failures trigger rate limiting / temporary lockout."""
        # Max attempts is 3 in setUp
        for _ in range(3):
            with self.assertRaises(AuthenticationError):
                self.auth_service.authenticate_user("alice", "WrongPass1")

        # 4th attempt must be locked out
        with self.assertRaises(AuthenticationError) as ctx:
            self.auth_service.authenticate_user("alice", "PassAlice123!")
        self.assertIn("terlalu banyak percobaan login gagal", str(ctx.exception).lower())

    def test_logout_clears_session(self):
        """Verifies logout destroys active session."""
        self.auth_service.authenticate_user(
            username="alice",
            password="PassAlice123!",
            usb_token_path=self.token_alice,
            face_image=self.face_alice_probe,
        )
        self.assertTrue(self.auth_service.session_manager.is_authenticated())

        self.auth_service.logout()
        self.assertFalse(self.auth_service.session_manager.is_authenticated())
        self.assertIsNone(self.auth_service.session_manager.get_current_session())

    def test_failed_login_clears_prior_active_session(self):
        """Verifies a new failed authentication attempt invalidates any prior active session."""
        # 1. Establish an active session for Alice
        self.auth_service.authenticate_user(
            username="alice",
            password="PassAlice123!",
            usb_token_path=self.token_alice,
            face_image=self.face_alice_probe,
        )
        self.assertTrue(self.auth_service.session_manager.is_authenticated())
        self.assertEqual(self.auth_service.session_manager.get_current_session().username, "alice")

        # 2. Attempt login with bad credentials (e.g. wrong password for Bob)
        with self.assertRaises(AuthenticationError):
            self.auth_service.authenticate_user(
                username="bob",
                password="WrongPassword123!",
            )

        # 3. Prior session must be terminated
        self.assertFalse(self.auth_service.session_manager.is_authenticated())
        self.assertIsNone(self.auth_service.session_manager.get_current_session())

    def test_logout_does_not_log_session_id(self):
        """Verifies logout logs user identifier without leaking the session_id token."""
        import io
        import logging

        self.auth_service.authenticate_user(
            username="alice",
            password="PassAlice123!",
            usb_token_path=self.token_alice,
            face_image=self.face_alice_probe,
        )
        session = self.auth_service.session_manager.get_current_session()
        self.assertIsNotNone(session)
        secret_session_id = session.session_id

        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        auth_logger = logging.getLogger("cryptosafe.auth")
        auth_logger.setLevel(logging.INFO)
        auth_logger.addHandler(handler)
        try:
            self.auth_service.logout()
            log_output = log_stream.getvalue()
            # Must not log session_id
            self.assertNotIn(secret_session_id, log_output)
            # Must mention username
            self.assertIn("alice", log_output)
        finally:
            auth_logger.removeHandler(handler)

if __name__ == "__main__":
    unittest.main()
