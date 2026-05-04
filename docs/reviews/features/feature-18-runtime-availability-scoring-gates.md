# Feature 18 Review: Runtime Availability And Semantic Scoring Gates

## Development Target

Add explicit gates before Arbor reports semantic trigger metrics from a real plugin runtime. The goal is to prevent environment blockers, runtime contract blockers, sidecar-backed labels, stub abstentions, or hook execution failures from being counted as semantic precision/recall evidence.

This feature does not implement semantic metric formulas. It only decides whether later metric computation is allowed to proceed.

## Scope

In scope:

- Add semantic scoring readiness gates to full-corpus reports.
- Keep `semantic_metrics.reported=false`.
- Add `semantic_metrics.ready_for_semantic_metrics`.
- Gate readiness on adapter eligibility, runtime availability, and hook execution cleanliness.
- Count runtime blocker decisions separately from semantic `NONE`.
- Preserve existing sidecar-baseline execution-chain reporting.

Out of scope:

- Computing H1/H2/H3 precision or recall.
- Computing `NONE` or near-miss false-positive rates.
- Computing ambiguous-case, multi-hook, or stability metrics.
- Changing trigger prompt behavior.
- Changing hook execution assertions.

## Gate Contract

`summary.semantic_metrics` now has this shape:

```json
{
  "reported": false,
  "ready_for_semantic_metrics": false,
  "reason": "Semantic trigger metrics are withheld until every scoring gate passes.",
  "gates": {
    "adapter_eligibility": {},
    "runtime_availability": {},
    "hook_execution": {}
  }
}
```

Gate meanings:

- `adapter_eligibility`: only `plugin-runtime-codex-exec` is eligible for real semantic scoring.
- `runtime_availability`: runtime blocker decisions are reported as blockers and excluded from scoring denominators.
- `hook_execution`: semantic scoring cannot proceed if selected hooks fail packet, outside-root, or unintended-write assertions.

## Implementation Summary

- Added `runtime_blocker_reason` to identify runtime blocker decisions from the Feature 17 blocker contract.
- Added `adapter_eligibility_gate`, `runtime_availability_gate`, and `hook_execution_gate`.
- Updated `semantic_metric_status` to return gate details and readiness.
- Updated corpus summaries to compute semantic gate status after hook execution summary fields are available.
- Added tests for sidecar ineligibility, plugin runtime blocker gating, and clean synthetic readiness.
- Added a no-results guard so an empty runtime corpus cannot accidentally pass the availability gate.

## Test Plan

Unit tests:

- Sidecar baseline corpus remains ineligible for semantic metrics.
- Plugin runtime blocker decisions produce `runtime_availability.status=blocked`.
- Runtime blocker counts and blocked scenario ids are visible.
- Synthetic clean plugin runtime results can set `ready_for_semantic_metrics=true` while formulas remain unreported.
- Empty plugin runtime results produce `runtime_availability.status=no_results`.

Scenario tests:

- Full sidecar baseline corpus remains passing.
- Mocked full plugin-runtime corpus with blocker decisions runs without hook execution and with semantic readiness false.

Regression tests:

- Existing hook execution-chain summary fields remain present.
- Existing `semantic_metrics.reported=false` invariant remains true.

## Developer Validation

- `python3 -m unittest tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 17 tests passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 128 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f18-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py scripts/probe_plugin_runtime.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f18-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios, 103/103 hook executions, outside-root leaks 0, unintended writes 0; `semantic_metrics.reported=false`, `ready_for_semantic_metrics=false`, adapter gate ineligible, hook execution gate clean.
- `python3 scripts/validate_plugin_install.py`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f18-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 128 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f18-coverage conda run -n arbor python -m coverage report`: total coverage 87%; `scripts/evaluate_hook_triggers.py` coverage 83%.

## Developer Response

Feature 18 is implemented and ready for review. The next feature should compute semantic metrics only when these gates pass.

## Review Feedback

### Round 1 - 2026-05-03

#### Findings

| ID | Priority | Location | Result | Finding |
| --- | --- | --- | --- | --- |
| F18-R1 | - | - | No new findings | Runtime availability and semantic scoring readiness gates behaved as scoped. |

