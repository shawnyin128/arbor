@AGENTS.md

## Claude Code

This repository is the Arbor plugin, and it uses Arbor. Volatile state arrives
through Arbor's own SessionStart hook; `AGENTS.md` above is the durable guide.

- Run the suite with `python -m pytest` from the repository root.
- `.arbor/memory.md` and `.arbor/ideas.md` are agent-written. `.arbor/session.json`
  is written by hooks; do not edit it by hand.
- When changing the plugin, remember that the installed copy is what runs. Verify
  against an installed cache, not just the source tree.
