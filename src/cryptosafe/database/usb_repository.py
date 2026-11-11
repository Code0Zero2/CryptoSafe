"""USB token credentials repository using SQLite."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from cryptosafe.common.errors import ValidationError

@dataclass(frozen=True)
class UsbCredential:
    id: int
    user_id: int
    token_id: str
    verifier: str
    created_at: str
    revoked_at: str | None

class UsbRepository:
    """Repository handling persistence of USB token verifiers."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def create_credential(self, user_id: int, token_id: str, verifier: str) -> UsbCredential:
        """Enroll and persist a new USB token verifier, revoking any prior active tokens."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._conn:
            # Revoke existing active tokens for this user
            self._conn.execute(
                "UPDATE usb_credentials SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL",
                (now_iso, user_id)
            )
            cursor = self._conn.execute(
                """
                INSERT INTO usb_credentials (user_id, token_id, verifier, created_at, revoked_at)
                VALUES (?, ?, ?, ?, NULL)
                """,
                (user_id, token_id, verifier, now_iso)
            )
            cred_id = cursor.lastrowid
            return UsbCredential(
                id=cred_id,
                user_id=user_id,
                token_id=token_id,
                verifier=verifier,
                created_at=now_iso,
                revoked_at=None,
            )

    def get_active_by_user_id(self, user_id: int) -> UsbCredential | None:
        """Retrieve active (non-revoked) token credential for user."""
        cursor = self._conn.execute(
            """
            SELECT id, user_id, token_id, verifier, created_at, revoked_at
            FROM usb_credentials
            WHERE user_id = ? AND revoked_at IS NULL
            """,
            (user_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return UsbCredential(
            id=row["id"],
            user_id=row["user_id"],
            token_id=row["token_id"],
            verifier=row["verifier"],
            created_at=row["created_at"],
            revoked_at=row["revoked_at"],
        )

    def get_by_token_id(self, token_id: str) -> UsbCredential | None:
        """Retrieve token credential by public token_id regardless of revocation."""
        cursor = self._conn.execute(
            """
            SELECT id, user_id, token_id, verifier, created_at, revoked_at
            FROM usb_credentials
            WHERE token_id = ?
            """,
            (token_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return UsbCredential(
            id=row["id"],
            user_id=row["user_id"],
            token_id=row["token_id"],
            verifier=row["verifier"],
            created_at=row["created_at"],
            revoked_at=row["revoked_at"],
        )

    def revoke_by_user_id(self, user_id: int) -> bool:
        """Revoke all active tokens for user. Returns True if any token was revoked."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._conn:
            cursor = self._conn.execute(
                "UPDATE usb_credentials SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL",
                (now_iso, user_id)
            )
            return cursor.rowcount > 0

