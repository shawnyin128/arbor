# Feature 6 Review: AGENTS Drift Hook

## Purpose

Turn the registered `arbor.goal_constraint_drift` intent into a concrete Hook 3 execution path. Hook 3 should emit project-local context that helps the running agent decide whether `AGENTS.md` needs a durable update, without automatically editing either `AGENTS.md` or `.codex/memory.md`.

## Scope

In scope:

- Add an executable `run_agents_guide_drift_hook.py` wrapper.
- Update hook registration so `arbor.goal_constraint_drift` points to the wrapper.
- Include `AGENTS.md`, `git status --short`, and optional agent-selected project-local docs in the packet.
- Provide a repeatable `--doc` optional argument channel.
- Reject selected docs outside the resolved project root.
- Keep missing files and path conflicts as diagnostics when they are project-local.
- Add unit and scenario coverage for the registered Hook 3 path.

Out of scope:

- Automatic semantic detection of goal or constraint drift.
- Automatic edits to `AGENTS.md`.
- Updates to `.codex/memory.md`.
- Any user-global hook state or memory state.

## Design Notes

Hook 3 follows the same packet-generation pattern as Hook 1 and Hook 2. The script fixes collection order and project boundaries, then leaves semantic judgment to the running agent plus current conversation context.

Packet order:

1. `AGENTS.md`
2. `git status --short`
3. Each `--doc` selected by the agent, in argument order

Agent instruction boundary:

- Edit only `Project Goal`, `Project Constraints`, or `Project Map` if a durable update is needed.
- Keep current uncommitted progress and transient implementation notes out of `AGENTS.md`.
- Do not update `.codex/memory.md` from this hook.

## Implementation Notes

- Added `skills/arbor/scripts/run_agents_guide_drift_hook.py`.
- Updated `skills/arbor/scripts/register_project_hooks.py` to register Hook 3 as a `skill-script` entrypoint.
- Changed the documented Hook 3 optional argument channel to repeatable `--doc`.
- Kept hidden `--doc-paths` compatibility in the script for older local hook files while newly registered hooks use `--doc`.
- Updated `skills/arbor/references/project-hooks-template.md`, `docs/arbor-skill-design.md`, and the review index.
- Updated the current project's `.codex/hooks.json`; this is this repo's project-level hook contract, not the future plugin payload.

## Validation

