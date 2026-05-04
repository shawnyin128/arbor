# Arbor Skill Review

## Purpose

Track the whole Arbor project-memory skill feature at a high level. Keep this file as the review index. Detailed review evidence belongs in one subfeature review file per feature so review agents can read progressively.

## Development Target

Create a standalone Codex skill named `arbor`, later composable into a plugin with the same name, that manages project initialization and memory hygiene for daily development.

The skill should:

- Initialize `.codex/memory.md` for project-local session memory.
- Initialize `AGENTS.md` with `Project Goal`, `Project Constraints`, and `Project Map`.
- Load startup context in order: `AGENTS.md`, formatted git log, `.codex/memory.md`, `git status`.
- Keep memory and hook behavior project-level.
- Avoid making the skill a bottleneck: fix workflow order, not read depth.

## Review Structure

- Use this file for the feature map, status, and routing.
- Use subfeature review files for detailed implementation notes, adversarial review rounds, test matrices, and developer responses.
- Use `docs/reviews/arbor-final-delivery.md` for the current-scope delivery summary and handoff commands.
- Append one row here when a new feature starts or completes.
- Do not duplicate detailed subfeature evidence here.

## Current Status

Status: release-ready for the current Arbor skill/plugin scope. Feature 25's retained authenticated real-runtime full corpus passed 150/150 scenarios, 111/111 selected hook executions, and reported passing semantic trigger metrics with 0 runtime blockers, 0 outside-root leaks, and 0 unintended writes.

Current completed features:

- Feature 1: Arbor initializer and startup flow MVP.
- Feature 2: startup fallback diagnostics.
- Feature 3: project hook registration skeleton.
- Feature 4: session startup hook execution.
- Feature 5: in-session memory hook execution.
- Feature 6: AGENTS drift hook execution.
- Feature 7: Arbor plugin packaging.
- Feature 8: plugin-based trigger scenario sidecar.
- Feature 9: dispatch eval fixture builders.
- Feature 10: simulated dispatcher adapter.
- Feature 11: registered hook execution harness.
- Feature 12: full-corpus hook execution report.
- Feature 13: plugin trigger adapter design.
- Feature 14: plugin trigger selection and non-circular input builder.
- Feature 15: plugin installation readiness.
- Feature 16: real plugin runtime probe.
- Feature 17: Codex exec plugin runtime trigger adapter.
- Feature 18: runtime availability and semantic scoring gates.
- Feature 19: semantic metric formulas for real plugin trigger output.
- Feature 20: repeated runtime corpus stability evaluation.
- Stage B final review: plugin runtime trigger evaluation closure.
- Feature 21: authenticated installed-plugin runtime probe.
- Feature 22: authenticated runtime corpus controls.
- Feature 23: runtime schema compatibility and smoke gates.
- Feature 24: runtime batch execution controls.
- Feature 25: authenticated real-runtime full corpus.

Current next step:

- Publish or hand off the repo-local `plugins/arbor` package. Repeated authenticated runtime stability remains an optional future enhancement, not a release blocker.

## Feature Index

| Feature | Purpose | Status | Detailed review |
| --- | --- | --- | --- |
| Feature 0: design and review setup | Establish the design doc, review workflow, project-level memory/hook boundaries, and no-read-limit principle. | Complete | This index plus `docs/arbor-skill-design.md` |
| Feature 1: Arbor initializer and startup flow MVP | Scaffold `skills/arbor`, create project memory templates, initialize `AGENTS.md` and `.codex/memory.md`, and provide the first ordered startup context collector. | Accepted after review and optimization | `docs/reviews/features/feature-1-initializer-startup-flow.md` |
| Feature 2: startup fallback diagnostics | Upgrade the collector into a stable startup diagnostic packet with per-section status/source/detail while preserving raw content and read-depth freedom. | Accepted after re-review | `docs/reviews/features/feature-2-startup-fallback-diagnostics.md` |
| Feature 3: project hook registration skeleton | Add visible project-level hook registration artifacts and fold memory freshness into the in-session hook workflow instead of creating a standalone semantic checker. | Accepted after re-review | `docs/reviews/features/feature-3-project-hook-registration.md` |
| Feature 4: session startup hook execution | Turn the registered `arbor.session_startup_context` intent into a concrete Hook 1 execution path before designing later hooks. | Accepted after re-review | `docs/reviews/features/feature-4-session-startup-hook.md` |
| Feature 5: in-session memory hook execution | Turn the registered `arbor.in_session_memory_hygiene` intent into a concrete Hook 2 packet-generation path before designing Hook 3. | Accepted after re-review | `docs/reviews/features/feature-5-in-session-memory-hook.md` |
| Feature 6: AGENTS drift hook execution | Turn the registered `arbor.goal_constraint_drift` intent into a concrete Hook 3 packet-generation path for durable `AGENTS.md` updates. | Accepted after review | `docs/reviews/features/feature-6-agents-drift-hook.md` |
| Feature-level hook trigger review | Review whether the complete Arbor flow has clear semantic activation boundaries across positive, negative, cross-language, and ambiguous hook scenarios. | Stage A and sidecar-backed Stage B accepted; authenticated selected runtime batches now available through Feature 24 | `docs/reviews/features/feature-level-hook-trigger-review.md` plus `docs/reviews/hook-trigger-scenarios.md` |
| Feature 7: Arbor plugin packaging | Package the accepted standalone Arbor skill and hook contract into a repo-local Codex plugin without adding semantic dispatch. | Accepted after review | `docs/reviews/features/feature-7-plugin-packaging.md` |
| Feature 8: trigger scenario sidecar | Convert the human-readable hook trigger corpus into machine-checkable structured expectations for future plugin-based dispatch evaluation. | Accepted after re-review | `docs/reviews/features/feature-8-trigger-sidecar.md` |
| Feature 9: dispatch eval fixture builders | Generate deterministic temporary project fixtures and summaries for Stage B dispatch evaluation without implementing dispatcher decisions or metrics. | Accepted after review | `docs/reviews/features/feature-9-fixture-builders.md` |
| Feature 10: simulated dispatcher adapter | Emit dispatcher-contract JSON from sidecar expectations so the next harness increment can test dispatch plumbing before real semantic dispatch. | Accepted after review | `docs/reviews/features/feature-10-simulated-dispatcher.md` |
| Feature 11: registered hook execution harness | Execute selected hooks through fixture-local `.codex/hooks.json` entrypoints and assert packet shape, outside-root rejection, and no unintended memory writes. | Accepted after review | `docs/reviews/features/feature-11-hook-execution-harness.md` |
| Feature 12: full-corpus hook execution report | Run all 150 scenarios through the sidecar-backed Stage B harness and report hook execution-chain quality without semantic trigger metrics. | Accepted in final closure | `docs/reviews/features/feature-12-full-corpus-report.md` |
| Feature 13: plugin trigger adapter design | Define the adapter boundary, non-circular input rules, and semantic metric gates for replacing the sidecar-backed baseline with true plugin trigger evaluation. | Implemented and self-tested; pending review | `docs/reviews/features/feature-13-plugin-trigger-adapter-design.md` |
| Feature 14: plugin trigger selection and input builder | Add harness trigger-adapter selection, trigger decision contract validation, and a non-circular `plugin-runtime-stub` input path without reporting semantic metrics. | Implemented and self-tested; pending review | `docs/reviews/features/feature-14-plugin-trigger-selection-input-builder.md` |
| Feature 15: plugin installation readiness | Add a repo-local marketplace and isolated install-readiness validation so Arbor can be tested as an installable Codex plugin package. | Accepted after re-review | `docs/reviews/features/feature-15-plugin-installation-readiness.md` |
| Feature 16: real plugin runtime probe | Add an isolated installed-plugin runtime probe that enables `arbor@arbor-local`, optionally runs real `codex exec`, and classifies runtime blockers before semantic metrics. | Accepted after re-review | `docs/reviews/features/feature-16-plugin-runtime-probe.md` |
| Feature 17: Codex exec plugin runtime trigger adapter | Add `plugin-runtime-codex-exec`, which invokes an isolated installed Arbor plugin runtime for trigger decision JSON and classifies blockers without executing hooks. | Accepted after re-review | `docs/reviews/features/feature-17-codex-exec-trigger-adapter.md` |
| Feature 18: runtime availability and semantic scoring gates | Add explicit semantic scoring readiness gates so runtime blockers, sidecar decisions, and hook execution failures are not counted as semantic trigger quality. | Accepted after review | `docs/reviews/features/feature-18-runtime-availability-scoring-gates.md` |
| Feature 19: semantic metric formulas for real plugin trigger output | Compute semantic trigger metrics only after scoring gates pass, while keeping runtime blockers and evaluation tooling out of plugin payload. | Accepted after optimization re-review | `docs/reviews/features/feature-19-semantic-metric-formulas.md` |
| Feature 20: repeated runtime corpus stability evaluation | Run full-corpus evaluation repeatedly and report trigger stability only for repeated, gate-ready real plugin runtime reports. | Accepted after re-review | `docs/reviews/features/feature-20-repeated-runtime-stability.md` |
| Stage B final review: plugin runtime trigger evaluation | Review Feature 13-20 as one completed stage, including release boundary, non-circular runtime input, blocker gating, semantic metrics, and repeated stability. | Round 4 payload-baseline synchronization optimization implemented | `docs/reviews/stage-b-plugin-runtime-final-review.md` |
| Feature 21: authenticated installed-plugin runtime probe | Materialize Arbor into isolated Codex plugin cache, copy explicit auth, trust the probe project, and verify true `$arbor` runtime injection before side-effect gates. | Accepted after re-review | `docs/reviews/features/feature-21-authenticated-runtime-probe.md` |
| Feature 22: authenticated runtime corpus controls | Add authenticated runtime options and corpus CLI flags for `plugin-runtime-codex-exec` so real installed-plugin scenario runs can copy explicit auth into isolated runtime homes. | Accepted after review | `docs/reviews/features/feature-22-authenticated-runtime-corpus-controls.md` |
| Feature 23: runtime schema compatibility and smoke gates | Make the real runtime trigger output schema strict-compatible, preserve optional-args contract semantics, add redacted runtime diagnostics, and prove one positive plus one negative authenticated smoke. | Accepted after re-review | `docs/reviews/features/feature-23-runtime-schema-compatibility-smoke.md` |
| Feature 24: runtime batch execution controls | Add selected real-runtime batch execution, progress JSONL, and adapter optional-args normalization so failed runtime scenarios can be replayed without running the full corpus. | Accepted after re-review | `docs/reviews/features/feature-24-runtime-batch-execution.md` |
| Feature 25: authenticated real-runtime full corpus | Run the full 150-scenario authenticated installed-plugin runtime corpus, retain report/progress artifacts, and close semantic trigger metrics for the current release scope. | Accepted after validation | `docs/reviews/features/feature-25-real-runtime-full-corpus.md` |

