# Feature 3 Review: Project Hook Registration Skeleton

## Purpose

Track the design, implementation, tests, and review feedback for adding visible project-level Arbor hook registration.

## Development Target

Feature 3 should make hook behavior concrete in project files. It should not build a standalone memory freshness checker. Memory freshness belongs inside the in-session hook workflow as a prompt/process responsibility backed by project-local context.

The feature should:

- Add a project-level hook registration helper.
- Add or template visible project hook configuration.
- Register the three Arbor hook intents: session startup context load, in-session memory hygiene, and goal/constraint drift update.
- Keep all hook state project-local.
- Preserve unrelated existing project hooks.
- Keep the hook flow unconstrained by read-depth, commit-count, byte, or summary limits.

## Scope

In scope:

- `register_project_hooks.py` or equivalent project-level registration helper.
- A project hook template or contract file.
- Tests for idempotent registration, preservation, path safety, and hook intent coverage.
- `SKILL.md` updates explaining how `$arbor` registers project hooks.

Out of scope:

- A standalone semantic `check_memory_freshness.py`.
- User-global hook storage.
- Automatic commits or pushes.
- Any fixed read-depth policy for hook execution.

## Initial Review Questions

- Are hook files visibly project-local after registration?
- Does repeated registration avoid duplicate Arbor hook entries?
- Are unrelated hook entries preserved?
- Does the in-session hook give the agent enough process guidance to update `.codex/memory.md` without becoming a brittle language-understanding gate?
- Does the goal/constraint hook update only targeted `AGENTS.md` sections?

## Implementation Notes

Implemented:

- Added `skills/arbor/scripts/register_project_hooks.py`.
- Added `skills/arbor/references/project-hooks-template.md`.
- Updated `skills/arbor/SKILL.md` to register project hooks during startup/init workflows.
- Generated `.codex/hooks.json` for this project with three Arbor hook intents.

The generated project hook contract contains:

- `arbor.session_startup_context`
- `arbor.in_session_memory_hygiene`
- `arbor.goal_constraint_drift`

Implementation choices:

- Use `.codex/hooks.json` as the first visible project-local Arbor hook contract.
- Preserve unrelated hook entries by removing only known Arbor hook ids and appending the canonical Arbor entries.
- Keep registration idempotent: if the canonical file is already present, the script returns `exists`.
- Keep hook behavior declarative. The startup hook points to `collect_project_context.py`; the memory and AGENTS drift hooks point to Arbor workflows rather than standalone semantic checker scripts.
- Reject resolved write paths outside the project root, including `.codex` symlink escapes.
- Wrap parse, path, and write failures in controlled CLI errors.

## Validation Plan

- Unit tests for missing hook config, existing hook config, duplicate Arbor hooks, and path conflicts.
- Scenario test for invoking Arbor in a fresh project and observing visible hook artifacts.
- Scenario test for an existing project with non-Arbor hooks.
- Regression test that Feature 1 initializer and Feature 2 collector still pass.

## Feedback Log

### Design Adjustment

The standalone memory freshness checker was removed from the planned feature queue. Its useful behavior is now part of the in-session hook: when uncommitted work, conversation direction, or existing memory makes `.codex/memory.md` stale, the hook should guide the agent to refresh short-term memory using project-local context.

### Design Validation

- `python3 -m unittest tests/test_arbor_skill.py`: 18 tests passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- Text scan confirmed `check_memory_freshness.py` remains only as an explicit out-of-scope item in this review.

### Implementation Validation

Commands:

