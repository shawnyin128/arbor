# Feature 4 Review: Session Startup Hook Execution

## Purpose

Track the implementation, tests, and review feedback for the first executable Arbor hook: `arbor.session_startup_context`.

## Development Target

Feature 4 should turn the registered session-startup hook intent into a concrete workflow that can be run and tested. It should not implement the in-session memory hook or the goal/constraint drift hook.

The feature should:

- Resolve the current project root.
- Execute the startup context flow in Arbor order: `AGENTS.md`, formatted `git log`, `.codex/memory.md`, `git status`.
- Reuse the existing startup collector as the deterministic core.
- Preserve agent-selected read depth and git-log arguments.
- Return fallback diagnostics without blocking later sections.
- Avoid writing `.codex/memory.md` or `AGENTS.md`.

## Scope

In scope:

- Session startup hook wrapper or workflow entrypoint.
- Tests that replay the registered `arbor.session_startup_context` hook path.
- Hook 1 scenario tests.
- Minimal `SKILL.md` updates if needed to explain how to run Hook 1.

Out of scope:

- In-session memory refresh behavior.
- Goal/constraint drift behavior.
- Detailed constraints for later hooks.
- Automatic commits or pushes.

## Initial Review Questions

- Can the registered Hook 1 entrypoint be replayed without special context?
- Does Hook 1 preserve the startup read order?
- Does Hook 1 preserve no-read-limit behavior?
- Does Hook 1 surface fallback diagnostics and continue through all sections?
- Does Hook 1 avoid mutating memory or `AGENTS.md`?

## Implementation Notes

Implemented:

- `.codex/hooks.json` registers `arbor.session_startup_context`.
- The registered entrypoint points to `scripts/run_session_startup_hook.py --root ${PROJECT_ROOT}`.
- `scripts/run_session_startup_hook.py` resolves the project root, forwards optional agent-selected `--git-log-args`, and reuses the startup collector.
- The hook contract exposes `optional_args` for `--git-log-args`.
- Hook 1 does not write `.codex/memory.md` or `AGENTS.md`.

## Validation Plan

- Unit tests for hook wrapper argument handling and root resolution.
- Scenario test for a registered project with clean git state.
- Scenario test for a registered project with uncommitted work.
- Scenario test for missing setup files and non-git fallback diagnostics.
- Regression test that hook registration remains idempotent.

## Feedback Log

### Planning Adjustment

The feature queue now implements hooks one at a time. Feature 4 is Hook 1 only: session startup execution. Hook 2 memory hygiene and Hook 3 goal/constraint drift are intentionally deferred.

## Adversarial Review Rounds

### Round 1: Registered Startup Hook Replay

#### Round Result Tab

| Round | Scope | Verdict | Problems | Probe pass rate | Convergence |
| --- | --- | --- | ---: | ---: | --- |
| F4-R1 | Registered Hook 1 replay plus fallback, no-write, git-depth, and Feature 3 regression probes | Changes requested | 1 | 11/12, 91.7% | Not converged |

#### Problems Found

| ID | Severity | Area | Finding | Evidence | Impact | Next-round acceptance gate |
| --- | --- | --- | --- | --- | --- | --- |
| F4-R1-P1 | P2 | Agent-selected git log arguments | The registered `arbor.session_startup_context` entrypoint has no `--git-log-args` argument channel. | `.codex/hooks.json` and `ARBOR_HOOKS` register Hook 1 as `scripts/collect_project_context.py` with args `["--root", "${PROJECT_ROOT}"]`; the probe checking for a git-log args channel failed. | The direct collector supports agent-selected git log depth, but the registered Hook 1 path cannot pass that choice through. Feature 4 requires preserving agent-selected read depth and git-log arguments in the hook execution path. | Add a Hook 1 wrapper or hook contract parameter that accepts and forwards agent-selected `--git-log-args`. Add tests that replay the registered Hook 1 path with a selected `--max-count=1` log depth. |

#### Test Coverage Table

