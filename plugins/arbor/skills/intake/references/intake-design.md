# Intake Skill Design

## Purpose

`intake` is the automatic gatekeeper for Arbor-managed development workflow. Its job is not to handle every user request. Its job is to decide whether a request should enter Arbor's workflow, whether it should be captured, how it should attach to current context, and which internal skill should handle the next step.

Codex should be able to select `intake` automatically when a user request may need Arbor workflow control or when the request needs a direct-vs-managed boundary decision. That automatic selection is separate from user visibility: users should not need explicit dollar-skill invocation, and intake should not become the visible response.

The skill must stay lightweight. It should not solve the task, design the full solution, write code, run tests, or invent new workflow stages.

## Automatic Selection vs User Visibility

`intake` has two separate contracts:

- **Runtime selection**: Codex should choose intake automatically for possible Arbor-managed requests or ambiguous boundary requests so it can classify, persist, and route before another workflow skill runs.
- **User visibility**: intake should keep normal output hidden and let the downstream skill or normal assistant provide the visible response.

Do not describe intake as non-selectable or manual-only. The intended user experience is that users do not need to call `$arbor:intake`, not that the runtime should avoid selecting intake.

Automatic selection should cover direct-vs-managed ambiguity, not only obvious managed work. Examples include broad read-only audits, codebase or paper-backed analysis, proposal and reviewer feedback used for planning, code review requests attached to active Arbor develop handoffs, mixed explanation-plus-optimization requests, context patches, and documentation edits whose purpose may or may not serve development workflow.

Keep the trigger description compact. Overly broad prose can make the model classify more cases, but it can also weaken the exact output contract. The skill should say when to select intake, then quickly hand control to the stable structured schema.

## Skill File Organization

Keep `SKILL.md` procedural and compact:

- purpose;
- checklist;
- process flow;
- core rules;
- anti-patterns;
- structured output contract;
- self-check;
- pointers to references.

Put long rationale, decision tables, and regression cases in `references/`. This keeps the runtime skill easy to follow while preserving enough design detail for implementation and future UI work.

## Fixed Skill Set

`intake` can route only to the declared Arbor skills:

- `brainstorm`
- `develop`
- `evaluate`
- `converge`
- `release`
- `none`

If no declared skill fits, `intake` must return a route gap instead of inventing a new skill.

## Core Contract

`intake` must:

- classify the user input;
- decide whether it is Arbor-managed;
- split compound requests into multiple intents when needed;
- preserve the raw user request;
- distinguish future backlog work from immediate active work;
- decide whether workflow metadata should be written;
- attach fragmentary input to the active context when appropriate;
- route to the next declared skill or stay outside Arbor;
- emit UI-ready structured output before any user-facing prose;
- ask only the minimum question needed when routing cannot be decided safely.

`intake` must not:

- turn all technical requests into Arbor workflow;
- require complete requirements before capturing a future idea;
- treat all repo file edits as Arbor-managed;
- treat generic assessment as `evaluate`;
- treat generic standalone code review as `evaluate`;
- treat all design thinking as `brainstorm`;
- route writing, review-style reasoning, or explanation prompts by keyword instead of checking whether they drive implementation, experiment planning, research direction, evaluation strategy, or development artifacts.

## Output Shape

`intake` output is an internal contract between the skill layer, runtime routing, replay, and optional debug UI. It is not the primary user-visible output. The downstream skill or normal assistant owns the response the user sees.

The skill may include an empty or minimal `user_response` for testing, but normal runtime should not stop at `intake`. Do not hide important decisions only in prose. This hidden-output rule does not weaken automatic runtime selection.

When running in simulation or structured mode, `intake` should produce:

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

`multi_intent` is required when different parts of a user request have different workflow boundaries. For example, "explain this file and think about optimizations" can split into direct explanation plus Arbor-managed `brainstorm`.

Use stable enums, not mixed booleans and strings:

- `boundary.arbor_managed`: `yes`, `no`, `mixed`, `context_dependent`, `uncertain`
- `persistence.todo`: `yes`, `no`, `maybe`
- `persistence.active_state`: `yes`, `no`, `maybe`, `requires_permission`
- `persistence.artifact_write`: `none`, `direct`, `defer`, `yes`
- `routing.next_skill`: `brainstorm`, `develop`, `evaluate`, `converge`, `release`, `none`
- `ui.visibility`: `hidden`, `debug`
- `ui.display_mode`: `none`, `trace`
- `ui.resolution_kind`: `none`, `context_lookup`, `user_decision`, `permission`

When the route depends on active context, set `routing.next_skill` to `none`, `resolution_required` to `true`, and list possible declared routes in `possible_routes`. Do not output undeclared routes such as `state_dependent`.

