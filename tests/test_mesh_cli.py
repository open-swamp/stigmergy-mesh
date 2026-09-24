import unittest
import os
import tempfile
import json
from mesh.cli.mesh_cli import build_parser, handle_command

class TestMeshCLI(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "cli_test.db")
        self.parser = build_parser()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_parser_push_args(self):
        args = self.parser.parse_args(["push", "--queue", "urgent", "--data", '{"job": "test"}', "--priority", "10"])
        self.assertEqual(args.command, "push")
        self.assertEqual(args.queue, "urgent")
        self.assertEqual(args.priority, 10)
        self.assertEqual(args.data, '{"job": "test"}')

    def test_parser_pop_args(self):
        args = self.parser.parse_args(["pop", "--queue", "urgent", "--lease", "45"])
        self.assertEqual(args.command, "pop")
        self.assertEqual(args.queue, "urgent")
        self.assertEqual(args.lease, 45)

    def test_cli_push_and_pop_flow(self):
        # Push via CLI handler
        args_push = self.parser.parse_args(["--db", self.db_path, "push", "--queue", "cli_queue", "--data", '{"msg": "hi"}'])
        push_output = handle_command(args_push)
        self.assertIn("task_id", push_output)

        # Pop via CLI handler
        args_pop = self.parser.parse_args(["--db", self.db_path, "pop", "--queue", "cli_queue"])
        pop_output = handle_command(args_pop)
        self.assertIsNotNone(pop_output)
        self.assertEqual(pop_output["payload"]["msg"], "hi")

if __name__ == "__main__":
    unittest.main()
