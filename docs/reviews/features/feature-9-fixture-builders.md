# Feature 9 Review: Dispatch Eval Fixture Builders

## Purpose

Build deterministic project-state fixtures for Stage B hook trigger dispatch evaluation.

## Scope

In scope:

- Add `scripts/eval_fixtures.py`.
- Generate temporary project roots for the planned Stage B fixtures.
- Register project-local Arbor hooks inside generated fixtures.
- Emit machine-readable JSON summaries for future dispatcher and hook-execution harness inputs.
- Add focused tests for fixture vocabulary, generated state, outside-root paths, and CLI behavior.

Out of scope:

- Simulated dispatcher implementation.
- Real plugin dispatcher integration.
- Registered-hook execution harness.
- Semantic precision, recall, false-positive, or stability metrics.
- Any dependency on this repository's current git status.

## Design Notes

The fixture builder is intentionally small and deterministic. It builds a single named fixture under a caller-provided empty directory and returns a summary with fields the future dispatch harness can consume:

- fixture name and project root;
- git repository presence and raw `git status --short` lines;
- `AGENTS.md`, `.codex/memory.md`, and `.codex/hooks.json` presence;
- available project docs;
- memory and AGENTS state labels;
- outside-root path only for rejection scenarios.

Fixture generation initializes project-local Arbor files and hooks through the same skill scripts used by the existing feature tests. This keeps Stage B fixture setup aligned with the accepted project-level hook registration flow.

## Implementation Notes

- Added `scripts/eval_fixtures.py`.
- Added `HookTriggerFixtureBuilderTests` to `tests/test_arbor_skill.py`.
- Updated `docs/arbor-skill-design.md` with Feature 9 scope and Stage B progress.
- Updated `AGENTS.md` project map with the new eval fixture script.

Supported fixtures:

- `clean_git_project`
- `non_git_project`
- `missing_agents`
- `missing_memory`
- `uncommitted_changes`
- `stale_memory`
- `durable_drift_docs`
- `outside_root_path`

## Validation

- `python3 -m unittest tests.test_arbor_skill.HookTriggerFixtureBuilderTests`: 11 tests passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 75 tests passed.
- `python3 -m json.tool docs/reviews/hook-trigger-scenarios.json`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f9-full-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py tests/test_arbor_skill.py`: passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f9-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 75 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f9-coverage conda run -n arbor python -m coverage report`: total coverage 89%.

## Developer Response

Feature 9 is implemented and targeted-tested. It supplies deterministic fixture state for the next Stage B increment while keeping dispatcher decisions, hook execution assertions, and metrics out of scope.

## Adversarial Review Rounds

### Round 1: Fixture Builder Replay

#### Round Result Tab

| Round | Scope | Verdict | Problems | Probe pass rate | Convergence |
| --- | --- | --- | ---: | ---: | --- |
| F9-R1 | Developer validation playback plus sidecar vocabulary alignment, generated summary shape, hook contract registration, raw git status preservation, fixture-specific state, deterministic payloads, and CLI behavior | Accepted | 0 | 104/104, 100% | Converged for Feature 9 fixture-builder scope |

#### Problems Found

| ID | Severity | Area | Finding | Evidence | Impact | Next-round acceptance gate |
| --- | --- | --- | --- | --- | --- | --- |
| F9-R1-NF1 | None | Fixture builders | No new review finding. | Developer baseline checks passed; independent adversarial probes passed 104/104. | Feature 9 can be treated as accepted for deterministic fixture generation. | No additional Feature 9 gate. Continue to simulated dispatcher adapter and registered-hook execution harness work. |

#### Test Coverage Table

