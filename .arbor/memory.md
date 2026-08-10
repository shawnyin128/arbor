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

- 2.1.1 is committed on master and installed locally, but nothing is pushed. The
  marketplace clone at `~/.claude/plugins/marketplaces/arbor` was reset to a local
  commit, so a plugin auto-update will fetch origin and silently revert the local
  install to 2.0.x. Push master before relying on it on another machine.
- The remote already has a `v2.1.0` tag pointing at `fee8d5e`, the abandoned
  hookless-runtime experiment on `codex/verifiable-hookless-runtime`. That is why
  this release is 2.1.1. Decide whether to delete or move that tag, and whether to
  delete the superseded branch and its worktree at
  `.worktrees/hookless-stable-triggers`; `v2.0.3` through `v2.0.5` are also tagged
  on the remote but absent from master.
- Hooks were verified by invoking the installed cache with the exact command
  strings from its `hooks.json`, and the receipts in `session.json` confirm all
  three ran. They have not yet been observed firing from a real new session, which
  needs `/reload-plugins` or a fresh session to confirm.
