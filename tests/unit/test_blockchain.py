import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

src_dir = Path(__file__).resolve().parent.parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from cryptosafe.database.connection import get_connection
from cryptosafe.database.schema import (
    CURRENT_SCHEMA_VERSION,
    init_db,
    MIGRATION_V1,
    MIGRATION_V2,
    MIGRATION_V3,
    MIGRATION_V4,
)
from cryptosafe.database.user_repository import UserRepository
from cryptosafe.database.blockchain_repository import BlockchainRepository, Block
from cryptosafe.crypto.blockchain_service import (
    BlockchainService,
    GENESIS_PREVIOUS_HASH,
    GENESIS_ASSET_HASH,
    calculate_block_hash,
)
from cryptosafe.common.errors import ValidationError


class TestBlockchainService(unittest.TestCase):
    def setUp(self):
        self.conn = get_connection(":memory:")
        init_db(self.conn)
        self.user_repo = UserRepository(self.conn)
        self.user = self.user_repo.create_user("alice", "hash123")
        self.repo = BlockchainRepository(self.conn)
        self.service = BlockchainService(self.repo)

        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.conn.close()
        self.temp_dir.cleanup()

    def test_schema_version_is_five(self):
        self.assertEqual(CURRENT_SCHEMA_VERSION, 5)
        row = self.conn.execute("SELECT MAX(version) AS version FROM schema_version").fetchone()
        self.assertEqual(row["version"], 5)

    def test_genesis_block_creation(self):
        genesis = self.service.ensure_genesis_block()
        self.assertEqual(genesis.block_index, 0)
        self.assertEqual(genesis.event_type, "GENESIS")
        self.assertEqual(genesis.previous_hash, GENESIS_PREVIOUS_HASH)
        self.assertEqual(genesis.asset_hash, GENESIS_ASSET_HASH)
        self.assertEqual(len(genesis.block_hash), 64)

        # Calling again returns same genesis block without duplicating
        genesis_again = self.service.ensure_genesis_block()
        self.assertEqual(genesis_again.id, genesis.id)
        self.assertEqual(self.repo.get_blocks_count(), 1)

    def test_append_blocks_and_chaining(self):
        sample_hash1 = hashlib.sha256(b"Asset 1 Content").hexdigest()
        sample_hash2 = hashlib.sha256(b"Asset 2 Content").hexdigest()

        b1 = self.service.append_block(
            event_type="CONTRACT_CREATED",
            asset_id="contract:101",
            asset_hash=sample_hash1,
            payload={"title": "Perjanjian A", "parties": "Alice & Bob"},
            created_by=self.user.id,
        )
        self.assertEqual(b1.block_index, 1)

        genesis = self.repo.get_by_index(0)
        self.assertIsNotNone(genesis)
        self.assertEqual(b1.previous_hash, genesis.block_hash)

        b2 = self.service.append_block(
            event_type="FILE_ATTACHED",
            asset_id="file:45",
            asset_hash=sample_hash2,
            payload={"filename": "lampiran.pdf", "size": 1024},
            created_by=self.user.id,
        )
        self.assertEqual(b2.block_index, 2)
        self.assertEqual(b2.previous_hash, b1.block_hash)
        self.assertEqual(self.repo.get_blocks_count(), 3)

    def test_verify_chain_integrity_success(self):
        for i in range(5):
            h = hashlib.sha256(f"Content {i}".encode()).hexdigest()
            self.service.append_block(
                event_type="TEST_EVENT",
                asset_id=f"asset:{i}",
                asset_hash=h,
                payload={"index": i},
                created_by=self.user.id,
            )

        result = self.service.verify_chain_integrity()
        self.assertTrue(result.is_valid)
        self.assertEqual(result.total_blocks, 6)  # 1 genesis + 5 blocks
        self.assertIsNone(result.tampered_index)
        self.assertIsNone(result.error_detail)

    def test_detect_tampered_payload(self):
        for i in range(3):
            h = hashlib.sha256(f"Item {i}".encode()).hexdigest()
            self.service.append_block("EVENT", f"id:{i}", h, {"i": i})

        # Directly tamper payload_json of block 2 in database
        # Bypass trigger by temporarily dropping/recreating trigger or testing tampering
        # Note: triggers protect against UPDATE, let's verify triggers prevent update first!
        pass

    def test_sqlite_trigger_prevents_update_and_delete(self):
        h = hashlib.sha256(b"Document").hexdigest()
        b = self.service.append_block("EVENT", "id:1", h, {"test": True})

        # Attempting UPDATE directly on SQLite must fail via trigger
        with self.assertRaises(sqlite3.IntegrityError) as ctx:
            self.conn.execute(
                "UPDATE blockchain_blocks SET asset_id = 'hacked' WHERE id = ?",
                (b.id,),
            )
        self.assertIn("immutable", str(ctx.exception).lower())

        # Attempting DELETE directly on SQLite must fail via trigger
        with self.assertRaises(sqlite3.IntegrityError) as ctx:
            self.conn.execute(
                "DELETE FROM blockchain_blocks WHERE id = ?",
                (b.id,),
            )
        self.assertIn("immutable", str(ctx.exception).lower())

    def test_detect_tampering_when_trigger_disabled_or_external_modification(self):
        # In a real forensic attack, an attacker with raw SQLite access might drop trigger,
        # edit block, and recreate trigger. Test that verify_chain_integrity catches it!
        for i in range(3):
            h = hashlib.sha256(f"Data {i}".encode()).hexdigest()
            self.service.append_block("EVENT", f"id:{i}", h, {"val": i})

        # Drop trigger temporarily to simulate malicious raw DB tampering
        self.conn.execute("DROP TRIGGER prevent_blockchain_update")
        try:
            # 1. Modify payload of block 1
            self.conn.execute(
                "UPDATE blockchain_blocks SET payload_json = '{\"val\":999}' WHERE block_index = 1"
            )
            res = self.service.verify_chain_integrity()
            self.assertFalse(res.is_valid)
            self.assertEqual(res.tampered_index, 1)
            self.assertIn("dimodifikasi", res.error_detail)

            # Revert payload, but tamper previous_hash
            orig_block = self.repo.get_by_index(1)
            calc_h = calculate_block_hash(
                1, orig_block.timestamp, orig_block.event_type, orig_block.asset_id,
                orig_block.asset_hash, '{"val":0}', orig_block.previous_hash, orig_block.created_by
            )
            self.conn.execute(
                "UPDATE blockchain_blocks SET payload_json = '{\"val\":0}', block_hash = ? WHERE block_index = 1",
                (calc_h,),
            )
            # Tamper previous_hash on block 2
            self.conn.execute(
                "UPDATE blockchain_blocks SET previous_hash = '1111111111111111111111111111111111111111111111111111111111111111' WHERE block_index = 2"
            )
            res2 = self.service.verify_chain_integrity()
            self.assertFalse(res2.is_valid)
            self.assertEqual(res2.tampered_index, 2)
            self.assertIn("tidak cocok dengan hash blok sebelumnya", res2.error_detail)

        finally:
            # Recreate trigger
            self.conn.execute("""
                CREATE TRIGGER IF NOT EXISTS prevent_blockchain_update
                BEFORE UPDATE ON blockchain_blocks
                BEGIN
                    SELECT RAISE(ABORT, 'Blockchain blocks are immutable and cannot be updated.');
                END;
            """)

    def test_detect_deleted_block_gap(self):
        for i in range(4):
            h = hashlib.sha256(f"Doc {i}".encode()).hexdigest()
            self.service.append_block("EVENT", f"id:{i}", h, {"val": i})

        self.conn.execute("DROP TRIGGER prevent_blockchain_delete")
        try:
            # Delete block index 2 (creates gap between 1 and 3)
            self.conn.execute("DELETE FROM blockchain_blocks WHERE block_index = 2")
            res = self.service.verify_chain_integrity()
            self.assertFalse(res.is_valid)
            self.assertEqual(res.tampered_index, 3)
            self.assertIn("terputus", res.error_detail)
        finally:
            self.conn.execute("""
                CREATE TRIGGER IF NOT EXISTS prevent_blockchain_delete
                BEFORE DELETE ON blockchain_blocks
                BEGIN
                    SELECT RAISE(ABORT, 'Blockchain blocks are immutable and cannot be deleted.');
                END;
            """)

    def test_detect_tampered_genesis_block(self):
        self.service.ensure_genesis_block()
        self.conn.execute("DROP TRIGGER prevent_blockchain_update")
        try:
            self.conn.execute(
                "UPDATE blockchain_blocks SET asset_hash = 'abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789' WHERE block_index = 0"
            )
            res = self.service.verify_chain_integrity()
            self.assertFalse(res.is_valid)
            self.assertEqual(res.tampered_index, 0)
        finally:
            self.conn.execute("""
                CREATE TRIGGER IF NOT EXISTS prevent_blockchain_update
                BEFORE UPDATE ON blockchain_blocks
                BEGIN
                    SELECT RAISE(ABORT, 'Blockchain blocks are immutable and cannot be updated.');
                END;
            """)

    def test_append_block_validation(self):
        h = hashlib.sha256(b"Valid").hexdigest()

        # Empty event_type
        with self.assertRaises(ValidationError) as ctx:
            self.service.append_block("", "id:1", h, {"a": 1})
        self.assertIn("Tipe event", str(ctx.exception))

        # Empty asset_id
        with self.assertRaises(ValidationError) as ctx:
            self.service.append_block("EVENT", "", h, {"a": 1})
        self.assertIn("Asset ID", str(ctx.exception))

        # Invalid asset_hash length / characters
        with self.assertRaises(ValidationError) as ctx:
            self.service.append_block("EVENT", "id:1", "not_a_valid_hash", {"a": 1})
        self.assertIn("64 karakter", str(ctx.exception))

        with self.assertRaises(ValidationError) as ctx:
            self.service.append_block("EVENT", "id:1", h[:60], {"a": 1})
        self.assertIn("64 karakter", str(ctx.exception))

    def test_streaming_file_hashing(self):
        test_file = self.temp_path / "test_doc.bin"
        content = b"CryptoSafe Streaming File Hashing Test Data \x00\xff\xfe" * 5000
        test_file.write_bytes(content)

        expected_hash = hashlib.sha256(content).hexdigest().lower()
        actual_hash = self.service.hash_file_streaming(test_file)

        self.assertEqual(actual_hash, expected_hash)

    def test_streaming_file_hashing_nonexistent_raises(self):
        with self.assertRaises(ValidationError) as ctx:
            self.service.hash_file_streaming(self.temp_path / "no_such_file.bin")
        self.assertIn("tidak ditemukan", str(ctx.exception))

    def test_streaming_file_hashing_empty_file(self):
        empty_file = self.temp_path / "empty.txt"
        empty_file.write_bytes(b"")
        expected_hash = hashlib.sha256(b"").hexdigest().lower()
        actual_hash = self.service.hash_file_streaming(empty_file)
        self.assertEqual(actual_hash, expected_hash)

    def test_payload_canonical_json_normalization(self):
        h = hashlib.sha256(b"Data").hexdigest()

        # Append using dict with keys out of order
        b1 = self.service.append_block("EVENT", "id:1", h, {"z": 100, "a": 5, "m": 50})
        self.assertEqual(b1.payload_json, '{"a":5,"m":50,"z":100}')

        # Append using string with spaces and different key order
        b2 = self.service.append_block("EVENT", "id:2", h, '{\n  "z": 100,\n  "a": 5,\n  "m": 50\n}')
        self.assertEqual(b2.payload_json, '{"a":5,"m":50,"z":100}')

        # Invalid JSON string must be rejected
        with self.assertRaises(ValidationError) as ctx:
            self.service.append_block("EVENT", "id:3", h, "{invalid_json:")
        self.assertIn("JSON yang valid", str(ctx.exception))

    def test_detect_tampered_genesis_subfields(self):
        self.service.ensure_genesis_block()
        self.conn.execute("DROP TRIGGER prevent_blockchain_update")
        try:
            # Tamper event_type
            self.conn.execute("UPDATE blockchain_blocks SET event_type = 'MODIFIED' WHERE block_index = 0")
            res = self.service.verify_chain_integrity()
            self.assertFalse(res.is_valid)
            self.assertEqual(res.tampered_index, 0)
            self.assertIn("Tipe event genesis block", res.error_detail)

            # Revert event_type, tamper asset_id
            self.conn.execute("UPDATE blockchain_blocks SET event_type = 'GENESIS', asset_id = 'bad_id' WHERE block_index = 0")
            res = self.service.verify_chain_integrity()
            self.assertFalse(res.is_valid)
            self.assertEqual(res.tampered_index, 0)
            self.assertIn("Asset ID genesis block", res.error_detail)

            # Revert asset_id, tamper payload_json
            self.conn.execute("UPDATE blockchain_blocks SET asset_id = 'genesis', payload_json = '{\"bad\":1}' WHERE block_index = 0")
            res = self.service.verify_chain_integrity()
            self.assertFalse(res.is_valid)
            self.assertEqual(res.tampered_index, 0)
            self.assertIn("Payload JSON genesis block", res.error_detail)
        finally:
            self.conn.execute("""
                CREATE TRIGGER IF NOT EXISTS prevent_blockchain_update
                BEFORE UPDATE ON blockchain_blocks
                BEGIN
                    SELECT RAISE(ABORT, 'Blockchain blocks are immutable and cannot be updated.');
                END;
            """)

    def test_triggers_persist_across_reopened_db_file(self):
        file_db = self.temp_path / "persistent.db"
        conn1 = get_connection(file_db)
        init_db(conn1)

        repo1 = BlockchainRepository(conn1)
        svc1 = BlockchainService(repo1)
        b = svc1.ensure_genesis_block()
        conn1.close()

        # Reopen connection from same file
        conn2 = get_connection(file_db)
        with self.assertRaises(sqlite3.IntegrityError):
            conn2.execute("UPDATE blockchain_blocks SET payload_json = '{}' WHERE block_index = 0")

        with self.assertRaises(sqlite3.IntegrityError):
            conn2.execute("DELETE FROM blockchain_blocks WHERE block_index = 0")
        conn2.close()

    def test_concurrent_genesis_and_append(self):
        import threading
        file_db = self.temp_path / "concurrent.db"
        init_conn = get_connection(file_db)
        init_db(init_conn)
        init_conn.close()

        threads = []
        errors = []

        def worker(worker_id):
            try:
                conn = get_connection(file_db)
                repo = BlockchainRepository(conn)
                svc = BlockchainService(repo)
                h = hashlib.sha256(f"Worker {worker_id}".encode()).hexdigest()
                svc.append_block(
                    event_type="CONCURRENT_EVENT",
                    asset_id=f"worker:{worker_id}",
                    asset_hash=h,
                    payload={"worker": worker_id},
                )
                conn.close()
            except Exception as e:
                errors.append(e)

        for i in range(8):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(errors, [])
        check_conn = get_connection(file_db)
        check_repo = BlockchainRepository(check_conn)
        check_svc = BlockchainService(check_repo)
        self.assertEqual(check_repo.get_blocks_count(), 9)  # 1 genesis + 8 blocks

        res = check_svc.verify_chain_integrity()
        self.assertTrue(res.is_valid)
        self.assertEqual(res.total_blocks, 9)
        check_conn.close()

    def test_verify_asset_file_roundtrip(self):
        doc1 = self.temp_path / "doc1.txt"
        doc1.write_text("Kontrak Kerja Sama Strategis 2026", encoding="utf-8")
        doc1_hash = self.service.hash_file_streaming(doc1)

        self.service.append_block(
            event_type="CONTRACT_REGISTERED",
            asset_id="contract:501",
            asset_hash=doc1_hash,
            payload={"title": "Kontrak Kerja Sama"},
        )

        found, block, chain_res = self.service.verify_asset_file(doc1)
        self.assertTrue(found)
        self.assertIsNotNone(block)
        self.assertEqual(block.asset_hash, doc1_hash)
        self.assertTrue(chain_res.is_valid)

        # Unregistered document returns False
        doc2 = self.temp_path / "doc2.txt"
        doc2.write_text("Dokumen Berbeda", encoding="utf-8")
        found2, block2, _ = self.service.verify_asset_file(doc2)
        self.assertFalse(found2)
        self.assertIsNone(block2)

    def test_two_python_processes_append_concurrently(self):
        """Verify that two distinct Python processes can append blocks concurrently to the same SQLite DB."""
        import subprocess
        proc_db = self.temp_path / "multiprocess.db"
        init_conn = get_connection(proc_db)
        init_db(init_conn)
        init_conn.close()

        worker_script = f"""
import sys
sys.path.insert(0, r"{src_dir}")
import hashlib
from cryptosafe.database.connection import get_connection
from cryptosafe.database.blockchain_repository import BlockchainRepository
from cryptosafe.crypto.blockchain_service import BlockchainService

tag = sys.argv[1]
conn = get_connection(r"{proc_db}")
repo = BlockchainRepository(conn)
svc = BlockchainService(repo)

for i in range(3):
    h = hashlib.sha256(f"{{tag}}-{{i}}".encode()).hexdigest()
    svc.append_block("PROC_EVENT", f"asset:{{tag}}:{{i}}", h, {{"worker": tag, "seq": i}})
conn.close()
"""
        script_file = self.temp_path / "worker.py"
        script_file.write_text(worker_script, encoding="utf-8")

        p1 = subprocess.Popen([sys.executable, str(script_file), "processA"])
        p2 = subprocess.Popen([sys.executable, str(script_file), "processB"])

        p1.wait(timeout=15)
        p2.wait(timeout=15)

        self.assertEqual(p1.returncode, 0)
        self.assertEqual(p2.returncode, 0)

        verify_conn = get_connection(proc_db)
        verify_repo = BlockchainRepository(verify_conn)
        verify_svc = BlockchainService(verify_repo)

        # Total: 1 genesis + 3 from processA + 3 from processB = 7 blocks
        self.assertEqual(verify_repo.get_blocks_count(), 7)
        res = verify_svc.verify_chain_integrity()
        self.assertTrue(res.is_valid)
        self.assertEqual(res.total_blocks, 7)
        verify_conn.close()

    def test_retry_on_operational_error_database_locked(self):
        """Verify append_block retries and succeeds if a transient 'database is locked' OperationalError occurs."""
        from unittest.mock import patch
        self.service.ensure_genesis_block()
        original_create = self.repo.create_block
        calls = {"count": 0}

        def mock_create(*args, **kwargs):
            calls["count"] += 1
            if calls["count"] == 1:
                # Simulate SQLite database is locked on the first attempt
                raise sqlite3.OperationalError("database is locked")
            return original_create(*args, **kwargs)

        with patch.object(self.repo, "create_block", side_effect=mock_create):
            h = hashlib.sha256(b"LockTest").hexdigest()
            block = self.service.append_block("LOCK_EVENT", "asset:lock", h, {"test": True})
            self.assertEqual(calls["count"], 2)
            self.assertEqual(block.asset_id, "asset:lock")

    def test_no_retry_on_permanent_operational_error(self):
        """Verify permanent operational errors (e.g. no such table) fail immediately without retrying."""
        from unittest.mock import patch
        self.service.ensure_genesis_block()
        calls = {"count": 0}

        def mock_create(*args, **kwargs):
            calls["count"] += 1
            raise sqlite3.OperationalError("no such table: blockchain_blocks")

        from cryptosafe.common.errors import CryptoOperationError
        with patch.object(self.repo, "create_block", side_effect=mock_create):
            h = hashlib.sha256(b"PermTest").hexdigest()
            with self.assertRaises(CryptoOperationError) as ctx:
                self.service.append_block("PERM_EVENT", "asset:perm", h, {"test": True})
            self.assertEqual(calls["count"], 1)  # Only 1 attempt, no useless retries
            self.assertIn("Gagal menulis ke blockchain", str(ctx.exception))

    def test_no_retry_on_permanent_foreign_key_integrity_error(self):
        """Verify permanent integrity error (foreign key constraint) fails immediately without retry."""
        h = hashlib.sha256(b"FKTest").hexdigest()
        # created_by=999999 does not exist in users table
        with self.assertRaises(sqlite3.IntegrityError):
            self.service.append_block("FK_EVENT", "asset:fk", h, {"test": True}, created_by=999999)

    def test_database_migration_v4_to_v5_preserves_data(self):
        """Verify that an existing V4 database migrates cleanly to V5 without losing data."""
        mig_conn = get_connection(":memory:")
        # Execute only V1 through V4 manually
        mig_conn.executescript(MIGRATION_V1)
        mig_conn.executescript(MIGRATION_V2)
        mig_conn.executescript(MIGRATION_V3)
        mig_conn.executescript(MIGRATION_V4)
        for v in (1, 2, 3, 4):
            mig_conn.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (?, '2026-11-10')",
                (v,),
            )

        # Insert sample user and contract into V4 schema
        mig_conn.execute(
            "INSERT INTO users (username, password_hash, is_active, created_at, updated_at) "
            "VALUES ('alice', 'hash123', 1, '2026-11-10', '2026-11-10')"
        )
        user_id = mig_conn.execute("SELECT id FROM users WHERE username='alice'").fetchone()["id"]

        mig_conn.execute(
            "INSERT INTO contracts (contract_number, title, parties, status, created_by, created_at, updated_at) "
            "VALUES ('CTR-V4', 'Kontrak Lama V4', 'Pihak 1 & 2', 'Signed', ?, '2026-11-10', '2026-11-10')",
            (user_id,),
        )

        # Run init_db which should upgrade V4 -> V5
        init_db(mig_conn)

        # Check schema version is now 5
        cur_v = mig_conn.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()["v"]
        self.assertEqual(cur_v, 5)

        # Check prior user and contract still exist
        user_row = mig_conn.execute("SELECT * FROM users WHERE username='alice'").fetchone()
        self.assertIsNotNone(user_row)
        self.assertEqual(user_row["username"], "alice")

        contract_row = mig_conn.execute("SELECT * FROM contracts WHERE contract_number='CTR-V4'").fetchone()
        self.assertIsNotNone(contract_row)
        self.assertEqual(contract_row["title"], "Kontrak Lama V4")

        # Check new blockchain_blocks table exists and is operational
        b_repo = BlockchainRepository(mig_conn)
        b_service = BlockchainService(b_repo)
        genesis = b_service.ensure_genesis_block()
        self.assertEqual(genesis.block_index, 0)
        mig_conn.close()


if __name__ == "__main__":
    unittest.main()
