# Agent Guide

## Project Goal

Arbor is a Claude Code plugin that restores the volatile half of project context
at session start: git position, the task list that was in flight, unresolved
decisions, and parked ideas. Claude Code already carries the durable half through
a `CLAUDE.md` that imports `AGENTS.md`, so Arbor deliberately does not inject the
project guide.

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
- The injected packet must stay under its budget. Host hook output above roughly
  10,000 characters is discarded silently, so over-budget output loses everything.
- Machine state belongs in `.arbor/session.json` and is written only by hooks;
  agent-written notes belong in `.arbor/memory.md` and `.arbor/ideas.md`.
- `arbor doctor` reports and never repairs. Nothing rewrites `AGENTS.md`.
- `plugins/arbor/hooks/arbor-hook.cmd` is parsed by both `cmd.exe` and POSIX
  shells and must stay LF-only; a stray CR makes it silently no-op.
- Behavior changes need a pytest contract, and the contract must be shown to fail
  when the implementation is broken.

## Project Map

- `README.md`: public overview, install, hook table, and design rationale.
- `plugins/`: the published plugin. Holds the Claude manifest, plugin-level hook
  registration and launcher under `hooks/`, and the single `arbor` skill whose
  `scripts/arbor_core/` package is the one implementation behind both the hooks
  and the CLI.
- `tests/`: pytest suite. Fixtures build real temporary git repositories; native
  paths only, because a Git Bash POSIX path silently defeats a Windows hook.
- `docs/`: local design notes and specs, not published.
