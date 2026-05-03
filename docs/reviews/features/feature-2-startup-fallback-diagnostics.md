# Feature 2 Review: Startup Fallback Diagnostics

## Purpose

Upgrade `collect_project_context.py` from ordered text collection into a stable startup fallback diagnostic packet.

The collector should answer: for each startup source, what is its state, where did it come from, and what raw content or error should the agent see next?

## Scope

In scope:

- Preserve startup read order:
  `AGENTS.md -> formatted git log -> .codex/memory.md -> git status`.
- Add per-section diagnostics.
- Keep collecting later sections after earlier failures.
- Preserve raw content and large outputs.
- Respect agent-selected git log arguments without making them defaults.
- Add targeted scenario tests.

Out of scope:

- Memory freshness detection.
- Context summarization.
- Read-depth limits.
- Hook registration.
- Mutating `AGENTS.md` or `.codex/memory.md`.

## Diagnostic Contract

Each rendered section includes:

- `Status`
- `Source`
- optional `Detail`
- raw body

Status values:

- `ok`
- `empty`
- `missing`
- `path-conflict`
- `read-error`
- `git-error`

## Implementation Summary

- Extended `ContextSection` with `status`, `source`, and optional `detail`.
- Added `read_file_section` for file diagnostics.
- Added `run_git_section` for git diagnostics.
- Kept compatibility helpers `read_file` and `run_git` returning text bodies.
- Updated `render_context` to include diagnostic metadata before raw body.
- Updated `SKILL.md`, `docs/arbor-skill-design.md`, and `.codex/memory.md` to describe the fallback diagnostic contract.

## Scenario Coverage

Added or expanded coverage for:

- Missing `AGENTS.md`.
- Missing `.codex/memory.md`.
- Non-git project.
- Git repo with no commits.
- Empty git status.
- `AGENTS.md` path conflict.
- `.codex/memory.md` path conflict.
- File read failure.
- Large file content preservation.
- Agent-selected `--max-count=1` git log depth.
- Default git log remains unconstrained.
- Required rendered section order.
- Existing malformed `--git-log-args` regression coverage.

## Verification

- `python3 -m unittest tests/test_arbor_skill.py`: passed, 16 tests.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 skills/arbor/scripts/collect_project_context.py --root .`: passed and rendered all four sections with `Status` and `Source`.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f2-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py tests/test_arbor_skill.py`: passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f2-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: passed, 16 tests.
- `env COVERAGE_FILE=/private/tmp/arbor-f2-coverage conda run -n arbor python -m coverage report`: total coverage 87%.

## Acceptance Status

Accepted after Review Round 2.

Completed:

- Ordered startup flow.
- Fallback diagnostic states.
- No read-depth bottleneck.
- Large-output preservation.
- Agent-selected git log depth.

Not started:

- Memory freshness detection.
- Hook registration.

## Adversarial Review Rounds

### Round 1: Startup Diagnostic Contract Playback

#### Round Result Tab

| Round | Scope | Verdict | Problems | Probe pass rate | Convergence |
| --- | --- | --- | ---: | ---: | --- |
| F2-R1 | Feature 2 playback plus raw-preservation and fallback diagnostics probes | Changes requested | 1 | 11/12, 91.7% | Not converged |

#### Problems Found

| ID | Severity | Area | Finding | Evidence | Impact | Next-round acceptance gate |
| --- | --- | --- | --- | --- | --- | --- |
| F2-R1-P1 | P2 | Raw body preservation | Empty file sections replace the raw body with `(empty)`. | `read_file_section()` returns `ContextSection(..., body="(empty)", status="empty", ...)` for an empty `AGENTS.md`. | Feature 2 promises diagnostic metadata plus raw body preservation. Using `(empty)` as the body makes the rendered packet unable to distinguish an actual file containing `(empty)` from an empty file. | Keep `status="empty"` but preserve `body=""`, or add the marker outside the raw body. Add a regression test for empty file raw-body preservation. |

#### Test Coverage Table

| Test category | Cases/checks run | Category coverage | Passed | Failed | Pass rate | Result summary |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Developer validation playback | 6 checks | 6/6 planned checks, 100% | 6 | 0 | 100% | Replayed unittest, skill validation, py_compile, current collector smoke, coverage run, and coverage report. |
| Diagnostic status classification | 4 cases | 4/4 planned probes, 100% | 4 | 0 | 100% | Missing files, non-git fallback, empty git status, path conflicts, and decode errors classified as intended. |
| Raw body preservation | 3 cases | 3/3 planned probes, 100% | 2 | 1 | 66.7% | Leading/trailing whitespace and large files are preserved; empty file body is replaced with `(empty)`. |
| Git behavior regression | 3 cases | 3/3 planned probes, 100% | 3 | 0 | 100% | Default log remains unconstrained, selected `--max-count=1` is respected, and rendered metadata order remains stable. |
| CLI regression | 2 cases | 2/2 planned probes, 100% | 2 | 0 | 100% | Malformed `--git-log-args` remains controlled and emits no traceback. |
| Total adversarial probes | 12 cases | 12/12 planned probes, 100% | 11 | 1 | 91.7% | Excludes baseline playback checks. |

