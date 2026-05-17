---
name: release
description: Internally checkpoint or finalize an Arbor feature by verifying review evidence, feature status, git readiness, commit-message convention, workflow continuation, policy-authorized checkpoint commits, and user confirmation before finalization commit, push, PR, tag, or publish.
---

# Release

## Purpose

Use `release` after `develop`, after `evaluate`, and after `converge` for Arbor-managed work. It is primarily an internal checkpoint/finalization skill in the Arbor pipeline, not the main user-facing entrypoint; finalization mode is the internal finalization gate for converged features.

`release` is a workflow gate for state tracking and current-feature finalization. In checkpoint mode, it records the latest developer or evaluator state before the next skill runs. For `checkpoint_develop`, that means creating a local checkpoint commit after a successful developer handoff before `evaluate` runs. In finalization mode, it verifies that the selected feature is converged, prepares safe local release evidence, enforces the commit convention, checks the project's actual version management method when one exists, blocks push, PR, tag, or publish actions unless the user explicitly authorized that action, then reports the next unfinished feature through `workflow_continuation`.

It does not plan, implement, evaluate, or decide convergence.

`release` has status-only user visibility. It may report concise action results such as checkpoint saved, commit hash, push status, confirmation needed, blocker, or next skill. It must not expose checkpoint handoff internals, dirty-scope reasoning, or full release evidence as the primary UI unless the user opens a debug/review trace.

`release` participates in the checkpoint policy but should stay status-only. In checkpoint mode after `develop` or `evaluate`, local checkpoint commits are internal workflow actions authorized by checkpoint policy and may continue automatically when no blocker, dirty-scope conflict, or confirmation need exists. In finalization mode after `converge`, it must surface status and stop before any externally visible action such as finalization commit, push, PR, tag, or publish unless the user explicitly authorized that exact action.

Checkpointed release output is not final delivery. In checkpoint mode, `release` preserves the current handoff and routes the same feature onward; it must not imply that evaluation, convergence, or final release has already happened.

When the user explicitly enables `develop_evaluate_converge` automation, `release` may carry internal checkpoint handoffs between `develop`, `evaluate`, and `converge`. Checkpoint policy authorizes the local checkpoint commit for those handoffs. It does not authorize finalization commit, push, PR, tag, publish, next-feature release, or any public action.

## Checklist

1. **Confirm source**: accept `develop.ready_for_evaluate` for `checkpoint_develop`, completed `evaluate` states for `checkpoint_evaluate`, and `converge.converged` or equivalent evidence for `finalize_feature`.
2. **Load state**: read `.arbor/workflow/features.json`, the selected feature's registry row, the selected review document, git status, and relevant diff/branch state.
3. **Verify mode evidence**: for develop checkpoints, confirm Context/Test Plan, done-when criteria when present, and Developer Round; for evaluate checkpoints, confirm Context/Test Plan, done-when criteria when present, Developer Round, and Evaluator Round; for finalization, confirm the selected source feature exists in the registry, its registry status is `done`, and the review document has Context/Test Plan, done-when criteria when present, Developer Round, Evaluator Round, and Convergence Round.
4. **Classify requested action**: local summary, stage, commit, push, PR, tag, publish, or route correction.
5. **Run readiness checks**: replay requested or policy-required checks when feasible; record blocked checks, replay conditions that affect release confidence, and residual risk.
6. **Prepare commit convention**: use `<type>[optional scope]: <description>` with optional body/footer.
7. **Check version management**: if the current project has a version-managed release artifact, identify the actual version management method before finalization or publish, such as plugin manifests, `package.json`, `pyproject.toml`, git tags, or a documented custom policy. Choose the target version from that method and the release scope. If a required bump is missing or the method is unclear, block release instead of publishing under the old version.
8. **Gate external actions**: for `checkpoint_develop`, create the local checkpoint commit when Arbor workflow checkpoint policy authorizes it and readiness checks pass. Treat checkpoint commits as internal workflow actions; push, PR, tag, publish, finalization commits, or other public/external actions always require explicit user authorization.
9. **Append release evidence**: append a Release Round to the same review document when release reaches a meaningful terminal state.
10. **Select continuation**: after a checkpoint state, route to the next stage for the same feature; after a release-final state, choose the next unfinished feature from `.arbor/workflow/features.json` or report that none remains.
11. **Update registry when justified**: update release metadata/status only for the selected feature.
12. **Update session memory**: before stopping with uncommitted Arbor workflow changes, ensure `.arbor/memory.md` exists and records unresolved in-flight state. After a successful commit/push/publish that resolves the current Arbor work, remove or shrink resolved entries so committed history becomes the source of truth.
13. **Return rendered checkpoint and runtime packet**: produce `release.v1` for runtime handoff, and make the normal user-visible response the rendered `user_response` status checkpoint, not raw JSON.

