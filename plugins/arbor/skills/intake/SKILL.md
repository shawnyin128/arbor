---
name: intake
description: Automatically triage possible Arbor workflow or boundary-ambiguous development requests before any downstream skill. Use for future ideas, bugs, non-trivial runtime tracebacks, pipeline blockers, optimizations, planning, audits, codebase/paper/proposal/reviewer-backed decisions, tests, evaluation, release follow-ups, context patches, active engineering planning continuations, and managed docs. Decide Arbor vs direct, split intents, choose persistence, and route only to declared workflow skills while keeping intake output hidden from normal users. Planning continuations routed to brainstorm must render the standard brainstorm headings, not ad hoc plans.
---

# Intake

## Purpose

Use `intake` as the automatic gate for user requests that may belong to Arbor's managed development workflow or need a direct-vs-managed boundary decision. Codex should select this skill automatically for possible Arbor workflow requests; normal users should not need explicit dollar-skill invocation.

`intake` is a classifier and router, not a universal router, not a solver, and not a user-facing stopping point. It may be selected by the runtime, but its normal output remains hidden from the user.

The skill must produce stable structured output for runtime handoff, replay, and debug review. The downstream skill or normal assistant owns visible user output. `intake` owns classification, boundary decisions, persistence decisions, and routing.

All enum-like fields must use the exact allowed enum values from the structured output contract. Do not output booleans, `none` as a substitute for `no`, or free-form phrases in `boundary.arbor_managed`, `persistence.todo`, `persistence.active_state`, `persistence.artifact_write`, or `routing.next_skill`.

## Checklist

Complete these steps in order:

1. **Read active context**: identify the current conversation topic and any known active workflow state. Do not treat short fragments as standalone requests before this check.
2. **Split intents**: separate compound user input when parts have different workflow boundaries.
3. **Decide Arbor boundary**: classify each intent as Arbor-managed, outside Arbor, or context-dependent.
4. **Decide persistence**: determine whether this creates backlog work, updates active state, writes an artifact, or writes nothing.
5. **Choose route**: select only one declared workflow skill, `none`, or report a route gap.
6. **Run self-check**: verify the decision does not hit an intake anti-pattern.
7. **Return structured internal output**: emit the JSON-shaped decision for runtime handoff; do not produce primary user-facing prose.

## Declared Workflow Skills

Route only to these skills:

- `brainstorm`
- `develop`
- `evaluate`
- `converge`
- `release`
- `none`

If no declared skill fits, return a route gap instead of inventing a skill.

## Automatic Selection

Codex should choose `intake` automatically when a user request might need Arbor workflow control, including possible backlog capture, planning, implementation, evaluation, convergence, release, active workflow continuation, or workflow-serving documentation.

Also choose `intake` for ambiguous boundary cases that need a direct-vs-managed decision before responding, such as:

- broad read-only audits or impact reviews;
- codebase, paper, proposal, report, or reviewer-feedback analysis that may affect research direction, experiments, implementation, or evaluation;
- code review or review-current-changes requests when they attach to an active Arbor develop handoff, current Arbor feature, or review packet;
- non-trivial runtime tracebacks, HPC or job failures, failing run logs, or pipeline blockers that may require debugging, implementation, validation, or active workflow routing;
- mixed requests where one part is direct explanation and another part asks for optimization, design, or future work;
- short context patches such as "continue," naming constraints, implementation constraints, or correction feedback;
- conversational planning continuations such as "based on my requirements, think through what to do," "do the first item," "think through the design before touching files," or "design a plan" when they attach to active engineering context;
- simple documentation or file-edit requests that might be direct work or managed workflow artifacts depending on purpose.

Automatic selection does not mean intake becomes visible to the user. It means intake produces the hidden routing decision that lets the downstream skill or normal assistant provide the visible response.

Normal users should not need to call `$arbor:intake`. Explicit invocation is reserved for debugging, review, simulation, or tests.

