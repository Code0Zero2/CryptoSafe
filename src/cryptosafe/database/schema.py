"""Database schema definition and migrations."""

import sqlite3
from datetime import datetime, timezone

CURRENT_SCHEMA_VERSION = 5

MIGRATION_V1 = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
"""

MIGRATION_V2 = """
CREATE TABLE IF NOT EXISTS usb_credentials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    token_id TEXT NOT NULL UNIQUE,
    verifier TEXT NOT NULL,
    created_at TEXT NOT NULL,
    revoked_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_usb_user_id ON usb_credentials(user_id);
CREATE INDEX IF NOT EXISTS idx_usb_token_id ON usb_credentials(token_id);
"""

MIGRATION_V3 = """
CREATE TABLE IF NOT EXISTS face_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    encrypted_template TEXT NOT NULL,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    consent_recorded_at TEXT NOT NULL,
    revoked_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_face_user_id ON face_profiles(user_id);
"""

MIGRATION_V4 = """
CREATE TABLE IF NOT EXISTS contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_number TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    parties TEXT NOT NULL,
    start_date TEXT,
    end_date TEXT,
    status TEXT NOT NULL DEFAULT 'Draft'
        CHECK (status IN (
            'Draft',
            'Review',
            'Approved',
            'Signed',
            'Archived'
        )),
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_contracts_created_by
ON contracts(created_by);

CREATE INDEX IF NOT EXISTS idx_contracts_status
ON contracts(status);


CREATE TABLE IF NOT EXISTS encrypted_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id INTEGER NOT NULL REFERENCES contracts(id)
        ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id),
    content_type TEXT NOT NULL
        CHECK (content_type IN ('note', 'clause', 'draft')),
    label TEXT NOT NULL,
    ciphertext TEXT NOT NULL,
    algorithm TEXT NOT NULL DEFAULT 'AES-256-GCM+Vigenere',
    envelope_version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_contract_id
ON encrypted_messages(contract_id);

CREATE INDEX IF NOT EXISTS idx_messages_user_id
ON encrypted_messages(user_id);


CREATE TABLE IF NOT EXISTS contract_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id INTEGER NOT NULL REFERENCES contracts(id)
        ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id),
    original_filename TEXT NOT NULL,
    encrypted_path TEXT NOT NULL UNIQUE,
    mime_type TEXT,
    size_bytes INTEGER NOT NULL,
    algorithm TEXT NOT NULL DEFAULT 'ChaCha20-Poly1305',
    envelope_version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_files_contract_id
ON contract_files(contract_id);

CREATE INDEX IF NOT EXISTS idx_files_user_id
ON contract_files(user_id);
"""

MIGRATION_V5 = """
CREATE TABLE IF NOT EXISTS blockchain_blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    block_index INTEGER NOT NULL UNIQUE,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    asset_hash TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    previous_hash TEXT NOT NULL,
    block_hash TEXT NOT NULL,
    created_by INTEGER REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_blockchain_index
ON blockchain_blocks(block_index);

CREATE INDEX IF NOT EXISTS idx_blockchain_asset_id
ON blockchain_blocks(asset_id);

CREATE INDEX IF NOT EXISTS idx_blockchain_asset_hash
ON blockchain_blocks(asset_hash);

CREATE TRIGGER IF NOT EXISTS prevent_blockchain_update
BEFORE UPDATE ON blockchain_blocks
BEGIN
    SELECT RAISE(ABORT, 'Blockchain blocks are immutable and cannot be updated.');
END;

CREATE TRIGGER IF NOT EXISTS prevent_blockchain_delete
BEFORE DELETE ON blockchain_blocks
BEGIN
    SELECT RAISE(ABORT, 'Blockchain blocks are immutable and cannot be deleted.');
END;
"""


def init_db(conn: sqlite3.Connection) -> None:
    """Initialize or migrate the database schema."""
    with conn:
        conn.executescript(MIGRATION_V1)
        cur = conn.cursor()
        cur.execute("SELECT version FROM schema_version WHERE version = 1")
        now_iso = datetime.now(timezone.utc).isoformat()
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (1, ?)",
                (now_iso,)
            )

        conn.executescript(MIGRATION_V2)
        cur.execute("SELECT version FROM schema_version WHERE version = 2")
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (2, ?)",
                (now_iso,)
            )

        conn.executescript(MIGRATION_V3)
        cur.execute("SELECT version FROM schema_version WHERE version = 3")
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (3, ?)",
                (now_iso,)
            )

        conn.executescript(MIGRATION_V4)
        cur.execute("SELECT version FROM schema_version WHERE version = 4")
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (4, ?)",
                (now_iso,)
            )

        conn.executescript(MIGRATION_V5)
        cur.execute("SELECT version FROM schema_version WHERE version = 5")
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (5, ?)",
                (now_iso,)
            )
