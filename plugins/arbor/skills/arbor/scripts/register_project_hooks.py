#!/usr/bin/env python3
"""Register Arbor hook intents in project-local hook configuration."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Iterable

from arbor_project_state import (
    CANONICAL_MEMORY_PATH,
    CODEX_HOOK_CONFIG_PATH,
    PROJECT_GUIDE_PATH,
    project_path,
    resolve_project_root,
)

HOOK_CONFIG_VERSION = 1

MEMORY_HYGIENE_CASE_CORPUS: list[dict[str, Any]] = [
    {
        "id": "trigger-dirty-edit-stop",
        "situation": "after any Arbor-managed file edit before the assistant stops",
        "expected": "trigger",
        "git_state": "dirty",
        "arbor_managed": True,
        "checkpoint": "stop",
        "rationale": "uncommitted Arbor work needs a resume pointer",
    },
    {
        "id": "trigger-brainstorm-feature-registry",
        "situation": "after brainstorm creates or updates `.arbor/workflow/features.json`",
        "expected": "trigger",
        "git_state": "dirty",
        "arbor_managed": True,
        "checkpoint": "brainstorm_artifact",
        "rationale": "feature state changed before commit",
    },
    {
        "id": "trigger-brainstorm-review-plan",
        "situation": "after brainstorm creates or updates a review Context/Test Plan",
        "expected": "trigger",
        "git_state": "dirty",
        "arbor_managed": True,
        "checkpoint": "brainstorm_artifact",
        "rationale": "planning evidence changed before handoff",
    },
    {
        "id": "trigger-develop-files",
        "situation": "after develop changes code, docs, tests, manifests, scripts, or workflow artifacts",
        "expected": "trigger",
        "git_state": "dirty",
        "arbor_managed": True,
        "checkpoint": "develop_edit",
        "rationale": "implementation state is not durable yet",
    },
    {
        "id": "trigger-develop-review-round",
        "situation": "after develop appends a Developer Round or updates feature status",
        "expected": "trigger",
        "git_state": "dirty",
        "arbor_managed": True,
        "checkpoint": "develop_handoff",
        "rationale": "handoff evidence should be resumable",
    },
    {
        "id": "trigger-evaluate-round",
        "situation": "after evaluate appends an Evaluator Round or records findings",
        "expected": "trigger",
        "git_state": "dirty",
        "arbor_managed": True,
        "checkpoint": "evaluate_handoff",
        "rationale": "findings can drive the next correction loop",
    },
    {
        "id": "trigger-converge-round",
        "situation": "after converge appends a Convergence Round or changes feature status",
        "expected": "trigger",
        "git_state": "dirty",
        "arbor_managed": True,
        "checkpoint": "converge_decision",
        "rationale": "loop decision is active state until committed",
    },
    {
        "id": "trigger-release-precommit",
        "situation": "after release prepares a local stage or commit but before the commit exists",
        "expected": "trigger",
        "git_state": "dirty",
        "arbor_managed": True,
        "checkpoint": "release_gate",
        "rationale": "release preparation is unresolved until committed",
    },
    {
        "id": "trigger-failed-check-dirty",
        "situation": "after a command or test fails while Arbor-managed work is still dirty",
        "expected": "trigger",
        "git_state": "dirty",
        "arbor_managed": True,
        "checkpoint": "failed_check",
        "rationale": "the failure is a next-step blocker",
    },
    {
        "id": "trigger-workflow-bugfix",
        "situation": "after a user reports a workflow bug that starts an Arbor-managed fix",
        "expected": "trigger",
        "git_state": "dirty_or_pending",
        "arbor_managed": True,
        "checkpoint": "bugfix_start",
        "rationale": "bug context must survive interruptions",
    },
    {
        "id": "trigger-scope-change",
        "situation": "after a user changes scope, constraints, naming, or acceptance criteria for active Arbor work",
        "expected": "trigger",
        "git_state": "dirty_or_pending",
        "arbor_managed": True,
        "checkpoint": "scope_change",
        "rationale": "new constraints affect the active implementation",
    },
    {
        "id": "trigger-brainstorm-to-develop",
        "situation": "before handing off from brainstorm to develop with dirty Arbor artifacts",
        "expected": "trigger",
        "git_state": "dirty",
        "arbor_managed": True,
        "checkpoint": "skill_handoff",
        "rationale": "the developer should recover the selected plan",
    },
    {
        "id": "trigger-develop-to-release-evaluate",
        "situation": "before handing off from develop to release/evaluate with dirty Arbor artifacts",
        "expected": "trigger",
        "git_state": "dirty",
        "arbor_managed": True,
        "checkpoint": "skill_handoff",
        "rationale": "developer evidence is active handoff state",
    },
    {
        "id": "trigger-evaluate-to-release-converge",
        "situation": "before handing off from evaluate to release/converge with dirty Arbor artifacts",
        "expected": "trigger",
        "git_state": "dirty",
        "arbor_managed": True,
        "checkpoint": "skill_handoff",
        "rationale": "evaluator decision is active handoff state",
    },
    {
        "id": "trigger-converge-to-release-or-correction",
        "situation": "before handing off from converge to release or a correction loop with dirty Arbor artifacts",
        "expected": "trigger",
        "git_state": "dirty",
        "arbor_managed": True,
        "checkpoint": "skill_handoff",
        "rationale": "convergence route should not be lost",
    },
    {
        "id": "trigger-user-review-checkpoint",
        "situation": "before asking the user to review a checkpoint while git status is dirty",
        "expected": "trigger",
        "git_state": "dirty",
        "arbor_managed": True,
        "checkpoint": "user_review",
        "rationale": "the checkpoint may pause the session",
    },
    {
        "id": "trigger-session-boundary",
        "situation": "before pausing, sleeping, archiving, compacting, or ending a session with dirty Arbor work",
        "expected": "trigger",
        "git_state": "dirty",
        "arbor_managed": True,
        "checkpoint": "session_boundary",
        "rationale": "session boundaries require recovery state",
    },
    {
        "id": "trigger-release-preflight",
        "situation": "before running release preflight, commit, push, tag, PR, or publish",
        "expected": "trigger",
        "git_state": "dirty_or_staged",
        "arbor_managed": True,
        "checkpoint": "release_gate",
        "rationale": "release actions should see current in-flight state first",
    },
    {
        "id": "trigger-cache-sync",
        "situation": "after syncing local plugin caches while package changes remain uncommitted",
        "expected": "trigger",
        "git_state": "dirty",
        "arbor_managed": True,
        "checkpoint": "cache_sync",
        "rationale": "runtime cache and source may diverge before commit",
    },
    {
        "id": "trigger-ignored-review-assets",
        "situation": "after editing ignored local review, fixture, or validation assets that explain uncommitted package changes",
        "expected": "trigger",
        "git_state": "dirty_or_ignored",
        "arbor_managed": True,
        "checkpoint": "local_evidence",
        "rationale": "ignored evidence may be the only resume pointer",
    },
    {
        "id": "suppress-clean-complete",
        "situation": "clean git status and no unresolved conversation state",
        "expected": "suppress",
        "git_state": "clean",
        "arbor_managed": False,
        "checkpoint": "none",
        "rationale": "there is no uncommitted state to recover",
    },
    {
        "id": "suppress-direct-explanation",
        "situation": "direct one-off explanation with no project file changes",
        "expected": "suppress",
        "git_state": "clean",
        "arbor_managed": False,
        "checkpoint": "direct_answer",
        "rationale": "direct answers should not create memory churn",
    },
    {
        "id": "suppress-read-only",
        "situation": "read-only inspection that leaves no dirty files and no unresolved Arbor decision",
        "expected": "suppress",
        "git_state": "clean",
        "arbor_managed": False,
        "checkpoint": "read_only",
        "rationale": "inspection without active state does not need memory",
    },
    {
        "id": "suppress-committed-pruned",
        "situation": "finished work already committed and pushed, with memory pruned",
        "expected": "suppress",
        "git_state": "clean",
        "arbor_managed": True,
        "checkpoint": "complete",
        "rationale": "durable history replaced short-term memory",
    },
    {
        "id": "suppress-guide-only",
        "situation": "stable project-guide or map update that belongs only in AGENTS.md",
        "expected": "suppress",
        "git_state": "dirty",
        "arbor_managed": False,
        "checkpoint": "guide_drift",
        "rationale": "stable guide drift uses the AGENTS hook instead",
    },
    {
        "id": "suppress-committed-review",
        "situation": "durable review evidence already committed with no active follow-up",
        "expected": "suppress",
        "git_state": "clean",
        "arbor_managed": True,
        "checkpoint": "complete",
        "rationale": "there is no remaining active loop",
    },
    {
        "id": "suppress-no-write-turn",
        "situation": "user explicitly forbids file writes for the current turn",
        "expected": "suppress",
        "git_state": "any",
        "arbor_managed": False,
        "checkpoint": "no_write",
        "rationale": "user write prohibition wins",
    },
    {
        "id": "suppress-unrelated-dirty",
        "situation": "dirty files are unrelated to Arbor and the user has not asked Arbor to manage them",
        "expected": "suppress",
        "git_state": "dirty_unrelated",
        "arbor_managed": False,
        "checkpoint": "out_of_scope",
        "rationale": "do not claim unrelated user changes as Arbor state",
    },
]

MEMORY_HYGIENE_POSITIVE_CASES = [
    str(case["situation"]) for case in MEMORY_HYGIENE_CASE_CORPUS if case.get("expected") == "trigger"
]

MEMORY_HYGIENE_NEGATIVE_CASES = [
    str(case["situation"]) for case in MEMORY_HYGIENE_CASE_CORPUS if case.get("expected") == "suppress"
]

GUIDE_DRIFT_CASE_CORPUS: list[dict[str, Any]] = [
    {
        "id": "trigger-new-top-level-directory",
        "situation": "after adding a new top-level source, tool, package, data, docs, or workflow directory",
        "expected": "trigger",
        "map_area": "Project Map",
        "rationale": "new durable entrypoints should be discoverable from AGENTS.md",
    },
    {
        "id": "trigger-removed-or-renamed-entrypoint",
        "situation": "after removing or renaming a top-level directory or stable entrypoint named in AGENTS.md",
        "expected": "trigger",
        "map_area": "Project Map",
        "rationale": "stale map pointers mislead future startup context",
    },
    {
        "id": "trigger-new-skill-or-runtime-adapter",
        "situation": "after adding a new skill, hook adapter, runtime cache path, or shared helper module",
        "expected": "trigger",
        "map_area": "Project Map",
        "rationale": "workflow entrypoints need an AGENTS map pointer",
    },
    {
        "id": "trigger-guide-drift-before-release",
        "situation": "before release, publish, push, or handoff when project structure changed",
        "expected": "trigger",
        "map_area": "Project Map",
        "rationale": "release should not publish a stale project guide",
    },
    {
        "id": "trigger-project-map-drift-packet",
        "situation": "when the AGENTS drift packet reports `Project Map Drift Candidates` as `update-needed`",
        "expected": "trigger",
        "map_area": "Project Map",
        "rationale": "the packet has detected missing map candidates",
    },
    {
        "id": "suppress-transient-temp-files",
        "situation": "only transient cache, pycache, temporary output, or ignored scratch files changed",
        "expected": "suppress",
        "map_area": "none",
        "rationale": "temporary files do not belong in AGENTS.md",
    },
    {
        "id": "suppress-current-session-progress",
        "situation": "only in-flight implementation notes or unresolved current-session progress changed",
        "expected": "suppress",
        "map_area": "none",
        "rationale": "short-term progress belongs in .arbor/memory.md",
    },
    {
        "id": "suppress-no-durable-map-change",
        "situation": "git status is clean and the current Project Map already mentions the stable entrypoints",
        "expected": "suppress",
        "map_area": "none",
        "rationale": "there is no durable guide drift to apply",
    },
]

GUIDE_DRIFT_POSITIVE_CASES = [
    str(case["situation"]) for case in GUIDE_DRIFT_CASE_CORPUS if case.get("expected") == "trigger"
]

GUIDE_DRIFT_NEGATIVE_CASES = [
    str(case["situation"]) for case in GUIDE_DRIFT_CASE_CORPUS if case.get("expected") == "suppress"
]

ARBOR_HOOKS: list[dict[str, Any]] = [
    {
        "id": "arbor.session_startup_context",
        "owner": "arbor",
        "event": "session.start",
        "description": "Load project startup context in Arbor order.",
        "entrypoint": {
            "type": "skill-script",
            "skill": "arbor",
            "script": "scripts/run_session_startup_hook.py",
            "args": ["--root", "${PROJECT_ROOT}"],
            "optional_args": [
                {
                    "name": "--git-log-args",
                    "placeholder": "${GIT_LOG_ARGS}",
                    "description": "Agent-selected git log arguments forwarded to the startup collector.",
                }
            ],
        },
        "order": [
            str(PROJECT_GUIDE_PATH),
            "formatted git log",
            str(CANONICAL_MEMORY_PATH),
            "git status",
        ],
        "depth_policy": "agent-selected; no fixed read limits",
    },
    {
        "id": "arbor.in_session_memory_hygiene",
        "owner": "arbor",
        "event": "conversation.checkpoint",
        "description": "Refresh project-local short-term memory when uncommitted work or conversation state makes it stale.",
        "entrypoint": {
            "type": "skill-script",
            "skill": "arbor",
            "script": "scripts/run_memory_hygiene_hook.py",
            "args": ["--root", "${PROJECT_ROOT}"],
            "optional_args": [
                {
                    "name": "--diff-args",
                    "placeholder": "${DIFF_ARGS}",
                    "description": "Agent-selected git diff arguments included in the memory hygiene packet.",
                }
            ],
        },
        "reads": [
            str(CANONICAL_MEMORY_PATH),
            "git status --short",
            "selected diffs when the agent decides they are needed",
            "recent conversation context available to the running agent",
        ],
        "writes": [str(CANONICAL_MEMORY_PATH)],
        "trigger_policy": {
            "mode": "high_recall_when_dirty_or_handoff",
            "positive_cases": MEMORY_HYGIENE_POSITIVE_CASES,
            "negative_cases": MEMORY_HYGIENE_NEGATIVE_CASES,
            "case_corpus": MEMORY_HYGIENE_CASE_CORPUS,
            "decision_rule": (
                "Trigger when Arbor-managed work may leave unresolved state before a stop, "
                "handoff, release gate, commit, or session boundary; suppress only when the "
                "worktree is clean or the request is direct/read-only with no unresolved Arbor state."
            ),
        },
        "depth_policy": "agent-selected; no fixed read limits",
    },
    {
        "id": "arbor.goal_constraint_drift",
        "owner": "arbor",
        "event": "project.guide_drift",
        "description": "Update the stable project guide or map when goals, constraints, or map pointers change.",
        "entrypoint": {
            "type": "skill-script",
            "skill": "arbor",
            "script": "scripts/run_agents_guide_drift_hook.py",
            "args": ["--root", "${PROJECT_ROOT}"],
            "optional_args": [
                {
                    "name": "--doc",
                    "placeholder": "${DOC_PATH}",
                    "repeatable": True,
                    "description": "Agent-selected project-local doc included in the AGENTS guide drift packet.",
                }
            ],
        },
        "reads": [
            str(PROJECT_GUIDE_PATH),
            "top-level project structure",
            "git status --short --untracked-files=all",
            "project docs selected by the agent",
        ],
        "writes": [str(PROJECT_GUIDE_PATH)],
        "allowed_sections": ["Project Goal", "Project Constraints", "Project Map"],
        "trigger_policy": {
            "mode": "high_recall_for_durable_guide_or_project_map_drift",
            "positive_cases": GUIDE_DRIFT_POSITIVE_CASES,
            "negative_cases": GUIDE_DRIFT_NEGATIVE_CASES,
            "case_corpus": GUIDE_DRIFT_CASE_CORPUS,
            "decision_rule": (
                "Trigger when durable project goals, constraints, or project-map entrypoints may have changed. "
                "If the drift packet reports Project Map Drift Candidates as update-needed, update AGENTS.md "
                "Project Map before handoff or release unless the missing or stale candidate is intentionally excluded."
            ),
        },
        "depth_policy": "agent-selected; no fixed read limits",
    },
]

ARBOR_HOOK_IDS = {hook["id"] for hook in ARBOR_HOOKS}


@dataclass(frozen=True)
class HookRegistrationAction:
    path: Path
    status: str
    detail: str = ""


class HookRegistrationError(ValueError):
    """Raised when Arbor hooks cannot be registered cleanly."""


def hook_config_path(root: Path) -> Path:
    try:
        return project_path(resolve_project_root(root), CODEX_HOOK_CONFIG_PATH)
    except ValueError as exc:
        raise HookRegistrationError(str(exc)) from exc


def load_hook_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": HOOK_CONFIG_VERSION, "hooks": []}
    if not path.is_file():
        raise HookRegistrationError(f"cannot register hooks at {path}: expected a file but found a directory")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except JSONDecodeError as exc:
        raise HookRegistrationError(f"cannot parse {path}: {exc}") from exc
    except OSError as exc:
        raise HookRegistrationError(f"cannot read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise HookRegistrationError(f"cannot register hooks at {path}: expected a JSON object")
    hooks = data.get("hooks", [])
    if not isinstance(hooks, list):
        raise HookRegistrationError(f"cannot register hooks at {path}: expected 'hooks' to be a list")
    return data


def merge_arbor_hooks(config: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(config)
    merged.setdefault("version", HOOK_CONFIG_VERSION)
    existing_hooks = merged.get("hooks", [])
    preserved_hooks = [
        hook
        for hook in existing_hooks
        if not (isinstance(hook, dict) and hook.get("owner") == "arbor" and hook.get("id") in ARBOR_HOOK_IDS)
    ]
    merged["hooks"] = [*preserved_hooks, *deepcopy(ARBOR_HOOKS)]
    return merged


def render_hook_config(config: dict[str, Any]) -> str:
    return json.dumps(config, indent=2, sort_keys=False) + "\n"


def register_project_hooks(root: Path, dry_run: bool = False) -> list[HookRegistrationAction]:
    root = root.resolve()
    path = hook_config_path(root)
    if path.parent.exists() and not path.parent.is_dir():
        raise HookRegistrationError(f"cannot register hooks at {path}: parent path is not a directory")

    existed = path.exists()
    config = load_hook_config(path)
    merged = merge_arbor_hooks(config)
    before = render_hook_config(config)
    after = render_hook_config(merged)

    if before == after:
        return [HookRegistrationAction(path=path, status="exists", detail="Arbor hooks already registered")]

    if not dry_run:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(after, encoding="utf-8")
        except OSError as exc:
            raise HookRegistrationError(f"cannot write {path}: {exc}") from exc

    if not existed:
        status = "would_create" if dry_run else "created"
    else:
        status = "would_update" if dry_run else "updated"
    return [HookRegistrationAction(path=path, status=status, detail="registered 3 Arbor hook intents")]


def render_actions(actions: Iterable[HookRegistrationAction]) -> str:
    lines = ["# Arbor Hook Registration", ""]
    for action in actions:
        suffix = f" ({action.detail})" if action.detail else ""
        lines.append(f"- {action.status}: {action.path}{suffix}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root to update.")
    parser.add_argument("--dry-run", action="store_true", help="Report hook registration without writing files.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        actions = register_project_hooks(args.root, dry_run=args.dry_run)
    except HookRegistrationError as exc:
        parser.error(str(exc))
    print(render_actions(actions))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
