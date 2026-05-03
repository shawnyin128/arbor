# Feature 5 Review: In-Session Memory Hook Execution

## Purpose

Track the implementation, tests, and review feedback for the second executable Arbor hook: `arbor.in_session_memory_hygiene`.

## Development Target

Feature 5 should turn the registered in-session memory hook intent into a concrete workflow that can be run and tested. It should not implement the goal/constraint drift hook.

The feature should:

- Resolve the current project root.
- Emit a memory hygiene packet with project-local context.
- Include existing `.codex/memory.md`, `git status --short`, `git diff --stat`, and optional agent-selected diff.
- Preserve agent-selected read depth by forwarding optional diff arguments.
- Let the running agent decide whether and how to update `.codex/memory.md`.
- Avoid writing `AGENTS.md`.
- Avoid a standalone semantic memory freshness checker.

## Scope

In scope:

- Hook 2 wrapper script.
- Registered Hook 2 script entrypoint.
- Optional `--diff-args` channel.
- Tests that replay the registered `arbor.in_session_memory_hygiene` hook path.
- Hook 2 scenario tests.

Out of scope:

- Goal/constraint drift behavior.
- Automatic semantic freshness classification.
- Automatic durable project guide updates.
- Automatic commits or pushes.

## Initial Review Questions

- Can the registered Hook 2 entrypoint be replayed without special context?
- Does Hook 2 preserve project-local memory boundaries?
- Does Hook 2 include enough context for the agent to decide whether memory is stale?
- Does Hook 2 preserve agent-selected diff arguments?
- Does Hook 2 avoid mutating `AGENTS.md`?

## Implementation Notes

Implemented:

- Added `skills/arbor/scripts/run_memory_hygiene_hook.py`.
- Updated canonical hook registration so `arbor.in_session_memory_hygiene` points to `scripts/run_memory_hygiene_hook.py`.
- Added an `optional_args` contract entry for `--diff-args`.
- Updated `.codex/hooks.json` in the current project by re-running hook registration.
- Updated `project-hooks-template.md`, `SKILL.md`, and `AGENTS.md`.
- Fixed git runner output preservation by changing stdout/stderr handling from `strip()` to `rstrip("\n")`, preserving leading spaces in `git status --short`.

Hook 2 emits:

- Agent instructions for memory hygiene.
- Current `.codex/memory.md`.
- `git status --short`.
- Unstaged `git diff --stat`.
- Staged `git diff --cached --stat`.
- Optional selected `git diff`.

The hook does not auto-edit memory. The running agent uses the packet plus conversation context to decide whether `.codex/memory.md` needs an update.

## Validation Plan

- Unit tests for root resolution and argument parsing.
- Scenario test for uncommitted tracked and untracked work.
- Scenario test for selected diff passthrough.
- Registered-hook replay test from generated `.codex/hooks.json`.
- No-write test for `.codex/memory.md` and `AGENTS.md`.
- Non-git fallback diagnostics test.
- Regression test that hook registration remains idempotent.

## Feedback Log

### Implementation Validation

Commands:

