"""Shared fixtures for the Arbor test suite.

Temporary projects are real git repositories built with native paths. Git Bash
POSIX paths such as ``/tmp/x`` are deliberately avoided: a Windows Python cannot
resolve them, which silently turns a hook into a no-op and would make a broken
test look like a passing one.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = REPO_ROOT / "plugins" / "arbor"
SCRIPTS_DIR = PLUGIN_ROOT / "skills" / "arbor" / "scripts"
LAUNCHER = PLUGIN_ROOT / "hooks" / "arbor-hook.cmd"
CLI = SCRIPTS_DIR / "arbor.py"

sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture(autouse=True)
def isolate_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove ambient state that would leak the real repository into a test.

    ``CLAUDE_PROJECT_DIR`` is set inside a live Claude Code session and takes
    precedence over the payload ``cwd``, so leaving it set would point every hook
    under test at this repository instead of the temporary project.
    """
    for name in (
        "CLAUDE_PROJECT_DIR",
        "ARBOR_PYTHON",
        "ARBOR_CONTEXT_BUDGET",
        "ARBOR_GIT_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)


@dataclass
class Project:
    """A temporary git repository used as an Arbor project."""

    root: Path

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(self.root), *args],
            text=True,
            capture_output=True,
            check=True,
        )

    def write(self, relative: str, text: str) -> Path:
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        return target

    def mkdir(self, relative: str) -> Path:
        target = self.root / relative
        target.mkdir(parents=True, exist_ok=True)
        return target

    def enable_arbor(self) -> Path:
        return self.mkdir(".arbor")

    def commit(self, message: str) -> None:
        self.git("add", "-A")
        self.git("commit", "-qm", message)

    def payload(self, **overrides: Any) -> str:
        data: dict[str, Any] = {"cwd": str(self.root), "session_id": "test-session"}
        data.update(overrides)
        return json.dumps(data)

    def session_state(self) -> dict[str, Any]:
        path = self.root / ".arbor" / "session.json"
        if not path.is_file():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def memory(self, *entries: str) -> Path:
        body = "\n".join(f"- {entry}" for entry in entries) or "- None."
        return self.write(".arbor/memory.md", f"# Session Memory\n\n## Unresolved\n\n{body}\n")

    def ideas(self, *entries: str) -> Path:
        body = "\n".join(f"- {entry}" for entry in entries) or "- None."
        return self.write(".arbor/ideas.md", f"# Parked Ideas\n\n## Parked\n\n{body}\n")

    def bridge(self, wired: bool = True) -> Path:
        body = "# Claude Guide\n\n@AGENTS.md\n" if wired else "# Claude Guide\n\nNo import here.\n"
        return self.write("CLAUDE.md", body)

    def guide(self, map_entries: tuple[str, ...] = ("README.md",)) -> Path:
        entries = "\n".join(f"- `{entry}`: durable entrypoint." for entry in map_entries)
        return self.write(
            "AGENTS.md",
            "# Agent Guide\n\n"
            "## Project Goal\n\nShip a tested thing.\n\n"
            "## Project Constraints\n\n- Keep it small.\n\n"
            f"## Project Map\n\n{entries}\n",
        )


@pytest.fixture
def make_project(tmp_path: Path):
    """Return a factory that builds temporary git projects."""
    counter = {"n": 0}

    def factory(*, git: bool = True, arbor: bool = True, commit: bool = True) -> Project:
        counter["n"] += 1
        root = tmp_path / f"project{counter['n']}"
        root.mkdir()
        project = Project(root)
        if git:
            subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
            project.git("config", "user.email", "arbor@example.invalid")
            project.git("config", "user.name", "Arbor Test")
            project.git("config", "commit.gpgsign", "false")
        if arbor:
            project.enable_arbor()
        project.write("README.md", "# fixture\n")
        if git and commit:
            project.commit("chore: seed fixture")
        return project

    return factory


@pytest.fixture
def project(make_project) -> Project:
    """A committed git project that has opted into Arbor."""
    return make_project()


def run_cli(*args: str, stdin: str = "", cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Invoke the Arbor CLI as a subprocess."""
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        input=stdin,
        text=True,
        capture_output=True,
        cwd=str(cwd) if cwd else None,
    )
