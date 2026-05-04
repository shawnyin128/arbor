# Feature 20 Review: Repeated Runtime Corpus Stability

## Objective

Add a repeated full-corpus evaluation path that can report trigger stability only when repeated real plugin runtime runs are available and all semantic scoring gates pass.

## Scope

In scope:

- Repeated `--all` corpus runs with isolated per-run fixture roots.
- Stability comparison across scenario ids using decision, selected hooks, and optional args.
- Stability reported only for repeated, gate-ready `plugin-runtime-codex-exec` reports.
- Explicit withheld-stability reasons for sidecar, stub, single-run, runtime blocker, and failed gate paths.
- Unit and CLI tests for reported and blocked stability paths.

Out of scope:

- Retrying runtime blockers.
- Making network/auth unavailable runtime paths pass.
- Changing trigger prompts or hook semantics.
- Shipping evaluation harness artifacts in the plugin payload.

## Release Boundary

This feature changes repository evaluation tooling only. The Arbor plugin payload remains unchanged:

- `plugins/arbor/.codex-plugin/plugin.json`
- `plugins/arbor/hooks.json`
- `plugins/arbor/skills/arbor/`

## Design

- `evaluate_repeated_corpus` runs the existing corpus evaluator multiple times under `<work-root>/run-NNN`.
- Single-run reports remain unchanged unless the caller explicitly requests repeated runs.
- Stability uses a compact trigger signature:
  - scenario id;
  - trigger decision;
  - selected hook ids;
  - optional args.
- Stability is withheld unless every run is semantic-metric ready. Runtime blockers remain blockers and are not counted as stable abstentions.
- When reported, output includes run count, scenario count, stable scenario count, stability rate, and unstable scenario details.

## Test Plan

Unit tests:

- Matching repeated plugin runtime reports produce `reported=true` and `stability_rate=1.0`.
- Changed repeated plugin runtime decisions produce unstable scenario details.
- Sidecar repeated reports with clean hook execution still withhold stability because they are not real runtime labels.
- Runtime-blocked repeated reports withhold stability because semantic metric gates fail.

Scenario/CLI tests:

- `--all --repeat-runs 2 --trigger-adapter sidecar-baseline` emits repeated-run JSON and withholds stability.
- Default `--all` output remains the existing single-run report shape.

Regression checks:

- Existing hook execution-chain assertions remain unchanged.
- Plugin payload validation remains unchanged.

## Developer Response

### Changes

- Added `evaluate_repeated_corpus`, which runs the existing full-corpus evaluator under isolated `run-NNN` fixture roots.
- Added `--repeat-runs` for `--all`; single-scenario evaluation rejects repeat mode.
- Added trigger decision signatures for stability comparison:
  - decision;
  - sorted selected hooks;
  - optional args.
- Added `compute_repeated_runtime_stability`.
- Stability now reports only when:
  - adapter is `plugin-runtime-codex-exec`;
  - at least two runs exist;
  - every run reports semantic metrics through the existing gates;
  - every run contains the same scenario ids.
- Sidecar, stub, single-run, and runtime-blocker paths explicitly withhold stability.

### Validation

