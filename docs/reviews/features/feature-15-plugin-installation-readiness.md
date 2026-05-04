# Feature 15 Review: Plugin Installation Readiness

## Purpose

Make Arbor testable as a real repo-local Codex plugin package before replacing the sidecar baseline with a true plugin runtime trigger path.

## Scope

In scope:

- Add a repo-local marketplace entry for `plugins/arbor`.
- Add an installation-readiness validation script.
- Validate the plugin manifest, marketplace entry, packaged skill payload, packaged hook entrypoints, and packaged skill smoke behavior.
- Add an optional isolated Codex CLI marketplace installation probe using a temporary `HOME`.

Out of scope:

- Installing Arbor into the user's real `~/.codex/config.toml`.
- Implementing semantic plugin trigger selection.
- Reporting semantic trigger metrics.
- Changing hook script behavior.

## Design

Feature 15 adds `.agents/plugins/marketplace.json` so the repo can act as a local Codex marketplace root:

```text
repo root
-> .agents/plugins/marketplace.json
-> ./plugins/arbor
-> .codex-plugin/plugin.json
-> skills/arbor + hooks.json
```

The validation script checks the package without relying on sidecar expectations:

- marketplace entry resolves to `./plugins/arbor`;
- plugin manifest points to `./skills/` and `./hooks.json`;
- packaged `SKILL.md` exists;
- packaged hook ids match the Arbor hook contract;
- each packaged hook entrypoint resolves to a packaged skill script;
- packaged initialization script works from the plugin payload;
- optional Codex CLI probe can add this repo as a local marketplace using an isolated temp home.

## Test Plan

- `python3 scripts/validate_plugin_install.py`
- `python3 scripts/validate_plugin_install.py --codex-probe`
- Existing unit and harness tests.
- Plugin skill validation for both standalone and packaged skill copies.

## Acceptance Gates

- Repo-local marketplace has exactly one Arbor entry.
- The Arbor plugin manifest and marketplace entry agree on plugin name and path.
- Packaged hook entrypoints resolve inside the packaged skill.
- Packaged skill smoke initializes `AGENTS.md` and `.codex/memory.md`.
- Isolated Codex CLI marketplace add succeeds without modifying the user's real Codex config.

## Developer Response

Feature 15 is implemented.

Implemented:

- Added `.agents/plugins/marketplace.json` with marketplace name `arbor-local` and one local Arbor plugin entry.
- Added `scripts/validate_plugin_install.py`.
- The validator checks marketplace shape, manifest shape, packaged skill presence, packaged hook ids, packaged hook script resolution, packaged initialization smoke, and packaged Hook 1/2/3 entrypoint smokes.
- The validator supports `--codex-probe`, which runs `codex plugin marketplace add <repo-root>` against a temporary isolated `HOME`.
- Added `PluginInstallationReadinessTests` to cover the validator in the unit suite.
- Updated `AGENTS.md` project map.

Validation:

- `python3 scripts/validate_plugin_install.py`: passed.
- `python3 scripts/validate_plugin_install.py --codex-probe`: passed; Codex CLI reported `Added marketplace arbor-local from /Users/shawn/Desktop/arbor`.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f15-pycache python3 -m py_compile scripts/validate_plugin_install.py`: passed.
- `python3 -m unittest tests.test_arbor_skill.PluginInstallationReadinessTests`: 2 tests passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 112 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f15-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py tests/test_arbor_skill.py`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f15-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios passed, 103/103 selected hook executions passed, outside-root leaks 0, unintended writes 0, semantic metrics not reported.

Feature 15 does not install Arbor into the user's real Codex config and does not implement semantic trigger selection. The next feature should use the installable plugin package as the target for a real plugin-runtime trigger adapter.

## Review Round 1 - 2026-05-03

### Findings

| ID | Priority | Location | Status | Finding |
| --- | --- | --- | --- | --- |
| F15-R1-1 | P2 | `scripts/validate_plugin_install.py:113-114` | Added | `validate_plugin_payload` only checks whether `skill_root / script` exists. A hook entrypoint such as `../../hooks.json` resolves outside the packaged skill but still passes because `plugins/arbor/hooks.json` exists, so the validator can approve a hook entrypoint that violates the acceptance gate requiring packaged hook entrypoints to resolve inside the packaged skill. |

