# Feature 21 Review: Authenticated Installed Plugin Runtime Probe

## Development Target

Turn the previous blocker-only runtime probe into a true installed-plugin probe that can run against an authenticated local Codex runtime without mutating the user's real Codex config.

This feature is about installed `$arbor` reachability and side-effect validation. It is not the final 150-scenario semantic trigger evaluation.

## Scope

In scope:

- Copy `auth.json` from an explicit source home into the isolated runtime home when requested.
- Materialize the repo-local Arbor plugin into the isolated installed plugin cache expected by Codex runtime.
- Mark the isolated probe project trusted in the isolated config.
- Run `codex exec` with `$arbor` and require real side effects:
  - `AGENTS.md`
  - `.codex/memory.md`
  - `.codex/hooks.json`
  - all three `owner=arbor` hook ids
- Keep the real user `~/.codex/config.toml` untouched.
- Preserve runtime blocker classification instead of converting blocked runs into semantic quality.

Out of scope:

- Bypassing Codex approvals or sandbox globally.
- Shipping the probe or test harness in the Arbor plugin payload.
- Counting blocked authenticated runs as semantic trigger success or failure.

## Implementation Summary

- `scripts/probe_plugin_runtime.py`
  - Added explicit auth-copy support via `--auth-source-home`.
  - Added local plugin cache materialization under `.codex/plugins/cache/arbor-local/arbor/<version>`.
  - Added isolated project trust registration.
  - Added `stdin=subprocess.DEVNULL` for noninteractive CLI calls.
  - Moved default temporary probe roots under the repo with a non-hidden `arbor-runtime-*` prefix.
  - Added `-s <sandbox>` forwarding to `codex exec`.
- `scripts/plugin_trigger_adapters.py`
  - Materializes the local plugin cache before enabling `arbor@arbor-local` for `plugin-runtime-codex-exec`.
  - Keeps trigger-selection runtime in read-only mode so semantic trigger selection cannot mutate project files.
- `tests/test_arbor_skill.py`
  - Added regressions for auth copy, missing auth, cache materialization, and isolated project trust.
  - Updated trigger-adapter tests to require plugin-cache materialization.

## Runtime Findings

Authenticated runtime now gets past the previous network/auth/plugin-visibility blockers:

- isolated marketplace add: `ok`
- auth copy: `ok`
- plugin cache materialization: `ok`
- plugin enable: `ok`
- project trust: `ok`
- real `$arbor` skill injection: observed in direct `codex exec` JSON events

The remaining blocker is Codex headless sandbox behavior around project `.codex` writes:

- In a direct installed-plugin run, `$arbor` loaded and the model followed the Arbor initialization flow.
- The runtime read `skills/arbor/SKILL.md` from the installed plugin cache.
- The runtime attempted Arbor initialization.
- Creating or writing project `.codex` artifacts was blocked in the headless `codex exec` environment.
- The side-effect gate therefore remains blocked: `.codex/memory.md` and `.codex/hooks.json` were not created by the real runtime run.

This is a true runtime blocker, not a semantic trigger result.

## Validation

