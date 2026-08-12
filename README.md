# Arbor

A Claude Code plugin that restores the volatile half of project context when a
session starts.

Claude Code already carries more than it used to. A `CLAUDE.md` that imports
`AGENTS.md` loads every session and survives compaction, and the host appends its
own git block with the branch, the full short status, and the five most recent
commits. What nothing native carries is state from *last* session: which tasks
were in flight, what landed while you were away, what decision was left open,
which idea got mentioned and dropped. Arbor captures that with hooks and injects
it back, in about a thousand characters.

Every section below was A/B tested against a session with the packet withheld.
Three earlier sections that restated the host's git block were removed in 2.2.0
after measuring no benefit from them.

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
| `PostToolUse` on the task tools | every task change | snapshots the task list |
| `SessionEnd` | session ends | records a handoff summary |

The task snapshot is the load-bearing one. Claude's own task list is the ground
truth for what was in flight, so nothing has to be summarized or inferred, and
because it is written as the list changes, it survives a session that ends
abruptly.

Hosts expose that list in one of two ways. `TodoWrite` carries the whole list in
its payload. The `Task` tools change one entry at a time, so a single payload
cannot describe the list; for those Arbor reads the host's own task files, which
are authoritative anyway. Both are matched, because which one exists depends on the
Claude Code version.

A typical injected packet:

```text
# Arbor Session Context

Volatile project state recovered by Arbor. ...

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

## Parked ideas
2 parked; most recent:
- Cache the token index between runs

## Upstream
2 ahead of origin/feature/parser
```

You also get a one-line summary in the session UI — "Arbor loaded in flight,
unresolved, parked ideas; 1048 chars" — through the `systemMessage` channel, which
the model never sees and which therefore costs no context.

## Files

| File | Written by | Holds |
| --- | --- | --- |
| `AGENTS.md` | you and the agent | goal, commands, constraints, the big picture |
| `CLAUDE.md` | `init`, then you | the `@AGENTS.md` import, plus your own notes |
| `.arbor/memory.md` | the agent | what is still unresolved |
| `.arbor/ideas.md` | the agent | ideas raised in passing |
| `.arbor/session.json` | hooks | todo snapshots, handoff, hook receipts |

The split is deliberate. Hooks can see *what* happened; only the agent knows
*why* the work stopped. Keeping machine state in JSON and agent notes in Markdown
means neither has to be told apart from the other, and the two Markdown files
stay reviewable in a diff. `init` gitignores `session.json`, because it is
rewritten constantly and would only add noise to your history.

## Best practices

There is no phrasebook. Talk the way you already talk; Claude decides when
something is worth keeping. What follows is a real afternoon.

You are working on the tokenizer, and partway through you think out loud:

```text
> btw at some point we should probably cache the token index, it's O(n) every run
```

That is not the current task, so Claude writes one line down and keeps going. Two
weeks later, when you ask what else was on the list, it is still there.

Later the same afternoon you hit a fork and do not resolve it:

```text
> i'm not sure whether to keep the old adapter. leave it for now
```

Written down as an open question, not as a decision. Tomorrow it comes back as an
open question, so nobody quietly assumes it was settled.

Then you stop:

```text
> ok that's enough for today
```

Next morning you open the same repository and just say what you want next. Claude
already has the half-finished task, the commits your teammate pushed overnight, the
adapter question, and the caching idea. You explain none of it.

### It gets better if you do two things

**Let it keep a task list on anything sizeable.** That list is what survives a
session that ends badly — a crash, a closed laptop, a `/clear`. Work without one
and there is nothing to pick up.

**Mention the file when you know it.** "Not sure about `src/adapter.py`" is worth
more than "not sure about the adapter", because Claude will tell you later when
that file no longer exists and the note has gone stale.

### When something settles, say so

```text
> we're keeping the adapter, that one's decided
```

Otherwise it sits in the notes forever. Every few weeks it is worth asking Claude
to read through the notes and clear out anything already done.

### Good to know

- Notes are committed with the repository, so a teammate — or you on another
  machine — gets them. A half-finished task list stays on the computer that made it.
- In a project you have not set up, Arbor does nothing at all.
- If you suspect it is not working, ask Claude to run `arbor doctor`. It reports
  when each part last ran, which is the quickest way to tell "nothing to say" from
  "not running".

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

Initializing with Arbor means you will not run Claude Code's own `/init`, so the
scaffold covers what `/init` produces and refuses what it refuses. It asks for
build, test, and lint commands — including how to run a single test, which `/init`
calls out specifically — and for the big picture, which `/init` defines as the
architecture that takes reading several files to understand. Applied as a test to
every bullet, that criterion keeps a relationship spanning files and cuts anything
one `ls` would show. It leaves out the five things `/init` declines to write: repetition,
obvious instructions, discoverable file structure, generic development practice,
and invented sections. New `CLAUDE.md` files carry the header `/init` mandates;
an existing one still only gains the import line.

