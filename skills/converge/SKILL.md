---
name: converge
description: Decide whether an Arbor develop/evaluate loop has converged, compare evaluator evidence against brainstorm goals, update feature status only after justified agreement, route correction loops, and escalate to the user when round limits or product decisions block automatic progress.
---

# Converge

## Purpose

Use `converge` after `evaluate` has appended an Evaluator Round for an Arbor-managed feature.

`converge` is a workflow decision skill. It decides whether the latest developer/evaluator loop agrees and whether the result still satisfies the brainstorm Context/Test Plan. After a current feature converges, it routes to internal `release` so the feature can be finalized before the next unfinished feature is selected. It does not implement fixes, run independent adversarial tests, create the brainstorm plan, commit, push, tag, or release.

The normal terminal output is a structured `converge.v1` decision plus a Convergence Round appended to the same review document.

## Checklist

1. **Confirm source**: accept only completed evaluator states or a valid convergence packet. If the request is not a convergence decision, return `route_correction`.
2. **Load workflow state**: read `.arbor/workflow/features.json` and the selected feature's review document.
3. **Load loop evidence**: identify brainstorm Context/Test Plan, latest Developer Round, latest Evaluator Round, evaluator findings, feature-registry signal, and round count.
4. **Check identity**: confirm feature id, review document, registry row, and evaluator signal all point to the same feature.
5. **Check agreement**: decide whether develop and evaluate agree, or whether evaluator findings require another round.
6. **Check brainstorm alignment**: decide whether the accepted result still satisfies brainstorm goals, acceptance criteria, non-goals, and test scope.
7. **Apply loop policy**: route automatically while under the round limit; escalate when the limit is reached or a user/product decision is required.
8. **Update feature registry when justified**: mark `done`, `changes_requested`, `planned`, or `blocked` only for the selected feature.
9. **Append convergence evidence**: append a Convergence Round to the same review document without rewriting prior rounds.
10. **Defer continuation**: after `converged`, route to internal `release`; release selects the next unfinished feature after finalization.
11. **Return structured output first**: emit `converge.v1` before prose.

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
5. Do not mark a feature done unless evaluator accepted and brainstorm goals remain satisfied.
6. Do not update a different feature than the one selected by registry, review document, and evaluator signal.
7. Do not infer convergence from prose alone; require explicit evaluator verdict, findings, and registry signal.
8. Append convergence evidence to the same review document.

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

## Structured Output Contract

Return this structure first:

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
    "warnings": []
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

For `converged`, `brainstorm_context_loaded`, `latest_developer_round_loaded`, `latest_evaluator_round_loaded`, `develop_evaluate_agree`, `brainstorm_goals_satisfied`, and `feature_identity_consistent` must all be true; `round_limit_reached` must be false; loaded acceptance criteria and brainstorm goals must be present; the evaluator signal must report `current_status=in_evaluate` and `recommended_next_status=done`; the registry update must move only the selected feature from `in_evaluate` to `done`; and `route.next_skill` must be `release`. If the evaluator accepted but brainstorm acceptance criteria or goals are missing, return `needs_evidence` and route to `brainstorm` instead of marking the feature done.

Keep `route` focused on the current feature's convergence result. `converge` must not advertise next-feature continuation; `workflow_continuation.status` stays `none`, with no next feature id and `next_skill=none`. Release owns next-feature continuation after finalization.

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
9. If the feature converged, did I route to internal release and defer next-feature selection?