- `python3 -m unittest tests.test_arbor_skill.PluginRuntimeProbeTests tests.test_arbor_skill.HookTriggerPluginAdapterTests`: 22 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-stage-c-pycache python3 -m py_compile scripts/probe_plugin_runtime.py scripts/plugin_trigger_adapters.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check scripts/probe_plugin_runtime.py scripts/plugin_trigger_adapters.py tests/test_arbor_skill.py --no-cache`: passed.
- `python3 scripts/probe_plugin_runtime.py --attempt-exec --auth-source-home ~ --timeout 90`: authenticated run reached marketplace/cache/auth/enable/trust gates, then blocked at exec side-effect validation.
- Direct `codex exec` with isolated installed `arbor@arbor-local`: `$arbor` injected and read from plugin cache; project `.codex` writes remained blocked.

## Status

Implemented and self-tested. Needs review focused on whether the remaining `.codex` write blocker should be treated as a Codex runtime limitation, a probe setup limitation, or a plugin packaging/API limitation.

## Round 1 Review - 2026-05-03

### Findings

| ID | Priority | File | Status | Finding |
| --- | --- | --- | --- | --- |
| F21-R1-001 | P1 | `scripts/probe_plugin_runtime.py:298-306` | Open | `run_exec_probe` can pass with pre-existing project files plus a marker-only runtime response. The gate checks only post-run file existence, hook ids, and `ARBOR_RUNTIME_PROBE_OK`, so a project that already has `AGENTS.md`, `.codex/memory.md`, and `.codex/hooks.json` can be reported as "plugin skill initialized project files" even when the mocked runtime performed no `$arbor` side effects and provided no installed-plugin injection evidence. |

### Test Matrix

| Test Area | Test Cases Run | Coverage | Passed | Pass Rate | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| Feature contract review | 1 feature contract | 1/1 runtime-probe boundary set | 1/1 inspected | 100% | Reviewed auth copy, plugin cache materialization, isolated project trust, side-effect gates, and blocker classification claims. |
| Focused developer regressions | 22 tests | 22/22 Feature 21 and adapter checks | 22/22 | 100% | `PluginRuntimeProbeTests` and `HookTriggerPluginAdapterTests` passed. |
| Static validation | 2 commands | 2/2 touched-code checks | 2/2 | 100% | `py_compile` passed for runtime probe, trigger adapter, and tests; `ruff check` passed for the same files. |
| No-exec isolated runtime probe | 1 command | 1/1 install/cache/enable/trust path | 1/1 | 100% | `scripts/probe_plugin_runtime.py --timeout 10 --temp-parent /private/tmp` passed marketplace add, plugin cache materialization, plugin enable, and isolated project trust with exec intentionally skipped. |
| Runtime trigger smoke | 1 scenario | 1/1 plugin-runtime-codex-exec blocker path | 1/1 | 100% | `H1-P001` passed as an accepted `network_unavailable` blocker with no semantic hook scoring. |
| Full regression suite | 144 tests | 144/144 unit/scenario tests | 144/144 | 100% | `python3 -m unittest tests/test_arbor_skill.py` passed with pycache redirected outside the repo. |
| Adversarial side-effect gate | 1 probe | 1/1 false-positive class | 0/1 accepted | 0% | Pre-created required files and hooks, mocked `codex exec` to emit only `ARBOR_RUNTIME_PROBE_OK`, and `run_exec_probe` incorrectly returned `status=passed`. |

### Scenario Testing

| Scenario | Target Risk | Method | Result |
| --- | --- | --- | --- |
| Auth/plugin setup replay | Feature 21 setup breaks isolated marketplace/cache/trust flow | Ran the no-exec probe with `/private/tmp` as temp parent | Passed: marketplace add, plugin cache materialization, plugin enable, and project trust were `ok`; exec was skipped by design. |
| Focused runtime-probe regression suite | Developer tests do not cover the implemented Feature 21 behavior | Ran `PluginRuntimeProbeTests` and `HookTriggerPluginAdapterTests` | Passed: 22/22 tests. |
| Marker without side effects | Probe accepts a marker even when expected files are absent | Existing regression `test_probe_exec_reports_missing_plugin_side_effects` plus focused suite replay | Passed: missing files still fail. |
| Pre-existing files plus marker | Probe treats pre-existing side effects as new `$arbor` runtime work | Pre-created `AGENTS.md`, `.codex/memory.md`, `.codex/hooks.json` with all Arbor hook ids, then mocked runtime to emit only `ARBOR_RUNTIME_PROBE_OK` | Failed: `run_exec_probe` returned `passed`, proving the readiness gate can be satisfied without observed plugin-created side effects. |
| Runtime adapter blocker path | Feature 21 cache materialization change breaks plugin-runtime-codex-exec harness behavior | Ran `H1-P001` through `plugin-runtime-codex-exec` | Passed: the unavailable real runtime remained an accepted `network_unavailable` blocker. |
| Full regression replay | Feature 21 changes break unrelated Arbor behavior | Ran full `tests/test_arbor_skill.py` suite | Passed: 144/144 tests. |

### Optimization Suggestions

| Priority | Suggestion | Rationale |
| --- | --- | --- |
| P1 | Snapshot the probe project before `codex exec` and require the runtime run to create or modify the expected files, or force a freshly empty probe project and reject pre-existing expected files before execution. | The feature claims real side effects; post-run existence alone cannot prove the installed `$arbor` runtime performed them. |
| P1 | Add an explicit installed-plugin injection signal to the success gate, such as verifying JSON events that read `skills/arbor/SKILL.md` from the materialized cache or requiring a probe-only marker generated by the installed skill path. | This prevents a generic model response plus project fixtures from being counted as true `$arbor` plugin reachability. |
| P2 | Add a regression where all expected files and hook ids exist before execution and `run_command` only returns the marker. | This locks the false-positive class exposed by this review. |

### Reviewer Verdict

Feature 21 is not accepted yet. The isolated setup path and existing blocker classification replay cleanly, but the runtime success gate can report `passed` without proving that the installed `$arbor` plugin injected or produced the required side effects in the current run.

## Developer Response - Round 1 Fix

### Changes

- `scripts/probe_plugin_runtime.py`
  - Added a fresh-project precondition for `run_exec_probe`: if `AGENTS.md`, `.codex/memory.md`, or `.codex/hooks.json` already exists before `codex exec`, the probe fails before invoking the runtime.
  - Added an installed-plugin injection gate. Passing now requires stdout/stderr evidence that the runtime read `skills/arbor/SKILL.md` from the isolated materialized plugin cache under `.codex/plugins/cache/arbor-local/arbor`.
  - Added structured result fields for `preexisting_files` and `injection_seen` so review and automation can distinguish missing side effects, pre-existing fixtures, and missing installed-plugin evidence.
- `tests/test_arbor_skill.py`
  - Reworked the positive runtime-probe unit scenario so expected files and hook registrations are created during the mocked `codex exec` call, not before it.
  - Added a regression that pre-creates all expected files and hook ids, verifies `run_command` is not called, and requires a failed precondition result.
  - Added a regression where the mocked runtime creates all files and emits the marker but provides no installed-plugin injection evidence; the probe now fails that case.
  - Adjusted the empty-hook regression so file creation also happens inside the runtime mock, preserving the fresh-project gate.

### Review Feedback Addressed

| Review item | Resolution |
| --- | --- |
| F21-R1-001 false pass with pre-existing files plus marker-only response | Fixed by rejecting pre-existing expected Arbor side-effect files before `codex exec`. |
| Require proof that the current run performed plugin side effects | Fixed by forcing expected files to be absent pre-run and checking post-run side effects. |
| Add installed-plugin injection signal | Fixed by requiring evidence of `skills/arbor/SKILL.md` under the isolated installed plugin cache. |
| Add adversarial regression for pre-existing files plus marker-only response | Added and verified. |

### Validation

- `python3 -m unittest tests.test_arbor_skill.PluginRuntimeProbeTests tests.test_arbor_skill.HookTriggerPluginAdapterTests`: 24 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-stage-c-f21-r1-pycache python3 -m py_compile scripts/probe_plugin_runtime.py scripts/plugin_trigger_adapters.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check scripts/probe_plugin_runtime.py scripts/plugin_trigger_adapters.py tests/test_arbor_skill.py --no-cache`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-stage-c-f21-r1-full-pycache python3 -m unittest tests/test_arbor_skill.py`: 146 tests passed.

### Status

Round 1 bug fix and optimization suggestions are implemented and self-tested. Feature 21 is ready for re-review.

## Round 2 Re-review - 2026-05-03

### Findings

| ID | Priority | File | Status | Finding |
| --- | --- | --- | --- | --- |
| F21-R2-001 | - | - | No new findings | `F21-R1-001` is accepted as fixed. The probe now rejects pre-existing Arbor side-effect files before invoking `codex exec`, requires current-run file creation, and requires installed-plugin injection evidence from the isolated plugin cache before reporting `passed`. |

### Test Matrix

| Test Area | Test Cases Run | Coverage | Passed | Pass Rate | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| Developer feedback review | 1 fix response | 1/1 P1 finding replayed | 1/1 accepted | 100% | Reviewed the fresh-project precondition, installed-plugin injection gate, and new structured result fields. |
| Focused developer regressions | 24 tests | 24/24 Feature 21 and adapter checks | 24/24 | 100% | `PluginRuntimeProbeTests` and `HookTriggerPluginAdapterTests` passed, including the new pre-existing-file and missing-injection regressions. |
| Static validation | 2 commands | 2/2 touched-code checks | 2/2 | 100% | `py_compile` passed for runtime probe, trigger adapter, and tests; `ruff check` passed for the same files. |
| No-exec isolated runtime probe | 1 command | 1/1 install/cache/enable/trust path | 1/1 | 100% | Marketplace add, plugin cache materialization, plugin enable, and isolated project trust were `ok`; exec remained skipped by design. |
| Runtime trigger smoke | 1 scenario | 1/1 plugin-runtime-codex-exec blocker path | 1/1 | 100% | `H1-P001` remained an accepted `network_unavailable` blocker with no semantic hook scoring. |
| Full regression suite | 146 tests | 146/146 unit/scenario tests | 146/146 | 100% | `python3 -m unittest tests/test_arbor_skill.py` passed with pycache redirected outside the repo. |
| Adversarial side-effect replay | 3 probes | 3/3 false-positive classes | 3/3 | 100% | Pre-existing files were rejected before runtime, current-run side effects without injection evidence failed, and current-run side effects with installed-cache evidence passed. |

### Scenario Testing

| Scenario | Target Risk | Method | Result |
| --- | --- | --- | --- |
| Pre-existing files plus marker replay | Previous P1 false positive remains exploitable | Pre-created `AGENTS.md`, `.codex/memory.md`, `.codex/hooks.json` with all Arbor hook ids, patched `run_command`, and called `run_exec_probe` | Passed: result failed with `probe project must not contain pre-existing Arbor side-effect files`, and `run_command` was not called. |
| Current-run side effects without injection | A generic runtime creates files and emits the marker but no installed `$arbor` evidence | Mocked `run_command` to create all expected files and hooks, then return only `ARBOR_RUNTIME_PROBE_OK` | Passed: result failed with `expected installed Arbor skill injection was not observed`. |
| Current-run side effects with installed-cache evidence | The stricter gate rejects the intended success path | Mocked `run_command` to create all expected files and hooks, then return marker output containing the isolated cache path and `skills/arbor/SKILL.md` | Passed: result returned `passed` with `injection_seen=true`. |
| Focused runtime-probe regression suite | Developer tests miss the repaired behavior | Ran `PluginRuntimeProbeTests` and `HookTriggerPluginAdapterTests` | Passed: 24/24 tests. |
| Runtime adapter blocker path | The runtime-probe fix regresses plugin-runtime-codex-exec blocker classification | Ran `H1-P001` through `plugin-runtime-codex-exec` | Passed: unavailable real runtime remained an accepted `network_unavailable` blocker. |
| Full regression replay | Feature 21 fix breaks unrelated Arbor behavior | Ran full `tests/test_arbor_skill.py` suite | Passed: 146/146 tests. |

### Optimization Suggestions

| Priority | Suggestion | Rationale |
| --- | --- | --- |
| P3 | Keep the installed-cache evidence check narrow and documented as a readiness signal, not a semantic-quality metric. | The gate now proves more than file existence, but semantic trigger quality is still gated on authenticated runtime availability and broader corpus replay. |
| P3 | If Codex JSON event shapes become stable, consider parsing event types instead of substring-matching stdout/stderr. | This would make the injection gate less dependent on textual runtime output while preserving the current reviewed behavior. |

### Reviewer Verdict

Feature 21 is accepted for the reviewed offline scope. The previous P1 false positive is fixed, setup/blocker replay remains clean, and the probe now requires fresh-project side effects plus installed-cache injection evidence before reporting runtime success. Online authenticated behavior still depends on the real Codex runtime environment and remains outside this offline replay.
