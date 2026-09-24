import unittest
import os
import tempfile
from mesh.storage.wal_engine import WALEngine
from mesh.metrics.collector import MetricsCollector

class TestMetrics(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "test_metrics.db")
        self.engine = WALEngine(self.db_path)
        self.engine.initialize_schema()
        self.metrics = MetricsCollector(self.engine)

    def tearDown(self):
        self.engine.close()
        self.tmpdir.cleanup()

    def test_increment_counter(self):
        self.metrics.increment("tasks_pushed", amount=1)
        self.metrics.increment("tasks_pushed", amount=3)
        
        val = self.metrics.get_counter("tasks_pushed")
        self.assertEqual(val, 4)

    def test_record_duration(self):
        self.metrics.record_duration("task_latency_ms", 12.5)
        self.metrics.record_duration("task_latency_ms", 25.0)
        
        stats = self.metrics.get_duration_stats("task_latency_ms")
        self.assertEqual(stats["count"], 2)
        self.assertAlmostEqual(stats["avg"], 18.75)

    def test_snapshot_all(self):
        self.metrics.increment("events_published", 10)
        snapshot = self.metrics.get_snapshot()
        self.assertIn("events_published", snapshot["counters"])
        self.assertEqual(snapshot["counters"]["events_published"], 10)

if __name__ == "__main__":
    unittest.main()
