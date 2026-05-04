# Feature 23 Review: Runtime Schema Compatibility And Smoke Gates

## Development Target

Unblock real `plugin-runtime-codex-exec` trigger selection after Feature 22 exposed that authenticated runtime execution still failed at the structured output schema gate.

This feature is intentionally narrow: fix the schema/runtime diagnostic gap, then prove one authenticated positive and one authenticated negative scenario can run through the installed plugin runtime path. It is not the final full-corpus semantic evaluation.

## Scope

In scope:

- Add a short redacted diagnostic suffix for nonzero Codex runtime failures.
- Keep runtime availability gates grouped by stable blocker class even when diagnostics are present.
- Reject non-positive `--runtime-timeout` values before invoking Codex.
- Make the trigger decision output schema compatible with strict structured-output requirements.
- Preserve the local trigger decision contract after schema normalization.
- Run authenticated smoke scenarios for one H1 positive and one NONE negative case.

Out of scope:

- Running the full 150-scenario corpus.
- Changing semantic metric formulas.
- Changing hook trigger descriptions to improve model behavior.
- Adding retry logic around model/runtime failures.

## Implementation Summary

- `scripts/plugin_trigger_adapters.py`
  - Added redacted runtime failure details to `runtime_failed` style blocker reasons.
  - Added schema-compatible `optional_args` output shape with explicit hook-id properties and `additionalProperties=false`.
  - Normalizes schema-required empty optional-arg arrays away before local contract validation.
  - Keeps non-empty optional args for unselected hooks invalid.
- `scripts/evaluate_hook_triggers.py`
  - Keeps blocker counts normalized to the stable blocker class before any diagnostic detail.
  - Added positive integer parsing for `--runtime-timeout`.
- `tests/test_arbor_skill.py`
  - Added tests for runtime detail redaction.
  - Added tests for blocker-count normalization with diagnostic detail.
  - Added tests for strict optional-args schema compatibility and normalization.
  - Added parser rejection coverage for non-positive runtime timeout.

## Runtime Findings

Before the schema fix, the authenticated runtime reached Codex but failed with:

- `runtime_failed`
- `invalid_json_schema`
- root cause: the `optional_args` schema used dynamic `additionalProperties`, which the structured-output path rejected.

After the schema fix:

- `H1-P001` selected `arbor.session_startup_context`.
- The registered startup hook executed successfully.
- `N-P001` returned `decision=none` and selected no hooks.

## Validation

- `python3 -m unittest tests.test_arbor_skill.HookTriggerPluginAdapterTests tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 45 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f23-schema-pycache python3 -m py_compile scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py tests/test_arbor_skill.py --no-cache`: passed.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-f23-runtime-smoke-schema --trigger-adapter plugin-runtime-codex-exec --auth-source-home ~ --runtime-timeout 90`: passed with real runtime trigger `arbor.session_startup_context` and hook execution success.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id N-P001 --work-root /private/tmp/arbor-f23-runtime-smoke-negative --trigger-adapter plugin-runtime-codex-exec --auth-source-home ~ --runtime-timeout 90`: passed with real runtime `decision=none` and no hooks.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-f23-timeout-smoke --trigger-adapter plugin-runtime-codex-exec --runtime-timeout 0`: failed early as expected with `must be a positive integer`.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f23-full-pycache python3 -m unittest tests/test_arbor_skill.py`: 155 tests passed.
- `git diff --check`: passed.

## Status

Implemented and self-tested. Ready for review before expanding from two authenticated smoke scenarios to a small real-runtime batch or the full corpus.

## Round 1 Review - 2026-05-03

### Findings

| ID | Priority | File | Status | Finding |
| --- | --- | --- | --- | --- |
| F23-R1-001 | P2 | `scripts/evaluate_hook_triggers.py:231-240` | Open | Single-scenario runtime blockers can satisfy the smoke command with `passed=true`. During review, the H1 authenticated smoke path returned `decision=ambiguous`, no hooks, and `network_unavailable`, but the report still had top-level `passed=true` because `evaluate_scenario` only checks selected hook execution results. Feature 23 uses H1/NONE commands as smoke gates, so a blocked runtime can look like a passed positive smoke unless a separate assertion checks runtime availability and the expected trigger decision. |

### Test Matrix

