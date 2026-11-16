import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hobomax.core import (
    build_report, discover_repos, due, execute_job, github_scan,
    load_config, make_prompt, score, select_task, task, validate_command,
)


class HobomaxTests(unittest.TestCase):
    def test_score_prefers_verified_urgent_work(self):
        self.assertGreater(score(5, 5, 5, 2, 1), score(2, 2, 3, 2, 2))
        self.assertEqual(score(5, 5, 5, 2, 1), 91)
        with self.assertRaises(ValueError):
            score(10, 2, 3, 2, 2)

    def test_identifiers_are_stable(self):
        a = task("todo", "/code", "a:1", "title", 3, 2, 3, 2, 2)
        b = task("todo", "/code", "a:1", "new title", 3, 2, 3, 2, 2)
        self.assertEqual(a["id"], b["id"])

    def test_config_rejects_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps({
                "version": 1, "jobs": [{"id": "same"}, {"id": "same"}]
            }))
            with self.assertRaises(ValueError):
                load_config(path)

    def test_discovers_only_explicit_git_roots(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "one" / ".git").mkdir(parents=True)
            (root / "ignored" / "node_modules" / "two" / ".git").mkdir(parents=True)
            repos, errors = discover_repos([directory])
            self.assertEqual([path.name for path in repos], ["one"])
            self.assertFalse(errors)

    def test_prompt_marks_external_text_untrusted(self):
        item = task("github-issue", "example/repo", "3", "Fix bug",
                    3, 3, 3, 3, 2)
        prompt = make_prompt(item)
        self.assertIn("untrusted data", prompt)
        self.assertIn("human must initiate", prompt)

    def test_github_prioritizes_failure_and_skips_pr_issues(self):
        def api(path, token=None):
            if "/issues?" in path:
                return [
                    {"number": 1, "title": "bug", "labels": [{"name": "bug"}]},
                    {"number": 2, "pull_request": {}, "title": "not an issue"}
                ]
            if "/pulls?" in path:
                return [{"number": 2, "title": "PR"}]
            return {"workflow_runs": [
                {"workflow_id": 4, "conclusion": "failure", "name": "CI"}
            ]}
        with patch("hobomax.core.github_request", side_effect=api):
            inventory, tasks, errors = github_scan(["example/repo"])
        self.assertFalse(errors)
        self.assertEqual(inventory[0]["open_issues_sampled"], 1)
        self.assertEqual([item["kind"] for item in tasks].count("github-issue"), 1)
        self.assertEqual([item["kind"] for item in tasks].count("github-ci"), 1)

    def test_command_requires_allowed_directory_and_no_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                validate_command({"argv": ["sh", "-c", "echo hi"],
                                  "cwd": directory}, [directory])
            with self.assertRaises(ValueError):
                validate_command({"argv": ["python3"], "cwd": "/"},
                                 [directory])
            argv, cwd = validate_command(
                {"argv": ["python3", "--version"], "cwd": directory}, [directory]
            )
            self.assertEqual(argv[0], "python3")
            self.assertEqual(cwd, Path(directory))

    def test_job_dry_run_and_success_cooldown(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state.json"
            config = {"version": 1, "local_roots": [directory], "jobs": [{
                "id": "test", "enabled": True, "type": "command",
                "cwd": directory, "argv": ["python3", "-c", "print('ok')"],
                "min_interval_hours": 24
            }]}
            self.assertEqual(execute_job(config, state, "test")["status"], "dry-run")
            self.assertFalse(state.exists())
            result = execute_job(config, state, "test", approve=True)
            self.assertEqual(result["status"], "success")
            self.assertIn("ok", result["stdout"])
            self.assertEqual(execute_job(config, state, "test", approve=True)["status"], "not-due")

    def test_report_is_stably_sorted(self):
        with patch("hobomax.core.local_scan", return_value=([], [], [])):
            report = build_report({
                "local_roots": [], "github_repos": [], "jobs": [
                    {"id": "z", "enabled": True},
                    {"id": "a", "enabled": True}
                ]
            }, github=False)
        self.assertEqual(len(report["tasks"]), 2)
        self.assertEqual([item["job_id"] for item in report["tasks"]], ["a", "z"])
        self.assertEqual(select_task(report, None)["job_id"], "a")


if __name__ == "__main__":
    unittest.main()
