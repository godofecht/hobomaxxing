"""Command line entry point for the Hobomaxxing agent-facing queue."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import (
    build_report, execute_job, load_config, make_prompt, select_task,
    state_read, write_report
)
from .interactive import complete, make_session, pending_tasks, serve


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="hobo", description="Inventory, rank, hand off and safely run known tasks"
    )
    parser.add_argument(
        "--config", default="hobomax.json",
        help="Explicit local config. Copy config.example.json and edit."
    )
    parser.add_argument(
        "--state", default=".hobomaxxing/state.json",
        help="Local execution ledger (do not commit)"
    )
    parser.add_argument(
        "--offline", action="store_true",
        help="Skip GitHub API reads"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("scan", help="Machine-readable JSON inventory and ranked task queue")
    plan = sub.add_parser("plan", help="Print highest-priority actionable tasks")
    plan.add_argument("--top", type=int, default=15)
    handoff = sub.add_parser("prompt", help="Print a human-initiated AI agent task packet")
    handoff.add_argument("--task", default=None, help="Task ID; defaults to top ranked")
    session = sub.add_parser("session", help="Create a multi-task, human-supervised agent handoff")
    session.add_argument("--top", type=int, default=5)
    dashboard = sub.add_parser("dashboard", help="Start the local interactive workbench")
    dashboard.add_argument("--port", type=int, default=8765)
    dashboard.add_argument("--no-browser", action="store_true")
    finish = sub.add_parser("complete", help="Record verified task completion locally")
    finish.add_argument("task_id")
    finish.add_argument("--evidence", required=True, help="Tests, PR or other validation")
    run = sub.add_parser("run", help="Execute a specifically configured, due job")
    run.add_argument("job_id")
    run.add_argument("--approve", action="store_true", help="Explicit human authorization")
    run.add_argument("--automatic", action="store_true", help="Only for pre-approved jobs")
    run.add_argument("--force", action="store_true", help="Reserved; not supported")
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        state_path = Path(args.state).expanduser()
        if args.command == "run":
            if args.force:
                raise ValueError("--force is not supported: respect the job interval")
            result = execute_job(
                config, state_path, args.job_id, args.approve, args.automatic
            )
            print(json.dumps(result, indent=2))
            return 1 if result["status"] == "failed" else 0
        if args.command == "dashboard":
            serve(args.config, state_path, args.offline, args.port, not args.no_browser)
            return 0
        state = state_read(state_path)
        report = build_report(config, state, github=not args.offline)
        pending = pending_tasks(report, state)
        if args.command == "complete":
            print(json.dumps(complete(state_path, report, args.task_id, args.evidence), indent=2))
            return 0
        if args.command == "scan":
            print(json.dumps(report, indent=2))
        elif args.command == "plan":
            print(
                str(len(report["inventory"]["local"])) + " local repositories; " +
                str(len(report["inventory"]["github"])) + " GitHub repositories; " +
                str(len(pending)) + " pending tasks"
            )
            for item in pending[:max(0, args.top)]:
                print(
                    str(item["priority"]).rjust(3) + "  " + item["id"] +
                    "  [" + item["kind"] + "] " + item["title"]
                )
            for error in report["errors"]:
                print("warning: " + error, file=sys.stderr)
        elif args.command == "prompt":
            print(make_prompt(select_task({"tasks": pending}, args.task)))
        elif args.command == "session":
            print(make_session({"tasks": pending}, state, args.top))
        return 0
    except (ValueError, OSError, RuntimeError) as exc:
        print("hobo: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
