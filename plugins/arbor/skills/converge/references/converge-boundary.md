# Converge Boundary

## Position

`converge` sits after `evaluate`:

```text
intake -> brainstorm -> develop -> release(checkpoint_develop) -> evaluate -> release(checkpoint_evaluate) -> converge -> release(finalize_feature) -> next feature
```

It is a decision point, not a planner, developer, evaluator, or releaser. It routes converged features to internal `release`; release handles finalization and next-feature continuation.

## Inputs

Minimum evidence:

- feature id;
- `.arbor/workflow/features.json`;
- shared review document path;
- brainstorm Context/Test Plan;
- latest Developer Round;
- latest Evaluator Round;
- loaded brainstorm acceptance criteria, done-when criteria when present, and goals;
- evaluator terminal state and findings;
- evaluator `feature_registry_signal`;
- loop round count and round limit.

If this evidence is missing, return `needs_evidence` rather than guessing.

## Two Required Questions

1. Do `develop` and `evaluate` agree?
2. Does the latest result still satisfy brainstorm goals, acceptance criteria, done-when criteria, non-goals, and test scope?
3. Does the evidence show decision trace consistency across key decisions, decision invariants, implementation-time decisions, decision deviations, decision drift checks, and hidden decision conflict checks?

All must be true to return `converged`.

## User-Facing Convergence Packet

`user_response` is the visible decision packet. It should not repeat the full evaluator test report. It should explain the convergence decision and the next workflow owner.

The structured `converge.v1` object is an internal workflow/runtime packet. Normal user-facing output should render `user_response` and `ui`, not print the raw JSON unless explicit debug output is requested.

Use these sections:

| Section | Purpose |
| --- | --- |
| Convergence Decision | State whether the feature converged, needs development, needs planning, needs evidence, needs a user decision, is blocked, or was misrouted. |
| Why This Decision | Explain the main evidence behind the decision in natural language. |
| Agreement Check | Use a Markdown table comparing developer side, evaluator side, and the resulting decision for the main agreement questions. |
| Goal Alignment | Explain whether the result still satisfies the brainstorm goal and feature scope. |
| Remaining Issues | Use a Markdown table listing blocking issues, their source, whether they block completion, and the next owner. |
| Next Step | State the next workflow step in plain language. |

Do not include a "What Will Be Preserved" section. Persistence and checkpoint details belong in structured fields for release and workflow continuation.

`Agreement Check` and `Remaining Issues` must be tables with user-readable cells. Keep internal ids, field names, terminal-state strings, route assignments, and finding ids out of primary visible text.

The normal visible final response MUST include these exact Markdown headings, in
this order:

- `**Convergence Decision**`
- `**Why This Decision**`
- `**Agreement Check**`
- `**Goal Alignment**`
- `**Remaining Issues**`
- `**Next Step**`

Before returning, self-check that the visible response contains those exact
headings and Markdown tables under `Agreement Check` and `Remaining Issues`.
A shorter prose-only convergence checkpoint is not acceptable.

## Checkpoint And Automation Policy

`converge` is a mandatory user-visible checkpoint by default. The output must include `ui.checkpoint` and `ui.workflow_automation`:

```json
{
  "ui": {
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
  }
}
```

A `converged` decision is not release completion. The visible output must say that release finalization remains next and must not imply commit, push, publish, or full release has happened.

The only allowed automatic continuation is the explicit `develop_evaluate_converge` policy requested by the user for the current workflow. Even then, `converge` may set `continue_policy=auto_continue_allowed` only for clear loop decisions inside the current feature, below the round limit, with no product/design decision, scope change, missing evidence, blocked convergence, or external release action required.

## Route Decisions

### Converged

Use when:

- evaluator terminal state is `accepted`;
- no blocking evaluator findings remain;
- brainstorm Context/Test Plan, latest Developer Round, and latest Evaluator Round are loaded;
- brainstorm acceptance criteria and goals are loaded;
- feature id matches across registry, review document, and evaluator signal;
- evaluator signal current status is `in_evaluate` and recommended next status is `done`;
- registry update finalizes the same feature from `in_evaluate` to `done`;
- evaluator evidence maps to brainstorm acceptance criteria;
- evaluator evidence maps to done-when criteria when present;
- evaluator evidence checks decision drift and hidden decision conflict when a decision trace handoff is present;
- developer evidence records implementation-time decisions and decision deviations against decision invariants when material;
- evaluator evidence checks optional delegation packet and effort budget results when delegation was used;
- evaluator evidence checks final state, checkpoint outcomes, rendered output, review evidence, process state, git/file side effects, realistic replay, trace evidence, and weak-pass gaps for workflow-facing changes;
- round limit has not been reached.

Action:

- update selected feature to `done`;
- append a Convergence Round;
- route to `release` for internal finalization.
- set `workflow_continuation.status=none`; release selects the next unfinished feature after finalization.

### Needs Develop

