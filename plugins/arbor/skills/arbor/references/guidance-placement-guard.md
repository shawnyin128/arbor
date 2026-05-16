# Guidance Placement Guard

Arbor improves the agent's working conditions; it does not replace the agent's
native judgment. Use this guard when deciding where persistent guidance,
workflow evidence, and task context should live.

## Placement Map

| Guidance or evidence | Belongs in | Reason |
| --- | --- | --- |
| Stable project goal, durable constraints, startup protocol, and project-map pointers | `AGENTS.md` | These are needed at startup and across sessions. |
| Claude Code runtime bridge | `CLAUDE.md` | Claude Code reads it natively; it should only point at canonical Arbor state. |
| Short-term unresolved work before commit or publish | `.arbor/memory.md` | This is the resume pointer for current in-flight work. |
| Repeatable task method, workflow contract, domain-specific behavior, and examples that load only when relevant | Arbor skills and skill references | Skills provide progressive disclosure without bloating startup context. |
| Brainstorm, developer, evaluator, convergence, and release evidence | `docs/review/` | Review docs are append-only evidence, not startup instructions. |
| Completed implementation and release facts | Git history plus release/checkpoint evidence | Committed history is the durable record after work is resolved. |
| Frequently changing or external live context | MCP tools, CLI tools, URLs, or task-specific docs | Fetch volatile context when needed instead of copying it into startup guidance. |

## Add To Startup Guidance Only When

- The guidance applies across many tasks in the repository.
- Removing it would likely cause repeated mistakes across fresh or resumed sessions.
- It is short enough to remain readable during startup.
- It points to deeper docs or skills instead of duplicating them.

## Move Out Of Startup Guidance When

- The guidance is a tutorial, example catalog, file-by-file description, or long explanation.
- The guidance is task-specific, domain-specific, or only relevant after a route has been selected.
- The information changes frequently or should be fetched from an external source.
- The content is current-session progress or unresolved implementation detail.

## Non-Goals

This guard must not:

- impose fixed reading limits, file counts, line counts, or context budgets;
- require plan-first behavior for direct or simple tasks;
- require subagents, worktrees, fan-out execution, or automations;
- prescribe implementation strategy, code style, or test type beyond the selected skill's actual contract;
- turn hooks into workflow decision makers.

The agent should continue reading whatever files, diffs, docs, logs, or external
sources the task requires. The guard only decides the durable home for guidance
after the agent has identified what kind of context it is.
