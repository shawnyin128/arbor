---
name: intake
description: Classify user input for Arbor-managed development workflow, decide whether the request belongs in Arbor, split compound intents, choose persistence behavior, attach context patches, and route only to declared internal workflow skills using UI-ready structured output.
---

# Intake

## Purpose

Use `intake` to decide whether a user request should enter Arbor's development workflow. `intake` is a gatekeeper, not a universal router and not a solver.

The skill must produce stable structured output that a future UI layer can render. The UI owns presentation. The skill owns classification, boundary decisions, persistence decisions, and routing.

## Checklist

Complete these steps in order:

1. **Read active context**: identify the current conversation topic and any known active workflow state. Do not treat short fragments as standalone requests before this check.
2. **Split intents**: separate compound user input when parts have different workflow boundaries.
3. **Decide Arbor boundary**: classify each intent as Arbor-managed, outside Arbor, or context-dependent.
4. **Decide persistence**: determine whether this creates backlog work, updates active state, writes an artifact, or writes nothing.
5. **Choose route**: select only one declared workflow skill, `none`, or report a route gap.
6. **Run self-check**: verify the decision does not hit an intake anti-pattern.
7. **Return structured output first**: emit the UI-ready JSON-shaped decision before any prose explanation.

## Declared Workflow Skills

Route only to these skills:

- `brainstorm`
- `develop`
- `evaluate`
- `converge`
- `release`
- `none`

If no declared skill fits, return a route gap instead of inventing a skill.

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

The terminal state is a structured intake decision. Do not invoke implementation, evaluation, release, or documentation work from inside `intake`.

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
11. Emit structured fields before user-facing prose.

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
- active workflow continuation, developer feedback replay, test replay, or release preflight;
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

Recommended context priority:

1. explicit instruction in the current user message;
2. active current conversation topic;
3. active workflow artifact;
4. backlog.

If current conversation and workflow artifacts conflict, surface the conflict.

## Routing Rules

### `brainstorm`

Use for clarification, planning, impact analysis, codebase-backed design synthesis, implementation strategy, experiment design, and feature breakdown.

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

Use these enums:

- `boundary.arbor_managed`: `yes`, `no`, `mixed`, `context_dependent`, `uncertain`
- `persistence.todo`: `yes`, `no`, `maybe`
- `persistence.active_state`: `yes`, `no`, `maybe`, `requires_permission`
- `persistence.artifact_write`: `none`, `direct`, `defer`, `yes`
- `routing.next_skill`: `brainstorm`, `develop`, `evaluate`, `converge`, `release`, `none`
- `ui.resolution_kind`: `none`, `context_lookup`, `user_decision`, `permission`

When the route depends on active context, set `routing.next_skill` to `none`, `resolution_required` to `true`, and list possible declared routes in `possible_routes`.

When `routing.resolution_required` is `true`, set `ui.requires_resolution` to `true`. Use `ui.requires_user_decision` only when the user must choose or grant permission.

## Self-Check

Before returning, check:

1. Did I split compound intents when one part is direct and another part is Arbor-managed?
2. Did I avoid creating todo for immediate work?
3. Did I avoid writing workflow metadata when the user requested read-only behavior?
4. Did I route generic assessment outside `evaluate`?
5. Did I classify proposal/report/paper/reviewer/docs/explanation requests by intent and downstream impact instead of keywords?
6. Did I preserve raw user input separately from normalized classification?
7. Did I include UI fields for warnings, review focus, and user decisions?

If any answer fails, revise the structured output before responding.

## Reference Material

- `references/intake-design.md`: full design rationale and boundary rules.
- `references/intake-simulation-cases.md`: regression cases from user simulation.
