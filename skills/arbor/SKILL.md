---
name: arbor
description: Initialize and maintain project-local Codex memory for daily development under the Arbor workflow. Use when starting or resuming work in a repo, creating `.codex/memory.md`, creating or updating `AGENTS.md`, loading startup context from project docs, formatted git log, session memory, and git status, refreshing stale pre-triage observations, or detecting durable project goal, constraint, or project-map changes.
---

# Arbor

## Core Rule

Fix the workflow order, not the agent's reading depth. Keep Arbor outcome-first: recover the right project context, maintain short-term memory, and update durable project guidance when needed. Do not impose commit counts, byte limits, file limits, documentation depth, or summary-size limits as part of this skill. Use scripts as helpers; continue reading whatever files, diffs, logs, or docs the task requires.

## Startup Workflow

When initializing, resuming, or orienting in a project:

1. Ensure `AGENTS.md` and `.codex/memory.md` exist. Use `scripts/init_project_memory.py --root <project-root>` when useful.
2. Register project-local Arbor hook intents when the project should keep the workflow active. Use `scripts/register_project_hooks.py --root <project-root>` when useful. This writes `.codex/hooks.json` in the project and preserves unrelated hook entries.
3. Load startup context in this order:
   - `AGENTS.md`
   - formatted `git log`
   - `.codex/memory.md`
   - `git status`
4. Use `scripts/collect_project_context.py --root <project-root>` when a deterministic ordered context packet is useful. The script does not decide how much context is enough.
5. Read additional docs, diffs, source files, or logs when the project map, task risk, or user request calls for them.

Collector sections include `Status`, `Source`, optional `Detail`, and raw body. Treat `missing`, `path-conflict`, `read-error`, `git-error`, and `empty` as fallback diagnostics, not blockers for reading later sections.

## Session Memory

Use `.codex/memory.md` for short-term, pre-triage observations only:

- Undecided bugs, hypotheses, concerns, risks, and notes.
- Items not already resolved by git history.
- Items not already captured in `AGENTS.md`, project docs, review docs, task trackers, or committed history.

Before adding an item, triage whether it is already resolved or captured elsewhere. Remove items once they are resolved, committed, or moved to their durable home. Keep the file under 30 lines when practical.

## Long-Term Memory

Use `AGENTS.md` for durable project context:

- `Project Goal`
- `Project Constraints`
- `Project Map`

Update `AGENTS.md` when the project goal, durable constraints, or project map changes. Keep only undecided transient observations in `.codex/memory.md`.

## Project Hooks

Arbor hook registration is project-level. `.codex/hooks.json` is the visible project contract for three hook intents:

- `arbor.session_startup_context`: load startup context in the required order.
- `arbor.in_session_memory_hygiene`: emit memory hygiene context so the agent can refresh `.codex/memory.md` when uncommitted work or conversation state makes it stale.
- `arbor.goal_constraint_drift`: emit AGENTS drift context so the agent can update only durable `AGENTS.md` goal, constraint, or map sections when needed.

Do not store Arbor hook state in user-global memory. Re-register hooks when needed; registration is idempotent and should preserve unrelated project hooks.

## Resources

- `references/memory-template.md`: template for `.codex/memory.md`
- `references/agents-template.md`: template for `AGENTS.md`
- `references/project-hooks-template.md`: project hook contract
- `scripts/init_project_memory.py`: create missing project memory files without overwriting existing files
- `scripts/collect_project_context.py`: collect startup context in the required order
- `scripts/run_session_startup_hook.py`: execute Hook 1 and forward optional agent-selected git log arguments
- `scripts/run_memory_hygiene_hook.py`: execute Hook 2 and forward optional agent-selected diff arguments
- `scripts/run_agents_guide_drift_hook.py`: execute Hook 3 and forward optional agent-selected project doc paths
- `scripts/register_project_hooks.py`: create or update `.codex/hooks.json` with Arbor hook intents
