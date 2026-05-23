# Brainstorm Boundary Design

## Purpose

`brainstorm` turns an Arbor-managed engineering request into a collaborative, reviewable plan. It combines clarification and planning, but it does not implement, execute tests, converge, release, or manage every kind of thinking.

For ready implementation work, `brainstorm` also creates or updates `.arbor/workflow/features.json` and creates the shared review document at `docs/review/<feature>-review.md`. The feature registry tracks queue/status. The review document holds Context/Test Plan and later internal developer/evaluator evidence under `converge`.

The skill is the public planning entrypoint for requests that belong in Arbor and need clarification, design, impact analysis, or feature planning.

## Position In The Workflow

```text
brainstorm -> converge
  -> internal develop -> release(checkpoint_develop)
  -> internal evaluate -> release(checkpoint_evaluate)
  -> converge decision
-> release(finalize_feature)
```

`brainstorm` receives an Arbor-managed request or active context. It returns a structured plan that can be reviewed by a user or UI and then routed to the public `converge` quality loop.

Its terminal state is a `brainstorm.v1` structured output plus, for ready implementation work, an initialized feature registry and review document. It must not make implementation code changes.

## Boundary Summary

`brainstorm` must not use artifact or topic keywords as hard boundaries. It should decide from user intent, evidence needs, and whether the answer will change engineering or research workflow.

Use `brainstorm` for:

- clarifying requirements;
- exposing hidden design decisions;
- understanding current project context before design;
- codebase-backed impact analysis;
- paper/spec/code-backed engineering analysis;
- proposal/report/reviewer/spec-backed research or experiment planning when the user is using the artifact as technical evidence;
- comparing viable approaches and trade-offs;
- reducing broad requests into smaller features;
- defining acceptance criteria;
- defining implementation plan outline;
- defining artifact-appropriate verification principles, such as unit tests, scenario checks, edge/negative cases, content checks, structure checks, dry runs, schema checks, or evaluator focus;
- creating or updating `.arbor/workflow/features.json` as the feature queue/status index;
- creating the `docs/review/<feature>-review.md` Context/Test Plan section for ready implementation work;
- deciding whether a task is ready for the `converge` quality loop.

Usually keep work outside `brainstorm` when the user intent is only:

- direct answers or ordinary knowledge questions;
- single-file explanations without optimization, design, or implementation planning;
- writing, reviewer reasoning, or argumentation that does not change experiment or implementation planning;
- simple file edits whose scope is already clear;
- direct implementation;
- running tests or coverage;
- developer/evaluator convergence decisions;
- commit, push, or release preflight.

These are not hard exclusions. The same prompt shape can enter `brainstorm` if it affects feature scope, research direction, implementation strategy, experiment design, evaluation strategy, project memory, or future agent behavior.

## Relationship To Other Skills

### Public Entrypoints

`brainstorm` owns planning. It should classify only enough boundary context to decide whether the current request needs managed planning, direct handling, or another explicit workflow skill.

If the request is a simple direct answer, an already authorized quality-loop continuation, an independent validation request with existing review context, a convergence decision, or a release gate, return a structured `route_correction` rather than silently changing scope. Public requests to implement, repair, evaluate, verify, or continue existing Arbor work belong to `converge`, not public `develop` or public `evaluate`.

### `develop`

`develop` is an internal stage that implements an approved feature or managed artifact when `converge` or an equivalent workflow handoff drives it.

`brainstorm` may outline implementation steps and create the review Context/Test Plan artifact, but must not edit implementation files, scaffold code, or run formatting/test commands as implementation work.

### `evaluate`

`evaluate` is an internal stage that independently validates implemented changes through tests, coverage, scenarios, and adversarial checks when `converge` or an equivalent workflow handoff drives it.

`brainstorm` writes the test plan in the review document, but it must not claim validation has passed.

### `converge`

`converge` decides whether the developer/evaluator loop is accepted, changes-requested, blocked, or needs more planning.

`brainstorm` may receive work from `converge` when findings reveal unclear requirements or bad design assumptions.

### `release`

`release` handles git and release gates.

`brainstorm` can note release considerations but must not commit, push, tag, or declare release readiness.

