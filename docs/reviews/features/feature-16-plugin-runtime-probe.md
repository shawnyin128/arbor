# Feature 16 Review: Real Plugin Runtime Probe

## Development Target

Add the first real installed-plugin runtime probe for Arbor. The probe should verify that the repo-local plugin package can be made visible to Codex in an isolated runtime, enabled as `arbor@arbor-local`, and optionally exercised through `codex exec` without mutating the user's real Codex config.

This feature is a runtime reachability step, not the final semantic trigger evaluator.

## Scope

In scope:

- Add `scripts/probe_plugin_runtime.py`.
- Use a temporary `HOME` for all Codex CLI config writes.
- Add the `arbor-local` marketplace through the real Codex CLI.
- Enable `arbor@arbor-local` in the isolated config.
- Skip model/runtime execution by default.
- When `--attempt-exec` is requested, run a real `codex exec` prompt that asks `$arbor` to initialize a temporary project and register hooks.
- Check for `AGENTS.md`, `.codex/memory.md`, and `.codex/hooks.json` after the exec probe.
- Classify runtime blockers separately from Arbor/plugin failures.

Out of scope:

- Full 150-scenario semantic trigger evaluation.
- Precision, recall, false-positive, or stability metrics.
- Mutating the real `~/.codex/config.toml`.
- Replacing the `plugin-runtime-stub` adapter in the scenario harness.
- Depending on network/model access in unit tests.

## Implementation Summary

- Added `scripts/probe_plugin_runtime.py`.
- The probe now:
  - validates the Codex binary exists;
  - runs `codex plugin marketplace add <repo-root>` with isolated `HOME`;
  - appends `[plugins."arbor@arbor-local"] enabled = true` to the isolated config;
  - skips `codex exec` unless `--attempt-exec` is set;
  - checks expected Arbor project files after an exec attempt;
  - classifies failures as `network_unavailable`, `auth_required`, `plugin_runtime_error`, or `runtime_failed`.
- Added `PluginRuntimeProbeTests` to cover config enablement, network failure classification, timeout classification, missing side-effect detection, passing side-effect detection, and default no-exec behavior.
- Updated `docs/arbor-skill-design.md`, `docs/reviews/arbor-skill-review.md`, and `AGENTS.md`.

## Developer Validation

- `python3 -m unittest tests.test_arbor_skill.PluginRuntimeProbeTests`: 6 tests passed.
- `python3 scripts/probe_plugin_runtime.py`: passed; isolated marketplace add and `arbor@arbor-local` enable succeeded; exec skipped by default.
- `python3 scripts/probe_plugin_runtime.py --attempt-exec --timeout 45`: completed with `exec_probe.status=blocked` and `reason=network_unavailable`; marketplace add and plugin enable still succeeded.
- `python3 -m unittest tests/test_arbor_skill.py`: 119 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f16-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py scripts/probe_plugin_runtime.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed after removing an unused import in `scripts/probe_plugin_runtime.py`.
- `python3 scripts/validate_plugin_install.py`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f16-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios, 103/103 hook executions, outside-root leaks 0, unintended writes 0.
- `env COVERAGE_FILE=/private/tmp/arbor-f16-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 119 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f16-coverage conda run -n arbor python -m coverage report`: total coverage 87%; `scripts/probe_plugin_runtime.py` coverage 67%.

## Runtime Probe Notes

Manual sandbox observation before implementation:

- `codex exec --ephemeral --json` can start a thread in an isolated HOME.
- The current sandbox cannot resolve `api.openai.com`, `github.com`, or plugin sync endpoints.
- The observed failure is an environment/network blocker, not evidence that Arbor hooks failed.

## Review Feedback

## Review Round 1 - 2026-05-03

### Findings

| ID | Priority | Location | Status | Finding |
| --- | --- | --- | --- | --- |
| F16-R1-1 | P2 | `scripts/probe_plugin_runtime.py:140-148` | Added | `run_exec_probe` marks the runtime probe as passed when the marker is present and `AGENTS.md`, `.codex/memory.md`, and `.codex/hooks.json` exist, but it never validates that `.codex/hooks.json` contains the Arbor hook registrations. A mocked successful exec with an empty `{"hooks":[]}` file returned `status="passed"`, so the probe can report that `$arbor` registered hooks even when no Arbor hooks were registered. |

