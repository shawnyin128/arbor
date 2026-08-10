"""Published-surface contracts.

Earlier versions asserted that a plugin-level hook manifest must *not* exist,
because hooks were registered into each project instead. Shipping them at plugin
level is the central change in this release, so these tests assert the opposite
and additionally assert that the project-registration and cache-discovery layers
are gone rather than merely unused.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from conftest import CLI, LAUNCHER, PLUGIN_ROOT, REPO_ROOT, SCRIPTS_DIR

MANIFEST = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
HOOKS_JSON = PLUGIN_ROOT / "hooks" / "hooks.json"
MARKETPLACE = REPO_ROOT / ".claude-plugin" / "marketplace.json"
SKILL = PLUGIN_ROOT / "skills" / "arbor" / "SKILL.md"
REFERENCES = PLUGIN_ROOT / "skills" / "arbor" / "references"

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def load_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{path} must be a JSON object"
    return data


class TestManifest:
    def test_is_a_json_object_with_a_release_version(self) -> None:
        manifest = load_json(MANIFEST)
        assert manifest["name"] == "arbor"
        assert SEMVER.match(manifest["version"]), manifest["version"]

    def test_version_is_in_the_2_1_line(self) -> None:
        assert load_json(MANIFEST)["version"].startswith("2.1.")

    def test_marketplace_points_at_the_plugin_root(self) -> None:
        entry = load_json(MARKETPLACE)["plugins"][0]
        assert entry["name"] == "arbor"
        assert entry["source"] == "./plugins/arbor"
        assert (REPO_ROOT / "plugins" / "arbor").is_dir()

    def test_plugin_version_is_readable_at_runtime(self) -> None:
        from arbor_core import paths

        assert paths.plugin_version() == load_json(MANIFEST)["version"]


class TestHookRegistration:
    def test_plugin_ships_a_hook_manifest(self) -> None:
        assert HOOKS_JSON.is_file(), "hooks are registered at plugin level in this release"

    def test_registers_exactly_the_three_intended_events(self) -> None:
        hooks = load_json(HOOKS_JSON)["hooks"]
        assert set(hooks) == {"SessionStart", "PostToolUse", "SessionEnd"}

    def test_stop_hook_is_not_registered(self) -> None:
        """Stop fired once per turn, which churned state and could mask the reply."""
        assert "Stop" not in load_json(HOOKS_JSON)["hooks"]

    def test_session_start_matches_every_context_losing_source(self) -> None:
        entry = load_json(HOOKS_JSON)["hooks"]["SessionStart"][0]
        assert set(entry["matcher"].split("|")) == {"startup", "resume", "clear", "compact"}

    def test_todo_capture_is_scoped_to_the_todo_tool(self) -> None:
        entry = load_json(HOOKS_JSON)["hooks"]["PostToolUse"][0]
        assert entry["matcher"] == "TodoWrite"

    @pytest.mark.parametrize("event", ["SessionStart", "PostToolUse", "SessionEnd"])
    def test_commands_resolve_through_the_plugin_root_variable(self, event: str) -> None:
        for group in load_json(HOOKS_JSON)["hooks"][event]:
            for hook in group["hooks"]:
                assert hook["type"] == "command"
                assert "${CLAUDE_PLUGIN_ROOT}" in hook["command"], (
                    "resolving the plugin path is the host's job, not a cache search"
                )
                assert "arbor-hook.cmd" in hook["command"]
                assert hook["timeout"] > 0

    def test_every_registered_event_maps_to_a_real_entrypoint(self) -> None:
        from arbor_core import hooks as hooks_module

        commands = [
            hook["command"]
            for groups in load_json(HOOKS_JSON)["hooks"].values()
            for group in groups
            for hook in group["hooks"]
        ]
        used = {command.rsplit(" ", 1)[-1].strip('"') for command in commands}
        assert used == set(hooks_module.ENTRYPOINTS)


class TestLayout:
    def test_launcher_is_present(self) -> None:
        assert LAUNCHER.is_file()

    def test_cli_and_package_are_present(self) -> None:
        assert CLI.is_file()
        assert (SCRIPTS_DIR / "arbor_core" / "__init__.py").is_file()

    def test_only_the_arbor_skill_is_published(self) -> None:
        skills = sorted(
            path.parent.name
            for path in (PLUGIN_ROOT / "skills").rglob("SKILL.md")
        )
        assert skills == ["arbor"]

    def test_every_template_init_needs_is_shipped(self) -> None:
        from arbor_core import init as init_module

        for name in init_module.TEMPLATES.values():
            assert (REFERENCES / name).is_file(), name

    def test_no_orphaned_reference_templates(self) -> None:
        from arbor_core import init as init_module

        shipped = {path.name for path in REFERENCES.glob("*.md")}
        assert shipped == set(init_module.TEMPLATES.values())

    def test_line_endings_are_pinned_for_the_launcher(self) -> None:
        attributes = (REPO_ROOT / ".gitattributes").read_text(encoding="utf-8")
        assert "arbor-hook.cmd text eol=lf" in attributes


class TestCodexRemoval:
    """This release is Claude Code only; the Codex surfaces are gone, not idle."""

    @pytest.mark.parametrize(
        "relative",
        [
            "plugins/arbor/.codex-plugin",
            ".agents",
            "plugins/arbor/skills/arbor/agents",
            "plugins/arbor/hooks/session-start",
            "plugins/arbor/hooks/stop-memory-hygiene",
        ],
    )
    def test_codex_surface_is_absent(self, relative: str) -> None:
        assert not (REPO_ROOT / relative).exists(), relative

    @pytest.mark.parametrize(
        "name",
        [
            "register_project_hooks.py",
            "diagnose_project_hooks.py",
            "check_install_state.py",
            "sync_local_plugin_cache.py",
            "check_project_wrapper_smoke.py",
            "check_runtime_smoke_evidence.py",
            "check_release_readiness.py",
            "check_quality_gate.py",
            "check_plugin_adapters.py",
            "run_framework_check.py",
            "collect_project_context.py",
            "arbor_project_state.py",
        ],
    )
    def test_retired_script_is_absent(self, name: str) -> None:
        assert not (SCRIPTS_DIR / name).exists(), name

    def test_no_published_file_mentions_codex(self) -> None:
        offenders = []
        for path in PLUGIN_ROOT.rglob("*"):
            if not path.is_file() or path.suffix not in {".md", ".json", ".py", ".cmd"}:
                continue
            if "codex" in path.read_text(encoding="utf-8", errors="replace").lower():
                offenders.append(path.relative_to(REPO_ROOT).as_posix())
        assert offenders == []


class TestSkillDocument:
    def test_declares_a_stable_invocation_name(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        assert text.startswith("---")
        assert re.search(r"(?m)^name: arbor$", text)

    def test_description_states_when_not_to_use_it(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        header = text.split("---")[1]
        assert "Not for" in header

    def test_stays_short_enough_to_be_read(self) -> None:
        lines = len(SKILL.read_text(encoding="utf-8").splitlines())
        assert lines < 140, f"SKILL.md grew to {lines} lines"

    def test_documents_every_cli_command(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        for command in ("init", "doctor", "context"):
            assert f"arbor.py {command}" in text


class TestSourceHygiene:
    def _sources(self) -> list[Path]:
        return [CLI, *sorted((SCRIPTS_DIR / "arbor_core").glob("*.py"))]

    def test_all_sources_parse(self) -> None:
        import ast

        for path in self._sources():
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    def test_no_trailing_whitespace(self) -> None:
        for path in self._sources():
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                assert line == line.rstrip(), f"{path.name}:{number}"

    def test_entry_script_suppresses_bytecode_before_importing(self) -> None:
        """A plugin must not leave __pycache__ inside its installed directory."""
        text = CLI.read_text(encoding="utf-8")
        assert text.index("sys.dont_write_bytecode = True") < text.index("from arbor_core")
