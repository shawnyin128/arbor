# Feature 10 Review: Simulated Dispatcher Adapter

## Purpose

Add a sidecar-backed simulated dispatcher adapter for Stage B hook trigger evaluation.

## Scope

In scope:

- Add `scripts/simulated_dispatcher.py`.
- Load the Markdown scenario corpus and JSON sidecar.
- Emit the dispatcher output contract for one scenario id.
- Preserve `trigger`, `none`, `ambiguous`, expected hook, optional hook, forbidden hook, optional-arg, and agent-judgment semantics.
- Add focused tests for representative H1, NONE, MULTI, ambiguous, optional-arg, outside-root, all-scenario contract, deterministic, and CLI behavior.

Out of scope:

- Natural-language semantic dispatch.
- Real plugin/runtime dispatcher integration.
- Hook execution.
- Precision, recall, false-positive, stability, or execution metrics.
- Any claim that sidecar-backed simulated output measures real trigger quality.

## Design Notes

The simulated dispatcher is intentionally an adapter, not a classifier. It consumes the accepted scenario sidecar and produces the same structured JSON shape that the future real dispatcher should produce:

- `hooks`
- `decision`
- `confidence`
- `requires_agent_judgment`
- `optional_args`
- `reason`

This lets the next harness feature validate fixture wiring, dispatch-contract parsing, hook selection plumbing, and optional-argument handling before introducing a real semantic dispatcher. It should not be used to report semantic activation metrics because its source of truth is the expected sidecar itself.

## Implementation Notes

- Added `scripts/simulated_dispatcher.py`.
- Added `HookTriggerSimulatedDispatcherTests` to `tests/test_arbor_skill.py`.
- Updated `docs/arbor-skill-design.md` with Feature 10 scope and Stage B progress.
- Updated `AGENTS.md` project map with the new simulated dispatcher script.

## Validation