- `python3 -m unittest tests/test_arbor_skill.py`: 27 tests passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 skills/arbor/scripts/register_project_hooks.py --root /Users/shawn/Desktop/arbor --dry-run`: reported `would_create` before registration.
- `python3 skills/arbor/scripts/register_project_hooks.py --root /Users/shawn/Desktop/arbor`: created `.codex/hooks.json`.
- `python3 skills/arbor/scripts/register_project_hooks.py --root /Users/shawn/Desktop/arbor --dry-run`: reported `exists` after registration.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f3-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py tests/test_arbor_skill.py`: passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f3-coverage conda run -n arbor python -m coverage report`: total coverage 87%.

Scenario coverage:

- Missing hook config creates `.codex/hooks.json`.
- Dry-run does not write.
- Repeated registration is idempotent.
- Existing non-Arbor hooks and unknown top-level fields are preserved.
- Stale Arbor hook entries are replaced with canonical entries.
- `.codex` path conflict and `hooks.json` directory conflict are controlled errors.
- `.codex` symlink escape outside the project root is rejected.
- Invalid JSON config reports a controlled CLI error without traceback.
- Write-time `PermissionError` is converted into a controlled `HookRegistrationError`.

Developer response:

- During current-project registration, sandboxed write to `.codex/hooks.json` raised `PermissionError` and initially produced a traceback. The script now catches write errors and reports them through the same controlled error path as parse/path conflicts.

## Adversarial Review Rounds

### Round 1: Hook Registration Contract Playback

#### Round Result Tab

| Round | Scope | Verdict | Problems | Probe pass rate | Convergence |
| --- | --- | --- | ---: | ---: | --- |
| F3-R1 | Feature 3 playback plus registration, preservation, root-safety, and blast-radius probes | Changes requested | 2 | 12/15, 80% | Not converged |

#### Problems Found

| ID | Severity | Area | Finding | Evidence | Impact | Next-round acceptance gate |
| --- | --- | --- | --- | --- | --- | --- |
| F3-R1-P1 | P1 | Project root safety | `register_project_hooks()` accepts a nonexistent `--root` and creates hook state there. | A probe with `/private/tmp/.../typo-project` returned `created`, created the missing root directory, and wrote `.codex/hooks.json`. | A typo or unresolved project root can silently create a new fake project and register Arbor hook state outside any confirmed project. This conflicts with the design requirement to resolve the project root before hook action and to no-op/ask when no project root can be resolved. | Reject nonexistent roots with a controlled `HookRegistrationError` or require an explicit initialization mode. Add function and CLI tests for nonexistent root. |
| F3-R1-P2 | P2 | Unrelated hook preservation | `merge_arbor_hooks()` removes any hook whose `id` matches an Arbor hook id, even when `owner` is not `arbor`. | A config containing `{"id": "arbor.session_startup_context", "owner": "third-party"}` was rewritten to only the canonical Arbor hooks. | The feature promises preservation of existing non-Arbor hooks. Removing by id only can delete unrelated project hook entries that collide with Arbor ids or were imported from another system. | Preserve hooks unless both `owner == "arbor"` and `id` is canonical, or reject owner/id collisions with a controlled error. Add a regression test for non-Arbor hook id collisions. |

#### Test Coverage Table

| Test category | Cases/checks run | Category coverage | Passed | Failed | Pass rate | Result summary |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Developer validation playback | 6 checks | 6/6 planned checks, 100% | 6 | 0 | 100% | Replayed unittest, skill validation, current dry-run, py_compile, coverage run, and coverage report. |
| Hook contract | 3 cases | 3/3 planned probes, 100% | 3 | 0 | 100% | Current `.codex/hooks.json` contains canonical ids, project-local writes, and restricted AGENTS sections. |
| Registration behavior | 6 cases | 6/6 planned probes, 100% | 4 | 2 | 66.7% | Create, dry-run, idempotency, field preservation pass; stale-hook probe used an overbroad string check; non-Arbor same-id hook is removed. |
| Boundary and error handling | 4 cases | 4/4 planned probes, 100% | 3 | 1 | 75% | Symlink escape, invalid JSON CLI, and write errors are controlled; nonexistent root is accepted and created. |
| Blast-radius regression | 2 cases | 2/2 planned probes, 100% | 2 | 0 | 100% | Initializer dry-run and collector fallback behavior are unaffected. |
| Total adversarial probes | 15 cases | 15/15 planned probes, 100% | 12 | 3 | 80% | One failed registration probe was test-noise from matching the word `stale` inside canonical hook descriptions; the two actionable failures are F3-R1-P1 and F3-R1-P2. |

#### Baseline Playback Table

| Command/check | Status | Notes |
| --- | --- | --- |
| `python3 -m unittest tests/test_arbor_skill.py` | Pass | 27 tests passed. |
| `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor` | Pass | Skill is valid. |
| `python3 skills/arbor/scripts/register_project_hooks.py --root /Users/shawn/Desktop/arbor --dry-run` | Pass | Reports current hook file as `exists`. |
| `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f3-review-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py tests/test_arbor_skill.py` | Pass | No compile errors. |
| `env COVERAGE_FILE=/private/tmp/arbor-f3-review-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py` | Pass | 27 tests passed under coverage. |
| `env COVERAGE_FILE=/private/tmp/arbor-f3-review-coverage conda run -n arbor python -m coverage report` | Pass | Total coverage 87%. |

#### Scenario Test Matrix

| Scenario ID | Scenario | Category | Expected behavior | Observed result | Status |
| --- | --- | --- | --- | --- | --- |
| F3-R1-S1 | Current project hook file contract | Hook contract | Three canonical Arbor ids and project-local writes. | Contract matched expected ids, writes, and allowed AGENTS sections. | Pass |
| F3-R1-S2 | Missing hook config in existing temp project | Registration | Create `.codex/hooks.json`. | Returned `created` and wrote canonical hooks. | Pass |
| F3-R1-S3 | Dry-run registration | Registration | Report planned create without writing. | Returned `would_create`; wrote no file. | Pass |
| F3-R1-S4 | Repeated registration | Registration | Return `exists` and keep file stable. | Idempotency passed. | Pass |
| F3-R1-S5 | Existing custom field and custom hook | Registration | Preserve unknown top-level fields and unrelated hook. | Preserved both. | Pass |
| F3-R1-S6 | Stale Arbor hook replacement | Registration | Replace stale Arbor hook with canonical hook. | Replacement worked, but one probe overmatched the word `stale` in canonical descriptions. | Pass |
| F3-R1-S7 | Non-Arbor hook with Arbor id collision | Registration | Preserve or explicitly reject non-Arbor collision. | Entry was silently removed. | Fail |
| F3-R1-S8 | `.codex` symlink escape | Boundary | Reject path outside project root. | Raised controlled `HookRegistrationError`. | Pass |
| F3-R1-S9 | Nonexistent project root | Boundary | Reject unresolved project root or require explicit init. | Created missing root and `.codex/hooks.json`. | Fail |
| F3-R1-S10 | Invalid JSON config via CLI | Boundary | Controlled CLI error, no traceback. | Exited code 2 with `cannot parse`, no traceback. | Pass |
| F3-R1-S11 | Write-time permission error | Boundary | Controlled `HookRegistrationError`. | Raised controlled error. | Pass |
| F3-R1-S12 | Initializer dry-run after hook changes | Blast radius | Existing initializer behavior unaffected. | Returned `would_create`, `would_create`. | Pass |
| F3-R1-S13 | Collector fallback after hook changes | Blast radius | Existing fallback statuses unaffected. | Returned `missing`, `git-error`, `missing`, `git-error`. | Pass |

#### Impact Assessment

| Functional area | Risk checked | Result | Assessment |
| --- | --- | --- | --- |
| Project-local hook contract | Hook file should be visible and scoped to the current project. | Current project hook file matches canonical three-hook contract. | No negative impact found. |
| Root resolution safety | Registration should not create hook state for unresolved roots. | Nonexistent root is accepted and created. | Finding F3-R1-P1 open. |
| Unrelated hook preservation | Existing non-Arbor hooks should be preserved. | Non-Arbor hook with Arbor id collision is silently deleted. | Finding F3-R1-P2 open. |
| Idempotency | Repeated registration should not duplicate Arbor hooks. | Re-registration returns `exists` and file is stable. | No negative impact found. |
| Error handling | Parse, path, and write failures should avoid tracebacks. | Invalid JSON, symlink escape, and write errors are controlled. | No negative impact found. |
| Feature 1/2 regression | Hook work should not affect initializer or collector. | Initializer dry-run and collector fallback probes passed. | No negative impact found. |

#### Optimization Suggestions

| Priority | Suggestion | Rationale | Verification expected next round |
| --- | --- | --- | --- |
| P1 | Reject nonexistent `--root` unless there is an explicit project initialization mode. | Hook registration is supposed to operate on a resolved current project, not create one from a typo. | Function and CLI tests prove nonexistent roots fail without creating directories. |
| P2 | Filter stale Arbor hooks by both canonical id and `owner == "arbor"`, or reject id/owner collisions explicitly. | This aligns implementation with the promise to preserve non-Arbor hooks. | Regression test with `owner: third-party` and `id: arbor.session_startup_context`. |
| P3 | Tighten stale-hook tests to assert the old stale field is removed from the replaced hook rather than scanning all hook JSON for the word `stale`. | The word appears in canonical hook descriptions, so broad string scans are noisy. | Test inspects specific replaced hook fields. |

### Developer Response: Round 1 Fixes

Changes made:

- Fixed F3-R1-P1 by rejecting nonexistent project roots in `hook_config_path()`.
- Added function coverage proving `register_project_hooks()` raises `HookRegistrationError` for a nonexistent root and does not create the directory.
- Added CLI coverage proving nonexistent `--root` exits through argparse error handling, produces no traceback, and does not create the directory.
- Fixed F3-R1-P2 by preserving hooks with canonical Arbor ids unless `owner == "arbor"`.
- Added regression coverage for a non-Arbor hook with `id: arbor.session_startup_context` and `owner: third-party`.
- Addressed F3-R1-P3 by asserting the replaced canonical Arbor hook no longer has the old `stale` field instead of scanning rendered JSON for the word `stale`.

Validation:

- `python3 -m unittest tests/test_arbor_skill.py`: 29 tests passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 skills/arbor/scripts/register_project_hooks.py --root /Users/shawn/Desktop/arbor --dry-run`: reported `exists`.
- `python3 skills/arbor/scripts/register_project_hooks.py --root /private/tmp/arbor-typo-root-check`: exited with controlled `project root does not exist` error.
- `test ! -e /private/tmp/arbor-typo-root-check`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f3-r1-fix-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py tests/test_arbor_skill.py`: passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f3-r1-fix-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 29 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f3-r1-fix-coverage conda run -n arbor python -m coverage report`: total coverage 87%.

