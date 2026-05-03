from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "arbor" / "scripts"
EVAL_SCRIPTS = ROOT / "scripts"
PLUGIN_ROOT = ROOT / "plugins" / "arbor"
SCENARIO_MARKDOWN = ROOT / "docs" / "reviews" / "hook-trigger-scenarios.md"
SCENARIO_SIDECAR = ROOT / "docs" / "reviews" / "hook-trigger-scenarios.json"
ARBOR_HOOK_IDS = {
    "arbor.session_startup_context",
    "arbor.in_session_memory_hygiene",
    "arbor.goal_constraint_drift",
}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


init_script = load_module("init_project_memory", SCRIPTS / "init_project_memory.py")
collect_script = load_module("collect_project_context", SCRIPTS / "collect_project_context.py")
hooks_script = load_module("register_project_hooks", SCRIPTS / "register_project_hooks.py")
startup_hook_script = load_module("run_session_startup_hook", SCRIPTS / "run_session_startup_hook.py")
memory_hook_script = load_module("run_memory_hygiene_hook", SCRIPTS / "run_memory_hygiene_hook.py")
agents_drift_hook_script = load_module("run_agents_guide_drift_hook", SCRIPTS / "run_agents_guide_drift_hook.py")
fixture_script = load_module("eval_fixtures", EVAL_SCRIPTS / "eval_fixtures.py")
dispatcher_script = load_module("simulated_dispatcher", EVAL_SCRIPTS / "simulated_dispatcher.py")
harness_script = load_module("evaluate_hook_triggers", EVAL_SCRIPTS / "evaluate_hook_triggers.py")


def configure_git_repo(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)


