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

Status: complete for current scope. The standalone Arbor skill, repo-local plugin package, project-level hooks, and sidecar-backed Stage B hook execution harness are accepted.

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

Current next feature:

- Optional next phase: replace the sidecar-backed simulated dispatcher with a real plugin/runtime dispatcher and measure semantic trigger quality.

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
| Feature-level hook trigger review | Review whether the complete Arbor flow has clear semantic activation boundaries across positive, negative, cross-language, and ambiguous hook scenarios. | Stage A accepted; sidecar-backed Stage B hook execution report accepted; real semantic dispatcher pending future phase | `docs/reviews/features/feature-level-hook-trigger-review.md` plus `docs/reviews/hook-trigger-scenarios.md` |
| Feature 7: Arbor plugin packaging | Package the accepted standalone Arbor skill and hook contract into a repo-local Codex plugin without adding semantic dispatch. | Accepted after review | `docs/reviews/features/feature-7-plugin-packaging.md` |
| Feature 8: trigger scenario sidecar | Convert the human-readable hook trigger corpus into machine-checkable structured expectations for future plugin-based dispatch evaluation. | Accepted after re-review | `docs/reviews/features/feature-8-trigger-sidecar.md` |
| Feature 9: dispatch eval fixture builders | Generate deterministic temporary project fixtures and summaries for Stage B dispatch evaluation without implementing dispatcher decisions or metrics. | Accepted after review | `docs/reviews/features/feature-9-fixture-builders.md` |
| Feature 10: simulated dispatcher adapter | Emit dispatcher-contract JSON from sidecar expectations so the next harness increment can test dispatch plumbing before real semantic dispatch. | Accepted after review | `docs/reviews/features/feature-10-simulated-dispatcher.md` |
| Feature 11: registered hook execution harness | Execute selected hooks through fixture-local `.codex/hooks.json` entrypoints and assert packet shape, outside-root rejection, and no unintended memory writes. | Accepted after review | `docs/reviews/features/feature-11-hook-execution-harness.md` |
| Feature 12: full-corpus hook execution report | Run all 150 scenarios through the sidecar-backed Stage B harness and report hook execution-chain quality without semantic trigger metrics. | Accepted in final closure | `docs/reviews/features/feature-12-full-corpus-report.md` |

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
- Git repository: yes, on `master` with no commits yet.
- Current untracked project files: `.codex/`, `.gitignore`, `AGENTS.md`, `docs/`, `plugins/`, `scripts/`, `skills/`, and `tests/`.

## Validation Summary

Latest validation from final current-scope closure:

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
- Feature 11 accepted for registered-hook execution and packet/side-effect assertions; real semantic trigger metrics remain pending until observed labels come from a real dispatcher.

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

## Open Questions

- Long-term packaging source of truth: keep the mirrored standalone skill and plugin copy, or migrate to a plugin-first layout.
- Whether installed plugin hook integration needs a separate adapter after repo-local packaging.
- Preferred optional git log presets to expose without constraining agent choice.
- Stage B dispatch evaluation artifacts: structured scenario sidecar, fixture builders, simulated dispatcher adapter, registered-hook execution harness, and metric report.