#### Baseline Playback Table

| Command/check | Status | Notes |
| --- | --- | --- |
| `python3 -m unittest tests/test_arbor_skill.py` | Pass | 16 tests passed. |
| `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor` | Pass | Skill is valid. |
| `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f2-review-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py tests/test_arbor_skill.py` | Pass | No compile errors. |
| `python3 skills/arbor/scripts/collect_project_context.py --root .` | Pass | Rendered all four sections with `Status` and `Source`. |
| `env COVERAGE_FILE=/private/tmp/arbor-f2-review-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py` | Pass | 16 tests passed under coverage. |
| `env COVERAGE_FILE=/private/tmp/arbor-f2-review-coverage conda run -n arbor python -m coverage report` | Pass | Total coverage 87%. |

#### Scenario Test Matrix

| Scenario ID | Scenario | Category | Expected behavior | Observed result | Status |
| --- | --- | --- | --- | --- | --- |
| F2-R1-S1 | Non-git project with both memory files missing | Diagnostic status | Return all four sections; classify files as `missing` and git sections as `git-error`. | Returned four sections with `missing`, `git-error`, `missing`, `git-error`. | Pass |
| F2-R1-S2 | Empty git repo with no files | Diagnostic status | Continue to `git status` after log failure; classify status as `empty`. | Returned `missing`, `git-error`, `missing`, `empty`. | Pass |
| F2-R1-S3 | `AGENTS.md` and memory path are directories | Diagnostic status | Classify both file sections as `path-conflict`. | Both file sections returned `path-conflict`. | Pass |
| F2-R1-S4 | UTF-8 decode failure | Diagnostic status | Classify as `read-error` and keep detail. | Returned `read-error` with decode detail. | Pass |
| F2-R1-S5 | File with leading/trailing whitespace and final newline | Raw preservation | Preserve exact file body. | Body matched the original string. | Pass |
| F2-R1-S6 | Empty file body | Raw preservation | Preserve empty raw body while status carries `empty`. | Body was `(empty)`. | Fail |
| F2-R1-S7 | Large file body | Raw preservation | Preserve all lines without truncation. | 500-line body preserved. | Pass |
| F2-R1-S8 | Four-commit repo with default log args | Git regression | Include all commits by default. | All four commits appeared. | Pass |
| F2-R1-S9 | Agent-selected `--max-count=1` | Git regression | Respect selected limit without making it default. | One commit appeared. | Pass |
| F2-R1-S10 | Rendered diagnostic packet order | Render regression | Keep section and metadata order stable. | Required section order and metadata positions held. | Pass |
| F2-R1-S11 | Malformed git-log args direct parser call | CLI regression | Controlled typed error. | Raised `ArgumentTypeError`. | Pass |
| F2-R1-S12 | Malformed git-log args CLI call | CLI regression | Exit non-zero with no traceback. | Exited code 2 with argparse error and no traceback. | Pass |

#### Impact Assessment

| Functional area | Risk checked | Result | Assessment |
| --- | --- | --- | --- |
| Fallback continuation | Earlier failures could block later sections. | Missing/path-conflict/git-error cases still return later sections. | No negative impact found. |
| Status taxonomy | New statuses could collapse distinct states. | `missing`, `path-conflict`, `read-error`, `git-error`, and `empty` were observed separately. | No negative impact found. |
| Raw file preservation | Diagnostic markers could replace source bytes. | Empty file body is replaced with `(empty)`. | Finding F2-R1-P1 open. |
| Read-depth freedom | Feature could impose a hidden git log limit. | Default log includes all commits; selected limit only applies when requested. | No negative impact found. |
| Prior CLI hardening | Feature 2 could regress malformed `--git-log-args` handling. | Controlled argparse error remains. | No negative impact found. |

#### Optimization Suggestions

| Priority | Suggestion | Rationale | Verification expected next round |
| --- | --- | --- | --- |
| P1 | Preserve empty raw file bodies as `""` and rely on `Status: empty` for diagnostics. | Keeps the raw body contract precise and avoids ambiguity with a file that literally contains `(empty)`. | Add direct unit test and rendered-output scenario for empty file raw-body preservation. |
| P2 | Add a test that distinguishes an empty file from a file containing `(empty)`. | This catches the ambiguity directly. | Empty file and literal-marker file produce different diagnostic/body combinations. |
| P2 | Keep `COVERAGE_FILE=/private/tmp/...` for future review commands. | This review left no project-root coverage artifact after cleanup. | Future review runs leave no `.coverage` in the repo root. |

