"""Non-ASCII content must survive the trip to the model.

Every fixture elsewhere is English, which is why a real session was the first
thing to notice that Chinese task titles arrived as replacement characters. The
cause was not the data: Python encodes stdout with the platform locale, a legacy
code page on Windows, while the host reads the bytes as UTF-8.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

import pytest
from conftest import CLI, LAUNCHER

# A mix of scripts, an emoji, and a combining accent: enough to break any
# single-byte or legacy multi-byte encoding.
SAMPLES = ["核对 doctor 的行数", "Écrire les tests", "проверить бюджет", "レビュー", "cafe\u0301 ✅"]
REPLACEMENT = chr(0xFFFD)


# Force a hostile locale for the child. On Linux and macOS the default is already
# UTF-8, so without this the pin is untestable there: removing it would change
# nothing and the check would pass against a broken implementation. latin-1 cannot
# represent any of the samples, so an unpinned stream fails loudly.
HOSTILE_LOCALE = "latin-1"


def run_hook(event: str, payload: dict, *, via_launcher: bool = False) -> tuple[int, bytes]:
    env = dict(os.environ)
    env.pop("CLAUDE_PROJECT_DIR", None)
    env["PYTHONIOENCODING"] = HOSTILE_LOCALE
    if via_launcher:
        command = ["bash", str(LAUNCHER), event]
    else:
        command = [sys.executable, str(CLI), "hook", event]
    proc = subprocess.run(
        command,
        input=json.dumps(payload).encode("utf-8"),
        capture_output=True,
        env=env,
    )
    return proc.returncode, proc.stdout


def write_host_tasks(tmp_path, session_id: str, subjects: list[str]) -> None:
    directory = tmp_path / "config" / "tasks" / session_id
    directory.mkdir(parents=True, exist_ok=True)
    for index, subject in enumerate(subjects, start=1):
        (directory / f"{index}.json").write_text(
            json.dumps({"id": str(index), "subject": subject, "status": "pending"}, ensure_ascii=False),
            encoding="utf-8",
        )


class TestHookOutputEncoding:
    def test_task_titles_survive_as_utf8(self, project, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "config"))
        write_host_tasks(tmp_path, "s1", SAMPLES)
        code, _ = run_hook(
            "todo-snapshot",
            {"cwd": str(project.root), "session_id": "s1", "tool_name": "TaskCreate", "tool_input": {}},
        )
        assert code == 0

        code, raw = run_hook("session-start", {"cwd": str(project.root), "source": "startup"})
        assert code == 0
        text = raw.decode("utf-8")  # must not need errors="replace"
        assert REPLACEMENT not in text
        context = json.loads(text)["hookSpecificOutput"]["additionalContext"]
        for sample in SAMPLES:
            assert sample in context, f"{sample!r} did not survive"

    def test_notes_survive_as_utf8(self, project) -> None:
        project.memory("决定是否保留旧的适配器", "Vérifier le budget du paquet")
        project.ideas("把索引缓存起来")
        code, raw = run_hook("session-start", {"cwd": str(project.root), "source": "startup"})
        assert code == 0
        text = raw.decode("utf-8")
        assert REPLACEMENT not in text
        context = json.loads(text)["hookSpecificOutput"]["additionalContext"]
        assert "决定是否保留旧的适配器" in context
        assert "Vérifier le budget du paquet" in context
        assert "把索引缓存起来" in context

    def test_non_ascii_paths_are_reported_as_outdated(self, project) -> None:
        """The staleness check must not corrupt the path it names."""
        project.write("源码/加载器.py", "x = 1\n")
        project.commit("feat: add loader")
        (project.root / "源码" / "加载器.py").unlink()
        project.commit("refactor: drop loader")
        project.memory("重写 `源码/加载器.py`")
        code, raw = run_hook("session-start", {"cwd": str(project.root), "source": "startup"})
        assert code == 0
        context = json.loads(raw.decode("utf-8"))["hookSpecificOutput"]["additionalContext"]
        assert "outdated" in context
        assert "源码/加载器.py" in context

    def test_receipt_line_survives(self, project) -> None:
        project.memory("决定是否保留旧的适配器")
        code, raw = run_hook("session-start", {"cwd": str(project.root), "source": "startup"})
        assert code == 0
        assert REPLACEMENT not in raw.decode("utf-8")


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash unavailable")
class TestThroughTheLauncher:
    def test_end_to_end_utf8(self, project, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "config"))
        write_host_tasks(tmp_path, "s1", ["核对 doctor 的行数"])
        run_hook(
            "todo-snapshot",
            {"cwd": str(project.root), "session_id": "s1", "tool_name": "TaskCreate", "tool_input": {}},
            via_launcher=True,
        )
        code, raw = run_hook("session-start", {"cwd": str(project.root), "source": "startup"}, via_launcher=True)
        if code != 0 or not raw:
            pytest.skip("launcher found no usable interpreter here")
        text = raw.decode("utf-8")
        assert REPLACEMENT not in text
        assert "核对 doctor 的行数" in json.loads(text)["hookSpecificOutput"]["additionalContext"]


class TestPayloadDecoding:
    """The payload arrives as UTF-8 too, and is decoded with the same locale."""

    def test_non_ascii_content_in_the_payload_round_trips(self, project) -> None:
        payload = {
            "cwd": str(project.root),
            "tool_name": "TodoWrite",
            "tool_input": {"todos": [{"content": "重写加载器", "status": "in_progress"}]},
        }
        code, _ = run_hook("todo-snapshot", payload)
        assert code == 0
        stored = json.loads((project.root / ".arbor" / "session.json").read_text(encoding="utf-8"))
        assert stored["todos"]["items"][0]["content"] == "重写加载器"

    def test_non_ascii_reason_does_not_break_the_handoff(self, project) -> None:
        code, _ = run_hook("session-end", {"cwd": str(project.root), "reason": "已清空"})
        assert code == 0
        stored = json.loads((project.root / ".arbor" / "session.json").read_text(encoding="utf-8"))
        assert stored["handoff"]["reason"] == "已清空"
