# Feature 1 Review: Arbor Initializer And Startup Flow MVP

## Purpose

Build the first usable Arbor skill: initialize project-local memory files and collect startup context in the required order.

## Scope

In scope:

- Scaffold `skills/arbor`.
- Add `.codex/memory.md` and `AGENTS.md` templates.
- Add initializer script.
- Add first startup context collector.
- Add unit and scenario tests.
- Initialize the current project with `AGENTS.md` and `.codex/memory.md`.

Out of scope:

- Memory freshness detection.
- Real hook registration.
- Context summarization or read-depth limits.

## Deliverables

- `skills/arbor/SKILL.md`
- `skills/arbor/agents/openai.yaml`
- `skills/arbor/references/memory-template.md`
- `skills/arbor/references/agents-template.md`
- `skills/arbor/scripts/init_project_memory.py`
- `skills/arbor/scripts/collect_project_context.py`
- `tests/test_arbor_skill.py`
- Current-project `AGENTS.md`
- Current-project `.codex/memory.md`

## Implementation Summary

- Generated the skill scaffold with `skill-creator`.
- Renamed the skill to `arbor` to match the future plugin name.
- Wrote the Arbor workflow into `SKILL.md`.
- Added project-local templates for durable `AGENTS.md` and short-term `.codex/memory.md`.
- Revised `.codex/memory.md` to match the user's preferred short-term memory style: pre-triage observations only, no duplication with durable docs, and under 30 lines when practical.
- Implemented `init_project_memory.py` with non-overwrite initialization, dry-run support, and controlled path-conflict errors.
- Implemented the first `collect_project_context.py` with ordered context collection and agent-selected `--git-log-args`.
- Initialized this repo's `AGENTS.md` and `.codex/memory.md`.

## Review Rounds

### Round 1: Feature 1 Playback And Incremental Probes

Verdict: developer response required.

Findings:

| ID | Severity | Finding | Resolution |
| --- | --- | --- | --- |
| R1-P1 | Medium | Malformed `--git-log-args` leaked a Python traceback from `shlex.split`. | Fixed by converting `ValueError` to `argparse.ArgumentTypeError` and calling `parser.error(...)`. |
| R1-P2 | Low | The review environment snapshot was stale and not labeled historical. | Fixed by labeling the initial snapshot historical and adding dated current-round observations. |

Key probes:

- Initializer empty project, existing files, dry-run, partial initialization, and `.codex` conflict.
- Collector non-git, no-commit git repo, multi-commit git repo, uncommitted status, rendered order, and malformed CLI args.

### Round 2: Developer Response Playback

Verdict: accepted.

Closure:

- R1-P1 closed: malformed `--git-log-args` exits with code 2 and a concise argparse error, no traceback.
- R1-P2 closed: review file distinguishes historical and current environment state.
- Coverage gap closed for the round by using `conda run -n arbor`.
- `.codex` path-conflict CLI polish deferred to initializer hardening.

### Round 3: Initializer Conflict Review

Verdict: accepted.

Closure:

- Deferred `.codex` path-conflict CLI polish closed.
- `InitError` added for controlled initializer conflict handling.
- Function and CLI tests cover `.codex` parent-file conflict and `AGENTS.md` directory conflict.

## Developer Responses

### Response 1: CLI Error Handling And Review Snapshot

Implementation changes:

- `parse_git_log_args` wraps malformed shell-style strings in `argparse.ArgumentTypeError`.
- CLI uses `parser.error(...)` for malformed `--git-log-args`.
- Added direct parser and subprocess CLI tests.
- Updated session memory to remove the resolved coverage gap and record Feature 2 as collector-hardening first.

Verification:

- `python3 -m unittest tests/test_arbor_skill.py`: passed, 8 tests.
- Malformed CLI probe: exit code 2, concise argparse error, no traceback.
- `quick_validate.py skills/arbor`: passed.
- `py_compile`: passed.
- Coverage under `conda run -n arbor`: total 83%.

### Response 2: Initializer Path-Conflict Polish

Implementation changes:

- Added `InitError`.
- `ensure_file` now reports:
  - output path exists as a directory;
  - parent path exists but is not a directory.
- Initializer CLI catches `InitError` and reports a concise argparse error.
- Added three initializer conflict tests.

Verification:

- `python3 -m unittest tests/test_arbor_skill.py`: passed, 11 tests.
- `quick_validate.py skills/arbor`: passed.
- `py_compile`: passed.
- Initializer conflict CLI probe: exit code 2, concise argparse error, no traceback.
- Coverage with `COVERAGE_FILE=/private/tmp/arbor-opt-coverage`: total 83%.

## Current Status

Accepted.

Permanent regression coverage:

- Malformed `--git-log-args` parser and CLI tests.
- Initializer path-conflict function and CLI tests.
- Existing-file preservation and dry-run tests.

Deferred:

- Memory freshness detection.
- Hook registration.
