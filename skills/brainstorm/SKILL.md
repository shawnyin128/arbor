---
name: brainstorm
description: Clarify Arbor-managed requirements, load required evidence, expose hidden decisions, compare approaches, split broad work into independently testable features, and produce a UI-ready structured plan before develop/evaluate begins.
---

# Brainstorm

## Purpose

Use `brainstorm` after `intake` has routed an Arbor-managed request to planning, clarification, impact analysis, or feature breakdown.

`brainstorm` does not implement, execute tests, converge, release, commit, or push. Its terminal output is a structured `brainstorm.v1` plan plus, for ready implementation work, a `.arbor/workflow/features.json` feature registry and a `docs/review/<feature>-review.md` Context/Test Plan section that downstream skills append to.

The terminal state is one of: `needs_clarification`, `needs_evidence`, `ready_for_user_review`, `ready_for_develop`, `route_correction`, or `blocked`.

## Checklist

Follow this normal sequence for brainstorm runs. Stop early with the correct terminal state when route correction, missing evidence, or a blocking clarification prevents later steps.

1. **Confirm route**: accept only Arbor-managed planning work; return `route_correction` if this belongs to direct work, `develop`, `evaluate`, `converge`, or `release`.
2. **Select evidence mode**: choose `pure`, `user_artifact`, `project_context`, `codebase`, `paper`, `paper_and_code`, or `mixed`.
3. **Load required evidence**: read available repo/docs/papers/user artifacts before making settled claims. If required evidence is missing, return `needs_evidence`.
4. **Clarify only blockers**: ask one material question at a time. Do not ask for facts the repo/docs can answer cheaply.
5. **Expose hidden decisions**: surface defaults the user did not specify but that affect implementation, testing, persistence, or user experience.
6. **Split scope**: reduce broad work into small independently testable features.
7. **Plan acceptance and verification**: define acceptance criteria and artifact-appropriate verification scope before routing onward.
8. **Create feature registry**: for ready broad or implementation work, create or update `.arbor/workflow/features.json` with all split features, their statuses, active feature, and review document paths.
9. **Create review context**: for the selected ready feature, create `docs/review/<feature>-review.md` with the Context/Test Plan section unless the request is read-only.
10. **Self-review**: check for missing evidence, hidden assumptions, oversized features, weak test scope, missing registry state, and accidental implementation.
11. **Return structured output first**: emit the UI-ready JSON-shaped plan before any prose explanation.

## Process Flow

```text
Confirm route
-> Evidence mode
-> Evidence loading or needs_evidence
-> Clarification or needs_clarification
-> Hidden decisions
-> Approach comparison
-> Feature split
-> Acceptance criteria and verification plan
-> Feature registry for queue/status tracking
-> Review context artifact for ready plans
-> Self-review
-> Structured output
```

## Core Rules

1. Do not redo `intake` unless new context shows the route is wrong.
2. Do not use artifact or topic keywords as hard boundaries.
3. Do not conclude from evidence that has not been loaded.
4. Ask only questions that materially change the plan.
5. Prefer one pending user question over a questionnaire.
6. Surface hidden decisions explicitly instead of silently choosing defaults.
7. Split large requests into incremental features before implementation planning.
8. Include acceptance criteria and artifact-appropriate review verification for every ready feature.
9. Maintain `features.json` as the feature queue/status index; do not make downstream skills infer progress by scanning review files.
10. Require user approval before `develop` unless the user already clearly approved a narrow low-risk plan.
11. For ready implementation work, create the review Context/Test Plan artifact that `develop` and `evaluate` will append to.
12. Never edit implementation files, run tests, commit, push, or declare validation success inside `brainstorm`.

## Anti-Patterns

### "We Can Plan From The Prompt Alone"

No, not when the plan depends on repo state, code, papers, proposals, logs, or review text. Return `needs_evidence` and list the missing evidence.

### "Ask Everything Up Front"

No. Ask one blocking question at a time. Do not turn brainstorming into a questionnaire.

### "This Is Ready For Develop Because The Process Is Obvious"

No. A ready plan needs concrete scope, features, acceptance criteria, verification scope, unresolved assumptions, and approval state.