## Borrowed From Superpowers Brainstorming

We should borrow these ideas:

- explore project context before detailed questions;
- ask one question at a time;
- ask for approval or correction when a plan is ready but still needs user review;
- detect over-broad requests early;
- propose alternatives with trade-offs when meaningful;
- recommend an approach with reasoning;
- present a design before implementation;
- self-review the spec for placeholders, contradictions, ambiguous requirements, and scope creep;
- require user approval before implementation.

We should not copy these parts directly:

- forcing brainstorming for all creative work;
- always writing to a fixed design-doc path regardless of artifact purpose;
- committing design documents from brainstorm;
- using a visual companion in the skill layer;
- having a fixed next skill like `writing-plans`;
- treating every simple change as needing a full design process.

`brainstorm` should remain scoped to Arbor-managed engineering work. It must not become a universal hidden router for every technical request.

## Documentation And Persistence Boundary

`brainstorm` makes the documentation decision only for planning work it owns:

- outside Arbor: documentation or writing whose only purpose is human presentation, prose, submission support, or one-off conversation recovery;
- another explicit workflow skill: already scoped implementation, evaluation, convergence, or release work with the required upstream evidence;
- `brainstorm`: requests where the document is really the outcome of unresolved design, planning, impact analysis, or feature breakdown.

This is an intent boundary, not a document-type boundary. A README, report, proposal, paper response, or project summary can enter Arbor when it drives development, experiments, evaluation, context recovery, or agent workflow rules.

`brainstorm` should not take over all documentation requests. It only decides persistence for plans it is already responsible for.

Every brainstorm must produce structured `brainstorm.v1` output. That output may remain in conversation/UI state unless durable handoff is needed.

For ready implementation work, durable handoff is always needed:

- create or update `.arbor/workflow/features.json` as the feature queue/status index;
- create `docs/review/<feature>-review.md` with the Context/Test Plan section for the selected feature.

The review document is not a design doc and not the feature queue. It is the shared evidence contract for one feature. `features.json` answers which features exist, which one is active, which are done, and which still need work.

### Feature Registry

`features.json` should live at `.arbor/workflow/features.json`.

It should use `schema_version: features.v1` and include:

- source brainstorm id or raw request pointer;
- `active_feature_id`;
- one entry per planned feature;
- stable feature ids;
- title/name and short summary;
- status;
- priority/order;
- dependencies;
- `review_doc_path`;
- acceptance criteria summary or pointers;
- test scope summary;
- timestamps or source refs when available.

Allowed feature statuses:

- `planned`: feature exists but is not approved for implementation;
- `approved`: selected or approved to enter the converge-owned quality loop;
- `in_develop`: develop is actively implementing it;
- `in_evaluate`: develop handed it to evaluate;
- `changes_requested`: evaluator/converge requested another develop round;
- `done`: converge accepted the feature;
- `blocked`: progress is blocked;
- `deferred`: intentionally postponed.

Status integrity rules:

- `feature_registry.status_summary` must be recomputable from the emitted feature rows;
- `ready_for_user_review` should create newly split features as `planned`;
- `ready_for_converge` should mark the active selected feature as `approved`;
- `brainstorm` should not mark newly planned work as `done`, `in_evaluate`, or `changes_requested`.

`features.json` and review docs are one-to-one at the feature level: every registry feature should have a `review_doc_path`, and each ready feature review doc should correspond to exactly one registry feature.

Do not use review docs as the only progress index. Downstream skills should not have to scan review files to know what remains unfinished.

The initial review document should include:

- raw request and source entrypoint;
- selected feature id/title;
- problem summary, goals, non-goals, and constraints;
- hidden decisions and resolved assumptions;
- decision trace handoff with key decisions, rejected options, allowed implementation discretion, and decision invariants;
- optional delegation packet and effort budget when separable evidence gathering would help, including objective, output format, tools/sources, boundaries, effort budget, context pointers, stop conditions, and when not to delegate;
- selected approach and rejected alternatives when relevant;
- acceptance criteria;
- done-when criteria and the artifact-appropriate verification method for each criterion;
- verification scope appropriate to the artifact, such as unit tests, scenario checks, edge/negative cases, content checks, structure checks, dry runs, schema checks, or evaluator focus;
- known risks and remaining assumptions;
- approval state and next route.

