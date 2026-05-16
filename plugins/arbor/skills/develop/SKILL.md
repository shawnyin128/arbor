---
name: develop
description: Execute an authorized Arbor-managed feature or artifact change, consume upstream plan/context, run developer self-tests against the review plan, append developer review handoff evidence, and emit structured output for release checkpointing before evaluate.
---

# Develop

## Purpose

Use `develop` when Arbor has an authorized implementation or managed-artifact unit ready to execute.

`develop` is not a coding-style constraint. Use normal engineering judgment and the repo's conventions. The skill's job is workflow discipline: consume upstream context, preserve traceability, implement, self-test against the brainstorm review test scope, append developer evidence, and hand off to `release` for an automatic local developer checkpoint commit before `evaluate`.

It does not approve plans, independently validate like `evaluate`, decide convergence, push, tag, or publish. It also does not create the checkpoint commit itself or decide whether a checkpoint should bypass evaluation; `release(checkpoint_develop)` creates the local checkpoint commit and routes onward when the developer handoff is ready.

`develop` is a mandatory user-visible checkpoint by default. The user must be able to see what changed, how the work maps to the plan, which implementation defaults were chosen, and how the developer self-tested before the workflow continues into independent evaluation.

A `ready_for_evaluate` developer handoff is not workflow completion. Do not present develop-only work as done, accepted, converged, release-ready, or finished. The visible output must make independent evaluation explicit as pending, either by stopping at the checkpoint or by continuing only under an eligible `develop_evaluate_converge` automation policy.

The only exception is an explicit `develop_evaluate_converge` automation policy requested by the user for the current workflow. Under that policy, `develop` may continue automatically only when the implementation stayed in scope, all planned developer checks passed, no material hidden decision needs review, and no unresolved risk or deviation is reported.

## Checklist

Follow this normal sequence for develop runs. Stop early with the correct terminal state when source, execution basis, scope, or upstream context is missing.

1. **Identify source**: determine whether input came from a known upstream example such as `brainstorm`, `intake`, or `converge`, or from another valid handoff source.
   Treat the known sources as examples, not the complete set. If the source is different, apply the fallback upstream contract below.
2. **Record execution basis**: record why execution is allowed. If required authorization is missing, stop with `blocked`.
3. **Select scope**: identify the selected feature or managed artifact. If multiple independent units exist with no selection, stop with `needs_selection`.
4. **Review upstream critically**: verify acceptance criteria, constraints, risks, feature registry path, review document path, brainstorm test expectations, and decision trace handoff are usable. If not, stop with `needs_brainstorm`.
5. **Implement freely within scope**: use repo conventions and senior engineering judgment. Record material deviations, implementation-time decisions, decision deviations, and whether decision invariants still hold.
6. **Self-test against the plan**: design and run developer checks that cover the artifact-appropriate verification scope and done-when criteria from the brainstorm review document. Record any uncovered planned checks. When using `verification_checks`, make each item replayable: name the inspected artifact, the check performed, the expected result, the actual result, and the result. For `ready_for_evaluate`, only `passed` verification checks count as completed evidence; skipped, failed, blocked, or not-run checks must be reflected in `uncovered_planned_tests`, `not_run`, or a non-ready terminal state.
7. **Append handoff**: append a Developer Round to the same existing review document named by `source.review_doc_path`. Do not create the Context/Test Plan section. Include a detailed self-test table so `evaluate` can see what was tested, what passed or failed, what was skipped, and which planned checks or done-when criteria each row covers.
8. **Update in-flight memory**: before stopping or handing off with uncommitted Arbor workflow changes, ensure `.arbor/memory.md` exists and records the selected feature/artifact, changed paths, current developer checkpoint, unresolved risks, and next expected step. Remove or shrink resolved entries only after the state is committed or moved to durable docs.
9. **Set checkpoint policy**: default to `must_stop`; use `auto_continue_allowed` only when the user explicitly enabled `develop_evaluate_converge` automation and no material decisions, deviations, skipped checks, or risks need user review.
10. **Guard continuation semantics**: if implementation reaches `ready_for_evaluate`, make the next independent evaluation step explicit and do not use final-completion language.
11. **Return rendered checkpoint and runtime packet**: produce `develop.v1` for runtime handoff, and make the normal user-visible response the rendered `user_response` checkpoint, not raw JSON.

## Terminal States

