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
- loaded brainstorm acceptance criteria and goals;
- evaluator terminal state and findings;
- evaluator `feature_registry_signal`;
- loop round count and round limit.

If this evidence is missing, return `needs_evidence` rather than guessing.

## Two Required Questions

1. Do `develop` and `evaluate` agree?
2. Does the latest result still satisfy brainstorm goals, acceptance criteria, non-goals, and test scope?

Both must be true to return `converged`.

## User-Facing Convergence Packet

`user_response` is the visible decision packet. It should not repeat the full evaluator test report. It should explain the convergence decision and the next workflow owner.

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

Action:

- update selected feature to `planned` or leave it blocked with a planning reason;
- route to `brainstorm`;
- append a Convergence Round.

### Needs User Decision

Use when:

- the configured correction round limit is reached;
- the next step requires a product/design choice not settled by brainstorm;
- develop and evaluate evidence conflict in a way the agent cannot resolve safely.

Action:

- do not continue the loop automatically;
- append a Convergence Round with options;
- route `none` and ask the user.

### Needs Evidence

Use when required evidence is missing even if some fields look accepted:

- missing brainstorm Context/Test Plan, acceptance criteria, or goals routes to `brainstorm`;
- missing latest Developer Round routes to `develop`;
- missing latest Evaluator Round or inconsistent evaluator signal routes to `evaluate`.

Action:

- do not mark the feature done;
- keep the feature in its current safe status unless the selected evidence problem requires a blocked marker;
- append a Convergence Round or blocker packet explaining which evidence owner must run next.

The evidence route must match the missing owner. Do not send missing Developer Round evidence to `brainstorm`, and do not send missing brainstorm criteria or goals to `evaluate`.

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
