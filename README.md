# Arbor

A Claude Code plugin that restores the volatile half of project context when a
session starts.

Claude Code already carries durable context well: a `CLAUDE.md` that imports
`AGENTS.md` loads every session and survives compaction. What it cannot carry is
the state that changes between sessions — where git is, which tasks were in
flight, what decision was left open, which idea got mentioned and dropped. Arbor
captures that with hooks and injects it back, in about a thousand characters.

No daemon, no port, no database, no model calls. Plain files in the repository.

## Install

```text
/plugin marketplace add shawnyin128/arbor
/plugin install arbor@arbor
```

Then initialize the projects you want it in:

```text
/arbor:arbor initialize this project
```

A project opts in by having a `.arbor/` directory. Everywhere else Arbor's hooks
are silent, which matters because plugin hooks fire in every project you open.

Requires a Python interpreter on `PATH` (`python` or `python3`). Set
`ARBOR_PYTHON` to choose one explicitly. Without one the hooks stay silent rather
than failing.

## What it does

Three hooks, registered by the plugin. Nothing is written into your project's
`.claude/settings.json`.

| Hook | When | What it does |
| --- | --- | --- |
| `SessionStart` | start, resume, clear, compact | injects the context packet |
| `PostToolUse` on `TodoWrite` | every todo change | snapshots the task list |
| `SessionEnd` | session ends | records a handoff summary |

The todo snapshot is the load-bearing one. Claude's own task list is the ground
truth for what was in flight, so nothing has to be summarized or inferred, and
because it is written as the list changes, it survives a session that ends
abruptly.

A typical injected packet:

```text
# Arbor Session Context

Volatile project state recovered by Arbor. ...

## Position
branch feature/parser, HEAD a1b2c3d, 2 ahead of origin/feature/parser

## In flight
1 unfinished, 4 done
- [>] Wire the streaming reader into the CLI

## Since last session
3 commits since a1b2c3d
- 9f2e1aa refactor: split the tokenizer
- 4c8d0b1 fix: handle empty input
5 files changed:
  src/tokenizer.py (new)
  src/lexer.py (gone)

## Unresolved
- Whether to keep the legacy adapter; depends on the parser decision

## Working tree
3 changed paths
 M src/parser.py
?? tests/test_streaming.py

## Parked ideas
2 parked; most recent:
- Cache the token index between runs
```

You also get a one-line summary in the session UI — "Arbor loaded position, in
flight, working tree; 1204 chars" — through the `systemMessage` channel, which
the model never sees and which therefore costs no context.

## Files

| File | Written by | Holds |
| --- | --- | --- |
| `AGENTS.md` | you | durable goal, constraints, project map |
| `CLAUDE.md` | `init`, then you | the `@AGENTS.md` import, plus your own notes |
| `.arbor/memory.md` | the agent | what is still unresolved |
| `.arbor/ideas.md` | the agent | ideas raised in passing |
| `.arbor/session.json` | hooks | todo snapshots, handoff, hook receipts |

The split is deliberate. Hooks can see *what* happened; only the agent knows
*why* the work stopped. Keeping machine state in JSON and agent notes in Markdown
means neither has to be told apart from the other, and the two Markdown files
stay reviewable in a diff. `init` gitignores `session.json`, because it is
rewritten constantly and would only add noise to your history.

## Commands

The `arbor` skill runs these; you can also run them directly.

```bash
python plugins/arbor/skills/arbor/scripts/arbor.py init --root .
python plugins/arbor/skills/arbor/scripts/arbor.py doctor --root .
python plugins/arbor/skills/arbor/scripts/arbor.py context --root .
```

`init` is additive: it creates what is missing and never overwrites what exists.
Its one edit to an existing file is appending `@AGENTS.md` to a `CLAUDE.md` that
lacks it, because without that line the durable guide is never loaded.

`doctor` prints one row per surface and answers the two questions that are
otherwise invisible: when each hook last fired, and how big the injected packet
is. It reports and never repairs.

## Design notes

**Budget.** Hook output above roughly 10,000 characters is discarded by the host
silently. The packet is capped below that, and when it does not fit, whole
sections are dropped from the least important upward — recent commits first,
in-flight tasks nearly last — each replaced by the one command that recovers it.
Dropping defers information rather than losing it.

**No clocks in injected context.** A timestamp that ticks while the project sits
still would invalidate the prompt prefix cache every session for no gain, so the
packet carries none. Staleness is expressed as commit distance instead: a todo
snapshot taken before the latest commit says so.

**What you missed.** Because the todo snapshot and the handoff both record the
commit they were taken at, Arbor can report what landed while you were away —
commit count, subjects, and which files were created, deleted, or renamed. If
that recorded commit is no longer reachable, it says history was rewritten
instead of computing a diff against it, because that fact matters more than any
diff derived from it. When this section renders, `Recent commits` is dropped: the
range subsumes it.

**Notes are checked, not just repeated.** A note that names a path in backticks is
making a claim about the tree. If that path is gone from disk and git has a commit
for it, the note is still shown but marked `outdated`, because it may hold the only
record of why the path was removed. A path git never tracked is not checked, since
a branch name looks exactly like a path and a false alarm is itself a distractor.
An unresolved merge conflict in a notes file is reported rather than silently
presented as a settled list.

**Receipts.** Every hook stamps `session.json` with the event, time, and plugin
version. Whether a hook fired is then a fact `doctor` can report rather than an
assumption. This was the one real advantage of abandoning hooks for an
agent-executed protocol, and it turns out to be orthogonal to the trigger.

**Silence over noise.** Any unusable input — an empty probe payload, a byte order
mark, a corrupt state file, a missing interpreter — is a silent skip with exit
code 0. A hook that fires in every project must fail quietly.

## Tests

```bash
python -m pytest
```

The suite builds real temporary git repositories and covers hook payload
robustness, the opt-in gate, budget enforcement and drop order, atomic state
writes, initialization idempotence, doctor reporting, and the launcher under both
`cmd.exe` and POSIX shells.

The suite is itself checked, because a test that also passes against a broken
implementation is not testing anything:

```bash
python tests/mutations.py
```

That breaks the implementation nineteen ways — removing the opt-in gate,
inverting the budget drop order, reintroducing a timestamp into injected context,
letting `init` overwrite user files, adding carriage returns to the launcher —
and requires the covering tests to fail each time.

## Version

```text
2.1.7
```
