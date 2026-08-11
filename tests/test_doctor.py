"""Doctor reporting contracts.

Doctor is the answer to "did the hooks actually fire?" and "is the packet within
budget?". It reports and never repairs.
"""

from __future__ import annotations

from arbor_core import doctor, hooks, init, notes, session
from conftest import run_cli


def row(rows, surface: str) -> doctor.Row:
    matches = [item for item in rows if item.surface == surface]
    assert matches, f"no row for {surface}; got {[item.surface for item in rows]}"
    return matches[0]


def _section(text: str, heading: str) -> str:
    body = doctor._section_body(text, heading)
    assert body is not None, f"no {heading} section in the scaffold"
    return body


class TestNonArborProject:
    def test_reports_only_that_arbor_is_absent(self, make_project) -> None:
        plain = make_project(arbor=False)
        rows = doctor.collect(plain.root)
        assert len(rows) == 1
        assert rows[0].status == doctor.MISSING
        assert doctor.result(rows) == "needs_attention"


class TestGuide:
    def test_missing_guide(self, project) -> None:
        assert row(doctor.collect(project.root), "AGENTS.md").status == doctor.MISSING

    def test_healthy_guide(self, project) -> None:
        project.guide(map_entries=("README.md",))
        assert row(doctor.collect(project.root), "AGENTS.md").status == doctor.OK

    def test_missing_required_section(self, project) -> None:
        project.write("AGENTS.md", "# Guide\n\n## Project Goal\n\nA goal.\n")
        entry = row(doctor.collect(project.root), "AGENTS.md")
        assert entry.status == doctor.WARN
        assert "Project Constraints" in entry.detail

    def test_commands_is_required(self, project) -> None:
        """Initializing with Arbor displaces `/init`, whose first output is commands."""
        project.write(
            "AGENTS.md",
            "# Guide\n\n## Project Goal\n\nA goal.\n\n"
            "## Project Constraints\n\n- Small.\n\n"
            "## Project Map\n\n- `README.md`: overview.\n",
        )
        entry = row(doctor.collect(project.root), "AGENTS.md")
        assert entry.status == doctor.WARN
        assert "Commands" in entry.detail

    def test_template_placeholder_is_flagged(self, project) -> None:
        init.run(project.root)
        entry = row(doctor.collect(project.root), "AGENTS.md")
        assert entry.status == doctor.WARN
        assert "placeholder" in entry.detail

    def test_an_unfilled_commands_section_is_flagged(self, project) -> None:
        """Every other section is written, so only the Commands marker can raise this."""
        init.run(project.root)
        scaffold = (project.root / "AGENTS.md").read_text(encoding="utf-8")
        commands = _section(scaffold, "Commands")
        assert "has not recorded the commands for this repository" in commands
        project.write(
            "AGENTS.md",
            "# Agent Guide\n\n"
            "## Project Goal\n\nShip a tested thing.\n\n"
            f"## Commands\n{commands}\n"
            "## Project Constraints\n\n- Keep it small.\n\n"
            "## Project Map\n\n- `README.md`: overview.\n",
        )
        entry = row(doctor.collect(project.root), "AGENTS.md")
        assert entry.status == doctor.WARN
        assert "placeholder" in entry.detail

    def test_a_path_git_tracked_but_now_gone_is_flagged(self, project) -> None:
        project.write("src/parser.py", "x = 1\n")
        project.commit("feat: add parser")
        (project.root / "src" / "parser.py").unlink()
        project.commit("refactor: drop parser")
        project.guide(map_entries=("README.md", "src/parser.py"))
        entry = row(doctor.collect(project.root), "AGENTS.md")
        assert entry.status == doctor.WARN
        assert "src/parser.py" in entry.detail

    def test_a_stale_path_outside_the_map_is_flagged_too(self, project) -> None:
        """A path in Project Constraints misleads exactly as much as one in the map."""
        project.write("hooks/launcher.cmd", "rem x\n")
        project.commit("feat: add launcher")
        (project.root / "hooks" / "launcher.cmd").unlink()
        project.commit("refactor: drop launcher")
        project.write(
            "AGENTS.md",
            "# Agent Guide\n\n"
            "## Project Goal\n\nShip a tested thing.\n\n"
            "## Commands\n\n- Run one test with `pytest -k name`.\n\n"
            "## Project Constraints\n\n- `hooks/launcher.cmd` must stay LF-only.\n\n"
            "## Project Map\n\n- `README.md`: durable entrypoint.\n",
        )
        entry = row(doctor.collect(project.root), "AGENTS.md")
        assert entry.status == doctor.WARN
        assert "hooks/launcher.cmd" in entry.detail

    def test_a_path_git_never_tracked_is_not_flagged(self, project) -> None:
        """A branch name looks like a path, and a false alarm is its own distractor."""
        project.write(
            "AGENTS.md",
            "# Agent Guide\n\n"
            "## Project Goal\n\nShip a tested thing.\n\n"
            "## Commands\n\n- Run one test with `pytest -k name`.\n\n"
            "## Project Constraints\n\n- Work happens on `feature/streaming`.\n\n"
            "## Project Map\n\n- `README.md`: durable entrypoint.\n",
        )
        assert row(doctor.collect(project.root), "AGENTS.md").status == doctor.OK

    def test_a_map_naming_a_nested_path_is_accepted(self, project) -> None:
        """Precise pointers beat a top-level census; only staleness is checked."""
        project.write("src/main.py", "x = 1\n")
        project.commit("feat: add main")
        project.guide(map_entries=("README.md", "src/main.py"))
        assert row(doctor.collect(project.root), "AGENTS.md").status == doctor.OK

    def test_an_unmapped_directory_is_not_a_problem(self, project) -> None:
        """A repository overview measurably does not help; completeness is not a goal."""
        project.mkdir("src")
        project.mkdir("scripts")
        project.guide(map_entries=("README.md",))
        assert row(doctor.collect(project.root), "AGENTS.md").status == doctor.OK


