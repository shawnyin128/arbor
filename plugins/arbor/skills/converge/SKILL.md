---
name: converge
description: Decide whether an Arbor develop/evaluate loop has converged, compare evaluator evidence against brainstorm goals, update feature status only after justified agreement, route correction loops, and escalate to the user when round limits or product decisions block automatic progress.
---

# Converge

## Purpose

Use `converge` after `evaluate` has appended an Evaluator Round for an Arbor-managed feature.

`converge` is a workflow decision skill. It decides whether the latest developer/evaluator loop agrees and whether the result still satisfies the brainstorm Context/Test Plan. After a current feature converges, it routes to internal `release` so the feature can be finalized before the next unfinished feature is selected. It does not implement fixes, run independent adversarial tests, create the brainstorm plan, commit, push, tag, or release.

The normal terminal output is a structured `converge.v1` decision plus a Convergence Round appended to the same review document.

`converge` is a mandatory user-visible checkpoint by default. Do not silently continue into release, the next feature, or another correction loop in the same final response. The user must be able to see whether the developer/evaluator loop agrees, whether the result still matches the brainstorm goal, and why the workflow is stopping, looping, or finalizing.

A `converged` decision is not release completion. Do not present convergence-only work as committed, pushed, published, or fully released. The visible output must make release finalization explicit as the next step.

The only exception is an explicit `develop_evaluate_converge` automation policy requested by the user for the current workflow. Under that policy, `converge` may continue automatically only for clear loop decisions inside the current feature, below the round limit, with no product/design decision, scope change, missing evidence, or external release action required.

## Checklist

1. **Confirm source**: accept only completed evaluator states or a valid convergence packet. If the request is not a convergence decision, return `route_correction`.
2. **Load workflow state**: read `.arbor/workflow/features.json` and the selected feature's review document.
3. **Load loop evidence**: identify brainstorm Context/Test Plan, latest Developer Round, latest Evaluator Round, evaluator findings, feature-registry signal, and round count.
4. **Check identity**: confirm feature id, review document, registry row, and evaluator signal all point to the same feature.
5. **Check agreement**: decide whether develop and evaluate agree, or whether evaluator findings require another round.
6. **Check brainstorm alignment**: decide whether the accepted result still satisfies brainstorm goals, acceptance criteria, done-when criteria, decision invariants, non-goals, and test scope.
7. **Apply loop policy**: route automatically while under the round limit; surface loop-health risk before automatic continuation when repeated same-class failures, evidence conflicts, weak replay evidence, or context contamination make the next route unreliable; escalate when the limit is reached or a user/product decision is required.
8. **Update feature registry when justified**: mark `done`, `changes_requested`, `planned`, or `blocked` only for the selected feature.
9. **Append convergence evidence**: append a Convergence Round to the same review document without rewriting prior rounds.
10. **Update in-flight memory**: before stopping or handing off with uncommitted Arbor workflow changes, ensure `.arbor/memory.md` exists and records the converged or looping feature, changed registry/review paths, decision, unresolved blockers, and next expected step. Remove or shrink resolved entries only after the state is committed or moved to durable docs.
11. **Defer continuation**: after `converged`, route to internal `release`; release selects the next unfinished feature after finalization.
12. **Return rendered checkpoint and runtime packet**: produce `converge.v1` for runtime handoff, and make the normal user-visible response the rendered `user_response` checkpoint, not raw JSON.

## Terminal States

- `converged`: developer/evaluator agreement and brainstorm-goal alignment are satisfied.
- `needs_develop`: evaluator found actionable implementation or test defects.
- `needs_brainstorm`: requirements, acceptance criteria, test plan, or scope assumptions need planning.
- `needs_evidence`: required developer/evaluator/review/registry evidence is missing or inconsistent.
- `needs_user_decision`: the loop hit the round limit or needs a product/design decision.
- `blocked`: required files, permissions, or environment prevent a decision.
- `route_correction`: request belongs to another skill or direct work.

## Core Rules

