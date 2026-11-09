"""Unit tests for M3 USB Token Authentication and Challenge-Response."""

import json
import os
import secrets
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

src_dir = Path(__file__).resolve().parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from cryptosafe.database.connection import get_connection
from cryptosafe.database.schema import init_db
from cryptosafe.database.user_repository import UserRepository
from cryptosafe.database.usb_repository import UsbRepository
from cryptosafe.auth.password_service import PasswordService
from cryptosafe.auth.usb_token_service import UsbTokenService, TOKEN_FILENAME
from cryptosafe.auth.auth_service import AuthService
from cryptosafe.common.errors import AuthenticationError, ValidationError

class TestM3UsbTokenAuthentication(unittest.TestCase):
    def setUp(self):
        self.conn = get_connection(":memory:")
        init_db(self.conn)
        self.user_repo = UserRepository(self.conn)
        self.usb_repo = UsbRepository(self.conn)
        self.password_service = PasswordService(time_cost=1, memory_cost=8192, parallelism=1)
        self.usb_service = UsbTokenService(self.usb_repo)
        self.auth_service = AuthService(self.user_repo, self.password_service, self.usb_service)

        self.user1 = self.auth_service.register_user("alice", "AlicePassword123", "AlicePassword123")
        self.user2 = self.auth_service.register_user("bob", "BobPassword123", "BobPassword123")

        self.temp_dir = tempfile.TemporaryDirectory()
        self.usb_mount1 = Path(self.temp_dir.name) / "drive_alice"
        self.usb_mount1.mkdir(parents=True, exist_ok=True)

        self.usb_mount2 = Path(self.temp_dir.name) / "drive_bob"
        self.usb_mount2.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.conn.close()
        self.temp_dir.cleanup()

    def test_enrollment_creates_file_and_verifier(self):
        """Verifies enrollment creates the token file and stores only the verifier (not the secret)."""
        cred, token_path = self.usb_service.enroll_token(self.user1.id, self.usb_mount1)

        self.assertTrue(token_path.exists())
        self.assertEqual(token_path.name, TOKEN_FILENAME)

        with open(token_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["token_id"], cred.token_id)
        raw_secret_hex = data["token_secret"]

        # Crucial security check: raw secret must NOT equal database verifier
        self.assertNotEqual(raw_secret_hex, cred.verifier)

    def test_valid_token_authentication(self):
        """Verifies challenge-response succeeds with valid enrolled token."""
        _, token_path = self.usb_service.enroll_token(self.user1.id, self.usb_mount1)
        challenge = self.usb_service.create_challenge(self.user1.id)

        result = self.usb_service.verify_token(self.user1.id, challenge.challenge_id, token_path)
        self.assertTrue(result)

        # Full auth service integration check
        user = self.auth_service.authenticate_user("alice", "AlicePassword123", usb_token_path=token_path)
        self.assertEqual(user.username, "alice")

    def test_missing_token_file_fails(self):
        """Verifies authentication fails when token file is missing."""
        self.usb_service.enroll_token(self.user1.id, self.usb_mount1)
        missing_path = self.usb_mount1 / "non_existent.key"
        challenge = self.usb_service.create_challenge(self.user1.id)

        with self.assertRaises(AuthenticationError) as ctx:
            self.usb_service.verify_token(self.user1.id, challenge.challenge_id, missing_path)
        self.assertIn("tidak ditemukan", str(ctx.exception))

    def test_wrong_secret_fails(self):
        """Verifies authentication fails when token has mismatched secret."""
        _, token_path = self.usb_service.enroll_token(self.user1.id, self.usb_mount1)

        # Tamper with the token secret on the drive
        with open(token_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["token_secret"] = secrets.token_hex(32)
        with open(token_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        challenge = self.usb_service.create_challenge(self.user1.id)
        with self.assertRaises(AuthenticationError) as ctx:
            self.usb_service.verify_token(self.user1.id, challenge.challenge_id, token_path)
        self.assertIn("gagal", str(ctx.exception).lower())

    def test_expired_challenge_fails(self):
        """Verifies authentication fails when challenge has expired."""
        _, token_path = self.usb_service.enroll_token(self.user1.id, self.usb_mount1)
        # Create challenge with negative/zero TTL
        challenge = self.usb_service.create_challenge(self.user1.id, ttl_seconds=-1)

        with self.assertRaises(AuthenticationError) as ctx:
            self.usb_service.verify_token(self.user1.id, challenge.challenge_id, token_path)
        self.assertIn("kedaluwarsa", str(ctx.exception).lower())

    def test_replay_challenge_fails(self):
        """Verifies challenge is single-use and cannot be replayed."""
        _, token_path = self.usb_service.enroll_token(self.user1.id, self.usb_mount1)
        challenge = self.usb_service.create_challenge(self.user1.id)

        # First use succeeds
        self.assertTrue(self.usb_service.verify_token(self.user1.id, challenge.challenge_id, token_path))

        # Replay attempt fails immediately
        with self.assertRaises(AuthenticationError) as ctx:
            self.usb_service.verify_token(self.user1.id, challenge.challenge_id, token_path)
        self.assertIn("replay", str(ctx.exception).lower())

    def test_corrupted_token_fails(self):
        """Verifies corrupted or invalid token payload fails gracefully."""
        corrupted_path = self.usb_mount1 / TOKEN_FILENAME
        with open(corrupted_path, "w", encoding="utf-8") as f:
            f.write("corrupted-not-json")

        challenge = self.usb_service.create_challenge(self.user1.id)
        with self.assertRaises(AuthenticationError) as ctx:
            self.usb_service.verify_token(self.user1.id, challenge.challenge_id, corrupted_path)
        self.assertIn("rusak atau tidak valid", str(ctx.exception))

    def test_cross_account_token_fails(self):
        """Verifies token enrolled for User 1 cannot authenticate User 2."""
        _, token_path_alice = self.usb_service.enroll_token(self.user1.id, self.usb_mount1)
        self.usb_service.enroll_token(self.user2.id, self.usb_mount2)

        # Bob tries to use Alice's token
        challenge_bob = self.usb_service.create_challenge(self.user2.id)
        with self.assertRaises(AuthenticationError) as ctx:
            self.usb_service.verify_token(self.user2.id, challenge_bob.challenge_id, token_path_alice)
        self.assertIn("tidak cocok", str(ctx.exception))

    def test_revoked_token_fails(self):
        """Verifies revoked token cannot be used to authenticate."""
        _, token_path = self.usb_service.enroll_token(self.user1.id, self.usb_mount1)
        
        # Revoke token
        self.assertTrue(self.usb_service.revoke_token(self.user1.id))
        self.assertFalse(self.usb_service.has_active_token(self.user1.id))

        challenge = self.usb_service.create_challenge(self.user1.id)
        with self.assertRaises(AuthenticationError) as ctx:
            self.usb_service.verify_token(self.user1.id, challenge.challenge_id, token_path)
        self.assertIn("dicabut", str(ctx.exception))

    def test_detect_token_file(self):
        """Verifies scanning and finding a valid token file across search paths."""
        self.assertIsNone(self.usb_service.detect_token_file([self.usb_mount1]))
        _, token_path = self.usb_service.enroll_token(self.user1.id, self.usb_mount1)
        detected = self.usb_service.detect_token_file([self.usb_mount1])
        self.assertEqual(detected, token_path)

if __name__ == "__main__":
    unittest.main()
