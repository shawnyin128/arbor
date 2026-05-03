# Feature 11 Review: Registered Hook Execution Harness

## Purpose

Add the Stage B harness increment that executes selected Arbor hooks through project-registered `.codex/hooks.json` entrypoints and checks packet/side-effect assertions.

## Scope

In scope:

- Add `scripts/evaluate_hook_triggers.py`.
- Build the scenario fixture under a caller-provided work root.
- Run the sidecar-backed simulated dispatcher for the scenario.
- Resolve selected hook ids through the fixture's `.codex/hooks.json`.
- Execute hook scripts through subprocess commands.
- Assert packet shape, outside-root rejection, and no unintended writes to `AGENTS.md` or `.codex/memory.md`.
- Add focused tests for H1, H2, H3, `NONE`, multi-hook, outside-root rejection, unknown hook errors, and CLI behavior.

Out of scope:

- Real natural-language semantic dispatch.
- Precision, recall, false-positive, ambiguous-case, multi-hook partial-match, or stability metrics.
- Replacing the simulated dispatcher with the plugin/runtime dispatcher.
- Full-corpus metric report generation.

## Design Notes

The harness now exercises the execution path that matters for hook reliability:

```text
scenario id
-> sidecar expectation
-> deterministic fixture
-> simulated dispatcher output
-> fixture .codex/hooks.json
-> registered hook subprocess
-> packet and side-effect assertions
```

The selected hook is resolved from the generated project's hook configuration. This protects the project-level hook registration contract from drifting away from the actual script entrypoints.

Outside-root scenarios are treated as passing when the hook rejects the outside path without leaking outside file contents. `NONE` and no-hook ambiguous decisions pass without hook execution because there is no registered hook to assert.

## Implementation Notes

- Added `scripts/evaluate_hook_triggers.py`.
- Added `HookTriggerExecutionHarnessTests` to `tests/test_arbor_skill.py`.
- Updated `docs/arbor-skill-design.md` with Feature 11 scope and Stage B progress.
- Updated `AGENTS.md` project map with the new harness script.

## Validation