### Test Matrix

| Category | Test cases / checks | Coverage focus | Pass rate | Result |
| --- | ---: | --- | ---: | --- |
| Developer validation replay | 8 command groups | Validator smoke, isolated Codex marketplace add, py_compile, feature unit tests, full unit suite, skill quick validation, sidecar corpus | 8/8 (100%) | Passed |
| Install-readiness unit tests | 2 unittest cases | `PluginInstallationReadinessTests` positive validator and packaged hook smoke paths | 2/2 (100%) | Passed |
| Full regression suite | 112 unittest cases | All Arbor skill, hook, trigger adapter, fixture, harness, and install-readiness tests | 112/112 (100%) | Passed |
| Coverage replay | 112 unittest cases | Total Python coverage 87%; `scripts/validate_plugin_install.py` measured at 61% under the checked-in unittest suite | 112/112 (100%) | Passed with residual validator negative-path gap |
| Hook execution corpus compatibility | 150 scenarios, 103 selected hook executions | Sidecar-backed Stage B harness compatibility after Feature 15 packaging | 150/150 scenarios, 103/103 hook executions (100%) | Passed |
| Payload sync and isolation probes | 13 checks | Real `~/.codex/config.toml` unchanged, 11 packaged skill files byte-identical to standalone skill, packaged hooks equal canonical `ARBOR_HOOKS` | 13/13 (100%) | Passed |
| Adversarial marketplace/manifest/payload mutations | 6 mutation cases | Duplicate Arbor entry, marketplace path drift, manifest skill path drift, missing packaged hook script, hook id drift, hook script path escape | 5/6 (83%) | Failed on hook script path escape |

### Scenario Testing

| Scenario | Setup | Expected | Observed | Result |
| --- | --- | --- | --- | --- |
| Repo-local marketplace happy path | Ran `python3 scripts/validate_plugin_install.py` from repo root | Marketplace, manifest, payload, packaged init, and Hook 1/2/3 smoke all validate | Validator returned the expected sections and skipped Codex probe | Passed |
| Isolated Codex CLI marketplace add | Ran `python3 scripts/validate_plugin_install.py --codex-probe` and independently hashed the real Codex config before/after | Marketplace add uses temporary `HOME` and does not modify the real user config | Probe created temp `home/.codex/config.toml`; real config hash was unchanged | Passed |
| Packaged skill parity | Compared `skills/arbor` with `plugins/arbor/skills/arbor` excluding cache files | Packaged skill should match accepted standalone skill payload | 11 files matched byte-for-byte | Passed |
| Packaged hook contract parity | Compared `plugins/arbor/hooks.json` hooks with canonical `register_project_hooks.ARBOR_HOOKS` | Packaged hooks should match canonical project hook contract | Hook lists matched exactly | Passed |
| Drift rejection - marketplace and manifest | Mutated temp copies with bad marketplace path, duplicate Arbor entry, and bad manifest skill path | Validator should reject each mutation with a controlled error | All three mutations were rejected | Passed |
| Drift rejection - payload shape | Mutated temp copies with missing packaged hook script and renamed hook id | Validator should reject missing or mismatched hook payloads | Both mutations were rejected | Passed |
| Hook script path escape | Mutated temp copy so one hook used `entrypoint.script="../../hooks.json"` | Validator should reject a script resolving outside `plugins/arbor/skills/arbor` | Validator accepted the escaped script path | Failed |
| Existing hook corpus compatibility | Ran all structured trigger scenarios through sidecar-baseline harness | Feature 15 packaging should not regress hook execution plumbing | 150/150 scenarios passed; 103/103 selected hook executions passed; outside-root leaks 0; unintended writes 0 | Passed |

### Optimization Suggestions

| Recommendation | Rationale |
| --- | --- |
| Resolve each hook script candidate and require it to stay under `skill_root.resolve()` before accepting it. | This directly enforces the Feature 15 acceptance gate that packaged hook entrypoints resolve inside the packaged skill. |
| Reject non-Python or non-script entrypoint targets, for example by requiring a `.py` suffix after the containment check. | This would prevent paths such as `../../hooks.json` from satisfying the existence check even if containment enforcement regresses. |
| Add unit tests for validator negative cases, especially path traversal, duplicate marketplace entries, manifest path drift, missing packaged scripts, and hook id mismatch. | Current checked-in unittest coverage leaves many validator error branches unexercised; the path traversal gap was only found through external adversarial probes. |

