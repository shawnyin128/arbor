# Develop Boundary Design

## Purpose

`develop` executes one Arbor-managed feature or managed artifact change with a clear execution basis. It consumes a scoped plan or handoff from known Arbor skills, manually approved project context, or any other source that provides enough executable scope, authorization when needed, success criteria, test expectations, feature registry state, and review context.

The skill combines implementation, developer self-test, and developer review handoff. It does not independently validate like `evaluate`, decide convergence like `converge`, create the brainstorm Context/Test Plan section, or handle git checkpoint/release gates like `release`.

`develop` is intentionally light on how the agent writes code. It should not constrain implementation strategy beyond the upstream contract and the repository's own conventions. Its core value is handoff discipline: consume upstream cleanly, cover the brainstorm test scope with self-tests, append developer evidence, and give downstream `release` a checkpoint packet that preserves state before `evaluate` attacks the work.

## Position In The Workflow

```text
intake -> brainstorm -> develop -> release(checkpoint_develop) -> evaluate -> release(checkpoint_evaluate) -> converge -> release(finalize_feature)
```

`develop` commonly receives one of these upstream states:

- `brainstorm.route.terminal_state=ready_for_develop`;
- `brainstorm.route.terminal_state=ready_for_user_review` after explicit user approval;
- `intake` direct route to `develop` for a clear managed artifact, such as release-bound README, workflow guide, project map, or session resume package;
- `converge` route back to `develop` for changes requested after evaluation.

These are examples, not a closed list. Other upstream sources can be valid when they provide the fallback upstream contract below.

Its terminal state is a `develop.v1` structured output plus code/artifact changes and a developer review entry for downstream `release` checkpointing before `evaluate`.

## Current Flow Being Preserved

The existing Arbor development flow is:

1. Receive one scoped feature or managed artifact.
2. Implement the change.
3. Self-test the change with artifact-appropriate checks, such as unit, integration, scenario, content, structure, dry-run, compile, lint, type, schema, or coverage checks.
4. Append a structured Developer Round to the same existing review document named by `source.review_doc_path` for downstream evaluation.
5. Update the selected feature status in `.arbor/workflow/features.json`.
6. Route to `release` with enough evidence for a developer checkpoint; release then routes the same feature to `evaluate`.

This is intentionally not only coding. Documentation, project maps, workflow guides, and review artifacts can be developed when they are part of the managed development workflow.

## Boundary Summary

Use `develop` for:

- implementing an authorized feature;
- fixing an active bug after diagnosis or a clear current traceback;
- updating a managed development artifact;
- applying evaluator-requested changes after `converge`;
- appending developer-side review evidence for `evaluate`;
- running developer self-tests after implementation.

Do not use `develop` for:

- unresolved requirements or broad scope that still needs `brainstorm`;
- independent validation of completed work, which belongs to `evaluate`;
- deciding whether developer and evaluator agree, which belongs to `converge`;
- commit, push, tag, or release handoff, which belongs to `release`;
- simple direct edits outside Arbor workflow;
- read-only audits or analysis where the user said not to modify anything.

## Upstream Source Contract

Known upstream examples are `brainstorm`, `intake`, and `converge`. They have clear contracts and should be handled with the specific rules below.

Do not limit `develop` to those three sources. Every source, known or fallback, must provide enough of the same minimum contract:

- preserve the raw request or handoff text;
- identify one executable feature or managed artifact scope;
- record execution basis or authorization evidence;
- extract acceptance criteria or equivalent success conditions;
- extract constraints, non-goals, risks, and test expectations when available;
- identify `.arbor/workflow/features.json` or equivalent feature registry when work belongs to a split feature plan;
- identify the review document path and existing Context/Test Plan section for planned Arbor features;
- record stable evidence pointers such as document paths, message ids, review sections, or finding ids.

Known source rules come first because they are the normal Arbor flows. Fallback handling is listed after them and should be used only when the source is outside the known flows.

## Known Source Flows

### `intake`

`intake` may route directly to `develop` only when the artifact or implementation target is already clear and Arbor-managed.

Examples:

- release-bound README update;
- development guide;
- project/data map used for future analysis or agent context;
- session resume package;
- active runtime error that belongs to a current fix.

Consume from `intake`:

- raw user request;
- normalized classification and subtype;
- target artifact or implementation target when present;
- persistence decision, especially whether artifact writes are allowed;
- active-state or context-patch information;
- warnings, permissions, and read-only constraints;
- selected route reason.

