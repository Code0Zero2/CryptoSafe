"""User persistence repository using parameterized SQLite queries."""

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from cryptosafe.common.errors import ValidationError

@dataclass(frozen=True)
class User:
    id: int
    username: str
    password_hash: str
    is_active: bool
    created_at: str
    updated_at: str

class UserRepository:
    """Repository handling CRUD operations for user accounts."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def create_user(self, username: str, password_hash: str) -> User:
        """Create and store a new user record."""
        normalized_username = username.strip().lower()
        now_iso = datetime.now(timezone.utc).isoformat()

        try:
            with self._conn:
                cursor = self._conn.execute(
                    """
                    INSERT INTO users (username, password_hash, is_active, created_at, updated_at)
                    VALUES (?, ?, 1, ?, ?)
                    """,
                    (normalized_username, password_hash, now_iso, now_iso)
                )
                user_id = cursor.lastrowid
                return User(
                    id=user_id,
                    username=normalized_username,
                    password_hash=password_hash,
                    is_active=True,
                    created_at=now_iso,
                    updated_at=now_iso,
                )
        except sqlite3.IntegrityError as err:
            if "UNIQUE constraint failed: users.username" in str(err):
                raise ValidationError("Username sudah terdaftar.")
            raise

    def get_by_username(self, username: str) -> User | None:
        """Retrieve user by normalized username."""
        normalized_username = username.strip().lower()
        cursor = self._conn.execute(
            """
            SELECT id, username, password_hash, is_active, created_at, updated_at
            FROM users
            WHERE username = ?
            """,
            (normalized_username,)
        )
        row = cursor.fetchone()
        if not row:
            return None

        return User(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def get_by_id(self, user_id: int) -> User | None:
        """Retrieve user by ID."""
        cursor = self._conn.execute(
            """
            SELECT id, username, password_hash, is_active, created_at, updated_at
            FROM users
            WHERE id = ?
            """,
            (user_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None

        return User(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

