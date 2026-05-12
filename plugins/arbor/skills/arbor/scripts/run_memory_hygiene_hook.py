#!/usr/bin/env python3
"""Run the Arbor in-session memory hygiene hook for one project."""

from __future__ import annotations

import argparse
import shlex
from pathlib import Path

from arbor_project_state import (
    CANONICAL_MEMORY_PATH,
    LEGACY_CODEX_MEMORY_PATH,
    ProjectStateError,
    resolve_project_root,
)
from collect_project_context import ContextSection, read_memory_section, run_git_section


DISALLOWED_DIFF_ARGS = {"--output", "-o", "--ext-diff", "--no-index"}
DISALLOWED_DIFF_ARG_PREFIXES = ("--output=",)


def parse_optional_git_args(raw: str | list[str] | None) -> list[str] | None:
    if raw is None:
        return None
    if isinstance(raw, list):
        if not raw:
            return None
        raw = " ".join(raw)
    try:
        args = shlex.split(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid git args: {exc}") from exc
    validate_diff_args(args)
    return args


def validate_diff_args(args: list[str], root: Path | None = None) -> None:
    resolved_root = root.resolve() if root is not None else None
    for arg in args:
        if arg in DISALLOWED_DIFF_ARGS or arg.startswith(DISALLOWED_DIFF_ARG_PREFIXES):
            raise argparse.ArgumentTypeError(f"unsafe git diff argument is not allowed: {arg}")
        if resolved_root is not None:
            path = Path(arg)
            if path.is_absolute():
                resolved_path = path.resolve()
                if resolved_path != resolved_root and resolved_root not in resolved_path.parents:
                    raise argparse.ArgumentTypeError(f"diff path is outside project root: {arg}")


def collect_memory_hygiene_context(root: Path, diff_args: list[str] | None = None) -> list[ContextSection]:
    resolved = resolve_project_root(root)
    sections = [
        read_memory_section("1. .arbor/memory.md", resolved),
        run_git_section("2. git status", resolved, ["status", "--short"]),
        run_git_section("3. git diff --stat", resolved, ["diff", "--stat"]),
        run_git_section("4. git diff --cached --stat", resolved, ["diff", "--cached", "--stat"]),
    ]
    if diff_args is not None:
        validate_diff_args(diff_args, resolved)
        sections.append(run_git_section("5. selected git diff", resolved, ["diff", *diff_args]))
    return sections


def render_memory_hygiene_packet(sections: list[ContextSection]) -> str:
    lines = [
        "# Memory Hygiene Context",
        "",
        "## Agent Instructions",
        "",
        "- Decide whether `.arbor/memory.md` is stale using this packet plus current conversation context.",
        "- If an update is needed, edit only the project-local `.arbor/memory.md`.",
        "- Keep only short-term, undecided pre-triage observations about uncommitted work.",
        "- Remove resolved, committed, or durable items that belong in docs, review files, or `AGENTS.md`.",
        "- Do not update `AGENTS.md` from this hook.",
        f"- If only legacy `{LEGACY_CODEX_MEMORY_PATH}` exists, run explicit Arbor initialization/migration before editing.",
        f"- Do not merge legacy `{LEGACY_CODEX_MEMORY_PATH}` into `{CANONICAL_MEMORY_PATH}` from this hook.",
        "",
    ]
    for section in sections:
        lines.append(f"## {section.title}")
        lines.append("")
        lines.append(f"Status: {section.status}")
        lines.append(f"Source: {section.source}")
        if section.detail:
            lines.append(f"Detail: {section.detail}")
        lines.append("")
        lines.append(section.body)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def run_memory_hygiene_hook(root: Path, diff_args: list[str] | None = None) -> str:
    return render_memory_hygiene_packet(collect_memory_hygiene_context(root, diff_args))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root to inspect.")
    parser.add_argument(
        "--diff-args",
        help=(
            "Optional git diff arguments selected by the agent. "
            "When omitted, the hook emits memory, git status, and diff stat only."
        ),
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        diff_args = parse_optional_git_args(args.diff_args)
        output = run_memory_hygiene_hook(args.root, diff_args)
    except (argparse.ArgumentTypeError, ProjectStateError) as exc:
        parser.error(str(exc))
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