| Test category | Cases/checks run | Category coverage | Passed | Failed | Pass rate | Result summary |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Developer baseline playback | 8 checks | 8/8 planned checks, 100% | 8 | 0 | 100% | Replayed targeted fixture tests, full unit suite, sidecar JSON parsing, standalone and packaged skill validation, py_compile, coverage run, and coverage report. |
| Fixture vocabulary | 4 probes | 4/4 planned probes, 100% | 4 | 0 | 100% | Available fixtures cover sidecar references, include only the planned extra `non_git_project`, have registered builders, and preserve declared order. |
| Summary shape | 24 probes | 24/24 planned probes, 100% | 24 | 0 | 100% | Every fixture summary has the required fields, matching project root, and nonempty notes. |
| Hook contract | 40 probes | 40/40 planned probes, 100% | 40 | 0 | 100% | Every fixture has `.codex/hooks.json`, Arbor hook ids match packaged plugin hooks, and all hook entrypoint scripts exist. |
| Git state | 16 probes | 16/16 planned probes, 100% | 16 | 0 | 100% | Git fixtures preserve raw `git status --short` lines; the non-git fixture has no `.git` directory and reports `git_status_short: null`. |
| Fixture semantics | 9 probes | 9/9 planned probes, 100% | 9 | 0 | 100% | Clean, non-git, missing setup, uncommitted, stale memory, durable drift docs, and outside-root fixtures expose the expected state. |
| Determinism | 8 probes | 8/8 planned probes, 100% | 8 | 0 | 100% | Rebuilding every fixture under a separate temp base produced identical non-git file payload digests. |
| CLI behavior | 3 probes | 3/3 planned probes, 100% | 3 | 0 | 100% | CLI builds JSON summaries and rejects nonempty roots without traceback. |
| Total adversarial probes | 104 probes | 104/104 planned probes, 100% | 104 | 0 | 100% | Excludes baseline playback checks. |

#### Baseline Playback Table

| Command/check | Status | Notes |
| --- | --- | --- |
| `python3 -m unittest tests.test_arbor_skill.HookTriggerFixtureBuilderTests` | Pass | 11 tests passed. |
| `python3 -m unittest tests/test_arbor_skill.py` | Pass | 75 tests passed. |
| `python3 -m json.tool docs/reviews/hook-trigger-scenarios.json` | Pass | Sidecar JSON parsed successfully. |
| `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor` | Pass | Standalone skill validation passed. |
| `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor` | Pass | Packaged skill validation passed. |
| `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f9-r1-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py tests/test_arbor_skill.py` | Pass | No compile errors. |
| `env COVERAGE_FILE=/private/tmp/arbor-f9-r1-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py` | Pass | 75 tests passed under coverage. |
| `env COVERAGE_FILE=/private/tmp/arbor-f9-r1-coverage conda run -n arbor python -m coverage report` | Pass | Total coverage 89%; `scripts/eval_fixtures.py` coverage 90%. |

#### Scenario Test Matrix

