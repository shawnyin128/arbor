# Parked Ideas

<!--
Ideas raised in passing that are not part of the current task. Appending one line
here is how an idea survives the session without derailing it.

One line per idea, newest at the bottom. Say enough that it is still
understandable months later without this conversation. Remove an idea once it is
done, filed as an issue, or deliberately rejected.

This is not a backlog or a specification. If an idea grows past one line, it has
earned a real home: an issue, a design note, or a project doc.
-->

## Parked

- Use the `InstructionsLoaded` hook to record that `CLAUDE.md` and its `@AGENTS.md`
  import actually loaded. Doctor infers this today by reading the file, so it
  cannot see the cases that matter: `claudeMdExcludes` skipping the file, or a
  declined external-import approval, which disables the import permanently and
  never asks again. Either one silently costs the user the durable half of their
  context. Matching only the `session_start` load reason keeps it to one
  invocation per session.
- Report note age in commit distance from `arbor doctor`, not in the packet. The
  primitive already exists as `vcs.count_commits_since`, and `git blame` plus
  `rev-list` measured 82ms on this repository. Keep it a display hint only:
  path existence stays the invalidation signal, and a "written 34 commits ago"
  line inside injected context would be a distractor.
- Investigate whether `shell: bash` in hooks.json is the right choice on Windows.
  CI showed that `bash` on PATH can be WSL's own launcher, which on a machine with
  no distribution prints an installation notice and exits 1 without reading the
  script, so the hook would fail before the launcher runs. Dropping `shell: bash`
  is not a one-line change: the launcher has no shebang and git mode 100644, so a
  POSIX host would fail with Permission denied, and adding a shebang makes cmd.exe
  report an unknown command on its first line. Not observed biting on this machine
  or on the GitHub Windows runner, both of which resolved a working POSIX bash.
