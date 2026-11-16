import tempfile
import unittest
from pathlib import Path

from hobomax.interactive import complete, make_session, pending_tasks


class InteractiveTests(unittest.TestCase):
    def setUp(self):
        self.report = {
            "tasks": [
                {
                    "id": "first", "title": "Fix CI", "kind": "github-ci",
                    "priority": 91, "resource": "example/repo", "reference": "88"
                },
                {
                    "id": "second", "title": "Review PR", "kind": "github-pr",
                    "priority": 73, "resource": "example/repo", "reference": "3"
                }
            ]
        }

    def test_session_is_bounded_and_untrusted(self):
        prompt = make_session(self.report, {}, 1)
        self.assertIn('"id": "first"', prompt)
        self.assertNotIn('"id": "second"', prompt)
        self.assertIn("untrusted input", prompt)
        self.assertIn("actively present", prompt)

    def test_completion_filters_queue(self):
        with tempfile.TemporaryDirectory() as path:
            state_path = Path(path) / "state.json"
            with self.assertRaises(ValueError):
                complete(state_path, self.report, "first", "")
            with self.assertRaises(ValueError):
                complete(state_path, self.report, "bogus", "verified")
            self.assertEqual(
                complete(state_path, self.report, "first", "Tests passed")["status"],
                "complete"
            )
            from hobomax.core import state_read
            state = state_read(state_path)
            self.assertEqual(
                [item["id"] for item in pending_tasks(self.report, state)],
                ["second"]
            )
            self.assertNotIn('"id": "first"', make_session(self.report, state, 5))

    def test_cap_at_ten(self):
        self.assertEqual(
            make_session(self.report, {}, 50).count('"id":'), 2
        )


if __name__ == "__main__":
    unittest.main()