class TestBridge:
    def test_missing_bridge(self, project) -> None:
        assert row(doctor.collect(project.root), "CLAUDE.md").status == doctor.MISSING

    def test_bridge_without_the_import_fails(self, project) -> None:
        project.bridge(wired=False)
        entry = row(doctor.collect(project.root), "CLAUDE.md")
        assert entry.status == doctor.FAIL
        assert "never loaded" in entry.detail

    def test_wired_bridge_passes(self, project) -> None:
        project.bridge(wired=True)
        assert row(doctor.collect(project.root), "CLAUDE.md").status == doctor.OK

    def test_oversized_bridge_warns(self, project) -> None:
        project.write("CLAUDE.md", "@AGENTS.md\n" + "\n".join(f"line {i}" for i in range(220)))
        entry = row(doctor.collect(project.root), "CLAUDE.md")
        assert entry.status == doctor.WARN
        assert "200 lines" in entry.detail


class TestNotes:
    def test_memory_within_budget(self, project) -> None:
        project.memory("One open question")
        assert row(doctor.collect(project.root), ".arbor/memory.md").status == doctor.OK

    def test_oversized_memory_warns(self, project) -> None:
        project.memory(*[f"Open question number {i}" for i in range(notes.LINE_BUDGET + 5)])
        entry = row(doctor.collect(project.root), ".arbor/memory.md")
        assert entry.status == doctor.WARN
        assert "budget" in entry.detail

    def test_legacy_entries_are_reported_for_pruning(self, project) -> None:
        project.write(".arbor/memory.md", "# M\n\n## Unresolved\n\n- [hook:resume] stale pointer\n")
        entry = row(doctor.collect(project.root), ".arbor/memory.md")
        assert entry.status == doctor.WARN
        assert "prune" in entry.detail

    def test_undecodable_memory_fails(self, project) -> None:
        (project.root / ".arbor" / "memory.md").write_bytes(b"\xff\xfe\x00")
        assert row(doctor.collect(project.root), ".arbor/memory.md").status == doctor.FAIL

    def test_ideas_count_is_reported(self, project) -> None:
        project.ideas("An idea", "Another")
        assert "2 parked" in row(doctor.collect(project.root), ".arbor/ideas.md").detail


class TestHookReceipts:
    def test_hooks_that_never_ran_are_reported(self, project) -> None:
        rows = doctor.collect(project.root)
        for event in doctor.HOOK_EVENTS:
            entry = row(rows, f"{event} hook")
            assert entry.status == doctor.WARN
            assert "never fired" in entry.detail

    def test_task_capture_reports_which_tool_fired(self, project, tmp_path, monkeypatch) -> None:
        """The receipt key depends on the host's tool, so the row reports the family."""
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "config"))
        directory = tmp_path / "config" / "tasks" / "abc"
        directory.mkdir(parents=True)
        import json as _json

        (directory / "1.json").write_text(
            _json.dumps({"id": "1", "subject": "A", "status": "pending"}), encoding="utf-8"
        )
        hooks.todo_snapshot(project.payload(tool_name="TaskCreate", session_id="abc", tool_input={}))
        entry = row(doctor.collect(project.root), "task capture hook")
        assert entry.status == doctor.OK
        assert "TaskCreate" in entry.detail

    def test_a_fired_hook_reports_when_and_which_version(self, project) -> None:
        hooks.session_start(project.payload(source="startup"))
        entry = row(doctor.collect(project.root), "SessionStart hook")
        assert entry.status == doctor.OK
        assert "last fired" in entry.detail
        assert "plugin" in entry.detail

    def test_all_three_hooks_report_after_a_full_session(self, project) -> None:
        hooks.session_start(project.payload(source="startup"))
        hooks.todo_snapshot(
            project.payload(tool_name="TodoWrite", tool_input={"todos": [{"content": "A", "status": "pending"}]})
        )
        hooks.session_end(project.payload(reason="clear"))
        rows = doctor.collect(project.root)
        for event in doctor.HOOK_EVENTS:
            assert row(rows, f"{event} hook").status == doctor.OK