- `needs_brainstorm`: requirements, plan, or product decisions are missing or invalid.
- `needs_selection`: multiple independent features exist and no selected unit is clear.
- `blocked`: required files, permissions, dependencies, upstream evidence, or execution authorization are unavailable.
- `implementation_failed`: implementation was attempted but did not complete.
- `self_test_failed`: implementation completed enough to test, but developer self-tests failed.
- `ready_for_evaluate`: implementation, self-test, and developer review handoff are complete.
- `route_correction`: request belongs to another skill or direct work.

Only `ready_for_evaluate` may route to `release`, and the release handoff must identify `release_context.release_mode=checkpoint_develop` so `release` creates a local checkpoint commit before the next workflow step continues to `evaluate`.

## User-Facing Development Packet

`user_response` is the visible development summary. It must lower the user's review cost; do not make the user read internal schema fields to understand what happened.

The structured `develop.v1` object is an internal workflow/runtime packet. In a normal user-facing final response, render the checkpoint from `user_response` and `ui`; do not print the raw `develop.v1` JSON unless the user explicitly asks for debug or machine output.

Write it in plain natural language with these sections:

1. **What I Completed**: summarize the implemented change or explain why implementation did not start.
2. **How It Maps To The Plan**: map the accepted plan, selected work, or incoming correction to the actual work in user-level words.
3. **What Changed**: list changed code, docs, or artifacts and the practical impact.
4. **Implementation Defaults I Chose**: expose implementation-time decisions the user did not explicitly specify, such as fallback behavior, scope interpretation, test substitution, naming, file placement, or engineering tradeoffs. If there were no material hidden decisions, say so explicitly.
5. **How I Self-Tested**: show the developer-side checks, what each check was meant to prove, and the observed result.
6. **Risks And Gaps**: list unresolved risks, skipped checks, blockers, or deviations from the plan.
7. **Next Step**: describe the next workflow step in plain language, such as saving a local checkpoint commit before independent evaluation, returning to planning, or stopping because authorization is missing.

For non-success states, keep the same readable shape but make the blocker clear. For example, say "the plan has not been confirmed yet, so implementation cannot start" instead of exposing the internal authorization state.

Never expose machine-oriented labels in `user_response`. Avoid schema field names, terminal-state strings, route assignments, feature ids, fixture ids, and shorthand such as `dev/eval`. If a table is useful, translate every cell into user-facing language; do not copy internal labels from `source`, `route`, `review_handoff`, `self_test`, `feature_registry_update`, or other structured fields.

## Upstream Source Contract

`brainstorm`, `intake`, and `converge` are the common Arbor upstream sources. They are not a closed list and are not the only possible valid sources.

For any upstream source, known or fallback, consume the same minimum contract:

- raw request or handoff text;
- executable scope;
- execution authorization evidence;
- acceptance criteria or equivalent success conditions;
- done-when criteria or equivalent completion conditions, when available;
- constraints, non-goals, risks, and test expectations when available;
- review document path with brainstorm-owned Context/Test Plan when the source is a planned Arbor feature;
- feature registry path, normally `.arbor/workflow/features.json`, when the source is part of a split feature plan;
- stable pointers to artifacts, messages, findings, or prior review evidence.

Set `source.from_skill` to the known skill name when the source is `brainstorm`, `intake`, or `converge`. For other sources, use a stable source label such as `manual_handoff`, `external_plan`, `project_doc`, or `unknown` if the source cannot be identified.

## Known Source Flows

### `brainstorm`

Consume the selected feature, recommended approach, goals, non-goals, constraints, acceptance criteria, done-when criteria, decision trace handoff, feature registry path, review document path, brainstorm verification scope, risks, evidence pointers, and execution basis.

If `brainstorm` ended in `ready_for_user_review`, require user approval evidence. If it ended in `ready_for_develop`, record that terminal state as the authorization source.

If the brainstorm handoff lacks `docs/review/<feature>-review.md` or an equivalent review context with test scope, return `needs_brainstorm` instead of creating it inside `develop`.

### Decision Trace Handoff

For brainstorm-backed work, consume the decision trace before editing. The trace should include key decisions, rejected options, allowed implementation discretion, and decision invariants. Implement freely inside that boundary, but record implementation-time decisions and decision deviations in the Developer Round.

