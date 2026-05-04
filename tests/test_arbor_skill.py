from __future__ import annotations

import copy
import importlib.util
import json
import re
import shutil
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
STAGE_B_REVIEW = ROOT / "docs" / "reviews" / "stage-b-plugin-runtime-final-review.md"
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
trigger_adapter_script = load_module("plugin_trigger_adapters", EVAL_SCRIPTS / "plugin_trigger_adapters.py")
harness_script = load_module("evaluate_hook_triggers", EVAL_SCRIPTS / "evaluate_hook_triggers.py")
plugin_install_script = load_module("validate_plugin_install", EVAL_SCRIPTS / "validate_plugin_install.py")
plugin_runtime_probe_script = load_module("probe_plugin_runtime", EVAL_SCRIPTS / "probe_plugin_runtime.py")


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


def stage_b_review_payload_baseline() -> set[str]:
    lines = STAGE_B_REVIEW.read_text(encoding="utf-8").splitlines()
    try:
        start = lines.index("Expected packaged payload baseline:") + 1
    except ValueError as exc:
        raise AssertionError("Stage B review is missing expected payload baseline section") from exc
    payload_files: set[str] = set()
    for line in lines[start:]:
        if line.startswith("## "):
            break
        match = re.fullmatch(r"- `(.+)`", line)
        if match:
            payload_files.add(match.group(1))
    return payload_files


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

    def test_git_log_args_cli_accepts_lone_pathspec_separator(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "collect_project_context.py"),
                "--root",
                str(ROOT),
                "--git-log-args=--",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("# Project Startup Context", proc.stdout)


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

    def test_memory_hygiene_hook_cli_accepts_lone_pathspec_separator(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "run_memory_hygiene_hook.py"),
                    "--root",
                    str(root),
                    "--diff-args=--",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("# Memory Hygiene Context", proc.stdout)
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

    def test_plugin_payload_excludes_evaluation_harness_artifacts(self) -> None:
        excluded = [
            PLUGIN_ROOT / "scripts" / "evaluate_hook_triggers.py",
            PLUGIN_ROOT / "scripts" / "simulated_dispatcher.py",
            PLUGIN_ROOT / "scripts" / "eval_fixtures.py",
            PLUGIN_ROOT / "docs" / "reviews" / "hook-trigger-scenarios.md",
            PLUGIN_ROOT / "docs" / "reviews" / "hook-trigger-scenarios.json",
            PLUGIN_ROOT / "docs" / "reviews" / "features",
        ]

        for path in excluded:
            self.assertFalse(path.exists(), str(path))

    def test_plugin_payload_excludes_transient_artifacts(self) -> None:
        transient_artifacts = [
            path
            for path in PLUGIN_ROOT.rglob("*")
            if path.is_file()
            and plugin_install_script.transient_payload_reason(path.relative_to(PLUGIN_ROOT)) is not None
        ]

        self.assertEqual(transient_artifacts, [])

    def test_plugin_payload_excludes_symlinks(self) -> None:
        symlinks = [path for path in PLUGIN_ROOT.rglob("*") if path.is_symlink()]

        self.assertEqual(symlinks, [])

    def test_stage_b_payload_baseline_matches_validator_allowlist(self) -> None:
        self.assertEqual(
            stage_b_review_payload_baseline(),
            plugin_install_script.EXPECTED_PAYLOAD_FILES,
        )


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


