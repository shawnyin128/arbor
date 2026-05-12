# Evaluate Boundary Design

## Purpose

`evaluate` independently validates one completed Arbor `develop` handoff. It consumes the same shared review document created by `brainstorm` and appended by `develop`, checks the selected feature in `.arbor/workflow/features.json` when present, attacks the implementation with additional tests and probes, appends an Evaluator Round, and routes the result to `release` for checkpointing before `converge`.

It does not implement fixes, approve plans, decide convergence, commit, push, tag, or release.

## Position In The Workflow

```text
intake -> brainstorm -> develop -> release(checkpoint_develop) -> evaluate -> release(checkpoint_evaluate) -> converge -> release(finalize_feature)
```

`evaluate` normally receives:

- `develop.route.terminal_state=ready_for_evaluate`;
- `source.review_doc_path` pointing to the shared review document;
- `source.feature_registry_path` pointing to `.arbor/workflow/features.json` when the feature came from the Arbor feature queue;
- changed files/artifacts;
- developer self-test commands and results;
- developer planned-test coverage and replay targets.

Its terminal state is a structured `evaluate.v1` output plus an Evaluator Round appended to the same review document.

## Boundary Summary

Use `evaluate` for:

- independent validation of implemented Arbor features or managed artifacts;
- replaying developer self-tests;
- running additional unit, scenario, edge, negative, mutation, static, compile, lint, schema, or coverage checks;
- checking whether implementation matches brainstorm acceptance criteria and test plan;
- finding defects, missing test coverage, scope drift, and adjacent regressions;
- appending evaluator evidence to `docs/review/`;
- producing structured findings for `converge`.

Do not use `evaluate` for:

- generic assessment, proposal review, paper judgment, or brainstorming;
- implementation fixes;
- developer self-test handoff creation;
- deciding whether the loop has converged;
- release or git operations;
- simple direct file edits.

## Handoff Contract

`evaluate` requires an evaluator-ready handoff. Minimum input:

- raw request or handoff text;
- `develop.route.terminal_state=ready_for_evaluate` or equivalent;
- feature id/title;
- `source.review_doc_path`;
- Developer Round reference or equivalent developer evidence;
- changed files or artifact changes;
- developer test commands/results;
- developer replay targets;
- known risks.

If this contract is missing, return `needs_develop_handoff`. Do not invent developer evidence.

For completed evaluation states, require `source.from_skill=develop` and `source.develop_terminal_state=ready_for_evaluate`. Future equivalent evaluator-ready packet types must be explicitly modeled with positive and negative fixtures before they can bypass the normal develop handoff.

## Feature Registry Contract

`.arbor/workflow/features.json` is the queue/status index. `evaluate` may read it to confirm which feature is under validation, but it does not finalize feature status.

For a normal brainstorm/develop/evaluate flow:

- `source.feature_registry_path` should be `.arbor/workflow/features.json`;
- the selected feature should correspond to `source.feature_id`;
- the current feature status should normally be `in_evaluate`;
- `evaluate` emits `feature_registry_signal` with the same feature id and a recommended next status;
- `feature_registry_signal.feature_id` must match `source.feature_id`;
- `converge` owns the actual status update.

Recommended next statuses:

- `accepted` recommends `done`;
- `changes_requested` recommends `changes_requested`;
- `needs_brainstorm` recommends `planned`;
- `blocked` recommends `blocked`;
- handoff blockers and route corrections use `null` unless a registry-backed feature is clearly selected.

Do not infer workflow progress by scanning review documents. Review documents contain evidence; `features.json` contains feature queue/status.

## Review Document Contract

The review document must contain:

- brainstorm Context/Test Plan section;
- acceptance criteria;
- required unit tests;
- required scenario tests;
- edge cases and negative cases;
- evaluator focus;
- at least one Developer Round for the current handoff.

If the review document is missing or lacks brainstorm/developer context, return `needs_develop_handoff` unless the problem is an unavailable file or environment dependency, in which case return `blocked`.

When `review_append.status=appended`, `review_append.path` must match `source.review_doc_path`.

For completed evaluation states, the loaded review context must include acceptance criteria and at least one planned test or evaluator-focus dimension: unit tests, scenario tests, edge cases, negative cases, or evaluator focus. `planned_scope_coverage` must map evaluation work back to that loaded scope.

`planned_scope_coverage` entries must name the specific loaded planned item they cover using a stable mapping such as `acceptance:<criterion>`, `unit:<planned test>`, `scenario:<planned scenario>`, `edge:<edge case>`, `negative:<negative case>`, `focus:<evaluator focus>`, `replay:<target>`, or `developer_replay:<target>`. The text after the prefix must match the loaded review scope or replay target. Generic or unrelated entries such as `covered`, `acceptance:covered`, `unit:checked`, or `acceptance:unrelated payment behavior` are not auditable.

## Adversarial Testing Contract

Evaluation should be adversarial. It should try to disprove the developer handoff, not merely confirm it.

Minimum evaluation surface:

- replay important developer commands or explain why they were not replayed;
- inspect changed files/artifacts;
- map checks to brainstorm acceptance criteria;
- cover required unit tests, required scenario tests, edge cases, negative cases, and evaluator focus;
- add at least one independent check for completed evaluation unless the change is documentation-only and the review plan justifies content/scenario checks instead;
- record blocked/skipped checks and residual risk.

Use repo conventions for commands. Do not add permanent implementation changes. Temporary probes should be cleaned up or clearly recorded.

Evaluator evidence lists such as `developer_replay`, `additional_unit_tests`, `additional_scenario_tests`, `edge_negative_tests`, and `mutation_or_static_probes` must contain replayable commands, checks, scenarios, or inspection targets plus an observed result. Do not use vague entries such as `checked output`, `checked parser output`, `manually reviewed UI`, `looks good`, or `good enough`.

## Findings

Findings should be structured and actionable:

- `id`: stable finding id such as `EVAL-R1-001`;
- `priority`: `P0`, `P1`, `P2`, `P3`, or `N/A`;
- `type`: `bug`, `test_gap`, `scope_drift`, `requirements_gap`, `blocked`, or `route`;
- `location`: file/path/section/command when available;
- `evidence`: what failed or what was inspected;
- `recommendation`: what should change;
- `blocks_acceptance`: boolean.

Blocking findings route to `changes_requested` unless the issue is unclear requirements or invalid planning scope, which routes to `needs_brainstorm`.

## User-Readable Scenario Output

`evaluate` should produce scenario summaries that a user can understand without reading code, JSON fixtures, or mutation details.

Test-matrix rows should also stand alone. Each row must include a concrete representative example of the exact replay or check, not only a category label, case count, and pass rate. If a reader cannot tell what was copied, changed, replayed, or inspected from the table row itself, the row is not readable enough.

Each user-readable scenario should include:

- `scenario`: the workflow situation in plain language;
- `simulated_situation`: what was replayed, checked, or changed;
- `what_this_proves`: the safety property or risk being tested;
- `actual_result`: the user-visible outcome;
- `evidence`: optional supporting commands, fields, fixture ids, or mutation details.

Do not make internal terms such as `Case 1`, enum values, field paths, mutation syntax, or synthetic ids such as `F2`, `ABC-123`, or `feature-001` the primary explanation. They are allowed in `evidence` after the workflow-level explanation.

Examples:

- Prefer: "Development was not actually ready for evaluation."
- Avoid: "Case 1 `source.develop_terminal_state=ready_for_evaluate -> self_test_failed`."
- Prefer: "The evaluator wrote to the wrong review file."
- Avoid: "`review_append.path != source.review_doc_path`."
- Prefer test-matrix example: "Copied a completed handoff and changed its source from develop to a manual packet."
- Avoid test-matrix example: "Source-gate adversarial replay."

## User-Facing Evaluation Packet

`user_response` is the inline summary for the user. It should be review-oriented: lead with the verdict and findings, then show enough evidence for the user to understand why the evaluator reached that result.

Use these sections:

| Section | Purpose |
| --- | --- |
| Evaluation Verdict | State whether the work passed independent evaluation, needs changes, needs planning, needs a developer handoff, is blocked, or was misrouted. |
| Findings First | List blocking findings first, or state that no blocking findings were found. |
| How I Challenged The Work | Explain adversarial scenarios, edge cases, negative cases, mutation/static probes, or why they were blocked. |
| Plan Coverage | Explain how checks map back to acceptance criteria and planned test scope in user-level language. |
| What I Checked | Summarize developer replay, inspected artifacts, and evaluator-added checks after the attack strategy and plan coverage are clear. |
| Unit Tests | Use a Markdown table to explain concrete unit-level checks in natural language, including what behavior each check exercised and the observed result. |
| Scenario Tests | Use a Markdown table to explain concrete workflow or user-situation checks in natural language, including what scenario each check exercised and the observed result. |
| Other Checks | Explain edge, negative, mutation, static, content, structure, coverage, or blocked checks that do not fit unit or scenario tests. |
| Evaluator Judgments I Made | Expose evaluation-time judgment calls, such as whether a missing test blocks acceptance, whether a failure belongs to implementation or planning, or why documentation was validated with content/scenario checks. |
| Risks And Gaps | Record blocked checks, skipped checks, residual risk, and uncertainty. |
| Next Step | Explain where the workflow goes next in plain language. |

Put `How I Challenged The Work` and `Plan Coverage` before `What I Checked`. The user should first understand the evaluation strategy and the relationship to the plan, then inspect the detailed test list.

`Unit Tests` and `Scenario Tests` must be tables with human-readable columns such as `Check`, `Behavior Covered`, `Expected`, `Actual`, and `Result`. If a category is not applicable or could not run, include a table row that explains why instead of omitting the section.

The visible text must not require the user to know the structured schema. Do not expose field names, assignment-style routes, terminal-state strings, fixture ids, synthetic feature ids, or unexplained shorthand. Keep internal evidence in structured fields or secondary evidence lists; primary prose should explain the workflow situation and user-visible risk.

## Relationship To Other Skills

### `develop`