If implementation would violate decision invariants, reopen rejected options, or materially change product intent, return `needs_brainstorm` or record a blocker instead of silently changing the plan. The trace must not be used to require subagents, worktrees, or a fixed implementation strategy.

### Delegation Packet And Effort Budget

If the upstream plan includes an optional delegation packet, `develop` may use it for bounded investigation or evidence gathering. The packet should specify objective, output format, tools/sources, boundaries, effort budget, context pointers, and stop conditions.

Implementation remains owned by the main developer unless the user explicitly assigned work elsewhere. Direct answers, simple edits, tightly coupled coding, and tightly coupled workflow changes remain single-threaded by default. Delegation guidance must not require subagents or worktrees, fan-out execution, parallel coding, fixed tool-call counts, or a fixed implementation strategy.

When delegation is used, record the packet, result, and any evidence gaps in the Developer Round. When delegation is skipped because the work is tightly coupled or unnecessary, record that decision only if it affects review.

## Done-When Verification Thread

For Arbor-managed features, `develop` continues the done-when verification thread without turning it into a coding constraint. Implement normally inside the accepted scope, then map self-tests to done-when criteria and planned verification items.

Rules:

- Each successful self-test table row must name the planned check, acceptance criterion, done-when criterion, evaluator finding, or replay target it covers.
- A row that only says the code was inspected, looks good, or generally covers the plan is not enough.
- If a done-when criterion cannot be covered by developer self-test, record the verification gap in `uncovered_planned_tests`, `not_run`, risks, and the Developer Round.
- Use the strongest artifact-appropriate check available; do not force one test type when content, structure, rendered output, static contract, or scenario evidence is the correct proof.
- `ready_for_evaluate` requires no uncovered done-when criteria unless the brainstorm plan explicitly assigned that proof to independent evaluation or release.

### `intake`

Use only for clear managed artifacts or narrow active implementation. Consume raw request, classification, target artifact or implementation target, persistence/write permission, active context, warnings, and route reason.

Infer only narrow obvious scope. If the request needs design or acceptance criteria first, return `needs_brainstorm`. If it should not be Arbor-managed, return `route_correction`.

### `converge`

Use for correction loops from evaluator findings. Consume review document path, evaluator finding ids, requested correction scope, prior rounds, reproduction steps, failing tests, and replay targets.

Append a new developer round. Do not rewrite old developer/evaluator evidence.

## Fallback Source Flow

Use fallback source handling only when the upstream source is not one of the known flows above.

If the fallback source provides the minimum upstream contract, `develop` may proceed. If it lacks scope, authorization, or success conditions, return `blocked`, `needs_selection`, or `needs_brainstorm` according to the missing piece.

Fallback is not a shortcut around planning. It is a compatibility path for manual handoffs, project documents, review artifacts, resume packets, future Arbor skills, or other sources that already contain enough executable evidence.

## Anti-Patterns

### "Develop Can Approve The Plan"

No. `brainstorm` gets user approval. `develop` only records execution authorization evidence.

### "Developer Self-Test Is Independent Evaluation"

No. Self-tests are developer evidence. Independent validation belongs to `evaluate`.

### "Ready For Evaluate Means Complete"

No. `ready_for_evaluate` only means the developer side has produced an implementation, self-test evidence, and a review handoff. Evaluation and convergence are still pending.

### "Just Start Coding And Explain Later"

No. First identify source, scope, and authorization. If those are missing, stop with the correct terminal state.

### "Failed Runs Can Still Look Successful"

No. Non-success terminal states must not carry success statuses or route to `release`.

### "Review Evidence Belongs In Skill References"

No. Runtime skill references are instructions. Developer/evaluator evidence belongs under `docs/review/` or the repo's equivalent review location.

### "Develop Can Create The Review Context"

No. `brainstorm` creates the Context/Test Plan section. `develop` appends Developer Rounds and maps self-tests to the brainstorm test scope.

### "Develop Can Append Somewhere Else"

No. When `review_handoff.status=appended`, `review_handoff.path` must match `source.review_doc_path`. The Developer Round belongs in the same document that contains the brainstorm Context/Test Plan.

### "Patch The Failing Example"

No. Do not add unapproved case-specific defensive programming for one observed input, fixture, prompt, user example, filename, or test case. If a defensive branch is unavoidable, first generalize the failure into a class of inputs, then implement a complete fallback chain at the lowest appropriate layer. Record the reason and scope in `implementation.deviations` or review evidence.