Closure assessment:

- F3-R1-P1: fixed.
- F3-R1-P2: fixed by preservation policy rather than collision rejection.
- F3-R1-P3: fixed in tests.

### Round 2: Hook Registration Fix Playback

#### Round Result Tab

| Round | Scope | Verdict | Problems | Probe pass rate | Convergence |
| --- | --- | --- | ---: | ---: | --- |
| F3-R2 | F3-R1 closure playback plus registration, boundary, contract, and blast-radius probes | Accepted | 0 new | 14/14, 100% | Converged for Feature 3 |

#### Problems Found

| ID | Severity | Area | Finding | Evidence | Impact | Next-round acceptance gate |
| --- | --- | --- | --- | --- | --- | --- |
| F3-R2-NF1 | None | Project root safety | No new issue found. F3-R1-P1 is closed. | Function path raises `HookRegistrationError: project root does not exist`; CLI exits code 2, emits no traceback, and does not create the typo root. | Hook registration now requires a resolved existing project root. | Keep function and CLI nonexistent-root tests. |
| F3-R2-NF2 | None | Unrelated hook preservation | No new issue found. F3-R1-P2 is closed. | A non-Arbor hook with `id=arbor.session_startup_context` and `owner=third-party` is preserved, while canonical Arbor hooks are appended once. | Non-Arbor hook entries are no longer silently deleted on id collision. | Keep owner/id collision regression test. |