When direct-develop input lacks enough detail for safe implementation, `develop` should not invent a full plan. It should either:

- infer the minimum obvious scope when the request is narrow and low-risk;
- return `needs_brainstorm` when requirements, acceptance criteria, or design decisions are missing;
- return `route_correction` when the request should have stayed direct or should go to another skill.

In the review handoff, record that the source was `intake_direct`, quote the raw request, and explain what scope was inferred directly from the request.

### `brainstorm`

`brainstorm` hands off:

- raw request;
- evidence loaded and missing;
- feature list;
- selected feature to implement;
- goals, non-goals, constraints;
- hidden decisions;
- recommended approach;
- acceptance criteria;
- test plan;
- review document path;
- feature registry path;
- risks;
- approval state.

Primary inputs from `brainstorm`:

- selected feature, not the whole feature list when multiple features exist;
- recommended approach;
- goals, non-goals, and constraints;
- acceptance criteria;
- test plan, including artifact-appropriate verification scope and evaluator focus;
- review document path with brainstorm-owned Context/Test Plan section;
- feature registry path with the selected feature entry;
- hidden decisions already resolved by the user or plan;
- unresolved assumptions and risks;
- loaded evidence and source pointers;
- execution authorization state;
- user approval evidence when `brainstorm` ended in `ready_for_user_review`.

Useful but optional inputs:

- design document path;
- feature plan path;
- diagrams or dataflow notes;
- user review notes on the plan;
- previous related review documents.

`develop` should treat the `brainstorm` output as the implementation contract. It can use normal engineering judgment inside that contract, but it should not silently expand scope, reverse resolved decisions, or choose a different product direction.

If implementation reveals missing requirements, major scope changes, or invalid assumptions, return `needs_brainstorm` or record a blocker instead of improvising a new design.

If the brainstorm handoff lacks `.arbor/workflow/features.json`, `docs/review/<feature>-review.md`, or equivalent feature/review context with test scope, return `needs_brainstorm`; do not create the missing brainstorm-owned context inside `develop`.

In the review handoff, record that the source was `brainstorm`, include the selected feature id/title, link or summarize the review context when available, and map implementation/tests back to the upstream acceptance criteria and planned test scope.

## Execution Basis Contract

`develop` does not approve plans. It records why it is allowed to execute.

For the `brainstorm` path, the normal approval point is exactly:

- `brainstorm` designs the plan;
- user approves the plan;
- `develop` consumes that approved plan.

Execution authorization is required when:

- `brainstorm` ended in `ready_for_user_review`, because the plan still needed user approval;
- the upstream plan explicitly requires user approval before implementation;
- the incoming work has external, destructive, or broad side effects.

Execution authorization can be inherited when:

- `brainstorm` ended in `ready_for_develop`;
- `intake` routed a narrow direct managed artifact and no approval gate is required;
- `converge` selected evaluator findings for a correction loop.

Record execution basis as structured evidence:

- `authorization_required`: whether an explicit approval/authorization gate existed;
- `authorization_state`: `authorized`, `not_required`, `missing`, or `rejected`;
- `authorization_source`: where authorization came from, such as `brainstorm_ready_for_develop`, `user_approved_brainstorm_plan`, `intake_direct_request`, or `converge_decision`;
- `authorized_by`: usually `user`, `system`, or `not_applicable`;
- `authorization_evidence`: short quote, message id, brainstorm terminal state, or converge decision that proves why development may proceed;
- `authorization_evidence_refs`: stable pointers such as upstream artifact paths, message ids, review document paths, or finding ids.

Prefer stable references over loose prose. A sentence like "the user approved it" is not enough when explicit authorization is required; quote or point to the approval.

If execution authorization is required but missing, return `blocked` or `needs_brainstorm`; do not self-report `authorization_state=authorized`.

### `converge`

`converge` may send changes requested by `evaluate`. This is not a fresh feature-planning entrypoint; it is a correction loop.

Consume from `converge`:

- convergence decision, such as changes requested, blocked, or needs brainstorm;
- evaluator findings selected for developer action;
- affected review document path;
- previous developer round summary;
- previous evaluator round summary;
- reproduction steps, failing tests, or scenario failures;
- accepted constraints and decisions that must not be reopened;
- requested correction scope.

`develop` should implement only the requested correction scope, preserve evaluator findings, and append a new developer round to the existing review document. It should not rewrite prior rounds or erase evaluator evidence.

If a converge finding changes requirements or reveals a bad plan assumption, route to `needs_brainstorm` instead of treating it as an ordinary fix.

