#!/usr/bin/env python3
"""Run the Arbor AGENTS guide drift hook for one project."""

from __future__ import annotations

import argparse
import shlex
from pathlib import Path

from collect_project_context import ContextSection, read_file_section, run_git_section


ALLOWED_AGENTS_SECTIONS = ["Project Goal", "Project Constraints", "Project Map"]


class AgentsGuideDriftHookError(ValueError):
    """Raised when the AGENTS guide drift hook cannot resolve project-local inputs."""


def resolve_project_root(root: Path) -> Path:
    resolved = root.resolve()
    if not resolved.exists():
        raise AgentsGuideDriftHookError(f"project root does not exist: {resolved}")
    if not resolved.is_dir():
        raise AgentsGuideDriftHookError(f"project root is not a directory: {resolved}")
    return resolved


def ensure_under_root(root: Path, path: Path) -> None:
    if path != root and root not in path.parents:
        raise AgentsGuideDriftHookError(f"doc path is outside project root: {path}")


def parse_doc_paths(raw_items: list[str] | None, legacy_raw: str | None = None) -> list[Path]:
    paths = [Path(item) for item in raw_items or []]
    if legacy_raw:
        try:
            paths.extend(Path(item) for item in shlex.split(legacy_raw))
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"invalid doc paths: {exc}") from exc
    return paths


def resolve_doc_path(root: Path, doc_path: Path) -> Path:
    candidate = doc_path if doc_path.is_absolute() else root / doc_path
    resolved = candidate.resolve()
    ensure_under_root(root, resolved)
    return resolved


def collect_agents_guide_drift_context(root: Path, doc_paths: list[Path] | None = None) -> list[ContextSection]:
    resolved = resolve_project_root(root)
    sections = [
        read_file_section("1. AGENTS.md", resolved / "AGENTS.md"),
        run_git_section("2. git status", resolved, ["status", "--short"]),
    ]
    for index, doc_path in enumerate(doc_paths or [], start=3):
        resolved_doc = resolve_doc_path(resolved, doc_path)
        sections.append(read_file_section(f"{index}. selected project doc: {doc_path}", resolved_doc))
    return sections


def render_agents_guide_drift_packet(sections: list[ContextSection]) -> str:
    allowed = ", ".join(ALLOWED_AGENTS_SECTIONS)
    lines = [
        "# AGENTS Guide Drift Context",
        "",
        "## Agent Instructions",
        "",
        "- Decide whether `AGENTS.md` needs a durable update using this packet plus current conversation context.",
        f"- If an update is needed, edit only these sections: {allowed}.",
        "- Keep current uncommitted progress, transient observations, and implementation notes out of `AGENTS.md`.",
        "- Put short-term undecided work in `.codex/memory.md`; put feature/review evidence in review docs.",
        "- Do not update `.codex/memory.md` from this hook.",
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


def run_agents_guide_drift_hook(root: Path, doc_paths: list[Path] | None = None) -> str:
    return render_agents_guide_drift_packet(collect_agents_guide_drift_context(root, doc_paths))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root to inspect.")
    parser.add_argument(
        "--doc",
        action="append",
        help=(
            "Optional project-local doc selected by the agent. Repeat this flag to include multiple docs. "
            "Absolute paths must stay under the project root."
        ),
    )
    parser.add_argument(
        "--doc-paths",
        help=argparse.SUPPRESS,
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        doc_paths = parse_doc_paths(args.doc, args.doc_paths)
        output = run_agents_guide_drift_hook(args.root, doc_paths)
    except (argparse.ArgumentTypeError, AgentsGuideDriftHookError) as exc:
        parser.error(str(exc))
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