### "Brainstorm Can Just Start Editing"

No. Implementation belongs to `develop`. Validation belongs to `evaluate`. Git gates belong to `release`. The only normal file write in `brainstorm` is the review context artifact for a ready Arbor plan.

### "Every Plan Needs A Design Doc"

No. Always emit structured output. A ready implementation plan needs a review context artifact, but broader design docs are still optional and purpose-driven.

### "Develop Can Create The Review Context"

No. `brainstorm` owns the Context/Test Plan section. `develop` appends Developer Rounds against that test scope.

### "Review Files Are Enough To Track Progress"

No. Review documents hold evidence and rounds. `.arbor/workflow/features.json` is the status index for which features exist, which one is active, which are done, and which still need work.

## Evidence Modes

- `pure`: current conversation is sufficient.
- `user_artifact`: requires reading a user-provided proposal, report, notes, review text, or spec.
- `project_context`: requires project files, docs, AGENTS, memory, git status, or recent commits.
- `codebase`: requires reading source code.
- `paper`: requires reading a paper/spec/external document.
- `paper_and_code`: requires both external source material and implementation code.
- `mixed`: combines several of the above.

If the evidence mode requires unavailable evidence, return `terminal_state: needs_evidence` and list exactly what must be loaded next.

## Route Boundaries

Return `route_correction` when:

- the request is direct writing, explanation, or simple file editing with no downstream workflow impact;
- the user is asking for implementation, tests, convergence, or release without unresolved planning work;
- the task belongs to `develop`, `evaluate`, `converge`, `release`, or `none`.

Proceed with `brainstorm` when the request needs:

- requirement clarification;
- hidden decision discovery;
- codebase/paper/artifact-backed engineering analysis;
- approach comparison;
- research or experiment planning;
- broad-to-feature decomposition;
- acceptance criteria and test plan design.

For detailed boundary rationale, read `references/brainstorm-boundary.md`.

## The Process

### Understand The Request

- Start from the `intake` route and raw user request.
- If the request spans multiple independent outcomes, say so before refining details.
- If it is too large for one feature, decompose it and brainstorm the first useful feature.

### Work In Existing Context

- Explore project structure before proposing codebase changes.
- Follow existing patterns unless the current work exposes a real design problem.
- Include targeted cleanup only when it serves the current goal.
- Do not add unrelated refactors to the plan.

### Ask Clarifying Questions

- Ask only when the answer changes scope, design, tests, persistence, or approval.
- Prefer multiple choice when options are clear.
- Keep exactly one pending question in the structured output.
- If evidence can answer the question cheaply, load evidence instead of asking the user.

### Explore Approaches

- Offer alternatives only when there are real alternatives.
- Lead with the recommended approach and explain why.
- Include trade-offs that affect implementation, tests, migration, cost, or user experience.
- Do not force multiple approaches when existing architecture or user instruction constrains the answer.

### Present The Plan

- Scale detail to complexity.
- Cover problem, goals, non-goals, constraints, hidden decisions, features, acceptance criteria, verification scope, risks, and route.
- Make each feature independently understandable and testable.
- Create or update the feature registry so every planned feature has a status and review document path.
- Create the review document Context/Test Plan section for ready implementation work.
- Ask for user approval before `develop` unless approval was already explicit and the task is narrow.

### After The Plan

- If evidence is missing, stop at `needs_evidence`.
- If one user decision blocks planning, stop at `needs_clarification`.
- If the request was misrouted, return `route_correction`.
- If the plan is ready but not approved, return `ready_for_user_review`.
- If the plan is approved and scoped, return `ready_for_develop`.

## Structured Output Contract

Return this structure first:

