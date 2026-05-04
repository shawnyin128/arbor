# Feature 22 Review: Authenticated Runtime Corpus Controls

## Development Target

Let the existing `plugin-runtime-codex-exec` harness path run with explicit authenticated Codex runtime options, so real installed-plugin trigger evaluation can be attempted from the corpus CLI instead of only from the standalone runtime probe.

This feature does not claim semantic quality by itself. It only makes authenticated real-runtime corpus execution reachable and keeps existing runtime blocker gates intact.

## Scope

In scope:

- Pass explicit auth source, Codex binary, and runtime timeout into `plugin-runtime-codex-exec`.
- Copy requested auth into each isolated runtime `HOME`.
- Add corpus CLI flags for authenticated runtime runs.
- Keep auth failure as a runtime blocker rather than a semantic `NONE` decision.
- Preserve sidecar-baseline and plugin-runtime-stub behavior.

Out of scope:

- Sharing one runtime home across all 150 scenarios.
- Retrying runtime blockers.
- Changing semantic metric formulas or thresholds.
- Shipping harness/probe files in the Arbor plugin payload.

## Implementation Summary

- `scripts/plugin_trigger_adapters.py`
  - Added `RuntimeAdapterOptions`.
  - Added `auth_source_home` support to `run_codex_exec_trigger`.
  - `plugin_runtime_codex_exec_trigger` now accepts runtime options and forwards Codex binary, timeout, and auth source into the isolated runtime.
  - Missing requested auth returns an `auth_required` runtime blocker before `codex exec`.
- `scripts/evaluate_hook_triggers.py`
  - Added runtime option forwarding through `evaluate_scenario`, `evaluate_corpus`, and `evaluate_repeated_corpus`.
  - Added CLI flags:
    - `--auth-source-home`
    - `--runtime-timeout`
    - `--codex-bin`
- `tests/test_arbor_skill.py`
  - Added regression coverage for auth copy into the isolated adapter runtime.
  - Added missing-auth blocker coverage.
  - Added harness option forwarding coverage.
  - Added parser coverage for the new CLI flags.

## Usage

Single authenticated runtime scenario:

```bash
python3 scripts/evaluate_hook_triggers.py \
  --scenario-id H1-P001 \
  --work-root /private/tmp/arbor-runtime-scenario \
  --trigger-adapter plugin-runtime-codex-exec \
  --auth-source-home ~ \
  --runtime-timeout 90
```

Full authenticated runtime corpus:

```bash
python3 scripts/evaluate_hook_triggers.py \
  --all \
  --work-root /private/tmp/arbor-runtime-corpus \
  --trigger-adapter plugin-runtime-codex-exec \
  --auth-source-home ~ \
  --runtime-timeout 90
```

## Validation

