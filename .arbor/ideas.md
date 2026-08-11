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

- Investigate whether `shell: bash` in hooks.json is the right choice on Windows.
  CI showed that `bash` on PATH can be WSL's own launcher, which on a machine with
  no distribution prints an installation notice and exits 1 without reading the
  script, so the hook would fail before the launcher runs. Not observed biting on
  this machine or on the GitHub Windows runner, both of which resolved a working
  POSIX bash. The Permission-denied half of this note was wrong and is settled:
  `shell: bash` never protected against it, the mode did, and the launcher is now
  checked in 100755.
- Check a backticked symbol the way a backticked path is already checked. Observed
  in real use: a note reading "TODO in `_chunk_loss_sum`" makes a claim Arbor
  verifies nothing about, because `notes.anchors` only accepts a token with a slash
  or a file extension. The session had to say the entry was unconfirmed, which is
  the exact hedge the path check exists to remove. `git grep -w` resolves a symbol
  as cheaply as `rev-list` resolves a path, and the same invalidation rule applies:
  report it only when git has a record of the symbol and the tree no longer does,
  so a renamed local variable does not raise a false alarm. Measure it before
  keeping it: an A/B where one arm's notes name symbols that have since been
  renamed, scored on whether the session acts on a stale entry as though it were
  current.
