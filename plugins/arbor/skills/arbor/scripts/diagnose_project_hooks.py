#!/usr/bin/env python3
"""Diagnose Arbor hook registration state for Codex and Claude Code."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from arbor_project_state import (
    CLAUDE_HOOKS_DIR,
    CLAUDE_SETTINGS_PATH,
    CODEX_HOOK_CONFIG_PATH,
    CODEX_HOOKS_DIR,
    project_path,
    resolve_project_root,
)
from register_project_hooks import claude_project_hook_command, codex_project_hook_command


CODEX_REQUIRED_EVENTS = ("SessionStart", "Stop")
CLAUDE_REQUIRED_EVENTS = ("SessionStart", "Stop")


@dataclass(frozen=True)
class HookState:
    status: str
    detail: str
    files: list[str]
    next_action: str


@dataclass(frozen=True)
class HookDiagnosis:
    root: str
    codex: HookState
    claude_project: HookState
    shared_adapters: HookState


def load_json_object(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "missing"
    if not path.is_file():
        return None, "not_a_file"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except JSONDecodeError as exc:
        return None, f"invalid_json: {exc}"
    if not isinstance(data, dict):
        return None, "not_an_object"
    return data, None


def event_handler_command_state(config: dict[str, Any], event: str, marker: str, expected_command: str) -> str:
    marker_seen = False
    hooks = config.get("hooks")
    if not isinstance(hooks, dict):
        return "missing"
    groups = hooks.get(event)
    if not isinstance(groups, list):
        return "missing"
    for group in groups:
        if not isinstance(group, dict):
            continue
        handlers = group.get("hooks")
        if not isinstance(handlers, list):
            continue
        for handler in handlers:
            if isinstance(handler, dict):
                command = str(handler.get("command", ""))
                if command == expected_command:
                    return "ok"
                if marker in command:
                    marker_seen = True
    return "stale" if marker_seen else "missing"


def has_event_handler_with_markers(config: dict[str, Any], event: str, markers: tuple[str, ...]) -> bool:
    hooks = config.get("hooks")
    if not isinstance(hooks, dict):
        return False
    groups = hooks.get(event)
    if not isinstance(groups, list):
        return False
    for group in groups:
        if not isinstance(group, dict):
            continue
        handlers = group.get("hooks")
        if not isinstance(handlers, list):
            continue
        for handler in handlers:
            if isinstance(handler, dict):
                command = str(handler.get("command", ""))
                if all(marker in command for marker in markers):
                    return True
    return False


def is_intent_style_codex_config(config: dict[str, Any]) -> bool:
    hooks = config.get("hooks")
    if not isinstance(hooks, list):
        return False
    return any(isinstance(hook, dict) and hook.get("owner") == "arbor" for hook in hooks)


def executable_file_state(path: Path) -> str:
    if not path.exists():
        return "missing"
    if not path.is_file():
        return "not_a_file"
    if os.name == "nt":
        return "ok"
    if not path.stat().st_mode & 0o111:
        return "not_executable"
    return "ok"


def adapter_command(path: Path) -> list[str]:
    if os.name == "nt":
        return [sys.executable, str(path)]
    return [str(path)]


def adapter_probe_state(plugin_root: Path, session_path: Path, stop_path: Path) -> str:
    env = os.environ.copy()
    env["ARBOR_PLUGIN_ROOT"] = str(plugin_root)
    env["PLUGIN_ROOT"] = str(plugin_root)
    env["CODEX_PLUGIN_ROOT"] = str(plugin_root)
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    probes = (
        ("session null", session_path, "null"),
        ("session malformed", session_path, "{bad json"),
        ("stop null", stop_path, "null"),
        ("stop malformed", stop_path, "{bad json"),
    )
    for label, path, payload in probes:
        proc = subprocess.run(
            adapter_command(path),
            input=payload,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            check=False,
        )
        if proc.returncode != 0 or proc.stderr:
            detail = proc.stderr.strip() or proc.stdout.strip() or f"exit {proc.returncode}"
            return f"{label} probe failed: {detail}"
    return "ok"


def diagnose_codex(root: Path, *, codex_trusted: bool) -> HookState:
    config_path = project_path(root, CODEX_HOOK_CONFIG_PATH)
    session_path = project_path(root, CODEX_HOOKS_DIR / "arbor-session-start")
    stop_path = project_path(root, CODEX_HOOKS_DIR / "arbor-stop-memory-hygiene")
    files = [str(config_path), str(session_path), str(stop_path)]
    config, error = load_json_object(config_path)
    if error == "missing":
        return HookState("missing", ".codex/hooks.json is missing", files, "run register_project_hooks.py --runtime codex")
    if error:
        return HookState("invalid", f".codex/hooks.json is {error}", files, "repair or regenerate .codex/hooks.json")
    assert config is not None

    session_state = executable_file_state(session_path)
    stop_state = executable_file_state(stop_path)
    if is_intent_style_codex_config(config):
        return HookState(
            "intent-only",
            ".codex/hooks.json contains Arbor intent records instead of executable Codex hook groups",
            files,
            "rerun register_project_hooks.py --runtime codex to migrate to command hooks and wrappers",
        )

    session_command_state = event_handler_command_state(
        config,
        "SessionStart",
        ".codex/hooks/arbor-session-start",
        codex_project_hook_command("arbor-session-start"),
    )
    stop_command_state = event_handler_command_state(
        config,
        "Stop",
        ".codex/hooks/arbor-stop-memory-hygiene",
        codex_project_hook_command("arbor-stop-memory-hygiene"),
    )
    if session_command_state != "ok" or stop_command_state != "ok" or session_state != "ok" or stop_state != "ok":
        return HookState(
            "executable-incomplete",
            (
                f"command hooks session={session_command_state} stop={stop_command_state}; "
                f"wrappers session={session_state} stop={stop_state}"
            ),
            files,
            "rerun register_project_hooks.py --runtime codex",
        )
    if not codex_trusted:
        return HookState(
            "executable-untrusted",
            "command hooks and wrappers exist, but Codex /hooks trust cannot be proven from files",
            files,
            "verify or trust hooks in an interactive Codex /hooks session",
        )
    return HookState("executable-ready", "command hooks, wrappers, and caller-asserted trust are present", files, "run an interactive hook smoke")


def diagnose_claude_project(root: Path) -> HookState:
    settings_path = project_path(root, CLAUDE_SETTINGS_PATH)
    session_path = project_path(root, CLAUDE_HOOKS_DIR / "arbor-session-start")
    stop_path = project_path(root, CLAUDE_HOOKS_DIR / "arbor-stop-memory-hygiene")
    files = [str(settings_path), str(session_path), str(stop_path)]
    settings, error = load_json_object(settings_path)
    if error == "missing":
        return HookState("project-Claude-missing", ".claude/settings.json is missing", files, "run register_project_hooks.py --runtime claude when project-level wrappers are desired")
    if error:
        return HookState("project-Claude-invalid", f".claude/settings.json is {error}", files, "repair or regenerate .claude/settings.json")
    assert settings is not None

    session_state = executable_file_state(session_path)
    stop_state = executable_file_state(stop_path)
    session_command_state = event_handler_command_state(
        settings,
        "SessionStart",
        ".claude/hooks/arbor-session-start",
        claude_project_hook_command("arbor-session-start"),
    )
    stop_command_state = event_handler_command_state(
        settings,
        "Stop",
        ".claude/hooks/arbor-stop-memory-hygiene",
        claude_project_hook_command("arbor-stop-memory-hygiene"),
    )
    if session_command_state != "ok" or stop_command_state != "ok" or session_state != "ok" or stop_state != "ok":
        return HookState(
            "project-Claude-incomplete",
            (
                f"settings session={session_command_state} stop={stop_command_state}; "
                f"wrappers session={session_state} stop={stop_state}"
            ),
            files,
            "rerun register_project_hooks.py --runtime claude",
        )
    return HookState("project-Claude-ready", "project-level Claude hook settings and wrappers exist", files, "run a Claude Code hook smoke")


def diagnose_shared_adapters(plugin_root: Path | None) -> HookState:
    if plugin_root is None:
        return HookState("shared-adapters-unknown", "no plugin root was provided", [], "pass --plugin-root to inspect shared hook adapters")
    manifest_path = plugin_root / "hooks" / "hooks.json"
    session_path = plugin_root / "hooks" / "session-start"
    stop_path = plugin_root / "hooks" / "stop-memory-hygiene"
    files = [str(session_path), str(stop_path)]
    if manifest_path.exists():
        return HookState(
            "shared-adapters-drift",
            "legacy plugin-level hooks/hooks.json is present; Arbor now supports only project-level runtime hook registration",
            [str(manifest_path), *files],
            "remove hooks/hooks.json and run register_project_hooks.py for each target runtime",
        )

    session_state = executable_file_state(session_path)
    stop_state = executable_file_state(stop_path)
    if session_state != "ok" or stop_state != "ok":
        return HookState(
            "shared-adapters-incomplete",
            f"adapters session={session_state} stop={stop_state}",
            files,
            "restore hooks/session-start and hooks/stop-memory-hygiene",
        )
    probe_state = adapter_probe_state(plugin_root, session_path, stop_path)
    if probe_state != "ok":
        return HookState(
            "shared-adapters-probe-failed",
            f"shared adapters exist but hook UI probe smoke failed: {probe_state}",
            files,
            "sync local plugin cache or reinstall Arbor from a version with probe-safe adapters",
        )
    return HookState("shared-adapters-ready", "shared hook adapter scripts exist for project-level wrappers", files, "none")


def diagnose(root: Path, plugin_root: Path | None = None, *, codex_trusted: bool = False) -> HookDiagnosis:
    resolved = resolve_project_root(root)
    resolved_plugin = plugin_root.resolve() if plugin_root is not None else None
    return HookDiagnosis(
        root=str(resolved),
        codex=diagnose_codex(resolved, codex_trusted=codex_trusted),
        claude_project=diagnose_claude_project(resolved),
        shared_adapters=diagnose_shared_adapters(resolved_plugin),
    )


def render_text(diagnosis: HookDiagnosis) -> str:
    lines = [f"# Arbor Hook Diagnosis", "", f"Project: {diagnosis.root}", ""]
    lines.extend(
        [
            "## Interpretation",
            "- Codex and Claude Code hooks are project-level runtime surfaces managed under `.codex/` and `.claude/`.",
            "- Arbor no longer ships plugin-level hook registrations; installed plugins provide shared adapters only.",
            "- Missing Claude project hooks mean Claude Code has not been initialized for this project yet.",
            "- `executable-untrusted` means files exist but the runtime trust/approval step still needs an interactive smoke.",
            "- Silent Stop can still be registered correctly while memory content behavior must be verified by replay.",
            "",
        ]
    )
    for label, state in (
        ("Codex project hooks", diagnosis.codex),
        ("Claude project hooks", diagnosis.claude_project),
        ("Shared hook adapters", diagnosis.shared_adapters),
    ):
        lines.extend(
            [
                f"## {label}",
                f"- status: {state.status}",
                f"- detail: {state.detail}",
                f"- next_action: {state.next_action}",
                "",
            ]
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root to inspect.")
    parser.add_argument("--plugin-root", type=Path, default=None, help="Arbor plugin root to inspect.")
    parser.add_argument("--codex-trusted", action="store_true", help="Assert Codex hooks have been trusted in /hooks.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args(argv)

    result = diagnose(args.root, args.plugin_root, codex_trusted=args.codex_trusted)
    if args.json:
        print(json.dumps(asdict(result), indent=2))
    else:
        print(render_text(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