Do not create the review document when the terminal state is `route_correction`
or `blocked`.

For `needs_evidence` or `needs_clarification`, create the feature registry and
review Context/Test Plan only when the loaded evidence already supports a
useful provisional feature split or durable planning checkpoint. The artifact
must name the blocker, pending question, non-goals, provisional acceptance
criteria, and the evidence required before implementation. If the request is
too vague to define a responsible provisional scope, keep the registry and
review document `not_required`.

Write or recommend durable artifacts when:

- `converge` and its internal implementation/validation stages need the plan;
- feature scope, acceptance criteria, or test plan must survive across sessions;
- future agents need the information for context recovery;
- the content is a stable project map or development reference.

Choose artifact targets by purpose:

- workflow state: `.arbor/workflow/*`;
- feature queue/status index: `.arbor/workflow/features.json`;
- shared review plan: `docs/review/<feature>-review.md`;
- feature plan or supplementary design reference: `docs/features/*` or equivalent project convention;
- project map or context entrypoint: `AGENTS.md` with concise pointers;
- detailed durable reference: `docs/*` linked from `AGENTS.md`.

### Done-When Verification Thread

For ready Arbor-managed implementation work, `brainstorm` starts the done-when verification thread before the converge-owned quality loop. It should describe what completion means in outcome language, map each criterion to artifact-appropriate verification, and name any weak evidence risk when exact live proof may not be available.

Each done-when criterion should name the user-visible or workflow-visible
outcome, the minimum acceptable proof, and the evidence owner when proof belongs
to `develop`, `evaluate`, or `release`. Avoid vague placeholders such as "tests
pass", "looks good", "verify it", or "coverage" unless the criterion also names
the concrete artifact, command, scenario, expected result, and owner.

Do not force one test type. A feature may need unit tests, scenario replay, content/structure checks, rendered-output inspection, static/schema checks, mutation probes, or live runtime evidence depending on what the feature changes. Small direct tasks stay outside this thread.

### Decision Trace Handoff

For ready Arbor-managed implementation work, `brainstorm` also starts the decision trace handoff. The Context/Test Plan should record key decisions, rejected options, allowed implementation discretion, and decision invariants so `develop`, `evaluate`, and `converge` do not lose or rewrite upstream intent.

This is workflow evidence, not a default multi-agent orchestration model. The trace must not require subagents or worktrees, fixed fan-out, or a fixed implementation strategy, and it must not pull small direct tasks into Arbor.

### Delegation Packet And Effort Budget

For ready Arbor-managed work, `brainstorm` may include optional delegation packet and effort budget guidance when the planned evidence work is separable. The packet should include objective, output format, tools/sources, boundaries, effort budget, context pointers, stop conditions, and when not to delegate.

Use the packet to reduce duplicated work and missing coverage, not to force fan-out. Direct answers, simple edits, tightly coupled coding, and tightly coupled workflow changes remain single-threaded by default. The guidance must not require subagents or worktrees, parallel coding, fixed tool-call counts, or a fixed implementation strategy.

Do not write durable artifacts when:

- the user requested read-only work;
- the discussion is still early and key decisions are missing;
- the user only asked for chat/UI analysis;
- the artifact is a writing deliverable rather than a development-serving artifact.

## Evidence Modes

Every brainstorm should declare its evidence mode:

- `pure`: reasoning from current conversation only;
- `user_artifact`: requires reading a user-provided artifact such as a proposal, report, notes, or reviewer text as planning evidence;
- `project_context`: requires project files, docs, AGENTS, memory, git status, or recent commits;
- `codebase`: requires reading source code;
- `paper`: requires reading a paper/spec/external document;
- `paper_and_code`: requires both external source material and implementation code;
- `mixed`: combines several of the above.

If a conclusion depends on evidence that has not been loaded, `brainstorm` must not present it as settled.

## Clarification Rules

Ask questions when the answer materially affects the plan or when a ready plan
needs explicit user approval/correction before the quality loop. This is not a broad
questionnaire; it is the collaboration loop that lets the user refine the
problem and verify that the agent understood it.

Rules:

- ask one question at a time;
- prefer short multiple-choice questions when the options are clear;
- use open-ended questions when the design space is genuinely unknown;
- do not ask for information the codebase or docs can answer cheaply;
- do not ask questions just to imitate process;
- record the clarification history available in `clarification.asked_questions`,
  including the current visible question when one is asked;
- set `clarification.pending_question` only for the current question when the
  answer blocks planning;
- treat "one question at a time" as pacing, not as permission to stop after one
  answer; after each answer, re-check hidden decisions and ask the next material
  question if scope, non-goals, validation, defaults, or approval remain unclear;
- for `ready_for_user_review`, ask for approval or correction under `Next`
  about the feature split, priority, interpretation, or the most important
  default;
- do not make `Next` plan-only when user review is still required;
- expose hidden decisions even if the user did not mention them.

Hidden decisions include:

- persistence format;
- active-state behavior;
- artifact location;
- compatibility and migration rules;
- testing scope;
- failure and rollback behavior;
- user approval gates;
- cost/performance trade-offs;
- cross-runtime differences;
- evidence source requirements.

## Scope Control

If the request is too broad for one implementation unit, `brainstorm` must split it before planning details.

Feature split rules:

- each feature should have one clear user-visible or workflow-visible outcome;
- each feature should be implementable and testable independently;
- each feature should have a status in `features.json`;
- each feature should point to one review document;
- shared infrastructure can be a feature only if it directly unlocks later features;
- avoid bundling unrelated refactors;
- prefer incremental delivery over one large redesign;
- preserve the user's active priority.

## Approach Comparison

Offer multiple approaches when there are real alternatives.

Do not force 2-3 approaches when the correct path is constrained by existing architecture, user instruction, or compatibility requirements.

When approaches are useful, include:

- approach name;
- summary;
- benefits;
- risks;
- implementation cost;
- test implications;
- recommendation.

## Required Output Shape

`brainstorm` should produce structured output for runtime and put the user-facing inline review packet in `user_response`. The raw `brainstorm.v1` object is an internal workflow packet; normal user-facing output should render `user_response` and `ui`, not print the raw JSON unless explicit debug output is requested.

```json
{
  "schema_version": "brainstorm.v1",
  "raw_user_request": "",
  "source_entrypoint": {
    "entrypoint": "brainstorm",
    "arbor_managed": "yes",
    "reason": ""
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
  "done_when_criteria": [
    {
      "criterion": "",
      "verification_method": "",
      "evidence_owner": "develop|evaluate|release",
      "weak_evidence_risk": null
    }
  ],
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
    "context_sections": ["Context", "Plan", "Acceptance Criteria", "Done-When Criteria", "Test Plan", "Risks"],
    "test_scope_summary": ""
  },
  "risks": [],
  "route": {
    "terminal_state": "ready_for_user_review",
    "next_skill": "converge",
    "requires_user_approval": true,
    "reason": ""
  },
  "ui": {
    "summary": "",
    "review_focus": [],
    "warnings": [],
    "requires_user_decision": true,
    "checkpoint": {
      "visibility": "user_visible",
      "continue_policy": "must_stop",
      "reason": "The plan, feature split, hidden decisions, and test goals must be visible before implementation begins.",
      "resume_after": "user_approval"
    }
  },
  "user_response": ""
}
```

## Checkpoint Policy

`brainstorm` is always a user-visible checkpoint. The output must include `ui.checkpoint.visibility=user_visible` and `ui.checkpoint.continue_policy=must_stop`.

The next public skill may be `converge`, but that route is a resume target after the user reviews the plan. It is not permission to silently continue into implementation or validation in the same final response.

## Inline Review Packet

The visible `user_response` should lower user review cost. It should answer five plain questions:

1. How is the problem being framed?
2. What small steps should the work be split into?
3. How will each small step be verified?
4. What defaults or assumptions did the agent make that the user did not state?
5. What will the user get when the idea is finished?

It should also ask or request one plain user response for the current turn. For
blocked plans, ask the next blocking clarification question. For reviewable
plans, ask for approval or correction of the plan's most important assumption.
Do not replace that request with a statement of the next action. If the user
answers with a new uncertainty, continue the clarification loop instead of
treating the first answer as enough.

