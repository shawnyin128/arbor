# Release Boundary

## Position

`release` sits after `develop`, `evaluate`, and `converge` as an internal checkpoint/finalization step:

```text
intake -> brainstorm -> develop -> release(checkpoint_develop) -> evaluate -> release(checkpoint_evaluate) -> converge -> release(finalize_feature) -> next feature
```

It is a current-feature state-tracking and finalization gate, not a planner, developer, evaluator, convergence judge, or primary user-facing entrypoint. Its user visibility is status-only: report what checkpoint/release action happened, whether confirmation is needed, and what comes next; keep detailed release reasoning in structured fields, review docs, or debug traces.

## Inputs

Minimum evidence:

- selected feature id from the develop, evaluate, or convergence handoff;
- `.arbor/workflow/features.json` and the selected source feature registry row;
- shared review document path;
- mode-specific review evidence:
  - `checkpoint_develop`: Context/Test Plan and latest Developer Round;
  - `checkpoint_evaluate`: Context/Test Plan, latest Developer Round, latest Evaluator Round, evaluator terminal state, feature registry signal, and blocking finding count;
  - `finalize_feature`: Convergence Round or equivalent convergence packet plus latest Developer Round and Evaluator Round references;
- verification evidence for done-when criteria when the brainstorm review context defines them;
- outcome and observability evidence for workflow-facing finalization or publish: rendered output, review evidence, process state, git/file side effects, realistic replay or an explicit weak-pass gap, and trace evidence when the feature required trace proof;
- replay conditions that affect release confidence, including runtime target,
  source path or published cache, relevant command, environment blocker,
  infrastructure/environment versus workflow-contract classification, and
  weak-pass gap when relevant;
- version-management evidence when the project has a versioned release artifact: version source files, current version, target_version, bump type, changed version files, and the actual version management method used to choose the bump;
- requested release action;
- git status, selected files, dirty scope, and branch/remotes when relevant;
- replayable `checkpoint_authorization` evidence for local checkpoint commits, with `source=user` or `source=policy`;
- user authorization for public/external actions;
- feature registry rows needed for next-feature continuation.

If finalization convergence evidence is missing, return `needs_converge`. If authorization is missing for an external action, return `needs_confirmation`.

## External Action Boundary

Safe local preparation:

- inspect git status and diffs;
- run release-readiness checks;
- check that verification evidence exists for done-when criteria without re-evaluating correctness;
- check that outcome and observability evidence exists for workflow-facing release gates without re-evaluating correctness;
- preserve replay conditions when runtime target, cache/source path, command,
  environment blocker, infrastructure failure, or weak-pass gap changes release
  confidence;
- prepare selected file list;
- classify dirty scope as `clean`, `selected_only`, `unrelated`, or `unknown`;
- draft commit message;
- inspect version-management sources and select the target version from the project's actual method;
- append Release Round or blocker packet.
- create a local checkpoint commit after `develop.ready_for_evaluate` when workflow checkpoint policy authorizes it and readiness checks pass;
- route the same feature to the next stage after a checkpoint state;
- select the next unfinished feature after a release-final state.

Confirmation-gated actions:

- staging files;
- creating a finalization commit;
- pushing a branch;
- opening or updating a PR;
- creating a tag;
- publishing a package, plugin, release artifact, or marketplace entry.

The user must authorize the specific public or finalization action. "Release this" can authorize preparation, but not every external action unless the prompt clearly asks for it. For Arbor-managed checkpoint mode, local git commits are internal workflow actions authorized by active workflow checkpoint policy; public actions and finalization commits still require explicit user authorization. Checkpoint authorization must be machine-readable through `checkpoint_authorization.source`, `checkpoint_authorization.ref`, `checkpoint_authorization.scope`, and `allows_local_commit`.

Standalone `stage` has no completed release terminal. `release` may prepare an exact stage file list, and staging may happen as part of an explicitly authorized finalization commit, but a stage-only request should not be reported as completed release delivery.

## Authorization Scope Ladder

`release` should treat authorization as a ladder with non-transitive steps:

