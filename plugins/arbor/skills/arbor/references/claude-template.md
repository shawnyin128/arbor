# Claude Guide

This project uses Arbor for shared project context. Claude Code reads this file
natively; the canonical Arbor state lives in the files this bridge points to.

- `AGENTS.md` is the canonical Arbor project guide and map. Read it first.
- `.arbor/memory.md` holds short-term, undecided observations. Read it after
  `AGENTS.md` and before deeper code or doc reads.

Follow the Arbor startup order:

1. Read `AGENTS.md`.
2. Review recent `git log` history as needed.
3. Read `.arbor/memory.md`.
4. Check `git status`.
5. Read deeper docs, diffs, or source files when the task calls for them.

Keep this file as a short bridge: do not duplicate long-term project knowledge
here. Durable goals, constraints, and project-map pointers belong in
`AGENTS.md`. Short-term unresolved state belongs in `.arbor/memory.md`.
Task-specific workflows, examples, and longer design notes belong in Arbor
skills or referenced project docs, not in this bridge.