## Process Flow

```text
Read active context
-> Split intents
-> Arbor boundary decision
-> Persistence decision
-> Route decision
-> Self-check
-> Structured output
```

The terminal state is a structured intake decision that must immediately hand off to a downstream skill or normal assistant. Do not invoke implementation, evaluation, release, or documentation work from inside `intake`, and do not stop the user experience at `intake`.

## Core Rules

1. Decide whether the request is Arbor-managed before routing.
2. Split compound requests when different parts have different Arbor boundaries.
3. Preserve the raw user request exactly.
4. Capture future work before asking clarification questions.
5. Keep backlog and active work separate.
6. Treat short fragments as context patches before creating new items.
7. Classify by user intent and downstream workflow impact, not by topic or artifact keywords.
8. Do not route every technical question into Arbor.
9. Do not route every file edit into Arbor.
10. Do not use `evaluate` for generic assessment.
11. Do not route generic code review to `evaluate` unless it is attached to an Arbor develop handoff, current Arbor feature, or review packet.
12. Do not produce primary user-facing prose; downstream output is the user-facing response.

## Visibility

`intake` is hidden by default. It should not render a primary user card, and normal users should not need to invoke it explicitly.

Use its structured output for:

- runtime routing;
- downstream handoff;
- persistence decisions;
- replay and audit;
- debug or reviewer trace views.

Only expose intake details in an explicit debug, review, or trace mode. If the route requires clarification, route to `brainstorm` or report a resolution need for the runtime; do not ask clarification as `intake`.

## Anti-Patterns

### "Everything Technical Belongs In Arbor"

No. A one-off code explanation, paper-writing judgment, or direct answer can remain outside Arbor even when it is technical.

### "Every File Edit Belongs In Develop"

No. Simple README or copy edits can be direct work. `develop` is for implementation or managed development artifacts.

### "Evaluate Means Any Assessment"

No. `evaluate` is only for independent validation of implemented features or code changes.

### "Brainstorm Means Think About Anything"

No. `brainstorm` is for planning, clarification, codebase-backed design synthesis, impact analysis, and implementation or experiment design. Writing or review-style prompts can enter Arbor when the user is using them to decide research direction, experiments, baselines, implementation, feature scope, or development artifacts.

### "Keywords Decide The Boundary"

No. Do not route by words like proposal, report, paper, README, reviewer, docs, or explanation. The same surface topic can be direct work, backlog capture, brainstorm planning, develop artifact work, or evaluation depending on user intent and downstream workflow impact.

### "Incomplete Requirements Cannot Be Captured"

No. Future ideas should be captured before clarification. Missing details affect readiness, not capture eligibility.

## Arbor Boundary

Enter Arbor when the request needs development workflow management:

- future feature, bug, optimization, or research idea that should be captured;
- feature breakdown, planning, implementation, evaluation, convergence, or release;
- broad or risky engineering work that needs scope control;
- codebase analysis that extracts implementation ideas, architecture patterns, impact maps, or experiment plans;
- non-trivial runtime tracebacks, failing job logs, HPC failures, or pipeline blockers that affect an implementation, experiment, test, release, or active debugging workflow;
- active workflow continuation, developer feedback replay, test replay, or release preflight;
- code review of current changes when the active context is an Arbor develop handoff, current Arbor feature, or review packet;
- development-serving artifacts such as feature specs, review reports, test plans, release notes, AGENTS project maps, or workflow rules;
- long tasks that need active state or checkpointing.

Usually handle directly when the intent is:

- one-off work whose answer or artifact does not guide later development, testing, research execution, analysis, or agent behavior;
- direct explanations when the user only wants understanding, not an optimization, design, or implementation plan;
- writing/editing tasks when the user intent is only presentation, prose, or submission support;
- ordinary file edits that do not need planning, evaluation, convergence, or workflow state.