class TestSessionState:
    def test_absent_state_is_reported(self, project) -> None:
        entry = row(doctor.collect(project.root), ".arbor/session.json")
        assert entry.status == doctor.MISSING

    def test_captured_task_counts_are_reported(self, project) -> None:
        session.snapshot_todos(
            project.root,
            [{"content": "A", "status": "pending"}, {"content": "B", "status": "completed"}],
        )
        entry = row(doctor.collect(project.root), ".arbor/session.json")
        assert entry.status == doctor.OK
        assert "2 captured tasks, 1 unfinished" in entry.detail

    def test_corrupt_state_is_reported_as_rebuildable(self, project) -> None:
        project.write(".arbor/session.json", "{ broken")
        entry = row(doctor.collect(project.root), ".arbor/session.json")
        assert entry.status == doctor.WARN


class TestPacketRow:
    def test_reports_size_against_the_budget(self, project) -> None:
        entry = row(doctor.collect(project.root), "context packet")
        assert entry.status == doctor.OK
        assert "of 9500 chars" in entry.detail


class TestResultAndCli:
    def test_fully_configured_project_is_ok(self, project) -> None:
        init.run(project.root)
        project.guide(map_entries=("README.md",))
        hooks.session_start(project.payload(source="startup"))
        hooks.todo_snapshot(
            project.payload(tool_name="TodoWrite", tool_input={"todos": [{"content": "A", "status": "pending"}]})
        )
        hooks.session_end(project.payload(reason="clear"))
        rows = doctor.collect(project.root)
        assert doctor.result(rows) == doctor.OK, [
            (item.surface, item.status, item.detail) for item in rows if item.status != doctor.OK
        ]

    def test_render_includes_a_result_line(self, project) -> None:
        rendered = doctor.render(project.root, doctor.collect(project.root))
        assert "**Arbor Doctor**" in rendered
        assert "Result:" in rendered

    def test_cli_exit_zero_without_strict(self, project) -> None:
        result = run_cli("doctor", "--root", str(project.root))
        assert result.returncode == 0
        assert "Result: needs_attention" in result.stdout

    def test_cli_strict_exits_nonzero_when_attention_needed(self, project) -> None:
        result = run_cli("doctor", "--root", str(project.root), "--strict")
        assert result.returncode == 1

    def test_cli_never_tracebacks(self, project) -> None:
        project.write(".arbor/session.json", "{ broken")
        (project.root / ".arbor" / "memory.md").write_bytes(b"\xff\xfe")
        result = run_cli("doctor", "--root", str(project.root))
        assert "Traceback" not in result.stdout + result.stderr


class TestOutdatedMemoryAnchors:
    def test_reports_a_deleted_path_named_by_a_note(self, project) -> None:
        project.write("src/parser.py", "x = 1\n")
        project.commit("feat: add parser")
        (project.root / "src" / "parser.py").unlink()
        project.commit("refactor: drop parser")
        project.memory("Finish the rework in `src/parser.py`")
        entry = row(doctor.collect(project.root), ".arbor/memory.md")
        assert entry.status == doctor.WARN
        assert "no longer exist" in entry.detail
        assert "src/parser.py" in entry.detail

    def test_quiet_when_every_named_path_resolves(self, project) -> None:
        project.write("src/parser.py", "x = 1\n")
        project.commit("feat: add parser")
        project.memory("Finish the rework in `src/parser.py`")
        assert row(doctor.collect(project.root), ".arbor/memory.md").status == doctor.OK


class TestConflictedMemory:
    def test_reported_as_fail(self, project) -> None:
        project.write(
            ".arbor/memory.md",
            "# M\n\n## Unresolved\n\n<<<<<<< HEAD\n- Mine\n=======\n- Theirs\n>>>>>>> other\n",
        )
        entry = row(doctor.collect(project.root), ".arbor/memory.md")
        assert entry.status == doctor.FAIL
        assert "merge conflict" in entry.detail