- `python3 -m unittest tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 24 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f20-pycache python3 -m py_compile scripts/evaluate_hook_triggers.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f20-repeat-stub --trigger-adapter plugin-runtime-stub --repeat-runs 2`: passed; repeated report emitted, stability withheld because the adapter is not real runtime.
- `python3 -m unittest tests/test_arbor_skill.py`: 136 tests passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f20-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios, 103/103 hook executions, outside-root leaks 0, unintended writes 0; semantic metrics remain unreported because the adapter is sidecar-backed.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-f20-runtime-smoke --trigger-adapter plugin-runtime-codex-exec`: passed; runtime returned `decision=ambiguous`, `hooks=[]`, and `reason=Plugin runtime unavailable: network_unavailable...`; no hook execution occurred.
- `python3 scripts/validate_plugin_install.py`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f20-full-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py scripts/probe_plugin_runtime.py tests/test_arbor_skill.py`: passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f20-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 136 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f20-coverage conda run -n arbor python -m coverage report`: total coverage 88%; `scripts/evaluate_hook_triggers.py` coverage 86%.

### Scenario Results

| Scenario | Expected | Actual | Status |
| --- | --- | --- | --- |
| Matching repeated gate-ready runtime reports | Report stability with `stability_rate=1.0` | Reported true, 1/1 scenarios stable | Pass |
| Changed repeated gate-ready runtime reports | Report unstable scenario details | Reported true, `H1-P001` unstable with per-run signatures | Pass |
| Repeated blocked runtime reports | Withhold stability | `not_ready_runs` records both blocked runs | Pass |
| Repeated sidecar/stub reports | Withhold stability | Stability `reported=false` because labels are not real runtime labels | Pass |
| Single-run default `--all` | Preserve existing output shape | Existing full-corpus report remains unchanged | Pass |

### Developer Notes

Feature 20 does not make the current environment's real runtime available. It adds the aggregation path needed for an online/authenticated environment to run repeated full-corpus stability evaluation without treating blocked runtime output as a stable semantic decision.

## Review Feedback

### Round 1 - 2026-05-03

#### Findings

| ID | Priority | Location | Result | Finding |
| --- | --- | --- | --- | --- |
| F20-R1-1 | P1 | `scripts/evaluate_hook_triggers.py:723-740` | Added | Keep gate-ready repeated stability compatible with default compact corpus reports. |

`evaluate_repeated_corpus` passes the caller's `include_details` flag through to each run and then computes stability from those run reports. The default CLI path uses `include_details=false`, so run scenarios are compact rows with `decision` and `hooks` fields, not full rows with `trigger_decision`. Sidecar, stub, and blocked runtime paths hide this because stability is withheld before signatures are read, but an online/authenticated gate-ready `plugin-runtime-codex-exec` repeated run will reach `trigger_decision_signature` and raise `KeyError: 'trigger_decision'` instead of reporting stability. Stability should either compute from compact rows or force detailed scenario rows internally before aggregation, and a regression should cover gate-ready repeated reports in the default compact shape.

#### Test Matrix

| Test category | Test cases / checks | Coverage | Passed | Pass rate | Notes |
| --- | ---: | --- | ---: | ---: | --- |
| Focused harness replay | 24 | Developer's repeated stability, scoring gate, CLI, and execution harness tests | 24 | 100% | Existing tests pass but do not cover gate-ready compact repeated reports. |
| Repeated stability adversarial probes | 6 | Gate-ready compact default shape, full matching runs, full changed runs, sidecar withheld, runtime-blocked withheld, single-run withheld | 5 | 83% | Gate-ready compact default shape raises `KeyError: 'trigger_decision'`. |
| Repeated stub CLI smoke | 1 | `--all --repeat-runs 2 --trigger-adapter plugin-runtime-stub` | 1 | 100% | Stability correctly withheld for stub labels. |
| Full unit regression | 136 | Arbor scripts, hooks, trigger adapters, plugin install, runtime probe, repeated stability, packaging, and metrics | 136 | 100% | No existing unit regression failed. |
| Runtime smoke via `plugin-runtime-codex-exec` | 1 | Real Codex exec path for `H1-P001` with isolated installed plugin | 1 | 100% | Current environment returned `network_unavailable`; semantic metrics remain withheld. |
| Sidecar baseline corpus replay | 150 scenarios / 103 hook executions | Existing Stage B harness and sidecar-ineligible gate behavior | 150 / 103 | 100% | Semantic metrics remain unreported because the adapter is sidecar-backed. |
| Static validation | 5 | `py_compile`, `ruff`, plugin install validation, standalone skill validate, packaged skill validate | 5 | 100% | All passed. |
| Coverage run | 1 | Full unittest coverage snapshot | 1 | 100% | Total coverage 88%; `scripts/evaluate_hook_triggers.py` 86%. |

#### Scenario Testing

| Scenario | Adapter / path | Expected behavior | Actual result | Status |
| --- | --- | --- | --- | --- |
| Gate-ready compact repeated reports | Synthetic repeated `plugin-runtime-codex-exec` reports with compact scenario rows matching default `--all --repeat-runs` output | Report stability or preserve enough signature fields for stability calculation | Raised `KeyError: 'trigger_decision'` | Fail |
| Gate-ready full matching reports | Synthetic repeated `plugin-runtime-codex-exec` reports with full scenario rows | Report `stability_rate=1.0` | Reported true, 1/1 stable | Pass |
| Gate-ready full changed reports | Synthetic repeated `plugin-runtime-codex-exec` reports with changed decision | Report unstable scenario details | Reported true, `stability_rate=0.0`, `H1-P001` unstable | Pass |
| Repeated sidecar reports | Synthetic sidecar repeated reports | Withhold stability because labels are not real plugin runtime labels | `reported=false`, reason requires real plugin runtime corpus runs | Pass |
| Repeated blocked runtime reports | Synthetic blocked `plugin-runtime-codex-exec` reports | Withhold stability because scoring gates are not ready | `reported=false`, `not_ready_runs` populated | Pass |
| Single real runtime run | Synthetic one-run `plugin-runtime-codex-exec` report | Withhold stability because at least two runs are required | `reported=false`, at-least-two-runs reason | Pass |
| Repeated stub CLI | `plugin-runtime-stub --repeat-runs 2` | Emit repeated report and withhold stability | Passed; `semantic_metrics_reported_runs=0`, stability withheld | Pass |
| Sidecar baseline full corpus | `sidecar-baseline --all` | Preserve execution-chain pass and keep semantic metrics unreported | 150/150 scenarios passed; 103/103 hook executions passed; outside-root leaks 0; unintended writes 0 | Pass |
| Real runtime smoke in current environment | `plugin-runtime-codex-exec` on `H1-P001` | Runtime blocker should withhold semantic metrics without executing hooks | `decision=ambiguous`, `hooks=[]`, `reason=Plugin runtime unavailable: network_unavailable...`; no hook execution | Pass |
| Plugin release boundary | Plugin install readiness and skill validation | Repeated evaluation tooling must not alter plugin payload | Plugin install validation and both quick validates passed | Pass |

#### Optimization Suggestions

| Area | Suggestion |
| --- | --- |
| Stability input shape | Make `trigger_decision_signature` accept both full scenario rows and compact rows, or have `evaluate_repeated_corpus` always compute stability from internal full-detail run results while still emitting compact output by default. |
| Regression coverage | Add a unit test that constructs two gate-ready compact repeated reports and asserts stability is reported instead of raising. A CLI-adjacent test with a mocked gate-ready runtime adapter would cover the default `--repeat-runs` path more directly. |
| Output contract | If compact repeated reports are expected to support later stability replay, include `optional_args` in `compact_scenario_result`; otherwise document that emitted compact rows are presentation-only and stability is computed before compaction. |

#### Round 1 Verdict

Needs changes. Feature 20's withheld paths and full-detail synthetic stability paths work, but the default repeated corpus output shape is incompatible with gate-ready stability reporting, which is the feature's core future online/runtime path.

## Developer Response - Round 1 Fix

### Changes

- Fixed `F20-R1-1` by making stability signatures compatible with both full scenario rows and default compact scenario rows.
- `trigger_decision_signature` now reads:
  - full rows from `trigger_decision`;
  - compact rows from `decision`, `hooks`, and `optional_args`.
- `compact_scenario_result` now includes `optional_args`, so compact repeated reports preserve every field needed for later stability replay.
- Added a gate-ready compact repeated-report regression that reproduces the review failure shape and asserts stability reports instead of raising.
- Added CLI/default-output coverage that confirms compact full-corpus rows preserve hook optional args.

### Validation

- `python3 -m unittest tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 25 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f20-r1-fix-pycache python3 -m py_compile scripts/evaluate_hook_triggers.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 137 tests passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f20-r1-fix-repeat-stub --trigger-adapter plugin-runtime-stub --repeat-runs 2`: passed; repeated report emitted, compact rows include `optional_args`, and stability remains withheld because the adapter is not real runtime.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f20-r1-fix-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios, 103/103 hook executions, outside-root leaks 0, unintended writes 0; compact rows include `optional_args`.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-f20-r1-fix-runtime-smoke --trigger-adapter plugin-runtime-codex-exec`: passed; runtime returned `decision=ambiguous`, `hooks=[]`, and `reason=Plugin runtime unavailable: network_unavailable...`; no hook execution occurred.
- `python3 scripts/validate_plugin_install.py`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f20-r1-fix-full-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py scripts/probe_plugin_runtime.py tests/test_arbor_skill.py`: passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f20-r1-fix-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 137 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f20-r1-fix-coverage conda run -n arbor python -m coverage report`: total coverage 88%; `scripts/evaluate_hook_triggers.py` coverage 86%.