## Terminal States

- `ready`: release readiness is verified, but no externally visible action was requested.
- `checkpointed`: a developer or evaluator checkpoint was safely recorded and the same feature can continue to the next workflow skill.
- `prepared`: safe local release preparation is complete; confirmation is needed for the next external action.
- `committed`: an explicitly authorized finalization commit succeeded.
- `pushed`: an explicitly authorized push, PR, tag, or publish step succeeded.
- `needs_confirmation`: the requested action is externally visible and lacks explicit authorization.
- `needs_converge`: convergence evidence is missing or stale.
- `blocked`: environment, git state, checks, permissions, or dependencies block release.
- `route_correction`: request belongs to another skill or direct work.

## Core Rules

1. Do not finalize a feature unless convergence evidence is loaded.
2. Do not infer user authorization from broad intent; confirm the specific external action. Local checkpoint commits after successful develop are internal workflow actions authorized by active Arbor workflow checkpoint policy; finalization commits and public actions require explicit user authorization.
3. Do not plan feature scope.
4. Do not change implementation files.
5. Do not re-run develop/evaluate logic except for release-readiness checks.
6. Do not re-evaluate correctness; only check that required verification evidence exists before finalization or publish.
7. Keep local preparation separate from finalization commit, push, PR, tag, and publish; do not treat the internal checkpoint commit as final release.
8. Use the commit convention exactly: `<type>[optional scope]: <description>`.
9. Reject commit subjects whose description is empty after trimming whitespace.
10. Append release evidence to the same review document.
11. Preserve unrelated dirty work and stage only selected files when staging is authorized.
12. For commit or public release success, record performed action evidence and action-specific metadata.
13. For public action success, require `release_action.external_effect == release_context.release_action`.
14. Do not treat standalone `stage` as a completed release terminal; stage can be prepared or folded into an authorized finalization commit.
15. When continuation is available, `workflow_continuation.next_feature_id` must not equal `source.feature_id`.
16. For finalize-feature release-ready states, the selected source feature must exist in `source.feature_registry_path`; the source feature status must match `release_context.feature_status` and must be `done`. Checkpoint states must prove the selected source feature exists when a registry is available, but they do not require status `done`.
17. When continuation is available, include registry evidence: `registry_path` must match `source.feature_registry_path`, `registry_index` must identify the selected row, the row id must match `next_feature_id`, and the row status must match `next_feature_status`.
18. Keep user-facing release output status-only; detailed handoff, authorization, and evidence fields are for structured state, review documents, or debug views.
19. Emit a checkpoint policy that distinguishes safe internal continuation from user-stopping external actions.
20. Do not leave unresolved uncommitted Arbor workflow state without an up-to-date `.arbor/memory.md`; do not leave resolved memory entries after a successful commit or publish makes git history authoritative.
21. For workflow-facing finalization or publish, check that outcome and observability evidence exists: rendered output, review evidence, process state, git/file side effects, realistic replay or an explicit weak-pass gap, and trace evidence when the feature required trace proof. Preserve replay conditions when runtime target, source path or published cache, command, environment blocker, infrastructure failure, or weak-pass gap affects release confidence. Do not require LLM judges, fixed path matching, exact turn-by-turn replay, or one universal test type by default.
22. If the current project has version management, release must reason from the actual version management method before finalization or publish. A plugin should follow its plugin manifests, a JavaScript package should follow `package.json`, a Python package should follow `pyproject.toml` or the documented package metadata, and a tag-driven project should follow its tag convention. Do not reuse a stale version or invent a bump without citing the method and selected target version.

## Authorization Scope

