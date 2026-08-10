"""Context packet contracts.

Two properties matter most here. Hook output above roughly 10,000 characters is
discarded by the host without warning, so the packet must stay inside its budget
under every input. And injected context that changes while the project does not
would invalidate the prompt prefix cache every session, so the packet must carry
no wall-clock value.
"""

from __future__ import annotations

import re

import pytest
from arbor_core import hooks, packet, session

ISO_CLOCK = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")


def build(project) -> str:
    rendered, _ = packet.build(project.root)
    return rendered


def add_todos(project, *specs: tuple[str, str]) -> None:
    todos = [{"content": content, "status": status} for content, status in specs]
    hooks.todo_snapshot(project.payload(tool_name="TodoWrite", tool_input={"todos": todos}))


class TestStructure:
    def test_starts_with_the_header_and_protocol(self, project) -> None:
        rendered = build(project)
        assert rendered.startswith("# Arbor Session Context")
        assert "not as a reason to invoke planning, review, or workflow tools" in rendered

    def test_sections_appear_in_priority_order(self, project) -> None:
        project.bridge()
        project.memory("Decide whether to split the parser")
        project.ideas("Try a streaming reader")
        project.write("dirty.txt", "x\n")
        add_todos(project, ("Do a thing", "in_progress"))
        rendered = build(project)
        order = [
            rendered.index("## Position"),
            rendered.index("## In flight"),
            rendered.index("## Unresolved"),
            rendered.index("## Working tree"),
            rendered.index("## Parked ideas"),
            rendered.index("## Recent commits"),
        ]
        assert order == sorted(order)

    def test_empty_sections_are_omitted_entirely(self, project) -> None:
        project.bridge()
        project.commit("chore: add bridge")
        rendered = build(project)
        assert "## In flight" not in rendered
        assert "## Unresolved" not in rendered
        assert "## Parked ideas" not in rendered
        assert "## Working tree" not in rendered

    def test_omits_git_sections_outside_a_repository(self, make_project) -> None:
        loose = make_project(git=False)
        rendered = build(loose)
        assert "## Position" not in rendered
        assert "## Recent commits" not in rendered

    def test_carries_no_wall_clock_value(self, project) -> None:
        """A clock in injected context busts the prompt prefix cache for nothing."""
        project.bridge()
        project.memory("Something unresolved")
        add_todos(project, ("Task", "pending"))
        assert not ISO_CLOCK.search(build(project))


class TestGuideWiring:
    def test_warns_when_the_bridge_is_missing(self, project) -> None:
        assert "does not import `AGENTS.md`" in build(project)

    def test_quiet_when_the_bridge_imports_the_guide(self, project) -> None:
        project.bridge(wired=True)
        assert "does not import `AGENTS.md`" not in build(project)

    def test_backticked_import_does_not_count(self, project) -> None:
        # Claude Code skips imports inside code spans, so neither may Arbor.
        project.write("CLAUDE.md", "# Guide\n\nMention `@AGENTS.md` without importing it.\n")
        assert "does not import `AGENTS.md`" in build(project)


class TestTodoRendering:
    def test_lists_in_progress_before_pending(self, project) -> None:
        add_todos(project, ("Later", "pending"), ("Now", "in_progress"))
        rendered = build(project)
        assert rendered.index("[>] Now") < rendered.index("[ ] Later")

    def test_summarizes_counts(self, project) -> None:
        add_todos(project, ("A", "completed"), ("B", "completed"), ("C", "pending"))
        assert "1 unfinished, 2 done" in build(project)

    def test_reports_when_everything_was_finished(self, project) -> None:
        add_todos(project, ("A", "completed"))
        assert "every captured task was completed" in build(project)

    def test_caps_the_listed_items(self, project) -> None:
        add_todos(project, *[(f"Task {index}", "pending") for index in range(packet.MAX_TODOS + 5)])
        rendered = build(project)
        assert f"(+5 more)" in rendered

    def test_flags_a_snapshot_taken_before_the_latest_commit(self, project) -> None:
        add_todos(project, ("Older work", "pending"))
        project.write("later.txt", "x\n")
        project.commit("feat: move ahead")
        assert "captured before the latest commit" in build(project)

    def test_no_staleness_note_when_head_matches(self, project) -> None:
        add_todos(project, ("Current work", "pending"))
        assert "captured before the latest commit" not in build(project)


