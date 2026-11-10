"""Local SHA-256 Blockchain / Hash Chain service for asset integrity tracking."""

import hashlib
import json
import logging
import re
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from cryptosafe.common.errors import CryptoOperationError, ValidationError
from cryptosafe.database.blockchain_repository import Block, BlockchainRepository

logger = logging.getLogger("cryptosafe.crypto.blockchain")

GENESIS_PREVIOUS_HASH = "0" * 64
GENESIS_ASSET_HASH = "0" * 64
GENESIS_EVENT_TYPE = "GENESIS"
GENESIS_ASSET_ID = "genesis"
GENESIS_PAYLOAD = {"message": "CryptoSafe Genesis Block", "version": 1}
GENESIS_PAYLOAD_JSON = json.dumps(
    GENESIS_PAYLOAD,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=False,
)
HEX_64_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


@dataclass(frozen=True)
class VerificationResult:
    """Structured report of blockchain integrity verification."""

    is_valid: bool
    total_blocks: int
    tampered_index: int | None = None
    error_detail: str | None = None


def calculate_block_hash(
    block_index: int,
    timestamp: str,
    event_type: str,
    asset_id: str,
    asset_hash: str,
    payload_json: str,
    previous_hash: str,
    created_by: int | None = None,
) -> str:
    """Calculate deterministic SHA-256 digest of block contents via canonical JSON.

    Excludes database row ID and block_hash itself.
    """
    block_data = {
        "asset_hash": asset_hash.lower(),
        "asset_id": asset_id,
        "block_index": block_index,
        "created_by": created_by,
        "event_type": event_type,
        "payload_json": payload_json,
        "previous_hash": previous_hash.lower(),
        "timestamp": timestamp,
    }

    canonical_json = json.dumps(
        block_data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest().lower()


class BlockchainService:
    """Manages append-only SHA-256 hash chain and document verification."""

    def __init__(self, repository: BlockchainRepository):
        self._repository = repository
        self._lock = threading.RLock()

    @property
    def repository(self) -> BlockchainRepository:
        return self._repository

    def ensure_genesis_block(self) -> Block:
        """Create genesis block if chain is empty, or return existing genesis block."""
        with self._lock:
            max_attempts = 5
            for attempt in range(max_attempts):
                try:
                    last_block = self._repository.get_last_block()
                    if last_block is not None:
                        return self._repository.get_by_index(0) or last_block

                    now_iso = datetime.now(timezone.utc).isoformat()
                    payload_json = GENESIS_PAYLOAD_JSON

                    block_hash = calculate_block_hash(
                        block_index=0,
                        timestamp=now_iso,
                        event_type=GENESIS_EVENT_TYPE,
                        asset_id=GENESIS_ASSET_ID,
                        asset_hash=GENESIS_ASSET_HASH,
                        payload_json=payload_json,
                        previous_hash=GENESIS_PREVIOUS_HASH,
                        created_by=None,
                    )

                    genesis = self._repository.create_block(
                        block_index=0,
                        timestamp=now_iso,
                        event_type=GENESIS_EVENT_TYPE,
                        asset_id=GENESIS_ASSET_ID,
                        asset_hash=GENESIS_ASSET_HASH,
                        payload_json=payload_json,
                        previous_hash=GENESIS_PREVIOUS_HASH,
                        block_hash=block_hash,
                        created_by=None,
                    )
                    logger.info("Initialized Genesis block with hash %s", block_hash)
                    return genesis

                except ValidationError as err:
                    # If genesis was inserted concurrently by another process, return existing
                    if "sudah ada di blockchain" in str(err):
                        existing = self._repository.get_by_index(0)
                        if existing is not None:
                            return existing
                    if attempt < max_attempts - 1:
                        import time
                        time.sleep(0.02 * (attempt + 1))
                        continue
                    raise

                except sqlite3.OperationalError as err:
                    err_msg = str(err).lower()
                    if ("locked" in err_msg or "busy" in err_msg) and attempt < max_attempts - 1:
                        import time
                        time.sleep(0.03 * (attempt + 1))
                        continue
                    raise CryptoOperationError(f"Gagal menginisialisasi genesis block: {err}") from err

    def append_block(
        self,
        event_type: str,
        asset_id: str,
        asset_hash: str,
        payload: dict | str,
        created_by: int | None = None,
    ) -> Block:
        """Append a new verified block to the blockchain atomically."""
        if not event_type or not isinstance(event_type, str) or not event_type.strip():
            raise ValidationError("Tipe event tidak boleh kosong.")

        if not asset_id or not isinstance(asset_id, str) or not asset_id.strip():
            raise ValidationError("Asset ID tidak boleh kosong.")

        if not asset_hash or not isinstance(asset_hash, str) or not HEX_64_PATTERN.match(asset_hash.strip()):
            raise ValidationError("Asset hash harus berupa 64 karakter heksadesimal SHA-256 yang valid.")

        clean_event = event_type.strip()
        clean_asset_id = asset_id.strip()
        clean_asset_hash = asset_hash.strip().lower()

        # Format payload as strictly canonical JSON
        if isinstance(payload, dict):
            payload_json = json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )
        elif isinstance(payload, str):
            clean_str = payload.strip()
            if not clean_str:
                raise ValidationError("Payload tidak boleh kosong.")
            try:
                parsed = json.loads(clean_str)
            except (json.JSONDecodeError, ValueError) as err:
                raise ValidationError(f"Payload harus berupa string JSON yang valid: {err}")

            if isinstance(parsed, (dict, list)):
                payload_json = json.dumps(
                    parsed,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                )
            else:
                raise ValidationError("Struktur JSON payload harus berupa objek (dict) atau array.")
        else:
            raise ValidationError("Payload harus berupa dict atau string JSON valid.")

        with self._lock:
            # Ensure genesis block exists first
            self.ensure_genesis_block()

            # Retry loop in case of multi-process concurrent index contention or locked DB
            max_attempts = 5
            for attempt in range(max_attempts):
                try:
                    last_block = self._repository.get_last_block()
                    if last_block is None:
                        raise CryptoOperationError("Gagal mengambil blok terakhir blockchain.")

                    next_index = last_block.block_index + 1
                    previous_hash = last_block.block_hash.lower()
                    now_iso = datetime.now(timezone.utc).isoformat()

                    block_hash = calculate_block_hash(
                        block_index=next_index,
                        timestamp=now_iso,
                        event_type=clean_event,
                        asset_id=clean_asset_id,
                        asset_hash=clean_asset_hash,
                        payload_json=payload_json,
                        previous_hash=previous_hash,
                        created_by=created_by,
                    )

                    new_block = self._repository.create_block(
                        block_index=next_index,
                        timestamp=now_iso,
                        event_type=clean_event,
                        asset_id=clean_asset_id,
                        asset_hash=clean_asset_hash,
                        payload_json=payload_json,
                        previous_hash=previous_hash,
                        block_hash=block_hash,
                        created_by=created_by,
                    )
                    logger.info(
                        "Appended block %d (event=%s, asset=%s) with hash %s",
                        next_index, clean_event, clean_asset_id, block_hash,
                    )
                    return new_block

                except ValidationError as err:
                    # Selectively retry ONLY when another concurrent process/thread appended the same index
                    if "sudah ada di blockchain" in str(err) and attempt < max_attempts - 1:
                        logger.warning("Concurrent append detected on index %d, retrying attempt %d...", next_index, attempt + 1)
                        import time
                        time.sleep(0.02 * (attempt + 1))
                        continue
                    # Permanent validation error: do not retry
                    logger.error("Permanent validation error appending block: %s", err)
                    raise

                except sqlite3.OperationalError as err:
                    # Selectively retry ONLY on transient SQLite database locked / busy
                    err_msg = str(err).lower()
                    if ("locked" in err_msg or "busy" in err_msg) and attempt < max_attempts - 1:
                        logger.warning("Database locked/busy on attempt %d, retrying...", attempt + 1)
                        import time
                        time.sleep(0.04 * (attempt + 1))
                        continue
                    # Permanent operational error: do not retry
                    logger.error("Permanent database operational error: %s", err)
                    raise CryptoOperationError(f"Gagal menulis ke blockchain: {err}") from err

    def verify_chain_integrity(self) -> VerificationResult:
        """Verify the cryptographic integrity of the entire blockchain.

        Checks:
        1. Genesis block correctness (index 0, previous_hash zeros, hash matches).
        2. Sequence order without any gaps or jumps.
        3. Continuity: block[i].previous_hash == block[i-1].block_hash.
        4. Recomputation of SHA-256 digest for every block matches stored block_hash.
        """
        blocks = self._repository.get_all_blocks()
        total_blocks = len(blocks)

        if total_blocks == 0:
            return VerificationResult(is_valid=True, total_blocks=0)

        # 1. Verify Genesis Block (Index 0)
        genesis = blocks[0]
        if genesis.block_index != 0:
            return VerificationResult(
                is_valid=False,
                total_blocks=total_blocks,
                tampered_index=genesis.block_index,
                error_detail="Blok pertama bukan genesis block (index harus 0).",
            )

        if genesis.previous_hash.lower() != GENESIS_PREVIOUS_HASH:
            return VerificationResult(
                is_valid=False,
                total_blocks=total_blocks,
                tampered_index=0,
                error_detail="Previous hash genesis block harus terdiri dari 64 karakter nol.",
            )

        if genesis.event_type != GENESIS_EVENT_TYPE:
            return VerificationResult(
                is_valid=False,
                total_blocks=total_blocks,
                tampered_index=0,
                error_detail=f"Tipe event genesis block tidak valid (ditemukan '{genesis.event_type}').",
            )

        if genesis.asset_id != GENESIS_ASSET_ID:
            return VerificationResult(
                is_valid=False,
                total_blocks=total_blocks,
                tampered_index=0,
                error_detail=f"Asset ID genesis block tidak valid (ditemukan '{genesis.asset_id}').",
            )

        if genesis.asset_hash.lower() != GENESIS_ASSET_HASH:
            return VerificationResult(
                is_valid=False,
                total_blocks=total_blocks,
                tampered_index=0,
                error_detail="Asset hash genesis block harus terdiri dari 64 karakter nol.",
            )

        if genesis.payload_json != GENESIS_PAYLOAD_JSON:
            return VerificationResult(
                is_valid=False,
                total_blocks=total_blocks,
                tampered_index=0,
                error_detail="Payload JSON genesis block tidak valid atau telah dimodifikasi.",
            )

        expected_genesis_hash = calculate_block_hash(
            block_index=0,
            timestamp=genesis.timestamp,
            event_type=genesis.event_type,
            asset_id=genesis.asset_id,
            asset_hash=genesis.asset_hash,
            payload_json=genesis.payload_json,
            previous_hash=genesis.previous_hash,
            created_by=genesis.created_by,
        )

        if genesis.block_hash.lower() != expected_genesis_hash:
            return VerificationResult(
                is_valid=False,
                total_blocks=total_blocks,
                tampered_index=0,
                error_detail="Data pada Genesis Block telah dimodifikasi (hash mismatch).",
            )

        # 2. Verify all subsequent blocks
        for i in range(1, total_blocks):
            curr = blocks[i]
            prev = blocks[i - 1]

            # Index sequence check
            if curr.block_index != i:
                return VerificationResult(
                    is_valid=False,
                    total_blocks=total_blocks,
                    tampered_index=curr.block_index,
                    error_detail=f"Urutan index terputus pada posisi {i}: ditemukan index {curr.block_index}.",
                )

            # Previous hash linkage check
            if curr.previous_hash.lower() != prev.block_hash.lower():
                return VerificationResult(
                    is_valid=False,
                    total_blocks=total_blocks,
                    tampered_index=curr.block_index,
                    error_detail=(
                        f"Previous hash pada blok {curr.block_index} ({curr.previous_hash[:16]}...) "
                        f"tidak cocok dengan hash blok sebelumnya ({prev.block_hash[:16]}...)."
                    ),
                )

            # Recompute block hash
            expected_hash = calculate_block_hash(
                block_index=curr.block_index,
                timestamp=curr.timestamp,
                event_type=curr.event_type,
                asset_id=curr.asset_id,
                asset_hash=curr.asset_hash,
                payload_json=curr.payload_json,
                previous_hash=curr.previous_hash,
                created_by=curr.created_by,
            )

            if curr.block_hash.lower() != expected_hash:
                return VerificationResult(
                    is_valid=False,
                    total_blocks=total_blocks,
                    tampered_index=curr.block_index,
                    error_detail=(
                        f"Data pada blok {curr.block_index} telah dimodifikasi atau hash rusak "
                        f"(tersimpan: {curr.block_hash[:16]}..., kalkulasi: {expected_hash[:16]}...)."
                    ),
                )

        return VerificationResult(is_valid=True, total_blocks=total_blocks)

    def hash_file_streaming(self, file_path: str | Path, chunk_size: int = 65536) -> str:
        """Calculate SHA-256 digest of a file in chunks without reading entire file into memory."""
        path = Path(file_path).resolve()
        if not path.is_file():
            raise ValidationError(f"Berkas tidak ditemukan: {path}")

        if not isinstance(chunk_size, int) or chunk_size <= 0:
            chunk_size = 65536

        hasher = hashlib.sha256()
        try:
            with open(path, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    hasher.update(chunk)
            return hasher.hexdigest().lower()
        except OSError as err:
            raise ValidationError(f"Gagal membaca berkas untuk hashing: {err}") from err

    def verify_asset_file(self, file_path: str | Path) -> tuple[bool, Block | None, VerificationResult]:
        """Verify if a document matches any recorded block hash, and check chain integrity."""
        file_hash = self.hash_file_streaming(file_path)
        chain_result = self.verify_chain_integrity()

        matching_blocks = self._repository.find_by_asset_hash(file_hash)
        if not matching_blocks:
            return False, None, chain_result

        # Return latest matching block
        return True, matching_blocks[-1], chain_result