When `routing.resolution_required` is `true`, set `ui.requires_resolution` to `true`. Use `ui.requires_user_decision` only when the user must choose or grant permission. Context lookup can require resolution without requiring a user decision.

## Hidden Output Rules

The structured output should make routing and later review cheap without making intake a user-facing stop:

- put the route, persistence decision, and boundary decision in separate fields;
- include confidence and reason for every major decision;
- include `raw_user_request` exactly as received so UI review, replay, and audit do not depend on normalized classification;
- include `requires_resolution: true` when the UI or agent must resolve active context before continuing;
- include `requires_user_decision: true` when the agent should stop before proceeding;
- include `warnings` for risky behavior such as external-visible actions, read-only conflicts, broad scope, missing active state, or evidence not yet loaded;
- include `review_focus` when a human should inspect only a small subset of the decision;
- keep enum-like fields stable so a UI can render filters and badges without parsing prose;
- keep raw user input separate from normalized classification;
- never require the UI to infer state transitions from natural-language text;
- set `ui.visibility=hidden` and `ui.display_mode=none` for normal operation;
- reserve intake trace rendering for explicit debug/review mode.

Good UI-level review targets include:

- "Does this belong in Arbor?"
- "Should this be captured to backlog?"
- "Is the selected next skill correct?"
- "Is this a context patch or a new item?"
- "Does this require permission before writing metadata or pushing?"

## Arbor Boundary

`intake` must classify by user intent and downstream workflow impact, not by artifact or topic keywords. Words like proposal, report, paper, README, reviewer, docs, and explanation are not boundary decisions by themselves.

### Enter Arbor

A request should enter Arbor when it needs development workflow management:

- future feature, bug, optimization, or research idea that should be captured;
- work that needs feature breakdown, planning, implementation, evaluation, convergence, or release;
- broad or risky engineering work that needs scope control;
- codebase analysis that extracts implementation ideas, architecture patterns, impact maps, or experiment plans;
- user-provided proposals, reports, reviewer comments, papers, specs, or docs that are being used to decide research direction, experiments, baselines, implementation, feature scope, or future workflow;
- active workflow continuation, developer feedback replay, test replay, or release preflight;
- code review of current changes when the active context is an Arbor develop handoff, current Arbor feature, or review packet;
- development-serving artifacts such as feature specs, review reports, test plans, release notes, AGENTS project maps, or workflow rules;
- long tasks that need active state or checkpointing.

### Usually Direct Work

A request usually stays outside Arbor when it does not need workflow management:

- one-off work whose answer or artifact does not guide later development, testing, research execution, analysis, or agent behavior;
- direct explanation when the user only wants understanding, not optimization, design, or implementation planning;
- conversation summary or prompt collection;
- writing/editing task where the user intent is only presentation, prose, or submission support;
- ordinary file edits that do not need planning, evaluation, convergence, or workflow state.

These are intent patterns, not exclusion rules. The same surface artifact can be direct work, backlog capture, brainstorm planning, develop artifact work, or evaluation depending on the user's intent and downstream impact.

The deciding factor is not whether the task is technical, not whether it writes a file, and not which artifact type is named. The deciding factor is whether the task needs Arbor's development workflow control.

## Capture and Persistence

### Capture First, Clarify Later

Future work should be captured before clarification. Missing details should not block backlog capture.

Use this rule for:

- "I have an idea, maybe later..."
- "We may need to optimize X later."
- "There is a bug, error is X."

Clarification enriches an existing item; it does not replace the raw captured idea.

### Backlog vs Active Work

`todo` is only for queued future work. Immediate work should not be written to `todo`.

- Future idea: append to workflow todo/backlog.
- Immediate task: create or update active state only when metadata writes are allowed.
- Active continuation: do not create new todo.
- Existing backlog review: do not create new todo.

If the user says "do not modify anything", `intake` must not write workflow metadata without explicit permission. In that case, preserve progress in conversation unless the user allows Arbor checkpoint files.

## Context Patches

Short, fragmentary, or constraint-like inputs should first try to attach to current context:

- "Do not use codex in the name."
- "Continue."
- "We do not need scaling."
- "Use our own quantizer."
- "Based on my requirements, think through what to do and design a plan."
- "Do the first item. Think through the design before touching files."

Only create a new item if the input cannot reasonably attach to current context and contains an independent work item.

Recommended context priority:

1. explicit instruction in the current user message;
2. active current conversation topic;
3. active workflow artifact;
4. backlog.

If current conversation and workflow artifacts conflict, `intake` should surface the conflict instead of silently choosing.

