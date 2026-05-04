# Feature 25: Real Runtime Full Corpus

## Goal

Run the full 150-scenario hook-trigger corpus through the authenticated installed-plugin runtime path and make the report distinguish hook execution success from semantic trigger success.

## Scope

- Use `plugin-runtime-codex-exec` with copied local auth and project-registered hook entrypoints.
- Preserve the Feature 24 selected replay/progress path for focused real-runtime failure replay.
- Accept model-natural single-value optional args for H1/H2 without making the adapter a bottleneck.
- Fail corpus reports when real-runtime semantic metrics are reported and contain failed scenarios.

Out of scope:

- Prompt-tuning or changing the scenario corpus expectations for the remaining semantic misses.
- Repeated full-corpus stability scoring.

## Implementation

- `scripts/plugin_trigger_adapters.py`
  - H1/H2 single-value optional args now accept bare values and normalize them to the canonical equals form:
    - `--stat` -> `--diff-args=--stat`;
    - `-- fix-parser.txt` -> `--diff-args=-- fix-parser.txt`;
    - `--max-count=10 --decorate --oneline` -> `--git-log-args=--max-count=10 --decorate --oneline`.
  - Empty H1/H2 values still fail adapter validation.
  - H3 document args remain structured and strict.
- `scripts/evaluate_hook_triggers.py`
  - Corpus-mode adapter contract errors are captured per scenario, written to progress JSONL, and block semantic scoring instead of aborting the whole run.
  - Semantic metric status now includes a `passed` boolean.
  - Corpus report `passed` now requires hook execution success and, when real semantic metrics are reported, zero semantic failed scenarios.
  - CLI exits non-zero whenever the produced report has `passed=false`.
- `tests/test_arbor_skill.py`
  - Added regressions for H1/H2 bare single-value normalization.
  - Added corpus continuation coverage for adapter errors.
  - Added a regression proving real-runtime semantic failures fail the corpus report.
  - Added a CLI exit-code regression for failed corpus reports.

## Validation

- `python3 -m unittest tests.test_arbor_skill.HookTriggerPluginAdapterTests tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 71 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f25-r4-pycache python3 -m py_compile scripts/evaluate_hook_triggers.py scripts/plugin_trigger_adapters.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check scripts/evaluate_hook_triggers.py scripts/plugin_trigger_adapters.py tests/test_arbor_skill.py --no-cache`: passed.
- Focused real-runtime replay after optional-args fix:
  - `H2-P015,M-P003,M-P005`: 3/3 scenarios passed, 5/5 hook executions passed, semantic gates passed.
- Full authenticated real-runtime corpus after optional-args fix:
  - 150/150 execution scenarios passed.
  - 108/108 selected hook executions passed.
  - Adapter contract gate passed: 0 adapter errors.
  - Runtime availability gate passed: 0 blockers.
  - Hook execution gate passed: 0 assertion failures, 0 outside-root leaks, 0 unintended writes.
  - Semantic metrics reported with 146/150 semantic scenarios passed.
  - Remaining semantic failures: `CL-P020`, `EV-P010`, `H1-P013`, `H3-P017`.
- Focused real-runtime semantic-failure replay after report-status fix:
  - `CL-P020,EV-P010,H1-P013,H3-P017`: report `passed=false`, semantic `passed=false`, process exit code 1.

## Current Findings

| ID | Priority | Status | Finding |
| --- | --- | --- | --- |
| F25-R1-001 | P1 | Fixed | Real runtime emitted bare H2 diff optional values; the adapter rejected those legal single-value forms before hook execution. |
| F25-R1-002 | P1 | Fixed | Full corpus reports could show top-level `passed=true` even when real semantic metrics contained failed scenarios. |
| F25-R1-003 | P1 | Open | Real runtime still misses 4/150 semantic cases: two H3 abstentions, one H2 abstention, and one H1/H2 confusion. |

## Status

Feature 25 is implemented for full-corpus real-runtime execution and honest failure reporting. The execution chain is clean; the remaining work is semantic trigger quality for the four failing scenarios.

## Reviewer Round 1 - 2026-05-03

### Findings

