"""Database schema definition and migrations."""

import sqlite3
from datetime import datetime, timezone

CURRENT_SCHEMA_VERSION = 3

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

