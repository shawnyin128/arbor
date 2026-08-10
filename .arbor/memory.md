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

- Task capture was broken until 2.1.9 and needs re-verifying in a real session.
  This host has no TodoWrite tool, so the old matcher never fired; 2.1.9 matches
  TaskCreate and TaskUpdate and reads the host's task files instead. The installed
  copy captures correctly when driven by hand, but a real session has only ever
  been observed firing SessionStart. To finish: start a session, have it create a
  three-item task list, end it, and expect `arbor doctor` to show all three hook
  rows `ok` with the task-capture row naming TaskCreate or TaskUpdate.