### Test Matrix

| Category | Test cases / checks | Coverage focus | Pass rate | Result |
| --- | ---: | --- | ---: | --- |
| Developer validation replay | 10 command groups | Feature 16 unit tests, default probe, attempted real `codex exec`, py_compile, ruff, install validator, quick_validate for standalone and packaged skill, full unittest suite, sidecar corpus, coverage | 10/10 (100%) | Passed |
| Runtime probe unit tests | 6 unittest cases | isolated config enablement, network classification, timeout classification, missing side effects, passing side effects, default no-exec behavior | 6/6 (100%) | Passed |
| Full regression suite | 119 unittest cases | All Arbor skill, hook, trigger adapter, fixture, harness, install-readiness, and runtime-probe tests | 119/119 (100%) | Passed |
| Coverage replay | 119 unittest cases | Total Python coverage 87%; `scripts/probe_plugin_runtime.py` measured at 67% | 119/119 (100%) | Passed |
| Hook execution corpus compatibility | 150 scenarios, 103 selected hook executions | Sidecar-backed Stage B harness compatibility after Feature 16 runtime probe addition | 150/150 scenarios, 103/103 hook executions (100%) | Passed |
| Isolated runtime reachability | 3 checks | Real Codex marketplace add, manual isolated plugin enable, default exec skip | 3/3 (100%) | Passed |
| Runtime blocker classification | 1 real exec attempt | `codex exec` under current sandbox/network constraints | 1/1 (100%) | Passed as blocked with `reason=network_unavailable` |
| Adversarial exec side-effect probe | 1 mutation case | Empty `.codex/hooks.json` with marker and expected file paths | 0/1 (0%) | Failed; empty hook registration was accepted as passed |

### Scenario Testing

| Scenario | Setup | Expected | Observed | Result |
| --- | --- | --- | --- | --- |
| Default runtime probe | Ran `python3 scripts/probe_plugin_runtime.py` | Marketplace add and plugin enable succeed in isolated `HOME`; exec skipped | `marketplace.status=ok`, `plugin_enable.status=ok`, `exec_probe.status=skipped` | Passed |
| Isolated config shape | Ran marketplace add into a temp `HOME`, then called `enable_arbor_plugin` | Config contains `[marketplaces.arbor-local]` and `[plugins."arbor@arbor-local"] enabled = true` | Both tables were written only in temp config | Passed |
| Real config isolation | Hashed real `~/.codex/config.toml` before/after `run_plugin_runtime_probe(..., attempt_exec=False)` | Real config hash remains unchanged | Hash unchanged | Passed |
| Attempted real exec | Ran `python3 scripts/probe_plugin_runtime.py --attempt-exec --timeout 45` | Environment/network blocker is classified separately from Arbor failure | `exec_probe.status=blocked`, `reason=network_unavailable`; marketplace and plugin enable succeeded | Passed |
| Empty hook registration false positive | Mocked `codex exec` success with `ARBOR_RUNTIME_PROBE_OK`, created `AGENTS.md`, `.codex/memory.md`, and empty `.codex/hooks.json` | Probe should fail because Arbor hooks were not registered | Probe returned `status=passed` | Failed |
| Existing hook corpus compatibility | Ran all structured trigger scenarios through sidecar-baseline harness | Feature 16 should not regress existing hook execution plumbing | 150/150 scenarios passed; 103/103 selected hook executions passed; outside-root leaks 0; unintended writes 0 | Passed |

### Optimization Suggestions

