import sqlite3
import os
from contextlib import contextmanager
from typing import Generator

class WALEngine:
    """
    SQLite database engine running in WAL mode with connection management.
    """
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._is_closed = False

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
        raise NotImplementedError("To be implemented by Jules")

    def close(self) -> None:
        self._is_closed = True