### Review Verdict

Needs changes. The current plugin package and normal installation probe are healthy, but the validator does not yet prove that hook entrypoints are contained inside the packaged skill payload.

## Developer Response to Review Round 1

Status: fixed and self-tested.

Changes made:

- Updated `scripts/validate_plugin_install.py` so each packaged hook script path is resolved before validation.
- Rejected hook scripts that resolve outside `plugins/arbor/skills/arbor`.
- Rejected hook scripts that do not have a `.py` suffix.
- Added negative unittest coverage for:
  - duplicate Arbor marketplace entries;
  - manifest `skills` path drift;
  - missing packaged hook script;
  - hook script path traversal such as `../../hooks.json`;
  - non-Python hook script targets such as `SKILL.md`.

Validation:

- `python3 -m unittest tests.test_arbor_skill.PluginInstallationReadinessTests`: 3 tests passed.
- `python3 scripts/validate_plugin_install.py`: passed.
- `python3 scripts/validate_plugin_install.py --codex-probe`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f15-fix-pycache python3 -m py_compile scripts/validate_plugin_install.py tests/test_arbor_skill.py`: passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 113 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f15-fix-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py tests/test_arbor_skill.py`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f15-fix-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios passed, 103/103 selected hook executions passed, outside-root leaks 0, unintended writes 0, semantic metrics not reported.

Finding closure:

- `F15-R1-1`: fixed. Hook entrypoint scripts now must resolve inside the packaged Arbor skill root before they can pass validation.

## Review Round 2 - 2026-05-03

### Findings

| ID | Priority | Location | Status | Finding |
| --- | --- | --- | --- | --- |
| F15-R2-1 | P2 | `scripts/validate_plugin_install.py:96-102` | Added | `validate_plugin_payload` derives hook contract validity from a set of dict hook ids and skips non-dict hook entries. A temp-copy mutation that appends a duplicate valid hook, or appends a non-object hook entry, still passes because the id set remains equal to `REQUIRED_HOOK_IDS`. The install-readiness validator should reject duplicate hook ids and non-object hook rows so `plugins/arbor/hooks.json` is proven to contain exactly the Arbor hook contract, not just at least one copy of each required id. |

### Test Matrix

| Category | Test cases / checks | Coverage focus | Pass rate | Result |
| --- | ---: | --- | ---: | --- |
| Developer fix replay | 8 command groups | Feature 15 unit tests, validator smoke, isolated Codex marketplace add, focused and full py_compile, full unittest suite, skill quick validation, sidecar corpus | 8/8 (100%) | Passed |
| Finding replay | 1 mutation case | Previous `../../hooks.json` path traversal regression | 1/1 (100%) | Passed |
| Install-readiness unit tests | 3 unittest cases | Positive install surface, packaged hook smoke, negative drift/path traversal/non-Python cases | 3/3 (100%) | Passed |
| Full regression suite | 113 unittest cases | All Arbor skill, hook, trigger adapter, fixture, harness, and install-readiness tests | 113/113 (100%) | Passed |
| Coverage replay | 113 unittest cases | Total Python coverage 87%; `scripts/validate_plugin_install.py` measured at 64% | 113/113 (100%) | Passed |
| Hook execution corpus compatibility | 150 scenarios, 103 selected hook executions | Sidecar-backed Stage B harness compatibility after Feature 15 fix | 150/150 scenarios, 103/103 hook executions (100%) | Passed |
| Isolation and path containment probes | 5 checks | Real `~/.codex/config.toml` unchanged; relative, absolute, symlink, and non-Python hook script targets rejected | 5/5 (100%) | Passed |
| Hook list exactness probes | 2 mutation cases | Duplicate hook rows and non-object hook rows in `plugins/arbor/hooks.json` | 0/2 (0%) | Failed; both malformed hook lists were accepted |

### Scenario Testing

