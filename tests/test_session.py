"""Machine-owned session state contracts."""

from __future__ import annotations

import json

import pytest
from arbor_core import SCHEMA_VERSION, session


class TestLoad:
    def test_missing_file_yields_an_empty_record(self, project) -> None:
        assert session.load(project.root) == session.empty_state()

    @pytest.mark.parametrize(
        "content",
        ["", "   ", "not json", "{unclosed", "[]", '"text"', "null"],
        ids=["empty", "spaces", "prose", "truncated", "array", "string", "null"],
    )
    def test_unusable_content_yields_an_empty_record(self, project, content: str) -> None:
        project.write(".arbor/session.json", content)
        assert session.load(project.root) == session.empty_state()

    def test_foreign_schema_is_discarded(self, project) -> None:
        project.write(".arbor/session.json", json.dumps({"schema": 999, "todos": {"items": [{"content": "x"}]}}))
        assert session.todo_items(session.load(project.root)) == []

    def test_undecodable_file_yields_an_empty_record(self, project) -> None:
        (project.root / ".arbor" / "session.json").write_bytes(b"\xff\xfe\x00")
        assert session.load(project.root) == session.empty_state()

    def test_a_corrupt_file_is_replaced_not_propagated(self, project) -> None:
        project.write(".arbor/session.json", "{ broken")
        assert session.snapshot_todos(project.root, [{"content": "A", "status": "pending"}])
        state = session.load(project.root)
        assert [item["content"] for item in session.todo_items(state)] == ["A"]


class TestSave:
    def test_refuses_to_create_state_outside_an_arbor_project(self, make_project) -> None:
        plain = make_project(arbor=False)
        assert session.save(plain.root, session.empty_state()) is False
        assert not (plain.root / ".arbor").exists()

    def test_writes_valid_json_with_the_current_schema(self, project) -> None:
        assert session.save(project.root, session.empty_state())
        data = project.session_state()
        assert data["schema"] == SCHEMA_VERSION
        assert data["updated_at"]

    def test_leaves_no_temporary_files_behind(self, project) -> None:
        for _ in range(5):
            session.snapshot_todos(project.root, [{"content": "A", "status": "pending"}])
        leftovers = [path.name for path in (project.root / ".arbor").iterdir() if path.suffix == ".tmp"]
        assert leftovers == []

    def test_replacement_is_atomic_across_repeated_writes(self, project) -> None:
        """Each write must leave a fully parseable file, never a truncated one."""
        for index in range(10):
            session.snapshot_todos(project.root, [{"content": f"Task {index}", "status": "pending"}])
            json.loads((project.root / ".arbor" / "session.json").read_text(encoding="utf-8"))


class TestNormalizeTodos:
    def test_accepts_the_documented_shape(self) -> None:
        items = session.normalize_todos(
            [{"content": "Build it", "status": "in_progress", "activeForm": "Building it"}]
        )
        assert items == [{"content": "Build it", "status": "in_progress", "activeForm": "Building it"}]

    def test_empty_list_is_a_valid_cleared_list(self) -> None:
        assert session.normalize_todos([]) == []

    @pytest.mark.parametrize("raw", [None, "text", 42, {"todos": []}])
    def test_non_list_input_is_rejected(self, raw) -> None:
        assert session.normalize_todos(raw) is None

    def test_a_list_of_only_junk_is_rejected(self) -> None:
        assert session.normalize_todos([{"nope": 1}, "text", None]) is None

    def test_unknown_status_values_are_dropped(self) -> None:
        items = session.normalize_todos(
            [{"content": "Keep", "status": "pending"}, {"content": "Drop", "status": "cancelled"}]
        )
        assert [item["content"] for item in items] == ["Keep"]

    def test_blank_content_is_dropped(self) -> None:
        items = session.normalize_todos(
            [{"content": "   ", "status": "pending"}, {"content": " Keep ", "status": "pending"}]
        )
        assert [item["content"] for item in items] == ["Keep"]

    def test_missing_active_form_is_allowed(self) -> None:
        assert session.normalize_todos([{"content": "A", "status": "pending"}]) == [
            {"content": "A", "status": "pending"}
        ]


class TestOrdering:
    def test_unfinished_puts_in_progress_first(self, project) -> None:
        session.snapshot_todos(
            project.root,
            [
                {"content": "P1", "status": "pending"},
                {"content": "I1", "status": "in_progress"},
                {"content": "C1", "status": "completed"},
                {"content": "P2", "status": "pending"},
            ],
        )
        state = session.load(project.root)
        assert [item["content"] for item in session.unfinished_todos(state)] == ["I1", "P1", "P2"]


class TestReceipts:
    def test_absent_receipt_is_an_empty_mapping(self, project) -> None:
        assert session.receipt(session.load(project.root), "SessionStart") == {}

    def test_receipt_records_time_and_plugin_version(self, project) -> None:
        session.record_start(project.root, "abc", "startup")
        entry = session.receipt(session.load(project.root), "SessionStart")
        assert entry["at"]
        assert entry["version"]

    def test_each_hook_gets_its_own_receipt(self, project) -> None:
        session.record_start(project.root, "abc", "startup")
        session.snapshot_todos(project.root, [{"content": "A", "status": "pending"}])
        session.record_handoff(project.root, "clear", "main", "abc1234", 2)
        receipts = session.load(project.root)["receipts"]
        assert set(receipts) == {"SessionStart", "PostToolUse:TodoWrite", "SessionEnd"}

    def test_handoff_preserves_the_todo_snapshot(self, project) -> None:
        session.snapshot_todos(project.root, [{"content": "A", "status": "pending"}])
        session.record_handoff(project.root, "clear", "main", "abc1234", 0)
        state = session.load(project.root)
        assert session.todo_items(state)
        assert state["handoff"]["unfinished"] == 1