In the review handoff, record that the source was `converge`, reference the evaluator finding ids, list what changed in the new developer round, and identify which evaluator tests should be replayed.

## Fallback Source Flow

Use this only when the source is not one of the known flows above, such as a manual user-approved plan, a project document, a previously written review artifact, a resume packet, or a future Arbor skill.

Fallback source outcomes:

- If the fallback contract is complete enough, execute normally and set `source.from_skill` to a stable label such as `manual_handoff`, `external_plan`, `project_doc`, or the future skill name.
- If source identity is unclear but the work is otherwise valid, use `source.from_skill=unknown` and record evidence in `authorization_evidence_refs`.
- If executable scope is missing, return `needs_selection` or `needs_brainstorm`.
- If authorization is missing, return `blocked`.
- If success conditions or design decisions are missing, return `needs_brainstorm`.

Fallback is not a shortcut around planning. It is a compatibility path for handoffs that already carry enough executable evidence.

## Upstream Source Matrix

This matrix captures common upstream examples, not every possible valid source.

| Source | Main purpose | Must consume | Missing input response | Review handoff emphasis |
| --- | --- | --- | --- | --- |
| `brainstorm` | Implement a user-approved or ready feature plan | selected feature, approach, goals/non-goals, acceptance criteria, review doc path, planned test scope, risks, authorization state | `needs_selection` for no selected feature; `needs_brainstorm` for unresolved design, missing review context, or missing approval | map implementation and self-tests to acceptance criteria and planned test scope |
| `intake` | Direct managed artifact or narrow active implementation | raw request, classification, target artifact/implementation target, persistence/write permission, existing review context, route reason | infer only narrow obvious scope when review context exists; otherwise `needs_brainstorm` or `route_correction` | explain inferred scope from raw request and append to existing review context |
| `converge` | Apply evaluator-requested corrections | review path, evaluator findings, requested correction scope, replay targets, prior rounds | `blocked` if review/finding evidence is missing; `needs_brainstorm` if requirements changed | append new developer round and reference evaluator finding ids |
| fallback source | Execute a valid handoff from another source | raw handoff, scope, authorization evidence, success conditions, constraints, test expectations | `blocked` for missing authorization; `needs_selection` for missing scope; `needs_brainstorm` for missing success conditions or design decisions | explain source identity, inferred contract, and evidence pointers |

## Scope Contract

The default unit is one selected feature or one managed artifact change. A small bundle is acceptable when the upstream plan marks it as atomic or when splitting it would make evaluation less coherent.

The develop unit should be clear enough for downstream evaluation:

- intended outcome;
- upstream acceptance criteria or equivalent success conditions;
- changed files or artifacts after implementation;
- developer self-test evidence;
- evaluator focus.

If the incoming plan contains multiple independent features and no selected unit is clear, return `needs_selection` instead of guessing.

## Implementation Freedom

Within the accepted scope, the agent should use normal senior-engineering judgment and the repository's existing conventions. `develop` should not prescribe file-by-file strategy, coding style, algorithms, abstractions, or exact commands unless those are part of the upstream plan or repo norms.

The only required constraints are contract-level:

- preserve the upstream intent and acceptance criteria;
- record material deviations from the upstream plan;
- avoid overwriting unrelated user work;
- when implementation reveals missing requirements, major scope changes, or invalid assumptions, return `needs_brainstorm`, `needs_selection`, or `blocked` instead of silently changing the product decision.
- do not add unapproved case-specific defensive programming for a single observed input, fixture, prompt, user example, filename, or test case.

When defensive programming is unavoidable, generalize the observed failure into a class of inputs and implement a complete fallback chain at the lowest appropriate layer. The fallback should be reusable, ordered from structured/normal handling to broader recovery, and documented in the Developer Round or `implementation.deviations`. Do not scatter one-off guards through higher-level workflow branches.

## Developer Self-Test

Choose self-tests appropriate to the changed surface. Examples include:

- unit tests for changed logic;
- integration tests for cross-module behavior;
- scenario tests for user/workflow behavior;
- content and structure checks for documentation or research artifacts;
- dry runs and schema checks for workflow or data artifacts;
- lint, type, formatting, compile, or schema checks when the repo supports them;
- coverage when the blast radius or user request makes coverage relevant.

If a test cannot run, record:

- command;
- reason it was skipped or failed to start;
- residual risk;
- recommended evaluator replay.

Developer self-test is not independent validation. Passing self-tests should route to `release` for a developer checkpoint, not directly to `evaluate`, `converge`, or finalization release.