```json
{
  "schema_version": "brainstorm.v1",
  "raw_user_request": "",
  "source_intake": {
    "arbor_managed": "yes",
    "route_reason": ""
  },
  "evidence": {
    "mode": "project_context",
    "loaded": [],
    "missing": [],
    "cannot_conclude": []
  },
  "clarification": {
    "asked_questions": [],
    "answered_questions": [],
    "pending_question": null
  },
  "problem": {
    "summary": "",
    "goals": [],
    "non_goals": [],
    "constraints": []
  },
  "hidden_decisions": [],
  "approaches": [],
  "recommended_approach": null,
  "features": [],
  "feature_registry": {
    "status": "created",
    "path": ".arbor/workflow/features.json",
    "active_feature_id": "F1",
    "feature_count": 1,
    "created_feature_ids": [],
    "status_summary": {
      "planned": 0,
      "approved": 0,
      "in_develop": 0,
      "in_evaluate": 0,
      "changes_requested": 0,
      "done": 0,
      "blocked": 0,
      "deferred": 0
    }
  },
  "acceptance_criteria": [],
  "test_plan": {
    "strategy": "",
    "required_unit_tests": [],
    "required_scenario_tests": [],
    "edge_cases": [],
    "negative_cases": [],
    "evaluator_focus": []
  },
  "review_doc": {
    "status": "created",
    "path": "docs/review/<feature>-review.md",
    "context_sections": ["Context", "Plan", "Acceptance Criteria", "Test Plan", "Risks"],
    "test_scope_summary": ""
  },
  "risks": [],
  "route": {
    "terminal_state": "ready_for_user_review",
    "next_skill": "develop",
    "requires_user_approval": true,
    "reason": ""
  },
  "ui": {
    "summary": "",
    "review_focus": [],
    "warnings": [],
    "requires_user_decision": true
  },
  "user_response": ""
}
```

Use these enums:

- `source_intake.arbor_managed`: `yes`, `mixed`, `context_dependent`, `uncertain`
- `evidence.mode`: `pure`, `user_artifact`, `project_context`, `codebase`, `paper`, `paper_and_code`, `mixed`
- `route.terminal_state`: `needs_clarification`, `needs_evidence`, `ready_for_user_review`, `ready_for_develop`, `route_correction`, `blocked`
- `route.next_skill`: `brainstorm`, `develop`, `evaluate`, `converge`, `release`, `none`

Keep enum-like fields stable. Do not require the UI to infer terminal state, missing evidence, approval status, or review focus from prose.

For ready features, define verification appropriate to the artifact. Code changes usually need unit tests, scenario tests, edge cases, negative cases, and evaluator focus. Documentation, research plans, workflow artifacts, or other non-code deliverables may use content checks, structure checks, dry runs, schema checks, or workflow scenario checks instead of pretending every artifact has unit tests. `evaluator_focus` guides independent review but is not itself a concrete verification check.

For `ready_for_user_review` and `ready_for_develop`, `review_doc.status` must be `created` unless the request is explicitly read-only or blocked. Non-ready states should use `not_required` or `blocked`.

For `ready_for_user_review` and `ready_for_develop`, `feature_registry.status` must be `created` or `updated`, `feature_registry.path` must be `.arbor/workflow/features.json`, and every feature should have an id, title/name, status, and `review_doc_path`. `feature_registry.status_summary` must match the actual feature rows. Non-ready states should use `not_required` or `blocked`.

For `ready_for_user_review`, newly planned features should start as `planned`. For `ready_for_develop`, the active feature should be `approved`; later skills own `in_develop`, `in_evaluate`, `changes_requested`, `done`, and `blocked`.

## Self-Check

Before returning, check:

1. Did I load the evidence required by the evidence mode, or explicitly return `needs_evidence`?
2. Did I avoid asking questions that repo/docs/artifacts can answer?
3. Did I expose hidden decisions?
4. Did I split broad work into independently testable features?
5. Did I create/update `.arbor/workflow/features.json` with feature statuses, active feature, and review document paths for ready work?
6. Did I include acceptance criteria and artifact-appropriate verification scope for ready features?
7. Did I create the review Context/Test Plan artifact for the selected ready feature?
8. Did I avoid implementation, test execution, commit, push, and release claims?
9. Did I make the next route and approval state explicit?

If any answer fails, revise the structured output before responding.

## Reference Material

- `references/brainstorm-boundary.md`: boundary, persistence, evidence, clarification, scope, and approval rules.
- `references/brainstorm-simulation-cases.md`: regression cases from user simulation.
