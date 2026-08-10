"""Hook entrypoint contracts.

Plugin-level hooks fire in every project the user opens, so the dominant risk is
not a missing feature but a hook that acts where it should not, or fails loudly
where it should stay quiet.
"""

from __future__ import annotations

import json

import pytest
from arbor_core import hooks, session


class TestPayloadParsing:
    @pytest.mark.parametrize(
        "raw",
        [
            "",
            "   ",
            "\n",
            "not json",
            "{unclosed",
            "[]",
            '"a string"',
            "123",
            "null",
            "probe",
        ],
        ids=[
            "empty",
            "spaces",
            "newline",
            "prose",
            "truncated-object",
            "array",
            "string",
            "number",
            "null",
            "probe-word",
        ],
    )
    def test_unusable_payloads_yield_none(self, raw: str) -> None:
        assert hooks.parse_payload(raw) is None

    def test_object_payload_parses(self) -> None:
        assert hooks.parse_payload('{"cwd": "/x"}') == {"cwd": "/x"}

    def test_byte_order_mark_is_tolerated(self) -> None:
        assert hooks.parse_payload(hooks.BOM + '{"cwd": "/x"}') == {"cwd": "/x"}


class TestProjectRootResolution:
    def test_uses_payload_cwd(self, project) -> None:
        assert hooks.project_root({"cwd": str(project.root)}) == project.root

    def test_claude_project_dir_wins_over_cwd(self, project, make_project, monkeypatch) -> None:
        other = make_project()
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(other.root))
        assert hooks.project_root({"cwd": str(project.root)}) == other.root

    @pytest.mark.parametrize("cwd", [None, "", "   ", 42, [], {}])
    def test_unusable_cwd_yields_none(self, cwd) -> None:
        assert hooks.project_root({"cwd": cwd}) is None

    def test_nonexistent_directory_yields_none(self, tmp_path) -> None:
        assert hooks.project_root({"cwd": str(tmp_path / "absent")}) is None

    def test_file_path_is_not_a_project_root(self, project) -> None:
        assert hooks.project_root({"cwd": str(project.root / "README.md")}) is None


class TestSessionStart:
    def test_emits_json_with_context_and_receipt_channels(self, project) -> None:
        code, output = hooks.session_start(project.payload(source="startup"))
        assert code == 0
        data = json.loads(output)
        assert data["hookSpecificOutput"]["hookEventName"] == "SessionStart"
        assert data["hookSpecificOutput"]["additionalContext"].startswith("# Arbor Session Context")
        assert data["systemMessage"].startswith("Arbor")

    @pytest.mark.parametrize("source", ["startup", "resume", "clear", "compact"])
    def test_runs_for_every_relevant_source(self, project, source: str) -> None:
        code, output = hooks.session_start(project.payload(source=source))
        assert code == 0
        assert output

    def test_skips_forked_sessions(self, project) -> None:
        # A fork inherits the parent conversation, so the context is already there.
        assert hooks.session_start(project.payload(source="fork")) == hooks.SKIP

    def test_runs_when_source_is_absent(self, project) -> None:
        code, output = hooks.session_start(project.payload())
        assert code == 0
        assert output

    def test_silent_in_project_without_arbor_directory(self, make_project) -> None:
        plain = make_project(arbor=False)
        assert hooks.session_start(plain.payload(source="startup")) == hooks.SKIP
        assert not (plain.root / ".arbor").exists()

    def test_records_receipt(self, project) -> None:
        hooks.session_start(project.payload(source="startup"))
        entry = session.receipt(session.load(project.root), "SessionStart")
        assert entry.get("at")
        assert entry.get("version")


class TestTodoSnapshot:
    def _payload(self, project, todos, **overrides):
        return project.payload(tool_name="TodoWrite", tool_input={"todos": todos}, **overrides)

    def test_captures_items(self, project) -> None:
        todos = [
            {"content": "First", "status": "completed", "activeForm": "Doing first"},
            {"content": "Second", "status": "in_progress", "activeForm": "Doing second"},
            {"content": "Third", "status": "pending", "activeForm": "Doing third"},
        ]
        assert hooks.todo_snapshot(self._payload(project, todos)) == hooks.SKIP
        state = session.load(project.root)
        assert [item["content"] for item in session.todo_items(state)] == ["First", "Second", "Third"]
        assert [item["content"] for item in session.unfinished_todos(state)] == ["Second", "Third"]

    def test_records_head_for_commit_distance(self, project) -> None:
        hooks.todo_snapshot(self._payload(project, [{"content": "A", "status": "pending"}]))
        assert session.load(project.root)["todos"]["captured_head"]

    def test_ignores_other_tools(self, project) -> None:
        payload = project.payload(tool_name="Write", tool_input={"todos": [{"content": "A", "status": "pending"}]})
        assert hooks.todo_snapshot(payload) == hooks.SKIP
        assert session.todo_items(session.load(project.root)) == []

    @pytest.mark.parametrize("tool_input", [None, "text", 5, []])
    def test_ignores_unusable_tool_input(self, project, tool_input) -> None:
        payload = project.payload(tool_name="TodoWrite", tool_input=tool_input)
        assert hooks.todo_snapshot(payload) == hooks.SKIP
        assert session.todo_items(session.load(project.root)) == []

    def test_malformed_todos_preserve_the_previous_snapshot(self, project) -> None:
        hooks.todo_snapshot(self._payload(project, [{"content": "Keep me", "status": "in_progress"}]))
        hooks.todo_snapshot(self._payload(project, [{"nonsense": True}, {"content": "", "status": "pending"}]))
        state = session.load(project.root)
        assert [item["content"] for item in session.todo_items(state)] == ["Keep me"]

    def test_silent_in_project_without_arbor_directory(self, make_project) -> None:
        plain = make_project(arbor=False)
        payload = plain.payload(tool_name="TodoWrite", tool_input={"todos": [{"content": "A", "status": "pending"}]})
        assert hooks.todo_snapshot(payload) == hooks.SKIP
        assert not (plain.root / ".arbor").exists()


