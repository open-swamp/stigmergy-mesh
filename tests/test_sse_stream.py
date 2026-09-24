import unittest
from mesh.core.models import Event
from mesh.server.sse_stream import SSEEventFormatter

class TestSSEStream(unittest.TestCase):
    def test_format_sse_message(self):
        event = Event(id="evt-42", topic="mesh.task.created", payload={"task_id": "100"})
        sse_text = SSEEventFormatter.format_event(event)
        
        self.assertIn("id: evt-42\n", sse_text)
        self.assertIn("event: mesh.task.created\n", sse_text)
        self.assertIn("data: ", sse_text)
        self.assertTrue(sse_text.endswith("\n\n"))

    def test_format_raw_sse(self):
        formatted = SSEEventFormatter.format_raw(event_type="heartbeat", data={"uptime": 100}, event_id="hb-1")
        self.assertIn("id: hb-1\n", formatted)
        self.assertIn("event: heartbeat\n", formatted)
        self.assertIn('"uptime": 100', formatted)
        self.assertTrue(formatted.endswith("\n\n"))

if __name__ == "__main__":
    unittest.main()
