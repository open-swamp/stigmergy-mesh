import unittest
import os
import tempfile
from mesh.core.models import Task
from mesh.storage.wal_engine import WALEngine
from mesh.queues.dead_letter import DeadLetterManager

class TestDeadLetter(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "test_dlq.db")
        self.engine = WALEngine(self.db_path)
        self.engine.initialize_schema()
        self.dlq = DeadLetterManager(self.engine)

    def tearDown(self):
        self.engine.close()
        self.tmpdir.cleanup()

    def test_quarantine_task(self):
        task = Task(queue="failing", payload={"bad": "payload"}, attempts=3, max_attempts=3)
        entry = self.dlq.quarantine(task, reason="retries_exhausted")
        
        self.assertIsNotNone(entry.id)
        self.assertEqual(entry.task_id, task.id)
        self.assertEqual(entry.reason, "retries_exhausted")
        
        items = self.dlq.list_quarantined(queue="failing")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].task_id, task.id)

    def test_replay_dead_letter(self):
        task = Task(queue="recoverable", payload={"key": "val"}, attempts=3)
        entry = self.dlq.quarantine(task, reason="timeout")
        
        replayed_task = self.dlq.replay(entry.id)
        self.assertIsNotNone(replayed_task)
        self.assertEqual(replayed_task.attempts, 0)
        self.assertEqual(replayed_task.status, "pending")
        
        # DLQ should now be empty for that entry
        items = self.dlq.list_quarantined(queue="recoverable")
        self.assertEqual(len(items), 0)

    def test_purge_dead_letter(self):
        task1 = Task(queue="q", payload={"i": 1})
        task2 = Task(queue="q", payload={"i": 2})
        self.dlq.quarantine(task1, reason="err1")
        self.dlq.quarantine(task2, reason="err2")
        
        purged_count = self.dlq.purge()
        self.assertEqual(purged_count, 2)
        self.assertEqual(len(self.dlq.list_quarantined()), 0)

if __name__ == "__main__":
    unittest.main()