- `python3 -m unittest tests/test_arbor_skill.py`: 42 tests passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 skills/arbor/scripts/register_project_hooks.py --root /Users/shawn/Desktop/arbor --dry-run`: reported `exists`.
- `python3 skills/arbor/scripts/run_memory_hygiene_hook.py --root /Users/shawn/Desktop/arbor --diff-args "-- .codex/memory.md"`: passed and rendered memory, git status, diff stat, and selected diff sections.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f5-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py tests/test_arbor_skill.py`: passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f5-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 42 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f5-coverage conda run -n arbor python -m coverage report`: total coverage 87%.

Scenario coverage:

- Hook 2 packet includes memory, git status, and diff stat.
- Hook 2 preserves `git status --short` leading spaces for unstaged tracked changes.
- Hook 2 forwards selected `--diff-args` into a selected diff section.
- Registered Hook 2 path is replayed from generated `.codex/hooks.json`.
- Registered Hook 2 path does not write `.codex/memory.md` or `AGENTS.md`.
- Non-git projects return fallback diagnostics without blocking later sections.
- Malformed `--diff-args` exits through controlled argparse error handling without traceback.
- Nonexistent roots exit through controlled argparse error handling without traceback.

## Adversarial Review Rounds

### Round 1: In-Session Memory Hook Replay

#### Round Result Tab

| Round | Scope | Verdict | Problems | Probe pass rate | Convergence |
| --- | --- | --- | ---: | ---: | --- |
| F5-R1 | Registered Hook 2 replay plus selected diff, no-write boundary, staged-work, fallback, CLI, and regression probes | Changes requested | 2 | 22/25, 88.0% | Not converged |

#### Problems Found

| ID | Severity | Area | Finding | Evidence | Impact | Next-round acceptance gate |
| --- | --- | --- | --- | --- | --- | --- |
| F5-R1-P1 | P1 | Selected diff argument safety | Hook 2 forwards raw `--diff-args` into `git diff`, so legal diff options with side effects can write project files. | Registered Hook 2 replay with `--diff-args "--output=AGENTS.md -- tracked.txt"` overwrote the temp project's `AGENTS.md` with diff text and emitted an empty selected-diff body. | This violates the Hook 2 packet boundary and the explicit "Do not update `AGENTS.md` from this hook" instruction. A mistaken agent-selected diff option can silently corrupt durable project guide content. | Reject side-effecting diff options such as `--output`, and add a registered-path regression test proving selected diff args cannot mutate `AGENTS.md` or `.codex/memory.md`. |
| F5-R1-P2 | P2 | Staged-only work visibility | The default packet uses `git diff --stat`, which omits staged-only changes. | In a temp repo with only staged changes, Hook 2 status showed `M  staged.txt`, but the `git diff --stat` section was `Status: empty`. | The packet under-reports uncommitted work at the exact checkpoint where memory hygiene is needed; the agent must infer stale memory from status alone without the promised diff-stat context. | Include staged changes in the default stat packet, for example with `git diff --stat HEAD` or separate unstaged and staged stat sections, and add staged-only tests. |

#### Test Coverage Table

| Test category | Cases/checks run | Category coverage | Passed | Failed | Pass rate | Result summary |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Developer baseline playback | 7 checks | 7/7 planned checks, 100% | 7 | 0 | 100% | Replayed unit tests, skill validation, registration dry-run, direct Hook 2 execution with selected args, py_compile, coverage run, and coverage report. |
| Hook contract | 4 probes | 4/4 planned probes, 100% | 4 | 0 | 100% | Registered Hook 2 points to the wrapper, keeps the root placeholder, exposes `--diff-args`, and matches canonical registration. |
| Registered hook replay | 6 probes | 6/6 planned probes, 100% | 6 | 0 | 100% | Parsed `.codex/hooks.json`, executed the registered command, included memory/status/diff-stat sections, preserved leading status spaces, and omitted selected diff by default. |
| Selected diff replay | 3 probes | 3/3 planned probes, 100% | 3 | 0 | 100% | Safe selected diff args render a selected diff section and include the expected hunk. |
| No-write and boundary probes | 3 probes | 3/3 planned probes, 100% | 1 | 2 | 33.3% | Safe selected diff is read-only, but `--output=AGENTS.md` mutates `AGENTS.md` and suppresses stdout packet content. |
| Staged-work coverage | 2 probes | 2/2 planned probes, 100% | 1 | 1 | 50% | Status surfaces staged-only files, but default `git diff --stat` is empty for staged-only changes. |
| Fallback and CLI robustness | 5 probes | 5/5 planned probes, 100% | 5 | 0 | 100% | Missing setup/non-git fallback, nonexistent root, and malformed diff args fail or render diagnostics without traceback. |
| Regression coverage | 2 probes | 2/2 planned probes, 100% | 2 | 0 | 100% | Feature 3 dry-run registration and Feature 2 empty raw-body behavior remain intact. |
| Total adversarial probes | 25 probes | 25/25 planned probes, 100% | 22 | 3 | 88.0% | Excludes baseline playback checks. |

#### Baseline Playback Table

| Command/check | Status | Notes |
| --- | --- | --- |
| `python3 -m unittest tests/test_arbor_skill.py` | Pass | 42 tests passed. |
| `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor` | Pass | Skill is valid. |
| `python3 skills/arbor/scripts/register_project_hooks.py --root /Users/shawn/Desktop/arbor --dry-run` | Pass | Reported `exists`. |
| `python3 skills/arbor/scripts/run_memory_hygiene_hook.py --root /Users/shawn/Desktop/arbor --diff-args "-- .codex/memory.md"` | Pass | Rendered memory, git status, diff stat, and selected diff sections. |
| `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f5-r1-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py tests/test_arbor_skill.py` | Pass | No compile errors. |
| `env COVERAGE_FILE=/private/tmp/arbor-f5-r1-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py` | Pass | 42 tests passed under coverage. |
| `env COVERAGE_FILE=/private/tmp/arbor-f5-r1-coverage conda run -n arbor python -m coverage report` | Pass | Total coverage 87%. |

#### Scenario Test Matrix

| Scenario ID | Scenario | Category | Expected behavior | Observed result | Status |
| --- | --- | --- | --- | --- | --- |
| F5-R1-S1 | Current hook contract parse | Hook contract | `arbor.in_session_memory_hygiene` is present and executable through the wrapper. | Hook script is `scripts/run_memory_hygiene_hook.py`. | Pass |
| F5-R1-S2 | Hook optional diff channel | Hook contract | Registered hook exposes agent-selected diff args. | `optional_args` contains `--diff-args` with `${DIFF_ARGS}`. | Pass |
| F5-R1-S3 | Registered Hook 2 default replay | Registered hook replay | Exit cleanly and include memory, status, and diff-stat sections. | All default sections rendered. | Pass |
| F5-R1-S4 | Unstaged tracked work | Registered hook replay | Preserve leading status space and show diff stat. | ` M tracked.txt` and `tracked.txt` diff stat appeared. | Pass |
| F5-R1-S5 | Untracked work | Registered hook replay | Surface untracked files in status. | `?? pending.txt` appeared. | Pass |
| F5-R1-S6 | Safe selected diff | Selected diff replay | Emit selected diff section with hunk body. | `## 4. selected git diff` and `+changed` appeared. | Pass |
| F5-R1-S7 | Safe selected diff no-write | No-write | Safe selected diff should not mutate memory or `AGENTS.md`. | SHA-256 digests stayed unchanged. | Pass |
| F5-R1-S8 | Side-effecting selected diff args | No-write | Hook should reject or neutralize options that write files. | `--output=AGENTS.md` overwrote `AGENTS.md`. | Fail |
| F5-R1-S9 | Side-effecting selected diff packet integrity | No-write | Hook should not silently emit an empty selected-diff body after redirecting output to a file. | Selected-diff stdout was empty while the diff was written to `AGENTS.md`. | Fail |
| F5-R1-S10 | Staged-only work status | Staged-work coverage | Surface staged-only changes. | `M  staged.txt` appeared in status. | Pass |
| F5-R1-S11 | Staged-only work diff stat | Staged-work coverage | Default diff stat should cover staged-only changes or explicitly include staged stat. | `git diff --stat` section was `Status: empty`. | Fail |
| F5-R1-S12 | Missing setup and non-git project | Fallback | Continue through packet sections with diagnostics. | Missing memory and git-error diagnostics rendered. | Pass |
| F5-R1-S13 | Nonexistent root | CLI robustness | Reject unresolved root with controlled CLI error. | Failed without traceback and reported the missing root. | Pass |
| F5-R1-S14 | Malformed diff args | CLI robustness | Reject malformed shell-style args without traceback. | Failed without traceback and reported invalid git args. | Pass |
| F5-R1-S15 | Feature 3 dry-run registration regression | Regression | Dry-run for a new project should still report hook creation without writing. | Returned `would_create`. | Pass |
| F5-R1-S16 | Feature 2 empty file regression | Regression | Empty file raw body remains empty while status carries `empty`. | `body == ""` and `status == "empty"`. | Pass |

