# Feature 17 Review: Codex Exec Plugin Runtime Trigger Adapter

## Development Target

Add the first real runtime trigger adapter for Arbor behind the existing adapter boundary. The adapter should use an isolated installed Arbor plugin runtime through `codex exec`, ask for the standard trigger decision JSON contract, and keep runtime blockers separate from semantic hook decisions.

This feature validates the runtime adapter path for single-scenario/blocker behavior. It does not yet report full-corpus semantic precision, recall, false-positive rate, or stability metrics.

## Scope

In scope:

- Add `plugin-runtime-codex-exec` to `scripts/plugin_trigger_adapters.py`.
- Use the non-circular runtime input from Feature 14.
- Install and enable `arbor@arbor-local` in an isolated `HOME`.
- Run `codex exec --ephemeral --json --output-schema --output-last-message` for trigger decision output.
- Parse and validate the returned trigger decision contract.
- Return a valid ambiguous blocker decision when runtime execution is unavailable.
- Keep hook execution disabled unless a selected hook decision is returned and the existing harness executes it normally.

Out of scope:

- Full 150-scenario semantic metric reporting.
- Changing the sidecar-baseline adapter.
- Executing hooks from inside the trigger adapter.
- Updating `.codex/memory.md`, `AGENTS.md`, or project hook files from the trigger adapter.
- Treating network/auth/runtime blockers as semantic `NONE` decisions.

## Implementation Summary

- Added `plugin-runtime-codex-exec` to the adapter choices.
- Added `TRIGGER_DECISION_SCHEMA` for Codex exec structured output.
- Added `build_codex_exec_trigger_prompt` to provide outcome-first trigger selection instructions and the non-circular runtime input.
- Added `run_codex_exec_trigger`:
  - validates no sidecar scoring fields are present;
  - verifies Codex CLI exists;
  - adds the repo-local marketplace in a temp `HOME`;
  - enables `arbor@arbor-local`;
  - calls `codex exec` with output schema and output-last-message;
  - parses and validates returned JSON;
  - classifies runtime failures as ambiguous blocker decisions.
- Updated `evaluate_hook_triggers.py` semantic metric status so `plugin-runtime-codex-exec` is recognized as a runtime adapter but still not metric-producing in this feature.
- Added tests for valid runtime decision parsing, network blocker classification, and harness compatibility with a blocker decision.

## Developer Validation

- `python3 -m unittest tests.test_arbor_skill.HookTriggerPluginAdapterTests tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 23 tests passed.
- `python3 -m unittest tests.test_arbor_skill.HookTriggerPluginAdapterTests`: 9 tests passed.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-f17-runtime-smoke --trigger-adapter plugin-runtime-codex-exec`: passed; runtime returned `decision=ambiguous`, `hooks=[]`, and `reason=Plugin runtime unavailable: network_unavailable...`; no hooks executed.
- `python3 -m unittest tests/test_arbor_skill.py`: 123 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f17-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py scripts/probe_plugin_runtime.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed.
- `python3 scripts/validate_plugin_install.py`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f17-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios, 103/103 hook executions, outside-root leaks 0, unintended writes 0.
- `env COVERAGE_FILE=/private/tmp/arbor-f17-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 123 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f17-coverage conda run -n arbor python -m coverage report`: total coverage 87%; `scripts/plugin_trigger_adapters.py` coverage 80%.

## Review Feedback

### Round 1 - 2026-05-03

#### Findings

| ID | Priority | Location | Result | Finding |
| --- | --- | --- | --- | --- |
| F17-R1-1 | P2 | `scripts/plugin_trigger_adapters.py:292-323` | Added | Detect trigger-adapter project file mutations before accepting runtime decisions. |

`run_codex_exec_trigger` runs `codex exec` in the fixture project root and accepts a valid trigger decision without checking whether the runtime edited project memory or hook files. An adversarial mocked runtime changed `AGENTS.md` while returning a valid ambiguous decision, and the adapter accepted the decision. Feature 17 explicitly keeps updates to `.codex/memory.md`, `AGENTS.md`, and project hook files out of scope for trigger adapters, so these mutations should be detected and rejected before the harness proceeds.

#### Test Matrix