## Project-Level Decisions

- Arbor hooks are project-level. The future plugin may distribute hook entrypoints, but `$arbor` should register them into the current project's hook configuration.
- Hook execution must resolve the current project root and read/write only that project's `AGENTS.md` and `.codex/memory.md`.
- No user-level/global Arbor memory is part of the current design.
- Feature 3 uses `.codex/hooks.json` as the first visible project-level hook contract.
- Hook runtime implementation proceeds one hook at a time: session startup first, in-session memory second, goal/constraint drift third.
- Coverage commands should use `COVERAGE_FILE=/private/tmp/...` to avoid leaving `.coverage` in the project root.

## Environment Notes

### Historical Feature 0 Snapshot

- Working directory: `/Users/shawn/Desktop/arbor`
- Git repository: no
- Current repo contents before Feature 0: empty directory

### Current Snapshot

- Working directory: `/Users/shawn/Desktop/arbor`
- Git repository: yes, on `master`.
- Current committed baseline: `ef4e75e Initial Arbor skill and plugin package`.
- Current uncommitted work: Feature 13 through Feature 25 plugin trigger/install/runtime-probe/scoring-gate/semantic-metric/repeated-stability/authenticated-runtime documentation and implementation plus release-closure notes.

## Validation Summary

Latest validation from release closure:

- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-release-pycache python3 scripts/validate_plugin_install.py --codex-probe`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 186 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-release-pycache python3 -m py_compile ...`: passed for standalone skill scripts, packaged skill scripts, evaluation scripts, install/runtime probe scripts, and tests.
- Plugin manifest, packaged hooks, and repo-local marketplace JSON validation passed.
- `git diff --check`: passed.
- Retained authenticated runtime evidence remains `docs/reviews/artifacts/feature-25-full-corpus-r4-report.json`: 150/150 scenarios passed, 111/111 hook executions passed, semantic metrics passed.

Prior validation from Feature 24 Round 1 optional-args hardening:

- Round 1 malformed optional-args hardening:
  - H3 rejects lone `--doc`, empty `--doc=`, option-like missing doc values, and unknown H3 flags.
  - H2/H1 reject lone `--diff-args`, lone `--git-log-args`, empty values, and unknown option shapes.
  - Malformed optional args now fail at adapter validation instead of being silently dropped or deferred to hook argparse.
- Focused adapter plus harness/progress regression: 64 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f24-r1-pycache python3 -m py_compile scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py tests/test_arbor_skill.py --no-cache`: passed.
- `python3 -m unittest tests.test_arbor_skill`: 174 tests passed.
- `git diff --check`: passed.

Prior validation from Feature 24 runtime batch execution controls:

- `scripts/evaluate_hook_triggers.py` now supports selected corpus batches with `--scenario-ids` and per-scenario progress events with `--progress-jsonl`.
- `scripts/plugin_trigger_adapters.py` now normalizes model-natural optional args before hook execution:
  - bare H3 doc paths become repeated `--doc <path>` args;
  - joined or split H2 `--diff-args --stat` becomes `--diff-args=--stat`;
  - joined or split H1 `--git-log-args ...` values preserve spaces as one option value.
- Real authenticated replay of prior failures `CL-P010`, `CL-P012`, and `M-P003`: passed, with 4/4 selected hook executions passing.
- Selected 25-scenario authenticated real-runtime batch: 25/25 scenarios passed, 18/18 selected hook executions passed, runtime availability gate passed, hook execution gate passed, none false-positive rate 0.0, near-miss false-positive rate 0.0.
- `python3 -m unittest tests.test_arbor_skill.HookTriggerPluginAdapterTests`: 28 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f24-fix2-pycache python3 -m py_compile scripts/plugin_trigger_adapters.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check scripts/plugin_trigger_adapters.py tests/test_arbor_skill.py --no-cache`: passed.
- Direct normalized hook argv smokes for H1 `--git-log-args=--max-count=1` and H2 `--diff-args=--stat`: passed.
- `python3 -m unittest tests.test_arbor_skill`: 168 tests passed.

Latest validation from Feature 23 Round 1 smoke-gate fix:

- `scripts/evaluate_hook_triggers.py` now supports explicit single-scenario smoke expectations via `--require-runtime-available`, `--expect-decision`, and `--expect-hooks`.
- Smoke expectations add `smoke_assertions` and return nonzero only when expectation flags are supplied and unmet.
- Default corpus/scoring behavior is preserved: runtime blockers remain accepted as unscored blocker decisions unless smoke expectations are requested.
- Authenticated H1 smoke now asserts runtime availability, `decision=trigger`, and exact hook `arbor.session_startup_context`.
- Authenticated negative smoke now asserts runtime availability, `decision=none`, and no hooks.
- `python3 -m unittest tests.test_arbor_skill.HookTriggerPluginAdapterTests tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 49 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f23-r1-pycache python3 -m py_compile scripts/evaluate_hook_triggers.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check scripts/evaluate_hook_triggers.py tests/test_arbor_skill.py --no-cache`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f23-r1-full-pycache python3 -m unittest tests/test_arbor_skill.py`: 159 tests passed.
- `git diff --check`: passed.

Prior validation from Feature 23 runtime schema compatibility and smoke gates:

- `scripts/plugin_trigger_adapters.py` now emits a strict structured-output-compatible `optional_args` schema and normalizes empty schema-required hook keys before validation.
- Runtime blocker reasons can include short redacted diagnostics, while `runtime_availability_gate` still groups by stable blocker class.
- `scripts/evaluate_hook_triggers.py` now rejects non-positive `--runtime-timeout` values before runtime execution.
- Authenticated real-runtime H1 smoke selected `arbor.session_startup_context` and the registered hook executed successfully.
- Authenticated real-runtime negative smoke returned `decision=none` and selected no hooks.
- `python3 -m unittest tests.test_arbor_skill.HookTriggerPluginAdapterTests tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 45 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f23-schema-pycache python3 -m py_compile scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py tests/test_arbor_skill.py --no-cache`: passed.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-f23-timeout-smoke --trigger-adapter plugin-runtime-codex-exec --runtime-timeout 0`: failed early as expected with `must be a positive integer`.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f23-full-pycache python3 -m unittest tests/test_arbor_skill.py`: 155 tests passed.
- `git diff --check`: passed.

Prior validation from Feature 22 authenticated runtime corpus controls:

- `scripts/plugin_trigger_adapters.py` now accepts `RuntimeAdapterOptions` for Codex binary, timeout, and explicit auth source.
- `scripts/evaluate_hook_triggers.py` now forwards runtime options through scenario, corpus, and repeated-corpus runs and exposes `--auth-source-home`, `--runtime-timeout`, and `--codex-bin`.
- Missing requested auth returns an `auth_required` runtime blocker and remains unscored.
- `python3 -m unittest tests.test_arbor_skill.HookTriggerPluginAdapterTests tests.test_arbor_skill.HookTriggerExecutionHarnessTests tests.test_arbor_skill.PluginRuntimeProbeTests`: 53 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f22-pycache python3 -m py_compile scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/probe_plugin_runtime.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/probe_plugin_runtime.py tests/test_arbor_skill.py --no-cache`: passed.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-f22-cli-smoke --trigger-adapter sidecar-baseline --auth-source-home ~ --runtime-timeout 90 --codex-bin /bin/codex`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f22-full-pycache python3 -m unittest tests/test_arbor_skill.py`: 150 tests passed.

Prior validation from Feature 21 Round 1 bug fix:

- `scripts/probe_plugin_runtime.py` now rejects pre-existing expected Arbor side-effect files before `codex exec`, so fixture files cannot satisfy the runtime side-effect gate.
- Successful exec probing now also requires installed-plugin injection evidence: `skills/arbor/SKILL.md` must be observed under the isolated materialized plugin cache.
- Added regressions for pre-existing project files plus marker-only runtime output, and for marker plus created files without installed-plugin injection evidence.
- `python3 -m unittest tests.test_arbor_skill.PluginRuntimeProbeTests tests.test_arbor_skill.HookTriggerPluginAdapterTests`: 24 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-stage-c-f21-r1-pycache python3 -m py_compile scripts/probe_plugin_runtime.py scripts/plugin_trigger_adapters.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check scripts/probe_plugin_runtime.py scripts/plugin_trigger_adapters.py tests/test_arbor_skill.py --no-cache`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-stage-c-f21-r1-full-pycache python3 -m unittest tests/test_arbor_skill.py`: 146 tests passed.

Prior validation from Feature 21 authenticated runtime probe:

- `scripts/probe_plugin_runtime.py` now copies explicit auth, materializes `arbor@arbor-local` into isolated plugin cache, marks the isolated probe project trusted, closes subprocess stdin, and forwards a configurable `codex exec` sandbox mode.
- `scripts/plugin_trigger_adapters.py` now materializes the local plugin cache before enabling `arbor@arbor-local` for `plugin-runtime-codex-exec`.
- Direct authenticated `codex exec` proved true `$arbor` injection from the isolated plugin cache.
- Remaining runtime blocker: headless `codex exec` blocks project `.codex` writes, so `.codex/memory.md` and `.codex/hooks.json` side-effect gates still do not pass in this runtime.
- `python3 -m unittest tests.test_arbor_skill.PluginRuntimeProbeTests tests.test_arbor_skill.HookTriggerPluginAdapterTests`: 22 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-stage-c-pycache python3 -m py_compile scripts/probe_plugin_runtime.py scripts/plugin_trigger_adapters.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check scripts/probe_plugin_runtime.py scripts/plugin_trigger_adapters.py tests/test_arbor_skill.py --no-cache`: passed.

Prior validation from Stage B Round 4 optimization pass:

- Implemented the P3 baseline-synchronization suggestion: `tests/test_arbor_skill.py` now parses `docs/reviews/stage-b-plugin-runtime-final-review.md` and asserts the documented expected payload baseline exactly matches `scripts/validate_plugin_install.py::EXPECTED_PAYLOAD_FILES`.
- Kept entry-level payload inventory as the release gate for future plugin packaging changes.
- `python3 -m unittest tests.test_arbor_skill.ArborPluginPackagingTests`: 8 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-stage-b-r4-opt-pycache python3 -m py_compile tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check tests/test_arbor_skill.py --no-cache`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-stage-b-r4-opt-install-pycache python3 scripts/validate_plugin_install.py`: passed; payload inventory reports 13 files and `matches_expected_payload=true`.
- `find plugins/arbor -type l -o -path '*/__pycache__/*' -o -name '*.pyc' -o -name '.coverage' -o -name '*.swp' -o -name '*~'`: no output.
- `python3 -m unittest tests/test_arbor_skill.py`: 140 tests passed.

Prior validation from Stage B Round 3 fix:

- Fixed `StageB-R3-001`: `scripts/validate_plugin_install.py` now walks every payload entry, rejects symlinks, rejects unsupported entry types, rejects unexpected directories, and still enforces the exact 13-file payload baseline.
- Added `EXPECTED_PAYLOAD_DIRS`, derived from the expected file baseline, to keep normal package directories explicit.
- Removed the empty non-baseline `plugins/arbor/hooks/` directory from the live plugin tree.
- Added regressions for replacing an expected file with an outside symlink, adding an unexpected symlink directory, and adding an unexpected empty directory.
- Added a live-tree test that fails if any symlink exists under `plugins/arbor`.
- `python3 -m unittest tests.test_arbor_skill.PluginInstallationReadinessTests tests.test_arbor_skill.ArborPluginPackagingTests`: 10 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-stage-b-r3-fix-pycache python3 -m py_compile scripts/validate_plugin_install.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-stage-b-r3-fix-install-pycache python3 scripts/validate_plugin_install.py`: passed; payload inventory reports 13 files and `matches_expected_payload=true`.
- `find plugins/arbor -type l -o -path '*/__pycache__/*' -o -name '*.pyc' -o -name '.coverage' -o -name '*.swp' -o -name '*~'`: no output.
- `python3 -m unittest tests/test_arbor_skill.py`: 139 tests passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-stage-b-r3-fix-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios, 103/103 selected hook executions, outside-root leaks 0, unintended writes 0.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-stage-b-r3-fix-repeat-stub --trigger-adapter plugin-runtime-stub --repeat-runs 2`: passed; 2/2 runs passed, semantic metrics reported runs 0, stability withheld.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-stage-b-r3-fix-runtime-smoke --trigger-adapter plugin-runtime-codex-exec`: passed; runtime returned `network_unavailable` blocker and selected no hooks.

