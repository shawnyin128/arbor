# Arbor

Arbor is a Codex plugin that gives each repository a project-local memory workflow.

It creates and maintains:

- `AGENTS.md` for durable project goals, constraints, and project map.
- `.codex/memory.md` for short-term, uncommitted session memory.
- `.codex/hooks.json` for project-level Arbor hook registration.

Arbor fixes the workflow order. It does not limit how much code, documentation, git history, or diff context the agent can read.

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

Use `$arbor` when you want Codex to initialize or resume a repository with project-local memory.

It is responsible for:

- creating `AGENTS.md` when missing;
- creating `.codex/memory.md` when missing;
- registering Arbor hooks into `.codex/hooks.json`;
- loading startup context in the fixed order: `AGENTS.md`, formatted `git log`, `.codex/memory.md`, `git status`;
- refreshing short-term memory when current-session or uncommitted work makes `.codex/memory.md` stale;
- preparing durable `AGENTS.md` updates when project goals, constraints, or project map entries change.

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

Update durable project guidance:

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

`$arbor` registers three project-level hook intents:

- `arbor.session_startup_context`: emits startup context in the required order.
- `arbor.in_session_memory_hygiene`: emits memory, git status, and diff context for short-term memory refresh.
- `arbor.goal_constraint_drift`: emits project guide context for durable `AGENTS.md` goal, constraint, and map updates.

The hooks emit context packets. The agent decides whether to edit `.codex/memory.md` or `AGENTS.md`.

## Maintainer Validation

Before publishing a release, run:

```bash
python3 scripts/validate_plugin_install.py --codex-probe
python3 -m unittest tests/test_arbor_skill.py
conda run -n arbor python -m ruff check . --no-cache
```

Current release validation:

- packaged payload: 13/13 expected files matched;
- Codex marketplace add: passed;
- packaged initialization smoke: passed;
- all three packaged hook smokes: passed;
- full unit suite: 186 tests passed;
- authenticated real-runtime corpus: 150/150 scenarios and 111/111 selected hook executions passed.

## Release Payload

The installable plugin lives in:

```text
plugins/arbor
```

The marketplace entry lives in:

```text
.agents/plugins/marketplace.json
```

Development and review tooling is not part of the plugin payload.

## Version

Current version:

```text
0.1.0
```

Version file:

```text
plugins/arbor/.codex-plugin/plugin.json
```