| Scope | Allowed Without Extra Confirmation | Requires Explicit User Authorization |
| --- | --- | --- |
| Local summary or readiness check | Inspect state, report blockers, draft a commit plan. | Staging, commit, push, PR, tag, publish. |
| Staging plan | Prepare the exact selected file list. | Running `git add` unless folded into an explicitly authorized finalization commit. |
| Internal checkpoint commit | Create a local checkpoint commit only under active Arbor checkpoint policy and selected-only dirty scope. | Finalization commit or any public action. |
| Finalization commit | Commit selected files only when explicitly authorized. | Push, PR, tag, publish, marketplace sync, connector mutation. |
| Public or external action | Nothing beyond the exact authorized action. | Any additional public/external effect not named in the prompt. |

Broad wording such as "go ahead" inherits only the active scope. It does not
upgrade a local preparation request into a finalization commit or public action.

## User-Visible Boundary

`release` should not render a full workflow panel. It should emit a compact status notification:

- checkpoint mode: checkpoint saved or blocked, commit hash when created, and next skill;
- finalization mode: readiness, commit/push/PR/tag/publish result when performed, and next feature;
- confirmation mode: the exact action requiring authorization;
- blocked mode: the blocker and next safe action.

The structured `release.v1` object is an internal workflow/runtime packet. Normal user-facing output should render the compact status from `user_response` and `ui`, not print the raw JSON unless explicit debug output is requested.

Do not show `checkpoint_handoff`, `feature_registry_signal`, dirty-scope analysis, selected-file reasoning, or authorization internals as primary UI. These remain machine-readable for the workflow and available in review/debug views.

## Checkpoint Policy

`release` participates in checkpoint policy but remains status-only. Its output must include `ui.checkpoint`:

```json
{
  "ui": {
    "visibility": "status",
    "display_mode": "release_status",
    "checkpoint": {
      "visibility": "status",
      "continue_policy": "auto_continue_allowed",
      "reason": "The internal checkpoint was recorded and no user-visible external action is pending.",
      "resume_after": "auto_policy"
    }
  }
}
```

Checkpointed release output is not final delivery. In checkpoint mode, `release` preserves the current handoff and routes the same feature onward; it must not imply that evaluation, convergence, or final release has already happened.

Use `continue_policy=auto_continue_allowed` only for safe internal `checkpoint_develop` or `checkpoint_evaluate` handoffs whose local checkpoint commit completed with no blocker, dirty-scope conflict, or confirmation need. Use `stop_for_user` for release-ready finalization summaries and next-feature reports. Use `must_stop` for finalization commit, push, PR, tag, publish, dirty-scope conflicts, missing convergence evidence, or any required confirmation.

An explicit `develop_evaluate_converge` automation policy can allow release to carry internal checkpoint handoffs between `develop`, `evaluate`, and `converge`. It authorizes the local checkpoint commit for those handoffs. It does not authorize finalization commit, push, PR, tag, publish, next-feature release, or any public action.

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

## Version Management

Before finalization or publish, `release` must check whether the current project has version management. It should inspect the project’s actual source of version truth instead of assuming a universal policy:

- Codex or Claude plugins: `.codex-plugin/plugin.json` and `.claude-plugin/plugin.json`, using the shared SemVer value when both manifests exist.
- JavaScript or TypeScript packages: `package.json`, and lockfile or workspace policy when present.
- Python packages: `pyproject.toml`, setup metadata, or the documented package source when present.
- Tag-driven projects: the established git tag pattern, such as `v1.2.3`.
- Custom projects: the project’s documented release notes, manifest, or release script contract.

When a versioned release artifact is affected, `release` records `version_management` evidence: `status`, `method`, `version_sources`, `current_version`, `target_version`, `bump_type`, `policy_source`, `changed_version_files`, and `reason`. The target version must come from the detected method and the release scope. For SemVer sources, use the smallest accurate bump: patch for bug fixes and release-gate hardening, minor for new user-facing capability, major only for breaking behavior, and prerelease/custom only when the project’s existing method uses it.

If source changes require a version bump but the version source files do not reflect the selected `target_version`, release must return a blocked state with `version_management.status=bump_required`. It must not commit, push, tag, publish, or sync package/plugin caches under the stale version. If the method is detected but ambiguous, use `version_management.status=blocked` and ask for the exact version policy instead of inventing a bump.