class HookTriggerPluginAdapterTests(unittest.TestCase):
    def trigger_decision(
        self,
        hook_id: str | None,
        optional_args: dict[str, list[str]],
    ) -> dict[str, object]:
        return {
            "hooks": [hook_id] if hook_id else [],
            "decision": "trigger" if hook_id else "none",
            "confidence": "high",
            "requires_agent_judgment": False,
            "optional_args": optional_args,
            "reason": "Test trigger decision.",
        }

    def test_plugin_runtime_input_excludes_sidecar_scoring_fields(self) -> None:
        scenarios = dispatcher_script.load_scenario_corpus()
        with tempfile.TemporaryDirectory() as tmp:
            fixture = fixture_script.build_fixture("stale_memory", Path(tmp) / "fixture")

            payload = trigger_adapter_script.build_plugin_runtime_input(
                expression=scenarios["H2-P001"].expression,
                project_root=fixture.root,
                fixture_summary=fixture.summary,
            )

            serialized = json.dumps(payload, sort_keys=True)
            for field in trigger_adapter_script.SIDECAR_SCORING_FIELDS:
                self.assertNotIn(f'"{field}"', serialized)
            self.assertNotIn("expected_hooks", serialized)
            self.assertNotIn("forbidden_hooks", serialized)
            self.assertNotIn("allowed_decisions", serialized)
            self.assertNotIn("Stale fixture item", serialized)
            self.assertNotIn("outside_path", serialized)
            self.assertIn("hook_contract", payload)
            self.assertEqual(payload["skill_metadata"]["name"], "arbor")

    def test_plugin_runtime_input_includes_outside_path_without_file_content(self) -> None:
        scenarios = dispatcher_script.load_scenario_corpus()
        with tempfile.TemporaryDirectory() as tmp:
            fixture = fixture_script.build_fixture("outside_root_path", Path(tmp) / "fixture")

            payload = trigger_adapter_script.build_plugin_runtime_input(
                expression=scenarios["EV-P010"].expression,
                project_root=fixture.root,
                fixture_summary=fixture.summary,
            )

            self.assertEqual(payload["project_state"]["outside_path"], fixture.summary["outside_path"])
            serialized = json.dumps(payload, sort_keys=True)
            self.assertIn('"outside_path"', serialized)
            self.assertNotIn("outside root content should never be leaked", serialized)
            for field in trigger_adapter_script.SIDECAR_SCORING_FIELDS:
                self.assertNotIn(f'"{field}"', serialized)

    def test_adapter_validates_sidecar_baseline_trigger_contract(self) -> None:
        scenarios = dispatcher_script.load_scenario_corpus()
        with tempfile.TemporaryDirectory() as tmp:
            fixture = fixture_script.build_fixture("uncommitted_changes", Path(tmp) / "fixture")

            decision = trigger_adapter_script.trigger_with_adapter(
                "sidecar-baseline",
                scenarios["H2-P001"],
                fixture.root,
                fixture.summary,
            )

            self.assertEqual(decision["decision"], "trigger")
            self.assertEqual(decision["hooks"], ["arbor.in_session_memory_hygiene"])

    def test_plugin_runtime_stub_adapter_returns_valid_abstention_contract(self) -> None:
        scenarios = dispatcher_script.load_scenario_corpus()
        with tempfile.TemporaryDirectory() as tmp:
            fixture = fixture_script.build_fixture("clean_git_project", Path(tmp) / "fixture")

            decision = trigger_adapter_script.trigger_with_adapter(
                "plugin-runtime-stub",
                scenarios["H1-P001"],
                fixture.root,
                fixture.summary,
            )

            self.assertEqual(decision["decision"], "ambiguous")
            self.assertEqual(decision["hooks"], [])
            self.assertTrue(decision["requires_agent_judgment"])

    def test_plugin_runtime_codex_exec_adapter_parses_valid_runtime_decision(self) -> None:
        scenarios = dispatcher_script.load_scenario_corpus()
        captured_prompt: dict[str, str] = {}

        def fake_run_command(args: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
            output_path = Path(args[args.index("--output-last-message") + 1])
            schema_path = Path(args[args.index("--output-schema") + 1])
            self.assertTrue(schema_path.is_file())
            captured_prompt["text"] = args[-1]
            output_path.write_text(
                json.dumps(
                    {
                        "hooks": ["arbor.session_startup_context"],
                        "decision": "trigger",
                        "confidence": "high",
                        "requires_agent_judgment": False,
                        "optional_args": {},
                        "reason": "The expression asks to resume project context.",
                    }
                ),
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="{}", stderr="")

        with tempfile.TemporaryDirectory() as tmp:
            fixture = fixture_script.build_fixture("clean_git_project", Path(tmp) / "fixture")
            payload = trigger_adapter_script.build_plugin_runtime_input(
                expression=scenarios["H1-P001"].expression,
                project_root=fixture.root,
                fixture_summary=fixture.summary,
            )

            with mock.patch.object(trigger_adapter_script.probe_plugin_runtime, "ensure_codex_binary"):
                with mock.patch.object(
                    trigger_adapter_script.probe_plugin_runtime,
                    "add_marketplace",
                    return_value={"status": "ok"},
                ):
                    with mock.patch.object(
                        trigger_adapter_script.probe_plugin_runtime,
                        "materialize_local_plugin_cache",
                        return_value={"status": "ok"},
                    ):
                        with mock.patch.object(
                            trigger_adapter_script.probe_plugin_runtime,
                            "enable_arbor_plugin",
                            return_value={"status": "ok"},
                        ):
                            with mock.patch.object(
                                trigger_adapter_script.probe_plugin_runtime,
                                "run_command",
                                side_effect=fake_run_command,
                            ):
                                decision = trigger_adapter_script.run_codex_exec_trigger(
                                    payload,
                                    fixture.root,
                                    codex_bin=Path("/bin/codex"),
                                )

            self.assertEqual(decision["decision"], "trigger")
            self.assertEqual(decision["hooks"], ["arbor.session_startup_context"])
            self.assertNotIn("expected_hooks", captured_prompt["text"])
            self.assertNotIn("allowed_decisions", captured_prompt["text"])
            self.assertIn("initializing the Arbor/project memory flow", captured_prompt["text"])
            self.assertIn("not-long-term notes", captured_prompt["text"])
            self.assertIn("naming", captured_prompt["text"])
            self.assertIn("outside the project root", captured_prompt["text"])
            self.assertIn("project_state.outside_path", captured_prompt["text"])
            self.assertIn("session-start events outside a project root", captured_prompt["text"])
            self.assertIn("paragraph-local reminders", captured_prompt["text"])
            self.assertIn("memory allocation", captured_prompt["text"])
            self.assertIn("local variable names", captured_prompt["text"])

    def test_plugin_runtime_codex_exec_adapter_copies_requested_auth(self) -> None:
        scenarios = dispatcher_script.load_scenario_corpus()

        def fake_run_command(args: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
            runtime_home = Path(kwargs["env"]["HOME"])
            self.assertEqual(
                (runtime_home / ".codex" / "auth.json").read_text(encoding="utf-8"),
                '{"token":"redacted"}\n',
            )
            output_path = Path(args[args.index("--output-last-message") + 1])
            output_path.write_text(
                json.dumps(
                    {
                        "hooks": [],
                        "decision": "none",
                        "confidence": "high",
                        "requires_agent_judgment": False,
                        "optional_args": {},
                        "reason": "The expression does not need Arbor hooks.",
                    }
                ),
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="{}", stderr="")

        with tempfile.TemporaryDirectory() as tmp:
            auth_home = Path(tmp) / "auth-home"
            (auth_home / ".codex").mkdir(parents=True)
            (auth_home / ".codex" / "auth.json").write_text('{"token":"redacted"}\n', encoding="utf-8")
            fixture = fixture_script.build_fixture("clean_git_project", Path(tmp) / "fixture")
            payload = trigger_adapter_script.build_plugin_runtime_input(
                expression=scenarios["N-P001"].expression,
                project_root=fixture.root,
                fixture_summary=fixture.summary,
            )

            with mock.patch.object(trigger_adapter_script.probe_plugin_runtime, "ensure_codex_binary"):
                with mock.patch.object(
                    trigger_adapter_script.probe_plugin_runtime,
                    "add_marketplace",
                    return_value={"status": "ok"},
                ):
                    with mock.patch.object(
                        trigger_adapter_script.probe_plugin_runtime,
                        "materialize_local_plugin_cache",
                        return_value={"status": "ok"},
                    ):
                        with mock.patch.object(
                            trigger_adapter_script.probe_plugin_runtime,
                            "enable_arbor_plugin",
                            return_value={"status": "ok"},
                        ):
                            with mock.patch.object(
                                trigger_adapter_script.probe_plugin_runtime,
                                "run_command",
                                side_effect=fake_run_command,
                            ):
                                decision = trigger_adapter_script.run_codex_exec_trigger(
                                    payload,
                                    fixture.root,
                                    codex_bin=Path("/bin/codex"),
                                    auth_source_home=auth_home,
                                )

            self.assertEqual(decision["decision"], "none")
            self.assertEqual(decision["hooks"], [])

    def test_plugin_runtime_codex_exec_adapter_blocks_missing_requested_auth(self) -> None:
        scenarios = dispatcher_script.load_scenario_corpus()

        with tempfile.TemporaryDirectory() as tmp:
            auth_home = Path(tmp) / "missing-auth-home"
            auth_home.mkdir()
            fixture = fixture_script.build_fixture("clean_git_project", Path(tmp) / "fixture")
            payload = trigger_adapter_script.build_plugin_runtime_input(
                expression=scenarios["H1-P001"].expression,
                project_root=fixture.root,
                fixture_summary=fixture.summary,
            )

            with mock.patch.object(trigger_adapter_script.probe_plugin_runtime, "ensure_codex_binary"):
                with mock.patch.object(
                    trigger_adapter_script.probe_plugin_runtime,
                    "add_marketplace",
                    return_value={"status": "ok"},
                ):
                    with mock.patch.object(trigger_adapter_script.probe_plugin_runtime, "run_command") as run_mock:
                        decision = trigger_adapter_script.run_codex_exec_trigger(
                            payload,
                            fixture.root,
                            codex_bin=Path("/bin/codex"),
                            auth_source_home=auth_home,
                        )

            run_mock.assert_not_called()
            self.assertEqual(decision["decision"], "ambiguous")
            self.assertEqual(decision["hooks"], [])
            self.assertIn("auth_required", decision["reason"])

    def test_plugin_runtime_codex_exec_adapter_classifies_network_blocker(self) -> None:
        scenarios = dispatcher_script.load_scenario_corpus()

        with tempfile.TemporaryDirectory() as tmp:
            fixture = fixture_script.build_fixture("clean_git_project", Path(tmp) / "fixture")
            payload = trigger_adapter_script.build_plugin_runtime_input(
                expression=scenarios["H1-P001"].expression,
                project_root=fixture.root,
                fixture_summary=fixture.summary,
            )
            proc = subprocess.CompletedProcess(
                args=["codex", "exec"],
                returncode=1,
                stdout="failed to lookup address information",
                stderr="",
            )

            with mock.patch.object(trigger_adapter_script.probe_plugin_runtime, "ensure_codex_binary"):
                with mock.patch.object(
                    trigger_adapter_script.probe_plugin_runtime,
                    "add_marketplace",
                    return_value={"status": "ok"},
                ):
                    with mock.patch.object(
                        trigger_adapter_script.probe_plugin_runtime,
                        "materialize_local_plugin_cache",
                        return_value={"status": "ok"},
                    ):
                        with mock.patch.object(
                            trigger_adapter_script.probe_plugin_runtime,
                            "enable_arbor_plugin",
                            return_value={"status": "ok"},
                        ):
                            with mock.patch.object(
                                trigger_adapter_script.probe_plugin_runtime,
                                "run_command",
                                return_value=proc,
                            ):
                                decision = trigger_adapter_script.run_codex_exec_trigger(
                                    payload,
                                    fixture.root,
                                    codex_bin=Path("/bin/codex"),
                                )

            self.assertEqual(decision["decision"], "ambiguous")
            self.assertEqual(decision["hooks"], [])
            self.assertTrue(decision["requires_agent_judgment"])
            self.assertIn("network_unavailable", decision["reason"])
            self.assertIn("returncode=1", decision["reason"])

    def test_plugin_runtime_codex_exec_adapter_redacts_sensitive_failure_details(self) -> None:
        proc = subprocess.CompletedProcess(
            args=["codex", "exec"],
            returncode=1,
            stdout="Authorization: Bearer secret-token\nordinary failure",
            stderr="api key leaked",
        )

        detail = trigger_adapter_script.runtime_failure_detail(proc)

        self.assertIn("returncode=1", detail)
        self.assertIn("ordinary failure", detail)
        self.assertIn("[redacted]", detail)
        self.assertNotIn("secret-token", detail)
        self.assertNotIn("api key leaked", detail)

    def test_plugin_runtime_codex_exec_adapter_blocks_and_restores_project_file_mutation(self) -> None:
        scenarios = dispatcher_script.load_scenario_corpus()

        def mutating_run_command(args: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
            output_path = Path(args[args.index("--output-last-message") + 1])
            project_root = Path(args[args.index("--cd") + 1])
            (project_root / "AGENTS.md").write_text("# Mutated Guide\n", encoding="utf-8")
            output_path.write_text(
                json.dumps(
                    {
                        "hooks": [],
                        "decision": "ambiguous",
                        "confidence": "low",
                        "requires_agent_judgment": True,
                        "optional_args": {},
                        "reason": "Valid JSON with an illegal project mutation.",
                    }
                ),
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="{}", stderr="")

        with tempfile.TemporaryDirectory() as tmp:
            fixture = fixture_script.build_fixture("clean_git_project", Path(tmp) / "fixture")
            original_agents = (fixture.root / "AGENTS.md").read_text(encoding="utf-8")
            payload = trigger_adapter_script.build_plugin_runtime_input(
                expression=scenarios["H1-P001"].expression,
                project_root=fixture.root,
                fixture_summary=fixture.summary,
            )

            with mock.patch.object(trigger_adapter_script.probe_plugin_runtime, "ensure_codex_binary"):
                with mock.patch.object(
                    trigger_adapter_script.probe_plugin_runtime,
                    "add_marketplace",
                    return_value={"status": "ok"},
                ):
                    with mock.patch.object(
                        trigger_adapter_script.probe_plugin_runtime,
                        "materialize_local_plugin_cache",
                        return_value={"status": "ok"},
                    ):
                        with mock.patch.object(
                            trigger_adapter_script.probe_plugin_runtime,
                            "enable_arbor_plugin",
                            return_value={"status": "ok"},
                        ):
                            with mock.patch.object(
                                trigger_adapter_script.probe_plugin_runtime,
                                "run_command",
                                side_effect=mutating_run_command,
                            ):
                                decision = trigger_adapter_script.run_codex_exec_trigger(
                                    payload,
                                    fixture.root,
                                    codex_bin=Path("/bin/codex"),
                                )

            self.assertEqual(decision["decision"], "ambiguous")
            self.assertEqual(decision["hooks"], [])
            self.assertIn("project_file_mutation:AGENTS.md", decision["reason"])
            self.assertEqual((fixture.root / "AGENTS.md").read_text(encoding="utf-8"), original_agents)

    def test_plugin_runtime_codex_exec_adapter_blocks_non_file_project_path_mutation(self) -> None:
        scenarios = dispatcher_script.load_scenario_corpus()

        def mutating_run_command(args: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
            output_path = Path(args[args.index("--output-last-message") + 1])
            project_root = Path(args[args.index("--cd") + 1])
            memory_path = project_root / ".codex" / "memory.md"
            memory_path.unlink()
            memory_path.mkdir()
            output_path.write_text(
                json.dumps(
                    {
                        "hooks": [],
                        "decision": "ambiguous",
                        "confidence": "low",
                        "requires_agent_judgment": True,
                        "optional_args": {},
                        "reason": "Valid JSON with an illegal project path mutation.",
                    }
                ),
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="{}", stderr="")

        with tempfile.TemporaryDirectory() as tmp:
            fixture = fixture_script.build_fixture("clean_git_project", Path(tmp) / "fixture")
            memory_path = fixture.root / ".codex" / "memory.md"
            original_memory = memory_path.read_text(encoding="utf-8")
            payload = trigger_adapter_script.build_plugin_runtime_input(
                expression=scenarios["H1-P001"].expression,
                project_root=fixture.root,
                fixture_summary=fixture.summary,
            )

            with mock.patch.object(trigger_adapter_script.probe_plugin_runtime, "ensure_codex_binary"):
                with mock.patch.object(
                    trigger_adapter_script.probe_plugin_runtime,
                    "add_marketplace",
                    return_value={"status": "ok"},
                ):
                    with mock.patch.object(
                        trigger_adapter_script.probe_plugin_runtime,
                        "materialize_local_plugin_cache",
                        return_value={"status": "ok"},
                    ):
                        with mock.patch.object(
                            trigger_adapter_script.probe_plugin_runtime,
                            "enable_arbor_plugin",
                            return_value={"status": "ok"},
                        ):
                            with mock.patch.object(
                                trigger_adapter_script.probe_plugin_runtime,
                                "run_command",
                                side_effect=mutating_run_command,
                            ):
                                decision = trigger_adapter_script.run_codex_exec_trigger(
                                    payload,
                                    fixture.root,
                                    codex_bin=Path("/bin/codex"),
                                )

            self.assertEqual(decision["decision"], "ambiguous")
            self.assertEqual(decision["hooks"], [])
            self.assertIn("project_file_mutation:.codex/memory.md", decision["reason"])
            self.assertTrue(memory_path.is_file())
            self.assertEqual(memory_path.read_text(encoding="utf-8"), original_memory)

    def test_harness_accepts_plugin_runtime_codex_exec_adapter_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(
                trigger_adapter_script,
                "plugin_runtime_codex_exec_trigger",
                return_value=trigger_adapter_script.runtime_blocker_decision("network_unavailable"),
            ):
                result = harness_script.evaluate_scenario(
                    "H1-P001",
                    Path(tmp),
                    trigger_adapter="plugin-runtime-codex-exec",
                )

            self.assertTrue(result["passed"])
            self.assertEqual(result["trigger_adapter"], "plugin-runtime-codex-exec")
            self.assertEqual(result["trigger_decision"]["decision"], "ambiguous")
            self.assertEqual(result["executions"], [])

    def test_harness_smoke_expectations_fail_runtime_blocker_positive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(
                trigger_adapter_script,
                "plugin_runtime_codex_exec_trigger",
                return_value=trigger_adapter_script.runtime_blocker_decision("network_unavailable"),
            ):
                result = harness_script.evaluate_scenario(
                    "H1-P001",
                    Path(tmp),
                    trigger_adapter="plugin-runtime-codex-exec",
                )

            strict = harness_script.apply_smoke_expectations(
                result,
                expected_decision="trigger",
                expected_hooks=["arbor.session_startup_context"],
                require_runtime_available=True,
            )

            self.assertTrue(result["passed"])
            self.assertFalse(strict["passed"])
            self.assertEqual(
                [item["name"] for item in strict["smoke_assertions"]],
                ["runtime_available", "expected_decision", "expected_hooks"],
            )
            self.assertFalse(strict["smoke_assertions"][0]["passed"])
            self.assertFalse(strict["smoke_assertions"][1]["passed"])
            self.assertFalse(strict["smoke_assertions"][2]["passed"])

    def test_harness_forwards_runtime_options_to_plugin_runtime_adapter(self) -> None:
        options = trigger_adapter_script.RuntimeAdapterOptions(
            codex_bin=Path("/bin/codex"),
            timeout_seconds=7,
            auth_source_home=Path("/tmp/auth-home"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(
                trigger_adapter_script,
                "plugin_runtime_codex_exec_trigger",
                return_value=trigger_adapter_script.runtime_blocker_decision("network_unavailable"),
            ) as trigger_mock:
                harness_script.evaluate_scenario(
                    "H1-P001",
                    Path(tmp),
                    trigger_adapter="plugin-runtime-codex-exec",
                    runtime_options=options,
                )

        self.assertIs(trigger_mock.call_args.kwargs["runtime_options"], options)

    def test_harness_parser_accepts_plugin_runtime_auth_options(self) -> None:
        args = harness_script.build_parser().parse_args(
            [
                "--scenario-id",
                "H1-P001",
                "--work-root",
                "/tmp/arbor-runtime",
                "--trigger-adapter",
                "plugin-runtime-codex-exec",
                "--auth-source-home",
                "~",
                "--runtime-timeout",
                "90",
                "--codex-bin",
                "/bin/codex",
            ]
        )

        self.assertEqual(args.auth_source_home, Path("~"))
        self.assertEqual(args.runtime_timeout, 90)
        self.assertEqual(args.codex_bin, Path("/bin/codex"))

    def test_harness_parser_rejects_non_positive_runtime_timeout(self) -> None:
        with self.assertRaises(SystemExit):
            harness_script.build_parser().parse_args(
                [
                    "--scenario-id",
                    "H1-P001",
                    "--work-root",
                    "/tmp/arbor-runtime",
                    "--trigger-adapter",
                    "plugin-runtime-codex-exec",
                    "--runtime-timeout",
                    "0",
                ]
            )

    def test_harness_parser_accepts_smoke_expectation_flags(self) -> None:
        args = harness_script.build_parser().parse_args(
            [
                "--scenario-id",
                "H1-P001",
                "--work-root",
                "/tmp/arbor-runtime",
                "--trigger-adapter",
                "plugin-runtime-codex-exec",
                "--expect-decision",
                "trigger",
                "--expect-hooks",
                "arbor.session_startup_context",
                "--require-runtime-available",
            ]
        )

        self.assertEqual(args.expect_decision, "trigger")
        self.assertEqual(args.expect_hooks, ["arbor.session_startup_context"])
        self.assertTrue(args.require_runtime_available)

    def test_harness_parser_accepts_selected_scenario_ids_and_progress_path(self) -> None:
        args = harness_script.build_parser().parse_args(
            [
                "--scenario-ids",
                "H1-P001,N-P001",
                "--work-root",
                "/tmp/arbor-runtime",
                "--progress-jsonl",
                "/tmp/progress.jsonl",
            ]
        )

        self.assertEqual(args.scenario_ids, ["H1-P001", "N-P001"])
        self.assertEqual(args.progress_jsonl, Path("/tmp/progress.jsonl"))

    def test_adapter_rejects_unknown_hook_id(self) -> None:
        dispatch = {
            "hooks": ["arbor.unknown"],
            "decision": "trigger",
            "confidence": "high",
            "requires_agent_judgment": False,
            "optional_args": {},
            "reason": "invalid hook",
        }

        with self.assertRaisesRegex(trigger_adapter_script.AdapterError, "unknown hook"):
            trigger_adapter_script.validate_trigger_decision_contract(dispatch)

    def test_adapter_rejects_invalid_decision_and_confidence(self) -> None:
        dispatch = {
            "hooks": [],
            "decision": "maybe",
            "confidence": "certain",
            "requires_agent_judgment": False,
            "optional_args": {},
            "reason": "invalid vocabulary",
        }

        with self.assertRaisesRegex(trigger_adapter_script.AdapterError, "invalid trigger decision"):
            trigger_adapter_script.validate_trigger_decision_contract(dispatch)

    def test_adapter_schema_optional_args_are_strict_output_schema_compatible(self) -> None:
        optional_args_schema = trigger_adapter_script.TRIGGER_DECISION_SCHEMA["properties"]["optional_args"]

        self.assertFalse(optional_args_schema["additionalProperties"])
        self.assertEqual(set(optional_args_schema["required"]), ARBOR_HOOK_IDS)
        self.assertEqual(set(optional_args_schema["properties"]), ARBOR_HOOK_IDS)

    def test_adapter_accepts_empty_schema_required_optional_args_for_unselected_hooks(self) -> None:
        dispatch = {
            "hooks": [],
            "decision": "none",
            "confidence": "high",
            "requires_agent_judgment": False,
            "optional_args": {hook_id: [] for hook_id in sorted(ARBOR_HOOK_IDS)},
            "reason": "schema-compatible empty optional args",
        }

        normalized = trigger_adapter_script.validate_trigger_decision_contract(dispatch)

        self.assertEqual(normalized["optional_args"], {})

    def test_adapter_normalizes_bare_agents_drift_doc_paths(self) -> None:
        dispatch = {
            "hooks": ["arbor.goal_constraint_drift"],
            "decision": "trigger",
            "confidence": "high",
            "requires_agent_judgment": False,
            "optional_args": {
                "arbor.goal_constraint_drift": ["docs/constraints.md", "docs/workflow.md"],
            },
            "reason": "Project goal or constraints may have changed.",
        }

        normalized = trigger_adapter_script.validate_trigger_decision_contract(dispatch)

        self.assertEqual(
            normalized["optional_args"],
            {
                "arbor.goal_constraint_drift": [
                    "--doc",
                    "docs/constraints.md",
                    "--doc",
                    "docs/workflow.md",
                ],
            },
        )

    def test_adapter_normalizes_joined_agents_drift_doc_flag(self) -> None:
        dispatch = {
            "hooks": ["arbor.goal_constraint_drift"],
            "decision": "trigger",
            "confidence": "high",
            "requires_agent_judgment": False,
            "optional_args": {
                "arbor.goal_constraint_drift": ["--doc docs/project-map.md", "--doc=docs/workflow.md"],
            },
            "reason": "Project map may need durable updates.",
        }

        normalized = trigger_adapter_script.validate_trigger_decision_contract(dispatch)

        self.assertEqual(
            normalized["optional_args"],
            {
                "arbor.goal_constraint_drift": [
                    "--doc",
                    "docs/project-map.md",
                    "--doc",
                    "docs/workflow.md",
                ],
            },
        )

    def test_adapter_normalizes_joined_memory_diff_args(self) -> None:
        dispatch = {
            "hooks": ["arbor.in_session_memory_hygiene"],
            "decision": "trigger",
            "confidence": "high",
            "requires_agent_judgment": False,
            "optional_args": {
                "arbor.in_session_memory_hygiene": ["--diff-args --stat"],
            },
            "reason": "Memory may be stale against uncommitted work.",
        }

        normalized = trigger_adapter_script.validate_trigger_decision_contract(dispatch)

        self.assertEqual(
            normalized["optional_args"],
            {"arbor.in_session_memory_hygiene": ["--diff-args=--stat"]},
        )

    def test_adapter_normalizes_split_memory_diff_args_with_dash_value(self) -> None:
        dispatch = {
            "hooks": ["arbor.in_session_memory_hygiene"],
            "decision": "trigger",
            "confidence": "high",
            "requires_agent_judgment": False,
            "optional_args": {
                "arbor.in_session_memory_hygiene": ["--diff-args", "--stat"],
            },
            "reason": "Memory should inspect a selected diff stat.",
        }

        normalized = trigger_adapter_script.validate_trigger_decision_contract(dispatch)

        self.assertEqual(
            normalized["optional_args"],
            {"arbor.in_session_memory_hygiene": ["--diff-args=--stat"]},
        )

    def test_adapter_normalizes_bare_memory_diff_args_with_dash_value(self) -> None:
        dispatch = {
            "hooks": ["arbor.in_session_memory_hygiene"],
            "decision": "trigger",
            "confidence": "high",
            "requires_agent_judgment": True,
            "optional_args": {
                "arbor.in_session_memory_hygiene": ["-- fix-parser.txt"],
            },
            "reason": "Memory should inspect a file-scoped diff.",
        }

        normalized = trigger_adapter_script.validate_trigger_decision_contract(dispatch)

        self.assertEqual(
            normalized["optional_args"],
            {"arbor.in_session_memory_hygiene": ["--diff-args=-- fix-parser.txt"]},
        )

    def test_adapter_normalizes_bare_memory_diff_args_stat_value(self) -> None:
        dispatch = self.trigger_decision(
            "arbor.in_session_memory_hygiene",
            {"arbor.in_session_memory_hygiene": ["--stat"]},
        )

        normalized = trigger_adapter_script.validate_trigger_decision_contract(dispatch)

        self.assertEqual(
            normalized["optional_args"],
            {"arbor.in_session_memory_hygiene": ["--diff-args=--stat"]},
        )

    def test_adapter_normalizes_bare_memory_diff_args_natural_language_value(self) -> None:
        dispatch = self.trigger_decision(
            "arbor.in_session_memory_hygiene",
            {
                "arbor.in_session_memory_hygiene": [
                    "include current uncommitted patch for tracked.txt and pending.txt",
                ],
            },
        )

        normalized = trigger_adapter_script.validate_trigger_decision_contract(dispatch)

        self.assertEqual(
            normalized["optional_args"],
            {
                "arbor.in_session_memory_hygiene": [
                    "--diff-args=include current uncommitted patch for tracked.txt and pending.txt",
                ],
            },
        )

    def test_adapter_preserves_git_log_args_value_with_spaces(self) -> None:
        dispatch = {
            "hooks": ["arbor.session_startup_context"],
            "decision": "trigger",
            "confidence": "high",
            "requires_agent_judgment": False,
            "optional_args": {
                "arbor.session_startup_context": [
                    "--git-log-args=--max-count=10 --decorate --oneline",
                ],
            },
            "reason": "Session startup should collect long-term project context.",
        }

        normalized = trigger_adapter_script.validate_trigger_decision_contract(dispatch)

        self.assertEqual(
            normalized["optional_args"],
            {
                "arbor.session_startup_context": [
                    "--git-log-args=--max-count=10 --decorate --oneline",
                ],
            },
        )

    def test_adapter_normalizes_bare_git_log_args_value_with_spaces(self) -> None:
        dispatch = {
            "hooks": ["arbor.session_startup_context"],
            "decision": "trigger",
            "confidence": "high",
            "requires_agent_judgment": True,
            "optional_args": {
                "arbor.session_startup_context": [
                    "--max-count=10 --decorate --oneline",
                ],
            },
            "reason": "Session startup should collect a selected git log shape.",
        }

        normalized = trigger_adapter_script.validate_trigger_decision_contract(dispatch)

        self.assertEqual(
            normalized["optional_args"],
            {
                "arbor.session_startup_context": [
                    "--git-log-args=--max-count=10 --decorate --oneline",
                ],
            },
        )

    def test_adapter_normalizes_split_git_log_args_with_dash_value(self) -> None:
        dispatch = {
            "hooks": ["arbor.session_startup_context"],
            "decision": "trigger",
            "confidence": "high",
            "requires_agent_judgment": False,
            "optional_args": {
                "arbor.session_startup_context": [
                    "--git-log-args",
                    "--max-count=10 --decorate --oneline",
                ],
            },
            "reason": "Session startup should collect a selected git log shape.",
        }

        normalized = trigger_adapter_script.validate_trigger_decision_contract(dispatch)

        self.assertEqual(
            normalized["optional_args"],
            {
                "arbor.session_startup_context": [
                    "--git-log-args=--max-count=10 --decorate --oneline",
                ],
            },
        )

    def test_adapter_rejects_lone_agents_drift_doc_flag(self) -> None:
        dispatch = self.trigger_decision(
            "arbor.goal_constraint_drift",
            {"arbor.goal_constraint_drift": ["--doc"]},
        )

        with self.assertRaisesRegex(trigger_adapter_script.AdapterError, "--doc requires"):
            trigger_adapter_script.validate_trigger_decision_contract(dispatch)

    def test_adapter_rejects_empty_agents_drift_doc_equals_value(self) -> None:
        dispatch = self.trigger_decision(
            "arbor.goal_constraint_drift",
            {"arbor.goal_constraint_drift": ["--doc="]},
        )

        with self.assertRaisesRegex(trigger_adapter_script.AdapterError, "--doc requires"):
            trigger_adapter_script.validate_trigger_decision_contract(dispatch)

    def test_adapter_rejects_unknown_agents_drift_optional_flag(self) -> None:
        dispatch = self.trigger_decision(
            "arbor.goal_constraint_drift",
            {"arbor.goal_constraint_drift": ["--doc-paths", "docs/constraints.md"]},
        )

        with self.assertRaisesRegex(trigger_adapter_script.AdapterError, "unknown optional arg"):
            trigger_adapter_script.validate_trigger_decision_contract(dispatch)

    def test_adapter_drops_lone_memory_diff_args_flag(self) -> None:
        dispatch = self.trigger_decision(
            "arbor.in_session_memory_hygiene",
            {"arbor.in_session_memory_hygiene": ["--diff-args"]},
        )

        normalized = trigger_adapter_script.validate_trigger_decision_contract(dispatch)

        self.assertEqual(normalized["optional_args"], {})

    def test_adapter_drops_lone_startup_git_log_args_flag(self) -> None:
        dispatch = self.trigger_decision(
            "arbor.session_startup_context",
            {"arbor.session_startup_context": ["--git-log-args"]},
        )

        normalized = trigger_adapter_script.validate_trigger_decision_contract(dispatch)

        self.assertEqual(normalized["optional_args"], {})

    def test_adapter_drops_empty_memory_diff_args_value(self) -> None:
        dispatch = self.trigger_decision(
            "arbor.in_session_memory_hygiene",
            {"arbor.in_session_memory_hygiene": ["   "]},
        )

        normalized = trigger_adapter_script.validate_trigger_decision_contract(dispatch)

        self.assertEqual(normalized["optional_args"], {})

    def test_adapter_drops_lone_memory_diff_pathspec_separator(self) -> None:
        dispatch = self.trigger_decision(
            "arbor.in_session_memory_hygiene",
            {"arbor.in_session_memory_hygiene": ["--"]},
        )

        normalized = trigger_adapter_script.validate_trigger_decision_contract(dispatch)

        self.assertEqual(normalized["optional_args"], {})

    def test_adapter_drops_lone_startup_git_log_pathspec_separator(self) -> None:
        dispatch = self.trigger_decision(
            "arbor.session_startup_context",
            {"arbor.session_startup_context": ["--git-log-args=--"]},
        )

        normalized = trigger_adapter_script.validate_trigger_decision_contract(dispatch)

        self.assertEqual(normalized["optional_args"], {})

    def test_adapter_rejects_optional_args_for_unselected_hooks(self) -> None:
        dispatch = {
            "hooks": [],
            "decision": "none",
            "confidence": "high",
            "requires_agent_judgment": False,
            "optional_args": {"arbor.goal_constraint_drift": ["--doc", "docs/constraints.md"]},
            "reason": "invalid optional args",
        }

        with self.assertRaisesRegex(trigger_adapter_script.AdapterError, "optional_args keys"):
            trigger_adapter_script.validate_trigger_decision_contract(dispatch)


class PluginInstallationReadinessTests(unittest.TestCase):
    def copy_plugin_install_surface(self, destination: Path) -> Path:
        repo = destination / "repo"
        repo.mkdir()
        shutil.copytree(ROOT / ".agents", repo / ".agents")
        plugin_parent = repo / "plugins"
        plugin_parent.mkdir()
        shutil.copytree(PLUGIN_ROOT, plugin_parent / "arbor")
        return repo

    def test_plugin_install_validation_resolves_marketplace_and_payload(self) -> None:
        result = plugin_install_script.validate_plugin_install(ROOT)

        self.assertEqual(result["marketplace"]["name"], "arbor-local")
        self.assertEqual(result["manifest"]["name"], "arbor")
        self.assertEqual(
            set(result["payload"]["hook_ids"]),
            {
                "arbor.session_startup_context",
                "arbor.in_session_memory_hygiene",
                "arbor.goal_constraint_drift",
            },
        )
        self.assertGreater(result["payload"]["inventory"]["file_count"], 0)
        self.assertTrue(result["payload"]["inventory"]["matches_expected_payload"])
        self.assertIn("skills/arbor/SKILL.md", result["payload"]["inventory"]["files"])
        self.assertEqual(result["codex_marketplace_probe"], {"skipped": True})

    def test_plugin_packaged_skill_smoke_executes_all_hook_entrypoints(self) -> None:
        result = plugin_install_script.validate_plugin_install(ROOT)

        self.assertEqual(
            result["packaged_skill_smoke"]["initialized"],
            ["AGENTS.md", ".codex/memory.md"],
        )
        self.assertEqual(
            [item["hook_id"] for item in result["packaged_skill_smoke"]["hook_smokes"]],
            [
                "arbor.session_startup_context",
                "arbor.in_session_memory_hygiene",
                "arbor.goal_constraint_drift",
            ],
        )

    def test_plugin_install_validation_rejects_drifted_install_surfaces(self) -> None:
        def mutate_marketplace_duplicate(repo: Path) -> str:
            path = repo / ".agents" / "plugins" / "marketplace.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["plugins"].append(dict(data["plugins"][0]))
            path.write_text(json.dumps(data), encoding="utf-8")
            return "exactly one arbor"

        def mutate_manifest_skill_path(repo: Path) -> str:
            path = repo / "plugins" / "arbor" / ".codex-plugin" / "plugin.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["skills"] = "./not-skills/"
            path.write_text(json.dumps(data), encoding="utf-8")
            return "skills path"

        def mutate_missing_hook_script(repo: Path) -> str:
            path = repo / "plugins" / "arbor" / "hooks.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["hooks"][0]["entrypoint"]["script"] = "scripts/missing.py"
            path.write_text(json.dumps(data), encoding="utf-8")
            return "hook script missing"

        def mutate_hook_script_escape(repo: Path) -> str:
            path = repo / "plugins" / "arbor" / "hooks.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["hooks"][0]["entrypoint"]["script"] = "../../hooks.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            return "escapes packaged skill root"

        def mutate_hook_script_non_python(repo: Path) -> str:
            path = repo / "plugins" / "arbor" / "hooks.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["hooks"][0]["entrypoint"]["script"] = "SKILL.md"
            path.write_text(json.dumps(data), encoding="utf-8")
            return "Python file"

        def mutate_duplicate_hook_row(repo: Path) -> str:
            path = repo / "plugins" / "arbor" / "hooks.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["hooks"].append(dict(data["hooks"][0]))
            path.write_text(json.dumps(data), encoding="utf-8")
            return "exactly 3 entries"

        def mutate_non_object_hook_row(repo: Path) -> str:
            path = repo / "plugins" / "arbor" / "hooks.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["hooks"][0] = "not-a-hook-object"
            path.write_text(json.dumps(data), encoding="utf-8")
            return "hook entry must be an object"

        def mutate_duplicate_hook_id_without_extra_count(repo: Path) -> str:
            path = repo / "plugins" / "arbor" / "hooks.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["hooks"][1]["id"] = data["hooks"][0]["id"]
            path.write_text(json.dumps(data), encoding="utf-8")
            return "duplicate packaged hook ids"

        def mutate_transient_payload_cache(repo: Path) -> str:
            path = (
                repo
                / "plugins"
                / "arbor"
                / "skills"
                / "arbor"
                / "scripts"
                / "__pycache__"
                / "collect_project_context.cpython-312.pyc"
            )
            path.parent.mkdir()
            path.write_bytes(b"not real bytecode")
            return "transient payload artifact"

        def mutate_unexpected_payload_file(repo: Path) -> str:
            path = repo / "plugins" / "arbor" / "skills" / "arbor" / "README.md"
            path.write_text("extra release doc\n", encoding="utf-8")
            return "unexpected packaged payload file"

        def mutate_expected_file_symlink_escape(repo: Path) -> str:
            outside = repo.parent / "outside-memory-template.md"
            outside.write_text("outside payload\n", encoding="utf-8")
            path = repo / "plugins" / "arbor" / "skills" / "arbor" / "references" / "memory-template.md"
            path.unlink()
            path.symlink_to(outside)
            return "symlink payload entry"

        def mutate_unexpected_symlink_directory(repo: Path) -> str:
            outside = repo.parent / "outside-dir"
            outside.mkdir()
            (outside / "ignored.txt").write_text("outside payload\n", encoding="utf-8")
            path = repo / "plugins" / "arbor" / "outside_link"
            path.symlink_to(outside, target_is_directory=True)
            return "symlink payload entry"

        def mutate_unexpected_payload_directory(repo: Path) -> str:
            path = repo / "plugins" / "arbor" / "extra-empty-dir"
            path.mkdir()
            return "unexpected packaged payload directories"

        mutations = [
            mutate_marketplace_duplicate,
            mutate_manifest_skill_path,
            mutate_missing_hook_script,
            mutate_hook_script_escape,
            mutate_hook_script_non_python,
            mutate_duplicate_hook_row,
            mutate_non_object_hook_row,
            mutate_duplicate_hook_id_without_extra_count,
            mutate_transient_payload_cache,
            mutate_unexpected_payload_file,
            mutate_expected_file_symlink_escape,
            mutate_unexpected_symlink_directory,
            mutate_unexpected_payload_directory,
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate.__name__):
                with tempfile.TemporaryDirectory() as tmp:
                    repo = self.copy_plugin_install_surface(Path(tmp))
                    expected_error = mutate(repo)

                    with self.assertRaisesRegex(plugin_install_script.PluginInstallValidationError, expected_error):
                        plugin_install_script.validate_plugin_install(repo)


class PluginRuntimeProbeTests(unittest.TestCase):
    def installed_skill_stdout(self, home: Path) -> str:
        skill_path = (
            home
            / ".codex"
            / "plugins"
            / "cache"
            / "arbor-local"
            / "arbor"
            / "0.1.0"
            / "skills"
            / "arbor"
            / "SKILL.md"
        )
        return f'{{"type":"event","path":"{skill_path}"}}\nARBOR_RUNTIME_PROBE_OK'

    def write_probe_files(self, project: Path, hooks: list[dict[str, object]]) -> None:
        (project / ".codex").mkdir(parents=True, exist_ok=True)
        (project / "AGENTS.md").write_text("# Agent Guide\n", encoding="utf-8")
        (project / ".codex" / "memory.md").write_text("# Session Memory\n", encoding="utf-8")
        (project / ".codex" / "hooks.json").write_text(json.dumps({"hooks": hooks}), encoding="utf-8")

    def test_probe_copies_auth_into_isolated_home_only_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_home = Path(tmp) / "source-home"
            target_home = Path(tmp) / "target-home"
            (source_home / ".codex").mkdir(parents=True)
            target_home.mkdir()
            (source_home / ".codex" / "auth.json").write_text('{"token":"redacted"}\n', encoding="utf-8")

            result = plugin_runtime_probe_script.copy_runtime_auth(source_home, target_home)

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["copied_files"], ["auth.json"])
            self.assertEqual((target_home / ".codex" / "auth.json").read_text(encoding="utf-8"), '{"token":"redacted"}\n')
            self.assertFalse((target_home / ".codex" / "config.toml").exists())

    def test_probe_reports_missing_requested_auth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_home = Path(tmp) / "source-home"
            target_home = Path(tmp) / "target-home"
            source_home.mkdir()
            target_home.mkdir()

            result = plugin_runtime_probe_script.copy_runtime_auth(source_home, target_home)

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["reason"], "missing auth file(s)")
            self.assertEqual(result["missing_files"], ["auth.json"])

    def test_probe_enables_arbor_plugin_in_isolated_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            codex_home = home / ".codex"
            codex_home.mkdir(parents=True)
            config_path = codex_home / "config.toml"
            config_path.write_text(
                '[marketplaces.arbor-local]\nsource_type = "local"\nsource = "/repo"\n',
                encoding="utf-8",
            )

            result = plugin_runtime_probe_script.enable_arbor_plugin(home)

            self.assertEqual(result["status"], "ok")
            self.assertIn('[plugins."arbor@arbor-local"]', config_path.read_text(encoding="utf-8"))
            self.assertIn("enabled = true", config_path.read_text(encoding="utf-8"))

    def test_probe_materializes_local_plugin_cache_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()

            result = plugin_runtime_probe_script.materialize_local_plugin_cache(ROOT, home)

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["plugin_id"], "arbor@arbor-local")
            cache_entry = Path(result["cache_entry"])
            self.assertTrue((cache_entry / ".codex-plugin" / "plugin.json").is_file())
            self.assertTrue((cache_entry / "skills" / "arbor" / "SKILL.md").is_file())
            self.assertEqual(cache_entry.parent, home / ".codex" / "plugins" / "cache" / "arbor-local" / "arbor")

    def test_probe_marks_isolated_project_trusted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            project = Path(tmp) / "project"
            (home / ".codex").mkdir(parents=True)
            project.mkdir()
            config_path = home / ".codex" / "config.toml"
            config_path.write_text('[marketplaces.arbor-local]\nsource_type = "local"\n', encoding="utf-8")

            result = plugin_runtime_probe_script.trust_project(home, project)

            self.assertEqual(result["status"], "ok")
            self.assertIn(f'[projects."{project.resolve()}"]', config_path.read_text(encoding="utf-8"))
            self.assertIn('trust_level = "trusted"', config_path.read_text(encoding="utf-8"))

    def test_probe_classifies_network_exec_failure(self) -> None:
        proc = subprocess.CompletedProcess(
            args=["codex", "exec"],
            returncode=1,
            stdout="failed to lookup address information",
            stderr="Could not resolve host: github.com",
        )

        self.assertEqual(plugin_runtime_probe_script.classify_exec_failure(proc), "network_unavailable")

    def test_probe_exec_reports_missing_plugin_side_effects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            home = Path(tmp) / "home"
            home.mkdir()
            proc = subprocess.CompletedProcess(
                args=["codex", "exec"],
                returncode=0,
                stdout='{"type":"agent_message","message":"ARBOR_RUNTIME_PROBE_OK"}',
                stderr="",
            )

            with mock.patch.object(plugin_runtime_probe_script, "run_command", return_value=proc):
                result = plugin_runtime_probe_script.run_exec_probe(
                    project_root=project,
                    home=home,
                    codex_bin=Path("/bin/codex"),
                    prompt="probe",
                    timeout_seconds=1,
                )

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["reason"], "expected plugin side effects were not observed")
            self.assertEqual(
                result["missing_files"],
                ["AGENTS.md", ".codex/memory.md", ".codex/hooks.json"],
            )

    def test_probe_exec_timeout_is_classified_as_blocked_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            home = Path(tmp) / "home"
            home.mkdir()

            with mock.patch.object(
                plugin_runtime_probe_script,
                "run_command",
                side_effect=subprocess.TimeoutExpired(cmd=["codex", "exec"], timeout=1),
            ):
                result = plugin_runtime_probe_script.run_exec_probe(
                    project_root=project,
                    home=home,
                    codex_bin=Path("/bin/codex"),
                    prompt="probe",
                    timeout_seconds=1,
                )

            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["reason"], "timeout")
            self.assertIsNone(result["returncode"])
            self.assertEqual(
                result["missing_files"],
                ["AGENTS.md", ".codex/memory.md", ".codex/hooks.json"],
            )

    def test_probe_exec_rejects_empty_hook_registration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            home = Path(tmp) / "home"
            home.mkdir()

            def fake_run_command(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
                self.write_probe_files(project, [])
                return subprocess.CompletedProcess(
                    args=["codex", "exec"],
                    returncode=0,
                    stdout=self.installed_skill_stdout(home),
                    stderr="",
                )

            with mock.patch.object(plugin_runtime_probe_script, "run_command", side_effect=fake_run_command):
                result = plugin_runtime_probe_script.run_exec_probe(
                    project_root=project,
                    home=home,
                    codex_bin=Path("/bin/codex"),
                    prompt="probe",
                    timeout_seconds=1,
                )

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["reason"], "expected Arbor hook registrations were not observed")
            self.assertEqual(result["registered_hook_ids"], [])
            self.assertEqual(sorted(result["missing_hook_ids"]), sorted(ARBOR_HOOK_IDS))

    def test_probe_exec_rejects_preexisting_project_files_before_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            self.write_probe_files(
                project,
                [{"id": hook_id, "owner": "arbor"} for hook_id in sorted(ARBOR_HOOK_IDS)],
            )
            home = Path(tmp) / "home"
            home.mkdir()

            with mock.patch.object(plugin_runtime_probe_script, "run_command") as run_mock:
                result = plugin_runtime_probe_script.run_exec_probe(
                    project_root=project,
                    home=home,
                    codex_bin=Path("/bin/codex"),
                    prompt="probe",
                    timeout_seconds=1,
                )

            run_mock.assert_not_called()
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["reason"], "probe project must not contain pre-existing Arbor side-effect files")
            self.assertEqual(
                result["preexisting_files"],
                ["AGENTS.md", ".codex/memory.md", ".codex/hooks.json"],
            )

    def test_probe_exec_rejects_marker_and_side_effects_without_injection_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            home = Path(tmp) / "home"
            home.mkdir()

            def fake_run_command(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
                self.write_probe_files(
                    project,
                    [{"id": hook_id, "owner": "arbor"} for hook_id in sorted(ARBOR_HOOK_IDS)],
                )
                return subprocess.CompletedProcess(
                    args=["codex", "exec"],
                    returncode=0,
                    stdout="ARBOR_RUNTIME_PROBE_OK",
                    stderr="",
                )

            with mock.patch.object(plugin_runtime_probe_script, "run_command", side_effect=fake_run_command):
                result = plugin_runtime_probe_script.run_exec_probe(
                    project_root=project,
                    home=home,
                    codex_bin=Path("/bin/codex"),
                    prompt="probe",
                    timeout_seconds=1,
                )

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["reason"], "expected installed Arbor skill injection was not observed")
            self.assertFalse(result["injection_seen"])

    def test_probe_exec_passes_when_installed_runtime_creates_project_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            home = Path(tmp) / "home"
            home.mkdir()

            def fake_run_command(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
                self.write_probe_files(
                    project,
                    [{"id": hook_id, "owner": "arbor"} for hook_id in sorted(ARBOR_HOOK_IDS)],
                )
                return subprocess.CompletedProcess(
                    args=["codex", "exec"],
                    returncode=0,
                    stdout=self.installed_skill_stdout(home),
                    stderr="",
                )

            with mock.patch.object(plugin_runtime_probe_script, "run_command", side_effect=fake_run_command):
                result = plugin_runtime_probe_script.run_exec_probe(
                    project_root=project,
                    home=home,
                    codex_bin=Path("/bin/codex"),
                    prompt="probe",
                    timeout_seconds=1,
                )

            self.assertEqual(result["status"], "passed")
            self.assertTrue(result["injection_seen"])
            self.assertEqual(result["preexisting_files"], [])
            self.assertEqual(result["missing_files"], [])
            self.assertEqual(set(result["registered_hook_ids"]), ARBOR_HOOK_IDS)
            self.assertEqual(result["missing_hook_ids"], [])
            self.assertEqual(
                result["created_files"],
                ["AGENTS.md", ".codex/memory.md", ".codex/hooks.json"],
            )

    def test_full_probe_skips_exec_by_default_after_install_enable(self) -> None:
        add_result = {
            "status": "ok",
            "returncode": 0,
            "stdout": "Added marketplace",
            "stderr": "",
            "config_path": "config.toml",
        }
        enable_result = {"status": "ok", "plugin_id": "arbor@arbor-local"}
        cache_result = {"status": "ok", "plugin_id": "arbor@arbor-local", "cache_entry": "cache"}

        with mock.patch.object(plugin_runtime_probe_script, "ensure_codex_binary"):
            with mock.patch.object(plugin_runtime_probe_script, "add_marketplace", return_value=add_result):
                with mock.patch.object(
                    plugin_runtime_probe_script,
                    "materialize_local_plugin_cache",
                    return_value=cache_result,
                ):
                    with mock.patch.object(plugin_runtime_probe_script, "enable_arbor_plugin", return_value=enable_result):
                        result = plugin_runtime_probe_script.run_plugin_runtime_probe(
                            repo_root=ROOT,
                            codex_bin=Path("/bin/codex"),
                        )

        self.assertEqual(result["marketplace"], add_result)
        self.assertEqual(result["plugin_cache"], cache_result)
        self.assertEqual(result["plugin_enable"], enable_result)
        self.assertEqual(result["exec_probe"]["status"], "skipped")


class HookTriggerExecutionHarnessTests(unittest.TestCase):
    def semantic_ready_report(self, results: list[dict[str, object]]) -> dict[str, object]:
        summary = harness_script.summarize_corpus_results(results, "plugin-runtime-codex-exec")
        return {
            "report_type": "plugin_trigger_adapter_hook_execution",
            "trigger_adapter": "plugin-runtime-codex-exec",
            "summary": summary,
            "scenarios": results,
            "passed": summary["passed_scenarios"] == summary["total_scenarios"],
        }

    def test_harness_executes_registered_h1_hook(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = harness_script.evaluate_scenario("H1-P001", Path(tmp))

            self.assertTrue(result["passed"])
            self.assertEqual(result["trigger_adapter"], "sidecar-baseline")
            self.assertEqual(result["trigger_decision"]["hooks"], ["arbor.session_startup_context"])
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
            self.assertEqual(result["trigger_decision"]["hooks"], ["arbor.in_session_memory_hygiene"])
            execution = result["executions"][0]
            self.assertIn("# Memory Hygiene Context", execution["stdout"])
            self.assertIn(" M tracked.txt", execution["stdout"])
            self.assertIn("?? pending.txt", execution["stdout"])

    def test_harness_executes_registered_h3_hook_with_selected_doc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = harness_script.evaluate_scenario("H3-P002", Path(tmp))

            self.assertTrue(result["passed"])
            self.assertEqual(result["trigger_decision"]["hooks"], ["arbor.goal_constraint_drift"])
            self.assertEqual(
                result["trigger_decision"]["optional_args"],
                {"arbor.goal_constraint_drift": ["--doc", "docs/constraints.md"]},
            )
            execution = result["executions"][0]
            self.assertIn("# AGENTS Guide Drift Context", execution["stdout"])
            self.assertIn("## 3. selected project doc: docs/constraints.md", execution["stdout"])

    def test_harness_skips_none_decision_without_hook_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = harness_script.evaluate_scenario("NM-P002", Path(tmp))

            self.assertTrue(result["passed"])
            self.assertEqual(result["trigger_decision"]["decision"], "none")
            self.assertEqual(result["trigger_decision"]["hooks"], [])
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
            self.assertEqual(result["trigger_decision"]["hooks"], ["arbor.session_startup_context"])

    def test_harness_full_corpus_report_summarizes_execution_quality(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = harness_script.evaluate_corpus(Path(tmp))

            summary = report["summary"]
            self.assertTrue(report["passed"])
            self.assertEqual(report["report_type"], "sidecar_baseline_hook_execution")
            self.assertEqual(report["trigger_adapter"], "sidecar-baseline")
            self.assertEqual(summary["total_scenarios"], 150)
            self.assertEqual(summary["passed_scenarios"], 150)
            self.assertEqual(summary["failed_scenarios"], [])
            self.assertGreater(summary["selected_hook_executions"], 0)
            self.assertEqual(summary["hook_execution_pass_rate"], 1.0)
            self.assertEqual(summary["outside_root_leaks"], 0)
            self.assertEqual(summary["unintended_write_failures"], 0)
            self.assertFalse(summary["semantic_metrics"]["reported"])
            self.assertFalse(summary["semantic_metrics"]["ready_for_semantic_metrics"])
            self.assertFalse(summary["semantic_metrics"]["gates"]["adapter_eligibility"]["passed"])
            self.assertEqual(len(report["scenarios"]), 150)
            self.assertNotIn("stdout", json.dumps(report["scenarios"][0]))

    def test_harness_runtime_blockers_fail_semantic_scoring_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(
                trigger_adapter_script,
                "plugin_runtime_codex_exec_trigger",
                return_value=trigger_adapter_script.runtime_blocker_decision("network_unavailable"),
            ):
                report = harness_script.evaluate_corpus(
                    Path(tmp),
                    trigger_adapter="plugin-runtime-codex-exec",
                )

            semantic_metrics = report["summary"]["semantic_metrics"]
            runtime_gate = semantic_metrics["gates"]["runtime_availability"]
            self.assertFalse(report["passed"])
            self.assertFalse(semantic_metrics["reported"])
            self.assertFalse(semantic_metrics["ready_for_semantic_metrics"])
            self.assertTrue(semantic_metrics["gates"]["adapter_eligibility"]["passed"])
            self.assertFalse(runtime_gate["passed"])
            self.assertEqual(runtime_gate["status"], "blocked")
            self.assertEqual(runtime_gate["blocked_scenario_count"], 150)
            self.assertEqual(runtime_gate["blocker_counts"], {"network_unavailable": 150})

    def test_harness_runtime_blocker_counts_ignore_diagnostic_detail(self) -> None:
        result = {
            "scenario_id": "H1-P001",
            "trigger_decision": trigger_adapter_script.runtime_blocker_decision(
                "runtime_failed",
                "returncode=1; output=details",
            ),
            "executions": [],
            "passed": True,
        }

        gate = harness_script.runtime_availability_gate("plugin-runtime-codex-exec", [result])

        self.assertEqual(gate["blocker_counts"], {"runtime_failed": 1})
        self.assertEqual(gate["blocked_scenarios"], [{"scenario_id": "H1-P001", "reason": "runtime_failed"}])

    def test_harness_semantic_scoring_gate_reports_metrics_when_ready(self) -> None:
        results = [
            {
                "scenario_id": "H1-P001",
                "expected_label": "H1",
                "trigger_decision": {
                    "decision": "trigger",
                    "hooks": ["arbor.session_startup_context"],
                    "requires_agent_judgment": False,
                    "reason": "Runtime selected startup context.",
                },
                "executions": [],
                "passed": True,
            },
            {
                "scenario_id": "N-P001",
                "expected_label": "NONE",
                "trigger_decision": {
                    "decision": "none",
                    "hooks": [],
                    "requires_agent_judgment": False,
                    "reason": "Runtime correctly ignored unrelated work.",
                },
                "executions": [],
                "passed": True,
            },
            {
                "scenario_id": "NM-P001",
                "expected_label": "NONE",
                "trigger_decision": {
                    "decision": "none",
                    "hooks": [],
                    "requires_agent_judgment": False,
                    "reason": "Runtime correctly ignored a near miss.",
                },
                "executions": [],
                "passed": True,
            },
            {
                "scenario_id": "M-P002",
                "expected_label": "MULTI",
                "trigger_decision": {
                    "decision": "trigger",
                    "hooks": ["arbor.session_startup_context", "arbor.in_session_memory_hygiene"],
                    "requires_agent_judgment": False,
                    "reason": "Runtime selected both required hooks.",
                },
                "executions": [],
                "passed": True,
            }
        ]
        execution_summary = {
            "hook_execution_pass_rate": 1.0,
            "outside_root_leaks": 0,
            "unintended_write_failures": 0,
            "assertion_failures": [],
        }

        semantic_metrics = harness_script.semantic_metric_status(
            "plugin-runtime-codex-exec",
            results,
            execution_summary,
        )

        self.assertTrue(semantic_metrics["reported"])
        self.assertTrue(semantic_metrics["passed"])
        self.assertTrue(semantic_metrics["ready_for_semantic_metrics"])
        self.assertTrue(semantic_metrics["gates"]["adapter_eligibility"]["passed"])
        self.assertTrue(semantic_metrics["gates"]["runtime_availability"]["passed"])
        self.assertTrue(semantic_metrics["gates"]["hook_execution"]["passed"])
        metrics = semantic_metrics["metrics"]
        self.assertEqual(metrics["scenario_count"], 4)
        self.assertEqual(metrics["failed_scenarios"], [])
        self.assertEqual(metrics["none_false_positive_rate"], 0)
        self.assertEqual(metrics["near_miss_false_positive_rate"], 0)
        self.assertEqual(metrics["multi_hook_required_recall"], 1.0)
        self.assertEqual(metrics["multi_hook_required_selected_count"], 2)
        self.assertEqual(metrics["multi_hook_required_total"], 2)
        self.assertEqual(metrics["per_hook"]["arbor.session_startup_context"]["precision"], 1.0)
        self.assertEqual(metrics["per_hook"]["arbor.session_startup_context"]["recall"], 1.0)
        self.assertFalse(metrics["stability"]["reported"])

    def test_harness_semantic_metrics_capture_false_positive_and_missing_required_hook(self) -> None:
        results = [
            {
                "scenario_id": "H2-P001",
                "expected_label": "H2",
                "trigger_decision": {
                    "decision": "trigger",
                    "hooks": ["arbor.session_startup_context"],
                    "requires_agent_judgment": False,
                    "reason": "Wrong hook selected.",
                },
                "executions": [],
                "passed": True,
            },
            {
                "scenario_id": "N-P001",
                "expected_label": "NONE",
                "trigger_decision": {
                    "decision": "trigger",
                    "hooks": ["arbor.session_startup_context"],
                    "requires_agent_judgment": False,
                    "reason": "False positive on unrelated work.",
                },
                "executions": [],
                "passed": True,
            },
        ]

        metrics = harness_script.compute_semantic_metrics(results)

        self.assertEqual(metrics["scenario_count"], 2)
        self.assertEqual(len(metrics["failed_scenarios"]), 2)
        self.assertEqual(
            metrics["failed_scenarios"][0]["raw_missing_required_hooks"],
            ["arbor.in_session_memory_hygiene"],
        )
        self.assertEqual(
            metrics["failed_scenarios"][0]["missing_required_hooks"],
            ["arbor.in_session_memory_hygiene"],
        )
        self.assertEqual(metrics["none_false_positive_rate"], 1.0)
        self.assertEqual(metrics["per_hook"]["arbor.session_startup_context"]["false_positive"], 2)
        self.assertEqual(metrics["per_hook"]["arbor.in_session_memory_hygiene"]["recall"], 0)

    def test_harness_corpus_fails_report_when_real_runtime_semantics_fail(self) -> None:
        valid_but_wrong_decision = {
            "hooks": [],
            "decision": "none",
            "confidence": "high",
            "requires_agent_judgment": False,
            "optional_args": {},
            "reason": "Runtime did not select startup context.",
        }
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(
                trigger_adapter_script,
                "trigger_with_adapter",
                return_value=valid_but_wrong_decision,
            ):
                report = harness_script.evaluate_corpus(
                    Path(tmp) / "work",
                    trigger_adapter="plugin-runtime-codex-exec",
                    scenario_ids=["H1-P001"],
                )

        semantic_metrics = report["summary"]["semantic_metrics"]
        self.assertFalse(report["passed"])
        self.assertEqual(report["summary"]["passed_scenarios"], 1)
        self.assertTrue(semantic_metrics["reported"])
        self.assertFalse(semantic_metrics["passed"])
        self.assertEqual(
            semantic_metrics["metrics"]["failed_scenarios"][0]["scenario_id"],
            "H1-P001",
        )

    def test_harness_semantic_metrics_do_not_count_ambiguous_abstention_as_exact_multi_hook_match(self) -> None:
        results = [
            {
                "scenario_id": "M-P001",
                "expected_label": "MULTI",
                "trigger_decision": {
                    "decision": "ambiguous",
                    "hooks": [],
                    "requires_agent_judgment": True,
                    "reason": "Runtime abstained on ambiguous multi-hook request.",
                },
                "executions": [],
                "passed": True,
            }
        ]

        outcome = harness_script.scenario_semantic_outcome(
            results[0],
            dispatcher_script.load_scenario_corpus()["M-P001"],
        )
        metrics = harness_script.compute_semantic_metrics(results)

        self.assertTrue(outcome["passed"])
        self.assertEqual(outcome["missing_required_hooks"], [])
        self.assertEqual(outcome["raw_missing_required_hooks"], ["arbor.session_startup_context"])
        self.assertEqual(metrics["ambiguous_acceptance_rate"], 1.0)
        self.assertEqual(metrics["multi_hook_required_recall"], 0.0)
        self.assertEqual(metrics["multi_hook_required_selected_count"], 0)
        self.assertEqual(metrics["multi_hook_required_total"], 1)
        self.assertEqual(metrics["multi_hook_exact_required_rate"], 0.0)
        self.assertEqual(metrics["multi_hook_exact_required_count"], 0)
        self.assertEqual(metrics["multi_hook_scenario_count"], 1)

    def test_harness_semantic_scoring_gate_rejects_empty_runtime_results(self) -> None:
        execution_summary = {
            "hook_execution_pass_rate": 1.0,
            "outside_root_leaks": 0,
            "unintended_write_failures": 0,
            "assertion_failures": [],
        }

        semantic_metrics = harness_script.semantic_metric_status(
            "plugin-runtime-codex-exec",
            [],
            execution_summary,
        )

        runtime_gate = semantic_metrics["gates"]["runtime_availability"]
        self.assertFalse(semantic_metrics["ready_for_semantic_metrics"])
        self.assertEqual(runtime_gate["status"], "no_results")
        self.assertEqual(runtime_gate["total_scenarios"], 0)

    def test_harness_repeated_runtime_stability_reports_matching_gate_ready_runs(self) -> None:
        result = {
            "scenario_id": "H1-P001",
            "expected_label": "H1",
            "trigger_decision": {
                "decision": "trigger",
                "hooks": ["arbor.session_startup_context"],
                "requires_agent_judgment": False,
                "optional_args": {},
                "reason": "Runtime selected startup context.",
            },
            "executions": [],
            "passed": True,
        }
        reports = [
            self.semantic_ready_report([result]),
            self.semantic_ready_report([copy.deepcopy(result)]),
        ]

        stability = harness_script.compute_repeated_runtime_stability(
            reports,
            "plugin-runtime-codex-exec",
        )

        self.assertTrue(stability["reported"])
        self.assertEqual(stability["run_count"], 2)
        self.assertEqual(stability["scenario_count"], 1)
        self.assertEqual(stability["stable_scenario_count"], 1)
        self.assertEqual(stability["stability_rate"], 1.0)
        self.assertEqual(stability["unstable_scenarios"], [])

    def test_harness_repeated_runtime_stability_accepts_gate_ready_compact_reports(self) -> None:
        scenario = {
            "scenario_id": "H3-P002",
            "expected_label": "H3",
            "fixture": "durable_drift_docs",
            "trigger_adapter": "plugin-runtime-codex-exec",
            "decision": "trigger",
            "hooks": ["arbor.goal_constraint_drift"],
            "optional_args": {"arbor.goal_constraint_drift": ["--doc", "docs/constraints.md"]},
            "requires_agent_judgment": False,
            "executions": [],
            "passed": True,
        }
        summary = {"semantic_metrics": {"reported": True}}
        reports = [
            {"summary": summary, "scenarios": [scenario], "passed": True},
            {"summary": copy.deepcopy(summary), "scenarios": [copy.deepcopy(scenario)], "passed": True},
        ]

        stability = harness_script.compute_repeated_runtime_stability(
            reports,
            "plugin-runtime-codex-exec",
        )

        self.assertTrue(stability["reported"])
        self.assertEqual(stability["stability_rate"], 1.0)
        self.assertEqual(stability["stable_scenario_count"], 1)
        self.assertEqual(stability["unstable_scenarios"], [])
        self.assertEqual(
            harness_script.trigger_decision_signature(scenario),
            {
                "decision": "trigger",
                "hooks": ["arbor.goal_constraint_drift"],
                "optional_args": {"arbor.goal_constraint_drift": ["--doc", "docs/constraints.md"]},
            },
        )

    def test_harness_repeated_runtime_stability_reports_unstable_decisions(self) -> None:
        first = {
            "scenario_id": "H1-P001",
            "expected_label": "H1",
            "trigger_decision": {
                "decision": "trigger",
                "hooks": ["arbor.session_startup_context"],
                "requires_agent_judgment": False,
                "optional_args": {},
                "reason": "Runtime selected startup context.",
            },
            "executions": [],
            "passed": True,
        }
        second = copy.deepcopy(first)
        second["trigger_decision"] = {
            "decision": "none",
            "hooks": [],
            "requires_agent_judgment": False,
            "optional_args": {},
            "reason": "Runtime abstained on the second run.",
        }
        reports = [
            self.semantic_ready_report([first]),
            self.semantic_ready_report([second]),
        ]

        stability = harness_script.compute_repeated_runtime_stability(
            reports,
            "plugin-runtime-codex-exec",
        )

        self.assertTrue(stability["reported"])
        self.assertEqual(stability["stability_rate"], 0.0)
        self.assertEqual(stability["unstable_scenario_count"], 1)
        self.assertEqual(stability["unstable_scenarios"][0]["scenario_id"], "H1-P001")
        self.assertEqual(stability["unstable_scenarios"][0]["signatures"][0]["decision"], "trigger")
        self.assertEqual(stability["unstable_scenarios"][0]["signatures"][1]["decision"], "none")

    def test_harness_repeated_runtime_stability_withholds_blocked_runtime_runs(self) -> None:
        blocked_result = {
            "scenario_id": "H1-P001",
            "expected_label": "H1",
            "trigger_decision": trigger_adapter_script.runtime_blocker_decision("network_unavailable"),
            "executions": [],
            "passed": True,
        }
        blocked_summary = harness_script.summarize_corpus_results(
            [blocked_result],
            "plugin-runtime-codex-exec",
        )
        reports = [
            {
                "trigger_adapter": "plugin-runtime-codex-exec",
                "summary": blocked_summary,
                "scenarios": [blocked_result],
                "passed": True,
            },
            {
                "trigger_adapter": "plugin-runtime-codex-exec",
                "summary": copy.deepcopy(blocked_summary),
                "scenarios": [copy.deepcopy(blocked_result)],
                "passed": True,
            },
        ]

        stability = harness_script.compute_repeated_runtime_stability(
            reports,
            "plugin-runtime-codex-exec",
        )

        self.assertFalse(stability["reported"])
        self.assertEqual(stability["run_count"], 2)
        self.assertEqual(len(stability["not_ready_runs"]), 2)
        self.assertIn("withheld", stability["reason"])

    def test_harness_repeated_corpus_uses_isolated_run_roots_and_withholds_sidecar_stability(self) -> None:
        report = {
            "report_type": "sidecar_baseline_hook_execution",
            "trigger_adapter": "sidecar-baseline",
            "summary": {
                "passed_scenarios": 1,
                "total_scenarios": 1,
                "semantic_metrics": {"reported": False, "reason": "sidecar"},
            },
            "scenarios": [],
            "passed": True,
        }
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(harness_script, "evaluate_corpus", side_effect=[report, copy.deepcopy(report)]) as mocked:
                repeated = harness_script.evaluate_repeated_corpus(Path(tmp), 2)

        self.assertTrue(repeated["passed"])
        self.assertEqual(repeated["report_type"], "repeated_hook_trigger_corpus")
        self.assertEqual(repeated["summary"]["passed_runs"], 2)
        self.assertFalse(repeated["summary"]["stability"]["reported"])
        self.assertEqual(
            [call.args[0].name for call in mocked.call_args_list],
            ["run-001", "run-002"],
        )

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

    def test_harness_selected_corpus_writes_progress_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            progress_path = Path(tmp) / "progress" / "events.jsonl"
            report = harness_script.evaluate_corpus(
                Path(tmp) / "work",
                trigger_adapter="sidecar-baseline",
                scenario_ids=["H1-P001", "N-P001"],
                progress_jsonl=progress_path,
            )

            self.assertTrue(report["passed"])
            self.assertEqual(report["scenario_scope"], "selected")
            self.assertEqual(report["summary"]["total_scenarios"], 2)
            events = [
                json.loads(line)
                for line in progress_path.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual([event["scenario_id"] for event in events], ["H1-P001", "N-P001"])
            self.assertEqual([event["index"] for event in events], [1, 2])
            self.assertTrue(all(event["passed"] for event in events))

    def test_harness_corpus_records_adapter_error_and_continues(self) -> None:
        valid_none_decision = {
            "hooks": [],
            "decision": "none",
            "confidence": "high",
            "requires_agent_judgment": False,
            "optional_args": {},
            "reason": "No Arbor hook is needed.",
        }
        with tempfile.TemporaryDirectory() as tmp:
            progress_path = Path(tmp) / "progress.jsonl"
            with mock.patch.object(
                trigger_adapter_script,
                "trigger_with_adapter",
                side_effect=[
                    trigger_adapter_script.AdapterError("optional_args --diff-args requires a value"),
                    valid_none_decision,
                ],
            ):
                report = harness_script.evaluate_corpus(
                    Path(tmp) / "work",
                    trigger_adapter="plugin-runtime-codex-exec",
                    scenario_ids=["H1-P001", "N-P001"],
                    progress_jsonl=progress_path,
                )

            events = [
                json.loads(line)
                for line in progress_path.read_text(encoding="utf-8").splitlines()
            ]

        self.assertFalse(report["passed"])
        self.assertEqual(report["summary"]["total_scenarios"], 2)
        self.assertEqual(report["summary"]["passed_scenarios"], 1)
        self.assertEqual(report["summary"]["failed_scenarios"], ["H1-P001"])
        self.assertEqual(report["scenarios"][0]["adapter_error"]["type"], "AdapterError")
        self.assertIn("--diff-args requires", report["scenarios"][0]["adapter_error"]["message"])
        self.assertEqual([event["scenario_id"] for event in events], ["H1-P001", "N-P001"])
        self.assertFalse(events[0]["passed"])
        self.assertIn("--diff-args requires", events[0]["adapter_error"]["message"])
        self.assertTrue(events[1]["passed"])
        adapter_gate = report["summary"]["semantic_metrics"]["gates"]["adapter_contract"]
        self.assertFalse(adapter_gate["passed"])
        self.assertEqual(adapter_gate["adapter_error_count"], 1)

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
            scenario_with_args = next(
                scenario
                for scenario in report["scenarios"]
                if scenario["scenario_id"] == "H3-P002"
            )
            self.assertEqual(
                scenario_with_args["optional_args"],
                {"arbor.goal_constraint_drift": ["--doc", "docs/constraints.md"]},
            )

    def test_harness_cli_outputs_selected_corpus_report_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            progress_path = Path(tmp) / "progress.jsonl"
            report_path = Path(tmp) / "reports" / "selected.json"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(EVAL_SCRIPTS / "evaluate_hook_triggers.py"),
                    "--scenario-ids",
                    "H1-P001,N-P001",
                    "--work-root",
                    str(Path(tmp) / "work"),
                    "--progress-jsonl",
                    str(progress_path),
                    "--report-json",
                    str(report_path),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            report = json.loads(proc.stdout)
            self.assertEqual(report["scenario_scope"], "selected")
            self.assertEqual(report["summary"]["total_scenarios"], 2)
            self.assertEqual(len(progress_path.read_text(encoding="utf-8").splitlines()), 2)
            saved_report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(saved_report, report)

    def test_harness_cli_returns_nonzero_for_failed_corpus_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            argv = [
                "evaluate_hook_triggers.py",
                "--scenario-ids",
                "H1-P001",
                "--work-root",
                str(Path(tmp) / "work"),
            ]
            with mock.patch.object(sys, "argv", argv), mock.patch("builtins.print"), mock.patch.object(
                harness_script,
                "evaluate_corpus",
                return_value={"passed": False},
            ):
                exit_code = harness_script.main()

        self.assertEqual(exit_code, 1)

    def test_harness_cli_rejects_repeat_runs_for_single_scenario(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [
                    sys.executable,
                    str(EVAL_SCRIPTS / "evaluate_hook_triggers.py"),
                    "--scenario-id",
                    "H1-P001",
                    "--work-root",
                    str(Path(tmp)),
                    "--repeat-runs",
                    "2",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("--repeat-runs can only be used with --all", proc.stderr)

    def test_harness_cli_accepts_explicit_sidecar_baseline_trigger_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [
                    sys.executable,
                    str(EVAL_SCRIPTS / "evaluate_hook_triggers.py"),
                    "--scenario-id",
                    "H1-P001",
                    "--work-root",
                    str(Path(tmp)),
                    "--trigger-adapter",
                    "sidecar-baseline",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            result = json.loads(proc.stdout)
            self.assertTrue(result["passed"])
            self.assertEqual(result["trigger_adapter"], "sidecar-baseline")
            self.assertEqual(result["trigger_decision"]["hooks"], ["arbor.session_startup_context"])

    def test_harness_cli_smoke_expectation_passes_for_matching_sidecar_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [
                    sys.executable,
                    str(EVAL_SCRIPTS / "evaluate_hook_triggers.py"),
                    "--scenario-id",
                    "H1-P001",
                    "--work-root",
                    str(Path(tmp)),
                    "--trigger-adapter",
                    "sidecar-baseline",
                    "--expect-decision",
                    "trigger",
                    "--expect-hooks",
                    "arbor.session_startup_context",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            result = json.loads(proc.stdout)
            self.assertTrue(result["passed"])
            self.assertTrue(all(item["passed"] for item in result["smoke_assertions"]))

    def test_harness_cli_smoke_expectation_fails_for_mismatched_sidecar_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [
                    sys.executable,
                    str(EVAL_SCRIPTS / "evaluate_hook_triggers.py"),
                    "--scenario-id",
                    "H1-P001",
                    "--work-root",
                    str(Path(tmp)),
                    "--trigger-adapter",
                    "sidecar-baseline",
                    "--expect-decision",
                    "none",
                    "--expect-hooks",
                    "",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 1)
            result = json.loads(proc.stdout)
            self.assertFalse(result["passed"])
            self.assertFalse(all(item["passed"] for item in result["smoke_assertions"]))

    def test_harness_cli_accepts_plugin_runtime_stub_without_hook_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [
                    sys.executable,
                    str(EVAL_SCRIPTS / "evaluate_hook_triggers.py"),
                    "--scenario-id",
                    "H1-P001",
                    "--work-root",
                    str(Path(tmp)),
                    "--trigger-adapter",
                    "plugin-runtime-stub",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            result = json.loads(proc.stdout)
            self.assertTrue(result["passed"])
            self.assertEqual(result["trigger_adapter"], "plugin-runtime-stub")
            self.assertEqual(result["trigger_decision"]["decision"], "ambiguous")
            self.assertEqual(result["trigger_decision"]["hooks"], [])
            self.assertEqual(result["executions"], [])

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