## Developer Responses

### Response 1: Empty Raw Body Preservation

Review items addressed:

- F2-R1-P1: fixed. Empty file sections now keep `body=""` and rely on `status="empty"` for diagnostics.
- Optimization P1: fixed. The diagnostic marker no longer replaces the raw body.
- Optimization P2: fixed. Added a regression test that distinguishes an empty file from a file whose literal content is `(empty)`.
- Optimization P2: retained. Coverage commands continue to use `COVERAGE_FILE=/private/tmp/...`.

Implementation changes:

- Updated `read_file_section` so empty file content returns `ContextSection(..., body="", status="empty", ...)`.
- Updated `run_git_section` so empty git stdout also preserves `body=""` with `status="empty"`.
- Added tests:
  - `test_empty_file_body_is_preserved_as_empty`
  - `test_empty_file_and_literal_empty_marker_are_distinct`

Verification:

- `python3 -m unittest tests/test_arbor_skill.py`: passed, 18 tests.
- `python3 skills/arbor/scripts/collect_project_context.py --root .`: passed and rendered all four sections with diagnostic metadata.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f2-fix-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py tests/test_arbor_skill.py`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f2-r1-fix-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: passed, 18 tests.
- `env COVERAGE_FILE=/private/tmp/arbor-f2-r1-fix-coverage conda run -n arbor python -m coverage report`: total coverage 88%.

Closure status:

| Review item | Status | Evidence |
| --- | --- | --- |
| F2-R1-P1 empty raw body replacement | Fixed, pending re-review | Empty file body is preserved as `""`; literal `(empty)` content remains `status="ok"` and `body="(empty)"`. |
| Empty-vs-literal ambiguity | Fixed, pending re-review | Regression test covers both cases directly. |

### Round 2: Empty Raw Body Fix Playback

#### Round Result Tab

| Round | Scope | Verdict | Problems | Probe pass rate | Convergence |
| --- | --- | --- | ---: | ---: | --- |
| F2-R2 | F2-R1 closure playback plus raw-body, git, CLI, and initializer regression probes | Accepted | 0 new | 13/13, 100% | Converged for Feature 2 |

#### Problems Found

| ID | Severity | Area | Finding | Evidence | Impact | Next-round acceptance gate |
| --- | --- | --- | --- | --- | --- | --- |
| F2-R2-NF1 | None | Raw body preservation | No new issue found. F2-R1-P1 is closed. | Empty file sections now return `status="empty"` and `body=""`; a file whose literal content is `(empty)` returns `status="ok"` and `body="(empty)"`. | The diagnostic packet now preserves raw empty file bodies without ambiguity. | Keep the empty-file and literal-marker regression tests. |

#### Closure Table

| Prior item | Previous status | Round 2 result | Closure evidence | Status |
| --- | --- | --- | --- | --- |
| F2-R1-P1 empty raw body replacement | Open | Replayed and accepted | Direct probe confirmed `read_file_section()` returns `body=""` for an empty file. Rendered output includes `Status: empty` and does not inject `(empty)`. | Closed |
| Empty-vs-literal ambiguity | Open suggestion | Replayed and accepted | Direct probe confirmed empty file is `status=empty/body=""`, literal marker file is `status=ok/body="(empty)"`. | Closed |
| Coverage evidence | Pending follow-up | Replayed and accepted | `env COVERAGE_FILE=/private/tmp/arbor-f2-r2-coverage conda run -n arbor python -m coverage report` reports total coverage 88%. | Closed |

#### Test Coverage Table

| Test category | Cases/checks run | Category coverage | Passed | Failed | Pass rate | Result summary |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Developer validation playback | 6 checks | 6/6 planned checks, 100% | 6 | 0 | 100% | Replayed unittest, skill validation, py_compile, current collector smoke, coverage run, and coverage report. |
| Closure probes | 3 cases | 3/3 planned probes, 100% | 3 | 0 | 100% | Covered empty file body, rendered output without marker injection, and empty-vs-literal marker distinction. |
| Diagnostic regression | 5 cases | 5/5 planned probes, 100% | 5 | 0 | 100% | Empty git status, whitespace preservation, large file preservation, missing/git-error fallback, and path conflicts remain correct. |
| Git and CLI regression | 4 cases | 4/4 planned probes, 100% | 4 | 0 | 100% | Default git log, agent-selected git log depth, render order, and malformed git args remain correct. |
| Initializer regression | 1 case | 1/1 planned probe, 100% | 1 | 0 | 100% | Initializer dry-run remains unaffected. |
| Total incremental probes | 13 cases | 13/13 planned probes, 100% | 13 | 0 | 100% | Excludes baseline playback checks. |

#### Baseline Playback Table

| Command/check | Status | Notes |
| --- | --- | --- |
| `python3 -m unittest tests/test_arbor_skill.py` | Pass | 18 tests passed. |
| `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor` | Pass | Skill is valid. |
| `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f2-r2-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py tests/test_arbor_skill.py` | Pass | No compile errors. |
| `python3 skills/arbor/scripts/collect_project_context.py --root .` | Pass | Rendered all four sections with diagnostic metadata. |
| `env COVERAGE_FILE=/private/tmp/arbor-f2-r2-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py` | Pass | 18 tests passed under coverage. |
| `env COVERAGE_FILE=/private/tmp/arbor-f2-r2-coverage conda run -n arbor python -m coverage report` | Pass | Total coverage 88%. |

#### Scenario Test Matrix

| Scenario ID | Scenario | Category | Expected behavior | Observed result | Status |
| --- | --- | --- | --- | --- | --- |
| F2-R2-S1 | Empty file section | Closure | Preserve raw body as `""` with `status="empty"`. | `body=""`, `status="empty"`. | Pass |
| F2-R2-S2 | Rendered empty file section | Closure | Do not inject `(empty)` into rendered raw body. | Rendered output has `Status: empty` and no `(empty)` marker. | Pass |
| F2-R2-S3 | Empty file versus literal `(empty)` file | Closure | Keep the two states distinguishable. | Empty file is `empty/""`; literal file is `ok/"(empty)"`. | Pass |
| F2-R2-S4 | Empty git status | Diagnostic regression | Preserve empty git stdout as empty raw body with `status="empty"`. | `body=""`, `status="empty"`. | Pass |
| F2-R2-S5 | Leading/trailing whitespace file | Diagnostic regression | Preserve exact non-empty body. | Body matched original content. | Pass |
| F2-R2-S6 | Large file content | Diagnostic regression | Preserve without truncation. | 500-line body preserved. | Pass |
| F2-R2-S7 | Missing files in non-git project | Diagnostic regression | Keep collecting all four sections. | Returned `missing`, `git-error`, `missing`, `git-error`. | Pass |
| F2-R2-S8 | File path conflicts | Diagnostic regression | Classify file sections as `path-conflict`. | Both file sections classified correctly. | Pass |
| F2-R2-S9 | Default git log depth | Git regression | Remain unconstrained by default. | All four commits appeared. | Pass |
| F2-R2-S10 | Agent-selected git log depth | Git regression | Respect selected `--max-count=1`. | One commit appeared. | Pass |
| F2-R2-S11 | Rendered section order | Render regression | Preserve `AGENTS.md`, git log, memory, status order. | Required order preserved. | Pass |
| F2-R2-S12 | Malformed git-log args | CLI regression | Keep controlled error. | `ArgumentTypeError` retained. | Pass |
| F2-R2-S13 | Initializer dry-run | Initializer regression | Remain unaffected by collector changes. | Returned `would_create`, `would_create`; wrote no files. | Pass |

#### Impact Assessment

| Functional area | Risk checked | Result | Assessment |
| --- | --- | --- | --- |
| Empty raw file preservation | Fix could still insert a marker or lose the empty signal. | `body=""` and `status="empty"` are both preserved. | No negative impact found. |
| Literal marker content | Fix could classify a real `(empty)` file as empty. | Literal marker file remains `status="ok"`. | No negative impact found. |
| Git empty output | Matching change to `run_git_section` could break empty status diagnostics. | Empty git status is `status="empty"` with `body=""`. | No negative impact found. |
| Raw non-empty content | Fix could affect whitespace or large bodies. | Whitespace and large files remain exact/untruncated. | No negative impact found. |
| Prior collector behavior | Fix could regress fallback, git log depth, render order, or malformed arg handling. | All regression probes passed. | No negative impact found. |
| Initializer | Collector-only fix should not affect initializer behavior. | Dry-run remains unchanged. | No negative impact found. |

#### Optimization Suggestions

| Priority | Suggestion | Rationale | Verification expected next round |
| --- | --- | --- | --- |
| P2 | Keep the two empty-body regression tests as permanent Feature 2 coverage. | They protect the raw-body contract and empty-vs-literal distinction. | Future collector changes must keep both tests green. |
| P2 | Treat Feature 2 as accepted and move review focus to Feature 3 project hook registration when implementation starts. | The startup fallback diagnostic surface has converged, and memory freshness should be folded into the in-session hook rather than built as a standalone checker. | Feature 3 should get its own per-feature review file and adversarial matrix. |
