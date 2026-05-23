# Real Workflow Chain Review

This document defines the required real-runtime review cases for Arbor workflow changes.
It is not a fixture baseline and not a prose-only checklist. A case passes only when a
real Codex or Claude Code process loads the Arbor plugin, runs the relevant skill path,
and an external harness verifies the rendered output plus git and file side effects.

## Review Principle

Static checks and JSONL fixture checks are preflight only. They must not be reported as
"full chain" validation.

Full-chain validation requires all of these:

- a temporary git repository created for the case;
- the local Arbor plugin loaded through the runtime under test;
- a real `codex exec` or `claude -p --plugin-dir` process;
- a user prompt that enters the workflow from the same surface a user would use;
- captured final rendered response text;
- captured git status, git log, changed files, and workflow artifacts;
- assertions over route trace, state changes, side effects, and readability.

Rendered-output assertions should follow `rendered-checkpoint-protocol.md`.
Reject raw workflow schema, route assignments, terminal-state labels,
unexplained internal ids, and missing skill-specific visible sections in the
captured `final-response.md`. These checks protect workflow readability; they do
not prescribe implementation approach or apply to direct answers that correctly
stay outside Arbor workflow.

Outcome evaluation should inspect final state, checkpoint outcomes, rendered
output, review evidence, process state, git/file side effects, realistic replay,
trace evidence, and weak-pass gaps before demanding exact path matching. Exact
route or turn-by-turn evidence is required only when the case's expected
behavior is the route, checkpoint order, startup behavior, release policy, or
trace surface itself. The runtime review does not require LLM judges, fixed path matching, exact turn-by-turn replay, or one universal test type by default.

Routing replay reports must classify the observable result instead of hiding
boundary uncertainty behind a single pass/fail label:

| Classification | Meaning |
| --- | --- |
| stable pass | The case passed and route evidence or local deterministic checks were strong enough for the selected runtime. |
| weak pass | The observable behavior passed, but exact skill telemetry was unavailable, so the result relies on the strongest visible substitute. |
| wrong route | The runtime produced the wrong observable route, side effect, or rendered contract for the scenario. |
| flaky/ambiguous | The case could not prove a stable route because runtime output or telemetry was ambiguous across the selected evidence. |
| blocked runtime | The runtime, permission model, timeout, or environment prevented a route judgment. |

The report must include a user-level situation and expected chain for each
routing replay case, so reviewers can understand what was tested without reading
only internal case ids or route labels.

When runtime telemetry cannot prove exact skill selection, the case must say so and
assert the strongest observable behavior. If exact skill sequence is required, the
runtime review harness must enable a review-only trace file such as
`.arbor/e2e-trace.jsonl`.

## Case Sources

Every case below comes from a previously reported workflow failure or review gap. New
Arbor regressions should be added here before the fix is accepted.

## Required Case Matrix

