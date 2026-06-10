#!/usr/bin/env python3
"""Validate Arbor AGENTS.md guide shape and Project Map usefulness."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from arbor_project_state import PROJECT_GUIDE_PATH, ProjectStateError, resolve_project_root
from run_agents_guide_drift_hook import project_map_token_exists, project_map_tokens, stale_project_map_entries


REQUIRED_TOP_LEVEL_SECTIONS = (
    "Startup Protocol",
    "Workflow Entrypoint Protocol",
    "Project Goal",
    "Project Constraints",
    "Project Map",
)
ALLOWED_TOP_LEVEL_SECTIONS = set(REQUIRED_TOP_LEVEL_SECTIONS)
TEMPLATE_PLACEHOLDER_TERMS = (
    "has not recorded a durable project map",
    "has not recorded a stable project goal",
    "inspect the repository itself before answering",
)
TRANSIENT_TERMS = (
    "in-flight",
    "work in progress",
    "review round",
    "developer round",
    "evaluator round",
    "convergence round",
    "release round",
)
SKIP_PROJECT_MAP_NAMES = {
    ".DS_Store",
    ".arbor",
    ".agents",
    ".claude",
    ".claude-plugin",
    ".codex",
    ".codex-plugin",
    ".git",
    ".gitignore",
    ".meridian",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "AGENTS.md",
    "CLAUDE.md",
    "LICENSE",
    "artifacts",
    "build",
    "dist",
    "fixture",
    "fixtures",
    "logs",
    "node_modules",
    "output",
    "outputs",
    "scratch",
    "temp",
    "tmp",
    "venv",
}
INCLUDE_PROJECT_MAP_FILES = {"Makefile", "README.md", "package.json", "pyproject.toml"}


@dataclass(frozen=True)
class GuideIssue:
    code: str
    severity: str
    message: str


@dataclass(frozen=True)
class GuideQualityResult:
    status: str
    issues: list[GuideIssue]


def top_level_sections(text: str) -> list[str]:
    return [match.group(1).strip() for match in re.finditer(r"(?m)^##\s+(.+?)\s*$", text)]


def extract_section(text: str, heading: str) -> str:
    match = re.search(rf"(?ms)^##\s+{re.escape(heading)}\s*\n(?P<body>.*?)(?=^##\s+|\Z)", text)
    return match.group("body") if match else ""


def list_items(text: str) -> list[str]:
    return [line for line in text.splitlines() if re.match(r"^\s*[-*]\s+", line)]


def project_map_candidates(root: Path) -> list[str]:
    candidates: list[str] = []
    for child in sorted(root.iterdir(), key=lambda item: item.name.lower()):
        if child.name in SKIP_PROJECT_MAP_NAMES or child.name.startswith("."):
            continue
        if child.is_dir():
            candidates.append(f"{child.name}/")
        elif child.is_file() and child.name in INCLUDE_PROJECT_MAP_FILES:
            candidates.append(child.name)
    return candidates


def candidate_is_mapped(candidate: str, tokens: set[str]) -> bool:
    variants = {candidate}
    if candidate.endswith("/"):
        variants.add(candidate.rstrip("/"))
    else:
        variants.add(f"{candidate}/")
    if variants & tokens:
        return True
    if candidate.endswith("/"):
        return any(token.startswith(candidate) for token in tokens)
    return False


def missing_project_map_candidates(root: Path, tokens: set[str]) -> list[str]:
    return [candidate for candidate in project_map_candidates(root) if not candidate_is_mapped(candidate, tokens)]


def add_transient_content_issue(text: str, issues: list[GuideIssue]) -> None:
    lowered = text.lower()
    for term in TRANSIENT_TERMS:
        if term in lowered:
            issues.append(
                GuideIssue(
                    "transient_content",
                    "blocking",
                    f"AGENTS.md appears to contain transient workflow content matching `{term}`.",
                )
            )
            return


def check_agents_guide_quality(root: Path) -> GuideQualityResult:
    resolved = resolve_project_root(root)
    path = resolved / PROJECT_GUIDE_PATH
    issues: list[GuideIssue] = []
    if not path.is_file():
        return GuideQualityResult(
            "fail",
            [GuideIssue("missing_agents", "blocking", f"{PROJECT_GUIDE_PATH} is missing or is not a file.")],
        )

    text = path.read_text(encoding="utf-8")
    sections = top_level_sections(text)
    for required in REQUIRED_TOP_LEVEL_SECTIONS:
        if required not in sections:
            issues.append(GuideIssue("missing_section", "blocking", f"Missing required section: {required}."))
    for section in sections:
        if section not in ALLOWED_TOP_LEVEL_SECTIONS:
            issues.append(
                GuideIssue(
                    "extra_section",
                    "blocking",
                    f"Unexpected top-level section: {section}. Move detailed guidance to skills, docs, or .arbor/memory.md.",
                )
            )

    add_transient_content_issue(text, issues)

    project_goal = extract_section(text, "Project Goal")
    project_map = extract_section(text, "Project Map")
    for term in TEMPLATE_PLACEHOLDER_TERMS:
        if term in project_goal.lower() or term in project_map.lower():
            issues.append(GuideIssue("template_placeholder", "blocking", f"Template placeholder text remains: `{term}`."))

    map_items = list_items(project_map)
    tokens = project_map_tokens(project_map)
    missing = missing_project_map_candidates(resolved, tokens)
    stale = stale_project_map_entries(resolved, tokens)
    if not map_items:
        issues.append(GuideIssue("thin_project_map", "blocking", "Project Map has no list entries."))
    elif missing:
        issues.append(
            GuideIssue(
                "missing_project_map_entry",
                "blocking",
                "Project Map omits durable entrypoint candidates: " + ", ".join(f"`{item}`" for item in missing) + ".",
            )
        )
    if stale:
        issues.append(
            GuideIssue(
                "stale_project_map_entry",
                "blocking",
                "Project Map contains stale entries: " + ", ".join(f"`{item}`" for item in stale) + ".",
            )
        )
    for token in tokens:
        if not project_map_token_exists(resolved, token):
            issues.append(GuideIssue("missing_mapped_path", "blocking", f"Mapped path no longer exists: `{token}`."))

    status = "fail" if any(issue.severity == "blocking" for issue in issues) else "pass"
    return GuideQualityResult(status, issues)


def render_text(result: GuideQualityResult) -> str:
    if result.status == "pass":
        return "AGENTS guide quality: pass\n"
    lines = ["AGENTS guide quality: fail", ""]
    for issue in result.issues:
        lines.append(f"- [{issue.severity}] {issue.code}: {issue.message}")
    lines.append("")
    lines.append(
        "Fix AGENTS.md before stopping: keep only the Arbor guide sections, move transient detail elsewhere, "
        "and make Project Map useful for startup orientation."
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root to inspect.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args(argv)
    try:
        result = check_agents_guide_quality(args.root)
    except (OSError, UnicodeDecodeError, ProjectStateError) as exc:
        result = GuideQualityResult("fail", [GuideIssue("read_error", "blocking", str(exc))])
    if args.json:
        print(json.dumps(asdict(result), indent=2))
    else:
        print(render_text(result), end="")
    return 0 if result.status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
