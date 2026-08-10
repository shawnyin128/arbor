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
        assert notes.read_memory(project.root).texts == ["First open question", "Second one"]

    def test_reads_the_legacy_heading_too(self, project) -> None:
        """Projects initialized by earlier versions used In-flight."""
        project.write(".arbor/memory.md", "# M\n\n## In-flight\n\n- Still open\n")
        assert notes.read_memory(project.root).texts == ["Still open"]

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
        assert result.texts == ["A human note"]
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
        assert notes.read_memory(project.root).texts == ["Mine"]

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
        assert notes.read_memory(project.root).texts == ["Star bullet"]


class TestIdeas:
    def test_reads_parked_entries(self, project) -> None:
        project.write(".arbor/ideas.md", "# I\n\n## Parked\n\n- Try a streaming reader\n- Cache the index\n")
        assert notes.read_ideas(project.root).texts == ["Try a streaming reader", "Cache the index"]

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


class TestMultiLineEntries:
    """Indented lines continue an entry; they are not separate notes."""

    def test_indented_continuation_folds_into_one_entry(self, project) -> None:
        project.write(
            ".arbor/memory.md",
            "# M\n\n## Unresolved\n\n"
            "- Decide whether to keep the adapter\n"
            "  because the parser rewrite may remove the need\n"
            "- Another open question\n",
        )
        result = notes.read_memory(project.root)
        assert len(result.entries) == 2
        assert "parser rewrite" in result.texts[0]

    def test_nested_sub_bullet_is_not_a_separate_entry(self, project) -> None:
        project.write(
            ".arbor/memory.md",
            "# M\n\n## Unresolved\n\n"
            "- Keep the adapter for now\n"
            "  - supersedes: the earlier note about wrappers\n"
            "- Another open question\n",
        )
        result = notes.read_memory(project.root)
        assert len(result.entries) == 2, result.texts
        assert "supersedes" in result.texts[0]


class TestAnchors:
    def test_extracts_backticked_paths(self) -> None:
        assert notes.anchors("see `src/parser.py` and `tests/test_parser.py`") == (
            "src/parser.py",
            "tests/test_parser.py",
        )

    def test_ignores_bare_filenames_as_too_ambiguous(self) -> None:
        assert notes.anchors("check `README.md` again") == ()

    def test_ignores_commands(self) -> None:
        assert notes.anchors("run `git push origin --delete v1.0`") == ()

    def test_ignores_urls(self) -> None:
        assert notes.anchors("see `https://example.invalid/a/b`") == ()

    def test_deduplicates(self) -> None:
        assert notes.anchors("`a/b` then `a/b`") == ("a/b",)


class TestMissingAnchors:
    def test_reports_a_tracked_path_that_was_deleted(self, project) -> None:
        project.write("src/parser.py", "x = 1\n")
        project.commit("feat: add parser")
        (project.root / "src" / "parser.py").unlink()
        project.commit("refactor: drop parser")
        entry = notes.Entry(text="rework `src/parser.py`", anchors=("src/parser.py",))
        assert notes.missing_anchors(project.root, entry) == ["src/parser.py"]

    def test_silent_for_a_path_that_still_exists(self, project) -> None:
        project.write("src/parser.py", "x = 1\n")
        project.commit("feat: add parser")
        entry = notes.Entry(text="rework `src/parser.py`", anchors=("src/parser.py",))
        assert notes.missing_anchors(project.root, entry) == []

    def test_silent_for_a_path_git_never_tracked(self, project) -> None:
        """A branch name or scratch dir contains a slash but is not a path claim."""
        entry = notes.Entry(text="on `codex/some-branch`", anchors=("codex/some-branch",))
        assert notes.missing_anchors(project.root, entry) == []

    def test_silent_outside_a_git_repository(self, make_project) -> None:
        loose = make_project(git=False)
        entry = notes.Entry(text="see `src/gone.py`", anchors=("src/gone.py",))
        assert notes.missing_anchors(loose.root, entry) == []
