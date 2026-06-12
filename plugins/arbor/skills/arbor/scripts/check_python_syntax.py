#!/usr/bin/env python3
"""Validate Arbor Python sources without writing bytecode artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


sys.dont_write_bytecode = True

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = PLUGIN_ROOT / "skills" / "arbor" / "scripts"
HOOKS_ROOT = PLUGIN_ROOT / "hooks"
TRANSIENT_DIR_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache"}
TRANSIENT_SUFFIXES = {".pyc", ".pyo"}


def is_transient(path: Path) -> bool:
    return path.name in TRANSIENT_DIR_NAMES or path.suffix in TRANSIENT_SUFFIXES


def should_compile(path: Path) -> bool:
    if not path.is_file() or is_transient(path):
        return False
    if path.suffix == ".py":
        return True
    try:
        first_line = path.read_text(encoding="utf-8").splitlines()[0]
    except IndexError:
        return False
    except UnicodeDecodeError:
        return True
    except OSError:
        return True
    return "python" in first_line.lower()


def validate_roots(roots: list[Path]) -> list[str]:
    failures: list[str] = []
    for root in roots:
        if not root.exists():
            failures.append(f"missing validation root: {root}")
            continue
        for path in sorted(root.rglob("*")):
            if is_transient(path):
                failures.append(f"transient artifact must not be present: {path}")
                continue
            if not should_compile(path):
                continue
            try:
                source = path.read_text(encoding="utf-8")
                compile(source, str(path), "exec")
            except SyntaxError as exc:
                failures.append(f"syntax error in {path}: {exc}")
            except UnicodeDecodeError as exc:
                failures.append(f"could not decode Python source {path}: {exc}")
            except OSError as exc:
                failures.append(f"could not read Python source {path}: {exc}")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("roots", nargs="*", type=Path, default=[SCRIPTS_ROOT, HOOKS_ROOT])
    args = parser.parse_args(argv)

    failures = validate_roots([root.resolve() for root in args.roots])
    if failures:
        print("Python syntax check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("Python syntax check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