### Affirmative Planning Continuations

Short acknowledgements can carry real planning intent when they attach to an active engineering context. Examples include "based on my requirements," "do the first item," "think through what to do," "think through the design before touching files," "design a plan," "split the work," "decide the checks," or "how should we approach this."

Use this rule only when the continuation has both:

- a reference back to prior requirements or active context;
- planning, design, feature-split, acceptance, or verification intent.

If the active context is code cleanup, implementation planning, experiment design, release preparation, workflow policy, or another Arbor-managed engineering task, classify the input as an active planning continuation and route to `brainstorm`. The first brainstorm action should load the relevant active context and evidence before producing a settled plan.

If there is no active engineering context, or the context is non-engineering work such as travel planning, email drafting, or prose-only writing support, do not route merely because the user used planning language. Keep the request direct or context-dependent according to the real topic.

### Active Code Review Continuations

Short requests such as "code review", "review the current change", "review this patch", or equivalent non-English phrasing should route to `evaluate` only when they attach to an active Arbor develop handoff, current Arbor feature, or review packet. In that context, the user is asking for independent validation of implemented work, not generic review prose.

If there is no Arbor develop handoff or active feature context, keep the request outside Arbor or mark it context-dependent. Do not route by the words "code review" alone.

## Documentation Boundaries

Arbor manages development-serving artifacts, not all artifacts.

Enter Arbor for:

- feature specs;
- design notes for upcoming implementation;
- test plans;
- review and evaluation reports;
- release notes tied to a release gate;
- workflow rules;
- AGENTS or memory policy updates;
- data or code maps used for later development, experiment execution, analysis, or context recovery.

Usually handle directly when the intent is:

- documents whose only purpose is human presentation, prose, or submission support;
- one-off notes or summaries that do not guide later development, testing, evaluation, analysis, or agent behavior;
- simple copy changes that do not need planning, validation, workflow state, or future context recovery.

This section is not a keyword list. A course report, README, proposal, review response, or project summary can enter Arbor if the user is using it to shape development work, experiment design, evaluation strategy, project memory, or future agent behavior.

If a requested document is a project map or context recovery entrypoint, prefer updating `AGENTS.md` Project Map. If the details are too large for `AGENTS.md`, create a detailed doc under `docs/` and add a concise pointer from `AGENTS.md`.

## Routing Rules

### `brainstorm`

Use for clarification, planning, impact analysis, codebase-backed design synthesis, implementation strategy, experiment design, and feature breakdown.

Writing-only help is direct work. Use `brainstorm` when a paper, proposal, report, reviewer comment, spec, or other user artifact is being used to change implementation plan, experiment plan, feature scope, research direction, or development artifacts.

Evidence-backed brainstorms should mark evidence mode:

- `pure`: reasoning only;
- `user_artifact`: requires reading a user-provided artifact such as a proposal, report, notes, or review text as planning evidence;
- `codebase`: requires reading code;
- `paper`: requires reading paper/spec/docs;
- `paper_and_code`: requires both.

If a question depends on an external paper, spec, or codebase, the first action must be to retrieve and read the source material before concluding.

### `develop`

Use for implementation and project artifact generation when the artifact is part of the managed development workflow.

`develop` is not only for code, but it should not be used for every document or file edit. Simple direct edits can stay outside Arbor.

### `evaluate`

Use only for independent validation of implemented features or code changes:

- tests;
- coverage;
- scenario validation;
- adversarial checks;
- replaying developer feedback;
- appending evaluator review rounds.

Do not use `evaluate` for generic assessment that is not independent validation of implemented features or code changes.

### `converge`

Use only to decide whether the develop/evaluate loop has converged:

- accepted;
- changes requested;
- blocked;
- needs brainstorm.

Do not use it for generic project management or writing readiness.

### `release`

Use for release and git workflow gates:

- status check;
- validation gate;
- commit message convention;
- push when explicitly authorized;
- release handoff.

Conditional push instructions still require release preflight.

## Advance Commands

Inputs like "continue", "next step", and "good, start the next step" are workflow-control commands, not new requirements.

They require state resolution:

- if the current feature was developed and self-reviewed, next is usually `evaluate`;
- if evaluation has findings, next is usually `converge`;
- if the current feature is accepted and another feature is ready, next may be `develop`;
- if the next feature is not planned, next may be `brainstorm`;
- if no active context exists, report that no active item is available and offer recovery options.

## Learning From User Feedback

During skill simulation, each run should produce a learning draft. User feedback should update the rules explicitly:

- keep;
- modify;
- delete;
- add;
- unresolved question.

Simulation output must clearly mark that it is not writing files or executing the real workflow.
