"""SQLite database connection manager."""

import sqlite3
from pathlib import Path
from cryptosafe.config import DEFAULT_DB_PATH

def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Create and return a configured SQLite connection."""
    target_path = db_path if db_path is not None else DEFAULT_DB_PATH
    
    if isinstance(target_path, Path) and str(target_path) != ":memory:":
        target_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(target_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