#### Impact Assessment

| Functional area | Risk checked | Result | Assessment |
| --- | --- | --- | --- |
| Registered Hook 2 execution | Hook should be replayable from `.codex/hooks.json`. | Registered path executes successfully. | No negative impact found. |
| Selected diff passthrough | Hook should preserve agent-selected diff args. | Safe path args work. | Core feature works, but argument safety is incomplete. |
| Project-local write boundary | Hook 2 should emit context and avoid `AGENTS.md` writes. | `--output=AGENTS.md` mutates the project guide. | Finding F5-R1-P1 open. |
| Staged uncommitted work | Hook should provide enough context for memory hygiene at checkpoints. | Status sees staged files, diff stat does not. | Finding F5-R1-P2 open. |
| Fallback diagnostics | Hook should continue through missing/non-git states. | Missing setup and non-git diagnostics pass. | No negative impact found. |
| Prior feature behavior | Feature 2 and Feature 3 regressions should remain closed. | Empty raw-body and dry-run registration probes passed. | No negative impact found. |

#### Optimization Suggestions

| Priority | Suggestion | Rationale | Verification expected next round |
| --- | --- | --- | --- |
| P1 | Validate `--diff-args` against side-effecting git diff options before calling git. | Hook 2 is a packet generator; selected args should change what is read, not write files. | Registered-path replay with `--output=AGENTS.md` fails with a concise error and leaves files unchanged. |
| P2 | Include staged changes in the default stat context. | Memory hygiene is about uncommitted work, and staged-only changes are still uncommitted. | Staged-only temp repo shows a non-empty stat section or an explicit staged stat section. |
| P3 | Add tests for staged-only work and side-effecting diff args. | Existing tests cover safe selected diffs but not the failure modes above. | Permanent suite includes both adversarial cases. |