| Test category | Test cases / checks | Coverage | Passed | Pass rate | Notes |
| --- | ---: | --- | ---: | ---: | --- |
| Focused plugin adapter and execution harness replay | 23 | Feature 17 adapter parsing, blocker classification, and harness compatibility | 23 | 100% | `HookTriggerPluginAdapterTests` plus `HookTriggerExecutionHarnessTests`. |
| Full unit regression | 123 | Arbor script, hook, trigger adapter, plugin install, and probe tests | 123 | 100% | No existing unit regression failed. |
| Runtime smoke via `plugin-runtime-codex-exec` | 1 | Real Codex exec path for `H1-P001` with isolated installed plugin | 1 | 100% | Runtime classified as `network_unavailable`, `decision=ambiguous`, `hooks=[]`, no hook execution. |
| Sidecar baseline corpus replay | 150 scenarios / 103 hook executions | Existing Stage B harness and hook execution baseline | 150 / 103 | 100% | No outside-root leaks or unintended writes. |
| Static validation | 5 | `py_compile`, `ruff`, plugin install validation, standalone skill validate, packaged skill validate | 5 | 100% | All passed. |
| Coverage run | 1 | Full unittest coverage snapshot | 1 | 100% | Total coverage 87%; `scripts/plugin_trigger_adapters.py` 80%. |
| Adversarial side-effect probe | 1 | Trigger adapter project-file mutation boundary | 0 | 0% | Mocked runtime changed `AGENTS.md`; adapter accepted valid JSON and did not detect mutation. |

#### Scenario Testing

| Scenario | Adapter / path | Expected behavior | Actual result | Status |
| --- | --- | --- | --- | --- |
| Valid runtime decision parsing | Mocked `plugin-runtime-codex-exec` | Parse schema-valid trigger decision and return selected hook | Returned valid `trigger` decision in focused replay | Pass |
| Runtime network blocker | Mocked and real `plugin-runtime-codex-exec` | Return ambiguous blocker, no semantic `NONE`, no hook execution | Returned `decision=ambiguous`, `hooks=[]`, reason classified as `network_unavailable` | Pass |
| Harness blocker compatibility | `evaluate_scenario` with plugin runtime blocker | Do not execute hooks when adapter returns no selected hooks | Passed with empty executions | Pass |
| Existing sidecar baseline stability | `sidecar-baseline --all` | Preserve 150-scenario hook execution-chain quality | 150/150 scenarios passed, 103/103 hook executions passed | Pass |
| Trigger adapter side-effect boundary | Mocked `codex exec` mutating `AGENTS.md` while writing valid output JSON | Reject or classify mutation as runtime blocker before accepting decision | Accepted decision and left `AGENTS.md` modified | Fail |

#### Optimization Suggestions

| Area | Suggestion |
| --- | --- |
| Side-effect guard | Snapshot `AGENTS.md`, `.codex/memory.md`, and `.codex/hooks.json` before `codex exec`; after runtime returns, reject or convert to a runtime blocker if any tracked file is created, deleted, or changed by the trigger adapter. |
| Diagnostics | Include the mutated relative path list in the blocker reason or adapter error so future review can distinguish runtime unavailability from contract violations. |
| Regression coverage | Add a focused test where mocked `run_command` mutates `AGENTS.md` and writes a schema-valid trigger decision; the expected result should be rejection/blocker rather than accepting the decision. |

#### Round 1 Verdict

Needs changes. The runtime-blocker and harness paths replay cleanly, and the existing sidecar baseline was not affected, but the adapter currently does not enforce Feature 17's no-project-file-update boundary.

## Developer Response - Round 1 Fix

### Changes

- Fixed `F17-R1-1` by snapshotting trigger-adapter protected project paths before `codex exec`.
- Protected paths are `AGENTS.md`, `.codex/memory.md`, and `.codex/hooks.json`.
- If the runtime creates, deletes, changes, or replaces a protected path with a non-file, the adapter restores the pre-run state and returns a valid ambiguous blocker decision.
- The blocker reason includes `project_file_mutation:<paths>` so review can distinguish contract violations from ordinary runtime unavailability.
- Added regression coverage for a mocked runtime that mutates `AGENTS.md` while returning schema-valid trigger JSON.
- Added regression coverage for a mocked runtime that replaces `.codex/memory.md` with a directory while returning schema-valid trigger JSON.
- Kept semantic trigger metrics out of scope; the real runtime smoke still reports a runtime blocker in this environment.

### Validation

