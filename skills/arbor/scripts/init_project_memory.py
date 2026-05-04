#!/usr/bin/env python3
"""Initialize project-local Codex memory files."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


SKILL_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = SKILL_ROOT / "references"


@dataclass(frozen=True)
class InitAction:
    path: Path
    status: str


class InitError(ValueError):
    """Raised when project memory files cannot be initialized cleanly."""


def read_template(name: str) -> str:
    return (REFERENCE_DIR / name).read_text(encoding="utf-8")


def ensure_file(path: Path, content: str, dry_run: bool) -> InitAction:
    if path.exists():
        if not path.is_file():
            raise InitError(f"cannot initialize {path}: expected a file but found a directory")
        return InitAction(path=path, status="exists")
    if path.parent.exists() and not path.parent.is_dir():
        raise InitError(f"cannot initialize {path}: parent path is not a directory")
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return InitAction(path=path, status="would_create" if dry_run else "created")


def init_project_memory(root: Path, dry_run: bool = False) -> list[InitAction]:
    root = root.resolve()
    return [
        ensure_file(root / ".codex" / "memory.md", read_template("memory-template.md"), dry_run),
        ensure_file(root / "AGENTS.md", read_template("agents-template.md"), dry_run),
    ]


def render_actions(actions: Iterable[InitAction]) -> str:
    lines = ["# Arbor Initialization", ""]
    for action in actions:
        lines.append(f"- {action.status}: {action.path}")
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
    except InitError as exc:
        parser.error(str(exc))
    print(render_actions(actions))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