### Developer Response: Round 1 Fixes

Changes made:

- Fixed F5-R1-P1 by validating selected `--diff-args` before calling `git diff`.
- Rejected side-effecting diff options that can write files, including `--output`, `--output=...`, `-o`, and `--ext-diff`.
- Added a registered-path regression test proving `--diff-args "--output=AGENTS.md -- tracked.txt"` exits with a controlled error and leaves both `AGENTS.md` and `.codex/memory.md` unchanged.
- Fixed F5-R1-P2 by adding an explicit staged stat section: `git diff --cached --stat`.
- Added staged-only regression coverage proving `M  staged.txt` appears in status and `staged.txt` appears in the staged stat context.
- Updated design and hook contract docs to describe unstaged stat, staged stat, and selected diff safety.

Validation:

- `python3 -m unittest tests/test_arbor_skill.py`: 44 tests passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 skills/arbor/scripts/run_memory_hygiene_hook.py --root /Users/shawn/Desktop/arbor --diff-args "--output=AGENTS.md -- .codex/memory.md"`: exited with controlled `unsafe git diff argument` error.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f5-r1-fix-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py tests/test_arbor_skill.py`: passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f5-r1-fix-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 44 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f5-r1-fix-coverage conda run -n arbor python -m coverage report`: total coverage 87%.

Closure assessment:

- F5-R1-P1: fixed.
- F5-R1-P2: fixed with a separate staged stat section.
- Optimization P3: fixed through permanent adversarial tests.

### Round 2: Developer Fix Playback

#### Round Result Tab

| Round | Scope | Verdict | Problems | Probe pass rate | Convergence |
| --- | --- | --- | ---: | ---: | --- |
| F5-R2 | Round 1 closure replay plus unsafe-arg variants, staged stat, fallback, CLI, regression, and project-local boundary probes | Changes requested | 1 | 28/29, 96.6% | Not converged |

#### Problems Found

| ID | Severity | Area | Finding | Evidence | Impact | Next-round acceptance gate |
| --- | --- | --- | --- | --- | --- | --- |
| F5-R2-P1 | P2 | Selected diff project-local boundary | `--diff-args` validation blocks write-oriented options, but still permits `--no-index`, which lets `git diff` compare project files with paths outside the project root. | Registered Hook 2 replay with `--diff-args "--no-index /private/tmp/.../outside.txt tracked.txt"` emitted the outside file path and body inside the selected diff packet. | Hook 2 is supposed to emit project-local memory hygiene context. This allows agent-selected hook arguments to pull arbitrary outside-root file content into the packet, violating the project-local boundary even though it does not write files. | Reject `--no-index` and add a registered-path test proving selected diff args cannot read outside the resolved project root. |

#### Closure Playback

| Prior item | Status | Replay evidence | Assessment |
| --- | --- | --- | --- |
| F5-R1-P1: side-effecting selected diff args can write `AGENTS.md` | Closed | Registered Hook 2 rejected `--output=AGENTS.md`, `--output AGENTS.md`, `-o AGENTS.md`, and `--ext-diff` with controlled CLI errors; memory and `AGENTS.md` digests remained unchanged. | The write-side boundary is fixed for the tested variants. |
| F5-R1-P2: staged-only work missing from default stat packet | Closed | Registered Hook 2 now emits `## 4. git diff --cached --stat`; staged-only temp repo showed `staged.txt` and `1 file changed` in that section. | The staged-only visibility gap is fixed. |
| Optimization P3: permanent adversarial tests | Closed | Suite increased to 44 tests and includes side-effecting diff args and staged-only coverage. | Regression coverage exists for the previous findings. |

#### Test Coverage Table