1. Do not re-evaluate implementation behavior. Use evaluator evidence.
2. Do not implement fixes. Route selected findings to `develop`.
3. Do not ask the user when an automatic correction route is clear and below the round limit.
4. Do ask the user when the correction would change brainstorm scope, hidden decisions, or product behavior.
5. Do not mark a feature done unless evaluator accepted and brainstorm goals plus done-when criteria remain satisfied.
6. Do not update a different feature than the one selected by registry, review document, and evaluator signal.
7. Do not infer convergence from prose alone; require explicit evaluator verdict, findings, and registry signal.
8. Append convergence evidence to the same review document.
9. Always emit a user-visible checkpoint before release finalization, next-feature selection, or another automatic loop.
10. Never present convergence-only output as release completion; `release` owns finalization and next-feature selection.
11. A loop-health advisory may recommend narrowing scope, re-brainstorming, exact runtime replay, or a fresh-session handoff, but it must not automatically clear context, spawn subagents, create worktrees, or require fan-out execution.
12. Check decision trace consistency before marking work done. Unresolved decision drift, hidden decision conflict, or violated decision invariants must return the appropriate evidence or planning route.
13. Do not require delegation to mark work done. When optional delegation packet evidence exists, use evaluator evidence to decide whether the objective, output format, boundaries, and effort budget were followed.
14. Check outcome evidence before exact path matching. Mark work done only when developer and evaluator evidence agree on final state, checkpoint outcomes, rendered output, review evidence, process state, git/file side effects, realistic replay, trace evidence, and any weak-pass gaps relevant to the brainstorm goal.

## Route Rules

| Situation | Terminal state | Next skill |
| --- | --- | --- |
| Evaluator accepted, ids match, goals satisfied | `converged` | `release` |
| Evaluator requested implementation/test changes | `needs_develop` | `develop` |
| Evaluator found plan/requirements contradiction | `needs_brainstorm` | `brainstorm` |
| Brainstorm, developer, or evaluator evidence is missing | `needs_evidence` | `brainstorm`, `develop`, or `evaluate` |
| Round limit or product decision blocks automation | `needs_user_decision` | `none` |
| Environment or file access blocks the decision | `blocked` | `none` |

For `needs_evidence`, route to the owner of the missing or inconsistent evidence: missing brainstorm Context/Test Plan, acceptance criteria, or goals routes to `brainstorm`; missing latest Developer Round routes to `develop`; missing latest Evaluator Round, identity mismatch, or inconsistent evaluator signal routes to `evaluate`.

For next feature selection after `converged`, do not choose the next feature in `converge`. Set `workflow_continuation.status=none` and route to `release`; release performs current-feature finalization and then selects the next unfinished feature.

For detailed boundary rationale, read `references/converge-boundary.md`.

## User-Facing Convergence Packet

`user_response` is the visible convergence decision. Keep it decision-oriented and shorter than an evaluation report. It should answer whether the feature converged, why, whether developer and evaluator evidence agree, whether the result still matches the brainstorm goal, what blocking issue remains, and where the workflow goes next.

The structured `converge.v1` object is an internal workflow/runtime packet. In a normal user-facing final response, render the checkpoint from `user_response` and `ui`; do not print the raw `converge.v1` JSON unless the user explicitly asks for debug or machine output.

Use this shape by default:

```markdown
**Convergence Decision**
...

**Why This Decision**
...

**Agreement Check**
| Question | Developer Side | Evaluator Side | Decision |
| --- | --- | --- | --- |
| ... | ... | ... | ... |

**Goal Alignment**
...

**Remaining Issues**
| Issue | Source | Blocks Completion | Next Owner |
| --- | --- | --- | --- |
| ... | ... | ... | ... |

**Next Step**
...
```

Do not include a "What Will Be Preserved" section in the visible response. Persistence, checkpoint, review-document, and registry details belong in the structured output for downstream skills, not in the user-facing packet.

`Agreement Check` and `Remaining Issues` must be Markdown tables with natural-language cells. Do not expose field names, route assignments, terminal-state strings, fixture ids, synthetic feature ids, finding ids, or unexplained shorthand. Describe the user-visible situation instead, such as "the reviewer found a blocking regression" rather than a finding id.

The normal visible final response MUST include these exact Markdown headings, in this order, even when a section has only one sentence or a not-applicable table:

- `**Convergence Decision**`
- `**Why This Decision**`
- `**Agreement Check**`
- `**Goal Alignment**`
- `**Remaining Issues**`
- `**Next Step**`

Before returning, self-check the captured visible response for the exact headings above and for Markdown tables under `Agreement Check` and `Remaining Issues`. If any heading or required table is missing, rewrite the visible response before finishing. A shorter prose-only convergence checkpoint is not acceptable.

## Done-When Verification Thread

`converge` closes the loop only when the developer and evaluator evidence agrees with the brainstorm done-when criteria. It does not rerun evaluation or invent missing proof; it checks whether the evidence already appended by `develop` and `evaluate` is strong enough to justify completion.

If done-when evidence is absent, generic, or only a weak pass for a criterion that required live proof, return the appropriate evidence or planning route instead of marking the feature done. If the weak pass was explicitly accepted by the brainstorm plan or by evaluator judgment with a visible residual risk, convergence may proceed only when that residual risk does not block the stated criteria.

