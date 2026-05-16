# Agent Guide

## Startup Protocol

At the start of a fresh or resumed session, and before answering project overview questions such as "what does this project do?", load Arbor startup context first:

1. Read this `AGENTS.md`.
2. Read recent formatted git history.
3. Read `.arbor/memory.md`.
4. Read `git status --short`.

If the Arbor plugin is available, prefer its startup context helper or `arbor:arbor` skill. If no helper path is available, perform the four reads manually before answering. Do not treat `.codex/hooks.json` as proof that startup context has already been injected.

## Project Goal

Describe the stable project objective here.

## Project Constraints

- Record durable engineering, workflow, validation, style, and collaboration constraints here.
- Keep transient current-session progress in `.arbor/memory.md`.
- Keep this file concise. Put task-specific workflows, examples, and long design notes in skills or referenced project docs.

## Project Map

Use this as the entrypoint to durable project context, not as the whole long-term memory store.

- Document major directories, modules, commands, architecture boundaries, and where to start reading.
- Add pointers to deeper design, review, and domain docs as the project grows.
- Link to volatile external context instead of copying it here.
- When durable top-level entrypoints or stable mapped subpaths are added, removed, or renamed, refresh this section before handoff or release; keep transient current-session progress in `.arbor/memory.md` instead.
