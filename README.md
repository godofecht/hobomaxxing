# Hobomaxxing

An **agent-facing, local-first backlog** for your whole *authorized* development setup.
It discovers Git workspaces, samples TODOs, reads GitHub issues, PRs and failed
workflow runs, ranks obvious work deterministically, and prepares scoped tasks
for a human or a coding agent. You can also run explicitly configured local jobs
and trigger existing GitHub Actions workflows using official APIs.

No paid API key, database, hosted server, or Python dependency is required.
No AI API is called implicitly. A configuration file controls exactly which
local roots, GitHub repositories and jobs are in scope.

## Start

Requires Python 3.10+, Git, and (for remote scans) access to the GitHub API.

```sh
git clone https://github.com/godofecht/hobomaxxing.git
cd hobomaxxing
cp config.example.json hobomax.json
# Edit hobomax.json to point at your own actual local directories and repositories.
python3 -m hobomax --config hobomax.json plan
python3 -m hobomax --config hobomax.json scan > .hobomaxxing/inventory.json
python3 -m hobomax --config hobomax.json prompt
python3 -m hobomax --config hobomax.json prompt --task TASK_ID
```

**Note:** the output redirection target above needs a directory. First run
`mkdir -p .hobomaxxing` or redirect to a file in an existing directory.

Use `python3 -m hobomax --config hobomax.json --offline plan` to scan
local Git projects without making GitHub API requests.

For private GitHub repositories, set `GH_TOKEN` or `GITHUB_TOKEN` locally
with read access. Public GitHub scans usually work without a token, subject
to unauthenticated rate limits. Do not put credentials in config.

The `plan` is deliberately deterministic, not an LLM's self-assessed confidence.
Failed CI is typically first, then bugs, reviews, local changes and TODOs.
Impact, urgency, evidence confidence, estimated effort and risk are visible
in the JSON report. It is a heuristic, not a claim that the task is correct.

## Interactive desktop workbench

This is primarily for **a human actively using the computer**, not a headless
agent or ad avoidance system. The human keeps Freebuff's real application and
its advertisements visible, starts each session themselves and remains present.
Freebuff's own agent can then work autonomously *inside that session* through
its intended features. Hobomaxxing never scripts Freebuff, opens unofficial
model endpoints, or suppresses ads. Keeping ads visible does not by itself
make an external bot permitted under Freebuff's terms.

After configuring a private `hobomax.json` with authorized local Git roots
and GitHub repositories, run:

~~~sh
python3 -m hobomax --config hobomax.json dashboard
~~~

The browser opens a local-only dashboard at `http://127.0.0.1:8765/`.
Review ranked tasks, prepare a one-task or five-task prompt, copy it, and
start your official Freebuff session. The page is bound to localhost, has
no cloud backend, and never sends data to a model provider itself.

For terminal workflows:

~~~sh
python3 -m hobomax --config hobomax.json session --top 5
python3 -m hobomax --config hobomax.json complete TASK_ID --evidence "verified tests passed"
~~~

Completed tasks disappear from the pending plan and dashboard. Their evidence
and timestamps remain local in `.hobomaxxing/state.json`; `scan` still includes
the underlying raw discoveries. Revisit or clear state manually if a completed
issue genuinely recurs. This implementation does not continuously monitor
active presence and cannot establish compliance on the user's behalf.

## Agent workflow

Point an assistant at this repository's [AGENTS.md](AGENTS.md). A human configures
the scope, runs `plan`, selects the highest-value appropriate task, and hands
the output of `prompt` to the coding agent. The agent verifies the task,
makes a minimal change, runs checks and presents a reviewable diff. The
prompt does not include issue bodies or source lines.

### Freebuff

[Freebuff](https://freebuff.com/) provides an official human-driven CLI,
desktop and web coding agent. It is a good *destination* for the task packet,
not an unattended worker. Copy `hobo prompt` output into a **session you
personally start and supervise**. Its [terms](https://freebuff.com/terms-of-service)
(effective 2026-11-12) disallow bots/scripts/autonomous agents operating
the product, unofficial inference endpoints and automation of account
limits absent written permission. Hobomaxxing intentionally does not
launch, script or relay Freebuff sessions.

### Automated jobs

Only jobs declared in the local `hobomax.json` can run. Jobs are **disabled by
default** in the example. For a command job, configure its exact `argv`,
a `cwd` inside an allowed root, its timeout and a minimum interval.
Nothing from an issue or TODO is interpolated into a command. Shell
wrappers and `sudo` are rejected. Subprocesses do not inherit tokens
or arbitrary environment variables. Scripts inside your explicitly
configured argv remain your responsibility: use trusted programs.

```sh
python3 -m hobomax --config hobomax.json run repo-tests
python3 -m hobomax --config hobomax.json run repo-tests --approve
```

The first is a dry run. The second really runs the job if enabled and due.
For a pre-approved scheduled job, set `approval` to `automatic` in your
private config and invoke `run JOB_ID --automatic` from your own scheduler.
Job success is recorded in `.hobomaxxing/state.json` to enforce cooldowns.
A command can change files or consume local resources: review it first.

The supported `github_dispatch` job calls GitHub's documented
`workflow_dispatch` API for an existing, explicitly allowed workflow.
It requires a GitHub token with appropriate Actions permission. GitHub
Actions can consume billed minutes depending on your plan, repository
and runner. **This system does not assume all GitHub Actions runs are free**;
set usage controls and enable dispatch only if you accept the quota risk.

## What it can and cannot do

| Capability | Current state |
| --- | --- |
| Discover Git repos under explicitly chosen directories | Implemented |
| Count local pending changes and find tracked TODO/FIXME locations | Implemented |
| Read open GitHub issues, PRs and latest CI failures | Implemented; first page/sample only |
| Rank and output a stable JSON task queue | Implemented |
| Create bounded one-task or multi-task packets for human-started coding sessions | Implemented |
| Local browser dashboard with completion evidence ledger | Implemented, human supervised |
| Run explicitly allowlisted commands and GitHub workflow dispatches | Implemented, opt-in |
| Execute Freebuff unattended or bypass quotas | Not supported |
| Discover every personal app/account automatically | Not implemented or authorized |
| Configure other providers, cloud credits, or paid services | Future adapters, not claimed |

## Privacy and limits

The tool inspects only configured roots and repositories, does not scan
a whole filesystem by default, skips common dependency and secret paths,
and emits file locations instead of copying source lines. The inventory
can still contain sensitive project paths and repository titles, so keep
it local. A public GitHub Actions run cannot scan your computer.

The GitHub API inventory samples up to the first 100 open issues and
PRs per repository, ranks up to 40 of each, and inspects recent workflow
runs. HTTP errors become visible scan warnings. Tasks are opportunities
for verification, not instructions to delete or merge anything.
The tool makes no claims about being a full billing or quota manager.

## Development

```sh
python3 -m unittest discover -s tests -v
python3 -m hobomax --config config.example.json --offline plan
```

Standard library only. Python 3.10+.
