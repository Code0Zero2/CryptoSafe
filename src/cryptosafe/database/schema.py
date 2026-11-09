"""Database schema definition and migrations."""

import sqlite3
from datetime import datetime, timezone

CURRENT_SCHEMA_VERSION = 1

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

def init_db(conn: sqlite3.Connection) -> None:
    """Initialize or migrate the database schema."""
    with conn:
        conn.executescript(MIGRATION_V1)
        
        cur = conn.cursor()
        cur.execute("SELECT version FROM schema_version WHERE version = ?", (CURRENT_SCHEMA_VERSION,))
        if not cur.fetchone():
            now_iso = datetime.now(timezone.utc).isoformat()
            cur.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                (CURRENT_SCHEMA_VERSION, now_iso)
            )
