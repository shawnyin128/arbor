# Feature 19 Review: Semantic Metric Formulas

## Development Target

Compute semantic trigger metrics for real plugin runtime trigger output, but only after the Feature 18 scoring gates pass.

This feature turns the gate-ready handoff into actual metric reporting. It does not make blocked runtime runs look successful, and it does not include evaluation tooling in the Arbor plugin payload.

## Scope

In scope:

- Per-hook precision and recall.
- `NONE` false-positive rate.
- Near-miss false-positive rate for `NM-*` scenarios.
- Ambiguous-case acceptance.
- Multi-hook required recall and exact-required rate.
- Failed scenario details for missing required hooks, forbidden hooks, and unexpected hooks.
- A stability placeholder that remains unreported until repeated real runtime runs exist.

Out of scope:

- Repeated-run stability computation.
- Changing runtime trigger prompts.
- Changing scenario sidecar semantics.
- Changing hook execution assertions.
- Shipping the evaluation harness or review corpus inside the plugin payload.

## Release Boundary

The metric harness is repository evaluation tooling, not product payload.

Do not ship these files in the Arbor plugin payload:

- `scripts/evaluate_hook_triggers.py`
- `scripts/simulated_dispatcher.py`
- `scripts/eval_fixtures.py`
- `docs/reviews/hook-trigger-scenarios.md`
- `docs/reviews/hook-trigger-scenarios.json`
- `docs/reviews/features/*.md`

The plugin payload remains:

- `plugins/arbor/.codex-plugin/plugin.json`
- `plugins/arbor/hooks.json`
- `plugins/arbor/skills/arbor/`

## Formula Summary

- Hook precision: selected hook is a true positive when it is required or optional for the scenario; otherwise it is a false positive.
- Hook recall: required hook is counted in recall only for non-agent-judgment scenarios.
- Optional hooks: acceptable for precision, not required for recall.
- Runtime blockers: excluded before formulas run because the runtime availability gate fails.
- `NONE` false positive: a `NONE` scenario returns `trigger` or selects any hook.
- Near-miss false positive: an `NM-*` scenario returns `trigger` or selects any hook.
- Ambiguous acceptance: an ambiguous/agent-judgment scenario uses an allowed decision and avoids forbidden or unexpected hooks.
- Multi-hook required recall: selected required hooks divided by total required hooks across multi-hook scenarios.
- Multi-hook exact-required rate: raw required hooks must actually be selected; allowed ambiguous abstention is accepted separately but is not an exact required-hook match.
- Stability: intentionally unreported until repeated real runtime runs are available.

## Implementation Summary

- Added `compute_semantic_metrics`.
- Added `scenario_semantic_outcome`.
- Updated `semantic_metric_status` so `reported=true` only when all gates pass.
- Added tests for gate-ready metric reporting and semantic failures.
- Added a release-boundary regression test proving evaluation harness artifacts are not present in `plugins/arbor`.

## Test Plan

Unit tests:

- Gate-ready synthetic plugin runtime results report metrics.
- Wrong hook selection records hook false positives and missing required hooks.
- `NONE` false positives are counted.
- Stability remains unreported.

Regression tests:

- Sidecar baseline reports remain metric-ineligible.
- Runtime blocker reports remain unscored.
- Existing hook execution-chain summary remains unchanged.
- Plugin payload still excludes evaluation scripts, scenario corpus, and review docs.

## Developer Validation

- `python3 -m unittest tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 18 tests passed.
- `python3 -m unittest tests.test_arbor_skill.ArborPluginPackagingTests tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 23 tests passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 130 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f19-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py scripts/probe_plugin_runtime.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f19-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios, 103/103 hook executions, outside-root leaks 0, unintended writes 0; semantic metrics remain unreported because the adapter is sidecar-backed.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-f19-runtime-smoke --trigger-adapter plugin-runtime-codex-exec`: passed; runtime returned `decision=ambiguous`, `hooks=[]`, `reason=Plugin runtime unavailable: network_unavailable...`; no semantic metrics reported for the single blocked runtime smoke.
- `python3 scripts/validate_plugin_install.py`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f19-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 130 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f19-coverage conda run -n arbor python -m coverage report`: total coverage 87%; `scripts/evaluate_hook_triggers.py` coverage 86%.

