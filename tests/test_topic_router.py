import unittest
import os
import tempfile
from mesh.storage.wal_engine import WALEngine
from mesh.pubsub.topic_router import TopicRouter

class TestTopicRouter(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "test_pubsub.db")
        self.engine = WALEngine(self.db_path)
        self.engine.initialize_schema()
        self.router = TopicRouter(self.engine)

    def tearDown(self):
        self.engine.close()
        self.tmpdir.cleanup()

    def test_exact_topic_match(self):
        self.router.subscribe("agent.jules.started", "sub_1")
        self.router.subscribe("agent.claude.started", "sub_2")

        matches = self.router.match_subscribers("agent.jules.started")
        self.assertIn("sub_1", matches)
        self.assertNotIn("sub_2", matches)

    def test_single_token_wildcard(self):
        # '*' matches exactly one dot-separated segment
        self.router.subscribe("agent.*.started", "sub_wild_single")
        
        m1 = self.router.match_subscribers("agent.jules.started")
        m2 = self.router.match_subscribers("agent.claude.started")
        m3 = self.router.match_subscribers("agent.jules.task.started")

        self.assertIn("sub_wild_single", m1)
        self.assertIn("sub_wild_single", m2)
        self.assertNotIn("sub_wild_single", m3)  # too many segments

    def test_multi_token_wildcard(self):
        # '>' or '#' matches one or more trailing segments
        self.router.subscribe("agent.>", "sub_wild_multi")

        m1 = self.router.match_subscribers("agent.jules")
        m2 = self.router.match_subscribers("agent.jules.task.started")
        m3 = self.router.match_subscribers("system.alert")

        self.assertIn("sub_wild_multi", m1)
        self.assertIn("sub_wild_multi", m2)
        self.assertNotIn("sub_wild_multi", m3)

    def test_publish_records_event(self):
        event = self.router.publish(
            topic="agent.jules.heartbeat",
            payload={"load": 0.42},
            producer="jules_runner"
        )
        self.assertIsNotNone(event.id)
        
        events = self.router.list_events(topic="agent.jules.heartbeat")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].payload["load"], 0.42)

if __name__ == "__main__":
    unittest.main()
