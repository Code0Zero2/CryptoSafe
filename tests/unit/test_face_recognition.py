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

from unittest.mock import patch, MagicMock
from cryptosafe.database.connection import get_connection
from cryptosafe.database.schema import init_db
from cryptosafe.database.user_repository import UserRepository
from cryptosafe.database.usb_repository import UsbRepository
from cryptosafe.database.face_repository import FaceRepository
from cryptosafe.auth.password_service import PasswordService
from cryptosafe.auth.usb_token_service import UsbTokenService
from cryptosafe.auth.face_service import (
    FaceService,
    OpenCvFaceAdapter,
    MIN_PBKDF2_ITERATIONS,
    MAX_PBKDF2_ITERATIONS,
    compute_face_aad,
)
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
            self.face_service.enroll_face(
                self.user_alice.id,
                self.face_alice,
                user_consent=False,
                password="AlicePass123",
            )
        self.assertIn("persetujuan", str(ctx.exception).lower())

    def test_enrollment_requires_password_or_key(self):
        """Verifies enrollment is rejected if password or key is missing (no ephemeral fallback)."""
        with self.assertRaises(ValidationError) as ctx:
            self.face_service.enroll_face(
                self.user_alice.id,
                self.face_alice,
                user_consent=True,
                password=None,
            )
        self.assertIn("kata sandi", str(ctx.exception).lower())

    def test_enrollment_stores_encrypted_template(self):
        """Verifies biometric template is encrypted and raw photo is not stored."""
        profile = self.face_service.enroll_face(
            self.user_alice.id,
            self.face_alice,
            user_consent=True,
            password="AlicePass123",
        )
        self.assertIsNotNone(profile.id)
        self.assertIsNotNone(profile.consent_recorded_at)

        # Ensure encrypted_template is valid JSON envelope with KDF, salt, nonce, and ciphertext
        envelope = json.loads(profile.encrypted_template)
        self.assertIn("nonce", envelope)
        self.assertIn("ciphertext", envelope)
        self.assertIn("salt", envelope)
        self.assertEqual(envelope.get("kdf"), "PBKDF2-HMAC-SHA256")
        self.assertEqual(envelope.get("algorithm"), "AES-256-GCM")
        self.assertEqual(envelope.get("iterations"), 600_000)

        # Raw image bytes should not appear in DB
        self.assertNotIn("face_alice", profile.encrypted_template)

    def test_matching_face_passes(self):
        """Verifies matching face probe passes authentication."""
        self.face_service.enroll_face(
            self.user_alice.id,
            self.face_alice,
            user_consent=True,
            password="AlicePass123",
        )
        result = self.face_service.verify_face(
            self.user_alice.id,
            self.face_alice_probe,
            password="AlicePass123",
            threshold=0.75,
        )
        self.assertTrue(result)

    def test_persistence_across_service_instances(self):
        """Verifies template can be decrypted by a brand new FaceService instance after app restart."""
        # 1. Enroll using first service instance
        service_instance_1 = FaceService(self.face_repo)
        service_instance_1.enroll_face(
            self.user_alice.id,
            self.face_alice,
            user_consent=True,
            password="AlicePass123",
        )

        # 2. Simulate app restart: drop service_instance_1, instantiate service_instance_2
        del service_instance_1
        service_instance_2 = FaceService(self.face_repo)

        # 3. Verification must succeed with the new instance
        result = service_instance_2.verify_face(
            self.user_alice.id,
            self.face_alice_probe,
            password="AlicePass123",
            threshold=0.75,
        )
        self.assertTrue(result)

    def test_wrong_password_fails_decryption(self):
        """Verifies wrong password fails to decrypt template and rejects authentication."""
        self.face_service.enroll_face(
            self.user_alice.id,
            self.face_alice,
            user_consent=True,
            password="AlicePass123",
        )
        with self.assertRaises(AuthenticationError) as ctx:
            self.face_service.verify_face(
                self.user_alice.id,
                self.face_alice_probe,
                password="WrongPassword999!",
            )
        self.assertIn("tidak dapat didekripsi", str(ctx.exception).lower())

    def test_missing_password_during_verification_fails(self):
        """Verifies verification fails if password is missing."""
        self.face_service.enroll_face(
            self.user_alice.id,
            self.face_alice,
            user_consent=True,
            password="AlicePass123",
        )
        with self.assertRaises(AuthenticationError) as ctx:
            self.face_service.verify_face(
                self.user_alice.id,
                self.face_alice_probe,
                password=None,
            )
        self.assertIn("kata sandi", str(ctx.exception).lower())

    def test_nonmatching_face_fails(self):
        """Verifies mismatched face fails authentication even with correct password."""
        self.face_service.enroll_face(
            self.user_alice.id,
            self.face_alice,
            user_consent=True,
            password="AlicePass123",
        )
        with self.assertRaises(AuthenticationError) as ctx:
            self.face_service.verify_face(
                self.user_alice.id,
                self.face_bob,
                password="AlicePass123",
                threshold=0.75,
            )
        self.assertIn("gagal", str(ctx.exception).lower())

    def test_corrupted_template_fails(self):
        """Verifies corrupted encrypted template in database fails gracefully."""
        self.face_service.enroll_face(
            self.user_alice.id,
            self.face_alice,
            user_consent=True,
            password="AlicePass123",
        )
        # Corrupt ciphertext in SQLite
        self.conn.execute("UPDATE face_profiles SET encrypted_template = 'invalid-json' WHERE user_id = ?", (self.user_alice.id,))
        self.conn.commit()

        with self.assertRaises(AuthenticationError) as ctx:
            self.face_service.verify_face(self.user_alice.id, self.face_alice, password="AlicePass123")
        self.assertIn("rusak atau tidak valid", str(ctx.exception))

    def test_camera_unavailable_handled(self):
        """Verifies camera capture handles unavailable hardware with clear error."""
        # Using invalid camera index e.g. 9999
        with self.assertRaises(AuthenticationError) as ctx:
            self.face_service.capture_camera_frame(camera_index=9999)
        self.assertIn("kamera tidak tersedia", str(ctx.exception).lower())

    def test_cross_account_face_profile_isolation(self):
        """Verifies Alice's face cannot authenticate Bob's account."""
        self.face_service.enroll_face(
            self.user_alice.id,
            self.face_alice,
            user_consent=True,
            password="AlicePass123",
        )
        self.face_service.enroll_face(
            self.user_bob.id,
            self.face_bob,
            user_consent=True,
            password="BobPass123",
        )

        # Bob tries to verify using Alice's face with Bob's password
        with self.assertRaises(AuthenticationError):
            self.face_service.verify_face(
                self.user_bob.id,
                self.face_alice,
                password="BobPass123",
            )

    def test_re_enrollment_uses_fresh_salt_and_nonce(self):
        """Verifies that re-enrolling generates unique random salt and nonce."""
        prof1 = self.face_service.enroll_face(
            self.user_alice.id,
            self.face_alice,
            user_consent=True,
            password="AlicePass123",
        )
        env1 = json.loads(prof1.encrypted_template)

        prof2 = self.face_service.enroll_face(
            self.user_alice.id,
            self.face_alice,
            user_consent=True,
            password="AlicePass123",
        )
        env2 = json.loads(prof2.encrypted_template)

        self.assertNotEqual(env1["salt"], env2["salt"])
        self.assertNotEqual(env1["nonce"], env2["nonce"])
        self.assertNotEqual(env1["ciphertext"], env2["ciphertext"])

    def test_rekey_face_profile_on_password_change(self):
        """Verifies rekeying face profile when user changes their password."""
        self.face_service.enroll_face(
            self.user_alice.id,
            self.face_alice,
            user_consent=True,
            password="OldPassword123!",
        )

        # Re-key template with new password
        self.face_service.rekey_face_profile(
            self.user_alice.id,
            old_password="OldPassword123!",
            new_password="NewPassword456!",
        )

        # Old password no longer decrypts
        with self.assertRaises(AuthenticationError):
            self.face_service.verify_face(
                self.user_alice.id,
                self.face_alice_probe,
                password="OldPassword123!",
            )

        # New password succeeds
        self.assertTrue(
            self.face_service.verify_face(
                self.user_alice.id,
                self.face_alice_probe,
                password="NewPassword456!",
            )
        )

    def test_revocation_prevents_verification(self):
        """Verifies revoked face profile cannot be used for verification."""
        self.face_service.enroll_face(
            self.user_alice.id,
            self.face_alice,
            user_consent=True,
            password="AlicePass123",
        )
        self.assertTrue(self.face_service.has_active_profile(self.user_alice.id))

        self.face_service.revoke_face(self.user_alice.id)
        self.assertFalse(self.face_service.has_active_profile(self.user_alice.id))

        with self.assertRaises(AuthenticationError) as ctx:
            self.face_service.verify_face(
                self.user_alice.id,
                self.face_alice_probe,
                password="AlicePass123",
            )
        self.assertIn("tidak memiliki profil", str(ctx.exception).lower())

    def test_full_auth_flow_with_face_mfa(self):
        """Verifies complete authentication sequence: Password + Face."""
        self.face_service.enroll_face(
            self.user_alice.id,
            self.face_alice,
            user_consent=True,
            password="AlicePass123",
        )

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

        self.face_service.enroll_face(
            self.user_alice.id,
            self.face_alice,
            user_consent=True,
            password="AlicePass123",
        )
        self.face_service.verify_face(
            self.user_alice.id,
            self.face_alice_probe,
            password="AlicePass123",
        )

        log_output = log_stream.getvalue()
        # Verify no raw floats or template dumps in log
        self.assertNotIn("ndarray", log_output)
        self.assertNotIn("[0.", log_output)
        logger.removeHandler(handler)

    def test_cross_account_envelope_transfer_fails_even_with_same_password(self):
        """Verifies envelope from User A cannot be decrypted by User B even with identical password (AAD binding)."""
        # Register charlie with the EXACT same password as Alice
        user_charlie = self.auth_service.register_user("charlie", "AlicePass123", "AlicePass123")

        # Alice enrolls face
        prof_alice = self.face_service.enroll_face(
            self.user_alice.id,
            self.face_alice,
            user_consent=True,
            password="AlicePass123",
        )

        # Attacker transfers Alice's envelope directly to Charlie's profile in DB
        now_iso = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """
            INSERT INTO face_profiles (
                user_id, encrypted_template, model_name, model_version,
                created_at, consent_recorded_at, revoked_at
            ) VALUES (?, ?, ?, ?, ?, ?, NULL)
            """,
            (user_charlie.id, prof_alice.encrypted_template, prof_alice.model_name, prof_alice.model_version, now_iso, now_iso),
        )
        self.conn.commit()

        # Charlie attempts verification using Alice's face and Charlie's password
        # This MUST fail because AAD is bound to Alice's user_id, not Charlie's!
        with self.assertRaises(AuthenticationError) as ctx:
            self.face_service.verify_face(
                user_charlie.id,
                self.face_alice_probe,
                password="AlicePass123",
            )
        self.assertIn("tidak dapat didekripsi", str(ctx.exception).lower())

    def test_iterations_below_minimum_rejected(self):
        """Verifies PBKDF2 iterations below 100,000 are strictly rejected."""
        prof = self.face_service.enroll_face(
            self.user_alice.id,
            self.face_alice,
            user_consent=True,
            password="AlicePass123",
        )
        data = json.loads(prof.encrypted_template)
        data["iterations"] = 99_999
        self.conn.execute(
            "UPDATE face_profiles SET encrypted_template = ? WHERE id = ?",
            (json.dumps(data), prof.id),
        )
        self.conn.commit()

        with self.assertRaises(AuthenticationError) as ctx:
            self.face_service.verify_face(
                self.user_alice.id,
                self.face_alice_probe,
                password="AlicePass123",
            )
        self.assertIn("di luar batas aman", str(ctx.exception).lower())

    def test_iterations_above_maximum_rejected(self):
        """Verifies PBKDF2 iterations above 2,000,000 are strictly rejected to prevent DoS."""
        prof = self.face_service.enroll_face(
            self.user_alice.id,
            self.face_alice,
            user_consent=True,
            password="AlicePass123",
        )
        data = json.loads(prof.encrypted_template)
        data["iterations"] = 2_000_001
        self.conn.execute(
            "UPDATE face_profiles SET encrypted_template = ? WHERE id = ?",
            (json.dumps(data), prof.id),
        )
        self.conn.commit()

        with self.assertRaises(AuthenticationError) as ctx:
            self.face_service.verify_face(
                self.user_alice.id,
                self.face_alice_probe,
                password="AlicePass123",
            )
        self.assertIn("di luar batas aman", str(ctx.exception).lower())

    def test_iterations_invalid_types_and_values_rejected(self):
        """Verifies 0, negative, boolean, float, string, and None iterations are rejected."""
        prof = self.face_service.enroll_face(
            self.user_alice.id,
            self.face_alice,
            user_consent=True,
            password="AlicePass123",
        )

        invalid_iterations = [0, -500, True, False, 600000.5, "600000", None]
        for val in invalid_iterations:
            data = json.loads(prof.encrypted_template)
            data["iterations"] = val
            self.conn.execute(
                "UPDATE face_profiles SET encrypted_template = ? WHERE id = ?",
                (json.dumps(data), prof.id),
            )
            self.conn.commit()

            with self.assertRaises(AuthenticationError):
                self.face_service.verify_face(
                    self.user_alice.id,
                    self.face_alice_probe,
                    password="AlicePass123",
                )

    def test_pbkdf2_not_invoked_when_iterations_invalid(self):
        """Verifies derive_key_from_passphrase is NEVER called when iterations are out of bounds."""
        prof = self.face_service.enroll_face(
            self.user_alice.id,
            self.face_alice,
            user_consent=True,
            password="AlicePass123",
        )
        data = json.loads(prof.encrypted_template)
        data["iterations"] = 50_000_000  # Extreme value that would cause CPU exhaustion DoS
        self.conn.execute(
            "UPDATE face_profiles SET encrypted_template = ? WHERE id = ?",
            (json.dumps(data), prof.id),
        )
        self.conn.commit()

        with patch("cryptosafe.auth.face_service.derive_key_from_passphrase") as mock_kdf:
            with self.assertRaises(AuthenticationError):
                self.face_service.verify_face(
                    self.user_alice.id,
                    self.face_alice_probe,
                    password="AlicePass123",
                )
            mock_kdf.assert_not_called()

    def test_invalid_structural_metadata_rejected(self):
        """Verifies tampering with version, algorithm, kdf, salt, nonce, ciphertext, shape, or dtype fails."""
        prof = self.face_service.enroll_face(
            self.user_alice.id,
            self.face_alice,
            user_consent=True,
            password="AlicePass123",
        )

        corruptions = [
            ("version", 99),
            ("algorithm", "AES-128-CBC"),
            ("kdf", "SCRYPT-UNKNOWN"),
            ("salt", "deadbeef"),  # Too short (4 bytes)
            ("salt", "not-a-hex-string!!"),
            ("nonce", "1234"),     # Too short (2 bytes)
            ("nonce", "00" * 32),  # Too long (32 bytes)
            ("ciphertext", "00" * 8),  # Too short (< 16 bytes tag)
            ("shape", []),
            ("shape", [64, -64]),
            ("dtype", "int64"),
        ]

        for field, bad_val in corruptions:
            data = json.loads(prof.encrypted_template)
            data[field] = bad_val
            self.conn.execute(
                "UPDATE face_profiles SET encrypted_template = ? WHERE id = ?",
                (json.dumps(data), prof.id),
            )
            self.conn.commit()

            with self.assertRaises(AuthenticationError):
                self.face_service.verify_face(
                    self.user_alice.id,
                    self.face_alice_probe,
                    password="AlicePass123",
                )

    def test_rekey_persists_across_new_instances(self):
        """Verifies rekeying works and persists when verified by a brand new FaceService instance."""
        service_1 = FaceService(self.face_repo)
        service_1.enroll_face(
            self.user_alice.id,
            self.face_alice,
            user_consent=True,
            password="OldPassword123!",
        )

        # Rekey with new password
        service_1.rekey_face_profile(
            self.user_alice.id,
            old_password="OldPassword123!",
            new_password="NewPassword456!",
        )

        # Destroy service_1, instantiate service_2
        del service_1
        service_2 = FaceService(self.face_repo)

        # Old password must fail
        with self.assertRaises(AuthenticationError):
            service_2.verify_face(
                self.user_alice.id,
                self.face_alice_probe,
                password="OldPassword123!",
            )

        # New password must succeed
        self.assertTrue(
            service_2.verify_face(
                self.user_alice.id,
                self.face_alice_probe,
                password="NewPassword456!",
            )
        )

    def test_rekey_failure_preserves_old_template(self):
        """Verifies rekey failure due to wrong old password keeps prior template intact and functional."""
        self.face_service.enroll_face(
            self.user_alice.id,
            self.face_alice,
            user_consent=True,
            password="CorrectOldPass!",
        )

        # Rekey attempt with wrong old password fails
        with self.assertRaises(AuthenticationError):
            self.face_service.rekey_face_profile(
                self.user_alice.id,
                old_password="WrongOldPass!",
                new_password="NewPass123!",
            )

        # Old profile must still be active and succeed with the correct old password
        self.assertTrue(
            self.face_service.verify_face(
                self.user_alice.id,
                self.face_alice_probe,
                password="CorrectOldPass!",
            )
        )

    def test_legacy_envelope_migration_to_aad(self):
        """Verifies legacy envelope without AAD decrypts, migrates automatically, and becomes AAD-bound."""
        from cryptosafe.crypto.key_manager import derive_key_from_passphrase
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import secrets

        # 1. Manually craft a legacy envelope (aad_bound=False / None associated_data)
        salt = secrets.token_bytes(16)
        nonce = secrets.token_bytes(12)
        key = derive_key_from_passphrase("AlicePass123", salt, 600_000)
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, self.face_alice.astype(np.float32).flatten().tobytes(), None)

        legacy_envelope = {
            "version": 1,
            "algorithm": "AES-256-GCM",
            "kdf": "PBKDF2-HMAC-SHA256",
            "iterations": 600_000,
            "salt": salt.hex(),
            "nonce": nonce.hex(),
            "ciphertext": ciphertext.hex(),
            "shape": [4096],
            "dtype": "float32",
        }

        # Store legacy envelope in SQLite
        now_iso = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """
            INSERT INTO face_profiles (
                user_id, encrypted_template, model_name, model_version,
                created_at, consent_recorded_at, revoked_at
            ) VALUES (?, ?, 'OpenCV-Haar-L2Norm', '1.0.0', ?, ?, NULL)
            """,
            (self.user_alice.id, json.dumps(legacy_envelope), now_iso, now_iso),
        )
        self.conn.commit()

        # 2. Verify: should succeed seamlessly via legacy fallback, and trigger auto-migration
        self.assertTrue(
            self.face_service.verify_face(
                self.user_alice.id,
                self.face_alice,
                password="AlicePass123",
            )
        )

        # 3. Check database: active profile must now be updated and aad_bound must be True
        active_prof = self.face_repo.get_active_by_user_id(self.user_alice.id)
        self.assertIsNotNone(active_prof)
        updated_data = json.loads(active_prof.encrypted_template)
        self.assertTrue(updated_data.get("aad_bound"))
        self.assertNotEqual(updated_data["salt"], salt.hex())  # Fresh salt generated

        # 4. Subsequent verification uses the migrated AAD-bound envelope
        self.assertTrue(
            self.face_service.verify_face(
                self.user_alice.id,
                self.face_alice,
                password="AlicePass123",
            )
        )

    def test_validate_template_shape_and_dtype(self):
        """Verifies template array dimensions and data type are strictly validated."""
        # Valid shapes
        valid_flat = np.zeros(4096, dtype=np.float32)
        valid_matrix = np.zeros((64, 64), dtype=np.float32)
        self.face_service._validate_template(valid_flat)
        self.face_service._validate_template(valid_matrix)

        # Invalid shape (wrong number of elements or dimensions)
        invalid_shape_1d = np.zeros(100, dtype=np.float32)
        with self.assertRaises(ValidationError) as ctx:
            self.face_service._validate_template(invalid_shape_1d)
        self.assertIn("dimensi template", str(ctx.exception).lower())

        invalid_shape_2d = np.zeros((128, 128), dtype=np.float32)
        with self.assertRaises(ValidationError) as ctx:
            self.face_service._validate_template(invalid_shape_2d)
        self.assertIn("dimensi template", str(ctx.exception).lower())

        # Invalid dtype (e.g. float64, int32)
        invalid_dtype_float64 = np.zeros(4096, dtype=np.float64)
        with self.assertRaises(ValidationError) as ctx:
            self.face_service._validate_template(invalid_dtype_float64)
        self.assertIn("tipe data template", str(ctx.exception).lower())

        invalid_dtype_int = np.zeros(4096, dtype=np.int32)
        with self.assertRaises(ValidationError) as ctx:
            self.face_service._validate_template(invalid_dtype_int)
        self.assertIn("tipe data template", str(ctx.exception).lower())

    def test_translation_jitter_tolerance(self):
        """Verifies translation-tolerant similarity allows genuine face with 2-3px jitter to pass."""
        # Create a smooth face patch with facial features
        face_img = np.zeros((100, 100), dtype=np.uint8) + 120
        face_img[35:45, 30:40] = 50
        face_img[35:45, 60:70] = 50
        face_img[45:65, 47:53] = 90
        face_img[70:80, 35:65] = 60

        self.face_service.enroll_face(
            self.user_alice.id,
            face_img,
            user_consent=True,
            password="AlicePass123",
        )

        # Shift face by 2 pixels (simulating slight camera/head movement)
        shifted_face = np.roll(face_img, 2, axis=0)
        shifted_face = np.roll(shifted_face, 2, axis=1)

        # Must pass with DEFAULT_FACE_THRESHOLD (0.70)
        verified = self.face_service.verify_face(
            self.user_alice.id,
            shifted_face,
            password="AlicePass123",
        )
        self.assertTrue(verified)

        # Bob's face must still fail
        with self.assertRaises(AuthenticationError):
            self.face_service.verify_face(
                self.user_alice.id,
                self.face_bob,
                password="AlicePass123",
            )

    def test_diagnostic_logging_records_safe_metrics(self):
        """Verifies diagnostic logs record similarity score and threshold without leaking secrets."""
        self.face_service.enroll_face(
            self.user_alice.id,
            self.face_alice,
            user_consent=True,
            password="AlicePass123",
        )

        with self.assertLogs("cryptosafe.face", level="INFO") as cm:
            self.face_service.verify_face(
                self.user_alice.id,
                self.face_alice_probe,
                password="AlicePass123",
            )

        log_output = "\n".join(cm.output)
        self.assertIn("similarity=", log_output)
        self.assertIn("threshold=", log_output)
        self.assertNotIn("AlicePass123", log_output)

    def test_capture_camera_frame_warmup(self):
        """Verifies capture_camera_frame discards warmup frames before returning."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_cap.read.return_value = (True, mock_frame)

        with patch("cv2.VideoCapture", return_value=mock_cap):
            frame = self.face_service.capture_camera_frame(camera_index=0)

        self.assertIsNotNone(frame)
        # 5 warmup reads + 1 final read = 6 calls
        self.assertEqual(mock_cap.read.call_count, 6)
        mock_cap.release.assert_called_once()

    def test_check_liveness_static_identical_frames_fails(self):
        """Identical freeze-frames or static printed photos fail liveness verification."""
        frame1 = make_synthetic_face(seed=10)
        frame2 = frame1.copy()
        is_live, msg = FaceService.check_liveness([frame1, frame2])
        self.assertFalse(is_live)
        self.assertIn("statis", msg)

    def test_check_liveness_varying_frames_passes(self):
        """Natural varying frames with micro-movement pass liveness check."""
        frame1 = make_synthetic_face(seed=10)
        # Add subtle natural micro-movement
        frame2 = frame1.copy()
        frame2[10:30, 10:30] = (frame2[10:30, 10:30] + 5) % 256
        is_live, msg = FaceService.check_liveness([frame1, frame2])
        self.assertTrue(is_live)
        self.assertIn("OK", msg)

    def test_verify_face_with_liveness_integration(self):
        """verify_face raises AuthenticationError when liveness verification fails."""
        self.face_service.enroll_face(self.user_alice.id, self.face_alice, password="AlicePass123")

        # Static identical frames trigger anti-spoofing rejection
        static_frame = self.face_alice.copy()
        with self.assertRaises(AuthenticationError) as cm:
            self.face_service.verify_face(
                self.user_alice.id,
                self.face_alice,
                password="AlicePass123",
                liveness_frames=[static_frame, static_frame],
            )
        self.assertIn("liveness", str(cm.exception).lower())


if __name__ == "__main__":
    unittest.main()