def commit_file(root: Path, name: str, content: str, message: str) -> None:
    tracked = root / name
    tracked.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", name], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", message], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def registered_startup_hook_command(root: Path, *extra_args: str) -> list[str]:
    hooks_script.register_project_hooks(root)
    data = json.loads((root / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    hook = next(item for item in data["hooks"] if item["id"] == "arbor.session_startup_context" and item["owner"] == "arbor")
    entrypoint = hook["entrypoint"]
    args = [str(root) if arg == "${PROJECT_ROOT}" else arg for arg in entrypoint["args"]]
    return [sys.executable, str(ROOT / "skills" / "arbor" / entrypoint["script"]), *args, *extra_args]


def registered_memory_hook_command(root: Path, *extra_args: str) -> list[str]:
    hooks_script.register_project_hooks(root)
    data = json.loads((root / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    hook = next(item for item in data["hooks"] if item["id"] == "arbor.in_session_memory_hygiene" and item["owner"] == "arbor")
    entrypoint = hook["entrypoint"]
    args = [str(root) if arg == "${PROJECT_ROOT}" else arg for arg in entrypoint["args"]]
    return [sys.executable, str(ROOT / "skills" / "arbor" / entrypoint["script"]), *args, *extra_args]


def registered_agents_drift_hook_command(root: Path, *extra_args: str) -> list[str]:
    hooks_script.register_project_hooks(root)
    data = json.loads((root / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    hook = next(item for item in data["hooks"] if item["id"] == "arbor.goal_constraint_drift" and item["owner"] == "arbor")
    entrypoint = hook["entrypoint"]
    args = [str(root) if arg == "${PROJECT_ROOT}" else arg for arg in entrypoint["args"]]
    return [sys.executable, str(ROOT / "skills" / "arbor" / entrypoint["script"]), *args, *extra_args]


def parse_trigger_scenario_markdown() -> dict[str, dict[str, str]]:
    scenarios: dict[str, dict[str, str]] = {}
    row_pattern = re.compile(r"^\| ([A-Z0-9]+-P\d{3}) \| (.*?) \| (H1|H2|H3|NONE|MULTI) \| (.*?) \|$")
    for line in SCENARIO_MARKDOWN.read_text(encoding="utf-8").splitlines():
        match = row_pattern.match(line)
        if not match:
            continue
        scenario_id, expression, expected, note = match.groups()
        if expression.startswith('"') and expression.endswith('"'):
            expression = expression[1:-1]
        scenarios[scenario_id] = {
            "expression": expression,
            "expected": expected,
            "note": note,
        }
    return scenarios


def load_trigger_sidecar() -> dict:
    return json.loads(SCENARIO_SIDECAR.read_text(encoding="utf-8"))


def expanded_trigger_expectation(sidecar: dict, scenario_id: str, expected: str) -> dict:
    expectation = dict(sidecar["default_expectations"][expected])
    expectation.update(sidecar.get("overrides", {}).get(scenario_id, {}))
    return expectation


class ProjectMemoryInitializerTests(unittest.TestCase):
    def test_initializes_memory_and_agents_in_empty_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            actions = init_script.init_project_memory(root)

            self.assertEqual([action.status for action in actions], ["created", "created"])
            self.assertTrue((root / ".codex" / "memory.md").exists())
            self.assertTrue((root / "AGENTS.md").exists())
            memory = (root / ".codex" / "memory.md").read_text()
            self.assertIn("# Session Memory", memory)
            self.assertIn("## Observations", memory)
            self.assertIn("## In-flight", memory)
            self.assertIn("## Project Map", (root / "AGENTS.md").read_text())

    def test_preserves_existing_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".codex").mkdir()
            (root / ".codex" / "memory.md").write_text("custom memory", encoding="utf-8")
            (root / "AGENTS.md").write_text("custom agents", encoding="utf-8")

            actions = init_script.init_project_memory(root)

            self.assertEqual([action.status for action in actions], ["exists", "exists"])
            self.assertEqual((root / ".codex" / "memory.md").read_text(), "custom memory")
            self.assertEqual((root / "AGENTS.md").read_text(), "custom agents")

    def test_dry_run_does_not_write_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            actions = init_script.init_project_memory(root, dry_run=True)

            self.assertEqual([action.status for action in actions], ["would_create", "would_create"])
            self.assertFalse((root / ".codex" / "memory.md").exists())
            self.assertFalse((root / "AGENTS.md").exists())

    def test_codex_path_conflict_raises_controlled_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".codex").write_text("not a directory", encoding="utf-8")

            with self.assertRaisesRegex(init_script.InitError, "parent path is not a directory"):
                init_script.init_project_memory(root)

    def test_agents_directory_conflict_raises_controlled_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").mkdir()

            with self.assertRaisesRegex(init_script.InitError, "expected a file but found a directory"):
                init_script.init_project_memory(root)

    def test_codex_path_conflict_cli_has_no_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".codex").write_text("not a directory", encoding="utf-8")

            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "init_project_memory.py"),
                    "--root",
                    str(root),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("parent path is not a directory", proc.stderr)
            self.assertNotIn("Traceback", proc.stderr)


class ProjectMemoryStartupContextTests(unittest.TestCase):
    def test_collects_context_in_required_order_for_non_git_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_script.init_project_memory(root)

            sections = collect_script.collect_startup_context(root)

            self.assertEqual(
                [section.title for section in sections],
                ["1. AGENTS.md", "2. formatted git log", "3. .codex/memory.md", "4. git status"],
            )
            self.assertEqual(
                [section.status for section in sections],
                ["ok", "git-error", "ok", "git-error"],
            )
            self.assertIn("Project Goal", sections[0].body)
            self.assertIn("Session Memory", sections[2].body)
            self.assertIn("[git exited", sections[1].body)
            self.assertIn("[git exited", sections[3].body)

    def test_collects_git_log_and_status_without_default_count_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            configure_git_repo(root)
            init_script.init_project_memory(root)

            for index in range(2):
                commit_file(root, f"file-{index}.txt", f"content {index}", f"commit {index}")

            (root / "uncommitted.txt").write_text("pending", encoding="utf-8")

            sections = collect_script.collect_startup_context(root)
            rendered = collect_script.render_context(sections)

            self.assertIn("commit 0", sections[1].body)
            self.assertIn("commit 1", sections[1].body)
            self.assertIn("?? uncommitted.txt", sections[3].body)
            self.assertEqual(sections[1].status, "ok")
            self.assertEqual(sections[3].status, "ok")
            self.assertLess(rendered.index("## 1. AGENTS.md"), rendered.index("## 2. formatted git log"))
            self.assertLess(rendered.index("## 2. formatted git log"), rendered.index("## 3. .codex/memory.md"))
            self.assertLess(rendered.index("## 3. .codex/memory.md"), rendered.index("## 4. git status"))
            self.assertIn("Status: ok", rendered)
            self.assertIn("Source: git log", rendered)

    def test_missing_files_are_classified_without_blocking_git_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            configure_git_repo(root)

            sections = collect_script.collect_startup_context(root)

            self.assertEqual(sections[0].status, "missing")
            self.assertEqual(sections[2].status, "missing")
            self.assertIn("Missing:", sections[0].body)
            self.assertEqual(sections[3].status, "empty")

    def test_file_path_conflicts_are_classified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").mkdir()
            (root / ".codex").mkdir()
            (root / ".codex" / "memory.md").mkdir()

            sections = collect_script.collect_startup_context(root)

            self.assertEqual(sections[0].status, "path-conflict")
            self.assertEqual(sections[2].status, "path-conflict")
            self.assertIn("Expected a file but found a directory", sections[0].body)
            self.assertIn("Expected a file but found a directory", sections[2].body)

    def test_file_read_errors_are_classified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("agent guide", encoding="utf-8")

            with mock.patch.object(Path, "read_text", side_effect=PermissionError("denied")):
                section = collect_script.read_file_section("1. AGENTS.md", root / "AGENTS.md")

            self.assertEqual(section.status, "read-error")
            self.assertIn("Could not read", section.body)
            self.assertIn("denied", section.detail)

    def test_empty_file_body_is_preserved_as_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "AGENTS.md"
            path.write_text("", encoding="utf-8")

            section = collect_script.read_file_section("1. AGENTS.md", path)
            rendered = collect_script.render_context([section])

            self.assertEqual(section.status, "empty")
            self.assertEqual(section.body, "")
            self.assertIn("Status: empty", rendered)
            self.assertNotIn("(empty)", rendered)

    def test_empty_file_and_literal_empty_marker_are_distinct(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            empty_path = root / "empty.md"
            literal_path = root / "literal.md"
            empty_path.write_text("", encoding="utf-8")
            literal_path.write_text("(empty)", encoding="utf-8")

            empty_section = collect_script.read_file_section("empty", empty_path)
            literal_section = collect_script.read_file_section("literal", literal_path)

            self.assertEqual(empty_section.status, "empty")
            self.assertEqual(empty_section.body, "")
            self.assertEqual(literal_section.status, "ok")
            self.assertEqual(literal_section.body, "(empty)")

    def test_large_file_content_is_not_truncated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lines = [f"line {index}" for index in range(300)]
            (root / "AGENTS.md").write_text("\n".join(lines), encoding="utf-8")

            section = collect_script.read_file_section("1. AGENTS.md", root / "AGENTS.md")

            self.assertEqual(section.status, "ok")
            self.assertIn("line 0", section.body)
            self.assertIn("line 299", section.body)

    def test_agent_selected_git_log_depth_is_respected_without_defaulting_to_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            configure_git_repo(root)
            init_script.init_project_memory(root)

            for index in range(3):
                commit_file(root, f"file-{index}.txt", f"content {index}", f"commit {index}")

            default_sections = collect_script.collect_startup_context(root)
            limited_sections = collect_script.collect_startup_context(root, ["--oneline", "--max-count=1"])

            self.assertIn("commit 0", default_sections[1].body)
            self.assertIn("commit 1", default_sections[1].body)
            self.assertIn("commit 2", default_sections[1].body)
            self.assertEqual(limited_sections[1].body.count("commit"), 1)

    def test_agent_selected_git_log_args_are_respected(self) -> None:
        args = collect_script.parse_git_log_args("--oneline --decorate")
        self.assertEqual(args, ["--oneline", "--decorate"])

    def test_malformed_git_log_args_raise_controlled_error(self) -> None:
        with self.assertRaisesRegex(Exception, "invalid --git-log-args"):
            collect_script.parse_git_log_args('"unterminated')

    def test_malformed_git_log_args_cli_has_no_traceback(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "collect_project_context.py"),
                "--root",
                str(ROOT),
                "--git-log-args",
                '"unterminated',
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("invalid --git-log-args", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)


class ProjectHookRegistrationTests(unittest.TestCase):
    def test_registers_project_hooks_in_missing_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            actions = hooks_script.register_project_hooks(root)

            path = root / ".codex" / "hooks.json"
            self.assertEqual([action.status for action in actions], ["created"])
            self.assertTrue(path.exists())
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["version"], 1)
            self.assertEqual(
                [hook["id"] for hook in data["hooks"]],
                [
                    "arbor.session_startup_context",
                    "arbor.in_session_memory_hygiene",
                    "arbor.goal_constraint_drift",
                ],
            )
            self.assertEqual(data["hooks"][0]["entrypoint"]["script"], "scripts/run_session_startup_hook.py")
            self.assertEqual(data["hooks"][0]["order"], ["AGENTS.md", "formatted git log", ".codex/memory.md", "git status"])
            self.assertEqual(data["hooks"][0]["entrypoint"]["optional_args"][0]["name"], "--git-log-args")
            self.assertEqual(data["hooks"][1]["entrypoint"]["script"], "scripts/run_memory_hygiene_hook.py")
            self.assertEqual(data["hooks"][1]["entrypoint"]["optional_args"][0]["name"], "--diff-args")
            self.assertEqual(data["hooks"][2]["entrypoint"]["script"], "scripts/run_agents_guide_drift_hook.py")
            self.assertEqual(data["hooks"][2]["entrypoint"]["optional_args"][0]["name"], "--doc")
            self.assertIs(data["hooks"][2]["entrypoint"]["optional_args"][0]["repeatable"], True)

    def test_hook_registration_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            actions = hooks_script.register_project_hooks(root, dry_run=True)

            self.assertEqual([action.status for action in actions], ["would_create"])
            self.assertFalse((root / ".codex" / "hooks.json").exists())

    def test_hook_registration_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            hooks_script.register_project_hooks(root)
            before = (root / ".codex" / "hooks.json").read_text(encoding="utf-8")
            actions = hooks_script.register_project_hooks(root)
            after = (root / ".codex" / "hooks.json").read_text(encoding="utf-8")

            self.assertEqual([action.status for action in actions], ["exists"])
            self.assertEqual(after, before)

    def test_preserves_unrelated_hooks_and_replaces_stale_arbor_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hooks_path = root / ".codex" / "hooks.json"
            hooks_path.parent.mkdir()
            hooks_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "custom": "keep",
                        "hooks": [
                            {"id": "custom.preflight", "owner": "custom"},
                            {"id": "arbor.session_startup_context", "owner": "third-party"},
                            {"id": "arbor.session_startup_context", "owner": "arbor", "stale": True},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            actions = hooks_script.register_project_hooks(root)
            data = json.loads(hooks_path.read_text(encoding="utf-8"))

            self.assertEqual([action.status for action in actions], ["updated"])
            self.assertEqual(data["custom"], "keep")
            self.assertEqual(data["hooks"][0], {"id": "custom.preflight", "owner": "custom"})
            self.assertEqual(data["hooks"][1], {"id": "arbor.session_startup_context", "owner": "third-party"})
            self.assertEqual(len([hook for hook in data["hooks"] if hook.get("owner") == "arbor"]), 3)
            replaced_hook = next(
                hook
                for hook in data["hooks"]
                if hook.get("owner") == "arbor" and hook.get("id") == "arbor.session_startup_context"
            )
            self.assertNotIn("stale", replaced_hook)

    def test_hook_registration_rejects_nonexistent_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "typo-project"

            with self.assertRaisesRegex(hooks_script.HookRegistrationError, "project root does not exist"):
                hooks_script.register_project_hooks(root)

            self.assertFalse(root.exists())

    def test_hook_registration_reports_path_conflicts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".codex").write_text("not a directory", encoding="utf-8")

            with self.assertRaisesRegex(hooks_script.HookRegistrationError, "parent path is not a directory"):
                hooks_script.register_project_hooks(root)

    def test_hook_registration_reports_config_directory_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".codex").mkdir()
            (root / ".codex" / "hooks.json").mkdir()

            with self.assertRaisesRegex(hooks_script.HookRegistrationError, "expected a file but found a directory"):
                hooks_script.register_project_hooks(root)

    def test_hook_registration_rejects_out_of_root_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            root = Path(tmp)
            (root / ".codex").symlink_to(Path(outside), target_is_directory=True)

            with self.assertRaisesRegex(hooks_script.HookRegistrationError, "outside project root"):
                hooks_script.register_project_hooks(root)

    def test_invalid_hook_config_cli_has_no_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".codex").mkdir()
            (root / ".codex" / "hooks.json").write_text("{", encoding="utf-8")

            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "register_project_hooks.py"),
                    "--root",
                    str(root),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("cannot parse", proc.stderr)
            self.assertNotIn("Traceback", proc.stderr)

    def test_nonexistent_root_cli_has_no_traceback_and_does_not_create_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "typo-project"

            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "register_project_hooks.py"),
                    "--root",
                    str(root),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("project root does not exist", proc.stderr)
            self.assertNotIn("Traceback", proc.stderr)
            self.assertFalse(root.exists())

    def test_hook_write_errors_are_controlled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            with mock.patch.object(Path, "write_text", side_effect=PermissionError("denied")):
                with self.assertRaisesRegex(hooks_script.HookRegistrationError, "cannot write"):
                    hooks_script.register_project_hooks(root)