- `python3 -m unittest tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 9 tests passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 99 tests passed.
- `python3 -m json.tool docs/reviews/hook-trigger-scenarios.json`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f11-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/evaluate_hook_triggers.py tests/test_arbor_skill.py`: passed.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-f11-smoke`: passed and emitted scenario execution JSON.
- `env COVERAGE_FILE=/private/tmp/arbor-f11-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 99 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f11-coverage conda run -n arbor python -m coverage report`: total coverage 89%; `scripts/evaluate_hook_triggers.py` coverage 81%.

## Developer Response

Feature 11 is implemented and targeted-tested. It proves the registered hook execution chain can run representative scenarios end to end with packet and side-effect assertions. It still does not claim semantic trigger quality because the dispatcher remains sidecar-backed.

## Adversarial Review Rounds

### Round 1: Registered Hook Execution Replay

#### Round Result Tab

| Round | Scope | Verdict | Problems | Probe pass rate | Convergence |
| --- | --- | --- | ---: | ---: | --- |
| F11-R1 | Developer validation playback plus end-to-end scenario execution, result contract, single and multi-hook execution, no-hook skip behavior, outside-root rejection, no-write digest checks, registered hook config tampering, CLI behavior, and scope-control probes | Accepted | 0 | 55/55, 100% | Converged for Feature 11 hook-execution harness scope |

#### Problems Found

| ID | Severity | Area | Finding | Evidence | Impact | Next-round acceptance gate |
| --- | --- | --- | --- | --- | --- | --- |
| F11-R1-NF1 | None | Registered hook execution harness | No new review finding. | Developer baseline checks passed; independent adversarial probes passed 55/55. | Feature 11 can be treated as accepted for registered-hook execution and packet/side-effect assertions. | No additional Feature 11 gate. Continue to full-corpus reporting and only report non-circular semantic metrics after observed labels come from a real dispatcher. |

#### Test Coverage Table

| Test category | Cases/checks run | Category coverage | Passed | Failed | Pass rate | Result summary |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Developer baseline playback | 9 checks | 9/9 planned checks, 100% | 9 | 0 | 100% | Replayed targeted harness tests, full unit suite, sidecar JSON parsing, standalone and packaged skill validation, py_compile, CLI smoke, coverage run, and coverage report. |
| End-to-end scenarios | 1 probe | 1/1 planned probe, 100% | 1 | 0 | 100% | Representative scenario set evaluated without harness exceptions. |
| Result contract | 20 probes | 20/20 planned probes, 100% | 20 | 0 | 100% | Scenario results contain required top-level keys and `passed` matches execution outcomes across selected samples. |
| Single-hook execution | 15 probes | 15/15 planned probes, 100% | 15 | 0 | 100% | H1, H2, H3, missing-setup runtime events, and selected-doc Hook 3 execute the expected registered hook and emit expected packet headers. |
| Multi-hook execution | 4 probes | 4/4 planned probes, 100% | 4 | 0 | 100% | Multi-hook scenarios execute hooks in dispatcher order and all execution assertions pass. |
| Skip decisions | 2 probes | 2/2 planned probes, 100% | 2 | 0 | 100% | `NONE` and no-hook ambiguous decisions skip hook execution and pass without false hook assertions. |
| Outside-root rejection | 4 probes | 4/4 planned probes, 100% | 4 | 0 | 100% | `EV-P010` executes Hook 3, rejects the outside path, reports the boundary error, and does not leak outside file content. |
| No-write boundaries | 3 probes | 3/3 planned probes, 100% | 3 | 0 | 100% | Direct Hook 1, Hook 2, and Hook 3 registered executions leave `AGENTS.md`, `.codex/memory.md`, and `.codex/hooks.json` unchanged. |
| Registered config boundary | 2 probes | 2/2 planned probes, 100% | 2 | 0 | 100% | Tampered registered script paths and unsupported entrypoint types are rejected through harness resolution. |
| CLI behavior | 3 probes | 3/3 planned probes, 100% | 3 | 0 | 100% | CLI emits selected-doc Hook 3 JSON, rejects unknown scenarios without traceback, and fails cleanly on repeated same-scenario work-root reuse. |
| Scope control | 1 probe | 1/1 planned probe, 100% | 1 | 0 | 100% | Harness does not implement semantic precision, recall, false-positive, or stability metric computation. |
| Total adversarial probes | 55 probes | 55/55 planned probes, 100% | 55 | 0 | 100% | Excludes baseline playback checks. |

#### Baseline Playback Table

| Command/check | Status | Notes |
| --- | --- | --- |
| `python3 -m unittest tests.test_arbor_skill.HookTriggerExecutionHarnessTests` | Pass | 9 tests passed. |
| `python3 -m unittest tests/test_arbor_skill.py` | Pass | 99 tests passed. |
| `python3 -m json.tool docs/reviews/hook-trigger-scenarios.json` | Pass | Sidecar JSON parsed successfully. |
| `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor` | Pass | Standalone skill validation passed. |
| `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor` | Pass | Packaged skill validation passed. |
| `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f11-r1-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/evaluate_hook_triggers.py tests/test_arbor_skill.py` | Pass | No compile errors. |
| `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-f11-smoke-r1` | Pass | Emitted scenario execution JSON with registered Hook 1 execution. |
| `env COVERAGE_FILE=/private/tmp/arbor-f11-r1-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py` | Pass | 99 tests passed under coverage. |
| `env COVERAGE_FILE=/private/tmp/arbor-f11-r1-coverage conda run -n arbor python -m coverage report` | Pass | Total coverage 89%; `scripts/evaluate_hook_triggers.py` coverage 81%. |

#### Scenario Test Matrix

| Scenario ID | Scenario | Category | Expected behavior | Observed result | Status |
| --- | --- | --- | --- | --- | --- |
| F11-R1-S1 | H1 startup hook execution | Single-hook execution | Resolve Hook 1 from fixture `.codex/hooks.json` and emit startup packet. | Hook 1 command ran through registered entrypoint and emitted `# Project Startup Context`. | Pass |
| F11-R1-S2 | H2 memory hygiene hook execution | Single-hook execution | Resolve Hook 2 and emit memory packet with git status and diff sections. | Hook 2 emitted memory, status, unstaged stat, staged stat, and pending work lines. | Pass |
| F11-R1-S3 | H3 selected-doc hook execution | Single-hook execution | Resolve Hook 3 and pass selected project-local doc args. | Hook 3 emitted AGENTS drift packet with `docs/constraints.md`. | Pass |
| F11-R1-S4 | Missing AGENTS runtime event | Single-hook execution | Startup fallback scenario should still run Hook 1 and emit diagnostics. | `EV-P007` executed Hook 1 and passed packet assertions. | Pass |
| F11-R1-S5 | Missing memory runtime event | Single-hook execution | Memory fallback scenario should run Hook 2 and emit diagnostics. | `EV-P008` executed Hook 2 and passed packet assertions. | Pass |
| F11-R1-S6 | Multi-hook H1 plus H2 | Multi-hook execution | Execute hooks in dispatcher order. | `M-P002` executed Hook 1 then Hook 2. | Pass |
| F11-R1-S7 | Multi-hook H2 plus H3 | Multi-hook execution | Execute all dispatcher-selected hooks and assert both packets. | `M-P003` executed selected hooks with passing assertions. | Pass |
| F11-R1-S8 | NONE skip | Skip decisions | `NONE` decisions should not execute hooks. | `NM-P002` returned no executions and passed. | Pass |
| F11-R1-S9 | Ambiguous no-hook skip | Skip decisions | No-hook ambiguous decisions should not execute hooks. | `M-P004` returned no executions and passed. | Pass |
| F11-R1-S10 | Outside-root selected doc | Outside-root rejection | Hook 3 should reject outside selected docs without leaking outside file content. | `EV-P010` returned nonzero, reported outside project root, and did not leak the outside content marker. | Pass |
| F11-R1-S11 | No-write digest boundary | No-write boundaries | Registered Hook 1/2/3 executions should not mutate durable project state files. | `AGENTS.md`, `.codex/memory.md`, and `.codex/hooks.json` digests were unchanged. | Pass |
| F11-R1-S12 | Tampered registered script | Registered config boundary | Harness should fail through registered hook resolution if config points to a missing script. | Controlled `registered hook script does not exist` error. | Pass |
| F11-R1-S13 | Unsupported entrypoint type | Registered config boundary | Harness should reject non-`skill-script` entrypoints. | Controlled `unsupported entrypoint type` error. | Pass |
| F11-R1-S14 | CLI selected-doc Hook 3 | CLI behavior | CLI should emit scenario JSON for selected-doc Hook 3. | JSON parsed, passed, and included selected doc optional args. | Pass |
| F11-R1-S15 | CLI unknown scenario | CLI behavior | Unknown scenario should fail without traceback. | Controlled `unknown scenario id` error. | Pass |
| F11-R1-S16 | CLI repeated same work-root | CLI behavior | Reusing the same scenario fixture root should fail cleanly rather than overwrite. | Second run reported `fixture root must be empty` without traceback. | Pass |
| F11-R1-S17 | Scope control | Scope control | Harness should not compute semantic metrics yet. | No precision/recall/false-positive/stability metric implementation found. | Pass |

