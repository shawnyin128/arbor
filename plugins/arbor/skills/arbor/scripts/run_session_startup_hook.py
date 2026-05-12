#!/usr/bin/env python3
"""Run the Arbor session startup hook for one project."""

from __future__ import annotations

import argparse
from pathlib import Path

from arbor_project_state import ProjectStateError, resolve_project_root
from collect_project_context import collect_startup_context, parse_git_log_args, render_context


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
    except (argparse.ArgumentTypeError, ProjectStateError) as exc:
        parser.error(str(exc))
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