| Test category | Cases/checks run | Category coverage | Passed | Failed | Pass rate | Result summary |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Developer baseline playback | 7 checks | 7/7 planned checks, 100% | 7 | 0 | 100% | Replayed unit tests, skill validation, registration dry-run, unsafe-arg CLI check, py_compile, coverage run, and coverage report. |
| Hook contract | 4 probes | 4/4 planned probes, 100% | 4 | 0 | 100% | Registered Hook 2 still points to the wrapper, keeps the root placeholder, exposes `--diff-args`, and matches canonical registration. |
| Registered hook replay | 6 probes | 6/6 planned probes, 100% | 6 | 0 | 100% | Default packet exits cleanly and includes memory, status, unstaged stat, staged stat, and no selected diff by default. |
| Selected diff replay | 3 probes | 3/3 planned probes, 100% | 3 | 0 | 100% | Safe selected diff still renders section 5 and includes the expected hunk. |
| Unsafe write-arg closure | 4 probes | 4/4 planned probes, 100% | 4 | 0 | 100% | `--output=...`, `--output ...`, `-o ...`, and `--ext-diff` are rejected without traceback and without file mutation. |
| Staged-work closure | 3 probes | 3/3 planned probes, 100% | 3 | 0 | 100% | Staged-only changes appear in status and staged stat; unstaged stat remains empty for staged-only changes. |
| Project-local boundary | 1 probe | 1/1 planned probe, 100% | 0 | 1 | 0% | `--no-index` can read an outside-root file into the selected diff packet. |
| Fallback and CLI robustness | 5 probes | 5/5 planned probes, 100% | 5 | 0 | 100% | Missing setup/non-git fallback, nonexistent root, and malformed diff args behave without traceback. |
| Regression coverage | 2 probes | 2/2 planned probes, 100% | 2 | 0 | 100% | Feature 3 dry-run registration and Feature 2 empty raw-body behavior remain intact. |
| Total adversarial probes | 29 probes | 29/29 planned probes, 100% | 28 | 1 | 96.6% | Excludes baseline playback checks. |

#### Baseline Playback Table

| Command/check | Status | Notes |
| --- | --- | --- |
| `python3 -m unittest tests/test_arbor_skill.py` | Pass | 44 tests passed. |
| `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor` | Pass | Skill is valid. |
| `python3 skills/arbor/scripts/register_project_hooks.py --root /Users/shawn/Desktop/arbor --dry-run` | Pass | Reported `exists`. |
| `python3 skills/arbor/scripts/run_memory_hygiene_hook.py --root /Users/shawn/Desktop/arbor --diff-args "--output=AGENTS.md -- .codex/memory.md"` | Pass | Exited with controlled `unsafe git diff argument` error. |
| `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f5-r2-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py tests/test_arbor_skill.py` | Pass | No compile errors. |
| `env COVERAGE_FILE=/private/tmp/arbor-f5-r2-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py` | Pass | 44 tests passed under coverage. |
| `env COVERAGE_FILE=/private/tmp/arbor-f5-r2-coverage conda run -n arbor python -m coverage report` | Pass | Total coverage 87%. |

#### Scenario Test Matrix

| Scenario ID | Scenario | Category | Expected behavior | Observed result | Status |
| --- | --- | --- | --- | --- | --- |
| F5-R2-S1 | Current hook contract parse | Hook contract | `arbor.in_session_memory_hygiene` remains executable through the wrapper. | Hook script is `scripts/run_memory_hygiene_hook.py`. | Pass |
| F5-R2-S2 | Default packet structure | Registered hook replay | Include memory, status, unstaged stat, and staged stat sections. | All four default sections rendered. | Pass |
| F5-R2-S3 | Unstaged tracked work | Registered hook replay | Show status and unstaged diff stat. | ` M tracked.txt` and unstaged stat appeared. | Pass |
| F5-R2-S4 | Safe selected diff | Selected diff replay | Render section 5 with selected diff body. | `## 5. selected git diff` and `+changed` appeared. | Pass |
| F5-R2-S5 | `--output=...` unsafe args | Unsafe write-arg closure | Reject without traceback and without writing files. | Controlled error; digests unchanged. | Pass |
| F5-R2-S6 | `--output ...` unsafe args | Unsafe write-arg closure | Reject without traceback and without writing files. | Controlled error; digests unchanged. | Pass |
| F5-R2-S7 | `-o ...` unsafe args | Unsafe write-arg closure | Reject without traceback and without writing files. | Controlled error; digests unchanged. | Pass |
| F5-R2-S8 | `--ext-diff` unsafe args | Unsafe write-arg closure | Reject without traceback and without external diff execution. | Controlled error; digests unchanged. | Pass |
| F5-R2-S9 | Staged-only work status | Staged-work closure | Surface staged-only changes. | `M  staged.txt` appeared. | Pass |
| F5-R2-S10 | Staged-only staged stat | Staged-work closure | Default staged stat should show staged-only changes. | `staged.txt` and `1 file changed` appeared under cached stat. | Pass |
| F5-R2-S11 | `--no-index` outside-root read | Project-local boundary | Selected diff should not read outside the project root. | Outside file path and body appeared in the packet. | Fail |
| F5-R2-S12 | Missing setup and non-git project | Fallback | Continue through packet sections with diagnostics. | Missing memory and git-error diagnostics rendered. | Pass |
| F5-R2-S13 | Nonexistent root | CLI robustness | Reject unresolved root with controlled CLI error. | Failed without traceback and reported the missing root. | Pass |
| F5-R2-S14 | Malformed diff args | CLI robustness | Reject malformed shell-style args without traceback. | Failed without traceback and reported invalid git args. | Pass |
| F5-R2-S15 | Feature 3 dry-run registration regression | Regression | Dry-run for a new project should still report hook creation without writing. | Returned `would_create`. | Pass |
| F5-R2-S16 | Feature 2 empty file regression | Regression | Empty file raw body remains empty while status carries `empty`. | `body == ""` and `status == "empty"`. | Pass |

