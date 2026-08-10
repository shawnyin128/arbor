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
  import actually loaded, turning doctor's static import check into observed fact.
- Warn on memory staleness by commit distance, not only by line count: an entry
  written many commits ago is more suspect than a long one.
- Investigate `watchPaths` in SessionStart output for keeping edits to
  `.arbor/memory.md` visible mid-session without a re-injection.
- Consider a `PostCompact` hook: compaction is exactly when volatile context is
  lost, and SessionStart only covers it if the host reports source `compact`.