### Outcome Evaluation And Observability

`converge` should compare the outcome evidence already produced by `develop` and `evaluate`: final state, checkpoint outcomes, rendered output, review evidence, process state, git/file side effects, realistic replay, and trace evidence. Do not require fixed path matching, exact turn-by-turn replay, LLM judges, subagents, worktrees, fan-out execution, or one universal test type by default.

If evaluator evidence labels a deterministic substitute as a weak pass, decide whether the named remaining proof blocks the brainstorm goal. Weak-pass gaps block convergence only when exact runtime telemetry, rendered final output, publish behavior, or trace proof was part of the required outcome.

### Decision Trace Handoff

`converge` closes the decision trace handoff only when developer and evaluator evidence shows decision trace consistency. Check that key decisions, rejected options, allowed implementation discretion, decision invariants, implementation-time decisions, decision deviations, decision drift checks, and hidden decision conflict checks all agree.

If the trace is missing, generic, or conflicted, return the appropriate evidence or planning route instead of marking the feature done: missing brainstorm trace routes to `brainstorm`, missing developer decision evidence routes to `develop`, and missing evaluator drift checks route to `evaluate`.

## Loop Health Advisory

Use the loop-health advisory when the loop evidence suggests that another broad automatic correction would likely repeat the same failure or rely on stale/conflicting context.

Surface a loop-health risk when any of these appear in the latest rounds:

- repeated same-class failures across correction attempts;
- unresolved evidence conflicts between developer claims, evaluator replay, review docs, feature registry state, or runtime output;
- weak replay evidence being treated as full proof for a criterion that needs stronger runtime evidence;
- context contamination, such as stale assumptions from older features, mixed feature identities, or copied findings that no longer match the current changed files;
- round-limit pressure combined with unclear ownership or scope.

The advisory changes the route only when the next safe step is no longer a clear normal correction. Use these routes:

- route to `develop` with a narrower correction when the owner and replay target are clear;
- route to `brainstorm` when acceptance criteria, done-when criteria, or test scope need restating;
- route to `evaluate` when the missing proof is exact runtime replay or evidence reconciliation;
- route to user decision when product intent, stale context, or round-limit pressure cannot be resolved from evidence.

Do not escalate a normal correction loop just because the evaluator found one new, coherent, scoped issue below the round limit. Do not automatically clear context, spawn subagents, create worktrees, or require fan-out execution. Subagents and worktrees remain optional strategies the agent may choose outside the convergence contract.

## Structured Output Contract

Produce this structure for internal workflow handoff:

```json
{
  "schema_version": "converge.v1",
  "raw_user_request": "",
  "source": {
    "from_skill": "evaluate",
    "evaluate_terminal_state": "accepted",
    "feature_id": "",
    "feature_registry_path": ".arbor/workflow/features.json",
    "review_doc_path": "docs/review/<feature>-review.md",
    "evaluator_round_ref": "",
    "feature_registry_signal": {
      "feature_id": "",
      "current_status": "in_evaluate",
      "recommended_next_status": "done"
    }
  },
  "review_context": {
    "brainstorm_context_loaded": true,
    "latest_developer_round_loaded": true,
    "latest_evaluator_round_loaded": true,
    "acceptance_criteria": [],
    "done_when_criteria": [],
    "brainstorm_goals": [],
    "non_goals": [],
    "round_count": 1,
    "round_limit": 3
  },
  "decision": {
    "develop_evaluate_agree": true,
    "brainstorm_goals_satisfied": true,
    "feature_identity_consistent": true,
    "round_limit_reached": false,
    "user_decision_required": false,
    "selected_findings": [],
    "correction_scope": []
  },
  "feature_registry_update": {
    "status": "updated",
    "path": ".arbor/workflow/features.json",
    "feature_id": "",
    "from_status": "in_evaluate",
    "to_status": "done",
    "reason": ""
  },
  "review_append": {
    "status": "appended",
    "path": "docs/review/<feature>-review.md",
    "round_type": "convergence",
    "summary": "",
    "next_loop": []
  },
  "workflow_continuation": {
    "status": "none",
    "next_feature_id": null,
    "next_feature_status": null,
    "next_feature_brainstorm_context_loaded": false,
    "next_skill": "none",
    "reason": ""
  },
  "route": {
    "terminal_state": "converged",
    "next_skill": "none",
    "reason": ""
  },
  "ui": {
    "summary": "",
    "review_focus": [],
    "warnings": [],
    "checkpoint": {
      "visibility": "user_visible",
      "continue_policy": "must_stop",
      "reason": "The convergence decision and any loop/finalization route must be visible before the workflow continues.",
      "resume_after": "user_acknowledgement"
    },
    "workflow_automation": {
      "policy": "develop_evaluate_converge",
      "enabled": false,
      "eligible": false,
      "stop_conditions": [
        "round limit reached",
        "product or design decision required",
        "scope change",
        "missing evidence",
        "blocked convergence",
        "external release action required"
      ]
    }
  },
  "user_response": ""
}
```

