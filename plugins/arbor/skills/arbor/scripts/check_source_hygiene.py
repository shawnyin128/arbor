#!/usr/bin/env python3
"""Validate text hygiene for Arbor published source files, including untracked files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


sys.dont_write_bytecode = True

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = PLUGIN_ROOT.parents[1]

DEFAULT_ROOTS = [
    REPO_ROOT / "README.md",
    REPO_ROOT / ".agents" / "plugins" / "marketplace.json",
    REPO_ROOT / ".claude-plugin" / "marketplace.json",
    PLUGIN_ROOT,
]

TEXT_SUFFIXES = {
    "",
    ".json",
    ".md",
    ".py",
    ".txt",
    ".yaml",
    ".yml",
}
BINARY_SUFFIXES = {
    ".gif",
    ".ico",
    ".jpg",
    ".jpeg",
    ".pdf",
    ".png",
    ".webp",
}
TRANSIENT_DIR_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache"}
TRANSIENT_SUFFIXES = {".pyc", ".pyo"}
CONFLICT_MARKERS = ("<<<<<<< ", "=======", ">>>>>>> ")


def is_transient(path: Path) -> bool:
    return path.name in TRANSIENT_DIR_NAMES or path.suffix in TRANSIENT_SUFFIXES


def should_skip(path: Path) -> bool:
    if any(part in TRANSIENT_DIR_NAMES for part in path.parts):
        return True
    if is_transient(path):
        return True
    return path.suffix.lower() in BINARY_SUFFIXES


def candidate_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    if not root.exists():
        return []
    return [path for path in sorted(root.rglob("*")) if path.is_file()]


def is_text_candidate(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES


def validate_file(path: Path) -> list[str]:
    failures: list[str] = []
    if should_skip(path):
        return failures
    if not is_text_candidate(path):
        return failures
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        failures.append(f"{path}: published text file must be UTF-8: {exc}")
        return failures
    except OSError as exc:
        failures.append(f"{path}: could not read published text file: {exc}")
        return failures

    if content and not content.endswith("\n"):
        failures.append(f"{path}: missing final newline")

    for line_number, line in enumerate(content.splitlines(), start=1):
        if line.rstrip(" \t") != line:
            failures.append(f"{path}:{line_number}: trailing whitespace")
        stripped = line.strip()
        if any(stripped.startswith(marker) for marker in CONFLICT_MARKERS):
            failures.append(f"{path}:{line_number}: conflict marker")
    return failures


def validate_roots(roots: list[Path]) -> list[str]:
    failures: list[str] = []
    for root in roots:
        if not root.exists():
            failures.append(f"missing published source root: {root}")
            continue
        for path in candidate_files(root):
            failures.extend(validate_file(path))
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("roots", nargs="*", type=Path, default=DEFAULT_ROOTS)
    args = parser.parse_args(argv)

    failures = validate_roots([root.resolve() for root in args.roots])
    if failures:
        print("source hygiene check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("source hygiene check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