| Scenario ID | Scenario | Category | Expected behavior | Observed result | Status |
| --- | --- | --- | --- | --- | --- |
| F9-R1-S1 | Sidecar fixture vocabulary | Fixture vocabulary | Fixture builders should cover every fixture referenced by expanded sidecar expectations. | All referenced fixtures are available. | Pass |
| F9-R1-S2 | Planned extra non-git fixture | Fixture vocabulary | `non_git_project` should be available even if not directly referenced by the sidecar. | `non_git_project` is available and no other unplanned names were present. | Pass |
| F9-R1-S3 | Summary schema | Summary shape | Every fixture summary should contain harness-consumable fields. | Required fields were present for all eight fixtures. | Pass |
| F9-R1-S4 | Registered hooks in generated fixtures | Hook contract | Generated fixtures should register project-local Arbor hooks. | Every fixture contained `.codex/hooks.json` with the three canonical Arbor hook ids. | Pass |
| F9-R1-S5 | Hook entrypoint resolvability | Hook contract | Future hook execution harness should be able to resolve registered entrypoint scripts. | All entrypoint scripts exist under `skills/arbor`. | Pass |
| F9-R1-S6 | Clean git fixture | Fixture semantics | Clean fixture should have initialized files and empty raw git status. | `git_status_short` was `[]`. | Pass |
| F9-R1-S7 | Non-git fixture | Fixture semantics | Non-git fixture should initialize Arbor files and hooks without a `.git` directory. | `is_git_repo` false, `git_status_short` null, hooks present. | Pass |
| F9-R1-S8 | Missing AGENTS fixture | Fixture semantics | Missing AGENTS fixture should keep hooks while surfacing deleted `AGENTS.md`. | `has_agents` false and raw status included ` D AGENTS.md`. | Pass |
| F9-R1-S9 | Missing memory fixture | Fixture semantics | Missing memory fixture should keep hooks while surfacing deleted `.codex/memory.md`. | `has_memory` false and raw status included ` D .codex/memory.md`. | Pass |
| F9-R1-S10 | Uncommitted changes fixture | Fixture semantics | Fixture should expose both tracked and untracked work. | Raw status included ` M tracked.txt` and `?? pending.txt`. | Pass |
| F9-R1-S11 | Stale memory fixture | Fixture semantics | Fixture should mark memory stale and expose uncommitted fix evidence. | `memory_state` was `stale` and raw status included `?? fix-parser.txt`. | Pass |
| F9-R1-S12 | Durable drift docs fixture | Fixture semantics | Fixture should expose project-local docs for Hook 3 selected-doc scenarios. | `available_docs` contained constraints, project-map, and workflow docs. | Pass |
| F9-R1-S13 | Outside-root path fixture | Fixture semantics | Fixture should create a real file outside the project root for rejection tests. | `outside_path` existed and resolved outside `project_root`. | Pass |
| F9-R1-S14 | Deterministic payload rebuild | Determinism | Rebuilding each fixture under a different temp base should produce identical non-git file payloads. | All eight fixture payload digests matched. | Pass |
| F9-R1-S15 | CLI JSON output | CLI behavior | CLI should emit a machine-readable summary. | `uncommitted_changes` CLI output parsed as JSON and included raw pending status. | Pass |
| F9-R1-S16 | CLI nonempty-root rejection | CLI behavior | CLI should reject nonempty fixture roots without traceback. | Controlled parser error; no traceback. | Pass |

#### Impact Assessment

| Functional area | Risk checked | Result | Assessment |
| --- | --- | --- | --- |
| Sidecar compatibility | Fixture names should cover the structured sidecar and future harness vocabulary. | Coverage probes passed. | No negative impact found. |
| Hook execution readiness | Future harness should find registered hooks and entrypoint scripts in every fixture. | Hook contract probes passed. | No negative impact found. |
| Git state fidelity | Summaries should preserve raw `git status --short` semantics instead of normalizing away important state. | Git state probes passed. | No negative impact found. |
| Fixture determinism | Rebuilds should not depend on this repository's current state or on non-deterministic file payloads. | Payload determinism probes passed. | No negative impact found. |
| Boundary fixture safety | Outside-root fixture should be explicit and isolated to rejection scenarios. | Outside-root probes passed. | No negative impact found. |
| Stage B scope control | Feature should not implement dispatcher decisions or metrics prematurely. | No dispatcher or metric code found in Feature 9 surface. | No negative impact found. |

#### Optimization Suggestions

| Priority | Suggestion | Rationale | Follow-up owner |
| --- | --- | --- | --- |
| P1 | Keep fixture vocabulary checks tied to expanded sidecar expectations. | Sidecar changes should force fixture-builder review before metrics are trusted. | Feature 9 maintenance. |
| P2 | In the next Stage B increment, consume only the JSON summary and registered hook files instead of reaching into builder internals. | This proves the fixture API is sufficient for the dispatcher/hook harness boundary. | Dispatch harness owner. |
| P3 | Preserve the non-git fixture even if the current sidecar does not reference it directly. | Runtime event scenarios include outside-project and missing-project-root behavior; non-git project state is useful for dispatch boundary tests. | Stage B fixture owner. |