#### Impact Assessment

| Functional area | Risk checked | Result | Assessment |
| --- | --- | --- | --- |
| Write-side Hook 2 boundary | Unsafe selected diff args should not mutate project files. | Tested write-oriented variants are rejected. | F5-R1-P1 closed. |
| Staged work visibility | Default packet should include staged-only work context. | Staged stat section covers staged-only changes. | F5-R1-P2 closed. |
| Project-local read boundary | Selected diff args should not pull outside-root file content into the packet. | `--no-index` can read outside-root files. | Finding F5-R2-P1 open. |
| Registered Hook 2 execution | Hook should remain replayable from `.codex/hooks.json`. | Registered path executes successfully. | No negative impact found. |
| Fallback diagnostics | Hook should continue through missing/non-git states. | Missing setup and non-git diagnostics pass. | No negative impact found. |
| Prior feature behavior | Feature 2 and Feature 3 regressions should remain closed. | Empty raw-body and dry-run registration probes passed. | No negative impact found. |

#### Optimization Suggestions

| Priority | Suggestion | Rationale | Verification expected next round |
| --- | --- | --- | --- |
| P1 | Reject `--no-index` in selected diff args. | It makes `git diff` compare arbitrary paths rather than project-local git-tracked paths. | Registered-path replay with `--no-index <outside> tracked.txt` fails with a concise error and does not include outside content. |
| P2 | Consider path-boundary validation for selected diff pathspecs if future args support absolute paths. | The hook contract is project-local; argument validation should protect both write and read boundaries. | Tests cover outside-root absolute path attempts. |
| P3 | Keep Round 1 closure tests as permanent suite coverage. | They guard the exact previously broken behavior. | Existing 44-test suite remains green after adding `--no-index` coverage. |

### Developer Response: Round 2 Fixes

Changes made:

- Fixed F5-R2-P1 by rejecting `--no-index` in selected `--diff-args`.
- Added project-local read-boundary validation for absolute diff path arguments.
- Added a registered-path regression test proving `--diff-args "--no-index <outside> tracked.txt"` exits with a controlled error and does not emit outside file content.
- Added a registered-path regression test proving `--diff-args "-- <outside-absolute-path>"` exits with a controlled outside-root path error and does not emit outside file content.

Validation:

- `python3 -m unittest tests/test_arbor_skill.py`: 46 tests passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 skills/arbor/scripts/run_memory_hygiene_hook.py --root /Users/shawn/Desktop/arbor --diff-args "--no-index /private/tmp/outside.txt .codex/memory.md"`: exited with controlled `unsafe git diff argument` error.
- `python3 skills/arbor/scripts/run_memory_hygiene_hook.py --root /Users/shawn/Desktop/arbor --diff-args "-- /private/tmp/outside.txt"`: exited with controlled outside-root path error.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f5-r2-fix-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py tests/test_arbor_skill.py`: passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f5-r2-fix-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 46 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f5-r2-fix-coverage conda run -n arbor python -m coverage report`: total coverage 87%.

Closure assessment:

- F5-R2-P1: fixed.
- Optimization P2: addressed with absolute outside-root path validation.
- Optimization P3: retained; prior closure tests remain in the permanent suite.

### Round 3: Project-Local Boundary Fix Playback

#### Round Result Tab

| Round | Scope | Verdict | Problems | Probe pass rate | Convergence |
| --- | --- | --- | ---: | ---: | --- |
| F5-R3 | Round 2 closure replay plus no-index, outside absolute path, safe selected diff, staged stat, fallback, CLI, and regression probes | Accepted | 0 | 29/29, 100% | Converged for Feature 5 |

#### Problems Found

| ID | Severity | Area | Finding | Evidence | Impact | Next-round acceptance gate |
| --- | --- | --- | --- | --- | --- | --- |
| F5-R3-NF1 | None | Hook 2 execution | No new review finding. | Developer baseline checks passed; independent adversarial probes passed 29/29. | Feature 5 can be treated as accepted. | No additional Feature 5 gate. Move to Feature 6 / Hook 3 review. |

#### Closure Playback

| Prior item | Status | Replay evidence | Assessment |
| --- | --- | --- | --- |
| F5-R2-P1: `--no-index` can read outside-root file content into the packet | Closed | Registered Hook 2 rejected `--no-index <outside> tracked.txt` with a controlled `unsafe git diff argument` error; stdout did not contain outside file content. | The project-local read boundary gap is fixed for `--no-index`. |
| Optimization P2: outside absolute path validation | Closed | Registered Hook 2 rejected `-- <outside-absolute-path>` with a controlled outside-root path error; stdout did not contain outside file content. | Absolute selected pathspecs are now root-bounded. |
| Round 1 closure behavior | Still closed | `--output=...`, `--output ...`, `-o ...`, and `--ext-diff` remained rejected; staged-only work still appeared in the staged stat section. | No regression found. |

#### Test Coverage Table

| Test category | Cases/checks run | Category coverage | Passed | Failed | Pass rate | Result summary |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Developer baseline playback | 8 checks | 8/8 planned checks, 100% | 8 | 0 | 100% | Replayed unit tests, skill validation, no-index CLI check, outside absolute path CLI check, py_compile, coverage run, coverage report, and registration dry-run. |
| Hook contract | 4 probes | 4/4 planned probes, 100% | 4 | 0 | 100% | Registered Hook 2 still points to the wrapper, keeps the root placeholder, exposes `--diff-args`, and matches canonical registration. |
| Registered hook replay | 6 probes | 6/6 planned probes, 100% | 6 | 0 | 100% | Default packet exits cleanly and includes memory, status, unstaged stat, staged stat, and no selected diff by default. |
| Selected diff replay | 3 probes | 3/3 planned probes, 100% | 3 | 0 | 100% | Safe selected diff still renders section 5 and includes the expected hunk. |
| Unsafe write/read-boundary closure | 6 probes | 6/6 planned probes, 100% | 6 | 0 | 100% | `--output=...`, `--output ...`, `-o ...`, `--ext-diff`, `--no-index`, and outside absolute path args are rejected without traceback or file mutation. |
| Project-local allowed path | 1 probe | 1/1 planned probe, 100% | 1 | 0 | 100% | Absolute path inside the resolved project root remains allowed and renders the selected diff. |
| Staged-work closure | 2 probes | 2/2 planned probes, 100% | 2 | 0 | 100% | Staged-only changes appear in status and staged stat. |
| Fallback and CLI robustness | 5 probes | 5/5 planned probes, 100% | 5 | 0 | 100% | Missing setup/non-git fallback, nonexistent root, and malformed diff args behave without traceback. |
| Regression coverage | 2 probes | 2/2 planned probes, 100% | 2 | 0 | 100% | Feature 3 dry-run registration and Feature 2 empty raw-body behavior remain intact. |
| Total adversarial probes | 29 probes | 29/29 planned probes, 100% | 29 | 0 | 100% | Excludes baseline playback checks. |

#### Baseline Playback Table

| Command/check | Status | Notes |
| --- | --- | --- |
| `python3 -m unittest tests/test_arbor_skill.py` | Pass | 46 tests passed. |
| `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor` | Pass | Skill is valid. |
| `python3 skills/arbor/scripts/run_memory_hygiene_hook.py --root /Users/shawn/Desktop/arbor --diff-args "--no-index /private/tmp/outside.txt .codex/memory.md"` | Pass | Exited with controlled `unsafe git diff argument` error. |
| `python3 skills/arbor/scripts/run_memory_hygiene_hook.py --root /Users/shawn/Desktop/arbor --diff-args "-- /private/tmp/outside.txt"` | Pass | Exited with controlled outside-root path error. |
| `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f5-r3-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py tests/test_arbor_skill.py` | Pass | No compile errors. |
| `env COVERAGE_FILE=/private/tmp/arbor-f5-r3-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py` | Pass | 46 tests passed under coverage. |
| `env COVERAGE_FILE=/private/tmp/arbor-f5-r3-coverage conda run -n arbor python -m coverage report` | Pass | Total coverage 87%. |
| `python3 skills/arbor/scripts/register_project_hooks.py --root /Users/shawn/Desktop/arbor --dry-run` | Pass | Reported `exists`. |

#### Scenario Test Matrix

| Scenario ID | Scenario | Category | Expected behavior | Observed result | Status |
| --- | --- | --- | --- | --- | --- |
| F5-R3-S1 | Current hook contract parse | Hook contract | `arbor.in_session_memory_hygiene` remains executable through the wrapper. | Hook script is `scripts/run_memory_hygiene_hook.py`. | Pass |
| F5-R3-S2 | Default packet structure | Registered hook replay | Include memory, status, unstaged stat, and staged stat sections. | All four default sections rendered. | Pass |
| F5-R3-S3 | Safe selected diff | Selected diff replay | Render section 5 with selected diff body. | `## 5. selected git diff` and `+changed` appeared. | Pass |
| F5-R3-S4 | `--output=...` unsafe args | Unsafe write-boundary closure | Reject without traceback and without writing files. | Controlled error; digests unchanged. | Pass |
| F5-R3-S5 | `--output ...` unsafe args | Unsafe write-boundary closure | Reject without traceback and without writing files. | Controlled error; digests unchanged. | Pass |
| F5-R3-S6 | `-o ...` unsafe args | Unsafe write-boundary closure | Reject without traceback and without writing files. | Controlled error; digests unchanged. | Pass |
| F5-R3-S7 | `--ext-diff` unsafe args | Unsafe write-boundary closure | Reject without traceback and without external diff execution. | Controlled error; digests unchanged. | Pass |
| F5-R3-S8 | `--no-index` outside-root read | Project-local boundary | Reject without emitting outside file content. | Controlled unsafe-argument error; outside content absent. | Pass |
| F5-R3-S9 | Outside absolute pathspec | Project-local boundary | Reject outside-root absolute path without emitting outside file content. | Controlled outside-root path error; outside content absent. | Pass |
| F5-R3-S10 | Inside absolute pathspec | Project-local boundary | Allow selected absolute path when it resolves under project root. | Selected diff rendered. | Pass |
| F5-R3-S11 | Staged-only work | Staged-work closure | Surface staged-only changes in status and staged stat. | `M  staged.txt` and staged stat appeared. | Pass |
| F5-R3-S12 | Missing setup and non-git project | Fallback | Continue through packet sections with diagnostics. | Missing memory and git-error diagnostics rendered. | Pass |
| F5-R3-S13 | Nonexistent root | CLI robustness | Reject unresolved root with controlled CLI error. | Failed without traceback and reported the missing root. | Pass |
| F5-R3-S14 | Malformed diff args | CLI robustness | Reject malformed shell-style args without traceback. | Failed without traceback and reported invalid git args. | Pass |
| F5-R3-S15 | Feature 3 dry-run registration regression | Regression | Dry-run for a new project should still report hook creation without writing. | Returned `would_create`. | Pass |
| F5-R3-S16 | Feature 2 empty file regression | Regression | Empty file raw body remains empty while status carries `empty`. | `body == ""` and `status == "empty"`. | Pass |