For `ready_for_evaluate`, `planned_test_coverage` must be non-empty, concrete passing check evidence must be present, and `uncovered_planned_tests` must be empty. Concrete result evidence comes from passed self-test table rows or passed `verification_checks` for content checks, structure checks, dry runs, schema checks, compile/lint/type checks, or other checks appropriate to the artifact. Raw command, unit-test, and scenario fields identify targets; they do not prove results by themselves.

Each `verification_checks` item must be replayable evidence, not a vague claim. Record the inspected `artifact`, the `check` performed, the `expected_result`, the `actual_result`, and the pass/fail `result`. Avoid entries such as `looks good`, `manual review passed`, or `checked output`; they do not tell `evaluate` what to attack.

For `ready_for_evaluate`, only `verification_checks` with `result=passed` count as completed evidence. A passed check's `actual_result` must not contradict the result by saying the check was not run, skipped, failed, blocked, or unavailable. If any planned check is skipped, failed, blocked, or not run, record it in `uncovered_planned_tests`, `not_run`, or the relevant failure/blocker evidence and use `self_test_failed`, `blocked`, or another non-ready terminal state instead of routing to `release`.

For `ready_for_evaluate`, `self_test.not_run` must be empty. A ready handoff cannot carry unresolved planned checks in a side field while routing to `release`.

For `ready_for_evaluate`, the raw `self_test.commands`, `self_test.unit_tests`, and `self_test.scenario_tests` fields are identifiers for commands, unit-test targets, and scenario targets. They should not carry result summaries such as passed, failed, skipped, blocked, not run, exit code, assertion error, exception, or traceback. Observed results belong in `review_handoff.self_test_table` or `verification_checks`.

For `self_test_failed`, record the planned checks that were attempted and the planned checks still uncovered or failing.

## Developer Review Handoff

Every successful develop run should append a structured Developer Round to the existing review document created by `brainstorm` under `docs/review/` or the repo's equivalent review location.

`develop` must not create the review document Context/Test Plan section. If the review document is missing for planned Arbor feature work, return `needs_brainstorm` or `blocked` according to whether the missing artifact is a planning gap or an unavailable file.

When `review_handoff.status=appended`, `review_handoff.path` must match `source.review_doc_path`. The Developer Round must land in the same review document that contains the brainstorm Context/Test Plan.

Every appended Developer Round must include a detailed self-test table for downstream `evaluate`. The table should use these columns:

| Column | Meaning |
| --- | --- |
| category | Unit, scenario, integration, content, structure, dry-run, schema, compile/lint/type, coverage, or other artifact-appropriate category. |
| check | The specific developer check performed. |
| evidence | Command, artifact path, fixture, scenario, or inspection target that supports the row. |
| expected | Expected result or pass condition. |
| actual | Actual result observed. |
| result | `passed`, `failed`, `skipped`, or `blocked`. |
| covers | Planned brainstorm test scope, acceptance criterion, or evaluator focus item covered by the row. |

This is not optional prose. It is the canonical review document surface that lets `evaluate` see exactly what the developer tested before running independent checks.

The table is the primary evidence surface. Raw `commands`, `unit_tests`, and `scenario_tests` identify what was run or inspected; `verification_checks` can provide structured supporting result evidence. Do not split result semantics across free-text fields. If any observed result is failed, skipped, blocked, or not run, then the terminal state is not `ready_for_evaluate` and the table must expose the non-passing evidence.

Apply the same evidence semantics to this table as to `self_test.verification_checks`:

- `ready_for_evaluate` table rows must all have `result=passed`;
- `self_test_failed` and `implementation_failed` tables must include at least one `failed`, `skipped`, or `blocked` row;
- every row's `covers` list must be non-empty and include at least one specific planned test label, acceptance criterion, evaluator finding id, or replay target, such as `check:<name>`, `acceptance:<criterion>`, `replay:<target>`, or a finding id;
- generic `covers` values such as `planned check`, `test plan`, or `coverage` are not traceable enough for evaluate;
- feature ids such as `feature:F2` are useful context but are not sufficient by themselves because they do not identify what the row proves;
- `check`, `expected`, and `actual` must be replayable, not vague phrases such as `looks good`, `manual review passed`, or `checked output`;
- a passed row's `actual` must not say the check was not run, skipped, failed, blocked, or unavailable.

## Feature Registry Update

`features.json` is the feature queue and state index. Review documents are not the queue.

