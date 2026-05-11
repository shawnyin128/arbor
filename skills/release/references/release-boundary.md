# Release Boundary

## Position

`release` sits after `converge` as an internal finalization step:

```text
intake -> brainstorm -> develop -> evaluate -> converge -> release -> next feature
```

It is a current-feature finalization gate, not a planner, developer, evaluator, convergence judge, or primary user-facing entrypoint.

## Inputs

Minimum evidence:

- selected feature id from the convergence handoff;
- `.arbor/workflow/features.json` and the selected source feature registry row;
- shared review document path;
- Convergence Round or equivalent convergence packet;
- latest Developer Round and Evaluator Round references;
- requested release action;
- git status, selected files, dirty scope, and branch/remotes when relevant;
- user authorization for external actions.
- feature registry rows needed for next-feature continuation.

If convergence evidence is missing, return `needs_converge`. If authorization is missing for an external action, return `needs_confirmation`.

## External Action Boundary

Safe local preparation:

- inspect git status and diffs;
- run release-readiness checks;
- prepare selected file list;
- classify dirty scope as `clean`, `selected_only`, `unrelated`, or `unknown`;
- draft commit message;
- append Release Round or blocker packet.
- select the next unfinished feature after a release-final state.

Confirmation-gated actions:

- staging files;
- creating a commit;
- pushing a branch;
- opening or updating a PR;
- creating a tag;
- publishing a package, plugin, release artifact, or marketplace entry.

The user must authorize the specific action. "Release this" can authorize preparation, but not every external action unless the prompt clearly asks for it.

Standalone `stage` has no completed release terminal. `release` may prepare an exact stage file list, and staging may happen as part of an explicitly authorized commit, but a stage-only request should not be reported as completed release delivery.

## Commit Convention

Use:

```text
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Allowed default `type` values:

- `feat`
- `fix`
- `docs`
- `test`
- `refactor`
- `chore`
- `release`

Choose the smallest accurate type from the changed surface. Prefer `feat(scope)` for user-facing workflow capability, `fix(scope)` for defect fixes, `docs(scope)` for documentation-only work, and `chore(release)` for packaging or metadata-only release preparation.

The subject description after the colon must be non-empty after trimming whitespace. For example, `feat:    ` is invalid even though it has a valid type prefix.

## Dirty Scope

`dirty_scope` records whether the worktree is safe for the requested release action:

- `clean`: no dirty files relevant to the release action.
- `selected_only`: dirty files exist, but every dirty file is intentionally selected for this release action.
- `unrelated`: dirty files exist outside the selected release set.
- `unknown`: git state could not be classified.

Commit, stage, push, PR, tag, or publish success must not proceed from `unrelated` or `unknown` dirty scope. Block or ask for explicit scope resolution instead.

For public action success, the requested action and recorded effect must match. For example, a `push` request cannot report `external_effect=tag`, even if tag metadata is present.

## Route Decisions

### Ready

Use when convergence evidence is present, checks are acceptable, and no externally visible action was requested.

Action:

- append Release Round;
- report readiness and proposed commit message;
- report `workflow_continuation` for the next unfinished feature or an empty queue;
- route `none`.

### Prepared

Use when safe local release preparation completed, but the next requested step requires confirmation.

Action:

- append Release Round;
- identify exact files, command, and message that would be used;
- route `none`.

### Committed Or Pushed

Use only after explicit user authorization and successful git action.

Action:

- record command evidence;
- record action-specific metadata: remote/branch for push, PR URL and target branch for PR, tag name for tag, artifact or package target for publish;
- append Release Round;
- update registry release metadata when available.
- report `workflow_continuation` for the next unfinished feature or an empty queue.

### Needs Confirmation

Use when the requested action would stage, commit, push, PR, tag, or publish without explicit authorization.

Action:

- do not perform the action;
- return the exact confirmation needed.

### Needs Converge

Use when:

- feature status is not `done`;
- no Convergence Round or equivalent packet exists;
- review evidence is stale or points to a different feature.

Action:

- route to `converge`;
- do not release.

### Blocked

Use when:

- git state is unsafe or ambiguous;
- selected files are missing;
- required readiness checks fail;
- permissions or environment block the requested action.

Action:

- record blocker;
- route `none`.

## Review Append

Append a Release Round to the same review document with:

- source convergence round;
- selected release action;
- readiness checks and results;
- selected files;
- dirty scope;
- commit message plan;
- actions performed or explicitly not performed;
- action-specific metadata for push, PR, tag, or publish;
- confirmation needs;
- residual risks.

Do not rewrite prior rounds.

## Workflow Continuation

Before a release-ready terminal state, `release` must prove the selected source feature exists in `source.feature_registry_path`. The selected source feature registry row must match `source.feature_id`, `source.review_doc_path`, and `release_context.feature_status`; release-ready states require that row status to be `done`.

After `ready`, `committed`, or `pushed`, `release` is responsible for returning the next feature to process:

1. scan `.arbor/workflow/features.json` in registry order;
2. skip the just-finalized feature and any feature already `done`;
3. choose the next unfinished feature when one exists;
4. include registry evidence by setting `workflow_continuation.registry_path` to the source registry path and `workflow_continuation.registry_index` to the selected row index;
5. derive `workflow_continuation.next_feature_status` from the selected registry row rather than trusting prose or a copied field;
6. route `changes_requested` or `in_develop` to `develop`, `in_evaluate` to `evaluate`, `planned` with brainstorm context to `develop`, and `planned` without brainstorm context to `brainstorm`;
7. if no unfinished feature remains, set `workflow_continuation.status=none`.

When `workflow_continuation.status=available`, `next_feature_id` must be different from the selected `source.feature_id` and must exist in the registry row identified by `registry_path` and `registry_index`. The continuation status must match that selected registry row status; route selection must be derived from the row status. Non-final release states such as `needs_confirmation`, `needs_converge`, `blocked`, and `route_correction` must not advertise next-feature continuation.