For successful publish or tag actions on versioned projects, the release action metadata must reflect the selected target version, such as `artifact_target=arbor-plugin@0.4.3` or `tag_name=v0.4.3`. Cache verification must compare the cache path derived from the manifest version, not a hard-coded old version directory.

## Route Decisions

### Outcome And Observability Evidence

For workflow-facing finalization or publish, `release` checks evidence existence rather than correctness re-evaluation. Required evidence may include rendered output, review evidence, process state, git/file side effects, realistic replay or an explicit weak-pass gap, and trace evidence when the feature required trace proof.

Release must not require LLM judges, fixed path matching, exact turn-by-turn replay, subagents, worktrees, fan-out execution, or one universal test type by default. If evaluator or convergence evidence names a weak-pass gap, release should preserve that risk in release evidence instead of silently presenting the feature as fully live-proven.

Release should also preserve replay conditions that affect finalization or
publish confidence. These facts are scoped to meaningful replayability: runtime
target, source path or published cache, relevant command, environment blocker,
infrastructure/environment versus workflow-contract classification, and
weak-pass gap. Do not require heavyweight environment metadata when a small
direct task, documentation-only change, or artifact-only check does not depend
on those facts.

### Checkpointed

Use when a developer or evaluator checkpoint has mode-specific review evidence, safe selected files, and local checkpoint authorization through user approval or workflow checkpoint policy. For `checkpoint_develop`, successful developer handoff plus workflow checkpoint policy is enough authorization to create the local checkpoint commit before evaluation.

Action:

- append Release Round;
- record checkpoint mode and selected files;
- preserve the upstream handoff in `checkpoint_handoff`, including terminal state, review round reference, and feature registry signal when the checkpoint comes from evaluate;
- record performed checkpoint commit when it was created; block rather than silently continue if `checkpoint_develop` lacks local commit authorization;
- route `checkpoint_develop` to `evaluate`;
- route `checkpoint_evaluate` to `converge`;
- keep `workflow_continuation.status=none` because this is the same feature, not next-feature selection.

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

Use when the requested action would stage, create a finalization commit, push, PR, tag, or publish without explicit authorization.

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

- release mode;
- source checkpoint or convergence round;
- checkpoint authorization evidence;
- checkpoint handoff preservation evidence;
- selected release action;
- readiness checks and results;
- replay conditions that affect confidence;
- selected files;
- dirty scope;
- version-management method, target_version, bump type, and changed version files or blocker;
- commit message plan;
- actions performed or explicitly not performed;
- action-specific metadata for push, PR, tag, or publish;
- confirmation needs;
- residual risks.

Do not rewrite prior rounds.

## Workflow Continuation

Before a checkpoint or final release terminal state, `release` must prove the selected source feature exists in `source.feature_registry_path` when a registry path is available. The selected source feature registry row must match `source.feature_id`, `source.review_doc_path`, and `release_context.feature_status`. Finalize-feature release-ready states require that row status to be `done`; checkpoint states keep the current feature status, usually `in_evaluate`.

After `checkpointed`, `release` routes the same feature to the next stage:

1. `checkpoint_develop` routes to `evaluate`;
2. `checkpoint_evaluate` routes to `converge`;
3. `workflow_continuation.status` remains `none` because the current feature is still active.

After `ready`, `committed`, or `pushed`, `release` is responsible for returning the next feature to process:

1. scan `.arbor/workflow/features.json` in registry order;
2. skip the just-finalized feature and any feature already `done`;
3. choose the next unfinished feature when one exists;
4. include registry evidence by setting `workflow_continuation.registry_path` to the source registry path and `workflow_continuation.registry_index` to the selected row index;
5. derive `workflow_continuation.next_feature_status` from the selected registry row rather than trusting prose or a copied field;
6. route `changes_requested` or `in_develop` to `develop`, `in_evaluate` to `evaluate`, `planned` with brainstorm context to `develop`, and `planned` without brainstorm context to `brainstorm`;
7. if no unfinished feature remains, set `workflow_continuation.status=none`.

When `workflow_continuation.status=available`, `next_feature_id` must be different from the selected `source.feature_id` and must exist in the registry row identified by `registry_path` and `registry_index`. The continuation status must match that selected registry row status; route selection must be derived from the row status. Non-final release states such as `needs_confirmation`, `needs_converge`, `blocked`, and `route_correction` must not advertise next-feature continuation.