When a develop run changes workflow state, update the selected feature in `.arbor/workflow/features.json` or the repo's equivalent feature registry:

- starting implementation: `approved -> in_develop`;
- successful developer handoff: `in_develop -> in_evaluate`;
- developer self-test failure: keep or return to `in_develop` and record the failure in the review handoff;
- implementation blocker: `blocked` when the blocker prevents progress;
- route correction or missing requirements before implementation: no feature status update unless a selected registry feature was already active.

Every update should record:

- registry path;
- feature id;
- previous status when known;
- new status;
- reason;
- review document path or finding reference when useful.

For registry-backed work, `feature_registry_update.feature_id` must match `source.feature_id`. A develop handoff must not implement one feature while moving a different feature to `in_evaluate`.

Downstream skills should be able to read `features.json` to know which features are planned, active, done, blocked, or waiting.

The review entry must include:

- feature identifier and title;
- upstream source label, such as `brainstorm`, `intake`, `converge`, `manual_handoff`, `external_plan`, `project_doc`, or `unknown`;
- raw request or plan pointer;
- implementation summary;
- changed files/artifacts;
- behavioral impact;
- likely affected adjacent features;
- acceptance criteria;
- mapping from brainstorm planned verification scope to developer self-tests;
- a detailed self-test table with category, check, evidence, expected, actual, result, and covers;
- developer self-test commands and results;
- scenario tests and results;
- planned checks not covered and why;
- known risks and residual gaps;
- evaluator focus areas;
- next route, usually `release` with checkpoint intent.

Review documents are durable development evidence. They do not belong in skill `references/`.

## Output Shape

