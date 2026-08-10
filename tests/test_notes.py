"""Agent-written notes parsing contracts."""

from __future__ import annotations

import pytest
from arbor_core import notes


class TestMemory:
    def test_missing_file(self, project) -> None:
        result = notes.read_memory(project.root)
        assert not result.exists
        assert result.entries == []

    def test_reads_entries_under_the_canonical_heading(self, project) -> None:
        project.write(".arbor/memory.md", "# M\n\n## Unresolved\n\n- First open question\n- Second one\n")
        assert notes.read_memory(project.root).entries == ["First open question", "Second one"]

    def test_reads_the_legacy_heading_too(self, project) -> None:
        """Projects initialized by earlier versions used In-flight."""
        project.write(".arbor/memory.md", "# M\n\n## In-flight\n\n- Still open\n")
        assert notes.read_memory(project.root).entries == ["Still open"]

    @pytest.mark.parametrize(
        "line",
        [
            "None.",
            "none",
            "N/A",
            "No unresolved decisions recorded yet.",
            "No pending uncommitted context recorded yet.",
            "No active Arbor resume context recorded yet.",
        ],
    )
    def test_placeholders_are_not_content(self, project, line: str) -> None:
        project.write(".arbor/memory.md", f"# M\n\n## Unresolved\n\n- {line}\n")
        result = notes.read_memory(project.root)
        assert result.entries == []
        assert not result.has_content

    def test_legacy_hook_entries_are_reported_as_stale(self, project) -> None:
        project.write(
            ".arbor/memory.md",
            "# M\n\n## Unresolved\n\n- [hook:resume] Discussion: x. Next: y.\n"
            "- [hook:fallback] something\n- A human note\n",
        )
        result = notes.read_memory(project.root)
        assert result.entries == ["A human note"]
        assert len(result.stale) == 2

    def test_missing_section_yields_no_entries(self, project) -> None:
        project.write(".arbor/memory.md", "# M\n\nSome prose with no section heading.\n")
        result = notes.read_memory(project.root)
        assert result.exists
        assert result.entries == []

    def test_content_after_the_section_is_not_included(self, project) -> None:
        project.write(
            ".arbor/memory.md",
            "# M\n\n## Unresolved\n\n- Mine\n\n## Archive\n\n- Not mine\n",
        )
        assert notes.read_memory(project.root).entries == ["Mine"]

    def test_undecodable_file_is_reported_unreadable(self, project) -> None:
        (project.root / ".arbor").mkdir(exist_ok=True)
        (project.root / ".arbor" / "memory.md").write_bytes(b"\xff\xfe\x00bad")
        result = notes.read_memory(project.root)
        assert result.exists
        assert not result.readable
        assert result.entries == []

    def test_counts_lines_for_the_size_budget(self, project) -> None:
        project.write(".arbor/memory.md", "# M\n\n## Unresolved\n\n" + "".join(f"- item {i}\n" for i in range(30)))
        assert notes.read_memory(project.root).line_count > 30

    def test_asterisk_bullets_are_accepted(self, project) -> None:
        project.write(".arbor/memory.md", "# M\n\n## Unresolved\n\n* Star bullet\n")
        assert notes.read_memory(project.root).entries == ["Star bullet"]


class TestIdeas:
    def test_reads_parked_entries(self, project) -> None:
        project.write(".arbor/ideas.md", "# I\n\n## Parked\n\n- Try a streaming reader\n- Cache the index\n")
        assert notes.read_ideas(project.root).entries == ["Try a streaming reader", "Cache the index"]

    def test_placeholder_is_not_content(self, project) -> None:
        project.write(".arbor/ideas.md", "# I\n\n## Parked\n\n- No parked ideas recorded yet.\n")
        assert notes.read_ideas(project.root).entries == []

    def test_missing_file(self, project) -> None:
        assert not notes.read_ideas(project.root).exists


class TestTemplatesParseAsEmpty:
    """A freshly initialized project must contain no live entries."""

    def test_shipped_templates_contain_only_placeholders(self, project) -> None:
        from arbor_core import init

        init.run(project.root)
        assert notes.read_memory(project.root).entries == []
        assert notes.read_ideas(project.root).entries == []
