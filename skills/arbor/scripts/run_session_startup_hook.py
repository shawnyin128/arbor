#!/usr/bin/env python3
"""Run the Arbor session startup hook for one project."""

from __future__ import annotations

import argparse
from pathlib import Path

from collect_project_context import collect_startup_context, parse_git_log_args, render_context


class SessionStartupHookError(ValueError):
    """Raised when the startup hook cannot resolve its project root."""


def resolve_project_root(root: Path) -> Path:
    resolved = root.resolve()
    if not resolved.exists():
        raise SessionStartupHookError(f"project root does not exist: {resolved}")
    if not resolved.is_dir():
        raise SessionStartupHookError(f"project root is not a directory: {resolved}")
    return resolved


def run_session_startup_hook(root: Path, git_log_args: list[str] | None = None) -> str:
    resolved = resolve_project_root(root)
    sections = collect_startup_context(resolved, git_log_args)
    return render_context(sections)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root to inspect.")
    parser.add_argument(
        "--git-log-args",
        help=(
            "Optional git log arguments selected by the agent. "
            "Forwarded to the startup collector without becoming a fixed default."
        ),
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        git_log_args = parse_git_log_args(args.git_log_args)
        output = run_session_startup_hook(args.root, git_log_args)
    except (argparse.ArgumentTypeError, SessionStartupHookError) as exc:
        parser.error(str(exc))
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
