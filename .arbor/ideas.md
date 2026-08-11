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
- Find out whether the plugin install path preserves a file's executable bit. The
  2.2.3 fix depends on it, and a zip-based install could drop it; the env var
  `CLAUDE_CODE_PLUGIN_USE_ZIP_CACHE` exists, so that path is real. If the bit does
  not survive, hooks.json has to stop relying on it, which is hard because the same
  command string must work under both cmd.exe and a POSIX shell.
