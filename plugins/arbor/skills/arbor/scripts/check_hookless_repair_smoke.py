#!/usr/bin/env python3
"""Smoke default Arbor repair in a fresh project without creating hook state."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


sys.dont_write_bytecode = True

SCRIPT_ROOT = Path(__file__).resolve().parent
PLUGIN_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TIMEOUT_SECONDS = 30.0
TIMEOUT_ENV_VAR = "ARBOR_HOOKLESS_REPAIR_SMOKE_TIMEOUT_SECONDS"


def timeout_seconds() -> float:
    raw = os.environ.get(TIMEOUT_ENV_VAR)
    if not raw:
        return DEFAULT_TIMEOUT_SECONDS
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS
    return value if value > 0 else DEFAULT_TIMEOUT_SECONDS


def subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def run_framework_repair(project: Path, plugin_root: Path) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_ROOT / "run_framework_check.py"),
                "--root",
                str(project),
                "--plugin-root",
                str(plugin_root),
                "--runtime",
                "both",
                "--mode",
                "repair",
                "--strict",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=subprocess_env(),
            check=False,
            timeout=timeout_seconds(),
        )
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout if isinstance(exc.stdout, str) else ""
        return 124, f"framework repair timed out after {timeout_seconds():g}s\n{output.strip()}"
    except OSError as exc:
        return 127, f"framework repair failed to start: {exc}"
    return proc.returncode, proc.stdout


def hook_surfaces(project: Path) -> list[Path]:
    return [
        project / ".codex",
        project / ".claude",
        project / ".codex" / "hooks.json",
        project / ".codex" / "hooks",
        project / ".claude" / "settings.json",
        project / ".claude" / "hooks",
    ]


def smoke_hookless_repair(plugin_root: Path) -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="arbor-hookless-repair-smoke-") as tmp:
        project = Path(tmp) / "project"
        project.mkdir()
        code, output = run_framework_repair(project, plugin_root)
        if code != 0:
            failures.append(f"run_framework_check.py default repair failed with exit {code}:\n{output.strip()}")
            return failures

        expected_files = [
            project / "AGENTS.md",
            project / ".arbor" / "memory.md",
            project / "CLAUDE.md",
        ]
        for path in expected_files:
            if not path.is_file():
                failures.append(f"default repair did not create expected file: {path.relative_to(project)}")
        for path in hook_surfaces(project):
            if path.exists():
                failures.append(f"default repair created hook surface unexpectedly: {path.relative_to(project)}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugin-root", type=Path, default=PLUGIN_ROOT, help="Arbor plugin root to smoke.")
    args = parser.parse_args()

    failures = smoke_hookless_repair(args.plugin_root.resolve())
    if failures:
        print("hookless repair smoke failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("hookless repair smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
