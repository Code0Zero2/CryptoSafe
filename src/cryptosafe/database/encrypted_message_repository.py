
"""Encrypted message persistence repository."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from cryptosafe.common.errors import ValidationError
from cryptosafe.database.connection import transaction


VALID_CONTENT_TYPES = ("note", "clause", "draft")
DEFAULT_ALGORITHM = "VIGENERE+AES-256-GCM"


@dataclass(frozen=True)
class EncryptedMessage:
    id: int
    contract_id: int
    user_id: int
    content_type: str
    label: str
    ciphertext: str
    algorithm: str
    envelope_version: int
    created_at: str
    updated_at: str


class EncryptedMessageRepository:
    """Store encrypted contract messages in SQLite."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    @property
    def conn(self) -> sqlite3.Connection:
        """Return the underlying SQLite database connection."""
        return self._conn

    @staticmethod
    def _row_to_message(row: sqlite3.Row) -> EncryptedMessage:
        return EncryptedMessage(
            id=row["id"],
            contract_id=row["contract_id"],
            user_id=row["user_id"],
            content_type=row["content_type"],
            label=row["label"],
            ciphertext=row["ciphertext"],
            algorithm=row["algorithm"],
            envelope_version=row["envelope_version"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _validate_content_type(content_type: str) -> str:
        if not isinstance(content_type, str):
            raise ValidationError("Jenis catatan tidak valid.")

        normalized = content_type.strip().lower()
        if normalized not in VALID_CONTENT_TYPES:
            raise ValidationError("Jenis catatan harus note, clause, atau draft.")

        return normalized

    @staticmethod
    def _validate_message(label: str, ciphertext: str) -> tuple[str, str]:
        if not isinstance(label, str) or not label.strip():
            raise ValidationError("Label catatan wajib diisi.")

        if not isinstance(ciphertext, str) or not ciphertext.strip():
            raise ValidationError("Ciphertext tidak boleh kosong.")

        return label.strip(), ciphertext

    def _row_for_user(
        self, message_id: int, user_id: int
    ) -> sqlite3.Row | None:
        cursor = self._conn.execute(
            """
            SELECT m.*
            FROM encrypted_messages AS m
            JOIN contracts AS c ON c.id = m.contract_id
            WHERE m.id = ? AND c.created_by = ?
            """,
            (message_id, user_id),
        )
        return cursor.fetchone()

    def create_message(
        self,
        contract_id: int,
        user_id: int,
        content_type: str,
        label: str,
        ciphertext: str,
    ) -> EncryptedMessage:
        """Create an encrypted message for a contract owned by the user."""
        content_type = self._validate_content_type(content_type)
        label, ciphertext = self._validate_message(label, ciphertext)

        now = datetime.now(timezone.utc).isoformat()

        try:
            with transaction(self._conn):
                cursor = self._conn.execute(
                    """
                    INSERT INTO encrypted_messages (
                        contract_id,
                        user_id,
                        content_type,
                        label,
                        ciphertext,
                        algorithm,
                        envelope_version,
                        created_at,
                        updated_at
                    )
                    SELECT ?, ?, ?, ?, ?, ?, 1, ?, ?
                    WHERE EXISTS (
                        SELECT 1 FROM contracts
                        WHERE id = ? AND created_by = ?
                    )
                    """,
                    (
                        contract_id,
                        user_id,
                        content_type,
                        label,
                        ciphertext,
                        DEFAULT_ALGORITHM,
                        now,
                        now,
                        contract_id,
                        user_id,
                    ),
                )

                if cursor.rowcount == 0:
                    raise ValidationError(
                        "Kontrak tidak ditemukan atau bukan milik pengguna."
                    )

                message_id = cursor.lastrowid

        except sqlite3.IntegrityError as err:
            raise ValidationError(
                f"Gagal menyimpan catatan terenkripsi: {err}"
            ) from err

        return self.get_by_id(message_id, user_id)

    def get_by_id(
        self, message_id: int, user_id: int
    ) -> EncryptedMessage | None:
        """Get a message only if its contract belongs to the user."""
        row = self._row_for_user(message_id, user_id)

        if row is None:
            return None

        return self._row_to_message(row)

    def list_by_contract(
        self, contract_id: int, user_id: int
    ) -> list[EncryptedMessage]:
        """List messages belonging to a contract owned by the user."""
        cursor = self._conn.execute(
            """
            SELECT m.*
            FROM encrypted_messages AS m
            JOIN contracts AS c ON c.id = m.contract_id
            WHERE m.contract_id = ? AND c.created_by = ?
            ORDER BY m.updated_at DESC, m.id DESC
            """,
            (contract_id, user_id),
        )

        return [self._row_to_message(row) for row in cursor.fetchall()]

    def update_message(
        self,
        message_id: int,
        user_id: int,
        content_type: str,
        label: str,
        ciphertext: str,
    ) -> EncryptedMessage:
        """Update an encrypted message owned by the user's contract."""
        content_type = self._validate_content_type(content_type)
        label, ciphertext = self._validate_message(label, ciphertext)
        now = datetime.now(timezone.utc).isoformat()

        with transaction(self._conn):
            cursor = self._conn.execute(
                """
                UPDATE encrypted_messages
                SET content_type = ?, label = ?, ciphertext = ?, updated_at = ?
                WHERE id = ?
                AND EXISTS (
                    SELECT 1 FROM contracts
                    WHERE contracts.id = encrypted_messages.contract_id
                    AND contracts.created_by = ?
                )
                """,
                (
                    content_type,
                    label,
                    ciphertext,
                    now,
                    message_id,
                    user_id,
                ),
            )

            if cursor.rowcount == 0:
                raise ValidationError(
                    "Catatan tidak ditemukan atau bukan milik pengguna."
                )

        return self.get_by_id(message_id, user_id)

    def delete_message(self, message_id: int, user_id: int) -> bool:
        """Delete a message only if its contract belongs to the user."""
        with transaction(self._conn):
            cursor = self._conn.execute(
                """
                DELETE FROM encrypted_messages
                WHERE id = ?
                AND EXISTS (
                    SELECT 1 FROM contracts
                    WHERE contracts.id = encrypted_messages.contract_id
                    AND contracts.created_by = ?
                )
                """,
                (message_id, user_id),
            )

        return cursor.rowcount > 0
