# Feature 12 Review: Full-Corpus Hook Execution Report

## Purpose

Run the complete trigger scenario corpus through the Stage B harness and report hook execution-chain quality.

## Scope

In scope:

- Add full-corpus mode to `scripts/evaluate_hook_triggers.py`.
- Evaluate every Markdown/sidecar scenario through fixture generation, sidecar-backed simulated dispatch, registered hook execution, and packet/side-effect assertions.
- Emit compact JSON report summaries by default.
- Support detailed full stdout/stderr output when requested.
- Add focused tests for full-corpus report summaries, detailed output mode, and CLI full-corpus mode.

Out of scope:

- Real semantic dispatcher integration.
- H1/H2/H3 precision or recall.
- `NONE` or near-miss false-positive rates as semantic metrics.
- Stochastic stability metrics.
- Any claim that sidecar-backed dispatch measures real trigger quality.

## Design Notes

The report measures whether the harness and registered hook execution chain work across the full corpus. It does not measure natural-language trigger quality because the dispatcher is still backed by the expected sidecar.

Reported chain-quality fields include:

- total and passed scenario counts;
- dispatcher decision counts;
- selected hook execution counts;
- hook execution pass rate;
- outside-root rejection counts and leak counts;
- unintended write failures;
- assertion failures;
- a `semantic_metrics.reported = false` marker with explanation.

The default report uses compact per-scenario results so review agents can inspect the corpus without reading every hook packet. `--include-details` is available for debugging.

## Implementation Notes

- Extended `scripts/evaluate_hook_triggers.py` with `evaluate_corpus`, compact report rendering, and `--all` CLI mode.
- Added full-corpus tests to `HookTriggerExecutionHarnessTests`.
- Updated `docs/arbor-skill-design.md` with Feature 12 scope and Stage B progress.

## Validation

- `python3 -m unittest tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 12 tests passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 102 tests passed.
- `python3 -m json.tool docs/reviews/hook-trigger-scenarios.json`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f12-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/evaluate_hook_triggers.py tests/test_arbor_skill.py`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f12-cli-smoke`: passed and emitted full-corpus report JSON.
- `env COVERAGE_FILE=/private/tmp/arbor-f12-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 102 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f12-coverage conda run -n arbor python -m coverage report`: total coverage 89%; `scripts/evaluate_hook_triggers.py` coverage 83%.

## Full-Corpus Report Snapshot

`python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f12-cli-smoke` produced:

- `total_scenarios`: 150
- `passed_scenarios`: 150
- `failed_scenarios`: 0
- `selected_hook_executions`: 103
- `hook_execution_pass_rate`: 1.0
- `outside_root_rejections`: 1
- `outside_root_rejections_passed`: 1
- `outside_root_leaks`: 0
- `unintended_write_failures`: 0
- `semantic_metrics.reported`: false

Decision counts:

- `trigger`: 96
- `none`: 48
- `ambiguous`: 6

Hook counts:

- `arbor.session_startup_context`: 33
- `arbor.in_session_memory_hygiene`: 35
- `arbor.goal_constraint_drift`: 35

## Developer Response

Feature 12 is implemented and targeted-tested. The full corpus now runs through the sidecar-backed Stage B harness and reports hook execution-chain quality while explicitly withholding semantic trigger metrics until a real dispatcher replaces the simulator.

## Final Closure

Feature 12 is accepted in the final Arbor current-scope closure.

Closure criteria met:

- The full 150-scenario corpus runs through the sidecar-backed Stage B harness.
- Registered hook execution succeeds for every selected hook.
- Outside-root rejection is exercised without leaking outside content.
- No hook script makes unintended writes to `AGENTS.md` or `.codex/memory.md`.
- Semantic trigger metrics remain explicitly withheld because the dispatcher is still sidecar-backed.
