"""Unit tests for M2 Database, User Repository, and AuthService."""

import unittest
import sqlite3
import sys
from pathlib import Path

src_dir = Path(__file__).resolve().parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from cryptosafe.database.connection import get_connection
from cryptosafe.database.schema import init_db
from cryptosafe.database.user_repository import UserRepository
from cryptosafe.auth.password_service import PasswordService
from cryptosafe.auth.auth_service import AuthService
from cryptosafe.common.errors import AuthenticationError, ValidationError

class TestM2UserManagement(unittest.TestCase):
    def setUp(self):
        # Use disposable in-memory SQLite database for test isolation
        self.conn = get_connection(":memory:")
        init_db(self.conn)
        self.user_repo = UserRepository(self.conn)
        self.password_service = PasswordService(time_cost=1, memory_cost=8192, parallelism=1)  # fast test params
        self.auth_service = AuthService(self.user_repo, self.password_service)

    def tearDown(self):
        self.conn.close()

    def test_database_schema_initialization(self):
        """Verifies tables and schema version exist."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row["name"] for row in cursor.fetchall()]
        self.assertIn("users", tables)
        self.assertIn("schema_version", tables)

    def test_password_hashing_and_verification(self):
        """Verifies Argon2id hashing produces valid hash and verifies correctly."""
        password = "SecurePassword123!"
        hashed = self.password_service.hash_password(password)

        self.assertNotEqual(password, hashed)
        self.assertTrue(hashed.startswith("$argon2id$"))
        self.assertTrue(self.password_service.verify_password(password, hashed))
        self.assertFalse(self.password_service.verify_password("WrongPassword!", hashed))

    def test_short_password_rejected(self):
        """Verifies passwords shorter than 6 characters are rejected."""
        with self.assertRaises(ValidationError):
            self.password_service.hash_password("12345")

    def test_user_registration_success(self):
        """Verifies registering a valid user account."""
        user = self.auth_service.register_user("alice", "MyPassword123", "MyPassword123")
        self.assertIsNotNone(user.id)
        self.assertEqual(user.username, "alice")
        self.assertTrue(user.is_active)
        self.assertNotEqual(user.password_hash, "MyPassword123")
        self.assertTrue(user.password_hash.startswith("$argon2id$"))

    def test_duplicate_username_rejected(self):
        """Verifies duplicate usernames are rejected with friendly error."""
        self.auth_service.register_user("bob_crypto", "Password123", "Password123")
        
        # Exact same case
        with self.assertRaises(ValidationError) as ctx:
            self.auth_service.register_user("bob_crypto", "Password456", "Password456")
        self.assertIn("sudah terdaftar", str(ctx.exception))

        # Normalized case insensitive duplicate check
        with self.assertRaises(ValidationError) as ctx2:
            self.auth_service.register_user("BOB_CRYPTO", "Password789", "Password789")
        self.assertIn("sudah terdaftar", str(ctx2.exception))

    def test_password_mismatch_rejected(self):
        """Verifies registration fails when password confirmation does not match."""
        with self.assertRaises(ValidationError) as ctx:
            self.auth_service.register_user("carol", "Password123", "Password999")
        self.assertIn("tidak cocok", str(ctx.exception))

    def test_invalid_username_characters(self):
        """Verifies invalid characters in username are rejected."""
        with self.assertRaises(ValidationError):
            self.auth_service.register_user("user space", "Password123", "Password123")

    def test_authentication_success_and_failure(self):
        """Verifies login succeeds with correct credentials and fails with wrong password."""
        self.auth_service.register_user("david", "DavidSecret123", "DavidSecret123")

        # Success
        user = self.auth_service.authenticate_user("david", "DavidSecret123")
        self.assertEqual(user.username, "david")

        # Wrong password
        with self.assertRaises(AuthenticationError) as ctx:
            self.auth_service.authenticate_user("david", "WrongSecret")
        self.assertEqual(str(ctx.exception), "Username atau password salah.")

        # Non-existent user (generic error message prevents enumeration)
        with self.assertRaises(AuthenticationError) as ctx2:
            self.auth_service.authenticate_user("ghost_user", "AnyPassword123")
        self.assertEqual(str(ctx2.exception), "Username atau password salah.")

    def test_inactive_account_cannot_login(self):
        """Verifies inactive user cannot log in."""
        user = self.auth_service.register_user("eve", "EveSecret123", "EveSecret123")
        
        # Mark inactive directly in DB
        self.conn.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user.id,))
        self.conn.commit()

        with self.assertRaises(AuthenticationError):
            self.auth_service.authenticate_user("eve", "EveSecret123")

if __name__ == "__main__":
    unittest.main()

