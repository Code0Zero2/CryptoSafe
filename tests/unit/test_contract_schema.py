
"""Tests for CryptoSafe contract database schema."""

import unittest
import sys
from pathlib import Path

src_dir = Path(__file__).resolve().parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from cryptosafe.database.connection import get_connection
from cryptosafe.database.schema import init_db, CURRENT_SCHEMA_VERSION
from cryptosafe.database.user_repository import UserRepository


class TestContractSchema(unittest.TestCase):

    def setUp(self):
        self.conn = get_connection(":memory:")
        init_db(self.conn)
        self.user_repo = UserRepository(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_schema_version_is_four(self):
        self.assertEqual(CURRENT_SCHEMA_VERSION, 4)

        row = self.conn.execute(
            "SELECT MAX(version) AS version FROM schema_version"
        ).fetchone()

        self.assertEqual(row["version"], 4)

    def test_contract_tables_exist(self):
        tables = {
            row["name"]
            for row in self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

        self.assertIn("contracts", tables)
        self.assertIn("encrypted_messages", tables)
        self.assertIn("contract_files", tables)

    def test_contract_creation(self):
        user = self.user_repo.create_user(
            "contract_user",
            "argon2_test_hash"
        )

        with self.conn:
            cursor = self.conn.execute(
                """
                INSERT INTO contracts (
                    contract_number,
                    title,
                    parties,
                    status,
                    created_by,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "CTR-001",
                    "Perjanjian Kerja Sama",
                    "PT Alpha dan PT Beta",
                    "Draft",
                    user.id,
                    "2026-11-10T10:00:00+00:00",
                    "2026-11-10T10:00:00+00:00",
                )
            )

        contract = self.conn.execute(
            "SELECT * FROM contracts WHERE id = ?",
            (cursor.lastrowid,)
        ).fetchone()

        self.assertEqual(contract["contract_number"], "CTR-001")
        self.assertEqual(contract["status"], "Draft")

    def test_invalid_contract_status_rejected(self):
        user = self.user_repo.create_user(
            "status_user",
            "argon2_test_hash"
        )

        with self.assertRaises(Exception):
            self.conn.execute(
                """
                INSERT INTO contracts (
                    contract_number,
                    title,
                    parties,
                    status,
                    created_by,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "CTR-002",
                    "Test Contract",
                    "Party A",
                    "Invalid Status",
                    user.id,
                    "2026-11-10",
                    "2026-11-10",
                )
            )

    def test_existing_user_preserved_after_reinitialization(self):
        user = self.user_repo.create_user(
            "preserved_user",
            "argon2_test_hash"
        )

        init_db(self.conn)

        preserved = self.user_repo.get_by_id(user.id)

        self.assertIsNotNone(preserved)
        self.assertEqual(preserved.username, "preserved_user")


if __name__ == "__main__":
    unittest.main()
