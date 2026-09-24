import unittest
import os
import tempfile
import time
from mesh.storage.wal_engine import WALEngine
from mesh.queues.priority_queue import PriorityQueueManager

class TestPriorityQueue(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "test_queue.db")
        self.engine = WALEngine(self.db_path)
        self.engine.initialize_schema()
        self.queue = PriorityQueueManager(self.engine)

    def tearDown(self):
        self.engine.close()
        self.tmpdir.cleanup()

    def test_push_and_pop_order_by_priority(self):
        # Push lower priority first
        t1 = self.queue.push(queue="jobs", payload={"name": "low"}, priority=1)
        # Push higher priority later
        t2 = self.queue.push(queue="jobs", payload={"name": "high"}, priority=10)
        # Push medium priority
        t3 = self.queue.push(queue="jobs", payload={"name": "medium"}, priority=5)

        # First pop should return highest priority (t2)
        popped1 = self.queue.pop(queue="jobs", lease_seconds=10)
        self.assertIsNotNone(popped1)
        self.assertEqual(popped1.id, t2.id)
        self.assertEqual(popped1.status, "active")

        # Second pop should return medium priority (t3)
        popped2 = self.queue.pop(queue="jobs", lease_seconds=10)
        self.assertIsNotNone(popped2)
        self.assertEqual(popped2.id, t3.id)

        # Third pop should return lowest priority (t1)
        popped3 = self.queue.pop(queue="jobs", lease_seconds=10)
        self.assertIsNotNone(popped3)
        self.assertEqual(popped3.id, t1.id)

        # Next pop should be None
        self.assertIsNone(self.queue.pop(queue="jobs"))

    def test_delayed_task_execution(self):
        # Push task with 1-second delay
        t = self.queue.push(queue="delayed", payload={"v": 1}, delay_seconds=1)
        
        # Should not be poppable immediately
        self.assertIsNone(self.queue.pop(queue="delayed"))
        
        # Wait for delay to pass
        time.sleep(1.1)
        
        popped = self.queue.pop(queue="delayed")
        self.assertIsNotNone(popped)
        self.assertEqual(popped.id, t.id)

    def test_ack_completes_task(self):
        t = self.queue.push(queue="work", payload={"job": 1})
        claimed = self.queue.pop(queue="work")
        self.assertIsNotNone(claimed)
        
        ack_res = self.queue.ack(claimed.id)
        self.assertTrue(ack_res)
        
        # Task should not be poppable again
        self.assertIsNone(self.queue.pop(queue="work"))

    def test_nack_requeues_or_retries(self):
        t = self.queue.push(queue="retry_queue", payload={"a": 1}, max_attempts=2)
        claimed = self.queue.pop(queue="retry_queue")
        
        # First failure
        self.queue.nack(claimed.id, error="transient error")
        
        # Can be popped again for second attempt
        claimed2 = self.queue.pop(queue="retry_queue")
        self.assertIsNotNone(claimed2)
        self.assertEqual(claimed2.attempts, 1)

    def test_queue_stats(self):
        self.queue.push(queue="alpha", payload={"x": 1})
        self.queue.push(queue="alpha", payload={"x": 2})
        self.queue.push(queue="beta", payload={"y": 1})
        
        stats = self.queue.stats("alpha")
        self.assertEqual(stats["pending"], 2)

if __name__ == "__main__":
    unittest.main()
