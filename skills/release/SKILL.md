---
name: release
description: Internally finalize an Arbor feature after convergence by verifying review evidence, feature status, git readiness, commit-message convention, workflow continuation, and user confirmation before commit, push, PR, tag, or publish.
---

# Release

## Purpose

Use `release` after `converge` has finalized an Arbor-managed feature. It is primarily an internal finalization skill in the Arbor pipeline, not the main user-facing entrypoint.

`release` is a workflow gate for current-feature finalization. It verifies that the selected feature is converged, prepares safe local release evidence, enforces the commit convention, blocks commit, push, PR, tag, or publish actions unless the user explicitly authorized that action, then reports the next unfinished feature through `workflow_continuation`.

It does not plan, implement, evaluate, or decide convergence.

## Checklist

1. **Confirm source**: prefer a `converge.converged` handoff; accept a manual release request only when equivalent convergence evidence is loaded.
2. **Load state**: read `.arbor/workflow/features.json`, the selected feature's registry row, the selected review document, git status, and relevant diff/branch state.
3. **Verify convergence evidence**: confirm the selected source feature exists in the registry, its registry status is `done`, and the review document has Context/Test Plan, Developer Round, Evaluator Round, and Convergence Round.
4. **Classify requested action**: local summary, stage, commit, push, PR, tag, publish, or route correction.
5. **Run readiness checks**: replay requested or policy-required checks when feasible; record blocked checks and residual risk.
6. **Prepare commit convention**: use `<type>[optional scope]: <description>` with optional body/footer.
7. **Gate external actions**: do not commit, push, open PR, tag, publish, or otherwise make externally visible changes without explicit user authorization.
8. **Append release evidence**: append a Release Round to the same review document when release reaches a meaningful terminal state.
9. **Select continuation**: after a release-final state, choose the next unfinished feature from `.arbor/workflow/features.json` or report that none remains.
10. **Update registry when justified**: update release metadata/status only for the selected feature.
11. **Return structured output first**: emit `release.v1` before prose.

## Terminal States

- `ready`: release readiness is verified, but no externally visible action was requested.
- `prepared`: safe local release preparation is complete; confirmation is needed for the next external action.
- `committed`: an explicitly authorized commit succeeded.
- `pushed`: an explicitly authorized push, PR, tag, or publish step succeeded.
- `needs_confirmation`: the requested action is externally visible and lacks explicit authorization.
- `needs_converge`: convergence evidence is missing or stale.
- `blocked`: environment, git state, checks, permissions, or dependencies block release.
- `route_correction`: request belongs to another skill or direct work.

## Core Rules

1. Do not release a feature unless convergence evidence is loaded.
2. Do not infer user authorization from broad intent; confirm the specific external action.
3. Do not plan feature scope.
4. Do not change implementation files.
5. Do not re-run develop/evaluate logic except for release-readiness checks.
6. Keep local preparation separate from commit, push, PR, tag, and publish.
7. Use the commit convention exactly: `<type>[optional scope]: <description>`.
8. Reject commit subjects whose description is empty after trimming whitespace.
9. Append release evidence to the same review document.
10. Preserve unrelated dirty work and stage only selected files when staging is authorized.
11. For commit or public release success, record performed action evidence and action-specific metadata.
12. For public action success, require `release_action.external_effect == release_context.release_action`.
13. Do not treat standalone `stage` as a completed release terminal; stage can be prepared or folded into an authorized commit.
14. When continuation is available, `workflow_continuation.next_feature_id` must not equal `source.feature_id`.
15. For release-ready states, the selected source feature must exist in `source.feature_registry_path`; the source feature status must match `release_context.feature_status` and must be `done`.
16. When continuation is available, include registry evidence: `registry_path` must match `source.feature_registry_path`, `registry_index` must identify the selected row, the row id must match `next_feature_id`, and the row status must match `next_feature_status`.

## Route Rules