class TestNotesRendering:
    def test_renders_unresolved_entries(self, project) -> None:
        project.memory("Undecided: whether to keep the adapter")
        assert "- Undecided: whether to keep the adapter" in build(project)

    def test_reports_damaged_memory_rather_than_treating_it_as_context(self, project) -> None:
        (project.root / ".arbor" / "memory.md").write_bytes(b"\xff\xfe\x00broken")
        rendered = build(project)
        assert "damaged" in rendered

    def test_counts_ignored_legacy_hook_entries(self, project) -> None:
        project.write(
            ".arbor/memory.md",
            "# Session Memory\n\n## In-flight\n\n"
            "- [hook:resume] Discussion: something. Next: resume.\n"
            "- A real human note\n",
        )
        rendered = build(project)
        assert "- A real human note" in rendered
        assert "1 legacy hook-written entry ignored" in rendered

    def test_shows_most_recent_ideas_first(self, project) -> None:
        project.ideas(*[f"Idea {index}" for index in range(packet.MAX_IDEAS + 1)])
        rendered = build(project)
        assert f"{packet.MAX_IDEAS + 1} parked" in rendered
        assert rendered.index("Idea 3") < rendered.index("Idea 2")
        assert "Idea 0" not in rendered, "only the most recent ideas are shown"


class TestWorkingTree:
    def test_lists_changed_paths_with_status_codes(self, project) -> None:
        project.write("added.txt", "x\n")
        rendered = build(project)
        assert "1 changed path" in rendered
        assert "?? added.txt" in rendered

    def test_caps_listed_paths(self, project) -> None:
        for index in range(packet.MAX_TREE_ENTRIES + 4):
            project.write(f"file{index}.txt", "x\n")
        assert "(+4 more)" in build(project)


class TestBudget:
    def _load_project(self, project) -> None:
        project.bridge()
        project.memory(*[f"Unresolved item number {index} with plenty of text" for index in range(60)])
        project.ideas(*[f"Parked idea number {index} with plenty of text" for index in range(40)])
        add_todos(project, *[(f"Task number {index} with a long description", "pending") for index in range(40)])
        for index in range(40):
            project.write(f"noise{index}.txt", "x\n")

    def test_never_exceeds_the_budget(self, project) -> None:
        self._load_project(project)
        for limit in (9500, 4000, 2000, 1000, 800, 500, 200, 10):
            rendered = packet.render(project.root, packet.build_sections(project.root), limit)
            assert len(rendered) <= limit, f"packet exceeded limit {limit}"

    def test_drops_lowest_priority_sections_first(self, project) -> None:
        self._load_project(project)
        sections = packet.build_sections(project.root)
        rendered = packet.render(project.root, sections, 2600)
        dropped = {section.key for section in sections if section.dropped}
        assert "commits" in dropped
        assert "todos" not in dropped, "in-flight state must outlive low-priority sections"
        assert "position" not in dropped

    def test_dropped_sections_state_how_to_recover_them(self, project) -> None:
        self._load_project(project)
        sections = packet.build_sections(project.root)
        rendered = packet.render(project.root, sections, 2600)
        assert "omitted for context budget" in rendered
        assert "git log" in rendered

    def test_protocol_is_the_last_thing_dropped(self, project) -> None:
        self._load_project(project)
        rendered = packet.render(project.root, packet.build_sections(project.root), 900)
        assert rendered.startswith("# Arbor Session Context")
        assert "## Recent commits" not in rendered or "omitted" in rendered

    def test_emits_nothing_when_even_the_protocol_does_not_fit(self, project) -> None:
        self._load_project(project)
        assert packet.render(project.root, packet.build_sections(project.root), 50) == ""

    def test_hook_skips_rather_than_emitting_a_partial_protocol(self, project, monkeypatch) -> None:
        monkeypatch.setenv("ARBOR_CONTEXT_BUDGET", "50")
        assert hooks.session_start(project.payload(source="startup")) == hooks.SKIP

    def test_budget_is_configurable(self, project, monkeypatch) -> None:
        monkeypatch.setenv("ARBOR_CONTEXT_BUDGET", "777")
        assert packet.budget() == 777

    @pytest.mark.parametrize("value", ["0", "-5", "abc", ""])
    def test_invalid_budget_falls_back_to_the_default(self, project, monkeypatch, value: str) -> None:
        monkeypatch.setenv("ARBOR_CONTEXT_BUDGET", value)
        assert packet.budget() == packet.DEFAULT_BUDGET

    def test_hook_output_stays_within_the_host_limit(self, project) -> None:
        """The whole JSON envelope, not just the packet, must fit the host cap."""
        self._load_project(project)
        _code, output = hooks.session_start(project.payload(source="startup"))
        assert len(output) < 10000


class TestReceipt:
    def test_names_loaded_sections(self, project) -> None:
        project.bridge()
        add_todos(project, ("A task", "pending"))
        _rendered, receipt = packet.build(project.root)
        assert "in flight" in receipt
        assert "chars" in receipt

    def test_names_omitted_sections(self, project) -> None:
        project.bridge()
        project.memory(*[f"Unresolved item {index} with text" for index in range(60)])
        sections = packet.build_sections(project.root)
        packet.render(project.root, sections, 1200)
        receipt = packet.summary(sections, 1200)
        assert "omitted" in receipt
