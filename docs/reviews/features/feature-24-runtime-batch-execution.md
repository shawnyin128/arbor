# Feature 24: Runtime Batch Execution Controls

## Development Target

Make authenticated real-plugin runtime evaluation practical for partial corpus runs before attempting the full 150-scenario corpus.

This feature exists because a full real-runtime corpus run is slow and previously had no incremental visibility. It should let the developer run selected scenario batches, watch progress, and replay failures without weakening the existing semantic scoring gates.

## Scope

- Add selected multi-scenario corpus execution via `--scenario-ids`.
- Add compact per-scenario progress events via `--progress-jsonl`.
- Keep strict smoke expectation flags limited to `--scenario-id`.
- Normalize model-natural optional hook arguments before hook execution:
  - H3 bare doc paths become repeated `--doc <path>` arguments.
  - H3 `--doc path` and `--doc=path` are canonicalized.
  - H2 joined `--diff-args --stat` becomes `--diff-args=--stat`.
  - H2 split `["--diff-args", "--stat"]` also becomes `--diff-args=--stat`.
  - H1 `--git-log-args=...` values with spaces stay intact.
  - H1 split `["--git-log-args", "--max-count=10 ..."]` becomes an equals-form option value.
- Preserve validation that non-empty optional args are allowed only for selected hooks.

## Out of Scope

- Full 150-scenario real-runtime corpus completion.
- Repeated real-runtime stability scoring.
- Any change to packaged Arbor hook scripts or skill behavior.
- Any release of evaluation-only files in the plugin payload.

## Implementation Notes

- `scripts/evaluate_hook_triggers.py`
  - Added `--scenario-ids` as a selected corpus target.
  - Added `--progress-jsonl` and progress event emission after each evaluated scenario.
  - Added `scenario_scope` to reports: `all` or `selected`.
  - Repeated corpus runs can write per-run progress files derived from the requested progress path.
- `scripts/plugin_trigger_adapters.py`
  - Added optional-args normalization inside `validate_trigger_decision_contract()`, so all adapter outputs cross the same contract boundary before hook execution.
  - Kept strict hook-id, decision, confidence, reason, and selected-hook optional-args validation.
- `tests/test_arbor_skill.py`
  - Added parser, CLI, selected-corpus progress, and optional-args normalization regressions.

## Review Feedback Addressed

| Review item | Resolution |
| --- | --- |
| Long real-runtime runs need visibility and replayability | Added `--scenario-ids` and `--progress-jsonl` so partial batches can be observed and replayed. |
| Runtime model output can express optional args in natural but non-argv-safe forms | Added adapter-level normalization for H2 and H3 optional args before hook command construction. |
| Smoke flags should not be confused with corpus metrics | `--expect-*` and `--require-runtime-available` remain single-scenario only. |

## Validation