Prior validation from Stage B Round 2 optimization pass:

- Implemented the P3 payload-baseline suggestion: `scripts/validate_plugin_install.py` now enforces an exact 13-file packaged payload allowlist and reports `matches_expected_payload=true`.
- Added regression coverage for an unexpected packaged `skills/arbor/README.md` file.
- Packaged skill and hook smoke subprocesses now execute with a temporary `PYTHONPYCACHEPREFIX` outside `plugins/arbor`.
- Documented the expected packaged payload baseline in `docs/reviews/stage-b-plugin-runtime-final-review.md`.
- `python3 -m unittest tests.test_arbor_skill.ArborPluginPackagingTests tests.test_arbor_skill.PluginInstallationReadinessTests`: 9 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-stage-b-r2-opt-pycache python3 -m py_compile scripts/validate_plugin_install.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-stage-b-r2-opt-install-pycache python3 scripts/validate_plugin_install.py`: passed; payload inventory reports 13 files and `matches_expected_payload=true`.
- `find plugins/arbor -path '*/__pycache__/*' -o -name '*.pyc' -o -name '.coverage' -o -name '*.swp' -o -name '*~'`: no output.
- `python3 -m unittest tests/test_arbor_skill.py`: 138 tests passed.

Prior validation from Stage B review Round 1 fix:

- Fixed `StageB-R1-001`: `scripts/validate_plugin_install.py` now rejects transient release artifacts under `plugins/arbor`, including cache directories, bytecode, coverage files, temporary files, editor swap files, and backup files.
- `python3 scripts/validate_plugin_install.py` now reports payload inventory with `file_count` and packaged file paths.
- Added regression coverage for an injected packaged `__pycache__/*.pyc` artifact and for transient artifacts in the live plugin tree.
- `python3 -m unittest tests.test_arbor_skill.ArborPluginPackagingTests tests.test_arbor_skill.PluginInstallationReadinessTests`: 9 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-stage-b-r1-fix-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py scripts/probe_plugin_runtime.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed.
- `python3 scripts/validate_plugin_install.py`: passed; payload inventory reports 13 packaged files and no transient artifacts.
- `find plugins/arbor -path '*/__pycache__/*' -o -name '*.pyc' -o -name '.coverage' -o -name '*.swp' -o -name '*~'`: no output.
- `python3 -m unittest tests/test_arbor_skill.py`: 138 tests passed.

Prior validation from Stage B final review drafting:

- Added `docs/reviews/stage-b-plugin-runtime-final-review.md` as the progressive review entry for Feature 13-20 closure.
- Stage review summarizes release boundary, data flow, validation commands, online/runtime-only blocker, and final review focus.
- No runtime code changed in this drafting step.
- `python3 -m unittest tests/test_arbor_skill.py`: 137 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-stage-b-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py scripts/probe_plugin_runtime.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed.
- `python3 scripts/validate_plugin_install.py`: passed.
- Standalone and packaged Arbor skill quick validates passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-stage-b-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios, 103/103 hook executions, outside-root leaks 0, unintended writes 0.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-stage-b-repeat-stub --trigger-adapter plugin-runtime-stub --repeat-runs 2`: passed; stability withheld because labels are not real runtime labels.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-stage-b-runtime-smoke --trigger-adapter plugin-runtime-codex-exec`: passed; runtime returned `network_unavailable` blocker and selected no hooks.
- Coverage: total 88%; `scripts/evaluate_hook_triggers.py` 86%.

Prior validation from Feature 20 review Round 2:

- No new findings.
- Closed F20-R1-1: stability signatures now support both full scenario rows and compact default corpus rows.
- Repeated stability adversarial probes: 7/7 passed. The original gate-ready compact repeated-report probe now returns `reported=true` and `stability_rate=1.0`; compact `optional_args` changes are detected as unstable.
- `python3 -m unittest tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 25 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f20-r2-pycache python3 -m py_compile scripts/evaluate_hook_triggers.py tests/test_arbor_skill.py`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f20-r2-repeat-stub --trigger-adapter plugin-runtime-stub --repeat-runs 2`: passed; repeated report emitted, compact rows include `optional_args`, and stability remains withheld because the adapter is not real runtime.
- `python3 -m unittest tests/test_arbor_skill.py`: 137 tests passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f20-r2-full-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py scripts/probe_plugin_runtime.py tests/test_arbor_skill.py`: passed.
- `python3 scripts/validate_plugin_install.py`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f20-r2-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios, 103/103 hook executions, outside-root leaks 0, unintended writes 0; compact rows include `optional_args`.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-f20-r2-runtime-smoke --trigger-adapter plugin-runtime-codex-exec`: passed; runtime returned `decision=ambiguous`, `hooks=[]`, and `reason=Plugin runtime unavailable: network_unavailable...`; semantic metrics remain unreported for the blocked smoke.
- `env COVERAGE_FILE=/private/tmp/arbor-f20-r2-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 137 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f20-r2-coverage conda run -n arbor python -m coverage report`: total coverage 88%; `scripts/evaluate_hook_triggers.py` coverage 86%.

Prior validation from Feature 20 Round 1 fix:

- Fixed F20-R1-1: stability signatures now support both full scenario rows and compact default corpus rows.
- Compact corpus rows now include `optional_args`, making default repeated reports replayable for stability signatures.
- Added a gate-ready compact repeated-report regression and compact output optional-args assertion.
- `python3 -m unittest tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 25 tests passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 137 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f20-r1-fix-full-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py scripts/probe_plugin_runtime.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f20-r1-fix-repeat-stub --trigger-adapter plugin-runtime-stub --repeat-runs 2`: passed; repeated report emitted, compact rows include `optional_args`, and stability remains withheld because the adapter is not real runtime.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f20-r1-fix-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios, 103/103 hook executions, outside-root leaks 0, unintended writes 0.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-f20-r1-fix-runtime-smoke --trigger-adapter plugin-runtime-codex-exec`: passed; runtime returned `network_unavailable` blocker and selected no hooks.
- `python3 scripts/validate_plugin_install.py`: passed.
- Standalone and packaged Arbor skill quick validates passed.
- Coverage: total 88%; `scripts/evaluate_hook_triggers.py` 86%.

Prior validation from Feature 20 review Round 1:

- Added finding F20-R1-1: default compact repeated corpus reports are incompatible with gate-ready stability calculation and raise `KeyError: 'trigger_decision'`.
- `python3 -m unittest tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 24 tests passed.
- Repeated stability adversarial probes: 5/6 passed; the gate-ready compact default-shape probe failed with `KeyError: 'trigger_decision'`.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f20-r1-pycache python3 -m py_compile scripts/evaluate_hook_triggers.py tests/test_arbor_skill.py`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f20-r1-repeat-stub --trigger-adapter plugin-runtime-stub --repeat-runs 2`: passed; repeated report emitted and stability withheld because the adapter is not real runtime.
- `python3 -m unittest tests/test_arbor_skill.py`: 136 tests passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f20-r1-full-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py scripts/probe_plugin_runtime.py tests/test_arbor_skill.py`: passed.
- `python3 scripts/validate_plugin_install.py`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f20-r1-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios, 103/103 hook executions, outside-root leaks 0, unintended writes 0; semantic metrics remain unreported because the adapter is sidecar-backed.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-f20-r1-runtime-smoke --trigger-adapter plugin-runtime-codex-exec`: passed; runtime returned `decision=ambiguous`, `hooks=[]`, and `reason=Plugin runtime unavailable: network_unavailable...`; semantic metrics remain unreported for the blocked smoke.
- `env COVERAGE_FILE=/private/tmp/arbor-f20-r1-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 136 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f20-r1-coverage conda run -n arbor python -m coverage report`: total coverage 88%; `scripts/evaluate_hook_triggers.py` coverage 86%.

Prior validation from Feature 20 developer pass:

- Added repeated full-corpus evaluation under isolated `run-NNN` roots.
- Added stability aggregation for repeated, gate-ready `plugin-runtime-codex-exec` reports.
- Stability remains withheld for sidecar, stub, single-run, and runtime-blocked reports.
- `python3 -m unittest tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 24 tests passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 136 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f20-full-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py scripts/probe_plugin_runtime.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f20-repeat-stub --trigger-adapter plugin-runtime-stub --repeat-runs 2`: passed; repeated report emitted, stability withheld because the adapter is not real runtime.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f20-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios, 103/103 hook executions, outside-root leaks 0, unintended writes 0.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-f20-runtime-smoke --trigger-adapter plugin-runtime-codex-exec`: passed; runtime returned `network_unavailable` blocker and selected no hooks.
- `python3 scripts/validate_plugin_install.py`: passed.
- Standalone and packaged Arbor skill quick validates passed.
- Coverage: total 88%; `scripts/evaluate_hook_triggers.py` 86%.

Prior validation from Feature 19 review Round 3:

- No new findings.
- Replayed developer's Round 2 optimization pass: raw missing-required metric inputs are documented separately from presentation missing-required fields; failed scenario details include raw missing-required fields; multi-hook numerator/denominator fields are emitted; stability remains unreported until repeated real runtime corpus runs exist.
- Optimization replay probes: 4/4 passed.
- `python3 -m unittest tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 19 tests passed.
- `python3 -m unittest tests.test_arbor_skill.ArborPluginPackagingTests tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 24 tests passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 131 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f19-r3-pycache python3 -m py_compile scripts/evaluate_hook_triggers.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f19-r3-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios, 103/103 hook executions, outside-root leaks 0, unintended writes 0; semantic metrics remain unreported because the adapter is sidecar-backed.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-f19-r3-runtime-smoke --trigger-adapter plugin-runtime-codex-exec`: passed; runtime returned `decision=ambiguous`, `hooks=[]`, and `reason=Plugin runtime unavailable: network_unavailable...`; semantic metrics remain unreported for the blocked smoke.
- `python3 scripts/validate_plugin_install.py`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f19-r3-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 131 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f19-r3-coverage conda run -n arbor python -m coverage report`: total coverage 88%; `scripts/evaluate_hook_triggers.py` coverage 87%.

Prior validation from Feature 19 Round 2 optimization pass:

- Addressed accepted optimization suggestions: raw missing-required metric inputs are documented separately from presentation missing-required fields; multi-hook numerator/denominator fields are emitted; stability remains unreported until repeated real runtime corpus runs exist.
- `python3 -m unittest tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 19 tests passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 131 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f19-r2-opt-pycache python3 -m py_compile scripts/evaluate_hook_triggers.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f19-r2-opt-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios, 103/103 hook executions, outside-root leaks 0, unintended writes 0; semantic metrics remain unreported because the adapter is sidecar-backed.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-f19-r2-opt-runtime-smoke --trigger-adapter plugin-runtime-codex-exec`: passed; runtime returned `decision=ambiguous`, `hooks=[]`, and `reason=Plugin runtime unavailable: network_unavailable...`; semantic metrics remain unreported for the blocked smoke.
- `python3 scripts/validate_plugin_install.py`: passed.
- Standalone and packaged Arbor skill quick validates passed.
- Coverage: total 88%; `scripts/evaluate_hook_triggers.py` 87%.

Prior validation from Feature 19 review Round 2:

- Accepted Feature 19 after re-review; no new findings.
- Closed F19-R1-1: `multi_hook_exact_required_rate` now uses raw required-hook presence instead of the ambiguous-acceptance-adjusted missing-required field.
- Formula adversarial probes: 4/4 passed. The original synthetic `M-P001` with `decision=ambiguous`, `hooks=[]` now reports `multi_hook_required_recall=0.0`, `multi_hook_exact_required_rate=0.0`, `raw_missing_required_hooks=["arbor.session_startup_context"]`, and `missing_required_hooks=[]`.
- `python3 -m unittest tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 19 tests passed.
- `python3 -m unittest tests.test_arbor_skill.ArborPluginPackagingTests tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 24 tests passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 131 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f19-r2-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py scripts/probe_plugin_runtime.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f19-r2-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios, 103/103 hook executions, outside-root leaks 0, unintended writes 0; semantic metrics remain unreported because the adapter is sidecar-backed.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-f19-r2-runtime-smoke --trigger-adapter plugin-runtime-codex-exec`: passed; runtime returned `decision=ambiguous`, `hooks=[]`, and `reason=Plugin runtime unavailable: network_unavailable...`; semantic metrics remain unreported for the blocked smoke.
- `python3 scripts/validate_plugin_install.py`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f19-r2-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 131 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f19-r2-coverage conda run -n arbor python -m coverage report`: total coverage 88%; `scripts/evaluate_hook_triggers.py` coverage 87%.

Latest validation from Feature 19 review Round 1:

- Added finding F19-R1-1: `multi_hook_exact_required_rate` counts an allowed ambiguous abstention on a required multi-hook scenario as an exact required-hook match.
- `python3 -m unittest tests.test_arbor_skill.ArborPluginPackagingTests tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 23 tests passed.
- Formula adversarial probes: 2/3 passed; the ambiguous `M-P001` abstention probe reported `multi_hook_required_recall=0.0` but `multi_hook_exact_required_rate=1.0`.
- `python3 -m unittest tests/test_arbor_skill.py`: 130 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f19-r1-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py scripts/probe_plugin_runtime.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f19-r1-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios, 103/103 hook executions, outside-root leaks 0, unintended writes 0; semantic metrics remain unreported because the adapter is sidecar-backed.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-f19-r1-runtime-smoke --trigger-adapter plugin-runtime-codex-exec`: passed; runtime returned `decision=ambiguous`, `hooks=[]`, and `reason=Plugin runtime unavailable: network_unavailable...`; semantic metrics remain unreported for the blocked smoke.
- `python3 scripts/validate_plugin_install.py`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f19-r1-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 130 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f19-r1-coverage conda run -n arbor python -m coverage report`: total coverage 87%; `scripts/evaluate_hook_triggers.py` coverage 86%.

Latest validation from Feature 19 developer pass:

- Added semantic metric formulas behind the Feature 18 gates.
- Metrics include per-hook precision/recall, `NONE` false-positive rate, near-miss false-positive rate, ambiguous acceptance, multi-hook required recall/exact-required rate, failed scenario details, and an unreported stability placeholder.
- Sidecar and stub paths remain metric-ineligible; runtime blocker reports remain unscored.
- Release boundary is explicit: evaluation harness, scenario corpus, and review docs are not plugin payload.
- `python3 -m unittest tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 18 tests passed.
- `python3 -m unittest tests.test_arbor_skill.ArborPluginPackagingTests tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 23 tests passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 130 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f19-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py scripts/probe_plugin_runtime.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f19-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios, 103/103 hook executions, outside-root leaks 0, unintended writes 0.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-f19-runtime-smoke --trigger-adapter plugin-runtime-codex-exec`: passed; runtime returned `decision=ambiguous`, `hooks=[]`, and `reason=Plugin runtime unavailable: network_unavailable...`; no hooks executed.
- `python3 scripts/validate_plugin_install.py`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f19-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 130 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f19-coverage conda run -n arbor python -m coverage report`: total coverage 87%; `scripts/evaluate_hook_triggers.py` coverage 86%.

Latest validation from Feature 18 review Round 1:

- No new findings.
- Gate replay: sidecar and stub adapters remain ineligible; runtime blockers, hook execution failures, and empty runtime results block readiness; clean synthetic plugin runtime results set `ready_for_semantic_metrics=true` while `reported=false`.
- `python3 -m unittest tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 17 tests passed.
- Manual semantic gate probes: 6/6 passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 128 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f18-r1-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py scripts/probe_plugin_runtime.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f18-r1-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios, 103/103 hook executions, outside-root leaks 0, unintended writes 0; adapter gate ineligible, runtime gate not applicable, hook execution gate clean.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-f18-r1-runtime-smoke --trigger-adapter plugin-runtime-codex-exec`: passed; runtime returned `decision=ambiguous`, `hooks=[]`, and `reason=Plugin runtime unavailable: network_unavailable...`; no hooks executed.
- `python3 scripts/validate_plugin_install.py`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f18-r1-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 128 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f18-r1-coverage conda run -n arbor python -m coverage report`: total coverage 87%; `scripts/evaluate_hook_triggers.py` coverage 83%.
- Feature 18 accepted after review.

Latest validation from Feature 18 developer pass:

- Added `semantic_metrics.ready_for_semantic_metrics` plus adapter eligibility, runtime availability, and hook execution gates to full-corpus reports.
- Runtime blocker decisions such as `Plugin runtime unavailable: network_unavailable...` now block semantic scoring readiness and are counted separately from semantic `NONE`.
- `python3 -m unittest tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 17 tests passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 128 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f18-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py scripts/probe_plugin_runtime.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f18-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios, 103/103 hook executions, outside-root leaks 0, unintended writes 0.
- `python3 scripts/validate_plugin_install.py`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f18-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 128 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f18-coverage conda run -n arbor python -m coverage report`: total coverage 87%; `scripts/evaluate_hook_triggers.py` coverage 83%.

Latest validation from Feature 17 review Round 2:

- No new findings.
- Round 1 finding replay: mocked runtime mutations to `AGENTS.md`, `.codex/memory.md`, and `.codex/hooks.json` now return `project_file_mutation:<paths>` blockers and restore original protected file state.
- `python3 -m unittest tests.test_arbor_skill.HookTriggerPluginAdapterTests tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 25 tests passed.
- Incremental adversarial probes for protected hook deletion, protected memory recreation, and nonzero runtime exit plus mutation: 3/3 passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 125 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f17-r2-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py scripts/probe_plugin_runtime.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed.
- `python3 scripts/validate_plugin_install.py`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-f17-r2-runtime-smoke --trigger-adapter plugin-runtime-codex-exec`: passed; runtime returned `decision=ambiguous`, `hooks=[]`, and `reason=Plugin runtime unavailable: network_unavailable...`; no hooks executed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f17-r2-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios, 103/103 hook executions, outside-root leaks 0, unintended writes 0.
- `env COVERAGE_FILE=/private/tmp/arbor-f17-r2-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 125 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f17-r2-coverage conda run -n arbor python -m coverage report`: total coverage 87%; `scripts/plugin_trigger_adapters.py` coverage 81%.
- Feature 17 accepted after re-review.

Latest validation from Feature 17 Round 1 fix:

- Fixed F17-R1-1: `run_codex_exec_trigger` now snapshots `AGENTS.md`, `.codex/memory.md`, and `.codex/hooks.json` before `codex exec`, restores them if the runtime mutates protected project paths, and returns an ambiguous blocker reason containing `project_file_mutation:<paths>`.
- Added focused regression coverage for a mocked runtime that mutates `AGENTS.md` while returning schema-valid trigger JSON.
- Added focused regression coverage for a mocked runtime that replaces `.codex/memory.md` with a directory while returning schema-valid trigger JSON.
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

Latest validation from Feature 17 Round 1 review:

- Added finding F17-R1-1: `run_codex_exec_trigger` accepts schema-valid runtime decisions without detecting trigger-adapter mutations to project files such as `AGENTS.md`.
- `python3 -m unittest tests.test_arbor_skill.HookTriggerPluginAdapterTests tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 23 tests passed.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-f17-r1-runtime-smoke --trigger-adapter plugin-runtime-codex-exec`: passed; runtime returned `decision=ambiguous`, `hooks=[]`, and `reason=Plugin runtime unavailable: network_unavailable...`; no hooks executed.
- Adversarial mocked runtime mutation probe: failed the side-effect boundary; mocked `codex exec` changed `AGENTS.md` while writing valid trigger JSON, and the adapter accepted the decision.
- `python3 -m unittest tests/test_arbor_skill.py`: 123 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f17-r1-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py scripts/probe_plugin_runtime.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed.
- `python3 scripts/validate_plugin_install.py`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f17-r1-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios, 103/103 hook executions, outside-root leaks 0, unintended writes 0.
- `env COVERAGE_FILE=/private/tmp/arbor-f17-r1-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 123 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f17-r1-coverage conda run -n arbor python -m coverage report`: total coverage 87%; `scripts/plugin_trigger_adapters.py` coverage 80%.

Latest validation from Feature 17 developer pass:

- Added `plugin-runtime-codex-exec` adapter for isolated installed-plugin Codex exec trigger decisions.
- `python3 -m unittest tests.test_arbor_skill.HookTriggerPluginAdapterTests tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 23 tests passed.
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

Latest validation from Feature 16 review Round 2:

- No new findings.
- Round 1 finding replay: empty hooks, malformed hooks JSON, non-list hooks, wrong owner, and incomplete Arbor hook sets are now rejected; all three `owner=arbor` hook ids are required for a passing exec probe.
- `python3 -m unittest tests.test_arbor_skill.PluginRuntimeProbeTests`: 7 tests passed.
- `python3 scripts/probe_plugin_runtime.py`: passed; isolated marketplace add and `arbor@arbor-local` enable succeeded; exec skipped by default.
- `python3 scripts/probe_plugin_runtime.py --attempt-exec --timeout 45`: completed with `exec_probe.status=blocked` and `reason=network_unavailable`; marketplace add and plugin enable still succeeded.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f16-r2-pycache python3 -m py_compile scripts/probe_plugin_runtime.py tests/test_arbor_skill.py`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f16-r2-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py scripts/probe_plugin_runtime.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed.
- `python3 scripts/validate_plugin_install.py`: passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 120 tests passed.
- `COVERAGE_FILE=/private/tmp/arbor-f16-r2-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 120 tests passed; total coverage 87%; `scripts/probe_plugin_runtime.py` coverage 67%.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f16-r2-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios passed, 103/103 selected hook executions passed, outside-root leaks 0, unintended writes 0, semantic metrics not reported.
- Independent isolation probe confirmed `run_plugin_runtime_probe(..., attempt_exec=False)` used a temporary `HOME` and did not change the real `~/.codex/config.toml` hash.
- Feature 16 accepted after re-review.

Prior validation from Feature 16 Round 1 fix:

- Fixed Round 1 finding: `scripts/probe_plugin_runtime.py` could report `exec_probe.status=passed` when `.codex/hooks.json` existed but contained no Arbor hook registrations.
- `run_exec_probe` now parses `.codex/hooks.json` and requires all three `owner=arbor` hook ids before returning `status="passed"`.
- `python3 -m unittest tests.test_arbor_skill.PluginRuntimeProbeTests`: 7 tests passed.
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

Latest validation from Feature 16 review Round 1:

- Review finding added: `scripts/probe_plugin_runtime.py` can report `exec_probe.status=passed` when `.codex/hooks.json` exists but contains no Arbor hook registrations.
- `python3 -m unittest tests.test_arbor_skill.PluginRuntimeProbeTests`: 6 tests passed.
- `python3 scripts/probe_plugin_runtime.py`: passed; isolated marketplace add and `arbor@arbor-local` enable succeeded; exec skipped by default.
- `python3 scripts/probe_plugin_runtime.py --attempt-exec --timeout 45`: completed with `exec_probe.status=blocked` and `reason=network_unavailable`; marketplace add and plugin enable still succeeded.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f16-r1-pycache python3 -m py_compile scripts/probe_plugin_runtime.py tests/test_arbor_skill.py`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f16-r1-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py scripts/probe_plugin_runtime.py tests/test_arbor_skill.py`: passed.
- `conda run -n arbor python -m ruff check . --no-cache`: passed.
- `python3 scripts/validate_plugin_install.py`: passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 119 tests passed.
- `COVERAGE_FILE=/private/tmp/arbor-f16-r1-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 119 tests passed; total coverage 87%; `scripts/probe_plugin_runtime.py` coverage 67%.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f16-r1-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios passed, 103/103 selected hook executions passed, outside-root leaks 0, unintended writes 0, semantic metrics not reported.
- Independent isolation probe confirmed `run_plugin_runtime_probe(..., attempt_exec=False)` used a temporary `HOME` and did not change the real `~/.codex/config.toml` hash.
- Adversarial exec side-effect probe: mocked successful exec with marker and empty `{"hooks":[]}` returned `status=passed`, so hook registration verification is incomplete.

Prior validation from Feature 16 developer pass:

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

Latest validation from Feature 15 review Round 3:

- No new findings.
- Round 2 finding replay: duplicate hook row, non-object hook row, duplicate hook id with same count, missing hook id, and wrong hook id mutations were all rejected.
- `python3 -m unittest tests.test_arbor_skill.PluginInstallationReadinessTests`: 3 tests passed.
- `python3 scripts/validate_plugin_install.py`: passed.
- `python3 scripts/validate_plugin_install.py --codex-probe`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f15-r3-pycache python3 -m py_compile scripts/validate_plugin_install.py tests/test_arbor_skill.py`: passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 113 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f15-r3-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py tests/test_arbor_skill.py`: passed.
- `COVERAGE_FILE=/private/tmp/arbor-f15-r3-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 113 tests passed; total coverage 87%; `scripts/validate_plugin_install.py` coverage 66%.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f15-r3-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios passed, 103/103 selected hook executions passed, outside-root leaks 0, unintended writes 0, semantic metrics not reported.
- Independent isolation probe confirmed `run_codex_marketplace_install_probe` used a temporary `HOME` and did not change the real `~/.codex/config.toml` hash.
- Feature 15 accepted after re-review.

Prior validation from Feature 15 review Round 2 fix:

- `python3 -m unittest tests.test_arbor_skill.PluginInstallationReadinessTests`: 3 tests passed.
- `python3 scripts/validate_plugin_install.py`: passed.
- `python3 scripts/validate_plugin_install.py --codex-probe`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f15-r2-pycache python3 -m py_compile scripts/validate_plugin_install.py tests/test_arbor_skill.py`: passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 113 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f15-r2-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py tests/test_arbor_skill.py`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f15-r2-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios passed, 103/103 selected hook executions passed, outside-root leaks 0, unintended writes 0, semantic metrics not reported.

Prior validation from Feature 15 review Round 2:

- Review finding added: `scripts/validate_plugin_install.py` accepts malformed hook lists with duplicate hook rows or non-object hook rows because it validates only the set of dict hook ids.
- Round 1 finding replay: `../../hooks.json` hook script path traversal is now rejected with `hook script escapes packaged skill root`.
- Additional path containment probes: absolute outside `.py`, symlink outside `.py`, and non-Python script targets are rejected.
- Hook list exactness probes: duplicate hook row and non-object hook row were incorrectly accepted.
- `python3 -m unittest tests.test_arbor_skill.PluginInstallationReadinessTests`: 3 tests passed.
- `python3 scripts/validate_plugin_install.py`: passed.
- `python3 scripts/validate_plugin_install.py --codex-probe`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f15-r2-pycache python3 -m py_compile scripts/validate_plugin_install.py tests/test_arbor_skill.py`: passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 113 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f15-r2-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py tests/test_arbor_skill.py`: passed.
- `COVERAGE_FILE=/private/tmp/arbor-f15-r2-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 113 tests passed; total coverage 87%; `scripts/validate_plugin_install.py` coverage 64%.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f15-r2-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios passed, 103/103 selected hook executions passed, outside-root leaks 0, unintended writes 0, semantic metrics not reported.

Prior validation from Feature 15 review Round 1 fix:

- `python3 -m unittest tests.test_arbor_skill.PluginInstallationReadinessTests`: 3 tests passed.
- `python3 scripts/validate_plugin_install.py`: passed.
- `python3 scripts/validate_plugin_install.py --codex-probe`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f15-fix-pycache python3 -m py_compile scripts/validate_plugin_install.py tests/test_arbor_skill.py`: passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 113 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f15-fix-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py tests/test_arbor_skill.py`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f15-fix-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios passed, 103/103 selected hook executions passed, outside-root leaks 0, unintended writes 0, semantic metrics not reported.

Prior validation from Feature 15 review Round 1:

- Review finding added: `scripts/validate_plugin_install.py` accepts hook entrypoint script paths that resolve outside the packaged skill, for example `../../hooks.json`.
- `python3 scripts/validate_plugin_install.py`: passed.
- `python3 scripts/validate_plugin_install.py --codex-probe`: passed; isolated temp `HOME` was used and the real Codex config hash was unchanged in an independent probe.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f15-review-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py tests/test_arbor_skill.py`: passed.
- `python3 -m unittest tests.test_arbor_skill.PluginInstallationReadinessTests`: 2 tests passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 112 tests passed.
- `COVERAGE_FILE=/private/tmp/arbor-f15-review-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 112 tests passed; total coverage 87%; `scripts/validate_plugin_install.py` coverage 61%.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f15-review-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios passed, 103/103 selected hook executions passed, outside-root leaks 0, unintended writes 0, semantic metrics not reported.
- Adversarial temp-copy mutations: 5/6 rejected; the hook script path escape mutation was incorrectly accepted.

Prior validation from Feature 15 developer pass:

- `python3 scripts/validate_plugin_install.py`: passed; validated marketplace, manifest, packaged hook entrypoints, packaged initialization, and packaged Hook 1/2/3 smoke behavior.
- `python3 scripts/validate_plugin_install.py --codex-probe`: passed; isolated `codex plugin marketplace add /Users/shawn/Desktop/arbor` added marketplace `arbor-local` using a temporary `HOME`.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f15-pycache python3 -m py_compile scripts/validate_plugin_install.py`: passed.
- `python3 -m unittest tests.test_arbor_skill.PluginInstallationReadinessTests`: 2 tests passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 112 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f15-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py tests/test_arbor_skill.py`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f15-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios passed, 103/103 selected hook executions passed, outside-root leaks 0, unintended writes 0, semantic metrics not reported.

Prior validation from Feature 14 developer pass:

- `python3 -m unittest tests.test_arbor_skill.HookTriggerPluginAdapterTests tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 20 tests passed.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-f14-plugin-stub-smoke --trigger-adapter plugin-runtime-stub`: passed and emitted an abstaining plugin-runtime trigger decision with no hook execution.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-f14-sidecar-smoke --trigger-adapter sidecar-baseline`: passed and executed registered Hook 1.
- `python3 -m unittest tests/test_arbor_skill.py`: 110 tests passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f14-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py tests/test_arbor_skill.py`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f14-corpus-sidecar --trigger-adapter sidecar-baseline`: passed; 150/150 scenarios passed, 103/103 selected hook executions passed, outside-root leaks 0, unintended writes 0, semantic metrics not reported.

Prior validation from Feature 13 developer pass:

- Documentation-only design update; no runtime code changed.
- `python3 -m unittest tests/test_arbor_skill.py`: 102 tests passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.

Prior validation from final current-scope closure:

- `python3 -m unittest tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 12 tests passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 102 tests passed.
- `python3 -m json.tool docs/reviews/hook-trigger-scenarios.json`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-final-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/evaluate_hook_triggers.py tests/test_arbor_skill.py`: passed.
- `python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-final-corpus`: passed; 150/150 scenarios passed, 103/103 selected hook executions passed, outside-root leaks 0, unintended writes 0, semantic metrics not reported.
- `env COVERAGE_FILE=/private/tmp/arbor-final-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 102 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-final-coverage conda run -n arbor python -m coverage report`: total coverage 89%; `scripts/evaluate_hook_triggers.py` coverage 83%.

Prior validation from Feature 11 Round 1 review:

- `python3 -m unittest tests.test_arbor_skill.HookTriggerExecutionHarnessTests`: 9 tests passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 99 tests passed.
- `python3 -m json.tool docs/reviews/hook-trigger-scenarios.json`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f11-r1-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/evaluate_hook_triggers.py tests/test_arbor_skill.py`: passed.
- `python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-f11-smoke-r1`: passed and emitted scenario execution JSON.
- `env COVERAGE_FILE=/private/tmp/arbor-f11-r1-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 99 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f11-r1-coverage conda run -n arbor python -m coverage report`: total coverage 89%; `scripts/evaluate_hook_triggers.py` coverage 81%.
- Feature 11 Round 1 adversarial probes: 55/55 passed.
- Feature 11 accepted for registered-hook execution and packet/side-effect assertions; real semantic trigger metrics remain pending until observed labels come from a real plugin trigger path.

Prior validation from Feature 10 Round 1 review:

- `python3 -m unittest tests.test_arbor_skill.HookTriggerSimulatedDispatcherTests`: 15 tests passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 90 tests passed.
- `python3 -m json.tool docs/reviews/hook-trigger-scenarios.json`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f10-r1-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py tests/test_arbor_skill.py`: passed.
- `python3 scripts/simulated_dispatcher.py --scenario-id H1-P001`: passed and emitted dispatcher-contract JSON.
- `env COVERAGE_FILE=/private/tmp/arbor-f10-r1-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 90 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f10-r1-coverage conda run -n arbor python -m coverage report`: total coverage 89%; `scripts/simulated_dispatcher.py` coverage 77%.
- Feature 10 Round 1 adversarial probes: 39/39 passed.
- Feature 10 accepted for sidecar-backed dispatcher-contract output; registered-hook execution, side-effect assertions, and non-circular semantic metrics remain pending in later Stage B increments.

Prior validation from Feature 9 Round 1 review:

- `python3 -m unittest tests.test_arbor_skill.HookTriggerFixtureBuilderTests`: 11 tests passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 75 tests passed.
- `python3 -m json.tool docs/reviews/hook-trigger-scenarios.json`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f9-r1-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py tests/test_arbor_skill.py`: passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f9-r1-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 75 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f9-r1-coverage conda run -n arbor python -m coverage report`: total coverage 89%; `scripts/eval_fixtures.py` coverage 90%.
- Feature 9 Round 1 adversarial probes: 104/104 passed.
- Feature 9 accepted for deterministic Stage B fixture generation; dispatcher decisions, hook execution assertions, and metrics remain pending in later Stage B increments.

Prior validation from Feature 8 Round 2 review:

- `python3 -m unittest tests.test_arbor_skill.HookTriggerSidecarTests`: 5 tests passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 64 tests passed.
- `python3 -m json.tool docs/reviews/hook-trigger-scenarios.json`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f8-r2-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py tests/test_arbor_skill.py`: passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f8-r2-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 64 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f8-r2-coverage conda run -n arbor python -m coverage report`: total coverage 88%.
- Feature 8 Round 2 adversarial probes: 33/33 passed.
- Feature 8 Round 1 finding closed: `M-P014` and `M-P015` are now `MULTI`, single-label invariants pass, and sidecar field semantics are documented.
- Feature 7 remains accepted for repo-local plugin payload distribution: 25/25 adversarial probes passed.
- Historical Feature 6 validation remains accepted: 28/28 adversarial probes passed.
- Feature-level hook trigger scenario corpus created with broad positive, negative, near-miss, ambiguous, cross-language, and runtime-event cases.
- Feature-level trigger plan Round 0 feedback addressed: static review and dispatch-harness metrics are now staged separately; structured scenario sidecar is a future harness prerequisite; `M-P011` was relabeled to `NONE`.
- Feature-level trigger plan Round 1 accepted Stage A with 7/7 checks passed and 0 new findings. Stage B still requires a structured sidecar and runnable dispatch harness before reporting semantic metrics.
- GPT-5.5 prompt guidance alignment added: Arbor skill instructions should stay outcome-first and concise, while large scenario/eval artifacts stay in docs or future plugin harnesses.
- Feature 25 implemented full authenticated real-runtime corpus execution and honest semantic failure reporting. Review file: `docs/reviews/features/feature-25-real-runtime-full-corpus.md`.
- Feature 25 initial validation found a clean execution chain but not full semantic closure: 150/150 execution scenarios passed, 108/108 hook executions passed, adapter/runtime/hook gates passed, and semantic metrics reported 146/150 passed.
- Feature 25 fixed two evaluation bugs found during full-corpus replay: H1/H2 bare single-value optional args no longer fail adapter validation, and semantic failed scenarios now make corpus reports fail with a non-zero CLI exit.
- Feature 25 Round 1 fixed the four known semantic misses in focused authenticated replay: `CL-P020`, `EV-P010`, `H1-P013`, and `H3-P017` now pass with persisted report/progress artifacts.
- Feature 25 evidence retention improved: `evaluate_hook_triggers.py` supports `--report-json`, and latest focused artifacts live under `docs/reviews/artifacts/`.
- Feature 25 Round 2 closed the retained full-corpus evidence gap: `docs/reviews/artifacts/feature-25-full-corpus-r4-report.json` reports 150/150 scenarios passed, 111/111 selected hook executions passed, 0 runtime blockers, 0 outside-root leaks, and semantic metrics passed.

## Open Questions

- Long-term packaging source of truth: keep the mirrored standalone skill and plugin copy, or migrate to a plugin-first layout.
- Whether installed plugin hook integration needs a separate adapter after repo-local packaging.
- Preferred optional git log presets to expose without constraining agent choice.
- Stage B dispatch evaluation artifacts: structured scenario sidecar, fixture builders, simulated dispatcher adapter, registered-hook execution harness, and metric report.
- Repeated real-runtime stability: run repeated full-corpus authenticated passes if stability metrics are needed; the current accepted full-corpus artifact intentionally reports stability as unavailable from a single pass.