| Test Area | Test Cases Run | Coverage | Passed | Pass Rate | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| Feature contract review | 1 feature contract | 1/1 schema/smoke boundary set | 1/1 inspected | 100% | Reviewed strict schema compatibility, optional-args normalization, blocker diagnostics, timeout parsing, and positive/negative smoke claims. |
| Focused developer regressions | 45 tests | 45/45 adapter and harness checks | 45/45 | 100% | `HookTriggerPluginAdapterTests` and `HookTriggerExecutionHarnessTests` passed. |
| Static validation | 3 commands | 3/3 static checks | 3/3 | 100% | `py_compile`, `ruff check`, and `git diff --check` passed. |
| Schema and contract probes | 3 probes | 3/3 optional-args schema/contract classes | 3/3 | 100% | Strict schema shape, selected-hook args preservation, and unselected-hook args rejection all behaved as expected. |
| Runtime diagnostic probes | 1 probe | 1/1 redaction and blocker grouping path | 1/1 | 100% | Sensitive-looking lines were redacted and `runtime_failed` remained the stable blocker key. |
| Runtime timeout gate | 2 checks | 2/2 parser/CLI rejection paths | 2/2 | 100% | `positive_int` rejected `0`, negative, and non-numeric input; CLI rejected `--runtime-timeout 0` before runtime execution. |
| Authenticated negative smoke | 1 scenario | 1/1 NONE smoke | 1/1 | 100% | Escalated N-P001 run returned real runtime `decision=none`, no hooks, and no blocker. |
| Authenticated positive smoke | 1 scenario | 1/1 H1 smoke command path | 0/1 verified | 0% | Sandbox H1 run returned `network_unavailable` with `passed=true`; unsandboxed H1 replay was blocked by safety review because it would send fixture/project data to an external runtime. |
| Full regression suite | 155 tests | 155/155 unit/scenario tests | 155/155 | 100% | `python3 -m unittest tests/test_arbor_skill.py` passed with pycache redirected outside the repo. |

### Scenario Testing

| Scenario | Target Risk | Method | Result |
| --- | --- | --- | --- |
| Strict optional-args schema | Runtime structured output rejects dynamic `additionalProperties` | Inspected `TRIGGER_DECISION_SCHEMA` and asserted explicit hook-id properties, required hook ids, and `additionalProperties=false` | Passed. |
| Selected hook optional args | Schema-required empty hook keys erase selected args | Validated a trigger decision with `arbor.goal_constraint_drift` selected and non-empty `--doc` args | Passed: selected hook args were preserved. |
| Unselected hook optional args | Empty-key normalization accidentally accepts args for unselected hooks | Validated a `decision=none` payload with non-empty `arbor.goal_constraint_drift` args | Passed: rejected with `optional_args keys must be selected hooks`. |
| Diagnostic redaction and stable blocker counts | Runtime details leak auth material or fragment blocker metrics | Built a `runtime_failed` blocker from output containing `Authorization`, `Bearer`, `TOKEN`, and `invalid_json_schema` | Passed: sensitive lines were redacted and runtime availability counted `runtime_failed: 1`. |
| Timeout CLI gate | Expensive runtime call starts with invalid timeout | Ran `--runtime-timeout 0` through the CLI | Passed: exited early with `must be a positive integer`. |
| H1 positive smoke under sandbox | Blocked runtime is mistaken for smoke success | Ran H1-P001 with `plugin-runtime-codex-exec`, `--auth-source-home ~`, and `--runtime-timeout 90` | Failed: report returned `network_unavailable`, no hooks, but top-level `passed=true`. |
| N-P001 negative smoke with real runtime | Negative runtime smoke cannot reach real runtime path | Ran N-P001 with authenticated runtime in an escalated environment | Passed: real runtime returned `decision=none`, no hooks, `requires_agent_judgment=false`. |
| Full regression replay | Feature 23 changes break unrelated Arbor behavior | Ran full `tests/test_arbor_skill.py` suite | Passed: 155/155 tests. |

### Optimization Suggestions

| Priority | Suggestion | Rationale |
| --- | --- | --- |
| P2 | Add a smoke-gate mode or helper that requires runtime availability plus exact expected smoke decision/hooks for selected scenario ids. | The existing corpus semantics intentionally accept blockers as unscored, but smoke validation needs a stricter success condition. |
| P2 | Make the Feature 23 validation commands assert `trigger_decision` fields, not only command exit code or top-level `passed`. | This prevents a `network_unavailable` H1 run from being reported as a positive smoke pass. |
| P3 | Keep the current redacted detail suffix short and stable until JSON event schemas are parsed structurally. | The diagnostic path is useful and did not fragment blocker counts in review. |