| ID | Priority | Location | Status | Finding |
| --- | --- | --- | --- | --- |
| F25-R1-003 | P1 | Runtime semantic quality | Confirmed open | The execution chain is clean, but the feature is not semantically converged while `CL-P020`, `EV-P010`, `H1-P013`, and `H3-P017` still fail real-runtime trigger expectations. |
| F25-R1-004 | P2 | Full-corpus validation evidence | Open | The review records aggregate authenticated full-corpus metrics, but it does not persist or link the raw full-corpus JSON/progress artifact or list the observed decision/hook details for each semantic miss. Because the full authenticated run is expensive to replay, future rounds need a durable artifact or detailed failure table to audit regression deltas without rerunning all 150 scenarios. |

### Test Matrix

| Test category | Test cases / probes | Coverage focus | Coverage | Pass rate | Result |
| --- | ---: | --- | ---: | ---: | --- |
| Feature contract review | 1 | Goal, scope, implementation claims, current findings | 100% | 100% | Passed |
| Focused adapter plus harness regression | 71 | H1/H2 bare optional values, adapter-error continuation, semantic status, CLI failure paths | 100% | 100% | Passed |
| Full project regression | 181 | `tests/test_arbor_skill.py` after Feature 25 changes | 100% | 100% | Passed |
| Static checks | 3 | `py_compile`, `ruff`, `git diff --check` | 100% | 100% | Passed |
| Independent normalization probes | 3 | H2 bare `--stat`, H2 bare pathspec, H1 bare git-log args | 100% | 100% | Passed |
| Independent corpus-status probes | 2 | Adapter-error continuation and semantic-failure report status | 100% | 100% | Passed |
| Scenario sidecar validation | 1 | `hook-trigger-scenarios.json` parseability | 100% | 100% | Passed |
| Semantic-miss control replay | 4 | Sidecar-backed execution for the four known failing real-runtime scenario ids | 100% | 100% | Passed |
| Authenticated full real-runtime rerun | 0 | Live 150-scenario `plugin-runtime-codex-exec` corpus | 0% live replay | N/A | Not rerun in this review round |

### Scenario Tests

| Scenario | Command / method | Expected | Actual | Result |
| --- | --- | --- | --- | --- |
| H1/H2 bare optional args | Direct adapter contract probe | Bare values normalize to canonical single-value option forms | 3/3 normalized correctly | Passed |
| Adapter-error continuation | Patched `trigger_with_adapter` to raise once, then return a valid none decision | Corpus continues, progress records the adapter error, report fails | `passed=false`, failed scenario `H1-P001`, adapter error count 1 | Passed |
| Semantic failure status | Patched real-runtime adapter to return a valid but semantically wrong decision for `H1-P001` | Semantic metrics report and make top-level report fail | `semantic_reported=true`, `semantic_passed=false`, `passed=false` | Passed |
| Known semantic-miss controls | Sidecar baseline selected replay for `CL-P020,EV-P010,H1-P013,H3-P017` | Harness and hook execution remain clean for these scenario contracts | 4/4 execution scenarios passed; outside-root H3 rejection passed | Passed |
| Focused regression replay | `python3 -m unittest tests.test_arbor_skill.HookTriggerPluginAdapterTests tests.test_arbor_skill.HookTriggerExecutionHarnessTests` | Focused Feature 25 tests remain green | 71 tests passed | Passed |
| Full regression replay | `python3 -m unittest tests/test_arbor_skill.py` | Existing Arbor test suite remains green | 181 tests passed | Passed |

### Optimization Suggestions

| Area | Recommendation |
| --- | --- |
| Semantic closure | Treat `F25-R1-003` as the blocking Feature 25 convergence item. Resolve the four misses with prompt guidance, scenario expectation adjustment, or both, then replay the four-case batch before another full corpus. |
| Evidence retention | Store the authenticated full-corpus JSON report or a stable artifact path/checksum, plus a table of the four observed failing decisions, so later review rounds can compare deltas without relying only on aggregate numbers. |
| Preflight set | Keep the independent normalization and corpus-status probes as a cheap preflight before any future authenticated full-corpus run. |

## Developer Response - Round 1 Fix

### Changes

