# Arbor

Arbor is a Codex plugin that makes Codex better at long-running repository work.

Codex is strongest when it has the right project context. In real projects, that context is split across docs, git history, current diffs, earlier session notes, and durable project rules. Arbor turns that into a repeatable workflow: every repo gets a project guide, short-term session memory, and hooks that restore the right context at the right time.

It creates and maintains:

- `AGENTS.md` as the durable project guide and map to deeper context.
- `.codex/memory.md` for short-term, uncommitted session memory.
- `.codex/hooks.json` in target projects for project-level Arbor hook registration.

The main benefit is continuity. Arbor helps Codex resume a repo without re-discovering the same facts, keep uncommitted work separate from durable project knowledge, and update project guidance when goals or constraints change.

Arbor fixes the workflow order. It does not limit how much code, documentation, git history, or diff context the agent can read.

## Why Use Arbor

- **Faster repo resumption**: Arbor always starts from the project guide, git history, short-term memory, and current git status.
- **Cleaner memory boundaries**: unresolved uncommitted state goes in `.codex/memory.md`; long-term context is reconstructed from `AGENTS.md`, git history, and project docs.
- **Less repeated context work**: decisions and project structure stop living only in chat history.
- **Project-local by default**: Arbor writes to the current repo, not a global memory store.
- **Hook-ready workflow**: startup context, memory hygiene, and AGENTS drift each have clear project-level hook intents.
- **Agent-friendly design**: Arbor controls the workflow shape without restricting the agent's reading depth or reasoning.

## Install

Install Arbor from GitHub:

```bash
codex plugin marketplace add shawnyin128/arbor
```

If `codex` is not on your `PATH` on macOS:

```bash
/Applications/Codex.app/Contents/Resources/codex plugin marketplace add shawnyin128/arbor
```

To install from SSH instead:

```bash
codex plugin marketplace add git@github.com:shawnyin128/arbor.git
```

To upgrade later:

```bash
codex plugin marketplace upgrade arbor-local
```

To remove the marketplace:

```bash
codex plugin marketplace remove arbor-local
```

## Skills

Arbor currently ships one skill:

```text
$arbor
```

### `$arbor`

Use `$arbor` when you want Codex to stay oriented across a real development workflow, especially when work spans multiple sessions or depends on git history.

What it does well:

- creating `AGENTS.md` when missing;
- creating `.codex/memory.md` when missing;
- registering Arbor hooks into target-project `.codex/hooks.json`;
- loading startup context in the fixed order: `AGENTS.md`, formatted `git log`, `.codex/memory.md`, `git status`;
- refreshing short-term memory when current-session or uncommitted work makes `.codex/memory.md` stale;
- preparing `AGENTS.md` updates when the project guide or map needs to point Codex at changed durable context.

How long-term memory works:

Important: `AGENTS.md` is not Arbor's long-term memory database.

- `AGENTS.md` is the entrypoint. It holds stable goals, constraints, and a map of where important project knowledge lives.
- `git log` is the completed-work history. Good commits make finished features, fixes, and verification discoverable.
- project docs hold deeper design, review, and domain context that should not be compressed into `AGENTS.md`.
- `.codex/memory.md` is only for short-term unresolved state before it is committed, resolved, or moved to durable docs.

Use it when:

- starting work in a new repo;
- resuming a repo after time away;
- preparing to commit and wanting memory to reflect only unresolved uncommitted work;
- changing project goals, constraints, naming, architecture, or the project map;
- building workflows where git log and project docs are part of the agent's long-term context.

## Usage

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

After initialization, the target project should contain:

```text
AGENTS.md
.codex/memory.md
.codex/hooks.json
```

## Hooks

`$arbor` registers three project-level hook intents into the target project's `.codex/hooks.json`:

- `arbor.session_startup_context`: emits startup context in the required order.
- `arbor.in_session_memory_hygiene`: emits memory, git status, and diff context for short-term memory refresh.
- `arbor.goal_constraint_drift`: emits project guide context when `AGENTS.md` may need to update its stable goals, constraints, or map pointers.

The hooks are registered by the skill during project initialization; Arbor does not ship a root-level Codex hook manifest. The hooks emit context packets, and the agent decides whether to edit `.codex/memory.md` or `AGENTS.md`.

## Version

Current version:

```text
0.1.0
```

Version file:

```text
.codex-plugin/plugin.json
```

Marketplace file:

```text
.claude-plugin/marketplace.json
```
