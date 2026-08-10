@AGENTS.md

## Arbor

`AGENTS.md` above is the durable project guide, imported so it loads every
session and survives compaction. Volatile state is injected separately by
Arbor's SessionStart hook.

- `.arbor/memory.md` holds what is still unresolved. Update it when a decision
  is left open, and remove entries once they are settled or committed.
- `.arbor/ideas.md` holds ideas raised in passing. Append one line rather than
  acting on them mid-task.
- `.arbor/session.json` is written by hooks. Do not edit it by hand.

Keep this file short. Durable knowledge belongs in `AGENTS.md`.