## Developer Response

Feature 19 is implemented and ready for review. Full validation should be run after review feedback, and stability should stay deferred until repeated real runtime corpus runs are possible.

## Review Feedback

### Round 1 - 2026-05-03

#### Findings

| ID | Priority | Location | Result | Finding |
| --- | --- | --- | --- | --- |
| F19-R1-1 | P2 | `scripts/evaluate_hook_triggers.py:454-461` | Added | Do not count ambiguous abstentions as exact-required multi-hook matches. |

`compute_semantic_metrics` clears `missing_required_hooks` for allowed ambiguous decisions, then reuses that cleared field for `multi_hook_exact_required_rate`. In a synthetic `M-P001` result with `decision=ambiguous` and no selected hooks, the metric reported `multi_hook_required_recall=0.0` but `multi_hook_exact_required_rate=1.0`. That makes an abstention with no required hook selected look like an exact required-hook match. Exact-required scoring should use raw required hook presence, not the ambiguous-acceptance shortcut.

#### Test Matrix

| Test category | Test cases / checks | Coverage | Passed | Pass rate | Notes |
| --- | ---: | --- | ---: | ---: | --- |
| Focused packaging and harness replay | 23 | Plugin payload boundary plus semantic metric harness tests | 23 | 100% | `ArborPluginPackagingTests` plus `HookTriggerExecutionHarnessTests`. |
| Formula adversarial probes | 3 | Ambiguous required multi-hook abstention, required-plus-optional multi-hook trigger, NONE/NM false positives | 2 | 67% | Ambiguous abstention incorrectly counted as exact-required match. |
| Full unit regression | 130 | Arbor script, hook, trigger adapter, plugin install, runtime probe, packaging, and metric tests | 130 | 100% | No existing unit regression failed. |
| Runtime smoke via `plugin-runtime-codex-exec` | 1 | Real Codex exec path for `H1-P001` with isolated installed plugin | 1 | 100% | Runtime classified as `network_unavailable`, `decision=ambiguous`, `hooks=[]`; metrics remain unreported for blocked smoke. |
| Sidecar baseline corpus replay | 150 scenarios / 103 hook executions | Existing Stage B harness and sidecar-ineligible gate behavior | 150 / 103 | 100% | Semantic metrics remain unreported because adapter is sidecar-backed. |
| Static validation | 5 | `py_compile`, `ruff`, plugin install validation, standalone skill validate, packaged skill validate | 5 | 100% | All passed. |
| Coverage run | 1 | Full unittest coverage snapshot | 1 | 100% | Total coverage 87%; `scripts/evaluate_hook_triggers.py` 86%. |

#### Scenario Testing

| Scenario | Adapter / path | Expected behavior | Actual result | Status |
| --- | --- | --- | --- | --- |
| Ambiguous required multi-hook abstention | Synthetic `M-P001`, `decision=ambiguous`, `hooks=[]` | Ambiguous can be accepted, but exact-required rate should not count as an exact required-hook hit | `multi_hook_required_recall=0.0`, `multi_hook_exact_required_rate=1.0` | Fail |
| Required plus optional multi-hook trigger | Synthetic `M-P001`, required H1 plus optional H2 selected | Count required recall and exact-required as successful | Both required recall and exact-required rate were 1.0 | Pass |
| NONE and near-miss false positives | Synthetic `N-P001` and `NM-P001` trigger selections | Count false positives in NONE and NM rates | Both false-positive rates were 1.0 and scenarios were listed as failures | Pass |
| Sidecar baseline full corpus | `sidecar-baseline --all` | Preserve execution-chain pass and keep semantic metrics unreported | 150/150 scenarios passed; semantic metrics withheld by adapter gate | Pass |
| Real runtime smoke in current environment | `plugin-runtime-codex-exec` on `H1-P001` | Runtime blocker should withhold semantic metrics | `network_unavailable` blocker; no hook execution | Pass |
| Release boundary | Plugin payload inspection and install validation | Evaluation harness, sidecar corpus, and review docs stay outside plugin payload | Plugin payload validation passed | Pass |

