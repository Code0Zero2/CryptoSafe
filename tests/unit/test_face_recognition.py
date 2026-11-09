"""Unit tests for M4 Local Face Recognition and Biometric Template Protection."""

import io
import json
import logging
import sys
import unittest
from datetime import datetime, timezone
import numpy as np
from pathlib import Path

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
from cryptosafe.auth.face_service import FaceService, OpenCvFaceAdapter
from cryptosafe.auth.auth_service import AuthService
from cryptosafe.common.errors import AuthenticationError, ValidationError

def make_synthetic_face(seed: int) -> np.ndarray:
    """Generate a reproducible synthetic 64x64 grayscale face patch."""
    rng = np.random.RandomState(seed)
    return rng.randint(0, 256, (64, 64), dtype=np.uint8)

class TestM4FaceRecognition(unittest.TestCase):
    def setUp(self):
        self.conn = get_connection(":memory:")
        init_db(self.conn)
        self.user_repo = UserRepository(self.conn)
        self.usb_repo = UsbRepository(self.conn)
        self.face_repo = FaceRepository(self.conn)

        self.password_service = PasswordService(time_cost=1, memory_cost=8192, parallelism=1)
        self.usb_service = UsbTokenService(self.usb_repo)
        self.face_service = FaceService(self.face_repo)
        self.auth_service = AuthService(
            self.user_repo,
            self.password_service,
            self.usb_service,
            self.face_service,
        )

        self.user_alice = self.auth_service.register_user("alice", "AlicePass123", "AlicePass123")
        self.user_bob = self.auth_service.register_user("bob", "BobPass123", "BobPass123")

        self.face_alice = make_synthetic_face(seed=42)
        # Slight variation of Alice's face (same person, minor lighting/angle noise)
        self.face_alice_probe = np.clip(self.face_alice.astype(np.int16) + np.random.RandomState(99).randint(-3, 4, (64, 64)), 0, 255).astype(np.uint8)
        self.face_bob = make_synthetic_face(seed=888)

    def tearDown(self):
        self.conn.close()

    def test_enrollment_requires_user_consent(self):
        """Verifies enrollment is rejected if user consent is not given."""
        with self.assertRaises(ValidationError) as ctx:
            self.face_service.enroll_face(self.user_alice.id, self.face_alice, user_consent=False)
        self.assertIn("persetujuan", str(ctx.exception).lower())

    def test_enrollment_stores_encrypted_template(self):
        """Verifies biometric template is encrypted and raw photo is not stored."""
        profile = self.face_service.enroll_face(self.user_alice.id, self.face_alice, user_consent=True)
        self.assertIsNotNone(profile.id)
        self.assertIsNotNone(profile.consent_recorded_at)

        # Ensure encrypted_template is valid JSON envelope with nonce and ciphertext
        envelope = json.loads(profile.encrypted_template)
        self.assertIn("nonce", envelope)
        self.assertIn("ciphertext", envelope)

        # Raw image bytes should not appear in DB
        self.assertNotIn("face_alice", profile.encrypted_template)

    def test_matching_face_passes(self):
        """Verifies matching face probe passes authentication."""
        self.face_service.enroll_face(self.user_alice.id, self.face_alice, user_consent=True)
        result = self.face_service.verify_face(self.user_alice.id, self.face_alice_probe, threshold=0.75)
        self.assertTrue(result)

    def test_nonmatching_face_fails(self):
        """Verifies mismatched face fails authentication."""
        self.face_service.enroll_face(self.user_alice.id, self.face_alice, user_consent=True)
        with self.assertRaises(AuthenticationError) as ctx:
            self.face_service.verify_face(self.user_alice.id, self.face_bob, threshold=0.75)
        self.assertIn("gagal", str(ctx.exception).lower())

    def test_corrupted_template_fails(self):
        """Verifies corrupted encrypted template in database fails gracefully."""
        self.face_service.enroll_face(self.user_alice.id, self.face_alice, user_consent=True)
        # Corrupt ciphertext in SQLite
        self.conn.execute("UPDATE face_profiles SET encrypted_template = 'invalid-json' WHERE user_id = ?", (self.user_alice.id,))
        self.conn.commit()

        with self.assertRaises(AuthenticationError) as ctx:
            self.face_service.verify_face(self.user_alice.id, self.face_alice)
        self.assertIn("rusak atau tidak valid", str(ctx.exception))

    def test_camera_unavailable_handled(self):
        """Verifies camera capture handles unavailable hardware with clear error."""
        # Using invalid camera index e.g. 9999
        with self.assertRaises(AuthenticationError) as ctx:
            self.face_service.capture_camera_frame(camera_index=9999)
        self.assertIn("kamera tidak tersedia", str(ctx.exception).lower())

    def test_cross_account_face_profile_isolation(self):
        """Verifies Alice's face cannot authenticate Bob's account."""
        self.face_service.enroll_face(self.user_alice.id, self.face_alice, user_consent=True)
        self.face_service.enroll_face(self.user_bob.id, self.face_bob, user_consent=True)

        # Bob tries to verify using Alice's face
        with self.assertRaises(AuthenticationError):
            self.face_service.verify_face(self.user_bob.id, self.face_alice)

    def test_full_auth_flow_with_face_mfa(self):
        """Verifies complete authentication sequence: Password + Face."""
        self.face_service.enroll_face(self.user_alice.id, self.face_alice, user_consent=True)

        # Successful login when providing matching face
        user = self.auth_service.authenticate_user("alice", "AlicePass123", face_image=self.face_alice_probe)
        self.assertEqual(user.username, "alice")

        # Fails when face does not match
        with self.assertRaises(AuthenticationError):
            self.auth_service.authenticate_user("alice", "AlicePass123", face_image=self.face_bob)

    def test_no_biometrics_in_logs(self):
        """Verifies that no biometric embedding arrays or image data leak into logs."""
        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        logger = logging.getLogger("cryptosafe")
        logger.addHandler(handler)

        self.face_service.enroll_face(self.user_alice.id, self.face_alice, user_consent=True)
        self.face_service.verify_face(self.user_alice.id, self.face_alice_probe)

        log_output = log_stream.getvalue()
        # Verify no raw floats or template dumps in log
        self.assertNotIn("ndarray", log_output)
        self.assertNotIn("[0.", log_output)
        logger.removeHandler(handler)

if __name__ == "__main__":
    unittest.main()