| ID | Prior failure | Entry surface | Expected real chain | Required observable proof |
| --- | --- | --- | --- | --- |
| R01 | Active engineering planning prompt did not trigger formal brainstorm. | Natural Codex and Claude prompt: "Based on my requirements, think through what to do and design a plan." with active repo cleanup context. | `brainstorm` | Rendered brainstorm checkpoint with the fixed brainstorm sections; `.arbor/workflow/features.json` and review Context/Test Plan are created or updated; no implementation files change. |
| R02 | Planning logic happened informally without formal Arbor checkpoint. | Explicit `$brainstorm` and `/arbor:brainstorm`. | `brainstorm -> converge` | Final response renders `user_response`; raw `brainstorm.v1` JSON is not primary output; review context exists before converge can drive internal implementation/review. |
| R03 | Standalone explanation or direct code review could be over-routed to Arbor. | Natural prompt asking only for a one-off explanation or standalone review. | direct answer | No workflow files are created; response stays direct; no `evaluate`-style review packet appears. |
| R04 | Code review attached to active Arbor handoff bypassed the public quality loop. | Natural "review this change" prompt in a repo with active Developer Round and review doc. | `converge -> internal evaluate` | Output uses converge-rendered sections; the quality loop can request internal evaluation; raw `evaluate.v1` JSON is hidden from the public response. |
| R05 | Runtime traceback was treated as direct work and skipped Arbor. | Paste a non-trivial traceback that blocks an active implementation or pipeline. | `brainstorm` or `develop` with review context | Route trace or observable behavior shows Arbor handling; immediate trivial explanation is not enough; fix or plan includes replay evidence. |
| R06 | Public validation requests could bypass converge and call evaluate directly. | Explicit `$converge` on a completed Developer Round. | `converge -> internal evaluate -> release(checkpoint_evaluate)` | Converge owns the public response and can require developer replay plus independent check categories; if a live replay is unavailable, the risk is rendered visibly. |
| R07 | Quality-loop output exposed or resembled raw `evaluate.v1` instead of readable rendering. | Explicit `$converge` and natural active-review continuation. | `converge` | Final response has converge sections, readable agreement/remaining-issue tables, and no raw evaluator schema object as primary UI. |
| R08 | Output layer was not checked after real execution. | Any workflow-facing change case. | Same as case chain | Harness saves `final-response.md` and asserts exact skill-specific headings, heading order, required table sections, hidden raw JSON, internal field leakage, and user-readable scenario wording. |
| R09 | Converge/replay loop was claimed without real convergence behavior. | Evaluate emits accepted, changes-requested, and needs-brainstorm examples. | `evaluate -> release(checkpoint_evaluate) -> converge` | Converge routes accepted work toward finalization, changes back to develop, and planning gaps back to brainstorm; registry status changes only when justified. |
| R10 | Release checkpoint policy was confused with final release. | Completed develop handoff. | `develop -> release(checkpoint_develop) -> evaluate` | A real local git commit is created before evaluation; commit contains selected workflow files only; push/PR/tag/publish do not happen. |
| R11 | Develop after success did not auto-commit. | Explicit `$converge` from approved scope with review context. | `converge -> internal develop -> release(checkpoint_develop)` | `git log -1` shows checkpoint commit; release status mentions checkpoint commit and next internal evaluate; unrelated dirty files are preserved. |
| R12 | Finalization/public release actions were not cleanly gated. | Natural "publish/release" prompts with and without explicit authorization. | `release(finalize_feature)` | Preparation can occur, but finalization commit, push, PR, tag, and publish require explicit user authorization; unauthorized cases stop with readable confirmation need. |
| R13 | "Publish" should finish the release path after validation passes. | Natural "publish" after converged feature and explicit permission. | `release(finalize_feature)` | Commit/push/publish action that was explicitly authorized succeeds; response includes action metadata; no unrelated work is included. |
| R14 | Local Codex and Claude plugin caches diverged from source. | Post-change cache verification. | Runtime cache sync check | Harness diffs source plugin against `~/.codex/plugins/cache/...` and `~/.claude/plugins/cache/...`; runtime smoke uses cached copy, not only worktree copy. |
| R15 | Startup/session-start context was not read in a fresh window. | Fresh Codex prompt: "What is this project doing?" and Claude SessionStart event. | `arbor` startup context | Response reflects `AGENTS.md`, recent git log, `.arbor/memory.md`, and `git status`; Claude hook output includes all sections under budget. |
| R16 | Codex startup relied on hook intent instead of reliable `AGENTS.md` bootstrap. | Fresh Codex run in initialized temp repo. | `arbor` startup protocol | Agent explicitly loads or reproduces startup context order; `.codex/hooks.json` alone is not treated as proof of injected context. |
| R17 | `.arbor/memory.md` was not updated during uncommitted Arbor work. | Stop after Arbor-managed edit before commit. | Any active workflow skill plus memory guard | `.arbor/memory.md` exists and names active feature, changed paths, checkpoint, risks, and next step before assistant stops. |
| R18 | Resolved memory remained after commit/publish. | Commit after previously dirty Arbor workflow state. | `release` or checkpoint commit | Resolved in-flight memory is pruned after successful commit; git history becomes authoritative. |
| R19 | Memory hygiene hook trigger rate was under-tested. | Case corpus spanning stops, handoffs, failed checks, release gates, cache syncs, direct answers, read-only turns, and no-write turns. | Hook intent review plus real dirty-state prompts | Positive cases emit memory-hygiene packet or result in memory update; negative cases remain quiet. |
| R20 | Hook/session logic was claimed without real adapter output. | Direct execution of Claude `hooks/session-start` plus real Claude plugin session where available. | SessionStart hook | Hook stdout includes startup packet for `startup` and `resume`, stays empty for `clear`, and is actually available through plugin load. |
| R21 | Structured output and rendered UI were not checked across public entrypoints. | Explicit invocation of public workflow entrypoints plus internal fixture checks for internal stages. | `brainstorm`, `feedback`, `converge`, `release`, plus internal develop/evaluate fixtures | Internal raw packet is not the primary final answer; visible text follows each public skill's designed sections and status style. |
| R22 | Public quality-loop routing could work but chain handoff could fail. | Start from `converge` with valid review evidence for internal develop/evaluate continuation. | `converge` plus next internal handoff | Handoff context is sufficient for the next internal stage; no skill requires hidden chat-only state to proceed. |
| R23 | Entry from the middle of the workflow could fail. | Direct prompts for converge and release with equivalent review evidence already present; public develop/evaluate prompts route-correct to converge. | Chosen public skill or route correction | Valid mid-chain public entries work; incomplete entries block with readable missing evidence instead of fabricating state. |
| R24 | Previous "full-chain" checks used ignored local fixtures. | Release validation command set. | Release gate | Required real-runtime runner and its scenario definitions are tracked in the repository or explicitly packaged; ignored fixtures are labelled optional and cannot satisfy release. |
| R25 | Real runtime behavior differed between Codex and Claude. | Paired Codex and Claude runs for routing, startup, converge rendering, and release checkpoint. | Same semantic chain on both runtimes | Differences are limited to adapter surfaces; shared skill behavior and rendered user contract match. |
| R26 | Review loops closed too early. | A failing real case followed by a fix attempt. | `develop -> release -> evaluate -> converge` until accepted | Runner repeats until pass or records a blocking finding; final status cannot be accepted from developer self-test alone. |
| R27 | Active planning continuation was only protected when the current task was embedded in the same prompt. | Split-context prompt: prior turn establishes active code cleanup requirements, current turn says "Okay. Based on my requirements, let's think through what to do and design a plan." | `brainstorm` | Rendered brainstorm checkpoint persists `.arbor/workflow/features.json` and review Context/Test Plan; implementation files do not change; the paired non-engineering fixture remains direct. |
| R28 | `AGENTS.md` Project Map drift was not surfaced or updated after durable project entrypoints changed. | A new top-level `tools/` directory exists but `AGENTS.md` only maps `src/`; user asks Arbor to update the map before release. | `arbor.goal_constraint_drift` -> AGENTS Project Map update | The drift packet exposes project-map candidates, final rendered text is readable, and `AGENTS.md` Project Map mentions `tools/` without adding transient session progress. |
| R29 | Informal or misspelled evaluate requests could bypass the public quality-loop entrypoint. | Natural prompt with a misspelled verb such as "evalute this active developer handoff" in a repo with active Developer Round and review doc. | `converge` | Captured `final-response.md` contains the complete converge checkpoint and does not tell the user to invoke public evaluate. |
| R30 | Non-English workflow prompts could still render canonical English headings because the skill package is English-only. | Non-English prompt invoking public quality-loop validation in a repo with active Developer Round and review doc. | `converge` | Captured `final-response.md` uses the user's non-English language for visible convergence checkpoint prose and localized headings, preserves required agreement/remaining-issue Markdown tables, and does not use the canonical English headings as the final visible headings. |
| R31 | Automatic develop/evaluate/converge runs could skip release checkpoint execution while writing hand-authored Release Round prose. | Explicit `develop_evaluate_converge` automation prompt from an approved feature. | `develop -> release(checkpoint_develop) -> evaluate -> release(checkpoint_evaluate) -> converge` | Developer, evaluator, release, and convergence evidence exist; git commit count increases by at least two local checkpoint commits after setup; finalization commit, push, tag, and publish do not happen. |
| R32 | Feedback prompts could fall back to direct prose or expose internal stages. | Explicit `$feedback` with a bug report tied to an active Arbor feature. | `feedback -> converge` | Final response renders `Feedback Decision`, `Why This Route`, `What I Need Or Will Use`, and `Next Step`; the route chooses `converge` for the existing feature and does not expose public develop/evaluate calls. |

