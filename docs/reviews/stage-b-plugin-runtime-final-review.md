# Stage B Review: Plugin Runtime Trigger Evaluation

## Objective

Review the completed Stage B evaluation layer for Arbor's plugin/runtime trigger path. This stage exists to prove that Arbor can be tested as an installable plugin, that hook trigger decisions can be evaluated without leaking sidecar labels into the runtime, and that semantic metrics are reported only when the runtime evidence is valid.

## Scope

In scope:

- Feature 13: plugin trigger adapter boundary and non-circular scoring design.
- Feature 14: adapter selection and non-circular runtime input builder.
- Feature 15: repo-local plugin installation readiness.
- Feature 16: isolated installed-plugin runtime probe.
- Feature 17: `plugin-runtime-codex-exec` trigger adapter and runtime blocker classification.
- Feature 18: runtime availability and semantic scoring gates.
- Feature 19: semantic metric formulas behind the gates.
- Feature 20: repeated corpus stability aggregation behind the gates.

Out of scope:

- Shipping the evaluation harness, fixture corpus, or review files in the plugin payload.
- Making the current sandbox's `network_unavailable` runtime path pass.
- Changing Arbor hook packet behavior.
- Adding another semantic dispatcher layer.

## Release Boundary

Plugin payload:

- `plugins/arbor/.codex-plugin/plugin.json`
- `plugins/arbor/hooks.json`
- `plugins/arbor/skills/arbor/`

Repository-only evaluation tooling:

- `scripts/evaluate_hook_triggers.py`
- `scripts/plugin_trigger_adapters.py`
- `scripts/probe_plugin_runtime.py`
- `scripts/validate_plugin_install.py`
- `scripts/eval_fixtures.py`
- `scripts/simulated_dispatcher.py`
- `docs/reviews/hook-trigger-scenarios.md`
- `docs/reviews/hook-trigger-scenarios.json`
- `docs/reviews/features/*.md`
- `docs/reviews/stage-b-plugin-runtime-final-review.md`

Expected packaged payload baseline:

- `.codex-plugin/plugin.json`
- `hooks.json`
- `skills/arbor/SKILL.md`
- `skills/arbor/agents/openai.yaml`
- `skills/arbor/references/agents-template.md`
- `skills/arbor/references/memory-template.md`
- `skills/arbor/references/project-hooks-template.md`
- `skills/arbor/scripts/collect_project_context.py`
- `skills/arbor/scripts/init_project_memory.py`
- `skills/arbor/scripts/register_project_hooks.py`
- `skills/arbor/scripts/run_agents_guide_drift_hook.py`
- `skills/arbor/scripts/run_memory_hygiene_hook.py`
- `skills/arbor/scripts/run_session_startup_hook.py`

## Data Flow

```text
scenario expression + fixture summary + project hook contract + Arbor skill metadata
-> plugin trigger adapter
-> trigger decision contract
-> registered project hook execution when hooks are selected
-> hook packet and side-effect assertions
-> semantic scoring gates
-> semantic metrics
-> repeated-run stability, only when repeated real runtime runs are gate-ready
```

Sidecar expectations remain evaluator-only data. They are never part of plugin runtime input.

## Current Evidence

- Repo-local plugin marketplace and packaged payload validate successfully.
- Packaged Hook 1, Hook 2, and Hook 3 smoke successfully through `scripts/validate_plugin_install.py`.
- Sidecar full-corpus hook execution chain passes: 150/150 scenarios, 103/103 selected hook executions, outside-root leaks 0, unintended writes 0.
- Runtime blockers are classified and excluded from semantic scoring.
- Current `plugin-runtime-codex-exec` smoke reaches the installed-plugin path but is blocked by `network_unavailable`; this is an environment blocker, not an Arbor semantic result.
- Semantic metrics are reported only after adapter eligibility, runtime availability, and hook execution gates pass.
- Repeated-run stability is reported only after repeated gate-ready real runtime reports; sidecar, stub, single-run, and blocked runtime paths withhold stability.
- Compact corpus rows preserve `optional_args`, so repeated-run stability signatures can be replayed from default reports.

## Review Focus

Review agents should focus on:

- Whether the plugin payload excludes evaluation harness and review artifacts.
- Whether `plugin-runtime-codex-exec` receives only non-circular runtime input.
- Whether runtime blockers cannot be counted as semantic `NONE`, false positives, or stable abstentions.
- Whether selected hooks execute through project-local `.codex/hooks.json`.
- Whether hook execution cannot mutate `.codex/memory.md`, `AGENTS.md`, or `.codex/hooks.json` through the trigger adapter path.
- Whether compact and full corpus reports carry enough trigger-decision data for metric and stability replay.
- Whether repeated stability requires real runtime, repeated runs, consistent scenario ids, and clean scoring gates.

## Validation Commands

Current offline validation:

```bash
python3 -m unittest tests/test_arbor_skill.py
env PYTHONPYCACHEPREFIX=/private/tmp/arbor-stage-b-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py scripts/probe_plugin_runtime.py tests/test_arbor_skill.py
conda run -n arbor python -m ruff check . --no-cache
env PYTHONPYCACHEPREFIX=/private/tmp/arbor-stage-b-install-pycache python3 scripts/validate_plugin_install.py
python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor
python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor
python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-stage-b-corpus-sidecar --trigger-adapter sidecar-baseline
python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-stage-b-repeat-stub --trigger-adapter plugin-runtime-stub --repeat-runs 2
python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-stage-b-runtime-smoke --trigger-adapter plugin-runtime-codex-exec
env COVERAGE_FILE=/private/tmp/arbor-stage-b-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py
env COVERAGE_FILE=/private/tmp/arbor-stage-b-coverage conda run -n arbor python -m coverage report
```

Online/authenticated runtime validation:

```bash
python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-stage-b-runtime-corpus --trigger-adapter plugin-runtime-codex-exec
python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-stage-b-runtime-stability --trigger-adapter plugin-runtime-codex-exec --repeat-runs 3
```

## Acceptance Gates

Stage B should be accepted when:

- offline validation passes;
- plugin payload validation confirms only plugin files ship;
- sidecar full-corpus hook execution remains clean;
- runtime blocker paths are withheld from semantic and stability metrics;
- no circular sidecar fields enter runtime trigger input;
- online/runtime-only metrics remain clearly gated behind an available authenticated runtime.

## Developer Status

Stage B is ready for final review. The only unresolved execution gap is environmental: the current sandbox classifies real `codex exec` runtime calls as `network_unavailable`, so measured semantic quality and measured repeated-run stability require an online/authenticated runtime.

## Developer Validation

- `python3 -m unittest tests/test_arbor_skill.py`: 137 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-stage-b-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py scripts/probe_plugin_runtime.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed.
- `python3 scripts/validate_plugin_install.py`: passed; packaged hooks smoke successfully and plugin payload remains limited to packaged Arbor files.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-stage-b-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios, 103/103 hook executions, outside-root leaks 0, unintended writes 0.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-stage-b-repeat-stub --trigger-adapter plugin-runtime-stub --repeat-runs 2`: passed; repeated report emitted and stability withheld because labels are not real runtime labels.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-stage-b-runtime-smoke --trigger-adapter plugin-runtime-codex-exec`: passed; runtime returned `decision=ambiguous`, `hooks=[]`, and `reason=Plugin runtime unavailable: network_unavailable...`.
- `env COVERAGE_FILE=/private/tmp/arbor-stage-b-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 137 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-stage-b-coverage conda run -n arbor python -m coverage report`: total coverage 88%; `scripts/evaluate_hook_triggers.py` coverage 86%.

## Developer Handoff

Give review agents this file first. They can then progressively open the focused feature reviews for any stage component they want to audit:

- `docs/reviews/features/feature-13-plugin-trigger-adapter-design.md`
- `docs/reviews/features/feature-14-plugin-trigger-selection-input-builder.md`
- `docs/reviews/features/feature-15-plugin-installation-readiness.md`
- `docs/reviews/features/feature-16-plugin-runtime-probe.md`
- `docs/reviews/features/feature-17-codex-exec-trigger-adapter.md`
- `docs/reviews/features/feature-18-runtime-availability-scoring-gates.md`
- `docs/reviews/features/feature-19-semantic-metric-formulas.md`
- `docs/reviews/features/feature-20-repeated-runtime-stability.md`

## Review Feedback

### Round 1 - 2026-05-03

#### Findings

| ID | Priority | File | Status | Finding |
| --- | --- | --- | --- | --- |
| StageB-R1-001 | P2 | `scripts/validate_plugin_install.py:87-131` | Added | `validate_plugin_payload` validates required hook ids and script roots, but it does not reject generated bytecode or cache artifacts under the packaged plugin tree. The review probe found `plugins/arbor/skills/arbor/scripts/__pycache__/collect_project_context.cpython-312.pyc` in the payload while `python3 scripts/validate_plugin_install.py` still passed. Stage B's final gate says the plugin payload is clean and limited to packaged Arbor files, so the validator should fail on `__pycache__`, `*.pyc`, and similar transient build artifacts before release. The observed cache file was removed after this finding was recorded. |

#### Test Matrix

| Test Area | Test Cases Run | Coverage | Passed | Pass Rate | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| Feature coverage | 8 feature scopes | 8/8 features | 7/8 clean | 87.5% | Features 13-20 were reviewed as one Stage B flow. The only failed gate is payload cleanliness. |
| Plugin install and payload boundary | 6 cases | 6/6 boundary checks | 5/6 | 83.3% | Marketplace, manifest, exact hook ids, script-root containment, hook smokes, and payload inventory were checked. Payload inventory found a shipped `__pycache__` file that validation misses. |
| Non-circular runtime input | 3 cases | 3/3 data-flow checks | 3/3 | 100% | Runtime input for `H1-P001` had no sidecar scoring fields and carried only expression, project state, hook contract, and skill metadata. |
| Hook execution chain | 150 scenarios / 103 hook executions | 150/150 corpus rows | 150/150 scenarios, 103/103 hooks | 100% | Sidecar full corpus passed with outside-root leaks 0 and unintended writes 0. |
| Runtime blocker gates | 3 cases | 3/3 gate paths | 3/3 | 100% | Real runtime smoke classified `network_unavailable`; synthetic blocked corpus withheld semantic metrics instead of counting abstention as a semantic result. |
| Repeated stability gates | 3 cases | 3/3 stability paths | 3/3 | 100% | Stub repeated run withheld stability; compact gate-ready rows with `optional_args` remained replayable; stability remains real-runtime gated. |
| Regression suite and static quality | 9 commands | 9/9 validation commands | 9/9 | 100% | Unit tests, py_compile, ruff, install validation, both skill quick validates, corpus replay, stub repeat, runtime smoke, and coverage all completed. |

