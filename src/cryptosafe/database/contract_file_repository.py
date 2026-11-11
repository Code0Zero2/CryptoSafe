"""Contract file attachment persistence repository."""

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from cryptosafe.common.errors import ValidationError
from cryptosafe.database.connection import transaction

DEFAULT_FILE_ALGORITHM = "ChaCha20-Poly1305"


@dataclass(frozen=True)
class ContractFile:
    id: int
    contract_id: int
    user_id: int
    original_filename: str
    encrypted_path: str
    mime_type: str | None
    size_bytes: int
    algorithm: str
    envelope_version: int
    created_at: str


class ContractFileRepository:
    """Repository handling contract file attachments in SQLite."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    @property
    def conn(self) -> sqlite3.Connection:
        """Return the underlying SQLite connection."""
        return self._conn

    @staticmethod
    def _row_to_file(row: sqlite3.Row) -> ContractFile:
        return ContractFile(
            id=row["id"],
            contract_id=row["contract_id"],
            user_id=row["user_id"],
            original_filename=row["original_filename"],
            encrypted_path=row["encrypted_path"],
            mime_type=row["mime_type"],
            size_bytes=row["size_bytes"],
            algorithm=row["algorithm"],
            envelope_version=row["envelope_version"],
            created_at=row["created_at"],
        )

    def create_file(
        self,
        contract_id: int,
        user_id: int,
        original_filename: str,
        encrypted_path: str,
        size_bytes: int,
        mime_type: str | None = None,
        algorithm: str = DEFAULT_FILE_ALGORITHM,
        envelope_version: int = 1,
    ) -> ContractFile:
        """Record an encrypted file attachment for a contract owned by user."""
        if not isinstance(original_filename, str) or not original_filename.strip():
            raise ValidationError("Nama file lampiran tidak boleh kosong.")

        clean_filename = Path(original_filename.strip()).name
        if not clean_filename:
            raise ValidationError("Nama file lampiran tidak valid.")

        if not isinstance(encrypted_path, str) or not encrypted_path.strip():
            raise ValidationError("Path file terenkripsi tidak boleh kosong.")

        if not isinstance(size_bytes, int) or size_bytes < 0:
            raise ValidationError("Ukuran file tidak valid.")

        now_iso = datetime.now(timezone.utc).isoformat()

        try:
            with transaction(self._conn):
                cursor = self._conn.execute(
                    """
                    INSERT INTO contract_files (
                        contract_id,
                        user_id,
                        original_filename,
                        encrypted_path,
                        mime_type,
                        size_bytes,
                        algorithm,
                        envelope_version,
                        created_at
                    )
                    SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?
                    WHERE EXISTS (
                        SELECT 1 FROM contracts
                        WHERE id = ? AND created_by = ?
                    )
                    """,
                    (
                        contract_id,
                        user_id,
                        clean_filename,
                        encrypted_path.strip(),
                        mime_type.strip() if isinstance(mime_type, str) and mime_type.strip() else None,
                        size_bytes,
                        algorithm,
                        envelope_version,
                        now_iso,
                        contract_id,
                        user_id,
                    ),
                )

                if cursor.rowcount == 0:
                    raise ValidationError(
                        "Kontrak tidak ditemukan atau bukan milik pengguna."
                    )

                file_id = cursor.lastrowid
                return ContractFile(
                    id=file_id,
                    contract_id=contract_id,
                    user_id=user_id,
                    original_filename=clean_filename,
                    encrypted_path=encrypted_path.strip(),
                    mime_type=mime_type.strip() if isinstance(mime_type, str) and mime_type.strip() else None,
                    size_bytes=size_bytes,
                    algorithm=algorithm,
                    envelope_version=envelope_version,
                    created_at=now_iso,
                )
        except sqlite3.IntegrityError as err:
            raise ValidationError(f"Gagal menyimpan data lampiran: {err}")

    def get_by_id(self, file_id: int, user_id: int) -> ContractFile | None:
        """Retrieve attachment by ID if owned by active user."""
        cursor = self._conn.execute(
            """
            SELECT f.*
            FROM contract_files AS f
            JOIN contracts AS c ON c.id = f.contract_id
            WHERE f.id = ? AND c.created_by = ?
            """,
            (file_id, user_id),
        )
        row = cursor.fetchone()
        return self._row_to_file(row) if row else None

    def list_by_contract(self, contract_id: int, user_id: int) -> list[ContractFile]:
        """List all attachments for a contract owned by user."""
        cursor = self._conn.execute(
            """
            SELECT f.*
            FROM contract_files AS f
            JOIN contracts AS c ON c.id = f.contract_id
            WHERE f.contract_id = ? AND c.created_by = ?
            ORDER BY f.id ASC
            """,
            (contract_id, user_id),
        )
        return [self._row_to_file(row) for row in cursor.fetchall()]

    def delete_file(self, file_id: int, user_id: int) -> bool:
        """Delete attachment metadata if owned by user."""
        with transaction(self._conn):
            cursor = self._conn.execute(
                """
                DELETE FROM contract_files
                WHERE id = ? AND contract_id IN (
                    SELECT id FROM contracts WHERE created_by = ?
                )
                """,
                (file_id, user_id),
            )
            return cursor.rowcount > 0