- `python3 -m unittest tests.test_arbor_skill.HookTriggerPluginAdapterTests`: 11 tests passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 125 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f17-r1-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py scripts/probe_plugin_runtime.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed.
- `python3 scripts/validate_plugin_install.py`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-f17-r1-runtime-smoke-2 --trigger-adapter plugin-runtime-codex-exec`: passed; runtime returned `decision=ambiguous`, `hooks=[]`, and `reason=Plugin runtime unavailable: network_unavailable...`; no hooks executed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f17-r1-corpus-sidecar-2 --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios, 103/103 hook executions, outside-root leaks 0, unintended writes 0.
- `env COVERAGE_FILE=/private/tmp/arbor-f17-r1-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 125 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f17-r1-coverage conda run -n arbor python -m coverage report`: total coverage 87%; `scripts/plugin_trigger_adapters.py` coverage 81%.

### Finding Closure

| Finding | Status | Evidence |
| --- | --- | --- |
| F17-R1-1 | Addressed | `run_codex_exec_trigger` now snapshots and restores protected project paths around `codex exec`; focused mutation tests cover both ordinary file mutation and non-file path replacement. |

### Round 2 - 2026-05-03

#### Findings

| ID | Priority | Location | Result | Finding |
| --- | --- | --- | --- | --- |
| F17-R2 | - | - | No new findings | Round 1 mutation-boundary finding replayed cleanly. |

`F17-R1-1` is closed. The adapter now snapshots `AGENTS.md`, `.codex/memory.md`, and `.codex/hooks.json` before runtime execution, restores protected paths after illegal runtime mutation, and returns a valid ambiguous blocker with `project_file_mutation:<paths>`.

#### Test Matrix

| Test category | Test cases / checks | Coverage | Passed | Pass rate | Notes |
| --- | ---: | --- | ---: | ---: | --- |
| Focused plugin adapter and execution harness replay | 25 | Feature 17 adapter parsing, blocker classification, mutation restore, and harness compatibility | 25 | 100% | Includes the new file-mutation and non-file path replacement regressions. |
| Incremental adversarial mutation probes | 3 | Protected path deletion, protected path recreation, nonzero runtime exit plus mutation | 3 | 100% | All returned `project_file_mutation:<path>` blockers and restored original protected file contents. |
| Full unit regression | 125 | Arbor script, hook, trigger adapter, plugin install, and probe tests | 125 | 100% | No existing unit regression failed. |
| Runtime smoke via `plugin-runtime-codex-exec` | 1 | Real Codex exec path for `H1-P001` with isolated installed plugin | 1 | 100% | Runtime classified as `network_unavailable`, `decision=ambiguous`, `hooks=[]`, no hook execution. |
| Sidecar baseline corpus replay | 150 scenarios / 103 hook executions | Existing Stage B harness and hook execution baseline | 150 / 103 | 100% | No outside-root leaks or unintended writes. |
| Static validation | 5 | `py_compile`, `ruff`, plugin install validation, standalone skill validate, packaged skill validate | 5 | 100% | All passed. |
| Coverage run | 1 | Full unittest coverage snapshot | 1 | 100% | Total coverage 87%; `scripts/plugin_trigger_adapters.py` 81%. |

#### Scenario Testing

| Scenario | Adapter / path | Expected behavior | Actual result | Status |
| --- | --- | --- | --- | --- |
| Round 1 file mutation replay | Mocked `codex exec` mutating `AGENTS.md` while writing valid output JSON | Reject/block and restore original file | Returned `project_file_mutation:AGENTS.md`; file restored | Pass |
| Non-file replacement replay | Mocked `codex exec` replacing `.codex/memory.md` with a directory | Reject/block and restore original file | Returned `project_file_mutation:.codex/memory.md`; file restored | Pass |
| Protected hook file deletion | Mocked runtime deleting `.codex/hooks.json` | Reject/block and restore original file | Returned `project_file_mutation:.codex/hooks.json`; file restored | Pass |
| Protected memory file recreation | Mocked runtime replacing `.codex/memory.md` contents | Reject/block and restore original file | Returned `project_file_mutation:.codex/memory.md`; file restored | Pass |
| Nonzero runtime exit plus mutation | Mocked runtime returning nonzero while mutating `AGENTS.md` | Prefer mutation contract blocker over ordinary runtime blocker and restore file | Returned `project_file_mutation:AGENTS.md`; file restored | Pass |
| Runtime network blocker | Real `plugin-runtime-codex-exec` | Return ambiguous blocker, no semantic `NONE`, no hook execution | Returned `decision=ambiguous`, `hooks=[]`, reason classified as `network_unavailable` | Pass |
| Existing sidecar baseline stability | `sidecar-baseline --all` | Preserve 150-scenario hook execution-chain quality | 150/150 scenarios passed, 103/103 hook executions passed | Pass |

#### Optimization Suggestions

| Area | Suggestion |
| --- | --- |
| Future semantic metrics | Keep the current blocker behavior separate from semantic `NONE` when the real plugin runtime becomes metric-producing. Runtime unavailable and runtime contract violations should remain excluded from precision/recall denominators until the scoring gate is explicitly designed. |
| Mutation diagnostics | The current `project_file_mutation:<paths>` reason is sufficient for this feature. If future review needs deeper forensics, include before/after kind only, not file body content. |

#### Round 2 Verdict

Accepted after re-review. The Round 1 mutation-boundary issue is addressed, no new findings were found, and existing hook execution baselines were not affected.
