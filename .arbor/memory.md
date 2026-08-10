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

- Four obsolete tags still exist on the remote and cannot be removed from this
  session: the permission classifier blocks `git push origin --delete` on tags.
  Deleting them locally does nothing, because `git fetch` restores them from the
  remote. `v2.1.0` is the one that matters, since it sits inside the 2.1 line but
  points at the superseded hookless architecture. Run this to finish:
  `git push origin --delete v2.1.0 v2.0.3 v2.0.4 v2.0.5`
  Every one of those commits stays reachable through the supersede merge
  `27b99c8`, so the tags can be recreated exactly:
  v2.0.3 49ddc35, v2.0.4 277e703, v2.0.5 0cdcb2c, v2.1.0 fee8d5e.
- Hooks have not yet been observed firing from a real session. The receipts in a
  temporary project confirm all three run from the installed cache, but this
  repository's own `session.json` will stay absent until a new session starts.
  Run `arbor doctor` then to confirm the three hook rows turn `ok`.
- No CI. `python -m pytest` and `python tests/mutations.py` are manual, so a
  regression can reach a release unnoticed. A GitHub Actions workflow running both
  is the obvious next step.