| Scenario | Setup | Expected | Observed | Result |
| --- | --- | --- | --- | --- |
| Review Round 1 path traversal replay | Mutated temp copy so one hook used `entrypoint.script="../../hooks.json"` | Validator rejects escaped hook script path | Rejected with `hook script escapes packaged skill root` | Passed |
| Absolute script path escape | Mutated temp copy so one hook used an absolute `/private/tmp/.../outside.py` path | Validator rejects script path outside packaged skill root | Rejected with `hook script escapes packaged skill root` | Passed |
| Symlink script escape | Added `scripts/outside_link.py` symlink inside packaged skill pointing to an outside `.py`, then referenced that script | Validator follows `resolve()` and rejects the outside target | Rejected with `hook script escapes packaged skill root` | Passed |
| Non-Python script target | Mutated temp copy so one hook used `entrypoint.script="SKILL.md"` | Validator rejects non-`.py` hook script targets | Rejected with `hook script must be a Python file` | Passed |
| Duplicate hook row | Appended a duplicate copy of an existing valid hook object to `plugins/arbor/hooks.json` | Validator rejects duplicate hook ids or hook count mismatch | Validator accepted the malformed hooks list | Failed |
| Non-object hook row | Appended `"not-a-hook-object"` to the hooks list | Validator rejects non-object hook rows | Validator accepted the malformed hooks list | Failed |
| Isolated Codex CLI marketplace add | Ran `python3 scripts/validate_plugin_install.py --codex-probe` and independently hashed real Codex config before/after | Temporary `HOME` is used; real config remains unchanged | Temp config was created; real config hash unchanged | Passed |
| Existing hook corpus compatibility | Ran all structured trigger scenarios through sidecar-baseline harness | Feature 15 fix should not regress hook execution plumbing | 150/150 scenarios passed; 103/103 selected hook executions passed; outside-root leaks 0; unintended writes 0 | Passed |

### Optimization Suggestions

| Recommendation | Rationale |
| --- | --- |
| Require every item in `hooks` to be a dict before computing ids or validating entrypoints. | This prevents malformed plugin hook config from being silently ignored. |
| Validate the ordered hook id list, or compare `len(hooks)` plus `set(hook_ids)` plus duplicate detection against `REQUIRED_HOOK_IDS`. | This proves the packaged plugin contains exactly the Arbor hook contract instead of a superset with duplicates. |
| Add negative unit tests for duplicate hook entries and non-object hook entries. | The checked-in negative tests now cover path traversal, but still miss hook-list exactness. |

### Review Verdict

Needs changes. The Round 1 path traversal finding is fixed, but the validator still accepts malformed `hooks.json` lists that are not exactly the Arbor hook contract.

## Developer Response to Review Round 2

Status: fixed and self-tested.

Changes made:

- Updated `scripts/validate_plugin_install.py` so `hooks.json` must contain exactly three hook entries.
- Rejected non-object hook rows before hook id extraction.
- Required every hook row to include a string `id`.
- Added duplicate hook id detection before comparing against `REQUIRED_HOOK_IDS`.
- Kept the exact hook-id set check after count/type/duplicate validation.
- Added negative unittest coverage for:
  - duplicate hook rows that increase hook count;
  - non-object hook rows;
  - duplicate hook ids without increasing hook count.

Validation:

- `python3 -m unittest tests.test_arbor_skill.PluginInstallationReadinessTests`: 3 tests passed.
- `python3 scripts/validate_plugin_install.py`: passed.
- `python3 scripts/validate_plugin_install.py --codex-probe`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f15-r2-pycache python3 -m py_compile scripts/validate_plugin_install.py tests/test_arbor_skill.py`: passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 113 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f15-r2-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py tests/test_arbor_skill.py`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f15-r2-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios passed, 103/103 selected hook executions passed, outside-root leaks 0, unintended writes 0, semantic metrics not reported.

Finding closure:

- `F15-R2-1`: fixed. The install-readiness validator now rejects duplicate hook entries, duplicate hook ids, and non-object hook rows, so `plugins/arbor/hooks.json` must be exactly the Arbor hook contract.

## Review Round 3 - 2026-05-03

### Findings