#### Scenario Testing

| Scenario | Target Risk | Method | Result |
| --- | --- | --- | --- |
| Packaged payload inventory | Release payload accidentally includes repo/test/transient artifacts | `find plugins/arbor -path '*/__pycache__/*' -o -name '*.pyc'` after install validation | Failed during review: found `plugins/arbor/skills/arbor/scripts/__pycache__/collect_project_context.cpython-312.pyc`; validator did not reject it. The cache file was removed during cleanup. |
| Plugin install smoke | Packaged skill or hooks do not run from plugin layout | `python3 scripts/validate_plugin_install.py` | Passed: manifest, marketplace, hook ids, packaged skill smoke, and all three hook smokes succeeded. |
| Non-circular input probe | Runtime adapter sees sidecar labels or scoring expectations | Built `H1-P001` runtime input from a clean fixture and scanned `SIDECAR_SCORING_FIELDS` | Passed: forbidden field list was empty; hook contract had 3 hooks. |
| Sidecar full corpus | Registered hook execution breaks or mutates project files | `python3 scripts/evaluate_hook_triggers.py --all --trigger-adapter sidecar-baseline` | Passed: 150/150 scenarios, 103/103 hook executions, outside-root leaks 0, unintended writes 0. |
| Stub repeated corpus | Stability is incorrectly reported for non-real runtime labels | `python3 scripts/evaluate_hook_triggers.py --all --trigger-adapter plugin-runtime-stub --repeat-runs 2` | Passed: 2/2 runs passed; semantic metrics reported runs 0; stability withheld. |
| Real runtime smoke | Environment blocker is misclassified as semantic NONE/ambiguous quality | `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --trigger-adapter plugin-runtime-codex-exec` | Passed: `decision=ambiguous`, `hooks=[]`, blocker reason `network_unavailable`; no semantic score reported on single-scenario smoke. |
| Synthetic blocker gate | Runtime blockers can leak into semantic metrics | Synthetic `network_unavailable` result through `summarize_corpus_results` | Passed: runtime gate `blocked`, blocked count 1, semantic metrics `reported=false`. |
| Compact stability replay | Compact reports lose selected args and become unreplayable | Synthetic compact gate-ready reports with `optional_args` through `compute_repeated_runtime_stability` | Passed: stability reported with `stability_rate=1.0` when gates were marked ready and signatures matched. |
| Protected file mutation replay | Trigger adapter accepts runtime writes to `AGENTS.md`, `.codex/memory.md`, or hooks | Unit regression replay inside `python3 -m unittest tests/test_arbor_skill.py` | Passed: mutation blocker and restore tests are covered in the 137-test suite. |

#### Optimization Suggestions

| Priority | Suggestion | Rationale |
| --- | --- | --- |
| P2 | Extend `validate_plugin_payload` to reject transient artifacts such as `__pycache__/`, `*.pyc`, `.coverage`, temporary files, and editor swap files anywhere under `plugins/arbor`. | This makes the Stage B release boundary machine-enforced instead of relying on manual cleanup. |
| P2 | Add a regression that creates a temporary plugin copy with a generated cache file and asserts install validation fails. | Prevents future validation changes from silently re-allowing polluted payloads. |
| P3 | Add a short payload inventory summary to `scripts/validate_plugin_install.py` output. | Reviewers can see which files were considered part of the distributable plugin without running a separate `find`. |
| P3 | Keep online/authenticated runtime metrics explicitly separate from offline Stage B acceptance. | The current `network_unavailable` classification is correct; semantic quality and stability should remain unavailable until a real runtime is reachable. |

#### Reviewer Verdict

Stage B is functionally converged for the offline trigger evaluation path, hook execution chain, blocker gates, non-circular runtime input, and repeated stability gate design. I would not mark the plugin payload release gate complete until transient generated files are removed from `plugins/arbor` and `validate_plugin_payload` rejects that class of artifact.

## Developer Response

### Round 1 Fix - 2026-05-03

#### Changes

