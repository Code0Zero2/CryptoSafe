
"""Contract persistence repository using parameterized SQLite queries."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from cryptosafe.common.errors import ValidationError
from cryptosafe.database.connection import transaction


VALID_STATUSES = (
    "Draft",
    "Review",
    "Approved",
    "Signed",
    "Archived",
)


@dataclass(frozen=True)
class Contract:
    id: int
    contract_number: str
    title: str
    parties: str
    start_date: str | None
    end_date: str | None
    status: str
    created_by: int
    created_at: str
    updated_at: str


class ContractRepository:
    """Repository handling contract CRUD operations."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    @property
    def conn(self) -> sqlite3.Connection:
        """Return the underlying SQLite database connection."""
        return self._conn

    @staticmethod
    def _row_to_contract(row: sqlite3.Row) -> Contract:
        return Contract(
            id=row["id"],
            contract_number=row["contract_number"],
            title=row["title"],
            parties=row["parties"],
            start_date=row["start_date"],
            end_date=row["end_date"],
            status=row["status"],
            created_by=row["created_by"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def create_contract(
        self,
        contract_number: str,
        title: str,
        parties: str,
        created_by: int,
        start_date: str | None = None,
        end_date: str | None = None,
        status: str = "Draft",
    ) -> Contract:
        """Create a contract belonging to a user."""

        contract_number = contract_number.strip()
        title = title.strip()
        parties = parties.strip()

        if not contract_number or not title or not parties:
            raise ValidationError(
                "Nomor kontrak, judul, dan pihak terkait wajib diisi."
            )

        if status not in VALID_STATUSES:
            raise ValidationError("Status kontrak tidak valid.")

        now_iso = datetime.now(timezone.utc).isoformat()

        try:
            with transaction(self._conn):
                cursor = self._conn.execute(
                    """
                    INSERT INTO contracts (
                        contract_number,
                        title,
                        parties,
                        start_date,
                        end_date,
                        status,
                        created_by,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        contract_number,
                        title,
                        parties,
                        start_date,
                        end_date,
                        status,
                        created_by,
                        now_iso,
                        now_iso,
                    ),
                )

                contract_id = cursor.lastrowid

            return self.get_by_id(contract_id, created_by)

        except sqlite3.IntegrityError as err:
            if "contracts.contract_number" in str(err):
                raise ValidationError(
                    "Nomor kontrak sudah digunakan."
                ) from err
            raise

    def get_by_id(
        self,
        contract_id: int,
        user_id: int,
    ) -> Contract | None:
        """Retrieve a contract only if it belongs to the requested user."""

        row = self._conn.execute(
            """
            SELECT *
            FROM contracts
            WHERE id = ? AND created_by = ?
            """,
            (contract_id, user_id),
        ).fetchone()

        if row is None:
            return None

        return self._row_to_contract(row)

    def list_by_user(self, user_id: int) -> list[Contract]:
        """Return all contracts belonging to a user."""

        rows = self._conn.execute(
            """
            SELECT *
            FROM contracts
            WHERE created_by = ?
            ORDER BY updated_at DESC, id DESC
            """,
            (user_id,),
        ).fetchall()

        return [self._row_to_contract(row) for row in rows]

    def update_status(
        self,
        contract_id: int,
        user_id: int,
        status: str,
    ) -> Contract:
        """Update a contract status owned by the requested user."""

        if status not in VALID_STATUSES:
            raise ValidationError("Status kontrak tidak valid.")

        now_iso = datetime.now(timezone.utc).isoformat()

        with transaction(self._conn):
            cursor = self._conn.execute(
                """
                UPDATE contracts
                SET status = ?, updated_at = ?
                WHERE id = ? AND created_by = ?
                """,
                (status, now_iso, contract_id, user_id),
            )

            if cursor.rowcount == 0:
                raise ValidationError("Kontrak tidak ditemukan.")

        return self.get_by_id(contract_id, user_id)

    def delete_contract(
        self,
        contract_id: int,
        user_id: int,
    ) -> bool:
        """Delete a contract owned by the requested user."""

        with transaction(self._conn):
            cursor = self._conn.execute(
                """
                DELETE FROM contracts
                WHERE id = ? AND created_by = ?
                """,
                (contract_id, user_id),
            )

        return cursor.rowcount > 0