`develop` creates implementation and developer evidence. `evaluate` consumes it, replays it, and challenges it.

If developer evidence is missing, return `needs_develop_handoff`. If evaluator finds implementation defects, append findings and route to `release` for checkpointing before `converge`; do not fix the defects directly.

### `brainstorm`

`brainstorm` owns the Context/Test Plan. `evaluate` checks whether the implementation and developer self-tests cover that plan.

If evaluation reveals missing or contradictory requirements, invalid acceptance criteria, or a bad test plan, route `needs_brainstorm` to `release` for checkpointing before `converge`.

### `converge`

`converge` decides whether the loop is accepted, changes are requested, more planning is needed, or the work is blocked.

`evaluate` provides the evidence and recommended direction, but it does not make the final convergence decision or mark a feature done in the registry.

## Status Matrix

| Terminal state | Evaluation status | Review append status | Finding requirement | Next skill |
| --- | --- | --- | --- | --- |
| `accepted` | `passed` | `appended` | zero blocking findings | `release` |
| `changes_requested` | `failed` or `partial` | `appended` | one or more blocking implementation/test findings | `release` |
| `needs_brainstorm` | `blocked` or `partial` | `appended` | requirements, acceptance, or test-plan finding | `release` |
| `needs_develop_handoff` | `not_started` or `blocked` | `not_required` or `blocker_packet` | missing/invalid developer handoff | `develop` |
| `blocked` | `blocked` | `blocker_packet` or `not_required` | unavailable environment/file/dependency | `none` |
| `route_correction` | `not_started` | `not_required` | route issue | declared route or `none` |

Only `accepted`, `changes_requested`, and `needs_brainstorm` may route to `release`. That route must carry `route.next_skill_context.release_mode=checkpoint_evaluate` plus `next_after_release=converge`; release then routes the same evaluator evidence to `converge`.

## Output Shape

`evaluate` should emit structured output first:

```json
{
  "schema_version": "evaluate.v1",
  "raw_user_request": "",
  "source": {
    "from_skill": "develop",
    "develop_terminal_state": "ready_for_evaluate",
    "feature_id": "",
    "feature_registry_path": ".arbor/workflow/features.json",
    "review_doc_path": "docs/review/<feature>-review.md",
    "developer_round_ref": "",
    "changed_files": [],
    "artifact_changes": [],
    "developer_replay_targets": []
  },
  "review_context": {
    "brainstorm_context_loaded": true,
    "developer_round_loaded": true,
    "acceptance_criteria": [],
    "planned_unit_tests": [],
    "planned_scenario_tests": [],
    "edge_cases": [],
    "negative_cases": [],
    "evaluator_focus": []
  },
  "evaluation": {
    "status": "passed",
    "strategy": "adversarial",
    "developer_replay": [],
    "additional_unit_tests": [],
    "additional_scenario_tests": [],
    "edge_negative_tests": [],
    "mutation_or_static_probes": [],
    "coverage": null,
    "planned_scope_coverage": [],
    "blocked_checks": [],
    "findings": []
  },
  "review_append": {
    "status": "appended",
    "path": "docs/review/<feature>-review.md",
    "round_type": "evaluator",
    "finding_count": 0,
    "blocking_finding_count": 0,
    "replay_targets": []
  },
  "feature_registry_signal": {
    "status": "not_updated",
    "path": ".arbor/workflow/features.json",
    "feature_id": "",
    "current_status": "in_evaluate",
    "recommended_next_status": "done",
    "reason": "converge owns final feature status update"
  },
  "route": {
    "terminal_state": "accepted",
    "next_skill": "release",
    "next_skill_context": {
      "release_mode": "checkpoint_evaluate",
      "next_after_release": "converge"
    },
    "reason": "Evaluator evidence is appended; release should checkpoint before converge."
  },
  "ui": {
    "summary": "",
    "review_focus": [],
    "warnings": [],
    "scenario_tests": [
      {
        "scenario": "",
        "simulated_situation": "",
        "what_this_proves": "",
        "actual_result": "",
        "evidence": []
      }
    ]
  },
  "user_response": ""
}
```

## Self-Review Checklist

Before returning:

1. Did I verify a valid developer handoff?
2. Did I load brainstorm Context/Test Plan and Developer Round from the same review document?
3. Did I read `.arbor/workflow/features.json` when the handoff included it?
4. Did I inspect actual files/artifacts when available?
5. Did I replay or explicitly decline developer checks with reason?
6. Did I add independent adversarial checks?
7. Did I map checks to planned scope?
8. Did I append an Evaluator Round to the same review document?
9. Did I route completed evaluation states only to `release`, with machine-readable checkpoint intent before `converge`?
10. Did I emit a feature-registry signal instead of directly finalizing status?
11. Did every test-matrix row include a concrete representative example and every scenario row start with a human workflow situation instead of a synthetic id?
12. Did `planned_scope_coverage` and evaluator evidence name concrete planned scope and replayable checks instead of generic phrases?
13. Did the visible response lead with verdict and findings, then explain checks, adversarial coverage, evaluator judgments, risks, and next step without leaking internal field names or codes?