#### Optimization Suggestions

| Area | Suggestion |
| --- | --- |
| Multi-hook exact formula | Compute exact-required from raw `expected_hooks <= selected_hooks` and forbidden/unexpected hook cleanliness. Do not reuse `outcome["missing_required_hooks"]` after ambiguous acceptance clears it. |
| Regression coverage | Add a focused test for `M-P001` with `decision=ambiguous`, `hooks=[]`; assert ambiguous acceptance can pass separately while `multi_hook_exact_required_rate` is 0.0. |
| Metric separation | Keep ambiguous acceptance and exact required-hook matching as separate dimensions. An allowed abstention should not be labeled as an exact hook-selection match. |

#### Round 1 Verdict

Needs changes. The gate and release-boundary behavior replayed cleanly, but the multi-hook exact-required formula currently overstates exact hook-selection quality for allowed ambiguous abstentions.

## Developer Response - Round 1 Fix

### Changes

- Fixed `F19-R1-1` by separating ambiguous acceptance from exact required-hook matching.
- `scenario_semantic_outcome` now exposes both:
  - `raw_missing_required_hooks`: the actual required hooks not selected by the runtime;
  - `missing_required_hooks`: the scenario-failure field after allowed ambiguous abstention is applied.
- `multi_hook_exact_required_rate` now uses `raw_missing_required_hooks`, forbidden-hook cleanliness, and unexpected-hook cleanliness. It no longer reuses the ambiguous-acceptance shortcut.
- Added focused regression coverage for synthetic `M-P001` with `decision=ambiguous` and `hooks=[]`.
- The regression asserts that ambiguous acceptance can pass while `multi_hook_required_recall=0.0` and `multi_hook_exact_required_rate=0.0`.

### Validation

- `python3 -m unittest tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 19 tests passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 131 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f19-r1-fix-pycache python3 -m py_compile scripts/evaluate_hook_triggers.py tests/test_arbor_skill.py`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f19-r1-fix-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py scripts/probe_plugin_runtime.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f19-r1-fix-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios, 103/103 hook executions, outside-root leaks 0, unintended writes 0; semantic metrics remain unreported because the adapter is sidecar-backed.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-f19-r1-fix-runtime-smoke --trigger-adapter plugin-runtime-codex-exec`: passed; runtime returned `decision=ambiguous`, `hooks=[]`, and `reason=Plugin runtime unavailable: network_unavailable...`; semantic metrics remain unreported for the blocked smoke.
- `python3 scripts/validate_plugin_install.py`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f19-r1-fix-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 131 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f19-r1-fix-coverage conda run -n arbor python -m coverage report`: total coverage 88%; `scripts/evaluate_hook_triggers.py` coverage 87%.

### Finding Closure

| Finding | Status | Evidence |
| --- | --- | --- |
| F19-R1-1 | Addressed | `multi_hook_exact_required_rate` now uses raw required-hook presence; ambiguous abstention on `M-P001` is accepted separately but no longer counted as an exact required-hook match. |

### Round 2 - 2026-05-03

#### Findings

| ID | Priority | Location | Result | Finding |
| --- | --- | --- | --- | --- |
| F19-R2 | - | - | No new findings | The Round 1 formula issue is closed. No new blocker or regression was found in replay, adjacent control probes, harness replay, runtime smoke, plugin validation, or static checks. |

#### Test Matrix