These are intent patterns, not exclusion rules. A proposal, report, paper, README, reviewer comment, or single-file question should enter Arbor when the user is using it as evidence for future work, experiment design, implementation planning, evaluation strategy, context recovery, or workflow policy.

The deciding factor is whether the task needs Arbor workflow control, not whether it is technical, not whether it writes a file, and not which artifact type is mentioned.

## Persistence Rules

`todo` is only for queued future work.

- Future idea: append to workflow todo/backlog.
- Immediate task: do not write todo; create or update active state only when metadata writes are allowed.
- Active continuation: do not create todo.
- Backlog review: do not create todo.
- Context patch: do not create todo; attach to current context if possible.

If the user says "do not modify anything", do not write workflow metadata without explicit permission.

## Context Rules

Fragmentary, imperative, or constraint-like input should attach to the active context when possible:

- "Do not use codex in the name."
- "Continue."
- "We do not need scaling."
- "Use our own quantizer."
- "Based on my requirements, think through what to do and design a plan."
- "Do the first item. Think through the design before touching files."

Recommended context priority:

1. explicit instruction in the current user message;
2. active current conversation topic;
3. active workflow artifact;
4. backlog.

If current conversation and workflow artifacts conflict, surface the conflict.

### Runtime Traceback and Pipeline Blockers

Pasted tracebacks and failing run logs are not automatically full Arbor workflows, but non-trivial runtime failures should first pass through intake because they often decide whether the next step is direct explanation, active bugfix, evidence replay, or broader planning.

Use these routes:

- active implementation, experiment, test, or cleanup context plus a traceback or blocker that needs a fix: route to `develop`, do not create todo;
- post-fix replay, independent validation, or "review why this passed/failed" request attached to an Arbor handoff: route to `evaluate`;
- unclear root cause, broad pipeline impact, or design-level remediation before touching files: route to `brainstorm`;
- one-off explanation of an error with no downstream implementation, testing, or workflow effect: route to `none`.

If the failure blocks a shared runtime path, the downstream skill should record validation evidence even when the fix is immediate.

When a short acknowledgement or continuation refers back to the user's requirements and asks for planning, design, splitting, or verification, treat it as an active-context planning continuation. If the active context is an engineering, experiment, release, or workflow task, route to `brainstorm` before implementation so scope, assumptions, acceptance criteria, and verification are visible. If no engineering context exists, keep it context-dependent or direct according to the actual topic; do not route on planning words alone.

For active engineering planning continuations that route to `brainstorm`, the downstream visible answer must be the standard brainstorm checkpoint, not an ad hoc planning summary. The final rendered response must use the brainstorm headings exactly: `Understanding And Recommendation`, `How I Would Handle This`, `Suggested Small Steps`, `How I Would Validate Each Step`, `Default Decisions I Made`, `Expected Delivery`, and `Next`. Do not use substitutes such as `Brainstorm Checkpoint`, `Recommended plan`, or prose-only acceptance criteria.

## Routing Rules

### `brainstorm`

Use for clarification, planning, impact analysis, codebase-backed design synthesis, implementation strategy, experiment design, and feature breakdown.

When routing to `brainstorm`, preserve the user-visible output contract. A planning continuation that arrived through `intake` still needs the exact brainstorm headings in the rendered response; route labels and internal JSON stay hidden.

Writing-only help is direct work. Use `brainstorm` when a paper, proposal, report, reviewer comment, spec, or other user artifact is being used to change implementation plan, experiment plan, feature scope, research direction, or development artifacts.

Mark evidence mode when applicable:

- `pure`
- `user_artifact`
- `codebase`
- `paper`
- `paper_and_code`

If a question depends on an external paper, spec, or codebase, the first action must be to retrieve and read the source material before concluding.

### `develop`

Use for implementation and managed development artifacts. Do not use for every document or file edit.

Use `develop` for active runtime error or traceback feedback when the current workflow needs a concrete fix or debugging pass. Do not create backlog todo for a bug the user is asking to fix now.