class TestSessionEnd:
    def test_records_handoff(self, project) -> None:
        project.write("dirty.txt", "x\n")
        hooks.todo_snapshot(
            project.payload(tool_name="TodoWrite", tool_input={"todos": [{"content": "A", "status": "pending"}]})
        )
        assert hooks.session_end(project.payload(reason="clear")) == hooks.SKIP
        handoff = session.load(project.root)["handoff"]
        assert handoff["reason"] == "clear"
        assert handoff["branch"]
        assert handoff["head"]
        assert handoff["dirty_count"] >= 1
        assert handoff["unfinished"] == 1

    def test_works_outside_a_git_repository(self, make_project) -> None:
        loose = make_project(git=False)
        assert hooks.session_end(loose.payload(reason="other")) == hooks.SKIP
        handoff = session.load(loose.root)["handoff"]
        assert handoff["branch"] == ""
        assert handoff["dirty_count"] == 0

    def test_silent_in_project_without_arbor_directory(self, make_project) -> None:
        plain = make_project(arbor=False)
        assert hooks.session_end(plain.payload(reason="logout")) == hooks.SKIP
        assert not (plain.root / ".arbor").exists()


class TestUniversalRobustness:
    """No entrypoint may fail or act on an unusable payload."""

    @pytest.mark.parametrize("event", sorted(hooks.ENTRYPOINTS))
    @pytest.mark.parametrize(
        "raw",
        ["", "not json", "[]", "null", '{"cwd": null}', '{"cwd": "/nonexistent-arbor-path"}'],
    )
    def test_unusable_input_is_a_silent_skip(self, event: str, raw: str) -> None:
        assert hooks.ENTRYPOINTS[event](raw) == hooks.SKIP


class TestTaskToolCapture:
    """This host exposes TaskCreate/TaskUpdate rather than TodoWrite."""

    def _write_tasks(self, tmp_path, session_id, tasks):
        directory = tmp_path / "config" / "tasks" / session_id
        directory.mkdir(parents=True, exist_ok=True)
        for index, (subject, status) in enumerate(tasks, start=1):
            (directory / f"{index}.json").write_text(
                json.dumps({"id": str(index), "subject": subject, "status": status}),
                encoding="utf-8",
            )

    @pytest.mark.parametrize("tool", ["TaskCreate", "TaskUpdate"])
    def test_captures_the_host_list(self, project, tmp_path, monkeypatch, tool: str) -> None:
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "config"))
        self._write_tasks(tmp_path, "abc", [("Wire it up", "in_progress"), ("Test it", "pending")])
        payload = project.payload(tool_name=tool, session_id="abc", tool_input={"subject": "Wire it up"})
        assert hooks.todo_snapshot(payload) == hooks.SKIP
        state = session.load(project.root)
        assert [item["content"] for item in session.unfinished_todos(state)] == ["Wire it up", "Test it"]

    def test_receipt_names_the_tool_that_fired(self, project, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "config"))
        self._write_tasks(tmp_path, "abc", [("A", "pending")])
        hooks.todo_snapshot(project.payload(tool_name="TaskCreate", session_id="abc", tool_input={}))
        assert session.receipt(session.load(project.root), "PostToolUse:TaskCreate")

    def test_ignores_unrelated_task_tools(self, project, tmp_path, monkeypatch) -> None:
        """TaskStop manages background agents, not the task list."""
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "config"))
        self._write_tasks(tmp_path, "abc", [("A", "pending")])
        payload = project.payload(tool_name="TaskStop", session_id="abc", tool_input={"task_id": "x"})
        assert hooks.todo_snapshot(payload) == hooks.SKIP
        assert session.todo_items(session.load(project.root)) == []

    def test_session_end_refreshes_from_the_host_list(self, project, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "config"))
        self._write_tasks(tmp_path, "abc", [("Left open", "pending")])
        hooks.session_end(project.payload(reason="clear", session_id="abc"))
        state = session.load(project.root)
        assert [item["content"] for item in session.unfinished_todos(state)] == ["Left open"]
        assert state["handoff"]["unfinished"] == 1

    def test_still_silent_outside_an_arbor_project(self, make_project, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "config"))
        self._write_tasks(tmp_path, "abc", [("A", "pending")])
        plain = make_project(arbor=False)
        payload = plain.payload(tool_name="TaskCreate", session_id="abc", tool_input={})
        assert hooks.todo_snapshot(payload) == hooks.SKIP
        assert not (plain.root / ".arbor").exists()
