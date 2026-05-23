# Agent Guide

## Startup Protocol

At the start of a fresh or resumed session, and before answering project overview questions such as "what does this project do?", load Arbor startup context first:

1. Read this `AGENTS.md`.
2. Read recent formatted git history.
3. Read `.arbor/memory.md`.
4. Read `git status --short`.

If the Arbor plugin is available, prefer its startup context helper or `arbor:arbor` skill. If no helper path is available, perform the four reads manually before answering. Do not treat `.codex/hooks.json` as proof that startup context has already been injected.

## Workflow Entrypoint Protocol

Before handling a user request that looks like managed engineering work, choose
an explicit Arbor public entrypoint instead of relying on a hidden router. Use
`brainstorm` for feature ideas, ordinary bug reports without review context,
broken behavior reports that need scoping, broad planning, workflow documents,
tests/evaluation planning, and any request that needs acceptance criteria or a
test plan before edits.

Use `feedback` for user bug reports, regressions, reviewer comments, failed
checks, or corrections to prior Arbor work when the next public owner is
unclear. Feedback should decide only between `brainstorm`, `converge`,
needs-evidence, or a direct response; it should not trigger from keywords alone
or sit in front of another named public entrypoint that already fits.

Use `converge` when the current feature already has Arbor review context or the
user asks to continue, repair, verify, or close an existing managed quality
loop. `develop` and `evaluate` are internal stages owned by `converge`, not
normal public user entrypoints.

Keep simple one-off explanations, prose-only writing, and standalone conceptual
questions direct unless they affect future development, testing, experiments,
workflow state, or agent behavior.

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