### `evaluate`

Use only for independent validation of implemented features or code changes:

- tests;
- coverage;
- scenario validation;
- adversarial checks;
- code review of current changes when attached to an Arbor develop handoff, active Arbor feature, or review packet;
- replaying developer feedback;
- appending evaluator review rounds.

Do not use `evaluate` for generic assessment or standalone code review that is not independent validation of an Arbor-managed implemented feature, code change, or develop handoff.

### `converge`

Use only to decide whether the develop/evaluate loop has converged.

### `release`

Use for release and git workflow gates. Conditional push instructions still require release preflight.

## Structured Output Contract

Return this structure first:

```json
{
  "schema_version": "intake.v1",
  "raw_user_request": "",
  "boundary": {
    "arbor_managed": "yes",
    "reason": "",
    "confidence": "high"
  },
  "classification": {
    "type": "",
    "subtype": "",
    "multi_intent": []
  },
  "persistence": {
    "todo": "no",
    "active_state": "no",
    "artifact_write": "none",
    "target_artifact": null,
    "reason": ""
  },
  "routing": {
    "next_skill": "none",
    "resolution_required": false,
    "possible_routes": [],
    "reason": "",
    "confidence": "high"
  },
  "ui": {
    "visibility": "hidden",
    "display_mode": "none",
    "summary": "",
    "badges": [],
    "warnings": [],
    "requires_resolution": false,
    "resolution_kind": "none",
    "requires_user_decision": false,
    "decision_options": [],
    "review_focus": []
  },
  "user_response": ""
}
```

Keep enum-like fields stable. Do not require the UI to infer route, persistence, risk, or user-decision state from prose.

These fields must be exact enums, never booleans or explanatory phrases:

- `boundary.arbor_managed`
- `persistence.todo`
- `persistence.active_state`
- `persistence.artifact_write`
- `routing.next_skill`
- `ui.visibility`
- `ui.display_mode`
- `ui.resolution_kind`

Use these enums:

- `boundary.arbor_managed`: `yes`, `no`, `mixed`, `context_dependent`, `uncertain`
- `persistence.todo`: `yes`, `no`, `maybe`
- `persistence.active_state`: `yes`, `no`, `maybe`, `requires_permission`
- `persistence.artifact_write`: `none`, `direct`, `defer`, `yes`
- `routing.next_skill`: `brainstorm`, `develop`, `evaluate`, `converge`, `release`, `none`
- `ui.visibility`: `hidden` or `debug`
- `ui.display_mode`: `none` or `trace`
- `ui.resolution_kind`: `none`, `context_lookup`, `user_decision`, `permission`

When the route depends on active context, set `routing.next_skill` to `none`, `resolution_required` to `true`, and list possible declared routes in `possible_routes`.

When `routing.resolution_required` is `true`, set `ui.requires_resolution` to `true`. Use `ui.requires_user_decision` only when the user must choose or grant permission. Even then, keep `ui.visibility=hidden`; the downstream skill or system UI owns the visible prompt.

## Self-Check

Before returning, check:

1. Did I split compound intents when one part is direct and another part is Arbor-managed?
2. Did I avoid creating todo for immediate work?
3. Did I avoid writing workflow metadata when the user requested read-only behavior?
4. Did I route generic assessment outside `evaluate`?
5. Did I classify proposal/report/paper/reviewer/docs/explanation requests by intent and downstream impact instead of keywords?
6. Did I preserve raw user input separately from normalized classification?
7. Did I include UI fields for warnings, review focus, and user decisions?
8. Did I keep intake hidden and avoid treating it as the visible user response?
9. Did I preserve the distinction between automatic runtime selection and hidden user-facing output?

If any answer fails, revise the structured output before responding.

## Reference Material

- `references/intake-design.md`: full design rationale and boundary rules.
- `references/intake-simulation-cases.md`: regression cases from user simulation.