#### Closure Table

| Prior item | Previous status | Round 2 result | Closure evidence | Status |
| --- | --- | --- | --- | --- |
| F3-R1-P1 nonexistent root accepted | Open | Replayed and accepted | Function and CLI probes reject nonexistent roots without creating directories. | Closed |
| F3-R1-P2 non-Arbor same-id hook removed | Open | Replayed and accepted | Non-Arbor same-id hook remains in `hooks.json`; canonical Arbor hooks are appended once. | Closed |
| F3-R1-P3 stale test noise | Open suggestion | Replayed and accepted | Stale Arbor hook test now inspects the replaced hook directly rather than scanning all JSON text. | Closed |

#### Test Coverage Table

| Test category | Cases/checks run | Category coverage | Passed | Failed | Pass rate | Result summary |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Developer validation playback | 7 checks | 7/7 planned checks, 100% | 7 | 0 | 100% | Replayed unittest, skill validation, current dry-run, nonexistent-root CLI, noncreation check, py_compile, coverage run, and coverage report. |
| Closure probes | 4 cases | 4/4 planned probes, 100% | 4 | 0 | 100% | Covered function and CLI nonexistent-root rejection plus non-Arbor same-id preservation and canonical append behavior. |
| Registration regression | 4 cases | 4/4 planned probes, 100% | 4 | 0 | 100% | Existing-root create, dry-run, idempotency, and precise stale-Arbor replacement still pass. |
| Boundary regression | 3 cases | 3/3 planned probes, 100% | 3 | 0 | 100% | Symlink escape, invalid JSON CLI, and write errors remain controlled. |
| Contract and blast-radius regression | 3 cases | 3/3 planned probes, 100% | 3 | 0 | 100% | Current project hook contract, initializer dry-run, and collector fallback remain correct. |
| Total incremental probes | 14 cases | 14/14 planned probes, 100% | 14 | 0 | 100% | Excludes baseline playback checks. |

#### Baseline Playback Table

| Command/check | Status | Notes |
| --- | --- | --- |
| `python3 -m unittest tests/test_arbor_skill.py` | Pass | 29 tests passed. |
| `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor` | Pass | Skill is valid. |
| `python3 skills/arbor/scripts/register_project_hooks.py --root /Users/shawn/Desktop/arbor --dry-run` | Pass | Reports current hook file as `exists`. |
| `python3 skills/arbor/scripts/register_project_hooks.py --root /private/tmp/arbor-typo-root-check` | Pass | Exits code 2 with controlled `project root does not exist` error. |
| `test ! -e /private/tmp/arbor-typo-root-check` | Pass | CLI did not create the typo root. |
| `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f3-r2-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py tests/test_arbor_skill.py` | Pass | No compile errors. |
| `env COVERAGE_FILE=/private/tmp/arbor-f3-r2-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py` | Pass | 29 tests passed under coverage. |
| `env COVERAGE_FILE=/private/tmp/arbor-f3-r2-coverage conda run -n arbor python -m coverage report` | Pass | Total coverage 87%. |