Filling those sections in needs the repository read, which the CLI does not do —
it makes no model calls. The `arbor` skill does it, in the same turn as `init`.

`doctor` prints one row per surface and answers the two questions that are
otherwise invisible: when each hook last fired, and how big the injected packet
is. It reports and never repairs.

## Design notes

**Nothing the host already sends.** Claude Code appends its own git block to every
session: the branch, the whole `git status --short`, and the five most recent
commits. Arbor used to restate all three. A 42-run A/B — the same fixture with the
packet injected and withheld — answered those three questions correctly in both
arms and needed no extra turns without Arbor, while the duplicated commit list
provoked an extra verification turn. They were removed in 2.2.0. What survived
measured a real gap: parked ideas went from 0/3 correct to 3/3, unresolved notes
from 1/3 to 3/3, and the in-flight task list from 8 turns to 1. Re-run it with
`python tests/ab_harness.py`.

**Front-loading, not trimming.** A payload over roughly 10,000 characters is not
discarded: the host keeps the head, writes the whole thing to a file, and says so
in context. Measured directly, at 9,400 characters it arrives whole, and at 13,500
and 40,000 the head arrives with a pointer to the complete text on disk. So the
packet is ordered most valuable first and never trimmed; per-section caps keep it
near a thousand characters anyway.

**No clocks in injected context.** A timestamp that ticks while the project sits
still would invalidate the prompt prefix cache every session for no gain, so the
packet carries none. Staleness is expressed as commit distance instead: a todo
snapshot taken before the latest commit says so.

**What you missed.** Because the todo snapshot and the handoff both record the
commit they were taken at, Arbor can report what landed while you were away —
commit count, subjects, and which files were created, deleted, or renamed. If
that recorded commit is no longer reachable, it says history was rewritten
instead of computing a diff against it, because that fact matters more than any
diff derived from it. This is the one section nothing native can produce: no
native session state stores a commit to measure from.

**Notes are checked, not just repeated.** A note that names a path in backticks is
making a claim about the tree. If that path is gone from disk and git has a commit
for it, the note is still shown but marked `outdated`, because it may hold the only
record of why the path was removed. A path git never tracked is not checked, since
a branch name looks exactly like a path and a false alarm is itself a distractor.
An unresolved merge conflict in a notes file is reported rather than silently
presented as a settled list.

**Losing the last hook costs little.** The task list is written when it changes, not
at the end, so closing a window or killing the process keeps it. Only the
end-of-session summary line is lost, and the "since last session" range falls back
to the commit recorded with the task snapshot, so a resumed session still reports
what landed while it was away.

**Receipts.** Every hook stamps `session.json` with the event, time, and plugin
version. Whether a hook fired is then a fact `doctor` can report rather than an
assumption. This was the one real advantage of abandoning hooks for an
agent-executed protocol, and it turns out to be orthogonal to the trigger.

**UTF-8 in both directions.** Python encodes and decodes the standard streams with
the platform locale, which on Windows is a legacy code page, while the host speaks
UTF-8. Left to the default, a non-ASCII task title reaches the model as a
replacement character and a payload naming a non-ASCII path is mis-decoded on the
way in. Arbor pins all three streams, and its tests force a hostile locale so the
pin is verified everywhere rather than only where the platform disagrees.

**Silence over noise.** Any unusable input — an empty probe payload, a byte order
mark, a corrupt state file, a missing interpreter — is a silent skip with exit
code 0. A hook that fires in every project must fail quietly.

## Tests

```bash
python -m pytest
```

Continuous integration runs the suite and the mutation check on Linux, macOS, and
Windows, because the launcher's failure mode is a silent exit and only a matrix
exercises both of its branches.

The suite builds real temporary git repositories and covers hook payload
robustness, the opt-in gate, budget enforcement and drop order, atomic state
writes, initialization idempotence, doctor reporting, and the launcher under both
`cmd.exe` and POSIX shells.

The suite is itself checked, because a test that also passes against a broken
implementation is not testing anything:

```bash
python tests/mutations.py
```

That breaks the implementation twenty-seven ways — removing the opt-in gate,
putting back a section the host already sends, reintroducing a timestamp into
injected context,
letting `init` overwrite user files, adding carriage returns to the launcher —
and requires the covering tests to fail each time.

## Version

```text
2.3.0
```
