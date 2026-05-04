# Arbor

Arbor is a project-context plugin for Codex and Claude Code. It makes both runtimes better at long-running repository work.

Either runtime is strongest when it has the right project context. In real projects, that context is split across docs, git history, current diffs, earlier session notes, and durable project rules. Arbor turns that into a repeatable workflow: every repo gets a project guide, short-term session memory, and hooks that restore the right context at the right time.

It creates and maintains:

- `AGENTS.md` as the canonical durable project guide and map to deeper context (read by both runtimes).
- `.arbor/memory.md` for short-term, uncommitted session memory (shared by both runtimes).
- `.codex/hooks.json` in target projects for project-level Arbor hook registration (Codex installs only).
- `CLAUDE.md` as a short Claude-native bridge pointing at `AGENTS.md` and `.arbor/memory.md` (Claude Code installs only).

The main benefit is continuity. Arbor helps each runtime resume a repo without re-discovering the same facts, keeps uncommitted work separate from durable project knowledge, and updates project guidance when goals or constraints change. Same project state, two runtimes, no duplication.

Arbor fixes the workflow order. It does not limit how much code, documentation, git history, or diff context the agent can read.

## Why Use Arbor

- **Faster repo resumption**: Arbor always starts from the project guide, git history, short-term memory, and current git status.
- **Cleaner memory boundaries**: unresolved uncommitted state goes in `.arbor/memory.md`; long-term context is reconstructed from `AGENTS.md`, git history, and project docs.
- **Less repeated context work**: decisions and project structure stop living only in chat history.
- **Project-local by default**: Arbor writes to the current repo, not a global memory store.
- **Hook-ready workflow**: startup context, memory hygiene, and AGENTS drift each have clear project-level hook intents.
- **Agent-friendly design**: Arbor controls the workflow shape without restricting the agent's reading depth or reasoning.

## Install

### Codex

Add the marketplace and install Arbor:

```bash
codex plugin marketplace add shawnyin128/arbor
```

If `codex` is not on your `PATH` on macOS:

```bash
/Applications/Codex.app/Contents/Resources/codex plugin marketplace add shawnyin128/arbor
```

SSH:

```bash
codex plugin marketplace add git@github.com:shawnyin128/arbor.git
```

Upgrade and remove:

```bash
codex plugin marketplace upgrade arbor
codex plugin marketplace remove arbor
```

### Claude Code

From within a Claude Code session:

```text
/plugin marketplace add shawnyin128/arbor
/plugin install arbor@arbor
```

Run `/reload-plugins` afterward to activate the skill and the bundled `SessionStart` hook in the current session. The hook auto-injects the Arbor startup packet (AGENTS.md, formatted git log, `.arbor/memory.md`, git status) on `startup` and `resume` sources, trimmed to fit Claude Code's context-injection cap.

## Skills

Arbor currently ships one skill, available on both runtimes:

```text
Codex:        $arbor
Claude Code:  /arbor:arbor
```

### `arbor`

Use Arbor when you want either runtime to stay oriented across a real development workflow, especially when work spans multiple sessions or depends on git history.

What it does well:

- creating `AGENTS.md` when missing;
- creating `.arbor/memory.md` when missing;
- migrating legacy `.codex/memory.md` by copying it to `.arbor/memory.md` during explicit initialization when the canonical file is missing;
- creating `CLAUDE.md` as a short bridge to `AGENTS.md` and `.arbor/memory.md` when initialized from a Claude Code install;
- registering Arbor hooks into target-project `.codex/hooks.json` (Codex);
- loading startup context in the fixed order: `AGENTS.md`, formatted `git log`, `.arbor/memory.md`, `git status` — automatically on Claude Code via `SessionStart`, on demand on Codex via the project hook intent;
- refreshing short-term memory when current-session or uncommitted work makes `.arbor/memory.md` stale (auto via `arbor.in_session_memory_hygiene` hook intent on Codex; user-invoked on Claude Code);
- preparing `AGENTS.md` updates when the project guide or map needs to point the agent at changed durable context (auto via `arbor.goal_constraint_drift` hook intent on Codex; user-invoked on Claude Code).

How long-term memory works:

Important: `AGENTS.md` is not Arbor's long-term memory database.

- `AGENTS.md` is the entrypoint. It holds stable goals, constraints, and a map of where important project knowledge lives.
- `git log` is the completed-work history. Good commits make finished features, fixes, and verification discoverable.
- project docs hold deeper design, review, and domain context that should not be compressed into `AGENTS.md`.
- `.arbor/memory.md` is only for short-term unresolved state before it is committed, resolved, or moved to durable docs.

Use it when:

- starting work in a new repo;
- resuming a repo after time away;
- preparing to commit and wanting memory to reflect only unresolved uncommitted work;
- changing project goals, constraints, naming, architecture, or the project map;
- building workflows where git log and project docs are part of the agent's long-term context.

## Usage

Invocation phrasing is the same idea on both runtimes; replace the prefix with `$arbor` on Codex or `/arbor:arbor` on Claude Code (or use natural language — both runtimes auto-trigger Arbor when the request matches its description).

Initialize Arbor in a project:

```text
$arbor initialize this project
```

Resume work in a repository:

```text
$arbor resume this repo
```

Refresh memory before a commit:

```text
$arbor refresh project memory before commit
```

Update the project guide or map:

```text
$arbor update AGENTS.md for the new project constraints
```

After initialization on Codex, the target project should contain:

```text
AGENTS.md
.arbor/memory.md
.codex/hooks.json
```

After initialization on Claude Code, the target project should contain:

```text
AGENTS.md
.arbor/memory.md
CLAUDE.md
```

A project that hosts both runtimes ends up with all four files, sharing the same `AGENTS.md` and `.arbor/memory.md`.

## Hooks

### Codex

`$arbor` registers three project-level hook intents into the target project's `.codex/hooks.json`:

- `arbor.session_startup_context`: emits startup context in the required order.
- `arbor.in_session_memory_hygiene`: emits memory, git status, and diff context for short-term memory refresh.
- `arbor.goal_constraint_drift`: emits project guide context when `AGENTS.md` may need to update its stable goals, constraints, or map pointers.

The hooks are registered by the skill during project initialization; Arbor does not ship a root-level Codex hook manifest. The hooks emit context packets, and the agent decides whether to edit `.arbor/memory.md` or `AGENTS.md`.

### Claude Code

The plugin bundles a single `SessionStart` hook (`hooks/hooks.json` + `hooks/session-start`) that fires on the `startup` and `resume` sources. Its Python adapter calls the shared `run_session_startup_hook.py`, applies a budget-aware truncation policy so the rendered packet stays under Claude Code's `additionalContext` cap, and prints the packet to stdout for automatic injection into the conversation.

Memory hygiene and goal-constraint drift are not auto-fired on Claude Code (Claude Code has no native event that delivers a context packet at the right time). Invoke them through the user-driven workflows above; the underlying scripts are the same on both runtimes.

## Legacy Memory Path

Arbor v0.1 used `.codex/memory.md` for short-term memory. Current Arbor uses `.arbor/memory.md` so the same memory file can be shared by future runtime adapters.

During explicit initialization, if `.arbor/memory.md` is missing and legacy `.codex/memory.md` exists, Arbor copies the legacy content into `.arbor/memory.md` and preserves the old file. It does not merge or delete legacy files automatically.

## Version

Current version:

```text
0.3.0
```

Version files:

```text
.codex-plugin/plugin.json
.claude-plugin/plugin.json
```

Marketplace file:

```text
.claude-plugin/marketplace.json
```