#### Scenario Test Matrix

| Scenario ID | Scenario | Category | Expected behavior | Observed result | Status |
| --- | --- | --- | --- | --- | --- |
| F3-R2-S1 | Nonexistent root via function | Closure | Controlled error and no directory creation. | Raised `HookRegistrationError`; root remained absent. | Pass |
| F3-R2-S2 | Nonexistent root via CLI | Closure | Exit code 2, no traceback, no directory creation. | Exited code 2 with `project root does not exist`; root remained absent. | Pass |
| F3-R2-S3 | Non-Arbor same-id hook | Closure | Preserve third-party hook and append canonical Arbor hooks. | Third-party hook preserved; three Arbor hooks appended once. | Pass |
| F3-R2-S4 | Existing root with missing hook config | Registration regression | Create canonical hook file. | Returned `created`; wrote three canonical hooks. | Pass |
| F3-R2-S5 | Dry-run registration | Registration regression | Report create without writing. | Returned `would_create`; wrote no file. | Pass |
| F3-R2-S6 | Repeated registration | Registration regression | Return `exists` and keep file stable. | Idempotency held. | Pass |
| F3-R2-S7 | Stale Arbor hook replacement | Registration regression | Replace only stale Arbor hook and preserve custom data. | Custom hook preserved; replaced Arbor hook has no stale field. | Pass |
| F3-R2-S8 | `.codex` symlink escape | Boundary regression | Reject outside-project target. | Raised controlled `HookRegistrationError`. | Pass |
| F3-R2-S9 | Invalid JSON config via CLI | Boundary regression | Controlled CLI error with no traceback. | Exited code 2 with `cannot parse`; no traceback. | Pass |
| F3-R2-S10 | Write-time permission error | Boundary regression | Controlled hook registration error. | Raised `HookRegistrationError: cannot write ...`. | Pass |
| F3-R2-S11 | Current project hook contract | Contract regression | Current `.codex/hooks.json` remains canonical. | Three Arbor ids match canonical order. | Pass |
| F3-R2-S12 | Initializer dry-run | Blast radius | Feature 1 initializer behavior unaffected. | Returned `would_create`, `would_create`. | Pass |
| F3-R2-S13 | Collector fallback | Blast radius | Feature 2 fallback statuses unaffected. | Returned `missing`, `git-error`, `missing`, `git-error`. | Pass |

#### Impact Assessment

| Functional area | Risk checked | Result | Assessment |
| --- | --- | --- | --- |
| Project root safety | Fix could still create typo paths or leak traceback. | Function and CLI reject missing roots and create nothing. | No negative impact found. |
| Hook preservation | Owner-aware filter could duplicate or drop hooks. | Third-party same-id hook is preserved and canonical Arbor hooks are appended once. | No negative impact found. |
| Stale Arbor replacement | Owner-aware filter could fail to replace old Arbor hooks. | Stale Arbor hook is replaced precisely. | No negative impact found. |
| Idempotency | Preservation change could make re-registration unstable. | Re-registration returns `exists` and file content is stable. | No negative impact found. |
| Boundary errors | Root checks could affect existing symlink/parse/write handling. | Symlink escape, invalid JSON, and write errors remain controlled. | No negative impact found. |
| Feature 1/2 regression | Hook fixes should not affect initializer or collector. | Initializer dry-run and collector fallback still pass. | No negative impact found. |

#### Optimization Suggestions

| Priority | Suggestion | Rationale | Verification expected next round |
| --- | --- | --- | --- |
| P2 | Treat Feature 3 as accepted and move review focus to Feature 4 goal/constraint drift when implementation starts. | Hook registration contract and boundary behavior have converged. | Feature 4 should get its own per-feature review file and adversarial matrix. |
| P3 | Consider documenting the owner/id collision policy in `project-hooks-template.md`. | The code now preserves non-Arbor same-id hooks; documenting the policy avoids future ambiguity. | Template explicitly says only `owner=arbor` canonical hooks are replaced. |

### Planning Correction

The next implementation feature is not the goal/constraint drift hook. Hook execution should proceed one hook at a time. Feature 4 is now the session startup hook execution path for `arbor.session_startup_context`; the in-session memory hook and goal/constraint drift hook should wait for later features.