class SessionStartupHookTests(unittest.TestCase):
    def test_startup_hook_function_forwards_selected_git_log_args(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            configure_git_repo(root)
            init_script.init_project_memory(root)
            for index in range(3):
                commit_file(root, f"file-{index}.txt", f"content {index}", f"commit {index}")

            output = startup_hook_script.run_session_startup_hook(root, ["--oneline", "--max-count=1"])

            self.assertIn("commit 2", output)
            self.assertNotIn("commit 1", output)
            self.assertNotIn("commit 0", output)
            self.assertLess(output.index("## 1. AGENTS.md"), output.index("## 2. formatted git log"))
            self.assertLess(output.index("## 2. formatted git log"), output.index("## 3. .codex/memory.md"))
            self.assertLess(output.index("## 3. .codex/memory.md"), output.index("## 4. git status"))

    def test_startup_hook_function_rejects_nonexistent_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "missing"

            with self.assertRaisesRegex(startup_hook_script.SessionStartupHookError, "project root does not exist"):
                startup_hook_script.run_session_startup_hook(root)

    def test_startup_hook_replays_registered_path_with_selected_git_log_args(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            configure_git_repo(root)
            init_script.init_project_memory(root)
            for index in range(3):
                commit_file(root, f"file-{index}.txt", f"content {index}", f"commit {index}")

            proc = subprocess.run(
                registered_startup_hook_command(root, "--git-log-args", "--oneline --max-count=1"),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("commit 2", proc.stdout)
            self.assertNotIn("commit 1", proc.stdout)
            self.assertNotIn("commit 0", proc.stdout)
            self.assertIn("## 1. AGENTS.md", proc.stdout)
            self.assertIn("## 4. git status", proc.stdout)

    def test_startup_hook_registered_path_does_not_write_memory_or_agents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            configure_git_repo(root)
            init_script.init_project_memory(root)
            memory_path = root / ".codex" / "memory.md"
            agents_path = root / "AGENTS.md"
            before = (memory_path.read_text(encoding="utf-8"), agents_path.read_text(encoding="utf-8"))

            proc = subprocess.run(
                registered_startup_hook_command(root),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            after = (memory_path.read_text(encoding="utf-8"), agents_path.read_text(encoding="utf-8"))

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(after, before)

    def test_startup_hook_registered_path_returns_fallback_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            proc = subprocess.run(
                registered_startup_hook_command(root),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("## 1. AGENTS.md", proc.stdout)
            self.assertIn("Status: missing", proc.stdout)
            self.assertIn("## 4. git status", proc.stdout)
            self.assertIn("Status: git-error", proc.stdout)

    def test_startup_hook_cli_rejects_nonexistent_root_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "missing"

            proc = subprocess.run(
                [sys.executable, str(SCRIPTS / "run_session_startup_hook.py"), "--root", str(root)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("project root does not exist", proc.stderr)
            self.assertNotIn("Traceback", proc.stderr)


class MemoryHygieneHookTests(unittest.TestCase):
    def test_memory_hygiene_hook_collects_memory_status_and_diff_stat(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            configure_git_repo(root)
            init_script.init_project_memory(root)
            commit_file(root, "tracked.txt", "base\n", "base commit")
            (root / "tracked.txt").write_text("base\nchanged\n", encoding="utf-8")
            (root / "pending.txt").write_text("pending", encoding="utf-8")

            output = memory_hook_script.run_memory_hygiene_hook(root)

            self.assertIn("# Memory Hygiene Context", output)
            self.assertIn("## 1. .codex/memory.md", output)
            self.assertIn("## 2. git status", output)
            self.assertIn(" M tracked.txt", output)
            self.assertIn("?? pending.txt", output)
            self.assertIn("## 3. git diff --stat", output)
            self.assertIn("## 4. git diff --cached --stat", output)
            self.assertIn("tracked.txt", output)
            self.assertNotIn("## 5. selected git diff", output)

    def test_memory_hygiene_hook_includes_staged_diff_stat(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            configure_git_repo(root)
            init_script.init_project_memory(root)
            commit_file(root, "staged.txt", "base\n", "base commit")
            (root / "staged.txt").write_text("base\nstaged\n", encoding="utf-8")
            subprocess.run(["git", "add", "staged.txt"], cwd=root, check=True)

            output = memory_hook_script.run_memory_hygiene_hook(root)

            self.assertIn("M  staged.txt", output)
            self.assertIn("## 4. git diff --cached --stat", output)
            self.assertIn("staged.txt", output)

    def test_memory_hygiene_hook_forwards_selected_diff_args(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            configure_git_repo(root)
            init_script.init_project_memory(root)
            commit_file(root, "tracked.txt", "base\n", "base commit")
            (root / "tracked.txt").write_text("base\nchanged\n", encoding="utf-8")

            output = memory_hook_script.run_memory_hygiene_hook(root, ["--", "tracked.txt"])

            self.assertIn("## 5. selected git diff", output)
            self.assertIn("+changed", output)

    def test_memory_hygiene_registered_path_forwards_selected_diff_args(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            configure_git_repo(root)
            init_script.init_project_memory(root)
            commit_file(root, "tracked.txt", "base\n", "base commit")
            (root / "tracked.txt").write_text("base\nchanged\n", encoding="utf-8")

            proc = subprocess.run(
                registered_memory_hook_command(root, "--diff-args", "-- tracked.txt"),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("## 5. selected git diff", proc.stdout)
            self.assertIn("+changed", proc.stdout)

    def test_memory_hygiene_registered_path_rejects_side_effecting_diff_args(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            configure_git_repo(root)
            init_script.init_project_memory(root)
            commit_file(root, "tracked.txt", "base\n", "base commit")
            (root / "tracked.txt").write_text("base\nchanged\n", encoding="utf-8")
            memory_path = root / ".codex" / "memory.md"
            agents_path = root / "AGENTS.md"
            before = (memory_path.read_text(encoding="utf-8"), agents_path.read_text(encoding="utf-8"))

            proc = subprocess.run(
                registered_memory_hook_command(root, "--diff-args", "--output=AGENTS.md -- tracked.txt"),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            after = (memory_path.read_text(encoding="utf-8"), agents_path.read_text(encoding="utf-8"))

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("unsafe git diff argument", proc.stderr)
            self.assertNotIn("Traceback", proc.stderr)
            self.assertEqual(after, before)

    def test_memory_hygiene_registered_path_rejects_no_index_outside_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside_tmp:
            root = Path(tmp)
            outside = Path(outside_tmp) / "outside.txt"
            outside.write_text("outside secret\n", encoding="utf-8")
            configure_git_repo(root)
            init_script.init_project_memory(root)
            commit_file(root, "tracked.txt", "base\n", "base commit")

            proc = subprocess.run(
                registered_memory_hook_command(root, "--diff-args", f"--no-index {outside} tracked.txt"),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("unsafe git diff argument", proc.stderr)
            self.assertNotIn("outside secret", proc.stdout)
            self.assertNotIn("Traceback", proc.stderr)

    def test_memory_hygiene_registered_path_rejects_outside_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside_tmp:
            root = Path(tmp)
            outside = Path(outside_tmp) / "outside.txt"
            outside.write_text("outside secret\n", encoding="utf-8")
            configure_git_repo(root)
            init_script.init_project_memory(root)
            commit_file(root, "tracked.txt", "base\n", "base commit")

            proc = subprocess.run(
                registered_memory_hook_command(root, "--diff-args", f"-- {outside}"),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("outside project root", proc.stderr)
            self.assertNotIn("outside secret", proc.stdout)
            self.assertNotIn("Traceback", proc.stderr)

    def test_memory_hygiene_hook_registered_path_does_not_write_memory_or_agents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            configure_git_repo(root)
            init_script.init_project_memory(root)
            memory_path = root / ".codex" / "memory.md"
            agents_path = root / "AGENTS.md"
            before = (memory_path.read_text(encoding="utf-8"), agents_path.read_text(encoding="utf-8"))

            proc = subprocess.run(
                registered_memory_hook_command(root),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            after = (memory_path.read_text(encoding="utf-8"), agents_path.read_text(encoding="utf-8"))

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(after, before)
            self.assertIn("If an update is needed, edit only the project-local `.codex/memory.md`.", proc.stdout)

    def test_memory_hygiene_hook_returns_fallback_diagnostics_for_non_git_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            output = memory_hook_script.run_memory_hygiene_hook(root)

            self.assertIn("## 1. .codex/memory.md", output)
            self.assertIn("Status: missing", output)
            self.assertIn("## 2. git status", output)
            self.assertIn("Status: git-error", output)
            self.assertIn("## 3. git diff --stat", output)
            self.assertIn("## 4. git diff --cached --stat", output)

    def test_memory_hygiene_hook_cli_rejects_bad_diff_args_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "run_memory_hygiene_hook.py"),
                    "--root",
                    str(root),
                    "--diff-args",
                    '"unterminated',
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("invalid git args", proc.stderr)
            self.assertNotIn("Traceback", proc.stderr)

    def test_memory_hygiene_hook_cli_rejects_nonexistent_root_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "missing"

            proc = subprocess.run(
                [sys.executable, str(SCRIPTS / "run_memory_hygiene_hook.py"), "--root", str(root)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("project root does not exist", proc.stderr)
            self.assertNotIn("Traceback", proc.stderr)


class AgentsGuideDriftHookTests(unittest.TestCase):
    def test_agents_drift_hook_collects_agents_and_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            configure_git_repo(root)
            init_script.init_project_memory(root)
            (root / "pending.txt").write_text("pending", encoding="utf-8")

            output = agents_drift_hook_script.run_agents_guide_drift_hook(root)

            self.assertIn("# AGENTS Guide Drift Context", output)
            self.assertIn("## 1. AGENTS.md", output)
            self.assertIn("## 2. git status", output)
            self.assertIn("?? AGENTS.md", output)
            self.assertIn("?? pending.txt", output)
            self.assertIn("edit only these sections: Project Goal, Project Constraints, Project Map", output)
            self.assertIn("Do not update `.codex/memory.md` from this hook.", output)

    def test_agents_drift_hook_registered_path_includes_selected_docs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            configure_git_repo(root)
            init_script.init_project_memory(root)
            docs = root / "docs"
            docs.mkdir()
            (docs / "architecture.md").write_text("# Architecture\n\nDurable map note.\n", encoding="utf-8")
            (docs / "constraints.md").write_text("# Constraints\n\nDurable workflow note.\n", encoding="utf-8")

            proc = subprocess.run(
                registered_agents_drift_hook_command(
                    root,
                    "--doc",
                    "docs/architecture.md",
                    "--doc",
                    "docs/constraints.md",
                ),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("## 3. selected project doc: docs/architecture.md", proc.stdout)
            self.assertIn("Durable map note.", proc.stdout)
            self.assertIn("## 4. selected project doc: docs/constraints.md", proc.stdout)
            self.assertIn("Durable workflow note.", proc.stdout)

    def test_agents_drift_hook_allows_absolute_doc_under_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            configure_git_repo(root)
            init_script.init_project_memory(root)
            doc = root / "durable.md"
            doc.write_text("root-local durable note\n", encoding="utf-8")

            output = agents_drift_hook_script.run_agents_guide_drift_hook(root, [doc])

            self.assertIn("root-local durable note", output)

    def test_agents_drift_hook_rejects_outside_absolute_doc_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside_tmp:
            root = Path(tmp)
            configure_git_repo(root)
            init_script.init_project_memory(root)
            outside = Path(outside_tmp) / "outside.md"
            outside.write_text("outside secret\n", encoding="utf-8")

            proc = subprocess.run(
                registered_agents_drift_hook_command(root, "--doc", str(outside)),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("outside project root", proc.stderr)
            self.assertNotIn("outside secret", proc.stdout)
            self.assertNotIn("Traceback", proc.stderr)

    def test_agents_drift_hook_missing_selected_doc_is_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            configure_git_repo(root)
            init_script.init_project_memory(root)

            output = agents_drift_hook_script.run_agents_guide_drift_hook(root, [Path("docs/missing.md")])

            self.assertIn("## 3. selected project doc: docs/missing.md", output)
            self.assertIn("Status: missing", output)
            self.assertIn("Missing:", output)

    def test_agents_drift_hook_path_conflict_selected_doc_is_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            configure_git_repo(root)
            init_script.init_project_memory(root)
            (root / "docs").mkdir()

            output = agents_drift_hook_script.run_agents_guide_drift_hook(root, [Path("docs")])

            self.assertIn("## 3. selected project doc: docs", output)
            self.assertIn("Status: path-conflict", output)
            self.assertIn("Expected a file but found a directory", output)

    def test_agents_drift_hook_registered_path_does_not_write_memory_or_agents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            configure_git_repo(root)
            init_script.init_project_memory(root)
            memory_path = root / ".codex" / "memory.md"
            agents_path = root / "AGENTS.md"
            before = (memory_path.read_text(encoding="utf-8"), agents_path.read_text(encoding="utf-8"))

            proc = subprocess.run(
                registered_agents_drift_hook_command(root),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            after = (memory_path.read_text(encoding="utf-8"), agents_path.read_text(encoding="utf-8"))

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(after, before)
            self.assertIn("Keep current uncommitted progress", proc.stdout)

    def test_agents_drift_hook_cli_rejects_bad_doc_paths_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "run_agents_guide_drift_hook.py"),
                    "--root",
                    str(root),
                    "--doc-paths",
                    '"unterminated',
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("invalid doc paths", proc.stderr)
            self.assertNotIn("Traceback", proc.stderr)

    def test_agents_drift_hook_cli_rejects_nonexistent_root_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "missing"

            proc = subprocess.run(
                [sys.executable, str(SCRIPTS / "run_agents_guide_drift_hook.py"), "--root", str(root)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("project root does not exist", proc.stderr)
            self.assertNotIn("Traceback", proc.stderr)


class ArborPluginPackagingTests(unittest.TestCase):
    def test_plugin_manifest_points_to_arbor_skill_and_hooks(self) -> None:
        manifest_path = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"

        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        rendered = json.dumps(data)

        self.assertEqual(data["name"], "arbor")
        self.assertEqual(data["skills"], "./skills/")
        self.assertEqual(data["hooks"], "./hooks.json")
        self.assertEqual(data["interface"]["displayName"], "Arbor")
        self.assertIn("Project-local memory", data["interface"]["shortDescription"])
        self.assertNotIn("[TODO:", rendered)

    def test_plugin_contains_current_arbor_skill_payload(self) -> None:
        def package_files(root: Path) -> list[Path]:
            return sorted(
                path.relative_to(root)
                for path in root.rglob("*")
                if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
            )

        source_files = package_files(ROOT / "skills" / "arbor")
        plugin_files = sorted(
            package_files(PLUGIN_ROOT / "skills" / "arbor")
        )

        self.assertEqual(plugin_files, source_files)
        for relative_path in source_files:
            source = (ROOT / "skills" / "arbor" / relative_path).read_text(encoding="utf-8")
            packaged = (PLUGIN_ROOT / "skills" / "arbor" / relative_path).read_text(encoding="utf-8")
            self.assertEqual(packaged, source, str(relative_path))

    def test_plugin_hook_contract_matches_registered_arbor_hooks(self) -> None:
        data = json.loads((PLUGIN_ROOT / "hooks.json").read_text(encoding="utf-8"))

        self.assertEqual(data["version"], hooks_script.HOOK_CONFIG_VERSION)
        self.assertEqual(data["hooks"], hooks_script.ARBOR_HOOKS)

    def test_plugin_packaged_hook_entrypoints_exist(self) -> None:
        data = json.loads((PLUGIN_ROOT / "hooks.json").read_text(encoding="utf-8"))

        for hook in data["hooks"]:
            entrypoint = hook["entrypoint"]
            self.assertEqual(entrypoint["type"], "skill-script")
            self.assertTrue((PLUGIN_ROOT / "skills" / "arbor" / entrypoint["script"]).is_file())


class HookTriggerSidecarTests(unittest.TestCase):
    def test_sidecar_schema_covers_markdown_corpus(self) -> None:
        scenarios = parse_trigger_scenario_markdown()
        sidecar = load_trigger_sidecar()

        self.assertEqual(sidecar["schema_version"], 1)
        self.assertEqual(sidecar["source"], "docs/reviews/hook-trigger-scenarios.md")
        self.assertEqual(set(sidecar["hook_ids"].values()), ARBOR_HOOK_IDS)
        self.assertEqual(len(scenarios), 150)
        self.assertEqual(set(sidecar["default_expectations"]), {"H1", "H2", "H3", "NONE", "MULTI"})
        self.assertLessEqual(set(sidecar["overrides"]), set(scenarios))

    def test_sidecar_expands_every_markdown_scenario_to_machine_expectation(self) -> None:
        scenarios = parse_trigger_scenario_markdown()
        sidecar = load_trigger_sidecar()

        for scenario_id, scenario in scenarios.items():
            expectation = expanded_trigger_expectation(sidecar, scenario_id, scenario["expected"])
            self.assertIn(expectation["fixture"], {
                "clean_git_project",
                "non_git_project",
                "missing_agents",
                "missing_memory",
                "uncommitted_changes",
                "stale_memory",
                "durable_drift_docs",
                "outside_root_path",
            }, scenario_id)
            self.assertTrue(set(expectation["allowed_decisions"]) <= {"trigger", "none", "ambiguous"}, scenario_id)
            self.assertTrue(set(expectation["expected_hooks"]) <= ARBOR_HOOK_IDS, scenario_id)
            self.assertTrue(set(expectation["optional_expected_hooks"]) <= ARBOR_HOOK_IDS, scenario_id)
            self.assertTrue(set(expectation["forbidden_hooks"]) <= ARBOR_HOOK_IDS, scenario_id)
            self.assertIsInstance(expectation["requires_agent_judgment"], bool, scenario_id)
            self.assertFalse(set(expectation["expected_hooks"]) & set(expectation["forbidden_hooks"]), scenario_id)
            self.assertFalse(set(expectation["optional_expected_hooks"]) & set(expectation["forbidden_hooks"]), scenario_id)

    def test_sidecar_preserves_single_hook_and_none_semantics(self) -> None:
        scenarios = parse_trigger_scenario_markdown()
        sidecar = load_trigger_sidecar()

        for scenario_id, scenario in scenarios.items():
            expectation = expanded_trigger_expectation(sidecar, scenario_id, scenario["expected"])
            if scenario["expected"] in {"H1", "H2", "H3"}:
                hook_id = sidecar["hook_ids"][scenario["expected"]]
                non_target_hooks = ARBOR_HOOK_IDS - {hook_id}
                self.assertEqual(expectation["expected_hooks"], [hook_id], scenario_id)
                self.assertEqual(expectation["optional_expected_hooks"], [], scenario_id)
                self.assertIn("trigger", expectation["allowed_decisions"], scenario_id)
                self.assertNotIn(hook_id, expectation["forbidden_hooks"], scenario_id)
                self.assertEqual(set(expectation["forbidden_hooks"]), non_target_hooks, scenario_id)
            if scenario["expected"] == "NONE":
                self.assertEqual(expectation["allowed_decisions"], ["none"], scenario_id)
                self.assertEqual(expectation["expected_hooks"], [], scenario_id)
                self.assertEqual(expectation["optional_expected_hooks"], [], scenario_id)
                self.assertEqual(set(expectation["forbidden_hooks"]), ARBOR_HOOK_IDS, scenario_id)

    def test_multi_scenarios_have_structured_expectations(self) -> None:
        scenarios = parse_trigger_scenario_markdown()
        sidecar = load_trigger_sidecar()

        multi_ids = [scenario_id for scenario_id, scenario in scenarios.items() if scenario["expected"] == "MULTI"]
        self.assertGreater(len(multi_ids), 0)
        for scenario_id in multi_ids:
            self.assertIn(scenario_id, sidecar["overrides"], scenario_id)
            expectation = expanded_trigger_expectation(sidecar, scenario_id, "MULTI")
            self.assertIn(True, [
                bool(expectation["expected_hooks"]),
                bool(expectation["optional_expected_hooks"]),
                expectation["requires_agent_judgment"],
            ], scenario_id)

    def test_sidecar_optional_args_are_project_hook_args(self) -> None:
        sidecar = load_trigger_sidecar()

        for scenario_id, override in sidecar["overrides"].items():
            optional_args = override.get("optional_args", {})
            self.assertTrue(set(optional_args) <= ARBOR_HOOK_IDS, scenario_id)
            for args in optional_args.values():
                self.assertIsInstance(args, list, scenario_id)
                self.assertTrue(all(isinstance(arg, str) for arg in args), scenario_id)


class HookTriggerFixtureBuilderTests(unittest.TestCase):
    def test_fixture_builders_cover_sidecar_fixture_vocabulary(self) -> None:
        scenarios = parse_trigger_scenario_markdown()
        sidecar = load_trigger_sidecar()
        fixture_names = set(fixture_script.available_fixtures())

        referenced_fixtures = {
            expanded_trigger_expectation(sidecar, scenario_id, scenario["expected"])["fixture"]
            for scenario_id, scenario in scenarios.items()
        }

        self.assertLessEqual(referenced_fixtures, fixture_names)
        self.assertIn("non_git_project", fixture_names)

    def test_all_fixtures_build_project_summary_and_hooks(self) -> None:
        required_fields = {
            "fixture",
            "project_root",
            "is_git_repo",
            "git_status_short",
            "has_agents",
            "has_memory",
            "has_hooks",
            "available_docs",
            "memory_state",
            "agents_state",
            "notes",
        }
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for name in fixture_script.available_fixtures():
                result = fixture_script.build_fixture(name, base / name)
                self.assertEqual(result.name, name)
                self.assertEqual(result.summary["fixture"], name)
                self.assertEqual(set(result.summary) & required_fields, required_fields, name)
                self.assertTrue(Path(result.summary["project_root"]).is_dir(), name)
                self.assertTrue(result.summary["has_hooks"], name)
                self.assertTrue((result.root / ".codex" / "hooks.json").is_file(), name)

    def test_clean_git_project_has_clean_status_and_initialized_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = fixture_script.build_fixture("clean_git_project", Path(tmp) / "fixture")

            self.assertTrue(result.summary["is_git_repo"])
            self.assertEqual(result.summary["git_status_short"], [])
            self.assertTrue(result.summary["has_agents"])
            self.assertTrue(result.summary["has_memory"])

    def test_non_git_project_has_initialized_files_without_git_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = fixture_script.build_fixture("non_git_project", Path(tmp) / "fixture")

            self.assertFalse(result.summary["is_git_repo"])
            self.assertIsNone(result.summary["git_status_short"])
            self.assertTrue(result.summary["has_agents"])
            self.assertTrue(result.summary["has_memory"])

    def test_missing_setup_fixtures_remove_expected_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            missing_agents = fixture_script.build_fixture("missing_agents", base / "missing-agents")
            missing_memory = fixture_script.build_fixture("missing_memory", base / "missing-memory")

            self.assertFalse(missing_agents.summary["has_agents"])
            self.assertEqual(missing_agents.summary["agents_state"], "missing")
            self.assertIn(" D AGENTS.md", missing_agents.summary["git_status_short"])
            self.assertFalse((missing_agents.root / "AGENTS.md").exists())

            self.assertFalse(missing_memory.summary["has_memory"])
            self.assertEqual(missing_memory.summary["memory_state"], "missing")
            self.assertIn(" D .codex/memory.md", missing_memory.summary["git_status_short"])
            self.assertFalse((missing_memory.root / ".codex" / "memory.md").exists())

    def test_uncommitted_changes_fixture_has_tracked_and_untracked_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = fixture_script.build_fixture("uncommitted_changes", Path(tmp) / "fixture")

            self.assertIn(" M tracked.txt", result.summary["git_status_short"])
            self.assertIn("?? pending.txt", result.summary["git_status_short"])

    def test_stale_memory_fixture_marks_memory_as_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = fixture_script.build_fixture("stale_memory", Path(tmp) / "fixture")
            memory = (result.root / ".codex" / "memory.md").read_text(encoding="utf-8")

            self.assertEqual(result.summary["memory_state"], "stale")
            self.assertIn("Stale fixture item", memory)
            self.assertIn("?? fix-parser.txt", result.summary["git_status_short"])

    def test_durable_drift_fixture_exposes_project_docs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = fixture_script.build_fixture("durable_drift_docs", Path(tmp) / "fixture")

            self.assertEqual(result.summary["agents_state"], "present_with_durable_drift_docs")
            self.assertEqual(
                result.summary["available_docs"],
                ["docs/constraints.md", "docs/project-map.md", "docs/workflow.md"],
            )
            self.assertTrue((result.root / "docs" / "constraints.md").is_file())

    def test_outside_root_fixture_creates_rejectable_external_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = fixture_script.build_fixture("outside_root_path", Path(tmp) / "fixture")

            self.assertIsNotNone(result.outside_path)
            assert result.outside_path is not None
            self.assertTrue(result.outside_path.is_file())
            self.assertNotIn(result.root, result.outside_path.resolve().parents)
            self.assertEqual(result.summary["outside_path"], str(result.outside_path))

    def test_fixture_builder_rejects_unknown_fixture_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [
                    sys.executable,
                    str(EVAL_SCRIPTS / "eval_fixtures.py"),
                    "--fixture",
                    "unknown",
                    "--root",
                    str(Path(tmp) / "fixture"),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("invalid choice", proc.stderr)
            self.assertNotIn("Traceback", proc.stderr)

    def test_fixture_builder_cli_outputs_json_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [
                    sys.executable,
                    str(EVAL_SCRIPTS / "eval_fixtures.py"),
                    "--fixture",
                    "clean_git_project",
                    "--root",
                    str(Path(tmp) / "fixture"),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            summary = json.loads(proc.stdout)
            self.assertEqual(summary["fixture"], "clean_git_project")
            self.assertEqual(summary["git_status_short"], [])


class HookTriggerSimulatedDispatcherTests(unittest.TestCase):
    def test_simulated_dispatcher_loads_entire_scenario_corpus(self) -> None:
        scenarios = dispatcher_script.load_scenario_corpus()

        self.assertEqual(len(scenarios), 150)
        self.assertEqual(scenarios["H1-P001"].expression, "Start this project session.")
        self.assertEqual(scenarios["H1-P001"].expected_label, "H1")

    def test_simulated_dispatcher_returns_h1_trigger_decision(self) -> None:
        result = dispatcher_script.dispatch_scenario("H1-P001")

        self.assertEqual(result["decision"], "trigger")
        self.assertEqual(result["hooks"], ["arbor.session_startup_context"])
        self.assertEqual(result["confidence"], "high")
        self.assertFalse(result["requires_agent_judgment"])

    def test_simulated_dispatcher_returns_none_for_negative_case(self) -> None:
        result = dispatcher_script.dispatch_scenario("NM-P002")

        self.assertEqual(result["decision"], "none")
        self.assertEqual(result["hooks"], [])
        self.assertEqual(result["optional_args"], {})

    def test_simulated_dispatcher_returns_expected_multi_hook_decision(self) -> None:
        result = dispatcher_script.dispatch_scenario("M-P002")

        self.assertEqual(result["decision"], "trigger")
        self.assertEqual(
            result["hooks"],
            ["arbor.session_startup_context", "arbor.in_session_memory_hygiene"],
        )

    def test_simulated_dispatcher_preserves_ambiguous_judgment_cases(self) -> None:
        result = dispatcher_script.dispatch_scenario("M-P004")

        self.assertEqual(result["decision"], "ambiguous")
        self.assertEqual(result["hooks"], [])
        self.assertEqual(result["confidence"], "low")
        self.assertTrue(result["requires_agent_judgment"])

    def test_simulated_dispatcher_includes_selected_hook_optional_args(self) -> None:
        result = dispatcher_script.dispatch_scenario("H3-P002")

        self.assertEqual(result["decision"], "trigger")
        self.assertEqual(result["hooks"], ["arbor.goal_constraint_drift"])
        self.assertEqual(
            result["optional_args"],
            {"arbor.goal_constraint_drift": ["--doc", "docs/constraints.md"]},
        )

    def test_simulated_dispatcher_resolves_outside_root_placeholder_from_fixture_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = fixture_script.build_fixture("outside_root_path", Path(tmp) / "fixture")

            result = dispatcher_script.dispatch_scenario("EV-P010", fixture_summary=fixture.summary)

            self.assertEqual(result["decision"], "trigger")
            self.assertEqual(result["hooks"], ["arbor.goal_constraint_drift"])
            self.assertEqual(
                result["optional_args"],
                {"arbor.goal_constraint_drift": ["--doc", fixture.summary["outside_path"]]},
            )

    def test_simulated_dispatcher_outputs_valid_contract_for_every_scenario(self) -> None:
        scenarios = dispatcher_script.load_scenario_corpus()

        for scenario_id, scenario in scenarios.items():
            result = dispatcher_script.simulate_dispatch(scenario)
            expectation = scenario.expectation

            self.assertEqual(
                set(result),
                {"hooks", "decision", "confidence", "requires_agent_judgment", "optional_args", "reason"},
                scenario_id,
            )
            self.assertIn(result["decision"], expectation["allowed_decisions"], scenario_id)
            self.assertIn(result["confidence"], {"high", "medium", "low"}, scenario_id)
            self.assertTrue(set(result["hooks"]) <= ARBOR_HOOK_IDS, scenario_id)
            self.assertFalse(set(result["hooks"]) & set(expectation["forbidden_hooks"]), scenario_id)
            self.assertTrue(set(result["optional_args"]) <= set(result["hooks"]), scenario_id)
            if result["decision"] == "trigger":
                self.assertTrue(set(expectation["expected_hooks"]) <= set(result["hooks"]), scenario_id)
            else:
                self.assertEqual(result["hooks"], [], scenario_id)

    def test_simulated_dispatcher_is_deterministic_for_same_input(self) -> None:
        first = dispatcher_script.dispatch_scenario("M-P014")
        second = dispatcher_script.dispatch_scenario("M-P014")

        self.assertEqual(second, first)

    def test_simulated_dispatcher_cli_outputs_json_contract(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(EVAL_SCRIPTS / "simulated_dispatcher.py"),
                "--scenario-id",
                "H1-P001",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result["decision"], "trigger")
        self.assertEqual(result["hooks"], ["arbor.session_startup_context"])

    def test_simulated_dispatcher_cli_rejects_unknown_scenario_without_traceback(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(EVAL_SCRIPTS / "simulated_dispatcher.py"),
                "--scenario-id",
                "NOPE-P999",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("unknown scenario id", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)

    def test_simulated_dispatcher_cli_rejects_missing_corpus_without_traceback(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(EVAL_SCRIPTS / "simulated_dispatcher.py"),
                "--scenario-id",
                "H1-P001",
                "--scenarios",
                "/private/tmp/does-not-exist-arbor-scenarios.md",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("cannot read", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)

    def test_simulated_dispatcher_cli_rejects_invalid_sidecar_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sidecar = Path(tmp) / "sidecar.json"
            sidecar.write_text("[]", encoding="utf-8")

            proc = subprocess.run(
                [
                    sys.executable,
                    str(EVAL_SCRIPTS / "simulated_dispatcher.py"),
                    "--scenario-id",
                    "H1-P001",
                    "--sidecar",
                    str(sidecar),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("expected JSON object", proc.stderr)
            self.assertNotIn("Traceback", proc.stderr)

    def test_simulated_dispatcher_supports_optional_only_trigger_fallback(self) -> None:
        expectation = {
            "allowed_decisions": ["trigger"],
            "expected_hooks": [],
            "optional_expected_hooks": ["arbor.in_session_memory_hygiene"],
            "forbidden_hooks": [],
            "requires_agent_judgment": False,
        }

        self.assertEqual(dispatcher_script.select_decision(expectation), "trigger")
        self.assertEqual(
            dispatcher_script.select_hooks("trigger", expectation),
            ["arbor.in_session_memory_hygiene"],
        )

    def test_simulated_dispatcher_detects_forbidden_hook_conflicts(self) -> None:
        scenario = dispatcher_script.TriggerScenario(
            scenario_id="TEST-P001",
            expression="conflict",
            expected_label="H1",
            note="conflict fixture",
            expectation={
                "allowed_decisions": ["trigger"],
                "expected_hooks": ["arbor.session_startup_context"],
                "optional_expected_hooks": [],
                "forbidden_hooks": ["arbor.session_startup_context"],
                "requires_agent_judgment": False,
            },
        )

        with self.assertRaisesRegex(dispatcher_script.DispatchError, "forbidden hooks"):
            dispatcher_script.simulate_dispatch(scenario)


class HookTriggerExecutionHarnessTests(unittest.TestCase):
    def test_harness_executes_registered_h1_hook(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = harness_script.evaluate_scenario("H1-P001", Path(tmp))

            self.assertTrue(result["passed"])
            self.assertEqual(result["dispatcher"]["hooks"], ["arbor.session_startup_context"])
            self.assertEqual(len(result["executions"]), 1)
            execution = result["executions"][0]
            self.assertEqual(execution["hook_id"], "arbor.session_startup_context")
            self.assertEqual(execution["returncode"], 0)
            self.assertIn("# Project Startup Context", execution["stdout"])
            self.assertTrue(all(item["passed"] for item in execution["assertions"]))

    def test_harness_executes_registered_h2_hook(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = harness_script.evaluate_scenario("H2-P001", Path(tmp))

            self.assertTrue(result["passed"])
            self.assertEqual(result["dispatcher"]["hooks"], ["arbor.in_session_memory_hygiene"])
            execution = result["executions"][0]
            self.assertIn("# Memory Hygiene Context", execution["stdout"])
            self.assertIn(" M tracked.txt", execution["stdout"])
            self.assertIn("?? pending.txt", execution["stdout"])

    def test_harness_executes_registered_h3_hook_with_selected_doc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = harness_script.evaluate_scenario("H3-P002", Path(tmp))

            self.assertTrue(result["passed"])
            self.assertEqual(result["dispatcher"]["hooks"], ["arbor.goal_constraint_drift"])
            self.assertEqual(
                result["dispatcher"]["optional_args"],
                {"arbor.goal_constraint_drift": ["--doc", "docs/constraints.md"]},
            )
            execution = result["executions"][0]
            self.assertIn("# AGENTS Guide Drift Context", execution["stdout"])
            self.assertIn("## 3. selected project doc: docs/constraints.md", execution["stdout"])

    def test_harness_skips_none_decision_without_hook_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = harness_script.evaluate_scenario("NM-P002", Path(tmp))

            self.assertTrue(result["passed"])
            self.assertEqual(result["dispatcher"]["decision"], "none")
            self.assertEqual(result["dispatcher"]["hooks"], [])
            self.assertEqual(result["executions"], [])

    def test_harness_executes_multi_hook_scenario_in_dispatch_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = harness_script.evaluate_scenario("M-P002", Path(tmp))

            self.assertTrue(result["passed"])
            self.assertEqual(
                [execution["hook_id"] for execution in result["executions"]],
                ["arbor.session_startup_context", "arbor.in_session_memory_hygiene"],
            )
            self.assertIn("# Project Startup Context", result["executions"][0]["stdout"])
            self.assertIn("# Memory Hygiene Context", result["executions"][1]["stdout"])

    def test_harness_treats_outside_root_rejection_as_passing_execution_assertion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = harness_script.evaluate_scenario("EV-P010", Path(tmp))

            self.assertTrue(result["passed"])
            execution = result["executions"][0]
            self.assertEqual(execution["hook_id"], "arbor.goal_constraint_drift")
            self.assertNotEqual(execution["returncode"], 0)
            self.assertIn("outside project root", execution["stderr"])
            self.assertNotIn("outside root content should never be leaked", execution["stdout"])
            self.assertTrue(all(item["passed"] for item in execution["assertions"]))

    def test_harness_rejects_unknown_registered_hook(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = fixture_script.build_fixture("clean_git_project", Path(tmp) / "fixture")

            with self.assertRaisesRegex(harness_script.HarnessError, "registered hook not found"):
                harness_script.execute_registered_hook(fixture.root, "arbor.missing_hook")

    def test_harness_cli_outputs_scenario_result_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [
                    sys.executable,
                    str(EVAL_SCRIPTS / "evaluate_hook_triggers.py"),
                    "--scenario-id",
                    "H1-P001",
                    "--work-root",
                    str(Path(tmp)),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            result = json.loads(proc.stdout)
            self.assertTrue(result["passed"])
            self.assertEqual(result["dispatcher"]["hooks"], ["arbor.session_startup_context"])

    def test_harness_full_corpus_report_summarizes_execution_quality(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = harness_script.evaluate_corpus(Path(tmp))

            summary = report["summary"]
            self.assertTrue(report["passed"])
            self.assertEqual(report["report_type"], "sidecar_backed_hook_execution")
            self.assertEqual(summary["total_scenarios"], 150)
            self.assertEqual(summary["passed_scenarios"], 150)
            self.assertEqual(summary["failed_scenarios"], [])
            self.assertGreater(summary["selected_hook_executions"], 0)
            self.assertEqual(summary["hook_execution_pass_rate"], 1.0)
            self.assertEqual(summary["outside_root_leaks"], 0)
            self.assertEqual(summary["unintended_write_failures"], 0)
            self.assertFalse(summary["semantic_metrics"]["reported"])
            self.assertEqual(len(report["scenarios"]), 150)
            self.assertNotIn("stdout", json.dumps(report["scenarios"][0]))

    def test_harness_full_corpus_report_can_include_execution_details(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = harness_script.evaluate_corpus(Path(tmp), include_details=True)

            detailed_execution = next(
                execution
                for scenario in report["scenarios"]
                for execution in scenario["executions"]
                if execution["hook_id"] == "arbor.session_startup_context"
            )
            self.assertIn("stdout", detailed_execution)
            self.assertIn("# Project Startup Context", detailed_execution["stdout"])

    def test_harness_cli_outputs_full_corpus_report_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [
                    sys.executable,
                    str(EVAL_SCRIPTS / "evaluate_hook_triggers.py"),
                    "--all",
                    "--work-root",
                    str(Path(tmp)),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            report = json.loads(proc.stdout)
            self.assertTrue(report["passed"])
            self.assertEqual(report["summary"]["total_scenarios"], 150)
            self.assertFalse(report["summary"]["semantic_metrics"]["reported"])

    def test_harness_cli_rejects_unknown_scenario_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [
                    sys.executable,
                    str(EVAL_SCRIPTS / "evaluate_hook_triggers.py"),
                    "--scenario-id",
                    "NOPE-P999",
                    "--work-root",
                    str(Path(tmp)),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("unknown scenario id", proc.stderr)
            self.assertNotIn("Traceback", proc.stderr)


if __name__ == "__main__":
    unittest.main()
