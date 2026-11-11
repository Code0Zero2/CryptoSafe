"""SQLite database connection and transaction manager."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
import itertools
from pathlib import Path
import sqlite3
import threading
from cryptosafe.config import DEFAULT_DB_PATH

_savepoint_seq = itertools.count(1)
_savepoint_lock = threading.Lock()


def _next_savepoint_name() -> str:
    """Generate a unique savepoint identifier."""
    with _savepoint_lock:
        return f"cs_sp_{next(_savepoint_seq)}"


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Create and return a configured SQLite connection."""
    target_path = db_path if db_path is not None else DEFAULT_DB_PATH
    
    if isinstance(target_path, Path) and str(target_path) != ":memory:":
        target_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(target_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Generator[sqlite3.Connection, None, None]:
    """Provide an atomic transaction context manager using SQLite SAVEPOINTs.

    Supports safe nesting without premature commits:
    - Inner blocks create nested savepoints; rolling back an inner block only rolls
      back changes made within that block.
    - Outer blocks govern the final persistence of all nested changes.
    - An unhandled exception in any block triggers a rollback to its savepoint.
    - Standalone (outermost) blocks commit changes when released.
    """
    sp_name = _next_savepoint_name()
    conn.execute(f"SAVEPOINT {sp_name}")
    try:
        yield conn
    except BaseException:
        try:
            conn.execute(f"ROLLBACK TO SAVEPOINT {sp_name}")
            conn.execute(f"RELEASE SAVEPOINT {sp_name}")
        except Exception:
            pass
        raise
    else:
        conn.execute(f"RELEASE SAVEPOINT {sp_name}")

