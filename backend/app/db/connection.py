"""SQLite WAL connection factory."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


def create_sqlite_connection(db_path: Path) -> sqlite3.Connection:
    """Open an isolated SQLite connection with mandatory WAL and FK pragmas."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=10.0, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn


@contextmanager
def sqlite_session(db_path: Path) -> Iterator[sqlite3.Connection]:
    """Context manager yielding a properly configured SQLite connection."""
    conn = create_sqlite_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()