- `python3 -m unittest tests/test_arbor_skill.py`: 55 tests passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 skills/arbor/scripts/register_project_hooks.py --root /Users/shawn/Desktop/arbor --dry-run`: reported Arbor hooks already registered.
- `python3 skills/arbor/scripts/run_agents_guide_drift_hook.py --root /Users/shawn/Desktop/arbor --doc docs/arbor-skill-design.md`: emitted a packet with `AGENTS.md`, git status, and the selected design doc.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f6-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py tests/test_arbor_skill.py`: passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f6-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 55 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f6-coverage conda run -n arbor python -m coverage report`: total coverage 87%.

## Scenario Coverage

- Registered Hook 3 command includes repeated selected docs in order.
- Absolute selected docs under the project root are allowed.
- Absolute selected docs outside the project root are rejected without leaking file contents.
- Missing selected project-local docs are surfaced as `Status: missing`.
- Directory-selected docs are surfaced as `Status: path-conflict`.
- Registered Hook 3 does not write `.codex/memory.md` or `AGENTS.md`.
- CLI errors for malformed legacy doc paths and nonexistent roots are controlled and traceback-free.

## Developer Response

Feature 6 is implemented and self-tested. The hook intentionally emits an AGENTS drift packet instead of trying to perform language-level drift detection itself, matching the Arbor principle that the skill controls workflow order and project boundaries rather than becoming the reasoning bottleneck.

## Adversarial Review Rounds

### Round 1: AGENTS Drift Hook Replay

#### Round Result Tab

| Round | Scope | Verdict | Problems | Probe pass rate | Convergence |
| --- | --- | --- | ---: | ---: | --- |
| F6-R1 | Registered Hook 3 replay plus selected docs, project-local boundaries, no-write behavior, fallback, CLI, and prior-feature regression probes | Accepted | 0 | 28/28, 100% | Converged for Feature 6 |

#### Problems Found

| ID | Severity | Area | Finding | Evidence | Impact | Next-round acceptance gate |
| --- | --- | --- | --- | --- | --- | --- |
| F6-R1-NF1 | None | Hook 3 execution | No new review finding. | Developer baseline checks passed; independent adversarial probes passed 28/28. | Feature 6 can be treated as accepted. | No additional Feature 6 gate. Move to feature-level Arbor review. |

#### Test Coverage Table

| Test category | Cases/checks run | Category coverage | Passed | Failed | Pass rate | Result summary |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Developer baseline playback | 7 checks | 7/7 planned checks, 100% | 7 | 0 | 100% | Replayed unit tests, skill validation, hook registration dry-run, direct Hook 3 execution with a selected doc, py_compile, coverage run, and coverage report. |
| Hook contract | 5 probes | 5/5 planned probes, 100% | 5 | 0 | 100% | Registered Hook 3 points to the wrapper, keeps root placeholder, exposes repeatable `--doc`, matches canonical registration, and declares allowed AGENTS sections. |
| Registered hook replay | 5 probes | 5/5 planned probes, 100% | 5 | 0 | 100% | Parsed `.codex/hooks.json`, executed the registered command, included AGENTS/status sections, surfaced untracked work, and rendered instruction boundaries. |
| Selected docs replay | 3 probes | 3/3 planned probes, 100% | 3 | 0 | 100% | Repeated `--doc` args preserve order and include raw doc bodies. |
| Project-local docs | 3 probes | 3/3 planned probes, 100% | 3 | 0 | 100% | Absolute docs under root are allowed; missing and directory-selected project-local docs render diagnostics. |
| Boundary probes | 4 probes | 4/4 planned probes, 100% | 4 | 0 | 100% | Outside absolute docs, relative traversal, symlink escape, and legacy `--doc-paths` outside docs are rejected without leaking file bodies. |
| No-write and fallback | 3 probes | 3/3 planned probes, 100% | 3 | 0 | 100% | Registered Hook 3 does not mutate `.codex/memory.md` or `AGENTS.md`; missing setup/non-git projects return diagnostics. |
| CLI robustness | 2 probes | 2/2 planned probes, 100% | 2 | 0 | 100% | Malformed legacy doc paths and nonexistent roots fail with controlled errors and no traceback. |
| Regression coverage | 3 probes | 3/3 planned probes, 100% | 3 | 0 | 100% | Feature 3 dry-run registration, Feature 2 empty raw-body preservation, and Feature 5 outside selected diff rejection remain intact. |
| Total adversarial probes | 28 probes | 28/28 planned probes, 100% | 28 | 0 | 100% | Excludes baseline playback checks. |

#### Baseline Playback Table

| Command/check | Status | Notes |
| --- | --- | --- |
| `python3 -m unittest tests/test_arbor_skill.py` | Pass | 55 tests passed. |
| `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor` | Pass | Skill is valid. |
| `python3 skills/arbor/scripts/register_project_hooks.py --root /Users/shawn/Desktop/arbor --dry-run` | Pass | Reported `exists`. |
| `python3 skills/arbor/scripts/run_agents_guide_drift_hook.py --root /Users/shawn/Desktop/arbor --doc docs/arbor-skill-design.md` | Pass | Rendered AGENTS drift packet with selected design doc. |
| `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f6-r1-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py tests/test_arbor_skill.py` | Pass | No compile errors. |
| `env COVERAGE_FILE=/private/tmp/arbor-f6-r1-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py` | Pass | 55 tests passed under coverage. |
| `env COVERAGE_FILE=/private/tmp/arbor-f6-r1-coverage conda run -n arbor python -m coverage report` | Pass | Total coverage 87%. |

#### Scenario Test Matrix

| Scenario ID | Scenario | Category | Expected behavior | Observed result | Status |
| --- | --- | --- | --- | --- | --- |
| F6-R1-S1 | Current hook contract parse | Hook contract | `arbor.goal_constraint_drift` is present and executable through the wrapper. | Hook script is `scripts/run_agents_guide_drift_hook.py`. | Pass |
| F6-R1-S2 | Repeatable doc channel | Hook contract | Registered hook exposes repeatable `--doc`. | `optional_args` contains `--doc` with `repeatable: true`. | Pass |
| F6-R1-S3 | Allowed AGENTS sections | Hook contract | Contract limits durable updates to goal, constraints, and map sections. | `allowed_sections` matches `Project Goal`, `Project Constraints`, `Project Map`. | Pass |
| F6-R1-S4 | Default registered Hook 3 replay | Registered hook replay | Exit cleanly and include AGENTS plus git status. | Both default sections rendered. | Pass |
| F6-R1-S5 | Instruction boundary | Registered hook replay | Tell the agent to update only allowed AGENTS sections and not memory. | Instruction text rendered. | Pass |
| F6-R1-S6 | Untracked work status | Registered hook replay | Surface untracked project work as supporting evidence. | `?? pending.txt` appeared. | Pass |
| F6-R1-S7 | Repeated selected docs | Selected docs replay | Preserve selected doc order and raw bodies. | Architecture doc rendered before constraints doc with raw body text. | Pass |
| F6-R1-S8 | Absolute selected doc under root | Project-local docs | Allow project-local absolute docs. | Selected doc body rendered. | Pass |
| F6-R1-S9 | Missing selected project-local doc | Project-local docs | Render diagnostic instead of aborting. | `Status: missing` rendered. | Pass |
| F6-R1-S10 | Directory selected as project-local doc | Project-local docs | Render path-conflict diagnostic. | `Status: path-conflict` rendered. | Pass |
| F6-R1-S11 | Outside absolute selected doc | Boundary | Reject outside-root doc without leaking body. | Controlled outside-root error; body absent. | Pass |
| F6-R1-S12 | Relative traversal selected doc | Boundary | Reject traversal outside root without leaking body. | Controlled outside-root error; body absent. | Pass |
| F6-R1-S13 | Symlink escaping root | Boundary | Reject symlink-resolved outside-root docs. | Controlled outside-root error; body absent. | Pass |
| F6-R1-S14 | Legacy `--doc-paths` outside doc | Boundary | Preserve compatibility without weakening boundary. | Controlled outside-root error; body absent. | Pass |
| F6-R1-S15 | Registered no-write behavior | No-write | Do not mutate `.codex/memory.md` or `AGENTS.md`. | SHA-256 digests unchanged. | Pass |
| F6-R1-S16 | Missing setup and non-git project | Fallback | Continue through AGENTS/status/doc diagnostics. | Missing and git-error diagnostics rendered. | Pass |
| F6-R1-S17 | Malformed legacy doc paths | CLI robustness | Reject malformed shell-style legacy paths without traceback. | Controlled `invalid doc paths` error. | Pass |
| F6-R1-S18 | Nonexistent root | CLI robustness | Reject unresolved root without traceback. | Controlled missing-root error. | Pass |
| F6-R1-S19 | Feature 3 dry-run registration regression | Regression | Dry-run for a new project should still report hook creation without writing. | Returned `would_create`. | Pass |
| F6-R1-S20 | Feature 2 empty file regression | Regression | Empty file raw body remains empty while status carries `empty`. | `body == ""` and `status == "empty"`. | Pass |
| F6-R1-S21 | Feature 5 outside selected diff regression | Regression | Hook 2 should still reject outside selected diff paths. | Controlled outside-root path error. | Pass |

#### Impact Assessment

| Functional area | Risk checked | Result | Assessment |
| --- | --- | --- | --- |
| Registered Hook 3 execution | Hook should be replayable from `.codex/hooks.json`. | Registered path executes successfully. | No negative impact found. |
| AGENTS update boundary | Hook should guide only durable `AGENTS.md` section updates. | Allowed sections are explicit in contract and instructions. | No negative impact found. |
| Project-local read boundary | Selected docs should stay under resolved project root. | Absolute outside, traversal, symlink escape, and legacy outside docs are rejected. | No negative impact found. |
| No-write behavior | Hook 3 should emit a packet and not mutate memory or AGENTS. | Digest check passed. | No negative impact found. |
| Fallback diagnostics | Missing setup, non-git state, missing docs, and directories should not block packet generation when project-local. | Diagnostics rendered. | No negative impact found. |
| Prior feature behavior | Feature 2, Feature 3, and Feature 5 regressions should remain closed. | Regression probes passed. | No negative impact found. |

#### Optimization Suggestions

| Priority | Suggestion | Rationale | Follow-up owner |
| --- | --- | --- | --- |
| P1 | Keep outside-doc, traversal, and symlink escape tests as permanent coverage. | Hook 3's main safety risk is accidentally reading durable context from outside the project root. | Feature 6 maintenance. |
| P2 | Proceed to feature-level review of the full Arbor flow. | All three hook entrypoints now have accepted executable review rounds. | Review queue. |
