#!/usr/bin/env python3
"""Run the Arbor AGENTS guide drift hook for one project."""

from __future__ import annotations

import argparse
import shlex
import subprocess
from pathlib import Path

from arbor_project_state import (
    CANONICAL_MEMORY_PATH,
    PROJECT_GUIDE_PATH,
    ProjectStateError,
    resolve_project_root,
)
from collect_project_context import ContextSection, read_file_section, run_git_section


ALLOWED_AGENTS_SECTIONS = ["Project Goal", "Project Constraints", "Project Map"]
PROJECT_MAP_HEADING = "Project Map"
MAX_PROJECT_MAP_CANDIDATES = 60
SKIP_PROJECT_MAP_NAMES = {
    ".DS_Store",
    ".claude",
    ".git",
    ".gitignore",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "LICENSE",
    "__pycache__",
}
INCLUDE_PROJECT_MAP_FILES = {"CLAUDE.md", "Makefile", "README.md", "package.json", "pyproject.toml"}


class AgentsGuideDriftHookError(ValueError):
    """Raised when the AGENTS guide drift hook cannot resolve project-local inputs."""


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


def run_git(root: Path, args: list[str]) -> tuple[str, str, int]:
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return proc.stdout.rstrip("\n"), proc.stderr.rstrip("\n"), proc.returncode


def project_map_candidates(root: Path) -> list[str]:
    names: list[str] = []
    for child in sorted(root.iterdir(), key=lambda item: item.name.lower()):
        if child.name in SKIP_PROJECT_MAP_NAMES:
            continue
        if child.name == "AGENTS.md":
            continue
        if child.is_dir():
            names.append(f"{child.name}/")
        elif child.is_file() and child.name in INCLUDE_PROJECT_MAP_FILES:
            names.append(child.name)
    return names[:MAX_PROJECT_MAP_CANDIDATES]


def extract_agents_section(text: str, heading: str) -> str:
    marker = f"## {heading}"
    start = text.find(marker)
    if start == -1:
        return ""
    body_start = text.find("\n", start)
    if body_start == -1:
        return ""
    next_heading = text.find("\n## ", body_start + 1)
    if next_heading == -1:
        return text[body_start + 1 :]
    return text[body_start + 1 : next_heading]


def read_agents_text(root: Path) -> str:
    path = root / PROJECT_GUIDE_PATH
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def missing_project_map_candidates(root: Path) -> list[str]:
    project_map = extract_agents_section(read_agents_text(root), PROJECT_MAP_HEADING)
    missing: list[str] = []
    for candidate in project_map_candidates(root):
        token = candidate.rstrip("/")
        if candidate not in project_map and token not in project_map:
            missing.append(candidate)
    return missing


def collect_project_map_snapshot(root: Path) -> ContextSection:
    candidates = project_map_candidates(root)
    status_output, status_error, status_code = run_git(root, ["status", "--short", "--untracked-files=all"])
    lines = ["Top-level project map candidates:"]
    lines.extend(f"- `{candidate}`" for candidate in candidates)
    lines.append("")
    lines.append("Git status paths:")
    if status_code == 0:
        lines.append(status_output or "(clean)")
        status = "ok"
        detail = ""
    else:
        lines.append(status_error or status_output or "(git status unavailable)")
        status = "git-error"
        detail = f"exit {status_code}"
    return ContextSection(
        title="3. Project Map Snapshot",
        body="\n".join(lines),
        status=status,
        source="filesystem top-level entries and git status --short --untracked-files=all",
        detail=detail,
    )


def collect_project_map_drift(root: Path) -> ContextSection:
    missing = missing_project_map_candidates(root)
    if missing:
        body = "\n".join(
            [
                "The current `AGENTS.md` Project Map does not mention these top-level candidates:",
                "",
                *[f"- `{candidate}`" for candidate in missing],
                "",
                "Update `AGENTS.md` Project Map before handoff or release unless a candidate is intentionally out of scope.",
            ]
        )
        return ContextSection(
            title="4. Project Map Drift Candidates",
            body=body,
            status="update-needed",
            source="AGENTS.md Project Map compared with top-level project entries",
        )
    return ContextSection(
        title="4. Project Map Drift Candidates",
        body="No missing top-level project map candidates detected.",
        status="ok",
        source="AGENTS.md Project Map compared with top-level project entries",
    )


def collect_agents_guide_drift_context(root: Path, doc_paths: list[Path] | None = None) -> list[ContextSection]:
    resolved = resolve_project_root(root)
    sections = [
        read_file_section("1. AGENTS.md", resolved / PROJECT_GUIDE_PATH),
        run_git_section("2. git status", resolved, ["status", "--short"]),
        collect_project_map_snapshot(resolved),
        collect_project_map_drift(resolved),
    ]
    for index, doc_path in enumerate(doc_paths or [], start=5):
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
        "- When `Project Map Drift Candidates` reports `update-needed`, update `AGENTS.md` Project Map before handoff or release unless the listed paths are intentionally excluded.",
        f"- If an update is needed, edit only these sections: {allowed}.",
        "- Keep current uncommitted progress, transient observations, and implementation notes out of `AGENTS.md`.",
        f"- Put short-term undecided work in `{CANONICAL_MEMORY_PATH}`; put feature/review evidence in review docs.",
        f"- Do not update `{CANONICAL_MEMORY_PATH}` from this hook.",
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
    except (argparse.ArgumentTypeError, AgentsGuideDriftHookError, ProjectStateError) as exc:
        parser.error(str(exc))
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