`develop` should emit structured output first:

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
    "notes": []
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
      "next_after_release": "evaluate"
    },
    "reason": "Developer handoff is ready; release should checkpoint before evaluation."
  },
  "ui": {
    "summary": "",
    "review_focus": [],
    "warnings": []
  },
  "user_response": ""
}
```

Use these status values:

- `source.authorization_state`: `authorized`, `not_required`, `missing`, `rejected`
- `source.from_skill`: known skill name or stable fallback source label; do not treat `brainstorm`, `intake`, and `converge` as a closed list
- `implementation.status`: `not_started`, `completed`, `partial`, `failed`
- `self_test.status`: `not_run`, `passed`, `failed`, `partial`, `blocked`
- `self_test.verification_checks`: structured artifact-appropriate evidence with `artifact`, `check`, `expected_result`, `actual_result`, and `result`; only `result=passed` counts as ready evidence, and passed evidence must not contradict itself in `actual_result`
- `self_test.commands`, `self_test.unit_tests`, and `self_test.scenario_tests`: raw identifiers for commands, unit-test targets, and scenario targets; observed results belong in the canonical self-test table or `verification_checks`
- `self_test.not_run`: skipped or unavailable checks; must be empty for `ready_for_evaluate`
- `review_handoff.status`: `not_started`, `appended`, `blocker_packet`, `not_required`
- `review_handoff.handoff_kind`: `success`, `blocker`, `failure`, `route_correction`, `none`
- `review_handoff.blocker_kind`: `missing_authorization`, `missing_selection`, `missing_requirements`, `missing_dependency`, `implementation_error`, `self_test_failure`, `scope_change`, `misroute`, or `null`
- `review_handoff.self_test_table`: detailed test rows written into the Developer Round; required and non-empty whenever `review_handoff.status=appended`
- `route.terminal_state`: `needs_brainstorm`, `needs_selection`, `blocked`, `implementation_failed`, `self_test_failed`, `ready_for_evaluate`, `route_correction`

## User-Facing Development Packet

`user_response` is the inline surface for the user. It is not a debug dump of `develop.v1`; it is a natural-language review packet that lets the user quickly judge whether development did what they expected.

The visible response should include:

| Section | Purpose |
| --- | --- |
| What I Completed | State the implemented change, or clearly state why development did not start. |
| How It Maps To The Plan | Explain how the work maps to the approved plan, selected work item, or evaluator-requested correction. |
| What Changed | Name the changed files or artifacts and describe their practical impact. |
| Implementation Defaults I Chose | Expose implementation-time decisions the user did not explicitly specify, or state that there were no material hidden decisions. |
| How I Self-Tested | Summarize developer-side checks, what each check was proving, and the observed result. |
| Risks And Gaps | List deviations, skipped checks, residual risks, blockers, or missing approvals. |
| Next Step | Say the next workflow step in plain language. For success this is checkpointing before independent evaluation; for blockers this is planning, selection, approval, or stop. |

For tables, every row and column must be written for a human reviewer. Translate internal sources, route reasons, status codes, check identifiers, and feature registry state into ordinary language.

Do not expose internal machine labels in `user_response`, including schema field names, terminal-state strings, route assignments, feature ids, fixture ids, and shorthand such as `dev/eval`. The structured JSON can keep machine-readable values; the visible text should be plain language.

## Terminal States

`develop` can end in:

- `needs_brainstorm`: plan is missing, invalid, or scope-changing assumptions appeared;
- `needs_selection`: multiple independent features exist and no selected feature is clear;
- `blocked`: implementation cannot proceed because required files, permissions, or dependencies are unavailable;
- `implementation_failed`: attempted implementation did not complete;
- `self_test_failed`: implementation completed but developer self-tests failed;
- `ready_for_evaluate`: implementation, self-test, and developer review handoff are complete;
- `route_correction`: request belongs to another skill or direct work.

## Terminal State Matrix

| Terminal state | Implementation status | Self-test status | Review handoff status | Next skill | Required evidence |
| --- | --- | --- | --- | --- | --- |
| `needs_brainstorm` | `not_started` or `partial` | `not_run` or `blocked` | `blocker_packet` or `not_required` | `brainstorm` | missing or invalid requirements, scope-changing assumption, or unresolved product decision |
| `needs_selection` | `not_started` | `not_run` | `not_required` | `brainstorm` | multiple independent features and no selected unit |
| `blocked` | `not_started` or `partial` | `not_run` or `blocked` | `blocker_packet` or `not_required` | `none` | unavailable files, permissions, dependencies, approval, or upstream artifacts |
| `implementation_failed` | `failed` or `partial` | `not_run`, `partial`, or `blocked` | `blocker_packet` or `appended` | `none` | attempted changes, failure point, residual state, and recovery suggestion |
| `self_test_failed` | `completed` or `partial` | `failed` or `partial` | `appended` | `none` | failing commands, failing scenarios, changed files, and evaluator/developer replay focus |
| `ready_for_evaluate` | `completed` | `passed` or `partial` | `appended` | `release` | changed files, self-test evidence, known risks, evaluator focus, and checkpoint intent |
| `route_correction` | `not_started` | `not_run` | `not_required` | appropriate declared route or `none` | reason the request belongs elsewhere |

Only `ready_for_evaluate` may route to `release`, and that route must carry `route.next_skill_context.release_mode=checkpoint_develop` plus `next_after_release=evaluate`. Non-success states must not claim `implementation.status=completed`, `self_test.status=passed`, and `review_handoff.status=appended` together unless the matrix permits it.

Blocked or failed states do not always need a full developer review document. They must still emit enough structured evidence for user review, `brainstorm`, or `converge` to decide the next step. If any code or artifact changed before failure, record those changes and the residual risk.

Use `review_handoff.handoff_kind` and `review_handoff.blocker_kind` so downstream tools can distinguish missing authorization, missing selection, missing requirements, dependency blockers, implementation failure, self-test failure, scope changes, and route corrections without parsing prose.

When adding a new terminal state, update this matrix, the output enums, `develop-simulation-cases.md`, `develop-self-test-results.jsonl`, and `scripts/check_develop_baselines.py` in the same change.

## Self-Review Checklist

Before returning:

1. Did I consume the upstream source and preserve its intent?
2. Did I record execution basis or correctly mark authorization as not required?
3. Did I record any material deviation from the upstream plan?
4. Did I preserve unrelated user work?
5. Did I run appropriate developer self-tests or record why not?
6. Did I append the developer review handoff under `docs/review/` when the run reached handoff state?
7. Did the appended Developer Round include a detailed self-test table for `evaluate`?
8. Did I avoid unapproved case-specific defensive programming, or document a generalized fallback chain at the lowest appropriate layer?
9. Did every self-test table row use specific `covers`, and did raw self-test fields stay as identifiers instead of result summaries?
10. Did the output statuses match the terminal-state matrix?
11. Did I list changed files, impact, tests, risks, and evaluator focus?
12. Did I route to `release` only from `ready_for_evaluate`, with machine-readable checkpoint intent before `evaluate`?
13. Did the visible response expose implementation-time hidden/default decisions in natural language, or explicitly state that there were no material hidden decisions?
14. Did the visible response explain the result in natural language without leaking internal field names, route codes, feature ids, fixture ids, or shorthand?

If any check fails, revise the output or return the appropriate blocked/needs state.
