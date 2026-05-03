#!/usr/bin/env python3
"""Build deterministic project fixtures for Arbor hook dispatch evaluation."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
ARBOR_SCRIPTS = ROOT / "skills" / "arbor" / "scripts"
if str(ARBOR_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(ARBOR_SCRIPTS))

import init_project_memory  # noqa: E402
import register_project_hooks  # noqa: E402


FIXTURE_NAMES = (
    "clean_git_project",
    "non_git_project",
    "missing_agents",
    "missing_memory",
    "uncommitted_changes",
    "stale_memory",
    "durable_drift_docs",
    "outside_root_path",
)


class FixtureError(ValueError):
    """Raised when a fixture cannot be built cleanly."""


@dataclass(frozen=True)
class FixtureResult:
    name: str
    root: Path
    summary: dict[str, Any]
    outside_path: Path | None = None


def run_git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def init_git_repo(root: Path) -> None:
    run_git(root, "init")
    run_git(root, "config", "user.email", "fixture@example.com")
    run_git(root, "config", "user.name", "Arbor Fixture")


def commit_all(root: Path, message: str) -> None:
    run_git(root, "add", ".")
    run_git(root, "commit", "-m", message)


def write_file(root: Path, relative_path: str, content: str) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def initialize_arbor_project(root: Path) -> None:
    init_project_memory.init_project_memory(root)
    register_project_hooks.register_project_hooks(root)


def available_fixtures() -> list[str]:
    return list(FIXTURE_NAMES)


def build_fixture(name: str, root: Path) -> FixtureResult:
    root = root.resolve()
    if name not in FIXTURE_NAMES:
        raise FixtureError(f"unknown fixture: {name}")
    if root.exists() and any(root.iterdir()):
        raise FixtureError(f"fixture root must be empty: {root}")
    root.mkdir(parents=True, exist_ok=True)

    builder = FIXTURE_BUILDERS[name]
    outside_path = builder(root)
    return FixtureResult(
        name=name,
        root=root,
        summary=summarize_fixture(name, root, outside_path),
        outside_path=outside_path,
    )


def build_clean_git_project(root: Path) -> Path | None:
    init_git_repo(root)
    initialize_arbor_project(root)
    write_file(root, "README.md", "# Fixture Project\n\nClean Arbor fixture.\n")
    commit_all(root, "initialize clean arbor fixture")
    return None


def build_non_git_project(root: Path) -> Path | None:
    initialize_arbor_project(root)
    write_file(root, "README.md", "# Fixture Project\n\nNon-git Arbor fixture.\n")
    return None


def build_missing_agents(root: Path) -> Path | None:
    init_git_repo(root)
    initialize_arbor_project(root)
    write_file(root, "README.md", "# Fixture Project\n\nMissing AGENTS fixture.\n")
    commit_all(root, "initialize missing agents fixture")
    (root / "AGENTS.md").unlink()
    return None


def build_missing_memory(root: Path) -> Path | None:
    init_git_repo(root)
    initialize_arbor_project(root)
    write_file(root, "README.md", "# Fixture Project\n\nMissing memory fixture.\n")
    commit_all(root, "initialize missing memory fixture")
    (root / ".codex" / "memory.md").unlink()
    return None


def build_uncommitted_changes(root: Path) -> Path | None:
    init_git_repo(root)
    initialize_arbor_project(root)
    write_file(root, "tracked.txt", "base\n")
    commit_all(root, "initialize uncommitted fixture")
    write_file(root, "tracked.txt", "base\nchanged\n")
    write_file(root, "pending.txt", "pending\n")
    return None


def build_stale_memory(root: Path) -> Path | None:
    init_git_repo(root)
    initialize_arbor_project(root)
    memory = root / ".codex" / "memory.md"
    memory.write_text(
        "# Session Memory\n\n"
        "## Observations\n\n"
        "## In-flight\n\n"
        "- **Stale fixture item.** Memory says the parser bug is unresolved, "
        "but `fix-parser.txt` records the completed fix and should prompt memory cleanup.\n",
        encoding="utf-8",
    )
    write_file(root, "tracked.txt", "base\n")
    commit_all(root, "initialize stale memory fixture")
    write_file(root, "fix-parser.txt", "parser bug fixed in current uncommitted work\n")
    return None


def build_durable_drift_docs(root: Path) -> Path | None:
    init_git_repo(root)
    initialize_arbor_project(root)
    write_file(
        root,
        "docs/constraints.md",
        "# Constraints\n\nDurable constraint: all hook execution must remain project-local.\n",
    )
    write_file(
        root,
        "docs/project-map.md",
        "# Project Map\n\nDurable map update: Stage B dispatch evaluation now owns fixture generation.\n",
    )
    write_file(
        root,
        "docs/workflow.md",
        "# Workflow\n\nDurable workflow update: run fixture, dispatcher, hook execution, then metrics.\n",
    )
    commit_all(root, "initialize durable drift fixture")
    return None


def build_outside_root_path(root: Path) -> Path | None:
    init_git_repo(root)
    initialize_arbor_project(root)
    commit_all(root, "initialize outside path fixture")
    outside_root = root.parent / f"{root.name}-outside"
    outside_path = outside_root / "project-map.md"
    outside_path.parent.mkdir(parents=True, exist_ok=True)
    outside_path.write_text("outside root content should never be leaked\n", encoding="utf-8")
    return outside_path


FIXTURE_BUILDERS: dict[str, Callable[[Path], Path | None]] = {
    "clean_git_project": build_clean_git_project,
    "non_git_project": build_non_git_project,
    "missing_agents": build_missing_agents,
    "missing_memory": build_missing_memory,
    "uncommitted_changes": build_uncommitted_changes,
    "stale_memory": build_stale_memory,
    "durable_drift_docs": build_durable_drift_docs,
    "outside_root_path": build_outside_root_path,
}


def git_status_short(root: Path) -> list[str] | None:
    if not (root / ".git").exists():
        return None
    proc = run_git(root, "status", "--short", check=False)
    if proc.returncode != 0:
        return None
    return proc.stdout.splitlines()


def list_available_docs(root: Path) -> list[str]:
    docs = root / "docs"
    if not docs.is_dir():
        return []
    return sorted(str(path.relative_to(root)) for path in docs.rglob("*") if path.is_file())


def classify_memory(name: str, root: Path) -> str:
    if not (root / ".codex" / "memory.md").is_file():
        return "missing"
    if name == "stale_memory":
        return "stale"
    return "present"


def classify_agents(name: str, root: Path) -> str:
    if not (root / "AGENTS.md").is_file():
        return "missing"
    if name == "durable_drift_docs":
        return "present_with_durable_drift_docs"
    return "present"


def summarize_fixture(name: str, root: Path, outside_path: Path | None = None) -> dict[str, Any]:
    status = git_status_short(root)
    summary: dict[str, Any] = {
        "fixture": name,
        "project_root": str(root),
        "is_git_repo": (root / ".git").is_dir(),
        "git_status_short": status,
        "has_agents": (root / "AGENTS.md").is_file(),
        "has_memory": (root / ".codex" / "memory.md").is_file(),
        "has_hooks": (root / ".codex" / "hooks.json").is_file(),
        "available_docs": list_available_docs(root),
        "memory_state": classify_memory(name, root),
        "agents_state": classify_agents(name, root),
        "notes": fixture_notes(name),
    }
    if outside_path is not None:
        summary["outside_path"] = str(outside_path)
    return summary


def fixture_notes(name: str) -> str:
    return {
        "clean_git_project": "Initialized git project with clean status.",
        "non_git_project": "Initialized Arbor files without a git repository.",
        "missing_agents": "AGENTS.md was removed after initial commit.",
        "missing_memory": ".codex/memory.md was removed after initial commit.",
        "uncommitted_changes": "Tracked modification and untracked file are present.",
        "stale_memory": "Memory contains an in-flight item contradicted by current uncommitted work.",
        "durable_drift_docs": "Project-local docs contain durable goal, constraint, or map update signals.",
        "outside_root_path": "Fixture includes an outside-root path for rejection tests.",
    }[name]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", choices=FIXTURE_NAMES, required=True, help="Fixture to build.")
    parser.add_argument("--root", type=Path, required=True, help="Empty directory where the fixture should be built.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = build_fixture(args.fixture, args.root)
    except FixtureError as exc:
        parser.error(str(exc))
    print(json.dumps(result.summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
