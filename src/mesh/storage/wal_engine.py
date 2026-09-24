import sqlite3
import os
import threading
from contextlib import contextmanager
from typing import Generator

class WALEngine:
    """
    SQLite database engine running in WAL mode with connection management.
    """
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._is_closed = False
        self.lock = threading.Lock()

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def initialize_schema(self) -> None:
        """Initializes tables in WAL mode."""
        with self.get_connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA busy_timeout=5000;")

            conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                queue TEXT,
                payload TEXT,
                priority INTEGER,
                status TEXT,
                attempts INTEGER,
                max_attempts INTEGER,
                run_at REAL,
                lease_until REAL,
                created_at REAL,
                updated_at REAL,
                error TEXT
            );
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                topic TEXT,
                payload TEXT,
                timestamp REAL,
                producer TEXT
            );
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS dead_letter (
                id TEXT PRIMARY KEY,
                task_id TEXT,
                queue TEXT,
                payload TEXT,
                reason TEXT,
                failed_at REAL,
                attempts INTEGER
            );
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                key TEXT PRIMARY KEY,
                value REAL
            );
            """)
            conn.commit()

    def close(self) -> None:
        self._is_closed = True
