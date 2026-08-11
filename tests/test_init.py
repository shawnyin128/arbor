"""Initialization contracts.

Initialization is additive. The property worth locking hardest is that running it
against a project someone already customized changes nothing they wrote.
"""

from __future__ import annotations

import pytest
from arbor_core import init, packet
from conftest import run_cli


def statuses(actions) -> dict[str, str]:
    return {action.path: action.status for action in actions}


class TestFreshProject:
    def test_creates_every_surface(self, make_project) -> None:
        plain = make_project(arbor=False)
        result = statuses(init.run(plain.root))
        assert result[".arbor"] == "created"
        assert result["AGENTS.md"] == "created"
        assert result["CLAUDE.md"] == "created"
        assert result[".arbor/memory.md"] == "created"
        assert result[".arbor/ideas.md"] == "created"
        assert result[".arbor/.gitignore"] == "created"

    def test_bridge_imports_the_guide(self, make_project) -> None:
        plain = make_project(arbor=False)
        init.run(plain.root)
        assert packet.guide_is_wired(plain.root)

    def test_new_bridge_carries_the_header_init_mandates(self, make_project) -> None:
        """A user who initializes with Arbor will not run `/init`, whose header this is."""
        plain = make_project(arbor=False)
        init.run(plain.root)
        text = (plain.root / "CLAUDE.md").read_text(encoding="utf-8")
        assert text.startswith("# CLAUDE.md\n")
        assert "guidance to Claude Code (claude.ai/code)" in text

    def test_the_scaffolded_guide_asks_for_a_single_test_command(self, make_project) -> None:
        """`/init` calls this out specifically, and it is the one agents need most."""
        plain = make_project(arbor=False)
        init.run(plain.root)
        text = (plain.root / "AGENTS.md").read_text(encoding="utf-8")
        assert "## Commands" in text
        assert "single" in text

    def test_the_scaffolded_guide_repeats_the_refusals_init_makes(self, make_project) -> None:
        plain = make_project(arbor=False)
        init.run(plain.root)
        text = (plain.root / "AGENTS.md").read_text(encoding="utf-8").lower()
        for refusal in ("do not repeat yourself", "easily discovered", "generic development"):
            assert refusal in text, refusal

    def test_machine_state_is_kept_out_of_review(self, make_project) -> None:
        plain = make_project(arbor=False)
        init.run(plain.root)
        assert "session.json" in (plain.root / ".arbor" / ".gitignore").read_text(encoding="utf-8")

    def test_generated_files_use_lf_endings(self, make_project) -> None:
        plain = make_project(arbor=False)
        init.run(plain.root)
        for relative in ("AGENTS.md", "CLAUDE.md", ".arbor/memory.md", ".arbor/ideas.md"):
            assert b"\r\n" not in (plain.root / relative).read_bytes(), relative


class TestIdempotence:
    def test_second_run_reports_everything_as_existing(self, make_project) -> None:
        plain = make_project(arbor=False)
        init.run(plain.root)
        second = statuses(init.run(plain.root))
        assert set(second.values()) == {"exists"}

    def test_second_run_leaves_files_byte_identical(self, make_project) -> None:
        plain = make_project(arbor=False)
        init.run(plain.root)
        tracked = ("AGENTS.md", "CLAUDE.md", ".arbor/memory.md", ".arbor/ideas.md", ".arbor/.gitignore")
        before = {name: (plain.root / name).read_bytes() for name in tracked}
        init.run(plain.root)
        after = {name: (plain.root / name).read_bytes() for name in tracked}
        assert before == after


class TestPreservesUserContent:
    def test_existing_guide_is_untouched(self, project) -> None:
        original = project.write("AGENTS.md", "# My Guide\n\nMy own words.\n").read_bytes()
        init.run(project.root)
        assert (project.root / "AGENTS.md").read_bytes() == original

    def test_existing_memory_is_untouched(self, project) -> None:
        original = project.memory("Something I wrote").read_bytes()
        init.run(project.root)
        assert (project.root / ".arbor" / "memory.md").read_bytes() == original

    def test_existing_bridge_keeps_its_content_and_gains_the_import(self, project) -> None:
        project.write("CLAUDE.md", "# Mine\n\nRule one.\nRule two.\n")
        action = [item for item in init.run(project.root) if item.path == "CLAUDE.md"][0]
        assert action.status == "updated"
        text = (project.root / "CLAUDE.md").read_text(encoding="utf-8")
        assert "Rule one." in text
        assert "Rule two." in text
        assert packet.guide_is_wired(project.root)

    def test_import_is_not_appended_twice(self, project) -> None:
        project.bridge(wired=True)
        init.run(project.root)
        init.run(project.root)
        text = (project.root / "CLAUDE.md").read_text(encoding="utf-8")
        assert text.count("@AGENTS.md") == 1

    def test_bridge_already_wired_reports_exists(self, project) -> None:
        project.bridge(wired=True)
        action = [item for item in init.run(project.root) if item.path == "CLAUDE.md"][0]
        assert action.status == "exists"


class TestDryRun:
    def test_creates_nothing(self, make_project) -> None:
        plain = make_project(arbor=False)
        actions = init.run(plain.root, dry_run=True)
        assert all(action.status.startswith("would_") for action in actions)
        assert not (plain.root / ".arbor").exists()
        assert not (plain.root / "AGENTS.md").exists()

    def test_reports_the_bridge_update_without_writing(self, project) -> None:
        original = project.write("CLAUDE.md", "# Mine\n").read_bytes()
        actions = init.run(project.root, dry_run=True)
        assert statuses(actions)["CLAUDE.md"] == "would_update"
        assert (project.root / "CLAUDE.md").read_bytes() == original


class TestFailureModes:
    def test_missing_root_raises_a_clean_error(self, tmp_path) -> None:
        with pytest.raises(init.InitError, match="does not exist"):
            init.run(tmp_path / "absent")

    def test_directory_where_a_file_belongs_raises_a_clean_error(self, project) -> None:
        (project.root / "AGENTS.md").mkdir()
        with pytest.raises(init.InitError, match="directory exists"):
            init.run(project.root)

    def test_cli_reports_errors_without_a_traceback(self, tmp_path) -> None:
        result = run_cli("init", "--root", str(tmp_path / "absent"))
        assert result.returncode == 2
        assert "Traceback" not in result.stderr
        assert "arbor init:" in result.stderr


class TestCli:
    def test_init_then_doctor_reports_a_wired_project(self, make_project) -> None:
        plain = make_project(arbor=False)
        assert run_cli("init", "--root", str(plain.root)).returncode == 0
        result = run_cli("doctor", "--root", str(plain.root))
        assert result.returncode == 0
        assert "imports @AGENTS.md" in result.stdout
