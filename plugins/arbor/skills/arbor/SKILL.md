---
name: arbor
description: "Use when setting up or checking Arbor in a project: initializing AGENTS.md, CLAUDE.md, and .arbor/ state, or reporting whether Arbor's hooks fired and its files are healthy. Not for project summaries, resume narration, or general maintenance advice."
---

# Arbor

Arbor restores the volatile half of project context. The durable half —
`AGENTS.md`, loaded through the `@AGENTS.md` import in `CLAUDE.md` — is carried by
Claude Code itself. Arbor's hooks supply what no static file can: where git is,
which tasks were in flight, what is still unresolved, and which ideas were parked.

Use this skill to initialize a project, or to report Arbor's state. Do not use it
to answer "what does this project do?" or "where were we?" — the injected
SessionStart packet plus the project's own files already answer those.

## Commands

Run these with the skill's own `scripts/` directory:

```bash
python scripts/arbor.py init --root .
python scripts/arbor.py doctor --root .
python scripts/arbor.py context --root .
```

- `init` creates missing files and never overwrites existing content. Its one
  edit to an existing file is appending `@AGENTS.md` to a `CLAUDE.md` that lacks
  it. Add `--dry-run` to preview. It writes placeholders, not content — filling
  them in is the second half of initializing, described below.
- `doctor` reports one row per surface, including when each hook last fired and
  how large the injected packet is. Add `--strict` to exit nonzero unless every
  row is `ok`. It reports; it never repairs.
- `context` prints the packet SessionStart would inject, for debugging.

## Initializing a project

Running `init` is half the job. A user who initializes with Arbor will not also
run Claude Code's `/init`, so the placeholders `init` leaves behind are a gap
until you fill them. Do that in the same turn, from the repository itself:

1. Read the build and test configuration — `package.json`, `pyproject.toml`,
   `Makefile`, `justfile`, CI workflows — and write the real command lines into
   `Commands`, including how to run one test rather than the whole suite.
2. Read `README.md`, and any `.cursor/rules/`, `.cursorrules`, or
   `.github/copilot-instructions.md`, and carry over the parts that state a rule.
   Do not copy prose that merely describes the project.
3. Write the architecture that takes reading several files to see — what talks to
   what, and which boundaries exist — into `Project Map` as rules about where code
   belongs, naming exact files.
4. Replace the `Project Goal` placeholder with one or two sentences.
5. Show the user what you wrote and ask them to correct it. You inferred it; they
   know it.

Leave a placeholder in place rather than guessing. `doctor` reports an unfilled
section, and an honest gap beats an invented answer that reads as settled fact.

## Files

| File | Written by | Holds |
| --- | --- | --- |
| `AGENTS.md` | you and the user | durable goal, constraints, project map |
| `CLAUDE.md` | `init`, then the user | the `@AGENTS.md` import and Claude-specific notes |
| `.arbor/memory.md` | you, deliberately | what is still unresolved |
| `.arbor/ideas.md` | you, deliberately | ideas raised in passing |
| `.arbor/session.json` | hooks only | todo snapshots, handoff, hook receipts |

Never hand-edit `session.json`. It is gitignored by `init`, because it is
rewritten on every todo change; the two Markdown files beside it stay committed
so they can be reviewed in a diff.

A project opts into Arbor by having a `.arbor/` directory. Without it every hook
is silent, which is what keeps a plugin-level hook from acting in unrelated
repositories.

## Writing notes

`.arbor/memory.md` answers what a hook cannot: not what changed, but why the
work stopped and what is still open. Record an entry when a decision is left
open. Remove it once it is settled, committed, or documented.

Do not record what the repository already records — code structure, past fixes,
git history, or anything already in `AGENTS.md` — and do not record what mattered
only to one conversation. If asked to remember one of those, work out what was
non-obvious about it and record that instead. Update an entry rather than adding a
near-duplicate.

`.arbor/ideas.md` takes one line per idea when the user floats something that is
not part of the current task. Appending is how the idea survives without
derailing the session. Remove it once it is done, filed, or rejected.

Keep both short. `doctor` warns when memory passes 40 lines: a long note is a
worse note, and the injected packet is meant to be re-read every session.

When a note names a path or filename in backticks, it is checked from the repository root. If it is gone from
disk but git has a commit for it, the note is still shown but marked `outdated`,
and `doctor` reports it. A path git never tracked is not checked, because a
branch name looks exactly like a path and a false alarm in injected context costs
more than the warning saves.

## Updating AGENTS.md

Change it when the durable goal or a real constraint changes. Keep transient state
out of it entirely.

Every Project Map bullet must say something the tree cannot show: where new code
of a given kind belongs, a boundary not to cross, a trap. A path list is not one,
because the agent finds files with glob and grep and a repository overview does
not measurably reduce the steps it takes to reach the files it must change. Point
at the exact file that matters, nested or not, rather than listing directories for
completeness.

Nothing in Arbor rewrites `AGENTS.md` automatically. `doctor` reports drift —
any backticked path in the guide that git has a record of but disk no longer has —
and leaves the edit to you.

## Hooks

The plugin registers three hooks in `hooks/hooks.json`; no project-level
registration is needed.

- `SessionStart` (`startup`, `resume`, `clear`, `compact`) injects the packet and
  reports a one-line summary to the user through `systemMessage`.
- `PostToolUse` on the task tools snapshots the task list, so in-flight work is
  durable even if the session ends abruptly. `TodoWrite` sends the whole list;
  `TaskCreate` and `TaskUpdate` change one entry, so the host's own task files are
  read instead. Which tools exist depends on the Claude Code version.
- `SessionEnd` records the handoff summary.

Each writes a receipt into `session.json`, which is how `doctor` can say whether a
hook actually fired rather than assuming it did. The recorded commit is also what
lets the next session's packet report what landed while it was away.

If hooks appear not to run, check that the plugin is enabled and that a Python
interpreter is on `PATH`; `ARBOR_PYTHON` overrides interpreter selection. A
missing interpreter makes the hooks silent by design, never failing.