| Recommendation | Rationale |
| --- | --- |
| Validate `.codex/hooks.json` after exec by parsing JSON and requiring the three Arbor hook ids. | This aligns the probe result with the prompt's requirement to initialize Arbor and register project hooks, not merely create placeholder files. |
| Treat malformed or missing hook ids as `status="failed"` with a reason such as `expected Arbor hook registrations were not observed`. | This keeps runtime/network blockers separate from Arbor/plugin side-effect failures. |
| Update `PluginRuntimeProbeTests.test_probe_exec_passes_when_marker_and_project_files_exist` so the passing fixture uses the real Arbor hook ids, and add a negative test for empty hooks. | The current passing unit test encodes the false-positive behavior by accepting `{"hooks":[]}`. |

### Review Verdict

Needs changes. The isolated install/enable and blocker classification paths work, but the exec pass condition does not yet prove that `$arbor` registered project hooks.

## Developer Response - Round 1 Fix

### Changes

- Fixed `F16-R1-1` in `scripts/probe_plugin_runtime.py`.
- Added `REQUIRED_HOOK_IDS` with the three Arbor hook ids:
  - `arbor.session_startup_context`
  - `arbor.in_session_memory_hygiene`
  - `arbor.goal_constraint_drift`
- Added `read_registered_arbor_hooks(project_root)` to parse `.codex/hooks.json` and collect only `owner=arbor` hook ids.
- Updated `run_exec_probe` so `status="passed"` requires:
  - `codex exec` return code 0;
  - `ARBOR_RUNTIME_PROBE_OK` marker;
  - `AGENTS.md`, `.codex/memory.md`, and `.codex/hooks.json`;
  - all three Arbor hook registrations.
- Empty, malformed, or incomplete hook registration now returns `status="failed"` with `reason="expected Arbor hook registrations were not observed"`.
- Preserved the separate missing-file failure reason: if expected project files are missing, the reason remains `expected plugin side effects were not observed`.
- Updated the positive unit test to write the real Arbor hook ids.
- Added a negative unit test proving an empty `{"hooks":[]}` file no longer passes.

### Validation

- `python3 -m unittest tests.test_arbor_skill.PluginRuntimeProbeTests`: 7 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f16-r1-pycache python3 -m py_compile scripts/probe_plugin_runtime.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed.
- `python3 scripts/probe_plugin_runtime.py`: passed; isolated marketplace add and `arbor@arbor-local` enable succeeded; exec skipped by default.
- `python3 -m unittest tests/test_arbor_skill.py`: 120 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f16-r1-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py scripts/probe_plugin_runtime.py tests/test_arbor_skill.py`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f16-r1-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios, 103/103 hook executions, outside-root leaks 0, unintended writes 0.
- `python3 scripts/validate_plugin_install.py`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f16-r1-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 120 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f16-r1-coverage conda run -n arbor python -m coverage report`: total coverage 87%; `scripts/probe_plugin_runtime.py` coverage 67%.

### Finding Closure

| Finding | Status | Evidence |
| --- | --- | --- |
| `F16-R1-1`: empty `.codex/hooks.json` accepted as a passed runtime probe | Fixed; pending re-review | `test_probe_exec_rejects_empty_hook_registration` now fails empty hooks with `expected Arbor hook registrations were not observed`; positive pass fixture now includes all three Arbor hook ids. |

## Review Round 2 - 2026-05-03

### Findings

| ID | Priority | Location | Status | Finding |
| --- | --- | --- | --- | --- |
| F16-R2 | N/A | N/A | No new findings | Review Round 1 finding was fixed and no new blocking issues were found in the runtime probe surface. |

### Test Matrix

