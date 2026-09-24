import unittest
from mesh.core.models import Task, Event, DeadLetterEntry

class TestModels(unittest.TestCase):
    def test_task_serialization(self):
        task = Task(queue="jobs", payload={"cmd": "build"}, priority=10)
        data = task.to_dict()
        self.assertEqual(data["queue"], "jobs")
        self.assertEqual(data["priority"], 10)
        self.assertEqual(data["payload"]["cmd"], "build")
        
        recreated = Task.from_dict(data)
        self.assertEqual(recreated.id, task.id)
        self.assertEqual(recreated.queue, "jobs")
        self.assertEqual(recreated.payload["cmd"], "build")

    def test_event_serialization(self):
        event = Event(topic="agent.jules.started", payload={"session": "123"}, producer="jules")
        data = event.to_dict()
        self.assertEqual(data["topic"], "agent.jules.started")
        self.assertEqual(data["producer"], "jules")
        
        recreated = Event.from_dict(data)
        self.assertEqual(recreated.id, event.id)
        self.assertEqual(recreated.payload["session"], "123")

    def test_dead_letter_serialization(self):
        dle = DeadLetterEntry(task_id="t-1", queue="retry", payload={"x": 1}, reason="timeout")
        data = dle.to_dict()
        self.assertEqual(data["task_id"], "t-1")
        self.assertEqual(data["reason"], "timeout")
        
        recreated = DeadLetterEntry.from_dict(data)
        self.assertEqual(recreated.id, dle.id)
        self.assertEqual(recreated.payload["x"], 1)

if __name__ == "__main__":
    unittest.main()