| Test category | Test cases / checks | Coverage | Passed | Pass rate | Notes |
| --- | ---: | --- | ---: | ---: | --- |
| Focused harness replay | 19 | Hook trigger execution harness and semantic metric formula regression tests | 19 | 100% | Includes the new ambiguous-abstention exact-required regression. |
| Focused packaging and harness replay | 24 | Plugin payload boundary plus semantic metric harness tests | 24 | 100% | `ArborPluginPackagingTests` plus `HookTriggerExecutionHarnessTests`. |
| Formula adversarial probes | 4 | Original failing ambiguous abstention plus required+optional, optional-only, and both-required multi-hook controls | 4 | 100% | Original `M-P001` abstention now reports `multi_hook_exact_required_rate=0.0`. |
| Full unit regression | 131 | Arbor scripts, hooks, trigger adapters, plugin install, runtime probe, packaging, and metrics | 131 | 100% | No unit regression failed. |
| Runtime smoke via `plugin-runtime-codex-exec` | 1 | Real Codex exec path for `H1-P001` with isolated installed plugin | 1 | 100% | Current environment returned `network_unavailable`; the adapter withheld semantic metrics through the blocker path. |
| Sidecar baseline corpus replay | 150 scenarios / 103 hook executions | Existing Stage B harness and sidecar-ineligible gate behavior | 150 / 103 | 100% | Semantic metrics remain unreported because the adapter is sidecar-backed. |
| Static validation | 5 | `py_compile`, `ruff`, plugin install validation, standalone skill validate, packaged skill validate | 5 | 100% | All passed. The first py_compile attempt used a stale script name and was rerun with the current file list. |
| Coverage run | 1 | Full unittest coverage snapshot | 1 | 100% | Total coverage 88%; `scripts/evaluate_hook_triggers.py` 87%. |

#### Scenario Testing

| Scenario | Adapter / path | Expected behavior | Actual result | Status |
| --- | --- | --- | --- | --- |
| F19-R1 ambiguous required multi-hook abstention replay | Synthetic `M-P001`, `decision=ambiguous`, `hooks=[]` | Scenario can pass through allowed ambiguous abstention, but exact-required rate must not count it as an exact hook-selection hit | `passed=true`, `missing_required_hooks=[]`, `raw_missing_required_hooks=["arbor.session_startup_context"]`, `multi_hook_required_recall=0.0`, `multi_hook_exact_required_rate=0.0` | Pass |
| Required plus optional multi-hook control | Synthetic `M-P001`, required H1 plus optional H2 selected | Required recall and exact-required rate both succeed | `multi_hook_required_recall=1.0`, `multi_hook_exact_required_rate=1.0` | Pass |
| Optional-only missing-required control | Synthetic `M-P001`, only optional H2 selected | Missing required H1 should fail the scenario and keep exact-required rate at 0.0 | `passed=false`, `raw_missing_required_hooks=["arbor.session_startup_context"]`, `multi_hook_exact_required_rate=0.0` | Pass |
| Both-required multi-hook control | Synthetic `M-P002`, H1 and H2 selected | Both required hooks should count as exact-required | `multi_hook_required_recall=1.0`, `multi_hook_exact_required_rate=1.0` | Pass |
| Sidecar baseline full corpus | `sidecar-baseline --all` | Preserve execution-chain pass and keep semantic metrics unreported | 150/150 scenarios passed; 103/103 hook executions passed; outside-root leaks 0; unintended writes 0; semantic metrics withheld by adapter gate | Pass |
| Real runtime smoke in current environment | `plugin-runtime-codex-exec` on `H1-P001` | Runtime blocker should withhold semantic metrics without executing hooks | `decision=ambiguous`, `hooks=[]`, `reason=Plugin runtime unavailable: network_unavailable...`; no hook execution | Pass |
| Plugin release boundary | Plugin install readiness and skill validation | Evaluation harness and review tooling stay outside plugin payload; packaged hooks remain valid | Plugin install validation and both quick validates passed | Pass |

#### Optimization Suggestions