- `scripts/plugin_trigger_adapters.py`
  - Added concise hook-selection boundary guidance to the real runtime prompt:
    - initialization/onboarding/project memory flow selects `arbor.session_startup_context`;
    - temporary, in-flight, current-session, or not-long-term notes select `arbor.in_session_memory_hygiene`;
    - permanent naming, goal, constraint, map, architecture, or workflow changes select `arbor.goal_constraint_drift`;
    - outside-root selected-doc runtime events should still select the relevant hook and let hook execution enforce project-local safety.
  - Added `outside_path` to the sanitized runtime project state. This exposes only the path needed for safety-boundary hook execution, not outside file content or sidecar scoring fields.
- `scripts/evaluate_hook_triggers.py`
  - Added `--report-json` so expensive authenticated runtime runs can persist the final report JSON instead of relying on terminal output.
- `tests/test_arbor_skill.py`
  - Added prompt-boundary regression checks.
  - Added a non-circular runtime-input test proving `outside_path` is available while outside file content and sidecar scoring fields remain absent.
  - Extended the selected corpus CLI test to verify `--report-json` writes the same report emitted on stdout.

### Review Feedback Addressed

| Review item | Resolution |
| --- | --- |
| `F25-R1-003`: four real-runtime semantic misses | Fixed in focused replay. The runtime now selects the expected hooks for `CL-P020`, `EV-P010`, `H1-P013`, and `H3-P017`; semantic metrics report 4/4 passed. |
| `F25-R1-004`: no durable evidence artifact or detailed miss table | Fixed for forward runs with `--report-json`; the latest focused replay artifacts are persisted under `docs/reviews/artifacts/`. This review now also records the observed decision/hook table below. |

### Latest Focused Real-Runtime Replay

Artifacts:

- Report JSON: `docs/reviews/artifacts/feature-25-semantic-replay-report.json`
- Progress JSONL: `docs/reviews/artifacts/feature-25-semantic-replay-progress.jsonl`

Command:

```bash
python3 scripts/evaluate_hook_triggers.py \
  --scenario-ids CL-P020,EV-P010,H1-P013,H3-P017 \
  --work-root /private/tmp/arbor-f25-r1-semantic-replay-r2 \
  --trigger-adapter plugin-runtime-codex-exec \
  --auth-source-home ~ \
  --runtime-timeout 90 \
  --progress-jsonl docs/reviews/artifacts/feature-25-semantic-replay-progress.jsonl \
  --report-json docs/reviews/artifacts/feature-25-semantic-replay-report.json
```

Result:

- `passed=true`
- 4/4 scenarios passed.
- 4/4 selected hook executions passed.
- Adapter contract gate passed: 0 adapter errors.
- Runtime availability gate passed: 0 blockers.
- Hook execution gate passed: 0 assertion failures, 0 outside-root leaks, 0 unintended writes.
- Semantic metrics passed: 4/4 passed scenarios, no failed semantic scenarios.
- `EV-P010` selected `arbor.goal_constraint_drift` with the outside `--doc` path; the hook rejected it with return code 2 and passed the outside-root safety assertions.

Observed decision table:

| Scenario | Expected | Observed decision | Observed hooks | Hook result |
| --- | --- | --- | --- | --- |
| `CL-P020` | H2 | `trigger` | `arbor.in_session_memory_hygiene` | Passed |
| `EV-P010` | H3 | `trigger` | `arbor.goal_constraint_drift` | Passed outside-root rejection |
| `H1-P013` | H1 | `trigger` | `arbor.session_startup_context` | Passed |
| `H3-P017` | H3 | `trigger` | `arbor.goal_constraint_drift` | Passed |

### Validation

- `python3 -m unittest tests.test_arbor_skill.HookTriggerPluginAdapterTests tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 72 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f25-r1-review2-pycache python3 -m py_compile scripts/evaluate_hook_triggers.py scripts/plugin_trigger_adapters.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check scripts/evaluate_hook_triggers.py scripts/plugin_trigger_adapters.py tests/test_arbor_skill.py --no-cache`: passed.
- Focused authenticated runtime replay for `CL-P020,EV-P010,H1-P013,H3-P017`: passed, exit code 0, persisted report/progress artifacts.

### Status

Round 1 review findings are addressed in focused validation. The next expensive check is a full 150-scenario authenticated runtime rerun using `--report-json` so the complete report is retained.

## Reviewer Round 2 - 2026-05-03

### Findings

