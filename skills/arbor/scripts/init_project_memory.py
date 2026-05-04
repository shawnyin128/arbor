#!/usr/bin/env python3
"""Initialize project-local Arbor memory files."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from arbor_project_state import (
    PROJECT_GUIDE_PATH,
    ProjectFileAction,
    ProjectStateError,
    ensure_file,
    ensure_memory_file,
    project_path,
    resolve_project_root,
)

SKILL_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = SKILL_ROOT / "references"


def read_template(name: str) -> str:
    return (REFERENCE_DIR / name).read_text(encoding="utf-8")


def init_project_memory(root: Path, dry_run: bool = False) -> list[ProjectFileAction]:
    root = resolve_project_root(root)
    return [
        *ensure_memory_file(root, read_template("memory-template.md"), dry_run),
        ensure_file(project_path(root, PROJECT_GUIDE_PATH), read_template("agents-template.md"), dry_run),
    ]


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
    return parser


def parse_args() -> argparse.Namespace:
    return build_parser().parse_args()


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        actions = init_project_memory(args.root, dry_run=args.dry_run)
    except ProjectStateError as exc:
        parser.error(str(exc))
    print(render_actions(actions))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