| Test category | Cases/checks run | Category coverage | Passed | Failed | Pass rate | Result summary |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Developer baseline playback | 5 checks | 5/5 planned checks, 100% | 5 | 0 | 100% | Replayed unittest, skill validation, py_compile, current Hook 1 entrypoint, coverage run, and coverage report. |
| Hook replay | 3 cases | 3/3 planned probes, 100% | 3 | 0 | 100% | Current registered Hook 1 exits cleanly, renders sections in order, and does not mutate `AGENTS.md` or `.codex/memory.md`. |
| Hook contract | 2 cases | 2/2 planned probes, 100% | 1 | 1 | 50% | Hook points to the collector, but has no agent-selected git-log args channel. |
| Hook scenarios | 5 cases | 5/5 planned probes, 100% | 5 | 0 | 100% | Fresh non-git, registered repo with commits, uncommitted status, and missing setup fallback all pass. |
| Collector and registration regression | 2 cases | 2/2 planned probes, 100% | 2 | 0 | 100% | Direct collector selected git-log args still work, and hook registration dry-run still works. |
| Total adversarial probes | 12 cases | 12/12 planned probes, 100% | 11 | 1 | 91.7% | Excludes baseline playback checks. |

#### Baseline Playback Table

| Command/check | Status | Notes |
| --- | --- | --- |
| `python3 -m unittest tests/test_arbor_skill.py` | Pass | 29 tests passed. |
| `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor` | Pass | Skill is valid. |
| `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f4-review-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py tests/test_arbor_skill.py` | Pass | No compile errors. |
| Registered Hook 1 replay from `.codex/hooks.json` | Pass | Exited code 0, rendered startup context, no stderr. |
| `env COVERAGE_FILE=/private/tmp/arbor-f4-review-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py` | Pass | 29 tests passed under coverage. |
| `env COVERAGE_FILE=/private/tmp/arbor-f4-review-coverage conda run -n arbor python -m coverage report` | Pass | Total coverage 87%. |

#### Scenario Test Matrix

| Scenario ID | Scenario | Category | Expected behavior | Observed result | Status |
| --- | --- | --- | --- | --- | --- |
| F4-R1-S1 | Current project registered Hook 1 replay | Hook replay | Exit cleanly and render startup context. | Exited code 0 with no stderr. | Pass |
| F4-R1-S2 | Current Hook 1 section order | Hook replay | Render `AGENTS.md`, git log, memory, git status in order. | Required order preserved. | Pass |
| F4-R1-S3 | Current Hook 1 no-write check | Hook replay | Do not mutate `AGENTS.md` or `.codex/memory.md`. | SHA-256 digests unchanged before/after replay. | Pass |
| F4-R1-S4 | Registered Hook 1 entrypoint target | Hook contract | Point to deterministic collector core. | Entrypoint script is `scripts/collect_project_context.py`. | Pass |
| F4-R1-S5 | Registered Hook 1 git-log args channel | Hook contract | Expose a way to pass agent-selected git log args. | Args are only `--root ${PROJECT_ROOT}`. | Fail |
| F4-R1-S6 | Fresh registered non-git project | Hook scenario | Return all four diagnostic sections. | Returned sections with git fallback diagnostics. | Pass |
| F4-R1-S7 | Registered git repo with commits | Hook scenario | Default log remains unconstrained. | All three commits appeared. | Pass |
| F4-R1-S8 | Registered git repo with uncommitted work | Hook scenario | Include pending file in git status. | `?? pending.txt` appeared. | Pass |
| F4-R1-S9 | Registered project with missing setup files | Hook scenario | Continue through all sections with missing/git-error diagnostics. | Returned all four sections. | Pass |
| F4-R1-S10 | Direct collector selected git-log args | Collector regression | Preserve selected `--max-count=1` behavior in core collector. | Direct collector returned one commit. | Pass |
| F4-R1-S11 | Hook registration dry-run | Feature 3 regression | Preserve registration behavior. | Returned `would_create`. | Pass |

#### Impact Assessment