### "Review Docs Are The Feature Queue"

No. Review docs are evidence. `.arbor/workflow/features.json` is the queue/status index. `develop` should update the selected feature status instead of making later skills infer progress by scanning review files.

### "Review Evidence Replaces Session Memory"

No. Review docs and feature registries do not replace `.arbor/memory.md`. If `develop` leaves uncommitted Arbor workflow changes, the short-term memory file must contain a compact in-flight entry so the next session can resume before any commit exists.

## Evidence Rules

Prefer stable evidence over loose prose. When recording execution authorization or handoff evidence, use one or more of:

- upstream artifact paths;
- message or turn ids when available;
- short exact user approval quotes;
- upstream terminal states;
- review document paths and finding ids.

Do not invent approval evidence. If a required approval cannot be pointed to, return `blocked`.

## Status Matrix

| Terminal state | Implementation | Self-test | Handoff | Next |
| --- | --- | --- | --- | --- |
| `needs_brainstorm` | `not_started` or `partial` | `not_run` or `blocked` | `blocker_packet` or `not_required` | `brainstorm` |
| `needs_selection` | `not_started` | `not_run` | `not_required` | `brainstorm` |
| `blocked` | `not_started` or `partial` | `not_run` or `blocked` | `blocker_packet` or `not_required` | `none` |
| `implementation_failed` | `failed` or `partial` | `not_run`, `partial`, or `blocked` | `blocker_packet` or `appended` | `none` |
| `self_test_failed` | `completed` or `partial` | `failed` or `partial` | `appended` | `none` |
| `ready_for_evaluate` | `completed` | `passed` or `partial` | `appended` | `release` |
| `route_correction` | `not_started` | `not_run` | `not_required` | declared route or `none` |

## Structured Output Contract

Produce this structure for internal workflow handoff:

```json
{
  "schema_version": "develop.v1",
  "raw_user_request": "",
  "source": {
    "from_skill": "brainstorm",
    "plan_id": null,
    "feature_id": "",
    "feature_registry_path": ".arbor/workflow/features.json",
    "review_doc_path": "docs/review/<feature>-review.md",
    "authorization_required": true,
    "authorization_state": "authorized",
    "authorization_source": "user_approved_brainstorm_plan",
    "authorized_by": "user",
    "authorization_evidence": "",
    "authorization_evidence_refs": []
  },
  "scope": {
    "title": "",
    "summary": "",
    "goals": [],
    "non_goals": [],
    "acceptance_criteria": []
  },
  "implementation": {
    "status": "completed",
    "changed_files": [],
    "artifact_changes": [],
    "notes": [],
    "deviations": []
  },
  "self_test": {
    "status": "passed",
    "commands": [],
    "unit_tests": [],
    "scenario_tests": [],
    "verification_checks": [
      {
        "artifact": "",
        "check": "",
        "expected_result": "",
        "actual_result": "",
        "result": "passed"
      }
    ],
    "planned_test_coverage": [],
    "uncovered_planned_tests": [],
    "coverage": null,
    "not_run": []
  },
  "review_handoff": {
    "status": "appended",
    "handoff_kind": "success",
    "blocker_kind": null,
    "path": "docs/review/<feature>-review.md",
    "self_test_table": [
      {
        "category": "unit",
        "check": "",
        "evidence": "",
        "expected": "",
        "actual": "",
        "result": "passed",
        "covers": []
      }
    ],
    "evaluator_focus": [],
    "known_risks": [],
    "replay_targets": []
  },
  "feature_registry_update": {
    "status": "updated",
    "path": ".arbor/workflow/features.json",
    "feature_id": "",
    "from_status": "in_develop",
    "to_status": "in_evaluate",
    "reason": ""
  },
  "route": {
    "terminal_state": "ready_for_evaluate",
    "next_skill": "release",
    "next_skill_context": {
      "release_mode": "checkpoint_develop",
      "next_after_release": "evaluate",
      "checkpoint_authorization": {
        "source": "policy",
        "ref": "arbor-workflow#checkpoint-policy",
        "scope": "local checkpoint commit for develop handoff",
        "allows_local_commit": true
      }
    },
    "reason": "Developer handoff is ready; release should create a local checkpoint commit before evaluation."
  },
  "ui": {
    "summary": "",
    "review_focus": [],
    "warnings": [],
    "checkpoint": {
      "visibility": "user_visible",
      "continue_policy": "must_stop",
      "reason": "The implementation summary, hidden decisions, and self-test evidence should be visible before independent evaluation.",
      "resume_after": "user_acknowledgement"
    },
    "workflow_automation": {
      "policy": "develop_evaluate_converge",
      "enabled": false,
      "eligible": false,
      "stop_conditions": [
        "material hidden/default decision",
        "scope deviation",
        "failed, skipped, blocked, or missing planned check",
        "unresolved risk",
        "missing authorization"
      ]
    }
  },
  "user_response": ""
}
```