### Reviewer Verdict

Feature 23 is not accepted as a smoke gate yet. The schema compatibility, optional-args normalization, redacted diagnostics, timeout parsing, negative runtime smoke, and full regression replay are clean, but the H1 positive smoke command can still return `passed=true` when the runtime is unavailable and no hook is selected. The next fix should separate "runtime blocker accepted for scoring-gate purposes" from "authenticated smoke succeeded."

## Developer Response - Round 1 Fix

### Changes

- `scripts/evaluate_hook_triggers.py`
  - Added explicit single-scenario smoke expectation flags:
    - `--require-runtime-available`
    - `--expect-decision`
    - `--expect-hooks`
  - Added `apply_smoke_expectations()`, which appends `smoke_assertions` and marks the scenario `passed=false` when runtime availability, decision, or exact hook expectations fail.
  - Preserved default corpus/scoring behavior: without smoke expectation flags, runtime blockers remain accepted as unscored blocker decisions.
  - Smoke expectation flags are single-scenario only and are rejected with `--all`.
  - CLI exits nonzero only when smoke expectation flags are supplied and their assertions fail.
- `tests/test_arbor_skill.py`
  - Added regression coverage proving a `network_unavailable` H1 blocker remains accepted by default but fails strict H1 smoke expectations.
  - Added parser coverage for smoke expectation flags.
  - Added CLI coverage for matching and mismatched smoke expectations.

### Review Feedback Addressed

| Review item | Resolution |
| --- | --- |
| F23-R1-001: single-scenario runtime blockers can satisfy smoke command with `passed=true` | Fixed by adding explicit smoke expectations that require runtime availability and exact expected decision/hooks. |
| Add smoke-gate mode/helper | Added `apply_smoke_expectations()` and CLI flags. |
| Feature 23 validation commands should assert `trigger_decision` fields | Updated runtime smoke commands to use `--require-runtime-available`, `--expect-decision`, and `--expect-hooks`. |

### Validation