- `python3 -m unittest tests.test_arbor_skill.HookTriggerPluginAdapterTests tests.test_arbor_skill.HookTriggerExecutionHarnessTests tests.test_arbor_skill.PluginRuntimeProbeTests`: 53 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f22-pycache python3 -m py_compile scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/probe_plugin_runtime.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/probe_plugin_runtime.py tests/test_arbor_skill.py --no-cache`: passed.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-f22-cli-smoke --trigger-adapter sidecar-baseline --auth-source-home ~ --runtime-timeout 90 --codex-bin /bin/codex`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f22-full-pycache python3 -m unittest tests/test_arbor_skill.py`: 150 tests passed.

## Status

Implemented and self-tested. Ready for review focused on whether this is the right minimal authenticated corpus control surface before running expensive real-runtime corpus experiments.

## Round 1 Review - 2026-05-03

### Findings

| ID | Priority | File | Status | Finding |
| --- | --- | --- | --- | --- |
| F22-R1-001 | - | - | No new findings | The authenticated runtime corpus control surface is accepted for the reviewed offline scope. Runtime options are wired into `plugin-runtime-codex-exec`, missing requested auth remains a runtime blocker, and sidecar behavior is unchanged when the new flags are supplied. |

### Test Matrix

| Test Area | Test Cases Run | Coverage | Passed | Pass Rate | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| Feature contract review | 1 feature contract | 1/1 authenticated corpus-control boundary set | 1/1 inspected | 100% | Reviewed explicit auth source, Codex binary, runtime timeout, blocker classification, and sidecar/stub preservation claims. |
| Focused developer regressions | 53 tests | 53/53 adapter, harness, and runtime-probe checks | 53/53 | 100% | `HookTriggerPluginAdapterTests`, `HookTriggerExecutionHarnessTests`, and `PluginRuntimeProbeTests` passed. |
| Static validation | 2 commands | 2/2 touched-code checks | 2/2 | 100% | `py_compile` passed for adapter, harness, runtime probe, and tests; `ruff check` passed for the same files. |
| CLI parser and sidecar smoke | 1 scenario | 1/1 runtime-flag sidecar scenario | 1/1 | 100% | `H1-P001` with `sidecar-baseline`, `--auth-source-home`, `--runtime-timeout`, and `--codex-bin /bin/codex` passed, proving the new flags do not affect sidecar execution. |
| Missing-auth runtime blocker | 2 probes | 2/2 missing-auth blocker paths | 2/2 | 100% | Direct CLI returned `auth_required`; mocked adapter probe confirmed `codex exec` is not invoked after requested auth copy fails. |
| Runtime option forwarding | 1 corpus probe | 150/150 corpus scenario calls | 150/150 | 100% | Mocked `evaluate_corpus` path forwarded the same `RuntimeAdapterOptions` object into every `plugin-runtime-codex-exec` scenario. |
| Sidecar full corpus with runtime flags | 1 corpus | 150/150 scenarios, 103/103 hook executions | 150/150 | 100% | Full sidecar corpus passed with runtime flags present; semantic metrics stayed withheld because sidecar remains ineligible. |
| Full regression suite | 150 tests | 150/150 unit/scenario tests | 150/150 | 100% | `python3 -m unittest tests/test_arbor_skill.py` passed with pycache redirected outside the repo. |

### Scenario Testing

| Scenario | Target Risk | Method | Result |
| --- | --- | --- | --- |
| Sidecar scenario with runtime flags | New auth/runtime flags accidentally alter sidecar behavior | Ran `H1-P001` through `sidecar-baseline` with `--auth-source-home`, `--runtime-timeout 90`, and `--codex-bin /bin/codex` | Passed: selected `arbor.session_startup_context` and hook execution passed. |
| Missing requested auth through real CLI | Missing auth is treated as semantic `NONE` or attempts real trigger selection | Ran `H1-P001` through `plugin-runtime-codex-exec` with an auth source directory that lacks `.codex/auth.json` | Passed: returned an accepted ambiguous runtime blocker with `auth_required` and no hooks. |
| Missing requested auth before `codex exec` | Adapter reaches expensive runtime execution after auth copy failure | Mocked marketplace success and missing auth source, then asserted `run_command` was not called | Passed: returned `auth_required` before `codex exec`. |
| Corpus runtime option forwarding | `--auth-source-home`, `--runtime-timeout`, or `--codex-bin` only work for single-scenario runs | Mocked `evaluate_scenario` under `evaluate_corpus` with `plugin-runtime-codex-exec` | Passed: all 150 scenario calls received the same runtime options object. |
| Sidecar full corpus isolation | New runtime flags pollute sidecar full-corpus behavior | Ran `--all` with `sidecar-baseline` and runtime flags | Passed: 150/150 scenarios, 103/103 hook executions, no unintended writes or outside-root leaks. |
| Full regression replay | Feature 22 changes break unrelated Arbor behavior | Ran full `tests/test_arbor_skill.py` suite | Passed: 150/150 tests. |

### Optimization Suggestions

| Priority | Suggestion | Rationale |
| --- | --- | --- |
| P3 | Consider rejecting non-positive `--runtime-timeout` values before invoking `codex exec`. | The current argparse type accepts zero or negative integers; a positive-timeout check would make expensive real-runtime corpus runs fail earlier with a clearer user error. |
| P3 | Keep the authenticated corpus CLI examples clearly separated from sidecar smoke examples. | The sidecar smoke is useful for parser/backward-compatibility checks, but it does not prove real runtime availability or semantic quality. |

### Reviewer Verdict

Feature 22 is accepted for the reviewed offline scope. The minimal authenticated corpus control surface is wired through the plugin-runtime adapter, missing auth stays a runtime blocker, sidecar behavior remains stable under the new flags, and semantic quality remains correctly gated until a real authenticated runtime corpus run is available.
