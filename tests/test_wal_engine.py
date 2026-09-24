import unittest
import os
import tempfile
import sqlite3
from mesh.storage.wal_engine import WALEngine

class TestWALEngine(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "test_mesh.db")
        self.engine = WALEngine(self.db_path)

    def tearDown(self):
        self.engine.close()
        self.tmpdir.cleanup()

    def test_wal_mode_enabled(self):
        self.engine.initialize_schema()
        with self.engine.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode;")
            mode = cursor.fetchone()[0]
            self.assertEqual(mode.lower(), "wal")

    def test_schema_tables_exist(self):
        self.engine.initialize_schema()
        with self.engine.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            self.assertIn("tasks", tables)
            self.assertIn("events", tables)
            self.assertIn("dead_letter", tables)
            self.assertIn("metrics", tables)

    def test_concurrent_read_write(self):
        self.engine.initialize_schema()
        with self.engine.get_connection() as conn1:
            conn1.execute("INSERT INTO metrics (key, value) VALUES ('test_key', 42);")
            conn1.commit()
            
        with self.engine.get_connection() as conn2:
            cursor = conn2.cursor()
            cursor.execute("SELECT value FROM metrics WHERE key='test_key';")
            val = cursor.fetchone()[0]
            self.assertEqual(val, 42)

if __name__ == "__main__":
    unittest.main()