| Situation | Terminal state | Next skill |
| --- | --- | --- |
| Converged feature is release-ready and no external action requested | `ready` | `none` |
| Local release prep is complete but confirmation is required | `prepared` or `needs_confirmation` | `none` |
| Commit/push/PR/tag/publish explicitly authorized and succeeds | `committed` or `pushed` | `none` |
| Convergence evidence is missing | `needs_converge` | `converge` |
| Git/check/environment blocker prevents release | `blocked` | `none` |
| Request is not a release decision | `route_correction` | declared route or `none` |

For detailed boundary rationale, read `references/release-boundary.md`.

## Structured Output Contract

Return this structure first:

```json
{
  "schema_version": "release.v1",
  "raw_user_request": "",
  "source": {
    "from_skill": "converge",
    "feature_id": "",
    "feature_registry_path": ".arbor/workflow/features.json",
    "review_doc_path": "docs/review/<feature>-review.md",
    "convergence_round_ref": ""
  },
  "release_context": {
    "feature_status": "done",
    "convergence_loaded": true,
    "developer_round_loaded": true,
    "evaluator_round_loaded": true,
    "release_action": "commit",
    "user_authorized_external_action": false,
    "selected_files": [],
    "dirty_worktree": true,
    "dirty_scope": "selected_only"
  },
  "readiness": {
    "checks": [],
    "blocked_checks": [],
    "risks": []
  },
  "commit_plan": {
    "type": "feat",
    "scope": "",
    "description": "",
    "body": "",
    "footers": [],
    "message": ""
  },
  "release_action": {
    "status": "not_run",
    "performed": [],
    "requires_confirmation": true,
    "external_effect": "commit",
    "metadata": {},
    "reason": ""
  },
  "feature_registry_update": {
    "status": "not_required",
    "path": ".arbor/workflow/features.json",
    "feature_id": "",
    "reason": ""
  },
  "review_append": {
    "status": "appended",
    "path": "docs/review/<feature>-review.md",
    "round_type": "release",
    "summary": ""
  },
  "workflow_continuation": {
    "status": "none",
    "next_feature_id": null,
    "next_feature_status": null,
    "next_feature_brainstorm_context_loaded": false,
    "next_skill": "none",
    "registry_path": null,
    "registry_index": null,
    "reason": ""
  },
  "route": {
    "terminal_state": "prepared",
    "next_skill": "none",
    "reason": ""
  },
  "ui": {
    "summary": "",
    "warnings": [],
    "next_actions": []
  },
  "user_response": ""
}
```

Use these enums:

- `source.from_skill`: `converge`, `manual_release_request`, or `unknown`
- `release_context.release_action`: `summary`, `stage`, `commit`, `push`, `pr`, `tag`, `publish`, or `unknown`
- `release_context.dirty_scope`: `clean`, `selected_only`, `unrelated`, or `unknown`
- `release_action.status`: `not_run`, `prepared`, `completed`, `blocked`
- `release_action.external_effect`: `none`, `stage`, `commit`, `push`, `pr`, `tag`, or `publish`
- `feature_registry_update.status`: `updated`, `not_required`, or `blocked`
- `review_append.status`: `appended`, `blocker_packet`, or `not_required`
- `workflow_continuation.status`: `available`, `none`, or `blocked`
- `workflow_continuation.next_skill`: `brainstorm`, `develop`, `evaluate`, or `none`
- `route.terminal_state`: `ready`, `prepared`, `committed`, `pushed`, `needs_confirmation`, `needs_converge`, `blocked`, or `route_correction`
- `route.next_skill`: `converge` or `none`

## Self-Check

Before returning:

1. Did I load registry, the selected source feature row, review doc, convergence evidence, and git state?
2. Did I avoid implementation changes and convergence decisions?
3. Did I verify the selected release action and whether it is externally visible?
4. Did I require explicit confirmation before commit, push, PR, tag, or publish?
5. Did I keep unrelated dirty work out of selected files and record `dirty_scope`?
6. Did I build a valid convention commit message with a non-empty trimmed description?
7. Did successful commit/push/PR/tag/publish output include performed evidence and metadata?
8. Did public action success match the requested action and safe dirty scope?
9. Did I append release evidence or a blocker packet to the review document?
10. If release reached a final state, did I select a different unfinished feature from the registry row data or explicitly report that none remains?