| Area | Suggestion |
| --- | --- |
| Metric field semantics | Keep `raw_missing_required_hooks` and `missing_required_hooks` documented as separate fields: raw metric input versus scenario-failure presentation after allowed ambiguous abstention. |
| Future repeated runtime runs | Do not report stability until repeated real runtime corpus runs are available; the current smoke still exercises only the blocker path in this environment. |
| Regression shape | Keep the ambiguous-abstention regression close to `compute_semantic_metrics` so future metric refactors cannot silently merge scenario acceptance and exact hook-selection scoring again. |

#### Round 2 Verdict

Accepted after re-review. `F19-R1-1` is closed, and no adjacent metric, packaging, harness, runtime-blocker, or static-validation regression was found.

## Developer Response - Round 2 Optimizations

### Changes

- Addressed the accepted optimization suggestions without changing the metric gates or plugin payload.
- Documented and preserved the distinction between `raw_missing_required_hooks` and `missing_required_hooks`:
  - `raw_missing_required_hooks` is the metric input for exact required-hook scoring;
  - `missing_required_hooks` is the scenario-failure presentation field after allowed ambiguous abstention is applied.
- Added explicit numerator/denominator fields for multi-hook metric replay:
  - `multi_hook_required_selected_count`;
  - `multi_hook_required_total`;
  - `multi_hook_exact_required_count`;
  - `multi_hook_scenario_count`.
- Added `raw_missing_required_hooks` to failed scenario details so reviewers can inspect raw scoring input separately from presentation output.
- Kept stability frozen as `reported=false` until repeated real runtime corpus runs exist.

### Validation

