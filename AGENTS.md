# Agent Guide

## Project Goal

Arbor is a Claude Code plugin that restores the volatile half of project context
at session start: git position, the task list that was in flight, unresolved
decisions, and parked ideas. Claude Code already carries the durable half through
a `CLAUDE.md` that imports `AGENTS.md`, so Arbor deliberately does not inject the
project guide.

## Commands

```bash
python -m pytest                       # the suite
python -m pytest tests/test_packet.py  # one file
python tests/mutations.py              # break the implementation 25 ways
```

- `pytest` needs an explicit `--basetemp` outside this repository on a machine
  whose default temporary directory is not writable; inside it, git parent
  discovery and file locks break the fixtures.
- `tests/ab_harness.py` is not collected by pytest. It drives a live `claude` CLI
  and spends real tokens, so run it deliberately: `--experiment packet` asks
  whether the injected packet beats the host's own context, `--experiment guide`
  whether a Project Map earns its characters.

## Project Constraints

- Claude Code only. Codex support, project-level hook registration, and installed
  cache discovery were removed in 2.1.0; do not reintroduce them.
- Hooks ship at plugin level in `plugins/arbor/hooks/hooks.json` and resolve
  paths through `${CLAUDE_PLUGIN_ROOT}`. Nothing writes into a project's
  `.claude/settings.json`.
- Plugin hooks fire in every project the user opens, so absence of a `.arbor/`
  directory must make every hook a silent no-op with exit code 0.
- Injected context must carry no wall-clock value; a clock that ticks while the
  project sits still invalidates the prompt prefix cache for nothing.
- Inject nothing the host already injects. It appends its own git block carrying
  the branch, the full `git status --short`, and the five most recent commits, so
  a second copy costs tokens, and a copy truncated differently from the host's can
  provoke the agent into re-checking a fact it already had.
- Sections are emitted highest value first, and the packet is not trimmed to a
  budget. Above roughly 10,000 characters the host keeps the head, writes the
  whole output to a file, and says so in context, so nothing is lost and
  front-loading is what protects what matters.
- Machine state belongs in `.arbor/session.json` and is written only by hooks;
  agent-written notes belong in `.arbor/memory.md` and `.arbor/ideas.md`.
- `arbor doctor` reports and never repairs. Nothing rewrites `AGENTS.md`.
- `plugins/arbor/hooks/arbor-hook.cmd` is parsed by both `cmd.exe` and POSIX
  shells and must stay LF-only; a stray CR makes it silently no-op.
- Behavior changes need a pytest contract, and the contract must be shown to fail
  when the implementation is broken.

## Project Map

Entries state something the tree cannot show. A path list is not one: an agent
finds files with glob and grep, and a repository overview measurably does not
reduce the steps it takes to reach the files it must change.

- `plugins/arbor/skills/arbor/scripts/arbor_core/` is the one implementation
  behind both the hooks and the CLI. Behavior changes go here, never into a
  second copy beside the launcher.
- New hooks register in `plugins/arbor/hooks/hooks.json` at plugin level. Nothing
  ever writes into a project's `.claude/settings.json`.
- Test fixtures build real temporary git repositories and must use native paths
  only, because a Git Bash POSIX path silently defeats a Windows hook.
- `tests/ab_harness.py` spends real tokens against a live `claude` CLI and is not
  collected by pytest. Run it when a claim about injected context needs evidence.
- `docs/` holds local design notes and is not published.