- `python3 -m unittest tests.test_arbor_skill.HookTriggerPluginAdapterTests tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 49 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f23-r1-pycache python3 -m py_compile scripts/evaluate_hook_triggers.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check scripts/evaluate_hook_triggers.py tests/test_arbor_skill.py --no-cache`: passed.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-f23-r1-sidecar-pass --trigger-adapter sidecar-baseline --expect-decision trigger --expect-hooks arbor.session_startup_context`: passed with smoke assertions.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-f23-r1-sidecar-fail --trigger-adapter sidecar-baseline --expect-decision none --expect-hooks ''`: failed as expected with `passed=false` and exit code 1.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-f23-r1-runtime-smoke --trigger-adapter plugin-runtime-codex-exec --auth-source-home ~ --runtime-timeout 90 --require-runtime-available --expect-decision trigger --expect-hooks arbor.session_startup_context`: passed with real runtime trigger `arbor.session_startup_context`, successful hook execution, and passing smoke assertions.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id N-P001 --work-root /private/tmp/arbor-f23-r1-runtime-negative --trigger-adapter plugin-runtime-codex-exec --auth-source-home ~ --runtime-timeout 90 --require-runtime-available --expect-decision none --expect-hooks ''`: passed with real runtime `decision=none`, no hooks, and passing smoke assertions.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f23-r1-full-pycache python3 -m unittest tests/test_arbor_skill.py`: 159 tests passed.
- `git diff --check`: passed.

### Status

Round 1 smoke-gate bug fix is implemented and self-tested. Feature 23 is ready for re-review.

## Round 2 Re-review - 2026-05-03

### Findings

| ID | Priority | File | Status | Finding |
| --- | --- | --- | --- | --- |
| F23-R2-001 | - | - | No new findings | `F23-R1-001` is accepted as fixed. Default scenario evaluation still preserves blocker-as-unscored behavior, while explicit smoke expectation flags now add `smoke_assertions`, flip `passed=false` on runtime/decision/hook mismatch, and make the CLI exit nonzero for failed smoke gates. |

### Test Matrix

| Test Area | Test Cases Run | Coverage | Passed | Pass Rate | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| Developer feedback review | 1 fix response | 1/1 P2 finding replayed | 1/1 accepted | 100% | Reviewed `apply_smoke_expectations()`, smoke expectation CLI flags, single-scenario restriction, and exit-code behavior. |
| Focused developer regressions | 49 tests | 49/49 adapter and harness checks | 49/49 | 100% | `HookTriggerPluginAdapterTests` and `HookTriggerExecutionHarnessTests` passed. |
| Static validation | 3 commands | 3/3 static checks | 3/3 | 100% | `py_compile`, `ruff check`, and `git diff --check` passed. |
| Sidecar smoke gate pass/fail | 2 CLI probes | 2/2 smoke assertion paths | 2/2 | 100% | Matching sidecar expectations exited 0 with passing assertions; mismatched expectations exited 1 with `passed=false`. |
| Smoke flag scope guard | 1 CLI probe | 1/1 invalid `--all` usage | 1/1 | 100% | `--all` with smoke expectation flags was rejected with `smoke expectation flags can only be used with --scenario-id`. |
| Runtime blocker default replay | 1 CLI probe | 1/1 default blocker semantics | 1/1 | 100% | H1 runtime blocker still returned `passed=true` without smoke flags, preserving corpus/scoring behavior. |
| Runtime blocker strict smoke replay | 2 CLI probes | 2/2 runtime blocker smoke-gate paths | 2/2 | 100% | H1 strict smoke failed with runtime/decision/hook assertions; N-P001 strict smoke failed under sandbox `network_unavailable` with runtime/decision assertions, proving blockers no longer pass smoke gates. |
| Full regression suite | 159 tests | 159/159 unit/scenario tests | 159/159 | 100% | `python3 -m unittest tests/test_arbor_skill.py` passed with pycache redirected outside the repo. |

### Scenario Testing

| Scenario | Target Risk | Method | Result |
| --- | --- | --- | --- |
| Default H1 runtime blocker replay | Fix accidentally breaks corpus/scoring blocker semantics | Ran H1-P001 through `plugin-runtime-codex-exec` without smoke flags in the sandbox | Passed: blocker remained accepted as `passed=true`, preserving default behavior. |
| Strict H1 smoke blocker replay | Previous P2 false pass still exists when smoke flags are used | Ran H1-P001 with `--require-runtime-available --expect-decision trigger --expect-hooks arbor.session_startup_context` | Passed: command exited 1, `passed=false`, and smoke assertions failed for runtime availability, decision, and hooks. |
| Strict N-P001 smoke under sandbox blocker | Negative smoke can still pass while runtime is unavailable | Ran N-P001 with `--require-runtime-available --expect-decision none --expect-hooks ''` | Passed: command exited 1 under `network_unavailable`; runtime availability and decision assertions failed while the empty-hook assertion passed. |
| Matching sidecar smoke expectations | Smoke assertion mode breaks expected success path | Ran H1-P001 sidecar with `--expect-decision trigger --expect-hooks arbor.session_startup_context` | Passed: command exited 0 and all smoke assertions passed. |
| Mismatched sidecar smoke expectations | Smoke assertion failures do not propagate to exit code | Ran H1-P001 sidecar with `--expect-decision none --expect-hooks ''` | Passed: command exited 1 with `passed=false` and failed smoke assertions. |
| Smoke flags with full corpus | Smoke flags accidentally apply to corpus reports | Ran `--all` with `--expect-decision trigger` | Passed: CLI rejected the combination. |
| Full regression replay | Smoke-gate fix breaks unrelated Arbor behavior | Ran full `tests/test_arbor_skill.py` suite | Passed: 159/159 tests. |

### Optimization Suggestions

| Priority | Suggestion | Rationale |
| --- | --- | --- |
| P3 | Keep using explicit smoke flags for authenticated runtime claims in review docs and release notes. | The default scenario `passed` field intentionally has corpus semantics; smoke claims should always assert runtime availability and expected decision/hooks. |
| P3 | If smoke gates expand beyond a few scenarios, consider a small named smoke manifest rather than long CLI invocations. | This would reduce command drift while preserving exact expectations. |

### Reviewer Verdict

Feature 23 is accepted for the reviewed offline smoke-gate scope. The prior false-green smoke issue is fixed: runtime blockers remain accepted only in default corpus/scoring mode, and strict smoke mode now fails blocked or mismatched runtime decisions with explicit assertions and a nonzero CLI exit. Real authenticated success remains environment-dependent; in this review sandbox, runtime smoke commands hit `network_unavailable` and were correctly failed by strict smoke gates.