- `python3 -m unittest tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 19 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f19-r2-opt-pycache python3 -m py_compile scripts/evaluate_hook_triggers.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 131 tests passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f19-r2-opt-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios, 103/103 hook executions, outside-root leaks 0, unintended writes 0; semantic metrics remain unreported because the adapter is sidecar-backed.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-f19-r2-opt-runtime-smoke --trigger-adapter plugin-runtime-codex-exec`: passed; runtime returned `decision=ambiguous`, `hooks=[]`, and `reason=Plugin runtime unavailable: network_unavailable...`; semantic metrics remain unreported for the blocked smoke.
- `python3 scripts/validate_plugin_install.py`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f19-r2-opt-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 131 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f19-r2-opt-coverage conda run -n arbor python -m coverage report`: total coverage 88%; `scripts/evaluate_hook_triggers.py` coverage 87%.

### Optimization Closure

| Suggestion | Status | Evidence |
| --- | --- | --- |
| Metric field semantics | Addressed | Raw missing-required fields are emitted in outcomes and failed scenario details; docs describe raw metric input versus presentation output. |
| Future repeated runtime runs | Addressed | Stability remains `reported=false`; final delivery now states that stability needs repeated real runtime corpus runs. |
| Regression shape | Addressed | The ambiguous-abstention regression now asserts raw/presentation separation plus multi-hook numerator and denominator fields close to `compute_semantic_metrics`. |

### Round 3 - 2026-05-03

#### Findings

| ID | Priority | Location | Result | Finding |
| --- | --- | --- | --- | --- |
| F19-R3 | - | - | No new findings | The Round 2 optimization feedback replays cleanly. The metric output now exposes raw missing-required inputs, presentation missing-required fields, and multi-hook numerator/denominator fields without changing gates or plugin payload. |

#### Test Matrix

| Test category | Test cases / checks | Coverage | Passed | Pass rate | Notes |
| --- | ---: | --- | ---: | ---: | --- |
| Focused harness replay | 19 | Hook trigger execution harness and semantic metric formula regression tests | 19 | 100% | Confirms raw/presentation field separation and multi-hook metric counts. |
| Focused packaging and harness replay | 24 | Plugin payload boundary plus semantic metric harness tests | 24 | 100% | Confirms optimization did not alter plugin payload readiness. |
| Optimization replay probes | 4 | Ambiguous abstention counts, failed-scenario raw detail, both-required exact counts, stability reporting gate | 4 | 100% | All requested optimization semantics replayed. |
| Full unit regression | 131 | Arbor scripts, hooks, trigger adapters, plugin install, runtime probe, packaging, and metrics | 131 | 100% | No unit regression failed. |
| Runtime smoke via `plugin-runtime-codex-exec` | 1 | Real Codex exec path for `H1-P001` with isolated installed plugin | 1 | 100% | Current environment returned `network_unavailable`; semantic metrics remain withheld. |
| Sidecar baseline corpus replay | 150 scenarios / 103 hook executions | Existing Stage B harness and sidecar-ineligible gate behavior | 150 / 103 | 100% | Semantic metrics remain unreported because the adapter is sidecar-backed. |
| Static validation | 5 | `py_compile`, `ruff`, plugin install validation, standalone skill validate, packaged skill validate | 5 | 100% | All passed. |
| Coverage run | 1 | Full unittest coverage snapshot | 1 | 100% | Total coverage 88%; `scripts/evaluate_hook_triggers.py` 87%. |

#### Scenario Testing

| Scenario | Adapter / path | Expected behavior | Actual result | Status |
| --- | --- | --- | --- | --- |
| Ambiguous abstention metric replay | Synthetic `M-P001`, `decision=ambiguous`, `hooks=[]` | Keep scenario accepted while raw required miss remains visible and exact-required count stays 0 | `passed=true`, `raw_missing_required_hooks=["arbor.session_startup_context"]`, `missing_required_hooks=[]`, `multi_hook_exact_required_count=0`, `multi_hook_exact_required_rate=0.0` | Pass |
| Failed scenario raw detail | Synthetic `H2-P001` with wrong H1 hook selected | Failed scenario details should include both raw and presentation missing-required fields | `failed_scenarios[0]` includes `raw_missing_required_hooks=["arbor.in_session_memory_hygiene"]` and matching `missing_required_hooks` | Pass |
| Both-required numerator/denominator replay | Synthetic `M-P002` with H1 and H2 selected | Multi-hook numerator and denominator fields should make exact-required replay auditable | `multi_hook_required_selected_count=2`, `multi_hook_required_total=2`, `multi_hook_exact_required_count=1`, `multi_hook_scenario_count=1` | Pass |
| Stability freeze after semantic readiness | Synthetic clean `plugin-runtime-codex-exec` semantic-ready metrics | Stability should remain unreported until repeated real runtime corpus runs exist | `metrics.stability.reported=false` with repeated-runtime reason | Pass |
| Sidecar baseline full corpus | `sidecar-baseline --all` | Preserve execution-chain pass and keep semantic metrics unreported | 150/150 scenarios passed; 103/103 hook executions passed; outside-root leaks 0; unintended writes 0 | Pass |
| Real runtime smoke in current environment | `plugin-runtime-codex-exec` on `H1-P001` | Runtime blocker should withhold semantic metrics without executing hooks | `decision=ambiguous`, `hooks=[]`, `reason=Plugin runtime unavailable: network_unavailable...`; no hook execution | Pass |
| Plugin release boundary | Plugin install readiness and skill validation | Optimization must not add evaluation tooling to plugin payload | Plugin install validation and both quick validates passed | Pass |

#### Optimization Suggestions

| Area | Suggestion |
| --- | --- |
| Metric consumers | Treat `raw_missing_required_hooks` as the canonical scoring/audit input; use `missing_required_hooks` only for scenario pass/fail presentation after allowed ambiguous abstention. |
| Report interpretation | Present `multi_hook_required_selected_count`, `multi_hook_required_total`, `multi_hook_exact_required_count`, and `multi_hook_scenario_count` with the rates in any future human-facing metric report. |
| Stability | Keep the current `reported=false` behavior until repeated real runtime corpus runs are available and comparable. |

#### Round 3 Verdict

Accepted. The Round 2 optimization suggestions are addressed and replayed cleanly; no new review finding was added.
