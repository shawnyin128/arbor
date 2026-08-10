"""Launcher contracts.

The launcher is the only platform-specific code in the plugin. Its failure mode
is dangerous because it is quiet: a stray carriage return makes the shell branch
fail its interpreter probe and exit 0 with no output, which looks exactly like a
healthy hook in a project Arbor does not manage.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import LAUNCHER


def detail(result) -> str:
    """Format a launcher result so a CI failure is diagnosable from the log alone."""
    return "\n".join(
        [
            f"exit={result.returncode}",
            f"stdout={result.stdout!r}",
            f"stderr={result.stderr!r}",
        ]
    )


def find_posix_bash() -> str | None:
    """Locate a bash that can actually run a POSIX script.

    Selected by running it, for the same reason the launcher selects its
    interpreter that way. On Windows, ``bash`` on PATH is often
    ``System32\\bash.exe``, the WSL launcher: it resolves, and on a machine with no
    distribution installed it prints an installation notice and exits 1 without
    ever reading the script it was handed.
    """
    candidates = [
        os.environ.get("ARBOR_TEST_BASH"),
        shutil.which("bash"),
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        if not Path(candidate).exists() and shutil.which(candidate) is None:
            continue
        try:
            probe = subprocess.run(
                [candidate, "-c", "printf posix"],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if probe.returncode == 0 and probe.stdout.strip() == "posix":
            return candidate
    return None


POSIX_BASH = find_posix_bash()


def run_launcher(event: str, payload: str, *, shell: str, env: dict[str, str] | None = None):
    base = dict(os.environ)
    base.pop("CLAUDE_PROJECT_DIR", None)
    base.pop("ARBOR_PYTHON", None)
    if env:
        base.update(env)
    if shell == "bash":
        assert POSIX_BASH is not None
        return subprocess.run(
            [POSIX_BASH, str(LAUNCHER), event],
            input=payload,
            text=True,
            capture_output=True,
            env=base,
        )
    # `cmd /s /c` with the whole command wrapped in one extra pair of quotes is
    # the form that survives a quoted path; a argv list would get its inner
    # quotes escaped by Python's Windows quoting rules.
    return subprocess.run(
        f'cmd.exe /d /s /c ""{LAUNCHER}" {event}"',
        input=payload,
        text=True,
        capture_output=True,
        env=base,
    )


class TestFileForm:
    def test_contains_no_carriage_returns(self) -> None:
        assert b"\r" not in LAUNCHER.read_bytes(), (
            "a CR makes the shell branch silently no-op; .gitattributes must pin LF"
        )

    def test_opens_with_the_polyglot_guard(self) -> None:
        first = LAUNCHER.read_text(encoding="utf-8").splitlines()[0]
        assert first == ": << 'CMDBLOCK'"

    def test_batch_block_is_closed_before_the_shell_section(self) -> None:
        lines = LAUNCHER.read_text(encoding="utf-8").splitlines()
        end = lines.index("CMDBLOCK")
        batch = lines[1:end]
        assert any(line.strip().startswith("exit /b") for line in batch)
        assert "exec" in "\n".join(lines[end:])

    def test_probes_interpreters_by_running_them(self) -> None:
        """Presence on PATH is not enough: the Windows python3 stub resolves and fails."""
        text = LAUNCHER.read_text(encoding="utf-8")
        assert '-c ""' in text


@pytest.mark.skipif(POSIX_BASH is None, reason="no POSIX bash available")
class TestShellBranch:
    def test_injects_context_for_an_arbor_project(self, project) -> None:
        result = run_launcher("session-start", project.payload(source="startup"), shell="bash")
        assert result.returncode == 0, detail(result)
        data = json.loads(result.stdout)
        assert data["hookSpecificOutput"]["additionalContext"].startswith("# Arbor Session Context")

    def test_silent_for_a_project_without_arbor(self, make_project) -> None:
        plain = make_project(arbor=False)
        result = run_launcher("session-start", plain.payload(source="startup"), shell="bash")
        assert result.returncode == 0, detail(result)
        assert result.stdout == "", detail(result)

    def test_honors_an_explicit_interpreter(self, project) -> None:
        result = run_launcher(
            "session-start",
            project.payload(source="startup"),
            shell="bash",
            env={"ARBOR_PYTHON": sys.executable},
        )
        assert result.returncode == 0, detail(result)
        assert json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]

    def test_rejects_an_interpreter_that_fails_to_run(self, project, tmp_path) -> None:
        """The Microsoft Store stub case: a name that resolves and then fails.

        PATH keeps its real entries so bash and its utilities still work; the
        interpreters are shadowed by stubs that exit nonzero. Emptying PATH instead
        would hide bash from Python and test nothing about the launcher.
        """
        shims = tmp_path / "shims"
        shims.mkdir()
        for name in ("python", "python3"):
            stub = shims / name
            stub.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8", newline="\n")
            stub.chmod(0o755)
        result = run_launcher(
            "session-start",
            project.payload(source="startup"),
            shell="bash",
            env={
                "PATH": str(shims) + os.pathsep + os.environ.get("PATH", ""),
                "ARBOR_PYTHON": str(tmp_path / "no-such-python"),
            },
        )
        assert result.returncode == 0, detail(result)
        assert result.stdout == "", detail(result)

    def test_snapshots_todos_through_the_launcher(self, project) -> None:
        payload = project.payload(
            tool_name="TodoWrite",
            tool_input={"todos": [{"content": "Via launcher", "status": "in_progress"}]},
        )
        result = run_launcher("todo-snapshot", payload, shell="bash")
        assert result.returncode == 0, detail(result)
        items = project.session_state()["todos"]["items"]
        assert items[0]["content"] == "Via launcher"

    def test_records_handoff_through_the_launcher(self, project) -> None:
        result = run_launcher("session-end", project.payload(reason="logout"), shell="bash")
        assert result.returncode == 0, detail(result)
        assert project.session_state()["handoff"]["reason"] == "logout"


@pytest.mark.skipif(sys.platform != "win32", reason="cmd.exe only exists on Windows")
class TestBatchBranch:
    def test_injects_context_for_an_arbor_project(self, project) -> None:
        result = run_launcher("session-start", project.payload(source="startup"), shell="cmd")
        assert result.returncode == 0, detail(result)
        data = json.loads(result.stdout)
        assert data["hookSpecificOutput"]["additionalContext"].startswith("# Arbor Session Context")

    def test_silent_for_a_project_without_arbor(self, make_project) -> None:
        plain = make_project(arbor=False)
        result = run_launcher("session-start", plain.payload(source="startup"), shell="cmd")
        assert result.returncode == 0, detail(result)
        assert result.stdout.strip() == "", detail(result)
