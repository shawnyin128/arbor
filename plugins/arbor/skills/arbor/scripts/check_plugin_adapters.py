#!/usr/bin/env python3
"""Validate Arbor plugin adapter structure and Claude hook smoke behavior."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def add_error(errors: list[str], message: str) -> None:
    errors.append(message)


def check(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        add_error(errors, message)


def load_json(path: Path, errors: list[str]) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        add_error(errors, f"missing JSON file: {path}")
        return {}
    except json.JSONDecodeError as exc:
        add_error(errors, f"invalid JSON in {path}: {exc}")
        return {}
    if not isinstance(data, dict):
        add_error(errors, f"JSON file must contain an object: {path}")
        return {}
    return data


def plugin_root_from_script() -> Path:
    return Path(__file__).resolve().parents[3]


def repo_root_from_plugin(plugin_root: Path) -> Path | None:
    if plugin_root.parent.name == "plugins":
        return plugin_root.parent.parent
    return None


def validate_manifests(plugin_root: Path, errors: list[str]) -> None:
    codex = load_json(plugin_root / ".codex-plugin" / "plugin.json", errors)
    claude = load_json(plugin_root / ".claude-plugin" / "plugin.json", errors)
    if not codex or not claude:
        return

    for field in ("name", "version", "description", "homepage", "repository", "license"):
        check(
            errors,
            codex.get(field) == claude.get(field),
            f"manifest field {field!r} must match between Codex and Claude manifests",
        )

    check(errors, codex.get("skills") == "./skills/", "Codex manifest must point at ./skills/")
    check(errors, isinstance(claude.get("keywords"), list), "Claude manifest must include keyword list")
    check(errors, "claude-code" in claude.get("keywords", []), "Claude manifest should include claude-code keyword")

    repo_root = repo_root_from_plugin(plugin_root)
    if repo_root is None:
        return
    marketplace = load_json(repo_root / ".claude-plugin" / "marketplace.json", errors)
    plugins = marketplace.get("plugins")
    check(errors, isinstance(plugins, list), "Claude marketplace must define plugins list")
    if isinstance(plugins, list):
        matches = [entry for entry in plugins if isinstance(entry, dict) and entry.get("name") == codex.get("name")]
        check(errors, len(matches) == 1, "Claude marketplace must contain exactly one Arbor entry")
        if matches:
            entry = matches[0]
            check(errors, entry.get("source") == "./plugins/arbor", "Claude marketplace source must point at ./plugins/arbor")


def validate_claude_hook_structure(plugin_root: Path, errors: list[str]) -> None:
    hooks_json = load_json(plugin_root / "hooks" / "hooks.json", errors)
    hooks = hooks_json.get("hooks")
    check(errors, isinstance(hooks, dict), "hooks/hooks.json must define hooks object")
    if isinstance(hooks, dict):
        check(errors, set(hooks) == {"SessionStart"}, "Claude adapter should only define SessionStart in this release")
        session_hooks = hooks.get("SessionStart")
        check(errors, isinstance(session_hooks, list) and bool(session_hooks), "SessionStart hook must be a non-empty list")

    session_start = plugin_root / "hooks" / "session-start"
    check(errors, session_start.is_file(), "hooks/session-start must exist")
    check(errors, os.access(session_start, os.X_OK), "hooks/session-start must be executable")
    check(errors, not (plugin_root / "hooks" / "pre-compact").exists(), "PreCompact adapter must not ship in this release")
    check(errors, not (plugin_root / "agents").exists(), "plugin-level agents directory is out of scope for this release")


def run_session_start(plugin_root: Path, project_root: Path, source: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    payload = {
        "session_id": "adapter-smoke",
        "transcript_path": str(project_root / "transcript.jsonl"),
        "cwd": str(project_root),
        "hook_event_name": "SessionStart",
        "source": source,
    }
    return subprocess.run(
        [str(plugin_root / "hooks" / "session-start")],
        input=json.dumps(payload),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=env,
    )


def validate_session_start_smoke(plugin_root: Path, errors: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="arbor-claude-adapter-") as tmp:
        project = Path(tmp)
        (project / ".arbor").mkdir()
        (project / "AGENTS.md").write_text("# Project Guide\n\n" + ("Guide line.\n" * 1400), encoding="utf-8")
        (project / ".arbor" / "memory.md").write_text("# Arbor Memory\n\n- Pending note.\n", encoding="utf-8")
        subprocess.run(["git", "init"], cwd=project, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, text=True)

        proc = run_session_start(plugin_root, project, "startup")
        check(errors, proc.returncode == 0, f"SessionStart startup smoke failed: {proc.stderr.strip()}")
        output = proc.stdout
        check(errors, len(output) <= 9500, "SessionStart startup output must stay within adapter budget")
        for expected in ("# Project Startup Context", "## 1. AGENTS.md", "## 2. formatted git log", "## 3. .arbor/memory.md", "## 4. git status"):
            check(errors, expected in output, f"SessionStart startup output missing {expected!r}")
        check(errors, "truncated - Arbor SessionStart context exceeded" in output, "large startup packet should include truncation notice")

        clear_proc = run_session_start(plugin_root, project, "clear")
        check(errors, clear_proc.returncode == 0, f"SessionStart clear smoke failed: {clear_proc.stderr.strip()}")
        check(errors, clear_proc.stdout == "", "SessionStart clear source must not inject context")


def main() -> int:
    errors: list[str] = []
    plugin_root = plugin_root_from_script()
    validate_manifests(plugin_root, errors)
    validate_claude_hook_structure(plugin_root, errors)
    validate_session_start_smoke(plugin_root, errors)

    if errors:
        print("plugin adapter checks failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("plugin adapter checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
