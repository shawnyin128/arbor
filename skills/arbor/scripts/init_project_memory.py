#!/usr/bin/env python3
"""Initialize project-local Arbor memory files."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from arbor_project_state import (
    INSTALL_RUNTIME_CLAUDE,
    PROJECT_GUIDE_PATH,
    ProjectFileAction,
    ProjectStateError,
    detect_install_runtime,
    ensure_claude_bridge,
    ensure_file,
    ensure_memory_file,
    project_path,
    resolve_project_root,
)

SKILL_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = SKILL_ROOT / "references"

CLAUDE_BRIDGE_AUTO = "auto"
CLAUDE_BRIDGE_ON = "on"
CLAUDE_BRIDGE_OFF = "off"
CLAUDE_BRIDGE_CHOICES = (CLAUDE_BRIDGE_AUTO, CLAUDE_BRIDGE_ON, CLAUDE_BRIDGE_OFF)


def read_template(name: str) -> str:
    return (REFERENCE_DIR / name).read_text(encoding="utf-8")


def resolve_claude_bridge(mode: str) -> bool:
    if mode == CLAUDE_BRIDGE_ON:
        return True
    if mode == CLAUDE_BRIDGE_OFF:
        return False
    if mode == CLAUDE_BRIDGE_AUTO:
        return detect_install_runtime() == INSTALL_RUNTIME_CLAUDE
    raise ProjectStateError(f"unknown --claude-bridge mode: {mode}")


def init_project_memory(
    root: Path,
    dry_run: bool = False,
    claude_bridge: str = CLAUDE_BRIDGE_AUTO,
) -> list[ProjectFileAction]:
    root = resolve_project_root(root)
    actions: list[ProjectFileAction] = [
        *ensure_memory_file(root, read_template("memory-template.md"), dry_run),
        ensure_file(project_path(root, PROJECT_GUIDE_PATH), read_template("agents-template.md"), dry_run),
    ]
    if resolve_claude_bridge(claude_bridge):
        actions.append(ensure_claude_bridge(root, read_template("claude-template.md"), dry_run))
    return actions


def render_actions(actions: Iterable[ProjectFileAction]) -> str:
    lines = ["# Arbor Initialization", ""]
    for action in actions:
        suffix = f" ({action.detail})" if action.detail else ""
        lines.append(f"- {action.status}: {action.path}{suffix}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root to initialize.")
    parser.add_argument("--dry-run", action="store_true", help="Report files that would be created.")
    parser.add_argument(
        "--claude-bridge",
        choices=CLAUDE_BRIDGE_CHOICES,
        default=CLAUDE_BRIDGE_AUTO,
        help=(
            "Whether to create a Claude-native CLAUDE.md bridge. "
            "auto (default): create only when this script lives in a Claude Code plugin cache. "
            "on: always create when missing. off: never create."
        ),
    )
    return parser


def parse_args() -> argparse.Namespace:
    return build_parser().parse_args()


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        actions = init_project_memory(
            args.root,
            dry_run=args.dry_run,
            claude_bridge=args.claude_bridge,
        )
    except ProjectStateError as exc:
        parser.error(str(exc))
    print(render_actions(actions))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