| ID | Priority | Location | Status | Finding |
| --- | --- | --- | --- | --- |
| F25-R1-003 | P1 | Runtime semantic quality | Closed for focused replay | Replayed from persisted focused artifacts. `CL-P020`, `EV-P010`, `H1-P013`, and `H3-P017` now pass under `plugin-runtime-codex-exec` in the focused replay report, with semantic metrics reported and passed. |
| F25-R1-004 | P2 | Full-corpus validation evidence | Partially addressed | `--report-json` and the focused replay artifacts fix evidence retention for forward/focused runs, but the original 150-scenario authenticated full-corpus aggregate is still not backed by a retained full-corpus report artifact. Keep this finding open until the next full authenticated rerun is persisted. |

### Test Matrix

| Test category | Test cases / probes | Coverage focus | Coverage | Pass rate | Result |
| --- | ---: | --- | ---: | ---: | --- |
| Developer response review | 1 | Round 1 fix notes, finding dispositions, artifact links | 100% | 100% | Passed |
| Persisted focused artifact verification | 2 | Report JSON and progress JSONL under `docs/reviews/artifacts/` | 100% | 100% | Passed |
| Focused adapter plus harness regression | 72 | Prompt-boundary tests, outside-path input, `--report-json`, adapter/harness regressions | 100% | 100% | Passed |
| Full project regression | 182 | `tests/test_arbor_skill.py` after Round 1 fix | 100% | 100% | Passed |
| Static checks | 3 | `py_compile`, `ruff`, `git diff --check` | 100% | 100% | Passed |
| Local report-json replay | 4 | Selected sidecar replay for the four prior miss ids with progress and report output | 100% | 100% | Passed |
| Authenticated focused replay rerun | 0 live reruns | Live `plugin-runtime-codex-exec` replay | 0% live replay | N/A | Verified persisted artifact only |
| Authenticated full-corpus rerun | 0 live reruns | Full 150-scenario `plugin-runtime-codex-exec` corpus with `--report-json` | 0% live replay | N/A | Still pending |

### Scenario Tests

| Scenario | Command / method | Expected | Actual | Result |
| --- | --- | --- | --- | --- |
| Persisted focused replay report | Parsed `docs/reviews/artifacts/feature-25-semantic-replay-report.json` | `plugin-runtime-codex-exec`, selected scope, 4/4 passed, semantic metrics passed | Report matched all expected fields; failed semantic scenarios list was empty | Passed |
| Persisted focused progress | Parsed `docs/reviews/artifacts/feature-25-semantic-replay-progress.jsonl` | Four rows for `CL-P020`, `EV-P010`, `H1-P013`, `H3-P017`, all passed | 4/4 rows present and passed | Passed |
| Local report-json write path | `evaluate_hook_triggers.py --scenario-ids CL-P020,EV-P010,H1-P013,H3-P017 --trigger-adapter sidecar-baseline --progress-jsonl ... --report-json ...` | Report file and progress file are written, selected replay passes | Report JSON had 4 total scenarios and progress JSONL had 4 rows | Passed |
| Focused regression replay | `python3 -m unittest tests.test_arbor_skill.HookTriggerPluginAdapterTests tests.test_arbor_skill.HookTriggerExecutionHarnessTests` | New prompt/evidence regressions stay green | 72 tests passed | Passed |
| Full regression replay | `python3 -m unittest tests/test_arbor_skill.py` | Existing Arbor test suite remains green | 182 tests passed | Passed |

### Optimization Suggestions

| Area | Recommendation |
| --- | --- |
| Full-corpus closure | Run the full 150-scenario authenticated `plugin-runtime-codex-exec` corpus with `--report-json` before marking Feature 25 release-ready. This is necessary because prompt guidance changed and focused replay cannot prove no regressions across the other 146 scenarios. |
| Finding status | Treat `F25-R1-003` as closed for the four known misses, but keep `F25-R1-004` partially open until a retained full-corpus artifact exists. |
| Artifact hygiene | Keep the focused artifacts under `docs/reviews/artifacts/`; for the full rerun, use stable names that include whether the report is selected or full corpus. |

## Developer Response - Round 2 Fix

### Changes