## Runtime Assertions

Every real case must define assertions in four groups.

### Route Assertions

- expected runtime: Codex, Claude, or both;
- expected entry surface: natural prompt, explicit skill, hook event, or mid-chain packet;
- expected skill chain when trace is available;
- acceptable observable substitute when exact runtime skill telemetry is unavailable.

### State Assertions

- expected git status before and after;
- expected commit count and commit message when a checkpoint commit is required;
- expected changed files and selected-file scope;
- expected `.arbor/workflow/features.json` state;
- expected review document sections and appended rounds;
- expected `.arbor/memory.md` presence or pruning.

### Rendered Output Assertions

- final response saved as `final-response.md`;
- raw `*.v1` JSON is not the primary UI unless debug output was explicitly requested;
- skill-specific headings and tables are present;
- non-English prompts use localized visible headings in the user's language while
  preserving the same section order and required tables;
- checkpoint cases compare git commit count against the pre-runtime baseline,
  not just the total number of commits in the fixture repository;
- internal field names and fixture ids are not the main user-facing explanation;
- release output stays status-only;
- evaluate output has readable verdict, findings, challenge plan, test tables, judgments, risks, and next step.

### Negative Assertions

- unauthorized public actions do not run;
- unrelated dirty files are not staged or committed;
- missing handoff evidence blocks instead of being invented;
- direct answers do not create Arbor workflow artifacts;
- evaluate does not edit implementation files;
- brainstorm does not implement;
- release does not plan or evaluate.

## Minimum Release Gate

A release may say "real workflow chain review passed" only when these cases pass:

- R01, R04, R05, R07, R10, R11, R12, R15, R17, R21, R22, R24 on Codex;
- R27 on Codex for split-context planning continuation changes;
- R29 on Codex for workflow rendered-output or evaluate-routing changes;
- R30 on Codex for visible language or localized checkpoint rendering changes;
- R31 on Codex for checkpoint gate or develop/evaluate/converge automation changes;
- R32 on Codex for feedback entrypoint or feedback-routing changes;
- R14 and R25 for shared Codex/Claude changes;
- R20 for Claude hook changes;
- the directly affected case for every bug fixed in the release.

If a runtime cannot be exercised, the release note must say "real runtime gap" and name
the skipped runtime and cases. Ignored simulation fixtures and baseline scripts cannot
close that gap.