Use these enums:

- `source.from_skill`: known skill name or stable fallback source label, such as `brainstorm`, `intake`, `converge`, `manual_handoff`, `external_plan`, `project_doc`, or `unknown`
- `source.authorization_state`: `authorized`, `not_required`, `missing`, `rejected`
- `implementation.status`: `not_started`, `completed`, `partial`, `failed`
- `self_test.status`: `not_run`, `passed`, `failed`, `partial`, `blocked`
- `self_test.verification_checks`: structured artifact-appropriate evidence; `ready_for_evaluate` may count only entries with `result=passed`; a passed check's `actual_result` must not say it was not run, skipped, failed, or blocked; do not use vague strings such as `looks good`, `manual review passed`, or `checked output`
- `self_test.commands`, `self_test.unit_tests`, and `self_test.scenario_tests`: raw identifiers for commands, unit-test targets, and scenario targets; for `ready_for_evaluate`, they should not carry result summaries such as passed, failed, skipped, blocked, not run, exit code, assertion error, exception, or traceback. Put observed results in `review_handoff.self_test_table` or `verification_checks`.
- `self_test.not_run`: skipped or unavailable checks; must be empty for `ready_for_evaluate`
- `review_handoff.status`: `not_started`, `appended`, `blocker_packet`, `not_required`
- `review_handoff.handoff_kind`: `success`, `blocker`, `failure`, `route_correction`, `none`
- `review_handoff.blocker_kind`: `missing_authorization`, `missing_selection`, `missing_requirements`, `missing_dependency`, `implementation_error`, `self_test_failure`, `scope_change`, `misroute`, or `null`
- `review_handoff.self_test_table`: detailed test rows written into the Developer Round; required and non-empty whenever `review_handoff.status=appended`
- `feature_registry_update.status`: `not_required`, `updated`, `blocked`
- `feature_registry_update.to_status`: `planned`, `approved`, `in_develop`, `in_evaluate`, `changes_requested`, `done`, `blocked`, `deferred`, or `null`
- `feature_registry_update.feature_id`: must match `source.feature_id` whenever a registry-backed run updates workflow state
- `route.terminal_state`: `needs_brainstorm`, `needs_selection`, `blocked`, `implementation_failed`, `self_test_failed`, `ready_for_evaluate`, `route_correction`
- `route.next_skill`: `brainstorm`, `develop`, `evaluate`, `converge`, `release`, `none`
- `route.next_skill_context.release_mode`: `checkpoint_develop` when `ready_for_evaluate` routes to `release`
- `route.next_skill_context.next_after_release`: `evaluate` when `ready_for_evaluate` routes to `release`
- `route.next_skill_context.checkpoint_authorization`: policy authorization for the local checkpoint commit that `release(checkpoint_develop)` must create before `evaluate`
- `ui.checkpoint.visibility`: `user_visible`
- `ui.checkpoint.continue_policy`: `must_stop` or `auto_continue_allowed`
- `ui.checkpoint.resume_after`: `user_acknowledgement`, `auto_policy`, `brainstorm_ready`, `selection_ready`, or `blocker_resolved`
- `ui.workflow_automation.policy`: `develop_evaluate_converge` or `none`

When adding a terminal state, update the status matrix, output enums, simulation cases, baseline JSONL, and `scripts/check_develop_baselines.py` in the same change.

For all terminal states, default to `ui.checkpoint.continue_policy=must_stop`. Use `auto_continue_allowed` only when all of these are true: the user explicitly enabled `develop_evaluate_converge` automation for the current workflow, implementation stayed inside scope, no material hidden/default decision needs review, all planned developer checks passed, and no unresolved risk or deviation is reported. Use `must_stop` for missing authorization, missing selection, missing brainstorm context, implementation failure, self-test failure, scope changes, or any blocker that needs a human decision.

