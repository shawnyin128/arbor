# Feature 14 Review: Plugin Trigger Selection and Input Builder

## Purpose

Add the first runtime-shaped plugin trigger boundary so the Stage B harness can swap between the sidecar-backed baseline and a future real plugin runtime trigger path without leaking evaluator expectations into plugin runtime input.

## Scope

In scope:

- Add a plugin trigger adapter module.
- Add a harness trigger-adapter selection option.
- Keep `sidecar-baseline` as the default behavior.
- Add a `plugin-runtime-stub` adapter that proves the harness can run a non-sidecar input path.
- Build plugin runtime input from expression, fixture/live summary, hook contract, and skill metadata.
- Validate trigger decision contract before executing selected hooks.

Out of scope:

- Implementing natural-language semantic trigger selection.
- Calling a model, plugin runtime, or external API.
- Reporting semantic precision, recall, false-positive, ambiguity, multi-hook, or stability metrics.
- Changing hook scripts or hook registration behavior.

## Design

Feature 14 introduces one adapter boundary:

```text
scenario corpus + fixture
-> plugin trigger adapter selection
-> trigger decision contract JSON
-> registered hook execution harness
```

The `sidecar-baseline` adapter keeps the current sidecar-backed behavior and remains the default so existing reports are stable.

The `plugin-runtime-stub` adapter builds the same kind of input that a future real plugin runtime trigger path should receive, then returns a valid no-hook trigger decision contract. It is intentionally not a semantic classifier. Its purpose is to make non-circularity testable before adding the real plugin runtime path.

The plugin runtime input may include:

- user expression;
- project root;
- fixture summary or live project summary;
- project-local hook contract;
- concise Arbor skill metadata;
- runtime event type.

The plugin runtime input must not include:

- expected label;
- expected hooks;
- optional expected hooks;
- forbidden hooks;
- allowed decisions;
- scenario notes;
- sidecar override/default scoring fields.

## Test Plan

Unit tests:

- Plugin runtime input builder excludes all sidecar scoring fields.
- Trigger decision contract validation accepts valid sidecar-baseline and plugin-runtime-stub output.
- Trigger decision contract validation rejects unknown hook ids.
- Trigger decision contract validation rejects invalid decisions and confidence values.
- Trigger decision contract validation rejects optional args for hooks that were not selected.

Scenario tests:

- Existing default harness scenario path still uses `sidecar-baseline` and passes.
- `--trigger-adapter sidecar-baseline` CLI path passes.
- `--trigger-adapter plugin-runtime-stub` CLI path passes without executing hooks.
- Full-corpus sidecar-baseline report remains passing and marks semantic metrics as unreported.

## Acceptance Gates

- Existing tests remain passing.
- Default CLI behavior is backward compatible.
- Plugin-runtime-stub path never reads sidecar expectation fields as plugin runtime input.
- Reports identify the plugin trigger adapter used.
- Semantic metrics remain withheld until a non-stub plugin runtime trigger adapter produces observed labels.

## Developer Response

Feature 14 is implemented as a small adapter-boundary increment.

Implemented:

- Added `scripts/plugin_trigger_adapters.py`.
- Added trigger decision contract validation for selected hooks, decisions, confidence values, optional args, and required contract keys.
- Added plugin runtime input building from expression, project state, hook contract, and skill metadata.
- Added recursive rejection for sidecar scoring fields in plugin runtime input.
- Added `plugin-runtime-stub`, which abstains with a valid trigger decision contract and selects no hooks.
- Added `--trigger-adapter sidecar-baseline|plugin-runtime-stub` to `scripts/evaluate_hook_triggers.py`, with `sidecar-baseline` as the backward-compatible default.
- Added report-level `trigger_adapter` metadata and adapter-specific semantic-metric withholding reasons.
- Updated `AGENTS.md` project map for the new adapter module.

Validation:

- `python3 -m unittest tests.test_arbor_skill.HookTriggerPluginAdapterTests tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 20 tests passed.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-f14-plugin-stub-smoke --trigger-adapter plugin-runtime-stub`: passed.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-f14-sidecar-smoke --trigger-adapter sidecar-baseline`: passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 110 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f14-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py tests/test_arbor_skill.py`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f14-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios passed, 103/103 selected hook executions passed, outside-root leaks 0, unintended writes 0, semantic metrics not reported.

Feature 14 still does not implement semantic trigger selection. The next feature should replace `plugin-runtime-stub` with a real plugin runtime trigger adapter behind the same contract, then report semantic metrics only from that non-stub observed output.
