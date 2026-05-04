# Arbor

Arbor is a Codex plugin for project-local development memory.

It initializes a repository with durable project guidance in `AGENTS.md`, short-term session memory in `.codex/memory.md`, and project-level Arbor hooks in `.codex/hooks.json`. The goal is to keep Codex oriented across daily development work without turning the skill into a bottleneck: Arbor fixes the workflow order, while the agent remains free to read as much code, docs, git history, and diff context as the task requires.

## What Arbor Provides

- Project initialization for `AGENTS.md` and `.codex/memory.md`.
- Project-level hook registration in `.codex/hooks.json`.
- Startup context loading in this order:
  1. `AGENTS.md`
  2. formatted `git log`
  3. `.codex/memory.md`
  4. `git status`
- In-session memory hygiene for uncommitted work and stale short-term notes.
- Durable project guide drift context for project goals, constraints, and project map changes.

## Install

### From GitHub

Add this repository as a Codex plugin marketplace:

```bash
codex plugin marketplace add <owner>/<repo>
```

You can also use a Git URL:

```bash
codex plugin marketplace add https://github.com/<owner>/<repo>.git
```

To pin a release tag:

```bash
codex plugin marketplace add <owner>/<repo> --ref arbor-v0.1.0
```

If `codex` is not on your `PATH` on macOS, use the bundled app binary:

```bash
/Applications/Codex.app/Contents/Resources/codex plugin marketplace add https://github.com/<owner>/<repo>.git
```

After adding the marketplace, install or enable the `arbor` plugin from the configured marketplace in Codex. The repo-local marketplace name is `arbor-local`, and the plugin package is `arbor`.

### From a Local Checkout

Clone or copy this repository, then add the repository root as a local marketplace:

```bash
/Applications/Codex.app/Contents/Resources/codex plugin marketplace add /path/to/arbor
```

For this checkout:

```bash
/Applications/Codex.app/Contents/Resources/codex plugin marketplace add /Users/shawn/Desktop/arbor
```

### Upgrade or Remove

Upgrade a configured marketplace:

```bash
codex plugin marketplace upgrade arbor-local
```

Remove the marketplace:

```bash
codex plugin marketplace remove arbor-local
```

## Initialize A Project

Open the target project in Codex and ask Arbor to initialize it:

```text
$arbor initialize this project
```

Expected project-local files:

```text
AGENTS.md
.codex/memory.md
.codex/hooks.json
```

Arbor writes project-local files only. It does not create a global Arbor memory store.

## Daily Use

Use Arbor when starting or resuming work in a repository:

```text
$arbor resume this repo
```

Use Arbor before committing or when the current session memory may be stale:

```text
$arbor refresh project memory before commit
```

Use Arbor when durable project guidance changes:

```text
$arbor update AGENTS.md for the new project constraints
```

## Hook Contract

Arbor registers three project-level hook intents:

- `arbor.session_startup_context`: emits startup context in the required order.
- `arbor.in_session_memory_hygiene`: emits current memory, git status, and diff context so the agent can refresh `.codex/memory.md`.
- `arbor.goal_constraint_drift`: emits AGENTS/project-doc context so the agent can update durable project goal, constraint, or map sections.

The hooks emit context packets. The agent decides whether to edit `.codex/memory.md` or `AGENTS.md` based on the current conversation and project state.

## Manual Script Usage

The plugin payload includes the same scripts used by the skill. From this repository root:

```bash
python3 skills/arbor/scripts/init_project_memory.py --root <project-root>
python3 skills/arbor/scripts/register_project_hooks.py --root <project-root>
python3 skills/arbor/scripts/run_session_startup_hook.py --root <project-root>
python3 skills/arbor/scripts/run_memory_hygiene_hook.py --root <project-root>
python3 skills/arbor/scripts/run_agents_guide_drift_hook.py --root <project-root>
```

## Validate The Plugin Package

Before publishing or handing off a release, run:

```bash
python3 scripts/validate_plugin_install.py --codex-probe
python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor
python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor
python3 -m unittest tests/test_arbor_skill.py
conda run -n arbor python -m ruff check . --no-cache
```

The current release gate passed with:

- 13/13 packaged payload files matched.
- Codex CLI marketplace add passed.
- Packaged initialization smoke passed.
- All three packaged hook smokes passed.
- Full unit suite passed: 186 tests.
- Authenticated real-runtime corpus passed: 150/150 scenarios and 111/111 selected hook executions.

The retained runtime report is stored at:

```text
docs/reviews/artifacts/feature-25-full-corpus-r4-report.json
```

## Release Payload

The installable plugin is:

```text
plugins/arbor
```

The repo-local marketplace entry is:

```text
.agents/plugins/marketplace.json
```

Development and review tooling is intentionally not part of the plugin payload:

```text
docs/reviews/
docs/reviews/artifacts/
scripts/evaluate_hook_triggers.py
scripts/eval_fixtures.py
scripts/plugin_trigger_adapters.py
scripts/probe_plugin_runtime.py
scripts/simulated_dispatcher.py
scripts/validate_plugin_install.py
tests/
```

## Version

Current plugin version:

```text
0.1.0
```

The version is defined in:

```text
plugins/arbor/.codex-plugin/plugin.json
```