### Finding Closure

| Finding | Status | Evidence |
| --- | --- | --- |
| F20-R1-1 | Addressed | Gate-ready compact repeated reports now produce `reported=true` stability output instead of raising `KeyError`; compact rows preserve `optional_args` for replay. |

### Optimization Closure

| Suggestion | Status | Evidence |
| --- | --- | --- |
| Stability input shape | Addressed | `trigger_decision_signature` accepts full and compact rows. |
| Regression coverage | Addressed | Added gate-ready compact repeated-report regression plus compact output optional-args assertion. |
| Output contract | Addressed | `compact_scenario_result` now emits `optional_args`, making compact rows replayable for stability signatures. |

### Round 2 - 2026-05-03

#### Findings

| ID | Priority | Location | Result | Finding |
| --- | --- | --- | --- | --- |
| F20-R2 | - | - | No new findings | The Round 1 compact repeated-report failure is closed. No new stability, gate, compact-output, runtime-blocker, sidecar, or plugin payload regression was found. |

#### Test Matrix

| Test category | Test cases / checks | Coverage | Passed | Pass rate | Notes |
| --- | ---: | --- | ---: | ---: | --- |
| Focused harness replay | 25 | Repeated stability, compact signature regression, scoring gate, CLI, and execution harness tests | 25 | 100% | Includes the new gate-ready compact repeated-report regression. |
| Repeated stability adversarial probes | 7 | Original compact failure replay, compact optional-args change, full matching, full changed, sidecar withheld, runtime-blocked withheld, single-run withheld | 7 | 100% | Original failure now reports stability instead of raising. |
| Repeated stub CLI smoke | 1 | `--all --repeat-runs 2 --trigger-adapter plugin-runtime-stub` | 1 | 100% | Compact rows include `optional_args`; stability remains withheld for stub labels. |
| Full unit regression | 137 | Arbor scripts, hooks, trigger adapters, plugin install, runtime probe, repeated stability, packaging, and metrics | 137 | 100% | No unit regression failed. |
| Runtime smoke via `plugin-runtime-codex-exec` | 1 | Real Codex exec path for `H1-P001` with isolated installed plugin | 1 | 100% | Current environment returned `network_unavailable`; semantic metrics remain withheld. |
| Sidecar baseline corpus replay | 150 scenarios / 103 hook executions | Existing Stage B harness and sidecar-ineligible gate behavior | 150 / 103 | 100% | Compact rows now include `optional_args`; semantic metrics remain unreported because the adapter is sidecar-backed. |
| Static validation | 5 | `py_compile`, `ruff`, plugin install validation, standalone skill validate, packaged skill validate | 5 | 100% | All passed. |
| Coverage run | 1 | Full unittest coverage snapshot | 1 | 100% | Total coverage 88%; `scripts/evaluate_hook_triggers.py` 86%. |