Use when evaluator findings are implementation bugs, developer evidence gaps, missing tests, or correction scopes that do not change product/design intent.

Action:

- update selected feature to `changes_requested` or `in_develop`;
- pass finding ids, correction scope, and replay targets to `develop`;
- append a Convergence Round.

### Needs Brainstorm

Use when evaluator evidence reveals:

- contradictory acceptance criteria;
- invalid or missing test plan;
- scope drift from brainstorm goals;
- an implementation correction that would change hidden decisions or product behavior.
- missing key decisions, rejected options, allowed implementation discretion, or decision invariants that block decision trace consistency.

Action:

- update selected feature to `planned` or leave it blocked with a planning reason;
- route to `brainstorm`;
- append a Convergence Round.

### Needs User Decision

Use when:

- the configured correction round limit is reached;
- the next step requires a product/design choice not settled by brainstorm;
- develop and evaluate evidence conflict in a way the agent cannot resolve safely.
- repeated same-class failures, weak replay evidence, or context contamination make another broad automatic correction unreliable and the safe route is not clear.

Action:

- do not continue the loop automatically;
- append a Convergence Round with options;
- route `none` and ask the user.

### Needs Evidence

Use when required evidence is missing even if some fields look accepted:

- missing brainstorm Context/Test Plan, acceptance criteria, or goals routes to `brainstorm`;
- missing latest Developer Round routes to `develop`;
- missing latest Evaluator Round or inconsistent evaluator signal routes to `evaluate`.
- missing decision trace consistency evidence follows the same owner rule: brainstorm owns key decisions and decision invariants, develop owns implementation-time decisions and decision deviations, and evaluate owns decision drift or hidden decision conflict checks.

When decision trace evidence is missing or inconsistent, return the appropriate evidence or planning route instead of marking the feature done.

Action:

- do not mark the feature done;
- keep the feature in its current safe status unless the selected evidence problem requires a blocked marker;
- append a Convergence Round or blocker packet explaining which evidence owner must run next.

The evidence route must match the missing owner. Do not send missing Developer Round evidence to `brainstorm`, and do not send missing brainstorm criteria or goals to `evaluate`.

## Outcome Evidence

Convergence is outcome-first. Use evaluator evidence to decide whether final state, checkpoint outcomes, rendered output, review evidence, process state, git/file side effects, realistic replay, and trace evidence agree with the brainstorm goal. Do not require fixed path matching, exact turn-by-turn replay, LLM judges, subagents, worktrees, fan-out execution, or one universal test type by default.

If evaluator evidence explicitly marks a deterministic substitute as a weak pass, check whether the remaining proof is required by the brainstorm goal. Exact path evidence should block convergence only when route, checkpoint order, startup behavior, release policy, or trace behavior is the claimed outcome.

## Next Feature Selection

After `converged`, `converge` must not choose the next feature directly. It must:

1. finalize the current selected feature first;
2. append the Convergence Round;
3. route to `release`;
4. leave `workflow_continuation.status=none`, `next_feature_id=null`, `next_feature_status=null`, and `next_skill=none`.

Release owns next-feature continuation because it is the final current-feature step. This prevents the pipeline from starting the next feature before release evidence, commit convention planning, and any confirmation-gated delivery actions are handled.

## Feature Registry Contract

`converge` is the first skill allowed to finalize feature status after evaluation.

Registry update rules:

- `converged` -> `done`;
- `needs_develop` -> `changes_requested` or `in_develop`;
- `needs_brainstorm` -> `planned` or `blocked`;
- `blocked` -> `blocked`;
- `needs_evidence`, `needs_user_decision`, and `route_correction` update only when a selected feature and safe status are clear.

Never update a row whose id does not match the evaluator signal.

## Loop Policy

The normal automatic loop limit is three correction rounds unless a project-specific policy says otherwise.

Round count should come from structured handoff fields when available. If only review prose is available, count distinct Developer/Evaluator correction rounds conservatively and record uncertainty.

## Loop Health Advisory

`converge` should surface loop-health risk before automatic continuation when
the latest rounds show repeated same-class failures, evidence conflicts,
unresolved evidence conflicts, weak replay evidence being treated as full proof, context
contamination, or round-limit pressure with unclear ownership.

The advisory is a routing and readability aid. It can recommend a narrower
developer correction, re-brainstorming, exact runtime replay, evidence
reconciliation, a fresh-session handoff, or a user decision. It must not automatically clear context, spawn subagents, create worktrees, or require
fan-out execution. Subagents and worktrees remain optional strategies.

A normal correction loop should continue without loop-health escalation when
the finding is new, coherent, clearly owned, below the round limit, and has a
specific replay target.

## Review Append

Append a Convergence Round to the same review document with:

- source evaluator round;
- feature id and registry status before/after;
- agreement decision;
- brainstorm alignment decision;
- selected findings and correction scope;
- next skill;
- user-decision options when needed.

Do not rewrite prior rounds.
