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

- The full hook lifecycle is verified live on 2.1.9, but the non-ASCII fix in
  2.1.10 is not. Open a session, have it create a task list with Chinese titles,
  then open another session and expect the `## In flight` section to show the
  characters rather than replacement marks. That is the last open item.