| Category | Test cases / checks | Coverage focus | Pass rate | Result |
| --- | ---: | --- | ---: | --- |
| Developer fix replay | 10 command groups | Runtime probe unit tests, default probe, attempted real `codex exec`, focused and full py_compile, ruff, install validator, quick_validate for standalone and packaged skill, full unittest suite, sidecar corpus | 10/10 (100%) | Passed |
| Finding replay and incrementals | 6 mutation cases | Empty hooks, malformed hooks JSON, non-list hooks, wrong owner, one missing Arbor hook, all three Arbor hooks positive path | 6/6 (100%) | Passed |
| Runtime probe unit tests | 7 unittest cases | Config enablement, network classification, timeout classification, missing side effects, empty hooks rejection, passing hook registration, default no-exec behavior | 7/7 (100%) | Passed |
| Full regression suite | 120 unittest cases | All Arbor skill, hook, trigger adapter, fixture, harness, install-readiness, and runtime-probe tests | 120/120 (100%) | Passed |
| Coverage replay | 120 unittest cases | Total Python coverage 87%; `scripts/probe_plugin_runtime.py` measured at 67% | 120/120 (100%) | Passed |
| Hook execution corpus compatibility | 150 scenarios, 103 selected hook executions | Sidecar-backed Stage B harness compatibility after Feature 16 runtime-probe fix | 150/150 scenarios, 103/103 hook executions (100%) | Passed |
| Isolated runtime reachability | 2 checks | Default probe and independent real-config hash check | 2/2 (100%) | Passed |
| Runtime blocker classification | 1 real exec attempt | `codex exec` under current sandbox/network constraints | 1/1 (100%) | Passed as blocked with `reason=network_unavailable` |

### Scenario Testing

| Scenario | Setup | Expected | Observed | Result |
| --- | --- | --- | --- | --- |
| Empty hook registration replay | Mocked successful `codex exec` with marker and `{"hooks":[]}` | Probe fails because Arbor hooks were not registered | `status=failed`, reason `expected Arbor hook registrations were not observed`, all three hook ids missing | Passed |
| Malformed hooks JSON | Mocked successful exec with `.codex/hooks.json` containing `{` | Probe fails with hook registration reason and exposes parse error in `hook_error` | Failed as expected | Passed |
| Hooks field is not a list | Mocked successful exec with `{"hooks":{}}` | Probe fails and reports hook-list shape error | Failed as expected | Passed |
| Wrong hook owner | Mocked successful exec with all three hook ids but `owner=third-party` | Probe fails because only `owner=arbor` hooks count | Failed as expected | Passed |
| Incomplete Arbor hook set | Mocked successful exec with two of three Arbor hook ids | Probe fails and reports the missing hook id | Failed as expected | Passed |
| Complete Arbor hook set | Mocked successful exec with marker, expected files, and all three `owner=arbor` hook ids | Probe passes and reports all registered hook ids | Passed | Passed |
| Default runtime probe | Ran `python3 scripts/probe_plugin_runtime.py` | Marketplace add and plugin enable succeed in isolated `HOME`; exec skipped | `marketplace.status=ok`, `plugin_enable.status=ok`, `exec_probe.status=skipped` | Passed |
| Attempted real exec | Ran `python3 scripts/probe_plugin_runtime.py --attempt-exec --timeout 45` | Environment/network blocker is classified separately from Arbor failure | `exec_probe.status=blocked`, `reason=network_unavailable`; marketplace and plugin enable succeeded | Passed |
| Real config isolation | Hashed real `~/.codex/config.toml` before/after default runtime probe | Real config remains unchanged | Hash unchanged | Passed |
| Existing hook corpus compatibility | Ran all structured trigger scenarios through sidecar-baseline harness | Feature 16 fix should not regress existing hook execution plumbing | 150/150 scenarios passed; 103/103 selected hook executions passed; outside-root leaks 0; unintended writes 0 | Passed |

### Optimization Suggestions

| Recommendation | Rationale |
| --- | --- |
| Keep `registered_hook_ids`, `missing_hook_ids`, and `hook_error` in the probe output. | These fields make runtime reachability failures debuggable without conflating Arbor side-effect failures with network/auth blockers. |
| Preserve the negative hook-registration tests when adding the real plugin runtime trigger adapter. | The next adapter depends on this probe to distinguish installed-plugin reachability from semantic trigger quality. |
| Consider ordered hook-id validation only if a future runtime contract depends on hook order. | Current Feature 16 acceptance requires all three Arbor hook registrations, not a specific order. |

### Review Verdict

Accepted after re-review. Feature 16 now proves isolated marketplace add, isolated plugin enablement, default no-exec behavior, runtime blocker classification, real-config isolation, and post-exec Arbor hook registration checks without reporting semantic trigger metrics.
