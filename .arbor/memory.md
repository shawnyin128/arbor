# Session Memory

<!--
What is still unresolved. This file answers the question a hook cannot: not what
changed, but why the work stopped and what is still open.

Do not record what the repository already records — code structure, past fixes,
git history, or anything already in AGENTS.md — and do not record what only
mattered to one conversation. If asked to remember one of those, work out what
was non-obvious about it and record that instead.

Update an entry rather than adding a near-duplicate. Delete an entry once it is
committed, documented, or decided. A short file gets read; a long one does not.

Each entry should say what is unresolved and what the next session should do
first. Naming a file or symbol makes a claim about how the code looked when the
entry was written, so a later session must confirm it still exists.
-->

## Unresolved

- Two decisions left open on the remote. The `v2.1.0` tag still points at
  `fee8d5e`, the superseded hookless-runtime work, and `v2.0.3` through `v2.0.5`
  tag Codex-line releases; all four are reachable from master through the
  supersede merge `27b99c8`, so nothing is lost if they stay. Also still present:
  the `codex/verifiable-hookless-runtime` branch and its worktree at
  `.worktrees/hookless-stable-triggers`, plus the local `2.0.5` and stale `2.1.0`
  plugin cache directories.
- Hooks have not yet been observed firing from a real session. The receipts in a
  temporary project confirm all three run from the installed cache, but this
  repository's own `session.json` will stay absent until a new session starts.
  Run `arbor doctor` then to confirm the three hook rows turn `ok`.
- No CI. `python -m pytest` and `python tests/mutations.py` are manual, so a
  regression can reach a release unnoticed. A GitHub Actions workflow running both
  is the obvious next step.