#### Impact Assessment

| Functional area | Risk checked | Result | Assessment |
| --- | --- | --- | --- |
| Project-local read boundary | Selected diff args should not pull outside-root file content into the packet. | `--no-index` and outside absolute paths are rejected. | F5-R2-P1 closed. |
| Write-side Hook 2 boundary | Unsafe selected diff args should not mutate project files. | Tested write-oriented variants remain rejected. | No regression found. |
| Staged work visibility | Default packet should include staged-only work context. | Staged stat section still covers staged-only changes. | No regression found. |
| Registered Hook 2 execution | Hook should remain replayable from `.codex/hooks.json`. | Registered path executes successfully. | No negative impact found. |
| Fallback diagnostics | Hook should continue through missing/non-git states. | Missing setup and non-git diagnostics pass. | No negative impact found. |
| Prior feature behavior | Feature 2 and Feature 3 regressions should remain closed. | Empty raw-body and dry-run registration probes passed. | No negative impact found. |

#### Optimization Suggestions

| Priority | Suggestion | Rationale | Follow-up owner |
| --- | --- | --- | --- |
| P1 | Keep the unsafe diff argument and outside-root path tests as permanent coverage. | Feature 5's main risk is preserving selected read depth without letting selected args escape project-local boundaries. | Feature 5 maintenance. |
| P2 | Treat Hook 2 as accepted and start Hook 3 from a fresh review round/file. | Feature 5 has converged; goal/constraint drift belongs to the next hook. | Review queue. |
