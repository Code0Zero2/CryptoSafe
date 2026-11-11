"""Blockchain block persistence repository using parameterized SQLite queries."""

import sqlite3
from dataclasses import dataclass
from cryptosafe.common.errors import ValidationError
from cryptosafe.database.connection import transaction


@dataclass(frozen=True)
class Block:
    """Immutable representation of a blockchain block."""

    id: int
    block_index: int
    timestamp: str
    event_type: str
    asset_id: str
    asset_hash: str
    payload_json: str
    previous_hash: str
    block_hash: str
    created_by: int | None = None


class BlockchainRepository:
    """Repository handling append-only blockchain block persistence in SQLite."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    @property
    def conn(self) -> sqlite3.Connection:
        """Return the underlying SQLite connection."""
        return self._conn

    @staticmethod
    def _row_to_block(row: sqlite3.Row) -> Block:
        return Block(
            id=row["id"],
            block_index=row["block_index"],
            timestamp=row["timestamp"],
            event_type=row["event_type"],
            asset_id=row["asset_id"],
            asset_hash=row["asset_hash"],
            payload_json=row["payload_json"],
            previous_hash=row["previous_hash"],
            block_hash=row["block_hash"],
            created_by=row["created_by"],
        )

    def create_block(
        self,
        block_index: int,
        timestamp: str,
        event_type: str,
        asset_id: str,
        asset_hash: str,
        payload_json: str,
        previous_hash: str,
        block_hash: str,
        created_by: int | None = None,
        external_transaction: bool = False,
    ) -> Block:
        """Insert a new block into the blockchain.

        Strictly append-only; update or delete are blocked by DB triggers.
        Uses savepoint transactions to participate safely in outer transactions
        without premature commits.
        """
        if not isinstance(block_index, int) or block_index < 0:
            raise ValidationError("Index blok harus berupa bilangan bulat non-negatif.")

        if not timestamp or not isinstance(timestamp, str):
            raise ValidationError("Timestamp blok wajib diisi.")

        if not event_type or not isinstance(event_type, str):
            raise ValidationError("Tipe event blok wajib diisi.")

        if not asset_id or not isinstance(asset_id, str):
            raise ValidationError("Asset ID wajib diisi.")

        if not asset_hash or not isinstance(asset_hash, str):
            raise ValidationError("Asset hash wajib diisi.")

        if not payload_json or not isinstance(payload_json, str):
            raise ValidationError("Payload JSON wajib diisi.")

        if not previous_hash or not isinstance(previous_hash, str):
            raise ValidationError("Previous hash wajib diisi.")

        if not block_hash or not isinstance(block_hash, str):
            raise ValidationError("Block hash wajib diisi.")

        try:
            with transaction(self._conn):
                cursor = self._conn.execute(
                    """
                    INSERT INTO blockchain_blocks (
                        block_index,
                        timestamp,
                        event_type,
                        asset_id,
                        asset_hash,
                        payload_json,
                        previous_hash,
                        block_hash,
                        created_by
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        block_index,
                        timestamp,
                        event_type,
                        asset_id,
                        asset_hash,
                        payload_json,
                        previous_hash,
                        block_hash,
                        created_by,
                    ),
                )
                block_id = cursor.lastrowid

            return Block(
                id=block_id,
                block_index=block_index,
                timestamp=timestamp,
                event_type=event_type,
                asset_id=asset_id,
                asset_hash=asset_hash,
                payload_json=payload_json,
                previous_hash=previous_hash,
                block_hash=block_hash,
                created_by=created_by,
            )

        except sqlite3.IntegrityError as err:
            if "blockchain_blocks.block_index" in str(err) or "UNIQUE constraint failed" in str(err):
                raise ValidationError(f"Blok dengan index {block_index} sudah ada di blockchain.") from err
            raise

    def get_by_index(self, block_index: int) -> Block | None:
        """Retrieve a block by its block_index."""
        row = self._conn.execute(
            """
            SELECT *
            FROM blockchain_blocks
            WHERE block_index = ?
            """,
            (block_index,),
        ).fetchone()

        if row is None:
            return None
        return self._row_to_block(row)

    def get_last_block(self) -> Block | None:
        """Retrieve the latest block in the chain."""
        row = self._conn.execute(
            """
            SELECT *
            FROM blockchain_blocks
            ORDER BY block_index DESC
            LIMIT 1
            """
        ).fetchone()

        if row is None:
            return None
        return self._row_to_block(row)

    def get_all_blocks(self) -> list[Block]:
        """Return all blocks ordered by block_index ascending."""
        rows = self._conn.execute(
            """
            SELECT *
            FROM blockchain_blocks
            ORDER BY block_index ASC
            """
        ).fetchall()

        return [self._row_to_block(row) for row in rows]

    def get_blocks_count(self) -> int:
        """Return total number of blocks in the blockchain."""
        row = self._conn.execute(
            "SELECT COUNT(*) AS total FROM blockchain_blocks"
        ).fetchone()
        return row["total"] if row else 0

    def find_by_asset_id(self, asset_id: str) -> list[Block]:
        """Find blocks associated with a specific asset_id."""
        rows = self._conn.execute(
            """
            SELECT *
            FROM blockchain_blocks
            WHERE asset_id = ?
            ORDER BY block_index ASC
            """,
            (asset_id,),
        ).fetchall()

        return [self._row_to_block(row) for row in rows]

    def find_by_asset_hash(self, asset_hash: str) -> list[Block]:
        """Find blocks associated with a specific asset_hash."""
        rows = self._conn.execute(
            """
            SELECT *
            FROM blockchain_blocks
            WHERE LOWER(asset_hash) = LOWER(?)
            ORDER BY block_index ASC
            """,
            (asset_hash,),
        ).fetchall()

        return [self._row_to_block(row) for row in rows]