- `python3 -m unittest tests.test_arbor_skill.HookTriggerSimulatedDispatcherTests`: 15 tests passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 90 tests passed.
- `python3 -m json.tool docs/reviews/hook-trigger-scenarios.json`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f10-final-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py tests/test_arbor_skill.py`: passed.
- `python3 scripts/simulated_dispatcher.py --scenario-id H1-P001`: passed and emitted dispatcher-contract JSON.
- `env COVERAGE_FILE=/private/tmp/arbor-f10-final-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 90 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f10-final-coverage conda run -n arbor python -m coverage report`: total coverage 89%; `scripts/simulated_dispatcher.py` coverage 77%.

## Developer Response

Feature 10 is implemented and targeted-tested. It supplies a stable dispatcher adapter contract for the next Stage B increment while keeping real semantic dispatch, hook execution, and metrics out of scope.

## Adversarial Review Rounds

### Round 1: Simulated Dispatcher Replay

#### Round Result Tab

| Round | Scope | Verdict | Problems | Probe pass rate | Convergence |
| --- | --- | --- | ---: | ---: | --- |
| F10-R1 | Developer validation playback plus corpus loading, dispatcher contract shape, sidecar scoring semantics, representative scenarios, fixture-summary integration, determinism, CLI errors, and scope-control probes | Accepted | 0 | 39/39, 100% | Converged for Feature 10 adapter scope |

#### Problems Found

| ID | Severity | Area | Finding | Evidence | Impact | Next-round acceptance gate |
| --- | --- | --- | --- | --- | --- | --- |
| F10-R1-NF1 | None | Simulated dispatcher adapter | No new review finding. | Developer baseline checks passed; independent adversarial probes passed 39/39. | Feature 10 can be treated as accepted for sidecar-backed dispatcher-contract output. | No additional Feature 10 gate. Continue to registered-hook execution and packet/side-effect assertions. |

#### Test Coverage Table

| Test category | Cases/checks run | Category coverage | Passed | Failed | Pass rate | Result summary |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Developer baseline playback | 9 checks | 9/9 planned checks, 100% | 9 | 0 | 100% | Replayed targeted dispatcher tests, full unit suite, sidecar JSON parsing, standalone and packaged skill validation, py_compile, CLI smoke, coverage run, and coverage report. |
| Corpus loading | 5 probes | 5/5 planned probes, 100% | 5 | 0 | 100% | Loaded all 150 scenarios, preserved ids, expressions, labels, required expectation fields, and hook id alignment with packaged plugin hooks. |
| Contract shape | 7 probes | 7/7 planned probes, 100% | 7 | 0 | 100% | Every scenario produced exact dispatcher-contract keys with valid decisions, confidence values, known hooks, optional args only for selected hooks, and scenario-aware reasons. |
| Sidecar semantics | 9 probes | 9/9 planned probes, 100% | 9 | 0 | 100% | Decisions stay within allowed decisions, selected hooks avoid forbidden hooks, trigger results include expected hooks, `NONE` and single-label rows preserve their semantics, and agent-judgment flags propagate. |
| Representative scenarios | 9 probes | 9/9 planned probes, 100% | 9 | 0 | 100% | H1, H2, H3, NONE, multi-hook trigger, ambiguous cases, selected docs, and outside-root placeholder behavior matched expectations. |
| Fixture integration | 2 probes | 2/2 planned probes, 100% | 2 | 0 | 100% | `EV-P010` outside-root placeholder resolves from an `eval_fixtures.py` summary through both API and CLI paths. |
| Determinism | 2 probes | 2/2 planned probes, 100% | 2 | 0 | 100% | Repeated all-scenario dispatch and custom corpus path dispatch returned stable results. |
| CLI/error handling | 3 probes | 3/3 planned probes, 100% | 3 | 0 | 100% | Missing scenario corpus, malformed sidecar JSON, and unknown scenario ids fail with controlled errors and no traceback. |
| Scope control | 2 probes | 2/2 planned probes, 100% | 2 | 0 | 100% | Adapter does not implement precision/recall/stability metrics or hook execution subprocesses. |
| Total adversarial probes | 39 probes | 39/39 planned probes, 100% | 39 | 0 | 100% | Excludes baseline playback checks. |

#### Baseline Playback Table

| Command/check | Status | Notes |
| --- | --- | --- |
| `python3 -m unittest tests.test_arbor_skill.HookTriggerSimulatedDispatcherTests` | Pass | 15 tests passed. |
| `python3 -m unittest tests/test_arbor_skill.py` | Pass | 90 tests passed. |
| `python3 -m json.tool docs/reviews/hook-trigger-scenarios.json` | Pass | Sidecar JSON parsed successfully. |
| `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor` | Pass | Standalone skill validation passed. |
| `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor` | Pass | Packaged skill validation passed. |
| `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f10-r1-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py tests/test_arbor_skill.py` | Pass | No compile errors. |
| `python3 scripts/simulated_dispatcher.py --scenario-id H1-P001` | Pass | Emitted dispatcher-contract JSON with Hook 1 trigger. |
| `env COVERAGE_FILE=/private/tmp/arbor-f10-r1-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py` | Pass | 90 tests passed under coverage. |
| `env COVERAGE_FILE=/private/tmp/arbor-f10-r1-coverage conda run -n arbor python -m coverage report` | Pass | Total coverage 89%; `scripts/simulated_dispatcher.py` coverage 77%. |

#### Scenario Test Matrix

| Scenario ID | Scenario | Category | Expected behavior | Observed result | Status |
| --- | --- | --- | --- | --- | --- |
| F10-R1-S1 | Full corpus load | Corpus loading | Load all 150 Markdown scenarios and expand sidecar expectations. | 150 scenarios loaded with preserved ids, expressions, and labels. | Pass |
| F10-R1-S2 | Contract shape for every scenario | Contract shape | Every scenario emits `hooks`, `decision`, `confidence`, `requires_agent_judgment`, `optional_args`, and `reason`. | Exact contract keys emitted for all scenarios. | Pass |
| F10-R1-S3 | H1 single-hook trigger | Representative scenarios | H1 rows should trigger `arbor.session_startup_context`. | `H1-P001` triggered Hook 1 with high confidence. | Pass |
| F10-R1-S4 | H2 single-hook trigger | Representative scenarios | H2 rows should trigger `arbor.in_session_memory_hygiene`. | `H2-P001` triggered Hook 2. | Pass |
| F10-R1-S5 | H3 single-hook trigger | Representative scenarios | H3 rows should trigger `arbor.goal_constraint_drift`. | `H3-P001` triggered Hook 3. | Pass |
| F10-R1-S6 | NONE scenario | Sidecar semantics | NONE rows should return `decision=none` and no hooks. | `N-P001` and all NONE rows returned no hooks. | Pass |
| F10-R1-S7 | Multi-hook trigger | Representative scenarios | Structured multi-hook rows should return all expected hooks. | `M-P002` returned Hook 1 plus Hook 2. | Pass |
| F10-R1-S8 | Ambiguous agent-judgment scenario | Representative scenarios | Ambiguous rows should return no hooks and require agent judgment. | `M-P004` and `M-P017` returned `ambiguous`, no hooks, and low confidence. | Pass |
| F10-R1-S9 | Selected docs optional args | Representative scenarios | Hook 3 selected-doc args should pass through. | `H3-P002` returned `--doc docs/constraints.md`. | Pass |
| F10-R1-S10 | Outside-root placeholder without fixture summary | Representative scenarios | Adapter may preserve the placeholder when no fixture summary is provided. | `EV-P010` returned `/outside/project-map.md`. | Pass |
| F10-R1-S11 | Outside-root placeholder with fixture summary | Fixture integration | Adapter should resolve placeholder from fixture summary when provided. | API and CLI paths resolved to the generated outside fixture path. | Pass |
| F10-R1-S12 | Forbidden hooks | Sidecar semantics | Selected hooks should never overlap `forbidden_hooks`. | No overlap found across all scenarios. | Pass |
| F10-R1-S13 | Optional args subset | Contract shape | `optional_args` should only be attached to selected hooks. | All optional arg keys were selected hooks. | Pass |
| F10-R1-S14 | Error handling | CLI/error handling | Missing corpus, malformed sidecar, and unknown ids should fail cleanly. | Controlled parser errors; no tracebacks. | Pass |
| F10-R1-S15 | Scope control | Scope control | Feature should not implement hook execution or semantic metrics. | No metric implementation or hook-execution subprocess found in adapter. | Pass |

#### Impact Assessment

| Functional area | Risk checked | Result | Assessment |
| --- | --- | --- | --- |
| Dispatcher contract readiness | Future harness should be able to parse a stable output shape for every corpus scenario. | Contract probes passed. | No negative impact found. |
| Sidecar scoring semantics | Adapter should preserve accepted expected/optional/forbidden hook semantics without inventing classifier behavior. | Sidecar semantics probes passed. | No negative impact found. |
| Fixture integration | Adapter should consume Feature 9 summaries for outside-root selected-doc scenarios. | Fixture integration probes passed. | No negative impact found. |
| Determinism | Simulated adapter should be stable for repeatable Stage B plumbing tests. | Determinism probes passed. | No negative impact found. |
| Scope boundary | Adapter should not report real semantic metrics or execute hooks. | Scope probes passed. | No negative impact found. |
| Prior feature behavior | Feature 8 sidecar and Feature 9 fixture assumptions should remain consumable. | JSON parsing, hook id alignment, and fixture-summary probes passed. | No negative impact found. |

#### Optimization Suggestions

| Priority | Suggestion | Rationale | Follow-up owner |
| --- | --- | --- | --- |
| P1 | In the next harness feature, treat simulated dispatcher results as fixture/plumbing observations only, not semantic-quality metrics. | The adapter echoes sidecar expectations, so precision and recall would be circular before a real dispatcher exists. | Stage B harness owner. |
| P2 | Execute selected hooks through generated `.codex/hooks.json` entrypoints rather than calling hook functions directly. | This preserves the accepted project-level hook contract and catches packaging/registration drift. | Hook execution harness owner. |
| P3 | Keep the outside-root fixture-summary path replacement test when hook execution is added. | It proves the selected-doc rejection path can be exercised without leaking outside content. | Stage B harness owner. |