- `python3 -m unittest tests.test_arbor_skill.HookTriggerPluginAdapterTests`: 28 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f24-fix2-pycache python3 -m py_compile scripts/plugin_trigger_adapters.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check scripts/plugin_trigger_adapters.py tests/test_arbor_skill.py --no-cache`: passed.
- `python3 skills/arbor/scripts/run_memory_hygiene_hook.py --root /Users/shawn/Desktop/arbor --diff-args=--stat`: passed.
- `python3 skills/arbor/scripts/run_session_startup_hook.py --root /Users/shawn/Desktop/arbor --git-log-args=--max-count=1`: passed.
- `python3 -m unittest tests.test_arbor_skill`: 168 tests passed.
- Strict failure replay with real plugin runtime:
  - `CL-P010`, `CL-P012`, and `M-P003` passed in an escalated authenticated runtime.
  - H3 bare docs normalized to canonical `--doc` pairs and executed successfully.
  - H2 joined diff args normalized to `--diff-args=--stat` and executed successfully.
- Selected 25-scenario authenticated real-runtime batch:
  - Command: `python3 scripts/evaluate_hook_triggers.py --scenario-ids CL-P001,CL-P002,CL-P003,CL-P004,CL-P005,CL-P006,CL-P007,CL-P008,CL-P009,CL-P010,CL-P011,CL-P012,CL-P013,CL-P014,CL-P015,CL-P016,EV-P002,NM-P001,NM-P002,NM-P003,NM-P004,M-P001,M-P002,M-P003,M-P004 --work-root /private/tmp/arbor-f24-batch25-runtime-fixed --trigger-adapter plugin-runtime-codex-exec --auth-source-home ~ --runtime-timeout 90 --progress-jsonl /private/tmp/arbor-f24-batch25-runtime-fixed/progress.jsonl`
  - Result: 25/25 scenarios passed.
  - Runtime availability gate: passed, no blockers.
  - Hook execution gate: passed, 18/18 selected hook executions passed.
  - None false-positive rate: 0.0.
  - Near-miss false-positive rate: 0.0.
  - Per-hook precision and recall: 1.0 for H1, H2, and H3 within this selected batch.

## Status

Implemented and self-tested. Ready for review before attempting either the full 150-scenario authenticated real-runtime corpus or repeated runtime stability runs.

## Reviewer Round 1 - 2026-05-03

### Findings

| ID | Priority | Location | Status | Finding |
| --- | --- | --- | --- | --- |
| F24-R1-001 | P2 | `tests/test_arbor_skill.py` optional-args normalization tests | Open | Malformed optional-args cases are not covered. The current tests prove happy-path normalization, but adversarial runtime outputs such as lone `--doc`, empty `--doc=`, unknown H3 flags, lone `--diff-args`, and lone `--git-log-args` are still accepted by the adapter or silently dropped. Add negative tests that define whether these malformed shapes must fail at adapter validation or be explicitly allowed to fail later at hook execution. |

### Test Matrix

| Test category | Test cases / probes | Coverage focus | Coverage | Pass rate | Result |
| --- | ---: | --- | ---: | ---: | --- |
| Feature contract review | 1 | Scope, out-of-scope, implementation notes, validation claims | 100% | 100% | Passed |
| Focused adapter regression | 28 | `HookTriggerPluginAdapterTests` | 100% | 100% | Passed |
| Full project regression | 168 | `tests/test_arbor_skill.py` | 100% | 100% | Passed |
| Static checks | 3 | `py_compile`, `ruff`, `git diff --check` | 100% | 100% | Passed |
| Selected corpus and progress | 4 | `--scenario-ids`, progress JSONL, selected H1/N/H3 paths, repeated progress derivation | 100% | 100% | Passed |
| CLI guardrails | 4 | Smoke flags with `--scenario-ids`, repeat with `--scenario-ids`, unknown ids, empty id list | 100% | 100% | Passed |
| Optional-args happy paths | 6 | H3 bare docs, H3 `--doc`, H3 `--doc=`, H2 joined/split diff args, H1 split/equal git log args | 100% | 100% | Passed |
| Optional-args malformed paths | 5 | Lone `--doc`, empty `--doc=`, unknown H3 flag, lone `--diff-args`, lone `--git-log-args` | 100% probed | 0% rejected | Failed coverage expectation |
| Direct hook smoke | 2 | Memory hygiene hook with diff args, startup hook with git log args | 100% | 100% | Passed |

### Scenario Tests

| Scenario | Command / method | Expected | Actual | Result |
| --- | --- | --- | --- | --- |
| Selected two-scenario batch | `evaluate_hook_triggers.py --scenario-ids H1-P001,N-P001 --progress-jsonl ...` | Selected scope, two compact progress events, both passed | `scenario_scope=selected`; two JSONL rows with correct indexes and decisions | Passed |
| Selected H3 optional docs | `evaluate_hook_triggers.py --scenario-ids H3-P002 --progress-jsonl ...` | H3 optional docs normalize to `--doc <path>` and hook passes | Optional args emitted as canonical `--doc` pairs; hook execution passed | Passed |
| Repeated progress derivation | `evaluate_hook_triggers.py --all --repeat-runs 2 --trigger-adapter plugin-runtime-stub --progress-jsonl ...` | Per-run progress files are derived from the base path | `progress-run-001.jsonl` and `progress-run-002.jsonl`, each with 150 rows | Passed |
| Smoke flag guardrail | `--scenario-ids H1-P001 --expect-decision trigger` | CLI rejects strict smoke flags outside `--scenario-id` | Exit 2 with the expected guardrail error | Passed |
| Repeat guardrail | `--scenario-ids H1-P001 --repeat-runs 2` | CLI rejects repeat mode outside `--all` | Exit 2 with the expected guardrail error | Passed |
| Scenario-id validation | `--scenario-ids UNKNOWN` and `--scenario-ids " , "` | CLI rejects unknown and empty selected ids | Exit 2 for both invalid inputs | Passed |
| Malformed optional args | Direct adapter contract probes | Malformed optional args should have explicit regression coverage and a defined failure boundary | Adapter accepted or silently normalized away all probed malformed classes | Failed coverage expectation |
| Full regression replay | `python3 -m unittest tests/test_arbor_skill.py` | Existing feature set remains green | 168 tests passed | Passed |

### Optimization Suggestions

| Area | Recommendation |
| --- | --- |
| Test completion | Add negative optional-args tests for incomplete and unknown flag forms. The tests should lock either strict adapter rejection or intentionally documented hook-level rejection. |
| Validation command set | Include `scripts/evaluate_hook_triggers.py` in the Feature 24 `py_compile` and `ruff` validation list because this feature changes CLI behavior and progress emission there. |
| Focused regression grouping | Add a focused test command that includes both adapter normalization tests and harness/progress tests, not only `HookTriggerPluginAdapterTests`, so future rounds catch selected-corpus regressions without requiring the full 168-test suite every time. |

## Developer Response - Round 1 Fix

### Changes

- `scripts/plugin_trigger_adapters.py`
  - Tightened optional-args normalization into strict adapter validation.
  - H3 now rejects malformed doc args before hook execution:
    - lone `--doc`;
    - empty `--doc=`;
    - `--doc` followed by another option-like token;
    - unknown H3 optional flags such as `--doc-paths`.
  - H2/H1 single-value options now reject missing or empty values instead of preserving malformed argv:
    - lone `--diff-args`;
    - lone `--git-log-args`;
    - empty equals-form values;
    - unknown option shapes.
  - Happy-path normalization remains unchanged for model-natural outputs that can be safely normalized.
- `tests/test_arbor_skill.py`
  - Added malformed optional-args regressions for the review's adversarial cases.
  - Added a small helper for trigger-decision contract fixtures in `HookTriggerPluginAdapterTests`.

### Review Feedback Addressed

| Review item | Resolution |
| --- | --- |
| F24-R1-001: malformed optional-args cases are not covered | Fixed. Added negative tests and made malformed optional args fail at adapter validation instead of silently passing through or being dropped. |
| Include `scripts/evaluate_hook_triggers.py` in Feature 24 compile and ruff validation | Done in the Round 1 fix validation command set. |
| Add focused regression grouping covering adapter plus harness/progress | Done with `HookTriggerPluginAdapterTests` plus `HookTriggerExecutionHarnessTests`. |

### Validation

- `python3 -m unittest tests.test_arbor_skill.HookTriggerPluginAdapterTests tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 64 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f24-r1-pycache python3 -m py_compile scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py tests/test_arbor_skill.py --no-cache`: passed.
- `python3 -m unittest tests.test_arbor_skill`: 174 tests passed.
- `git diff --check`: passed.

### Status

Round 1 malformed optional-args fix is implemented and self-tested. Feature 24 is ready for re-review.

## Round 2 Re-review - 2026-05-03

### Findings

| ID | Priority | Location | Status | Finding |
| --- | --- | --- | --- | --- |
| F24-R2-001 | - | - | No new findings | `F24-R1-001` is accepted as fixed. Malformed optional args now have an explicit adapter-validation failure boundary, and the focused validation set includes both adapter normalization and harness/progress behavior. |

### Reviewer Verdict

Feature 24 is accepted. The next stage can use `--scenario-ids` and `--progress-jsonl` for targeted replay, or run the full authenticated real-runtime corpus with progress tracking.

## Reviewer Round 2 - 2026-05-03

### Findings

| ID | Priority | Location | Status | Finding |
| --- | --- | --- | --- | --- |
| F24-R1-001 | P2 | `tests/test_arbor_skill.py` optional-args normalization tests | Closed | Replayed. The developer fixed the finding by making malformed optional args fail at adapter validation and adding negative regressions for the adversarial cases. No new findings were added in this round. |

### Test Matrix

| Test category | Test cases / probes | Coverage focus | Coverage | Pass rate | Result |
| --- | ---: | --- | ---: | ---: | --- |
| Developer response review | 1 | Round 1 fix notes, validation claims, status update | 100% | 100% | Passed |
| Focused adapter plus harness regression | 64 | `HookTriggerPluginAdapterTests` and `HookTriggerExecutionHarnessTests` | 100% | 100% | Passed |
| Full project regression | 174 | `tests/test_arbor_skill.py` after Round 1 fix | 100% | 100% | Passed |
| Static checks | 3 | `py_compile`, `ruff`, `git diff --check` | 100% | 100% | Passed |
| Malformed optional-args replay | 5 | Lone `--doc`, empty `--doc=`, unknown H3 flag, lone `--diff-args`, lone `--git-log-args` | 100% | 100% rejected | Passed |
| Legal selected corpus replay | 4 | H1, H2, H3, and NONE selected batch with progress JSONL | 100% | 100% | Passed |
| Direct hook smoke | 2 | Memory hygiene hook with diff args, startup hook with git log args | 100% | 100% | Passed |

### Scenario Tests

| Scenario | Command / method | Expected | Actual | Result |
| --- | --- | --- | --- | --- |
| Malformed optional args replay | Direct adapter contract probe for 5 adversarial cases | Every malformed shape raises `AdapterError` before hook execution | 5/5 rejected with controlled errors | Passed |
| Focused regression replay | `python3 -m unittest tests.test_arbor_skill.HookTriggerPluginAdapterTests tests.test_arbor_skill.HookTriggerExecutionHarnessTests` | Adapter and harness/progress tests stay green | 64 tests passed | Passed |
| Full regression replay | `python3 -m unittest tests/test_arbor_skill.py` | Existing feature set remains green after stricter validation | 174 tests passed | Passed |
| Selected legal batch replay | `evaluate_hook_triggers.py --scenario-ids H1-P001,H2-P001,H3-P002,N-P001 --progress-jsonl ...` | Tightened validation does not break legal selected execution | 4/4 scenarios passed; progress rows had indexes 1-4 and total 4 | Passed |
| Direct hook replay | Startup and memory hygiene hook commands with selected args | Registered hook scripts still execute legal optional args | Both hooks returned successful context packets | Passed |

### Optimization Suggestions

| Area | Recommendation |
| --- | --- |
| Closure status | Mark F24-R1-001 closed in the review index if the project keeps a cross-feature finding tracker outside this file. |
| Future real-runtime batches | Keep the malformed optional-args replay as a focused preflight before authenticated runtime batch runs, since real model output can drift back into non-argv-safe shapes. |