#### Scenario Testing

| Scenario | Adapter / path | Expected behavior | Actual result | Status |
| --- | --- | --- | --- | --- |
| F20-R1 gate-ready compact repeated replay | Synthetic repeated `plugin-runtime-codex-exec` reports with compact rows | Report stability without requiring `trigger_decision` | `reported=true`, `run_count=2`, `stability_rate=1.0`, no unstable scenarios | Pass |
| Compact optional-args instability | Synthetic compact `H3-P002` repeated reports with changed `--doc` args | Detect optional-args differences as unstable | `reported=true`, `stability_rate=0.0`, unstable signatures include both optional-args values | Pass |
| Gate-ready full matching reports | Synthetic repeated full rows | Preserve full-row stability behavior | `reported=true`, `stability_rate=1.0` | Pass |
| Gate-ready full changed reports | Synthetic repeated full rows with changed decision | Preserve unstable decision reporting | `reported=true`, `stability_rate=0.0`, `H1-P001` unstable | Pass |
| Repeated sidecar reports | Synthetic sidecar repeated reports | Withhold stability because labels are not real plugin runtime labels | `reported=false`, real-runtime-required reason | Pass |
| Repeated blocked runtime reports | Synthetic blocked `plugin-runtime-codex-exec` repeated reports | Withhold stability because scoring gates are not ready | `reported=false`, `not_ready_runs` populated | Pass |
| Single real runtime run | Synthetic one-run `plugin-runtime-codex-exec` report | Withhold stability because at least two runs are required | `reported=false`, at-least-two-runs reason | Pass |
| Repeated stub CLI | `plugin-runtime-stub --repeat-runs 2` | Emit repeated report, include `optional_args`, and withhold stability | Passed; compact rows include `optional_args`; `semantic_metrics_reported_runs=0` | Pass |
| Sidecar baseline full corpus | `sidecar-baseline --all` | Preserve execution-chain pass and keep semantic metrics unreported | 150/150 scenarios passed; 103/103 hook executions passed; outside-root leaks 0; unintended writes 0 | Pass |
| Real runtime smoke in current environment | `plugin-runtime-codex-exec` on `H1-P001` | Runtime blocker should withhold semantic metrics without executing hooks | `decision=ambiguous`, `hooks=[]`, `reason=Plugin runtime unavailable: network_unavailable...`; no hook execution | Pass |
| Plugin release boundary | Plugin install readiness and skill validation | Repeated evaluation fix must not alter plugin payload | Plugin install validation and both quick validates passed | Pass |

#### Optimization Suggestions

| Area | Suggestion |
| --- | --- |
| Compact replay contract | Keep `optional_args` in compact scenario rows as part of the repeated stability replay contract. |
| Stability regression | Keep the gate-ready compact regression near `compute_repeated_runtime_stability`; it covers the future online runtime path that local blocked smoke cannot exercise. |
| Output compatibility | If compact row fields change again, update both `compact_scenario_result` and `trigger_decision_signature` together to avoid drift between emitted reports and replay logic. |

#### Round 2 Verdict

Accepted after re-review. `F20-R1-1` is closed, and no adjacent repeated-stability regression was found.