No new code review findings were added. The implementation preserves `semantic_metrics.reported=false`, keeps sidecar and stub adapters ineligible, blocks readiness on runtime blockers and hook execution failures, and allows readiness only for clean synthetic `plugin-runtime-codex-exec` results.

#### Test Matrix

| Test category | Test cases / checks | Coverage | Passed | Pass rate | Notes |
| --- | ---: | --- | ---: | ---: | --- |
| Focused hook execution harness replay | 17 | Full-corpus summary, adapter gates, runtime blocker gates, empty-results guard, CLI behavior | 17 | 100% | `HookTriggerExecutionHarnessTests`. |
| Manual gate probes | 6 | Sidecar ineligible, stub ineligible, runtime blocked, hook failed, empty results, clean readiness | 6 | 100% | Confirmed `reported=false` for every probe. |
| Full unit regression | 128 | Arbor script, hook, trigger adapter, plugin install, runtime probe, and harness tests | 128 | 100% | No existing unit regression failed. |
| Runtime smoke via `plugin-runtime-codex-exec` | 1 | Real Codex exec path for `H1-P001` with isolated installed plugin | 1 | 100% | Runtime classified as `network_unavailable`, `decision=ambiguous`, `hooks=[]`, no hook execution. |
| Sidecar baseline corpus replay | 150 scenarios / 103 hook executions | Existing Stage B harness and hook execution baseline plus new semantic gate shape | 150 / 103 | 100% | Adapter gate ineligible, runtime gate not applicable, hook execution gate clean. |
| Static validation | 5 | `py_compile`, `ruff`, plugin install validation, standalone skill validate, packaged skill validate | 5 | 100% | All passed. |
| Coverage run | 1 | Full unittest coverage snapshot | 1 | 100% | Total coverage 87%; `scripts/evaluate_hook_triggers.py` 83%. |

#### Scenario Testing

| Scenario | Adapter / path | Expected behavior | Actual result | Status |
| --- | --- | --- | --- | --- |
| Sidecar baseline full corpus | `sidecar-baseline --all` | Preserve 150-scenario execution-chain pass while blocking semantic readiness | 150/150 scenarios passed; adapter gate `ineligible`; `ready_for_semantic_metrics=false` | Pass |
| Stub adapter eligibility | Direct `semantic_metric_status` probe | Stub should not be metric-eligible | Adapter gate `ineligible`; readiness false | Pass |
| Runtime blocker corpus | Mocked `plugin-runtime-codex-exec` blocker decisions | Runtime blockers should be counted separately and block readiness | Runtime gate `blocked`; blocker count visible; readiness false | Pass |
| Hook execution failure | Synthetic clean runtime result plus failed execution summary | Hook failures should block semantic readiness | Hook execution gate `failed`; readiness false | Pass |
| Empty runtime results | Direct `semantic_metric_status` probe | Empty plugin runtime corpus should not pass availability | Runtime gate `no_results`; readiness false | Pass |
| Clean runtime readiness handoff | Synthetic clean plugin runtime result plus clean execution summary | Readiness can be true while formulas remain unreported | `ready_for_semantic_metrics=true`; `reported=false` | Pass |
| Real runtime smoke in current environment | `plugin-runtime-codex-exec` on `H1-P001` | Network/auth/runtime blocker should not be semantic `NONE` or execute hooks | `decision=ambiguous`, `hooks=[]`, reason `network_unavailable`; no hook execution | Pass |

#### Optimization Suggestions

| Area | Suggestion |
| --- | --- |
| Metric formula feature | Preserve this readiness contract as the only entry point for precision, recall, false-positive, ambiguity, multi-hook, and stability formulas. |
| Runtime blocker taxonomy | Keep using the normalized blocker reason strings in `runtime_availability.blocker_counts`; avoid mixing them into `decision_counts.none` when metrics are added. |
| Report readability | When semantic formulas are implemented, keep `reported`, `ready_for_semantic_metrics`, and `gates` in the report so blocked runs remain auditable. |

#### Round 1 Verdict

Accepted after review. Feature 18 correctly adds semantic scoring readiness gates without reporting semantic metrics or changing hook execution behavior.
