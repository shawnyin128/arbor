# Arbor Release Closure

## Release Scope

Arbor is ready to publish as the current repo-local Codex plugin package.

Release contents:

- `plugins/arbor/.codex-plugin/plugin.json`
- `plugins/arbor/hooks.json`
- `plugins/arbor/skills/arbor/SKILL.md`
- `plugins/arbor/skills/arbor/agents/openai.yaml`
- `plugins/arbor/skills/arbor/references/agents-template.md`
- `plugins/arbor/skills/arbor/references/memory-template.md`
- `plugins/arbor/skills/arbor/references/project-hooks-template.md`
- `plugins/arbor/skills/arbor/scripts/collect_project_context.py`
- `plugins/arbor/skills/arbor/scripts/init_project_memory.py`
- `plugins/arbor/skills/arbor/scripts/register_project_hooks.py`
- `plugins/arbor/skills/arbor/scripts/run_agents_guide_drift_hook.py`
- `plugins/arbor/skills/arbor/scripts/run_memory_hygiene_hook.py`
- `plugins/arbor/skills/arbor/scripts/run_session_startup_hook.py`

Release exclusions:

- `docs/reviews/`
- `docs/reviews/artifacts/`
- `scripts/evaluate_hook_triggers.py`
- `scripts/eval_fixtures.py`
- `scripts/plugin_trigger_adapters.py`
- `scripts/probe_plugin_runtime.py`
- `scripts/simulated_dispatcher.py`
- `scripts/validate_plugin_install.py`
- `tests/`

These exclusions are intentional. They are development, review, and validation tooling, not packaged Arbor runtime payload.

## Release Evidence

Feature 25 retained the release-gating authenticated real-runtime corpus:

- Report: `docs/reviews/artifacts/feature-25-full-corpus-r4-report.json`
- Progress: `docs/reviews/artifacts/feature-25-full-corpus-r4-progress.jsonl`
- Result: 150/150 scenarios passed.
- Selected hook executions: 111/111 passed.
- Runtime blockers: 0.
- Outside-root leaks: 0.
- Unintended writes: 0.
- Semantic metrics: reported and passed.

Latest release smoke should verify:

- exact packaged payload inventory;
- repo-local marketplace configuration;
- plugin manifest and hook entrypoints;
- packaged skill initialization and hook packet smokes;
- isolated Codex CLI marketplace add;
- standalone and packaged skill validation;
- full unit suite;
- static lint and compile checks.

## Release Decision

Accepted for current release.

Repeated authenticated runtime stability remains deferred because it requires repeated full real-runtime corpus runs. It is not a release blocker for this single-pass validated version.

## Latest Release Gate

Commands:

```bash
env PYTHONPYCACHEPREFIX=/private/tmp/arbor-release-pycache python3 scripts/validate_plugin_install.py --codex-probe
python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor
python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor
conda run -n arbor python -m ruff check . --no-cache
python3 -m unittest tests/test_arbor_skill.py
env PYTHONPYCACHEPREFIX=/private/tmp/arbor-release-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py plugins/arbor/skills/arbor/scripts/init_project_memory.py plugins/arbor/skills/arbor/scripts/collect_project_context.py plugins/arbor/skills/arbor/scripts/register_project_hooks.py plugins/arbor/skills/arbor/scripts/run_session_startup_hook.py plugins/arbor/skills/arbor/scripts/run_memory_hygiene_hook.py plugins/arbor/skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py scripts/probe_plugin_runtime.py tests/test_arbor_skill.py
python3 -m json.tool plugins/arbor/.codex-plugin/plugin.json
python3 -m json.tool plugins/arbor/hooks.json
python3 -m json.tool .agents/plugins/marketplace.json
git diff --check
```

Results:

- Plugin install validation passed with `--codex-probe`.
- Codex CLI marketplace add passed for `arbor-local`.
- Packaged payload inventory matched the expected 13 files.
- Packaged skill smoke initialized `AGENTS.md` and `.codex/memory.md`.
- Packaged hook smokes passed for all three Arbor hooks.
- Standalone skill quick validation passed.
- Packaged skill quick validation passed.
- `ruff` passed.
- Full unit suite passed: 186 tests.
- `py_compile`, JSON validation, and `git diff --check` passed.