- `scripts/plugin_trigger_adapters.py`
  - Dropped lone `--` values from H1/H2 single-value optional-arg normalization. A bare end-of-options separator carries no extra retrieval value, so the hook now falls back to its default full context packet instead of receiving `--diff-args=--`.
- `skills/arbor/scripts/run_memory_hygiene_hook.py`
- `skills/arbor/scripts/collect_project_context.py`
  - Accepted argparse's empty-list edge case for `--diff-args=--` and `--git-log-args=--` without emitting a traceback.
- `plugins/arbor/skills/arbor/scripts/run_memory_hygiene_hook.py`
- `plugins/arbor/skills/arbor/scripts/collect_project_context.py`
  - Synchronized the packaged plugin payload with the standalone skill payload.
- `tests/test_arbor_skill.py`
  - Added regressions for dropping lone H1/H2 `--` optional args.
  - Added CLI regressions proving the startup and memory hook scripts handle the lone separator edge case cleanly.

### Review Feedback Addressed

| Review item | Resolution |
| --- | --- |
| `F25-R1-004`: retained full-corpus evidence missing | Closed. A full authenticated 150-scenario `plugin-runtime-codex-exec` rerun now has retained report and progress artifacts under `docs/reviews/artifacts/`. |
| Optimization: stable full-corpus artifact names | Implemented with `feature-25-full-corpus-r4-report.json` and `feature-25-full-corpus-r4-progress.jsonl`. |

### Latest Full Real-Runtime Corpus

Artifacts:

- Report JSON: `docs/reviews/artifacts/feature-25-full-corpus-r4-report.json`
- Progress JSONL: `docs/reviews/artifacts/feature-25-full-corpus-r4-progress.jsonl`

Command:

```bash
python3 scripts/evaluate_hook_triggers.py \
  --all \
  --work-root /private/tmp/arbor-f25-full-runtime-r7 \
  --trigger-adapter plugin-runtime-codex-exec \
  --auth-source-home ~ \
  --runtime-timeout 300 \
  --progress-jsonl docs/reviews/artifacts/feature-25-full-corpus-r4-progress.jsonl \
  --report-json docs/reviews/artifacts/feature-25-full-corpus-r4-report.json
```

Result:

- `passed=true`
- 150/150 scenarios passed.
- 111/111 selected hook executions passed.
- Adapter contract gate passed: 0 adapter errors.
- Runtime availability gate passed: 0 blockers.
- Hook execution gate passed: 0 assertion failures, 0 outside-root leaks, 0 unintended writes.
- Semantic metrics reported and passed.
- Per-hook precision/recall:
  - `arbor.session_startup_context`: precision 1.0, recall 1.0.
  - `arbor.in_session_memory_hygiene`: precision 1.0, recall 1.0.
  - `arbor.goal_constraint_drift`: precision 1.0, recall 1.0.
- `NONE` false-positive rate: 0.0.
- Near-miss false-positive rate: 0.0.
- Multi-hook required recall: 1.0.
- Stability remains unreported because this is a single full real-runtime corpus pass.

### Validation

