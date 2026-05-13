#!/usr/bin/env python3
"""Validate Arbor skill packages without relying on shell PATH."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SKILLS_ROOT = PLUGIN_ROOT / "skills"


def quick_validate_candidates() -> list[Path]:
    candidates: list[Path] = []
    if env_path := os.environ.get("QUICK_VALIDATE"):
        candidates.append(Path(env_path).expanduser())
    if path_entry := shutil.which("quick_validate.py"):
        candidates.append(Path(path_entry))
    candidates.extend(
        [
            Path.home() / ".codex/skills/.system/skill-creator/scripts/quick_validate.py",
            Path.home()
            / ".claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator/skills/skill-creator/scripts/quick_validate.py",
        ]
    )
    return candidates


def find_quick_validate() -> Path:
    for candidate in quick_validate_candidates():
        if candidate.is_file():
            return candidate
    searched = "\n".join(f"- {candidate}" for candidate in quick_validate_candidates())
    raise SystemExit(f"could not find quick_validate.py; searched:\n{searched}")


def default_skill_dirs(skills_root: Path) -> list[Path]:
    if not skills_root.is_dir():
        raise SystemExit(f"skills root not found: {skills_root}")
    return sorted(path for path in skills_root.iterdir() if (path / "SKILL.md").is_file())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skills", nargs="*", type=Path, help="Skill directories to validate. Defaults to all Arbor skills.")
    parser.add_argument("--skills-root", type=Path, default=DEFAULT_SKILLS_ROOT, help="Root containing Arbor skill directories.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    validator = find_quick_validate()
    skill_dirs = args.skills or default_skill_dirs(args.skills_root)

    failures: list[str] = []
    for skill_dir in skill_dirs:
        proc = subprocess.run(
            [sys.executable, str(validator), str(skill_dir)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            failures.append(f"{skill_dir}: {proc.stderr.strip() or proc.stdout.strip()}")

    if failures:
        print("skill package validation failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print(f"skill package checks passed count={len(skill_dirs)} validator={validator}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
