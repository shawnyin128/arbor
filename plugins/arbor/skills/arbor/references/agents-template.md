# Agent Guide

## Startup Protocol

At the start of a fresh or resumed session, and before answering project
overview questions such as "what does this project do?", load Arbor startup
context first:

1. Read this `AGENTS.md`.
2. Read recent formatted git history.
3. Read `.arbor/memory.md`.
4. Read `git status --short`.

If the Arbor plugin is available, prefer its startup context helper or
`arbor:arbor` skill. If no helper path is available, perform the four reads
manually before answering. Do not treat `.codex/hooks.json` as proof that
startup context has already been injected.

## Project Goal

Arbor has not recorded a stable project goal for this repository yet. Inspect
the repository itself before answering project-purpose questions, and replace
this section once the durable goal is known.

## Project Constraints

- Keep this file concise; record only durable repository-wide guidance that is
  useful at startup.
- Keep transient current-session progress in `.arbor/memory.md`.
- Put task-specific procedures, examples, and long design notes in skills or
  referenced project docs.
- Link to volatile external context instead of copying it here.

## Project Map

Arbor has not recorded a durable project map for this repository yet. Inspect
the repository directly before answering project-structure questions, and keep
this section as the entrypoint to durable project context once the map is known.

- Add major directories, modules, commands, architecture boundaries, and where
  to start reading.
- Add pointers to deeper design and domain docs as the project grows.
- When durable top-level entrypoints or stable mapped subpaths are added,
  removed, or renamed, refresh this section before handoff; keep transient
  current-session progress in `.arbor/memory.md` instead.