`release` must preserve the difference between these action scopes:

- local summary or readiness check;
- staging plan;
- internal checkpoint commit authorized by active Arbor checkpoint policy;
- finalization commit;
- push, PR, tag, publish, marketplace sync, or other public/external side
  effect.

Authorization is not transitive across the ladder. A local summary does not
authorize staging; staging does not authorize a finalization commit; a
checkpoint commit does not authorize finalization; and finalization does not
authorize push, PR, tag, publish, marketplace sync, or connector mutation unless
the user explicitly authorized that exact action.

## Route Rules

| Situation | Terminal state | Next skill |
| --- | --- | --- |
| Developer handoff is checkpointed | `checkpointed` | `evaluate` |
| Evaluator evidence is checkpointed | `checkpointed` | `converge` |
| Converged feature is release-ready and no external action requested | `ready` | `none` |
| Local release prep is complete but confirmation is required | `prepared` or `needs_confirmation` | `none` |
| Finalization commit/push/PR/tag/publish explicitly authorized and succeeds | `committed` or `pushed` | `none` |
| Convergence evidence is missing | `needs_converge` | `converge` |
| Git/check/environment blocker prevents release | `blocked` | `none` |
| Request is not a release decision | `route_correction` | declared route or `none` |

For detailed boundary rationale, read `references/release-boundary.md`.

## Structured Output Contract

The structured `release.v1` object is an internal workflow/runtime packet. Produce this structure for runtime handoff. Normal user-facing output must render the compact status from `user_response` and `ui`; do not print the raw `release.v1` JSON unless the user explicitly asks for debug or machine output:

```json
{
  "schema_version": "release.v1",
  "raw_user_request": "",
  "source": {
    "from_skill": "converge",
    "feature_id": "",
    "feature_registry_path": ".arbor/workflow/features.json",
    "review_doc_path": "docs/review/<feature>-review.md",
    "convergence_round_ref": "",
    "develop_terminal_state": "",
    "developer_round_ref": "",
    "evaluate_terminal_state": "",
    "evaluator_round_ref": "",
    "feature_registry_signal": null,
    "blocking_finding_count": 0
  },
  "release_context": {
    "release_mode": "finalize_feature",
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
  "checkpoint_authorization": {
    "source": "none",
    "ref": "",
    "scope": "",
    "allows_local_commit": false
  },
  "checkpoint_handoff": {
    "status": "not_required",
    "preserved_terminal_state": "",
    "preserved_round_ref": "",
    "preserved_feature_registry_signal": null,
    "next_skill": "none",
    "reason": ""
  },
  "readiness": {
    "checks": [],
    "blocked_checks": [],
    "replay_conditions": [],
    "verification_evidence": [],
    "risks": []
  },
  "version_management": {
    "status": "not_detected",
    "method": "none",
    "version_sources": [],
    "current_version": "",
    "target_version": "",
    "bump_type": "none",
    "policy_source": "",
    "changed_version_files": [],
    "reason": ""
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
    "visibility": "status",
    "display_mode": "release_status",
    "summary": "",
    "status_items": [],
    "warnings": [],
    "next_actions": [],
    "debug_details_available": false,
    "checkpoint": {
      "visibility": "status",
      "continue_policy": "auto_continue_allowed",
      "reason": "The internal checkpoint was recorded and no user-visible external action is pending.",
      "resume_after": "auto_policy"
    }
  },
  "user_response": ""
}
```

Use these enums:

- `source.from_skill`: `develop`, `evaluate`, `converge`, `manual_release_request`, or `unknown`
- `release_context.release_mode`: `checkpoint_develop`, `checkpoint_evaluate`, `finalize_feature`, or `unknown`
- `checkpoint_authorization.source`: `user`, `policy`, or `none`; checkpoint commits require `user` or `policy`
- `checkpoint_handoff.status`: `preserved`, `not_required`, or `blocked`
- `release_context.release_action`: `summary`, `stage`, `commit`, `push`, `pr`, `tag`, `publish`, or `unknown`
- `release_context.dirty_scope`: `clean`, `selected_only`, `unrelated`, or `unknown`
- `release_action.status`: `not_run`, `prepared`, `completed`, `blocked`
- `release_action.external_effect`: `none`, `stage`, `commit`, `push`, `pr`, `tag`, or `publish`
- `version_management.status`: `not_detected`, `not_required`, `up_to_date`, `bump_required`, or `blocked`
- `version_management.method`: `none`, `plugin_manifest_semver`, `package_json`, `pyproject_pep440`, `git_tag`, `custom`, or `unknown`
- `version_management.bump_type`: `none`, `patch`, `minor`, `major`, `prerelease`, `custom`, or `unknown`
- `feature_registry_update.status`: `updated`, `not_required`, or `blocked`
- `review_append.status`: `appended`, `blocker_packet`, or `not_required`
- `workflow_continuation.status`: `available`, `none`, or `blocked`
- `workflow_continuation.next_skill`: `brainstorm`, `develop`, `evaluate`, or `none`
- `route.terminal_state`: `ready`, `checkpointed`, `prepared`, `committed`, `pushed`, `needs_confirmation`, `needs_converge`, `blocked`, or `route_correction`
- `route.next_skill`: `evaluate`, `converge`, or `none`
- `ui.visibility`: `status` or `debug`
- `ui.display_mode`: `release_status` or `trace`
- `ui.checkpoint.visibility`: `status`, `user_visible`, or `debug`
- `ui.checkpoint.continue_policy`: `auto_continue_allowed`, `stop_for_user`, or `must_stop`
- `ui.checkpoint.resume_after`: `auto_policy`, `user_acknowledgement`, `user_confirmation`, `blocker_resolved`, or `none`

Use `auto_continue_allowed` only for internal checkpoint states whose local checkpoint commit completed with no blocker, dirty-scope conflict, or confirmation need, including internal checkpoint handoffs under an explicit `develop_evaluate_converge` automation policy. Use `stop_for_user` for release-ready finalization summaries and next-feature reports. Use `must_stop` for finalization commit, push, PR, tag, publish, dirty-scope conflicts, missing convergence evidence, or any required confirmation. Use `must_stop` for commit, push, PR, tag, publish.

## User-Visible Status

Use `ui.summary`, `ui.status_items`, `ui.warnings`, and `ui.next_actions` for concise status output only:

- checkpoint mode: checkpoint status, local checkpoint commit hash when created, and next skill;
- finalization mode: commit message, commit hash, push/PR/tag/publish status when performed, and next feature;
- blocked or confirmation mode: blocker or exact confirmation needed.

Do not make the primary UI display `checkpoint_handoff`, `feature_registry_signal`, `dirty_scope`, selected-file reasoning, or authorization internals. Those fields remain available for review documents and debug traces.

## Self-Check

Before returning:

1. Did I load registry, the selected source feature row, review doc, mode-specific review evidence, and git state?
2. Did I avoid implementation changes and convergence decisions?
3. Did I check that done-when verification evidence exists without re-evaluating correctness?
4. Did I preserve replay conditions when runtime target, source path or published cache, command, environment blocker, infrastructure failure, or weak-pass gap affected release confidence?
5. Did I verify the selected release action and whether it is externally visible?
6. Did I require explicit confirmation before finalization commit, push, PR, tag, or publish while allowing policy-authorized checkpoint commits?
7. Did I keep unrelated dirty work out of selected files and record `dirty_scope`?
8. Did I build a valid convention commit message with a non-empty trimmed description?
9. Did successful commit/push/PR/tag/publish output include performed evidence and metadata?
10. Did public action success match the requested action and safe dirty scope?
11. Did I append release evidence or a blocker packet to the review document?
12. If release reached a checkpoint state, did I route the same feature to the next stage without selecting a new feature?
13. If release reached a final state, did I select a different unfinished feature from the registry row data or explicitly report that none remains?
14. Did I keep user-visible release output status-only while preserving detailed evidence in structured fields?
15. Did I create or refresh `.arbor/memory.md` when unresolved uncommitted Arbor workflow state remains, or clear resolved entries after a successful commit/publish?
16. Did I set checkpoint policy so internal checkpoints may continue automatically but external actions and finalization decisions stop for the user?
17. If the project has version management, did I identify the actual method, choose the target version from that method, include the version files in the selected release scope when needed, and block the release when the bump is required but absent?