- Fixed `StageB-R1-001` in `scripts/validate_plugin_install.py`.
- Added payload inventory validation before hook/script validation runs.
- `validate_plugin_payload` now rejects transient release artifacts anywhere under `plugins/arbor`, including `__pycache__/`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`, `*.pyc`, `*.pyo`, `.coverage`, `.DS_Store`, editor swap files, temporary files, and backup files ending in `~`.
- `python3 scripts/validate_plugin_install.py` now reports a payload inventory summary with `file_count` and packaged file paths.
- Added regression coverage in `tests/test_arbor_skill.py` that copies the plugin install surface, injects `skills/arbor/scripts/__pycache__/collect_project_context.cpython-312.pyc`, and asserts install validation fails with `transient payload artifact`.
- Added a direct plugin packaging test that fails if any transient artifact is present in the live `plugins/arbor` tree.

#### Validation

- `python3 -m unittest tests.test_arbor_skill.ArborPluginPackagingTests tests.test_arbor_skill.PluginInstallationReadinessTests`: 9 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-stage-b-r1-fix-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py scripts/probe_plugin_runtime.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed.
- `python3 scripts/validate_plugin_install.py`: passed; payload inventory reports 13 packaged files and no transient artifacts.
- `find plugins/arbor -path '*/__pycache__/*' -o -name '*.pyc' -o -name '.coverage' -o -name '*.swp' -o -name '*~'`: no output.
- `python3 -m unittest tests/test_arbor_skill.py`: 138 tests passed.

#### Status

`StageB-R1-001` is fixed and ready for re-review. The online/authenticated runtime metrics remain intentionally separate from offline Stage B acceptance.

### Round 2 Re-review - 2026-05-03

#### Findings

| ID | Priority | File | Status | Finding |
| --- | --- | --- | --- | --- |
| StageB-R2-001 | - | - | No new findings | `StageB-R1-001` is accepted. The validator now walks the packaged plugin inventory before hook validation, rejects transient cache/build/editor artifacts, reports the packaged file inventory, and has regression coverage for injected `__pycache__/*.pyc`. |

#### Test Matrix

| Test Area | Test Cases Run | Coverage | Passed | Pass Rate | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| Developer feedback review | 1 fix response | 1/1 finding replayed | 1/1 accepted | 100% | Reviewed the Round 1 response for `StageB-R1-001`; implementation matches the requested validator and regression-test scope. |
| Focused packaging tests | 9 tests | 9/9 packaging/install checks | 9/9 | 100% | `python3 -m unittest tests.test_arbor_skill.ArborPluginPackagingTests tests.test_arbor_skill.PluginInstallationReadinessTests`. |
| Full regression suite | 138 tests | 138/138 unit/scenario tests | 138/138 | 100% | `python3 -m unittest tests/test_arbor_skill.py` with `PYTHONPYCACHEPREFIX` set outside the repo. |
| Static validation | 2 commands | 2/2 static checks | 2/2 | 100% | `py_compile` and `ruff check . --no-cache` passed. |
| Plugin install validation | 1 command | 1/1 install path | 1/1 | 100% | `python3 scripts/validate_plugin_install.py` passed and reported 13 packaged files. |
| Transient artifact rejection | 4 injected artifacts | 4/4 artifact classes | 4/4 blocked | 100% | Injected `__pycache__/*.pyc`, `.coverage`, `.swp`, and backup `~` into temp plugin copies; all failed with `transient payload artifact(s) found`. |
| Payload cleanliness probe | 1 live-tree scan | 1/1 transient scan | 1/1 clean | 100% | `find plugins/arbor -path '*/__pycache__/*' -o -name '*.pyc' -o -name '.coverage' -o -name '*.swp' -o -name '*~'` returned no output. |
| Hook execution replay | 150 scenarios / 103 hooks | 150/150 corpus rows | 150/150 scenarios, 103/103 hooks | 100% | Sidecar corpus passed with outside-root leaks 0 and unintended writes 0. |
| Runtime and stability gates | 2 commands | 2/2 gate paths | 2/2 | 100% | Stub repeated run withheld stability; real runtime smoke remained correctly classified as `network_unavailable`. |

#### Scenario Testing

| Scenario | Target Risk | Method | Result |
| --- | --- | --- | --- |
| Fixed validator happy path | Valid plugin payload is rejected by the new inventory walk | `python3 scripts/validate_plugin_install.py` | Passed: payload inventory includes 13 packaged files and all packaged hook smokes succeed. |
| Live payload cleanliness | Stale bytecode remains in `plugins/arbor` after tests | `find plugins/arbor ... transient patterns ...` | Passed: no transient artifacts found. |
| Injected bytecode cache | Original finding remains reproducible after fix | Temp plugin copy with `skills/arbor/scripts/__pycache__/collect_project_context.cpython-312.pyc` | Passed: validation rejects it with `transient payload artifact(s) found`. |
| Injected coverage file | Release payload can carry test coverage output | Temp plugin copy with `.coverage` | Passed: validation rejects it. |
| Injected editor artifacts | Release payload can carry editor swap/backup files | Temp plugin copy with `.swp` and `SKILL.md~` | Passed: validation rejects both. |
| Focused regression replay | Added tests do not only check the live tree | Packaging and install-readiness test classes | Passed: 9/9 tests. |
| Full Stage B replay | Payload fix breaks hook execution or Stage B gates | Full unit suite, sidecar corpus, stub repeat, runtime smoke | Passed: no regression observed. |

#### Optimization Suggestions

| Priority | Suggestion | Rationale |
| --- | --- | --- |
| P3 | Consider documenting the exact allowed packaged file set in the release review or validator output baseline. | The current transient denylist fixes the reported issue; an allowlist or reviewed inventory snapshot would make future payload drift easier to audit. |
| P3 | Keep `PYTHONPYCACHEPREFIX` in validation commands that import or execute packaged plugin scripts. | This reduces accidental cache generation during review and release checks. |

#### Reviewer Verdict

`StageB-R1-001` is fixed. Offline Stage B is accepted for the reviewed scope: payload cleanliness is now machine-checked, the original cache-artifact failure mode is blocked, and the broader Stage B hook/runtime gate replay remains green. Online/authenticated runtime quality and repeated stability metrics remain intentionally gated until a real runtime is available.

### Round 2 Optimization Response - 2026-05-03

#### Changes

- Implemented the P3 payload-baseline suggestion in `scripts/validate_plugin_install.py`.
- Added an exact `EXPECTED_PAYLOAD_FILES` allowlist for the 13 packaged Arbor plugin files.
- `validate_payload_inventory` now rejects unexpected packaged files and missing baseline files, after rejecting transient artifacts.
- The install validation JSON now includes `payload.inventory.matches_expected_payload=true` when the shipped payload exactly matches the reviewed baseline.
- Added regression coverage for an unexpected packaged `skills/arbor/README.md` file.
- Implemented the P3 `PYTHONPYCACHEPREFIX` suggestion inside `run_plugin_smoke`: packaged skill and hook smoke subprocesses now execute with a temporary pycache root outside `plugins/arbor`.
- Updated the current Stage B validation command for `scripts/validate_plugin_install.py` to show `PYTHONPYCACHEPREFIX` explicitly.
- Documented the exact expected packaged payload baseline in this Stage B review.

#### Validation

- `python3 -m unittest tests.test_arbor_skill.ArborPluginPackagingTests tests.test_arbor_skill.PluginInstallationReadinessTests`: 9 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-stage-b-r2-opt-pycache python3 -m py_compile scripts/validate_plugin_install.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-stage-b-r2-opt-install-pycache python3 scripts/validate_plugin_install.py`: passed; payload inventory reports 13 files and `matches_expected_payload=true`.
- `find plugins/arbor -path '*/__pycache__/*' -o -name '*.pyc' -o -name '.coverage' -o -name '*.swp' -o -name '*~'`: no output.
- `python3 -m unittest tests/test_arbor_skill.py`: 138 tests passed.

#### Status

Round 2 P3 optimizations are implemented and ready for re-review. Offline Stage B remains accepted for the reviewed scope; online/authenticated semantic quality and stability metrics remain gated.

### Round 3 Re-review - 2026-05-03

#### Findings

| ID | Priority | File | Status | Finding |
| --- | --- | --- | --- | --- |
| StageB-R3-001 | P2 | `scripts/validate_plugin_install.py:139-162` | Added | `validate_payload_inventory` now enforces an exact file-name baseline, but it still treats symlinks as acceptable payload members. `Path.is_file()` follows symlinks, so replacing an expected file such as `skills/arbor/references/memory-template.md` with a symlink to a file outside `plugins/arbor` still returns `matches_expected_payload=true`. An extra symlink directory under `plugins/arbor` is also ignored by `iter_payload_files` and passes validation. Reject symlinks and other non-regular payload entries before reporting the payload as exactly matching the reviewed baseline. |

#### Test Matrix

| Test Area | Test Cases Run | Coverage | Passed | Pass Rate | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| Developer optimization review | 2 P3 optimizations | 2/2 reviewed | 1/2 accepted | 50% | The file allowlist and external pycache smoke are useful, but symlink payload entries bypass the allowlist. |
| Focused packaging tests | 9 tests | 9/9 packaging/install checks | 9/9 | 100% | `python3 -m unittest tests.test_arbor_skill.ArborPluginPackagingTests tests.test_arbor_skill.PluginInstallationReadinessTests` passed. |
| Full regression suite | 138 tests | 138/138 unit/scenario tests | 138/138 | 100% | Full unit suite passed with `PYTHONPYCACHEPREFIX` outside the repo. |
| Static validation | 2 commands | 2/2 static checks | 2/2 | 100% | `py_compile` for touched files and `ruff check . --no-cache` passed. |
| Plugin install validation | 1 command | 1/1 normal install path | 1/1 | 100% | Install validation passed and reported 13 files with `matches_expected_payload=true`. |
| Live transient scan | 1 scan | 1/1 transient patterns | 1/1 clean | 100% | No `__pycache__`, `*.pyc`, `.coverage`, `*.swp`, or backup files were found under `plugins/arbor`. |
| Allowlist adversarial probes | 2 symlink cases | 2/2 symlink classes | 0/2 blocked | 0% | Expected-file symlink escape and unexpected symlink directory both passed with `matches_expected_payload=true`. |
| Hook/runtime replay | 3 commands | sidecar, stub repeat, runtime smoke | 3/3 | 100% | Sidecar corpus passed 150/150 scenarios and 103/103 hooks; stub stability withheld; runtime smoke remained `network_unavailable`. |

#### Scenario Testing

| Scenario | Target Risk | Method | Result |
| --- | --- | --- | --- |
| Expected payload baseline happy path | New allowlist rejects valid packaged Arbor files | `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-stage-b-r2-review-install-pycache python3 scripts/validate_plugin_install.py` | Passed: 13 files reported and `matches_expected_payload=true`. |
| Unexpected regular file | Extra release file is allowed despite allowlist | Existing regression injects `skills/arbor/README.md` | Passed: focused test suite covers rejection. |
| Expected-file symlink escape | Baseline filename points outside packaged plugin root | Temp plugin copy replaced `skills/arbor/references/memory-template.md` with a symlink to `/private/tmp/.../outside-memory-template.md` | Failed: validation accepted it and returned `matches_expected_payload=true`. |
| Unexpected symlink directory | Extra payload tree avoids file inventory | Temp plugin copy added `plugins/arbor/outside_link -> /private/tmp/.../outside-dir` | Failed: validation accepted it and returned `matches_expected_payload=true`. |
| External pycache smoke | Packaged hook smoke writes cache files into plugin tree | `run_plugin_smoke` path through install validation plus live transient scan | Passed: no transient cache files remained under `plugins/arbor`. |
| Stage B replay | Optimization breaks trigger/hook evaluation | Sidecar full corpus, stub repeated corpus, and real runtime smoke | Passed: no hook/runtime regression observed. |

#### Optimization Suggestions

| Priority | Suggestion | Rationale |
| --- | --- | --- |
| P2 | Walk every payload entry, not just `path.is_file()` results, and reject any `path.is_symlink()` or unsupported file type under `plugins/arbor`. | The reviewed payload baseline should describe real packaged files, not references to external content or hidden directory links. |
| P2 | Add regressions for replacing an expected file with a symlink and adding an unexpected symlink directory. | These are the two bypasses observed in the re-review. |
| P3 | Keep the 13-file allowlist and `matches_expected_payload=true` output after symlink rejection is added. | The optimization is still valuable once the inventory walker proves entries are regular in-package files. |

#### Reviewer Verdict

The P3 optimization mostly works for regular files and pycache hygiene, but it is not converged yet. `StageB-R3-001` should be fixed before considering the payload baseline release gate complete, because symlink payload entries can currently bypass the exact file inventory.

### Round 3 Fix - 2026-05-03

#### Changes

- Fixed `StageB-R3-001` in `scripts/validate_plugin_install.py`.
- Replaced the file-only payload walk with an entry-level inventory walk across every path under `plugins/arbor`.
- Added `EXPECTED_PAYLOAD_DIRS`, derived from the expected file baseline, so normal payload directories are accepted only when they are required parents of reviewed payload files.
- `validate_payload_inventory` now rejects any symlink payload entry before reporting `matches_expected_payload=true`.
- `validate_payload_inventory` now rejects unsupported entry types and unexpected directories, including empty directories that file-only inventory would ignore.
- Removed the empty non-baseline `plugins/arbor/hooks/` directory from the live plugin tree.
- Added regression coverage for replacing an expected payload file with a symlink to an outside file.
- Added regression coverage for adding an unexpected symlink directory.
- Added regression coverage for adding an unexpected empty directory.
- Added a direct live-tree test that fails if any symlink exists under `plugins/arbor`.

#### Validation

- `python3 -m unittest tests.test_arbor_skill.PluginInstallationReadinessTests tests.test_arbor_skill.ArborPluginPackagingTests`: 10 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-stage-b-r3-fix-pycache python3 -m py_compile scripts/validate_plugin_install.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-stage-b-r3-fix-install-pycache python3 scripts/validate_plugin_install.py`: passed; payload inventory reports 13 files and `matches_expected_payload=true`.
- `find plugins/arbor -type l -o -path '*/__pycache__/*' -o -name '*.pyc' -o -name '.coverage' -o -name '*.swp' -o -name '*~'`: no output.
- `python3 -m unittest tests/test_arbor_skill.py`: 139 tests passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-stage-b-r3-fix-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios, 103/103 selected hook executions, outside-root leaks 0, unintended writes 0.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-stage-b-r3-fix-repeat-stub --trigger-adapter plugin-runtime-stub --repeat-runs 2`: passed; 2/2 runs passed, semantic metrics reported runs 0, stability withheld.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-stage-b-r3-fix-runtime-smoke --trigger-adapter plugin-runtime-codex-exec`: passed; runtime returned `network_unavailable` blocker and selected no hooks.

#### Status

`StageB-R3-001` is fixed and ready for re-review. The payload baseline gate now requires reviewed regular files, reviewed directories, no symlinks, no transient artifacts, and no unexpected payload drift.

### Round 4 Re-review - 2026-05-03

#### Findings

| ID | Priority | File | Status | Finding |
| --- | --- | --- | --- | --- |
| StageB-R4-001 | - | - | No new findings | `StageB-R3-001` is accepted. The payload inventory now walks every entry under `plugins/arbor`, rejects symlinks before baseline matching, rejects unexpected directories, and still reports the 13-file payload with `matches_expected_payload=true` on the valid path. |

#### Test Matrix

| Test Area | Test Cases Run | Coverage | Passed | Pass Rate | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| Developer feedback review | 1 fix response | 1/1 finding replayed | 1/1 accepted | 100% | Reviewed the Round 3 fix for `StageB-R3-001`; implementation covers symlink and unexpected-directory payload entries. |
| Focused packaging tests | 10 tests | 10/10 packaging/install checks | 10/10 | 100% | `python3 -m unittest tests.test_arbor_skill.PluginInstallationReadinessTests tests.test_arbor_skill.ArborPluginPackagingTests`. |
| Full regression suite | 139 tests | 139/139 unit/scenario tests | 139/139 | 100% | `python3 -m unittest tests/test_arbor_skill.py` with `PYTHONPYCACHEPREFIX` outside the repo. |
| Static validation | 2 commands | 2/2 static checks | 2/2 | 100% | `py_compile` for touched files and `ruff check . --no-cache` passed. |
| Plugin install validation | 1 command | 1/1 normal install path | 1/1 | 100% | Install validation passed and reported 13 files with `matches_expected_payload=true`. |
| Payload adversarial probes | 3 injected entries | 3/3 payload bypass classes | 3/3 blocked | 100% | Expected-file symlink escape, unexpected symlink directory, and unexpected empty directory were all rejected. |
| Live payload scan | 1 scan | 1/1 symlink/transient patterns | 1/1 clean | 100% | No symlinks or transient artifacts were found under `plugins/arbor`. |
| Hook/runtime replay | 3 commands | sidecar, stub repeat, runtime smoke | 3/3 | 100% | Sidecar corpus passed 150/150 scenarios and 103/103 hooks; stub stability withheld; runtime smoke remained `network_unavailable`. |

#### Scenario Testing

| Scenario | Target Risk | Method | Result |
| --- | --- | --- | --- |
| Valid payload baseline | Entry-level inventory rejects valid packaged Arbor tree | `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-stage-b-r3-review-install-pycache python3 scripts/validate_plugin_install.py` | Passed: 13 files reported and `matches_expected_payload=true`. |
| Expected-file symlink escape | Baseline filename points outside packaged plugin root | Temp plugin copy replaced `skills/arbor/references/memory-template.md` with a symlink to `/private/tmp/.../outside-memory-template.md` | Passed: validation rejects it with `symlink payload entry not allowed`. |
| Unexpected symlink directory | Extra payload tree avoids file inventory | Temp plugin copy added `plugins/arbor/outside_link -> /private/tmp/.../outside-dir` | Passed: validation rejects it with `symlink payload entry not allowed`. |
| Unexpected empty directory | Directory-only payload drift is ignored | Temp plugin copy added `plugins/arbor/extra-empty-dir` | Passed: validation rejects it with `unexpected packaged payload directories`. |
| Live payload cleanliness | Current plugin tree has symlinks or transient artifacts after tests | `find plugins/arbor -type l -o -path '*/__pycache__/*' -o -name '*.pyc' -o -name '.coverage' -o -name '*.swp' -o -name '*~'` | Passed: no output. |
| Stage B replay | Payload fix breaks hook execution or runtime gates | Sidecar full corpus, stub repeated corpus, and real runtime smoke | Passed: no hook/runtime regression observed. |

#### Optimization Suggestions

| Priority | Suggestion | Rationale |
| --- | --- | --- |
| P3 | Keep the entry-level payload inventory as the release gate for future plugin packaging changes. | This now covers regular files, expected directories, symlinks, transient artifacts, and empty-directory drift. |
| P3 | If new packaged files are intentionally added later, update both `EXPECTED_PAYLOAD_FILES` and the Stage B payload baseline together. | Keeps the code gate and review artifact synchronized. |

#### Reviewer Verdict

`StageB-R3-001` is fixed. The payload baseline gate is now accepted for the reviewed scope: it requires the reviewed 13 regular files, only reviewed parent directories, no symlinks, no transient artifacts, and no unexpected payload entries. Offline Stage B remains accepted; online/authenticated semantic quality and repeated stability metrics remain gated by runtime availability.

### Round 4 Optimization Response - 2026-05-03

#### Changes

- Implemented the P3 baseline-synchronization suggestion in `tests/test_arbor_skill.py`.
- Added `stage_b_review_payload_baseline()`, which parses the `Expected packaged payload baseline` section in this review document.
- Added a regression asserting the parsed Stage B payload baseline exactly matches `scripts/validate_plugin_install.py::EXPECTED_PAYLOAD_FILES`.
- Kept `validate_payload_inventory` as the release gate: the validator still enforces entry-level payload inventory, regular expected files, expected parent directories, no symlinks, no transient artifacts, and no unexpected payload entries.

#### Validation

- `python3 -m unittest tests.test_arbor_skill.ArborPluginPackagingTests`: 8 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-stage-b-r4-opt-pycache python3 -m py_compile tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check tests/test_arbor_skill.py --no-cache`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-stage-b-r4-opt-install-pycache python3 scripts/validate_plugin_install.py`: passed; payload inventory reports 13 files and `matches_expected_payload=true`.
- `find plugins/arbor -type l -o -path '*/__pycache__/*' -o -name '*.pyc' -o -name '.coverage' -o -name '*.swp' -o -name '*~'`: no output.
- `python3 -m unittest tests/test_arbor_skill.py`: 140 tests passed.

#### Status

Round 4 P3 optimizations are implemented and ready for re-review. Future packaged payload changes now need to update both the validator allowlist and this Stage B review baseline, or the packaging test suite fails.

### Round 5 Re-review - 2026-05-03

#### Findings

| ID | Priority | File | Status | Finding |
| --- | --- | --- | --- | --- |
| StageB-R5-001 | - | - | No new findings | Round 4 P3 baseline-synchronization optimization is accepted. `stage_b_review_payload_baseline()` parses the documented `Expected packaged payload baseline`, and the packaging test now fails if that reviewed baseline drifts from `scripts/validate_plugin_install.py::EXPECTED_PAYLOAD_FILES`. |

#### Test Matrix

| Test Area | Test Cases Run | Coverage | Passed | Pass Rate | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| Developer feedback review | 1 optimization response | 1/1 Round 4 optimization replayed | 1/1 accepted | 100% | Reviewed the baseline parser and the new allowlist synchronization regression. |
| Baseline synchronization | 2 tests | 2/2 baseline drift checks | 2/2 | 100% | `ArborPluginPackagingTests` includes the new regression, and a direct probe confirmed the parsed review baseline exactly equals `EXPECTED_PAYLOAD_FILES`. |
| Focused packaging tests | 8 tests | 8/8 Arbor packaging checks | 8/8 | 100% | `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-stage-b-r4-review-pycache python3 -m unittest tests.test_arbor_skill.ArborPluginPackagingTests` passed. |
| Full regression suite | 140 tests | 140/140 unit/scenario tests | 140/140 | 100% | `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-stage-b-r4-review-pycache python3 -m unittest tests/test_arbor_skill.py` passed. |
| Static validation | 2 commands | 2/2 static checks | 2/2 | 100% | `py_compile` for `tests/test_arbor_skill.py` and `scripts/validate_plugin_install.py` passed; `ruff check tests/test_arbor_skill.py scripts/validate_plugin_install.py --no-cache` passed. |
| Plugin install validation | 1 command | 1/1 normal install path | 1/1 | 100% | `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-stage-b-r4-review-install-pycache python3 scripts/validate_plugin_install.py` passed with 13 files and `matches_expected_payload=true`. |
| Payload adversarial probes | 3 injected entries | 3/3 payload bypass classes | 3/3 blocked | 100% | Unexpected regular file, expected-file symlink escape, and unexpected empty directory were all rejected. |
| Live payload scan | 1 scan | 1/1 symlink/transient patterns | 1/1 clean | 100% | No symlinks, `__pycache__`, `*.pyc`, `.coverage`, swap files, or backup files were found under `plugins/arbor`. |
| Hook/runtime replay | 3 commands | sidecar, stub repeat, runtime smoke | 3/3 | 100% | Sidecar corpus passed 150/150 scenarios and 103/103 hook executions; stub repeat passed 2/2 runs with stability withheld; runtime smoke remained the expected `network_unavailable` blocker. |

#### Scenario Testing

| Scenario | Target Risk | Method | Result |
| --- | --- | --- | --- |
| Review baseline parser | Parser silently misses or over-includes documented payload rows | Directly parsed the `Expected packaged payload baseline` section and compared it to `EXPECTED_PAYLOAD_FILES` | Passed: both sides produced the same 13-file sorted baseline. |
| Packaging regression path | New synchronization test is not wired into the focused suite | `python3 -m unittest tests.test_arbor_skill.ArborPluginPackagingTests` | Passed: 8/8 packaging tests passed, including the baseline synchronization regression. |
| Valid payload baseline | New parser/test change breaks install validation | `python3 scripts/validate_plugin_install.py` with pycache redirected outside the repo | Passed: 13 files reported and `matches_expected_payload=true`. |
| Unexpected regular file | Extra packaged file is accepted because the documented baseline still matches | Temp plugin copy added `skills/arbor/README.md` | Passed: validation rejects the unexpected file. |
| Expected-file symlink escape | Reviewed filename is present but points outside packaged plugin root | Temp plugin copy replaced `skills/arbor/references/memory-template.md` with an external symlink | Passed: validation rejects the symlink payload entry. |
| Unexpected empty directory | Directory-only payload drift remains invisible | Temp plugin copy added an unexpected empty directory | Passed: validation rejects the unexpected directory. |
| Stage B replay | Baseline synchronization change regresses hook execution-chain quality | Sidecar full corpus, stub repeated corpus, and real runtime smoke | Passed: no hook/runtime regression observed. |

#### Optimization Suggestions

| Priority | Suggestion | Rationale |
| --- | --- | --- |
| P3 | Keep future packaged payload additions in the same review/update unit across `EXPECTED_PAYLOAD_FILES` and the Stage B baseline section. | The new regression intentionally makes documentation and validator drift fail fast. |
| P3 | If the baseline section grows more complex, add explicit start/end markers before extending the parser. | The current heading-and-bullet parser is adequate for the reviewed structure; markers would reduce future formatting sensitivity. |

#### Reviewer Verdict

Round 4 optimization is accepted. No new findings were found in the replay. Offline Stage B remains accepted for the reviewed scope: exact 13-file packaged payload, documented baseline synchronization, no symlinks, no transient artifacts, no unexpected payload entries, clean hook execution-chain replay, and runtime semantic metrics still gated by real plugin runtime availability.