Use these enums:

- `source.from_skill`: `evaluate`, `manual_convergence_packet`, or `unknown`
- `source.evaluate_terminal_state`: `accepted`, `changes_requested`, `needs_brainstorm`, `needs_develop_handoff`, `blocked`, `route_correction`, or `unknown`
- `feature_registry_update.status`: `updated`, `not_required`, `blocked`
- `feature_registry_update.to_status`: `done`, `changes_requested`, `in_develop`, `planned`, `blocked`, or `null`
- `review_append.status`: `appended`, `blocker_packet`, `not_required`
- `workflow_continuation.status`: `available`, `none`, or `blocked`
- `workflow_continuation.next_feature_status`: `changes_requested`, `in_develop`, `in_evaluate`, `planned`, or `null`
- `workflow_continuation.next_skill`: `brainstorm`, `develop`, `evaluate`, or `none`
- `route.terminal_state`: `converged`, `needs_develop`, `needs_brainstorm`, `needs_evidence`, `needs_user_decision`, `blocked`, `route_correction`
- `route.next_skill`: `brainstorm`, `develop`, `evaluate`, `converge`, `release`, `none`
- `ui.checkpoint.visibility`: `user_visible`
- `ui.checkpoint.continue_policy`: `must_stop` or `auto_continue_allowed`
- `ui.checkpoint.resume_after`: `user_acknowledgement`, `auto_policy`, `user_decision`, `evidence_loaded`, or `blocker_resolved`
- `ui.workflow_automation.policy`: `develop_evaluate_converge` or `none`

For `converged`, `brainstorm_context_loaded`, `latest_developer_round_loaded`, `latest_evaluator_round_loaded`, `develop_evaluate_agree`, `brainstorm_goals_satisfied`, and `feature_identity_consistent` must all be true; `round_limit_reached` must be false; loaded acceptance criteria, done-when criteria when present, and brainstorm goals must be present; the evaluator signal must report `current_status=in_evaluate` and `recommended_next_status=done`; the registry update must move only the selected feature from `in_evaluate` to `done`; and `route.next_skill` must be `release`. If the evaluator accepted but brainstorm acceptance criteria, done-when criteria, or goals are missing, return `needs_evidence` and route to `brainstorm` instead of marking the feature done.

Keep `route` focused on the current feature's convergence result. `converge` must not advertise next-feature continuation; `workflow_continuation.status` stays `none`, with no next feature id and `next_skill=none`. Release owns next-feature continuation after finalization.

For every terminal state, default to `ui.checkpoint.visibility=user_visible` and `ui.checkpoint.continue_policy=must_stop`. A clear route may still be recorded for the next workflow step, but it is normally a resume target after the visible convergence checkpoint, not permission to continue silently in the same turn. Use `auto_continue_allowed` only when the user explicitly enabled `develop_evaluate_converge` automation and the decision remains inside the current feature loop without any stop condition.

For `converged`, the visible `user_response` must say that release finalization remains next. It must not imply commit, push, publish, or full release has happened.

## Self-Check

Before returning:

1. Did I load feature registry and the shared review document?
2. Did I verify latest developer and evaluator evidence?
3. Did I compare evaluator result with brainstorm goals and acceptance criteria?
4. Did I avoid rerunning evaluate or implementing fixes?
5. Did I route automatic correction loops without asking the user unnecessarily?
6. Did I escalate when round limit, evidence conflict, or product decision required it?
7. Did I update only the selected feature status?
8. Did I append a Convergence Round to the same review document?
9. If uncommitted Arbor workflow changes remain, did I create or refresh `.arbor/memory.md` with the in-flight state and next step?
10. If the feature converged, did I route to internal release and defer next-feature selection?
11. Did I include a user-visible checkpoint that prevents silent continuation into release, next-feature selection, or a correction loop?
12. Did `user_response` make clear that release finalization remains pending after convergence?
13. Did `user_response` explain the decision, agreement check, goal alignment, remaining issues, and next step without leaking internal ids or state codes?