#### Impact Assessment

| Functional area | Risk checked | Result | Assessment |
| --- | --- | --- | --- |
| Registered hook contract | Harness should execute hooks from generated `.codex/hooks.json`, not internal functions. | Registered config tampering probes proved the config path is used. | No negative impact found. |
| Packet shape | Hook 1/2/3 packets should expose expected headers and sections. | Packet assertions passed for single and multi-hook samples. | No negative impact found. |
| Project-local side effects | Harness should detect unintended writes to durable project state files. | Digest and assertion probes passed. | No negative impact found. |
| Boundary rejection | Outside-root selected docs should be rejected without content leakage. | Rejection probes passed. | No negative impact found. |
| No-hook decisions | `NONE` and ambiguous no-hook decisions should not create false execution failures. | Skip probes passed. | No negative impact found. |
| Stage B scope | Harness should still avoid semantic-quality metrics while dispatcher is simulated. | Scope-control probe passed. | No negative impact found. |

#### Optimization Suggestions

| Priority | Suggestion | Rationale | Follow-up owner |
| --- | --- | --- | --- |
| P1 | Add the next report feature as a full-corpus execution report, but keep semantic precision/recall labeled as not meaningful while using the sidecar-backed dispatcher. | Feature 11 proves runtime execution assertions, not real semantic dispatch quality. | Stage B report owner. |
| P2 | Keep registered-config tampering tests when replacing the simulated dispatcher with a real plugin/runtime dispatcher. | The project-level hook contract must remain the execution source of truth. | Harness maintenance. |
| P3 | Consider adding an explicit workspace cleanup mode or unique run id if repeated CLI runs in the same work root should be supported later. | Current repeated same-scenario work-root behavior fails safely, which is fine for one-shot temp runs but may be inconvenient for batch reports. | Future report tooling. |