| ID | Priority | Location | Status | Finding |
| --- | --- | --- | --- | --- |
| F15-R3 | N/A | N/A | No new findings | Review Round 2 finding was fixed and no new blocking issues were found in the plugin installation-readiness surface. |

### Test Matrix

| Category | Test cases / checks | Coverage focus | Pass rate | Result |
| --- | ---: | --- | ---: | --- |
| Developer fix replay | 8 command groups | Feature 15 unit tests, validator smoke, isolated Codex marketplace add, focused and full py_compile, full unittest suite, skill quick validation, sidecar corpus | 8/8 (100%) | Passed |
| Finding replay | 5 mutation cases | Duplicate hook row, non-object hook row, duplicate hook id with same count, missing hook id, wrong hook id | 5/5 (100%) | Passed |
| Install-readiness unit tests | 3 unittest cases | Positive install surface, packaged hook smoke, negative drift/path traversal/hook-list exactness cases | 3/3 (100%) | Passed |
| Full regression suite | 113 unittest cases | All Arbor skill, hook, trigger adapter, fixture, harness, and install-readiness tests | 113/113 (100%) | Passed |
| Coverage replay | 113 unittest cases | Total Python coverage 87%; `scripts/validate_plugin_install.py` measured at 66% | 113/113 (100%) | Passed |
| Hook execution corpus compatibility | 150 scenarios, 103 selected hook executions | Sidecar-backed Stage B harness compatibility after Feature 15 fix | 150/150 scenarios, 103/103 hook executions (100%) | Passed |
| Isolation probe | 1 check | `--codex-probe` uses temporary `HOME`; real `~/.codex/config.toml` remains unchanged | 1/1 (100%) | Passed |

### Scenario Testing

| Scenario | Setup | Expected | Observed | Result |
| --- | --- | --- | --- | --- |
| Duplicate hook row replay | Appended a duplicate copy of an existing hook object to `plugins/arbor/hooks.json` in a temp copy | Validator rejects hook-count mismatch | Rejected with `packaged hooks must contain exactly 3 entries` | Passed |
| Non-object hook row replay | Replaced a hook row with `"not-a-hook-object"` in a temp copy | Validator rejects non-object hook row | Rejected with `hook entry must be an object` | Passed |
| Duplicate hook id without extra count | Changed one hook id to duplicate another while keeping exactly three rows | Validator rejects duplicate hook ids | Rejected with `duplicate packaged hook ids` | Passed |
| Missing hook id | Removed one hook id while keeping exactly three rows | Validator rejects missing/string-id violation | Rejected with `hook entry must include string id` | Passed |
| Wrong hook id | Replaced one hook id with `arbor.unexpected` while keeping exactly three rows | Validator rejects required hook mismatch | Rejected with `packaged hooks mismatch` | Passed |
| Isolated Codex CLI marketplace add | Ran `python3 scripts/validate_plugin_install.py --codex-probe` and independently hashed real Codex config before/after | Temporary `HOME` is used; real config remains unchanged | Temp config was created; real config hash unchanged | Passed |
| Existing hook corpus compatibility | Ran all structured trigger scenarios through sidecar-baseline harness | Feature 15 fix should not regress hook execution plumbing | 150/150 scenarios passed; 103/103 selected hook executions passed; outside-root leaks 0; unintended writes 0 | Passed |

### Optimization Suggestions

| Recommendation | Rationale |
| --- | --- |
| Keep the current count, object type, string id, duplicate id, and required-id set checks together in `validate_plugin_payload`. | The checks now close both prior bypass classes: escaped scripts and malformed hook lists. |
| If plugin hook ordering becomes part of the runtime contract later, add an ordered-id assertion at that time. | Current behavior proves exact membership and valid entry shape; order is not required by the current Feature 15 acceptance gates. |
| Preserve the temp-copy mutation tests as regression coverage when the plugin runtime adapter is introduced. | The real runtime adapter will depend on this packaged hook contract being trustworthy. |

### Review Verdict

Accepted after re-review. Feature 15 now validates the repo-local marketplace, packaged skill payload, packaged hook entrypoints, isolated Codex marketplace add, and exact packaged hook contract sufficiently for the next plugin-runtime trigger adapter increment.