- `python3 -m unittest tests.test_arbor_skill.ProjectMemoryStartupContextTests tests.test_arbor_skill.MemoryHygieneHookTests tests.test_arbor_skill.HookTriggerPluginAdapterTests`: 66 tests passed.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H2-P008 --work-root /private/tmp/arbor-f25-h2p008-r4-runtime --trigger-adapter plugin-runtime-codex-exec --auth-source-home ~ --runtime-timeout 300 --report-json docs/reviews/artifacts/feature-25-h2p008-r4-report.json`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f25-full-runtime-r7 --trigger-adapter plugin-runtime-codex-exec --auth-source-home ~ --runtime-timeout 300 --progress-jsonl docs/reviews/artifacts/feature-25-full-corpus-r4-progress.jsonl --report-json docs/reviews/artifacts/feature-25-full-corpus-r4-report.json`: passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 186 tests passed.
- `PYTHONPYCACHEPREFIX=/private/tmp/arbor_pycache python3 -m py_compile scripts/plugin_trigger_adapters.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/collect_project_context.py plugins/arbor/skills/arbor/scripts/run_memory_hygiene_hook.py plugins/arbor/skills/arbor/scripts/collect_project_context.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed.
- `git diff --check`: passed.
- `python3 -m json.tool docs/reviews/artifacts/feature-25-full-corpus-r4-report.json`: passed.

### Status

Feature 25 is now release-ready for the current scope. The remaining runtime metric not reported is repeated-run stability, which requires a separate repeated real-runtime corpus feature rather than blocking this single-pass full-corpus closure.

## Reviewer Round 3 - 2026-05-04

### Findings

| ID | Priority | Location | Status | Finding |
| --- | --- | --- | --- | --- |
| F25-R1-004 | P2 | Full-corpus validation evidence | Closed | Replayed from retained artifacts. `docs/reviews/artifacts/feature-25-full-corpus-r4-report.json` contains a full 150-scenario `plugin-runtime-codex-exec` report with `passed=true`, semantic metrics reported and passed, 0 adapter errors, 0 runtime blockers, 0 outside-root leaks, and 0 unintended writes. The matching progress JSONL has 150 rows. |
| F25-R3-NF1 | N/A | Feature 25 re-review | Closed | No new findings were added in this round. |

### Test Matrix

| Test category | Test cases / probes | Coverage focus | Coverage | Pass rate | Result |
| --- | ---: | --- | ---: | ---: | --- |
| Developer response review | 1 | Round 2 fix notes, full-corpus artifact names, status claim | 100% | 100% | Passed |
| Retained full-corpus artifact verification | 2 | Full report JSON and progress JSONL | 100% | 100% | Passed |
| Known miss replay within full artifact | 4 | `CL-P020`, `EV-P010`, `H1-P013`, `H3-P017` rows inside the full report | 100% | 100% | Passed |
| Focused script and adapter regression | 66 | Startup, memory hygiene, plugin adapter, lone separator regressions | 100% | 100% | Passed |
| Full project regression | 186 | `tests/test_arbor_skill.py` after Round 2 fix | 100% | 100% | Passed |
| Static checks | 3 | `py_compile`, `ruff`, `git diff --check` | 100% | 100% | Passed |
| CLI separator replay | 2 | `--git-log-args=--` and `--diff-args=--` | 100% | 100% | Passed |
| Packaged script sync | 2 | Standalone vs packaged startup and memory hook scripts | 100% | 100% | Passed |
| Local full report-json replay | 150 | Sidecar full corpus with report/progress output | 100% | 100% | Passed |

### Scenario Tests

| Scenario | Command / method | Expected | Actual | Result |
| --- | --- | --- | --- | --- |
| Retained full real-runtime report | Parsed `docs/reviews/artifacts/feature-25-full-corpus-r4-report.json` | Full `plugin-runtime-codex-exec` report is retained and gate-clean | 150/150 scenarios passed, 111/111 hook executions passed, semantic metrics passed | Passed |
| Retained full progress | Parsed `docs/reviews/artifacts/feature-25-full-corpus-r4-progress.jsonl` | One progress row per corpus scenario | 150 rows; all rows passed | Passed |
| Prior semantic misses inside full report | Inspected `CL-P020`, `EV-P010`, `H1-P013`, `H3-P017` | Each prior miss now selects the expected hook and passes | 4/4 passed; `EV-P010` used H3 outside-root rejection path safely | Passed |
| Lone separator startup CLI | `collect_project_context.py --git-log-args=--` | No traceback; startup packet renders | Command exited 0 | Passed |
| Lone separator memory CLI | `run_memory_hygiene_hook.py --diff-args=--` | No traceback; memory packet renders | Command exited 0 | Passed |
| Local full report-json path | `evaluate_hook_triggers.py --all --trigger-adapter sidecar-baseline --progress-jsonl ... --report-json ...` | Full report and progress files are written | 150/150 sidecar scenarios passed; 150 progress rows | Passed |
| Full regression replay | `python3 -m unittest tests/test_arbor_skill.py` | Existing Arbor suite remains green | 186 tests passed | Passed |

### Optimization Suggestions

| Area | Recommendation |
| --- | --- |
| Stability boundary | Keep repeated real-runtime stability outside Feature 25 unless the release scope explicitly requires repeated full authenticated runs. |
| Artifact retention | Keep both the full report and progress artifacts under `docs/reviews/artifacts/`; avoid replacing them with only aggregate prose in later cleanup. |