| Functional area | Risk checked | Result | Assessment |
| --- | --- | --- | --- |
| Registered Hook 1 execution | Hook should be replayable from `.codex/hooks.json`. | Current project hook entrypoint executes successfully. | No negative impact found. |
| Startup order | Hook should preserve Arbor order. | Required section order preserved. | No negative impact found. |
| Fallback diagnostics | Hook should continue through missing/non-git states. | Missing setup and non-git scenarios return all sections. | No negative impact found. |
| No-write behavior | Hook 1 must not mutate memory or `AGENTS.md`. | Current project digest check passed. | No negative impact found. |
| Agent-selected read depth | Hook should preserve selected git-log args. | Registered hook has no args channel. | Finding F4-R1-P1 open. |
| Feature 3 regression | Hook registration should remain stable. | Dry-run still works. | No negative impact found. |

#### Optimization Suggestions

| Priority | Suggestion | Rationale | Verification expected next round |
| --- | --- | --- | --- |
| P1 | Add an explicit Hook 1 wrapper or update the hook contract so agent-selected `--git-log-args` can be forwarded. | The core collector already supports the option; the registered hook path needs to preserve it. | Replay the registered hook path with `--max-count=1` and show only one commit. |
| P2 | Add permanent tests that parse `.codex/hooks.json` or generated hook config and execute the registered Hook 1 path. | Current tests cover collector and registration separately, but not the integrated registered hook execution path. | Test suite includes registered-hook replay, no-write, fallback, and selected-depth cases. |
| P3 | After fixing Hook 1, update this review file from partial implementation to accepted or changes-needed based on replay. | Keeps the feature review aligned with actual executable behavior. | Round 2 closure table records the final Hook 1 status. |

### Developer Response: Round 1 Fixes

Changes made:

- Added `skills/arbor/scripts/run_session_startup_hook.py` as the Hook 1 execution wrapper.
- Updated canonical hook registration so `arbor.session_startup_context` points to `scripts/run_session_startup_hook.py`.
- Added an `optional_args` contract entry for `--git-log-args` so agent-selected git-log arguments can be forwarded through the registered hook path.
- Updated `.codex/hooks.json` in the current project by re-running hook registration.
- Updated `project-hooks-template.md` and `SKILL.md` to document the Hook 1 wrapper.
- Added permanent tests that parse generated `.codex/hooks.json`, execute the registered Hook 1 path, append selected `--git-log-args`, verify no-write behavior, and verify fallback diagnostics.
- Added direct wrapper tests so coverage includes the new wrapper logic as well as subprocess replay.

Validation:

- `python3 -m unittest tests/test_arbor_skill.py`: 35 tests passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 skills/arbor/scripts/register_project_hooks.py --root /Users/shawn/Desktop/arbor --dry-run`: reported `exists`.
- `python3 skills/arbor/scripts/run_session_startup_hook.py --root /Users/shawn/Desktop/arbor --git-log-args "--oneline --max-count=1"`: passed and rendered all four startup sections.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f4-r1-fix-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py tests/test_arbor_skill.py`: passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f4-r1-fix-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 35 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f4-r1-fix-coverage conda run -n arbor python -m coverage report`: total coverage 87%.

Closure assessment:

- F4-R1-P1: fixed. The registered Hook 1 path now has an explicit `--git-log-args` channel and tests replay that path with `--max-count=1`.
- Optimization P2: fixed. Registered-hook replay, selected-depth, no-write, and fallback tests are permanent suite coverage.
- Optimization P3: pending re-review.

### Round 2: Developer Fix Playback

#### Round Result Tab

| Round | Scope | Verdict | Problems | Probe pass rate | Convergence |
| --- | --- | --- | ---: | ---: | --- |
| F4-R2 | Round 1 closure replay plus wrapper, registered hook, fallback, CLI robustness, and regression probes | Accepted | 0 | 17/17, 100% | Converged for Feature 4 |

#### Problems Found

| ID | Severity | Area | Finding | Evidence | Impact | Next-round acceptance gate |
| --- | --- | --- | --- | --- | --- | --- |
| F4-R2-NF1 | None | Hook 1 execution | No new review finding. | Developer baseline checks passed; independent adversarial probes passed 17/17. | Feature 4 can be treated as accepted. | No additional Feature 4 gate. Move to Feature 5. |

#### Closure Playback

| Prior item | Status | Replay evidence | Assessment |
| --- | --- | --- | --- |
| F4-R1-P1: registered Hook 1 cannot forward selected git-log args | Closed | `.codex/hooks.json` now points to `scripts/run_session_startup_hook.py` and exposes `optional_args` for `--git-log-args` with `${GIT_LOG_ARGS}`. A temp git repo replay through the registered hook path with `--oneline --max-count=1` returned only the latest commit. | The original functional gap is fixed. |
| Optimization P2: add permanent registered-hook replay tests | Closed | Developer suite now has 35 tests, including registered Hook 1 replay, selected-depth, no-write, fallback, and direct wrapper coverage. | The regression surface is now represented in the suite. |
| Optimization P3: update final feature status after replay | Closed | Round 2 replay accepted Feature 4 with no new findings. | Feature 4 review is converged. |

#### Test Coverage Table

| Test category | Cases/checks run | Category coverage | Passed | Failed | Pass rate | Result summary |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Developer baseline playback | 7 checks | 7/7 planned checks, 100% | 7 | 0 | 100% | Replayed unit tests, skill validation, registration dry-run, direct Hook 1 execution with selected args, py_compile, coverage run, and coverage report. |
| Hook contract | 4 probes | 4/4 planned probes, 100% | 4 | 0 | 100% | Registered Hook 1 points to the wrapper, keeps the root placeholder, exposes `--git-log-args`, and matches canonical registration. |
| Registered hook replay | 5 probes | 5/5 planned probes, 100% | 5 | 0 | 100% | Parsed `.codex/hooks.json`, executed the registered command, preserved section order, kept default log unconstrained, and enforced selected `--max-count=1`. |
| No-write and fallback | 3 probes | 3/3 planned probes, 100% | 3 | 0 | 100% | Registered Hook 1 did not mutate `AGENTS.md` or `.codex/memory.md`, and missing setup/non-git projects still returned all four sections. |
| CLI robustness | 2 probes | 2/2 planned probes, 100% | 2 | 0 | 100% | Nonexistent root and malformed `--git-log-args` fail through concise CLI errors without traceback. |
| Regression coverage | 3 probes | 3/3 planned probes, 100% | 3 | 0 | 100% | Direct collector selected-depth behavior, Feature 3 dry-run create behavior, and Feature 2 empty raw-body preservation stayed intact. |
| Total adversarial probes | 17 probes | 17/17 planned probes, 100% | 17 | 0 | 100% | Excludes baseline playback checks. |

#### Baseline Playback Table

| Command/check | Status | Notes |
| --- | --- | --- |
| `python3 -m unittest tests/test_arbor_skill.py` | Pass | 35 tests passed. |
| `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor` | Pass | Skill is valid. |
| `python3 skills/arbor/scripts/register_project_hooks.py --root /Users/shawn/Desktop/arbor --dry-run` | Pass | Reported `exists`. |
| `python3 skills/arbor/scripts/run_session_startup_hook.py --root /Users/shawn/Desktop/arbor --git-log-args "--oneline --max-count=1"` | Pass | Rendered all four startup sections. Current repo has no commits, so git log returns the expected diagnostic status. |
| `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f4-r2-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py tests/test_arbor_skill.py` | Pass | No compile errors. |
| `env COVERAGE_FILE=/private/tmp/arbor-f4-r2-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py` | Pass | 35 tests passed under coverage. |
| `env COVERAGE_FILE=/private/tmp/arbor-f4-r2-coverage conda run -n arbor python -m coverage report` | Pass | Total coverage 87%. |

#### Scenario Test Matrix

| Scenario ID | Scenario | Category | Expected behavior | Observed result | Status |
| --- | --- | --- | --- | --- | --- |
| F4-R2-S1 | Current hook contract parse | Hook contract | `arbor.session_startup_context` is present and executable through the wrapper. | Hook script is `scripts/run_session_startup_hook.py`. | Pass |
| F4-R2-S2 | Hook optional git-log channel | Hook contract | Registered hook exposes a channel for agent-selected git-log args. | `optional_args` contains `--git-log-args` with `${GIT_LOG_ARGS}`. | Pass |
| F4-R2-S3 | Temp git repo default registered replay | Registered hook replay | Default registered hook remains no-read-limit and shows all commits. | All three probe commits appeared. | Pass |
| F4-R2-S4 | Temp git repo selected-depth registered replay | Registered hook replay | `--oneline --max-count=1` through the registered hook path returns only the latest commit. | Latest commit appeared; older probe commits were absent. | Pass |
| F4-R2-S5 | Section order replay | Registered hook replay | Render `AGENTS.md`, formatted git log, `.codex/memory.md`, and git status in order. | Rendered headings appeared in the expected order. | Pass |
| F4-R2-S6 | No-write replay | No-write | Hook 1 must not modify `AGENTS.md` or `.codex/memory.md`. | SHA-256 digests stayed unchanged. | Pass |
| F4-R2-S7 | Missing setup and non-git project | Fallback | Continue through all sections with diagnostics instead of aborting. | All four sections returned with missing/git diagnostics. | Pass |
| F4-R2-S8 | Nonexistent root | CLI robustness | Reject unresolved root with controlled CLI error. | Failed without traceback and reported that the root does not exist. | Pass |
| F4-R2-S9 | Malformed git-log args | CLI robustness | Reject malformed shell-style args without traceback. | Failed without traceback and reported invalid `--git-log-args`. | Pass |
| F4-R2-S10 | Direct collector selected-depth regression | Regression | Existing collector selected-depth behavior still works. | Direct collector returned only the latest probe commit. | Pass |
| F4-R2-S11 | Feature 3 dry-run registration regression | Regression | Dry-run for a new project should still report hook creation without writing. | Returned `would_create`. | Pass |
| F4-R2-S12 | Feature 2 empty file regression | Regression | Empty file raw body remains empty while status carries `empty`. | `body == ""` and `status == "empty"`. | Pass |

#### Impact Assessment

| Functional area | Risk checked | Result | Assessment |
| --- | --- | --- | --- |
| Hook 1 selected-depth forwarding | The registered hook path should preserve agent-selected git-log args. | Registered path with `--max-count=1` returned only one commit. | Fixed; no remaining issue found. |
| Hook 1 default read depth | The fix should not constrain default startup context. | Default registered replay returned all probe commits. | No negative impact found. |
| Startup order | Wrapper should preserve the collector's Arbor order. | Section headings stayed in order. | No negative impact found. |
| Fallback diagnostics | Wrapper should not block later sections on missing files or non-git roots. | All sections rendered with diagnostics. | No negative impact found. |
| No-write behavior | Session startup must not mutate project memory or `AGENTS.md`. | Digest check passed. | No negative impact found. |
| Prior feature behavior | Feature 2 and Feature 3 regressions should remain closed. | Empty raw-body and dry-run registration probes passed. | No negative impact found. |

#### Optimization Suggestions

| Priority | Suggestion | Rationale | Follow-up owner |
| --- | --- | --- | --- |
| P1 | Keep the registered-hook selected-depth replay as permanent coverage. | This is the exact integration path that broke in Round 1. | Feature 4 maintenance. |
| P2 | Use the same wrapper-plus-contract pattern for Feature 5 rather than calling lower-level helpers directly from hook config. | It gives each hook a stable CLI boundary for root resolution, argument parsing, fallback behavior, and tests. | Feature 5 design. |
| P3 | Treat Hook 1 as accepted and start the in-session memory hook review from a fresh feature file. | Feature 4 has converged; further work belongs to Hook 2. | Review queue. |
