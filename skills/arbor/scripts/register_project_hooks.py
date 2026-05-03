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


HOOK_CONFIG_RELATIVE_PATH = Path(".codex") / "hooks.json"
HOOK_CONFIG_VERSION = 1

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
            "AGENTS.md",
            "formatted git log",
            ".codex/memory.md",
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
            ".codex/memory.md",
            "git status --short",
            "selected diffs when the agent decides they are needed",
            "recent conversation context available to the running agent",
        ],
        "writes": [".codex/memory.md"],
        "depth_policy": "agent-selected; no fixed read limits",
    },
    {
        "id": "arbor.goal_constraint_drift",
        "owner": "arbor",
        "event": "project.guide_drift",
        "description": "Update durable project goal, constraints, or map when they change.",
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
        "reads": ["AGENTS.md", "project docs selected by the agent"],
        "writes": ["AGENTS.md"],
        "allowed_sections": ["Project Goal", "Project Constraints", "Project Map"],
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


def ensure_under_root(root: Path, path: Path) -> None:
    if path != root and root not in path.parents:
        raise HookRegistrationError(f"refusing to write outside project root: {path}")


def hook_config_path(root: Path) -> Path:
    root = root.resolve()
    if not root.exists():
        raise HookRegistrationError(f"project root does not exist: {root}")
    if not root.is_dir():
        raise HookRegistrationError(f"project root is not a directory: {root}")
    path = (root / HOOK_CONFIG_RELATIVE_PATH).resolve()
    ensure_under_root(root, path)
    return path


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
