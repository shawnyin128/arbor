"""Shared fixtures for the Arbor test suite.

Temporary projects are real git repositories built with native paths. Git Bash
POSIX paths such as ``/tmp/x`` are deliberately avoided: a Windows Python cannot
resolve them, which silently turns a hook into a no-op and would make a broken
test look like a passing one.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
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

# Deliberately outside the repository. A temp root inside it makes git's upward
# search discover this repository from a project built to have none, and leaves
# repository files open to a subprocess while tests are running.
FALLBACK_TEMP = Path(tempfile.gettempdir()) / "arbor-pytest-tmp"


def _default_temp_root_is_usable() -> bool:
    """Report whether pytest can use the platform temp directory.

    pytest keeps its temporary projects under ``<temp>/pytest-of-<user>`` and
    scans that directory to pick the next run number. Some environments leave it
    unreadable, which aborts collection before a single test runs and reads as a
    broken suite rather than a broken environment.
    """
    root = Path(tempfile.gettempdir())
    try:
        probe = root / f"arbor-probe-{os.getpid()}"
        probe.mkdir(exist_ok=True)
        probe.rmdir()
        for existing in root.glob("pytest-of-*"):
            list(os.scandir(existing))
    except OSError:
        return False
    return True


def pytest_configure(config: pytest.Config) -> None:
    """Redirect the temp root to a private one when the default is unusable."""
    if config.option.basetemp or _default_temp_root_is_usable():
        return
    FALLBACK_TEMP.mkdir(parents=True, exist_ok=True)
    config.option.basetemp = str(FALLBACK_TEMP)


@pytest.fixture(autouse=True)
def isolate_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Remove ambient state that would leak the real repository into a test.

    ``CLAUDE_PROJECT_DIR`` is set inside a live Claude Code session and takes
    precedence over the payload ``cwd``, so leaving it set would point every hook
    under test at this repository instead of the temporary project.

    ``GIT_CEILING_DIRECTORIES`` stops git's upward search at the temp root. Without
    it, a project built to have no repository would discover whichever repository
    happens to contain the temp directory, so the no-repo tests would pass or fail
    depending on where the platform puts temporary files.
    """
    for name in (
        "CLAUDE_PROJECT_DIR",
        "ARBOR_PYTHON",
        "ARBOR_CONTEXT_BUDGET",
        "ARBOR_GIT_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))


@dataclass
class Project:
    """A temporary git repository used as an Arbor project."""

    root: Path

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        # Decode as UTF-8 explicitly. The platform locale is a legacy code page on
        # Windows, and git echoes filenames, so a non-ASCII path in a fixture would
        # otherwise raise inside subprocess's reader thread.
        return subprocess.run(
            ["git", "-C", str(self.root), *args],
            text=True,
            encoding="utf-8",
            errors="replace",
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

    def track_upstream(self) -> None:
        """Give the current branch a real upstream, level with it.

        A clone would be heavier and a fabricated config entry would not exercise
        the same git plumbing, so this creates a bare remote and pushes to it.
        """
        remote = self.root.parent / f"{self.root.name}-remote.git"
        subprocess.run(
            ["git", "init", "-q", "--bare", str(remote)],
            check=True,
            capture_output=True,
        )
        self.git("remote", "add", "origin", str(remote))
        branch = self.git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        self.git("push", "-q", "-u", "origin", branch)

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
            "## Commands\n\n- Run one test with `pytest -k name`.\n\n"
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
        encoding="utf-8",
        capture_output=True,
        cwd=str(cwd) if cwd else None,
    )