Use these section headings exactly for every normal English user-visible
brainstorm checkpoint. Do not rename them to alternatives such as "Planning
Checkpoint", "Goal", "Recommended Plan", or "Acceptance Criteria"; those
concepts belong inside the fixed sections so live rendered output stays
predictable. When the user's active chat language is not English, render
localized heading equivalents in the same order with the same section meaning
and required table sections. Do not fall back to English headings only because
this reference is written in English.

Use this natural-language shape by default:

```markdown
**Understanding And Recommendation**

**How I Would Handle This**
...

**Suggested Small Steps**
...

**How I Would Validate Each Step**
...

**Default Decisions I Made**
...

**Expected Delivery**
...

**Next**
...
```

Avoid exposing machine names such as `feature_registry`, `review_doc`, `terminal_state`, `evaluator_focus`, `source_entrypoint`, or `route` in the primary inline text. The structured fields still keep those machine concepts for runtime and later UI work.

The visible tables must paraphrase structured data. Do not paste internal feature labels, test labels, status labels, or handoff phrases into user-facing cells. Each row should describe the user-level action, why it matters, and how completion is recognized. A reader should not need to know Arbor internals to understand a row.

Do not show internal shorthand in the primary inline text. Status strings such as `ready_for_converge`, route assignments such as `next_skill=converge`, feature ids such as `F1`, fixture ids such as `Case 2`, and abbreviations such as `RFQ` or `dev/eval` must be translated into plain user-facing language.

Final response preflight must run on the exact final assistant message, not only
on the internal `user_response` draft. The final message must keep the standard
brainstorm headings in order for English prompts, or localized equivalents in
the same order for non-English prompts. It must preserve the table sections as
Markdown tables, ask the current blocking, approval, or correction question, and
avoid collapsing into a plan-only, artifact-list, status-paragraph, or
prose-only summary. Even blocked, needs-evidence, and needs-clarification
outcomes must render the full checkpoint shape with blocked or not-applicable
table rows.

## Terminal States

`brainstorm` can end in one of these states:

- `needs_clarification`: one pending user question blocks planning;
- `needs_evidence`: code/docs/paper must be read before conclusion;
- `ready_for_user_review`: a plan exists but needs user approval;
- `ready_for_converge`: user has approved a sufficiently scoped feature plan;
- `route_correction`: this should not be handled by `brainstorm`;
- `blocked`: progress requires unavailable information or permission.

It must not end by making implementation code changes.

For `ready_for_user_review` and `ready_for_converge`, it should create or update the feature registry and create the review Context/Test Plan document unless explicitly read-only. For non-ready states, `feature_registry.status` and `review_doc.status` should be `not_required` or `blocked`.

## Approval Gate

Implementation requires explicit user approval unless the user already clearly asked to proceed and the plan is low-risk, narrow, and fully specified.

Even then, `brainstorm` should output the plan and route to `converge`; it should not perform the implementation itself.

## Self-Review Checklist

Before returning a final brainstorm plan, check:

1. Did I load the evidence required by the evidence mode?
2. Did I avoid asking questions that the repo can answer?
3. Did I ask the next material blocking question or request approval/correction instead of producing a plan-only checkpoint?
4. Did I avoid treating "one question at a time" as "only one question total"?
5. Did I expose hidden decisions?
6. Did I split broad work into independently testable features?
7. Did I create/update `.arbor/workflow/features.json` so feature status does not have to be inferred from review files?
8. Did I define acceptance criteria?
9. Did I define artifact-appropriate concrete verification checks, with evaluator focus as review guidance rather than the only check?
10. Did I create the review Context/Test Plan document for ready implementation work?
11. Did I avoid implementation?
12. Did I identify unresolved assumptions?
13. Did I make the next route explicit?
14. Did I make the inline response understandable without Arbor-internal field names?
15. Did I paraphrase internal labels into user-level action and verification language?
16. Did I translate status codes, feature ids, fixture ids, and abbreviations before writing visible text?
17. Did I run final response preflight on the exact final message and reject status-paragraph or artifact-list output?

If any check fails, revise the output or return `needs_clarification` / `needs_evidence`.