For `ready_for_evaluate`, the visible `user_response` must say that `release` will save a local checkpoint commit and then independent evaluation remains next. It must not imply the feature is accepted, converged, release-ready, or complete.

For `ready_for_evaluate`, `planned_test_coverage` must be non-empty, concrete check evidence must be present, and `uncovered_planned_tests` must be empty. Concrete result evidence comes from passed self-test table rows or passed `verification_checks` for content checks, structure checks, dry runs, schema checks, compile/lint/type checks, or other checks appropriate to the artifact. Raw command, unit-test, and scenario fields identify targets; they do not prove results by themselves. For `self_test_failed`, record the planned checks that were attempted and the planned checks still uncovered or failing.

When appending the Developer Round, write the self-test table into the review document with these columns: category, check, evidence, expected, actual, result, and covers. `covers` maps the row back to brainstorm planned verification scope or acceptance criteria. This table is mandatory for appended success and failure handoffs; it is the primary surface `evaluate` reads before running independent tests.

Treat `review_handoff.self_test_table` as the canonical developer self-test evidence surface for `evaluate`. The raw `commands`, `unit_tests`, and `scenario_tests` fields identify what was run or inspected; they are not the place to summarize pass/fail status. `verification_checks` may provide structured supporting result evidence. If any observed result is failed, skipped, blocked, or not run, the terminal state is not `ready_for_evaluate` and the table must show the unresolved evidence.

For `ready_for_evaluate`, every self-test table row must have `result=passed`, and every row's `covers` list must be non-empty. `covers` must include at least one specific planned test label, acceptance criterion, evaluator finding id, or replay target, such as `check:<name>`, `acceptance:<criterion>`, `replay:<target>`, or a finding id. Generic values such as `planned check`, `test plan`, or `coverage` are not enough. A feature id such as `feature:F2` is useful context but is not sufficient by itself because it does not identify what the row proves. For `self_test_failed` or `implementation_failed`, the table must include at least one row with `result=failed`, `result=skipped`, or `result=blocked`. Do not use vague table text such as `looks good`, `manual review passed`, or `checked output`.

## Self-Check

Before returning:

1. Did I consume the upstream source and preserve its intent?
2. Did I record execution authorization evidence or correctly mark authorization as not required?
3. Did I record material deviations from the upstream plan?
4. Did I preserve unrelated user work?
5. Did I map developer self-tests to the brainstorm review verification scope and done-when criteria?
6. Did I record any planned checks I could not cover?
7. Did I append developer review handoff evidence, including the detailed self-test table, to the same existing review document named by `source.review_doc_path` when the run reached handoff state?
8. Did I avoid unapproved case-specific defensive programming, or document a generalized fallback chain at the lowest appropriate layer?
9. Did the self-test table avoid generic `covers`, and did raw self-test fields stay as identifiers instead of result summaries?
10. Did I update the selected feature status in `.arbor/workflow/features.json` when the run changed workflow state?
11. Did the output statuses match the status matrix?
12. If uncommitted Arbor workflow changes remain, did I create or refresh `.arbor/memory.md` with the in-flight state and next step?
13. Did blocked or failed runs expose a machine-readable `handoff_kind`, `blocker_kind`, and replay target where useful?
13. Did I route to `release` only from `ready_for_evaluate`, with `route.next_skill_context.release_mode=checkpoint_develop`, `next_after_release=evaluate`, and policy authorization for a local checkpoint commit?
14. Did I include a user-visible checkpoint with the correct continue policy before independent evaluation?
15. Did `user_response` expose implementation-time hidden/default decisions in natural language, or explicitly state that there were no material hidden decisions?
16. Did `user_response` make clear that independent evaluation remains pending instead of implying final completion?
17. Did `user_response` explain the development result in natural language without leaking internal field names, route codes, feature ids, fixture ids, or shorthand?

If any check fails, revise the output or return the appropriate blocked/needs state.

## Reference Material

- `references/develop-boundary.md`: full boundary, upstream source contracts, execution basis contract, review handoff, and terminal-state matrix.
- `references/develop-simulation-cases.md`: regression cases from user simulation.
- `scripts/check_develop_baselines.py`: deterministic replay/schema checks for the develop simulation baselines.
