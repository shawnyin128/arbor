#!/usr/bin/env python3
"""Register Arbor runtime hooks in project-local hook configuration."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from copy import deepcopy
from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable


sys.dont_write_bytecode = True

from arbor_project_state import (
    CANONICAL_MEMORY_PATH,
    CLAUDE_HOOKS_DIR,
    CLAUDE_SETTINGS_PATH,
    CODEX_HOOK_CONFIG_PATH,
    CODEX_HOOKS_DIR,
    INSTALL_RUNTIME_CLAUDE,
    INSTALL_RUNTIME_CODEX,
    PROJECT_GUIDE_PATH,
    detect_install_runtime,
    project_path,
    resolve_project_root,
)

RUNTIME_AUTO = "auto"
RUNTIME_BOTH = "both"
RUNTIME_CHOICES = (RUNTIME_AUTO, RUNTIME_BOTH, INSTALL_RUNTIME_CODEX, INSTALL_RUNTIME_CLAUDE)
CODEX_SESSION_START_WRAPPER = CODEX_HOOKS_DIR / "arbor-session-start"
CODEX_STOP_WRAPPER = CODEX_HOOKS_DIR / "arbor-stop-memory-hygiene"
CLAUDE_SESSION_START_WRAPPER = CLAUDE_HOOKS_DIR / "arbor-session-start"
CLAUDE_STOP_WRAPPER = CLAUDE_HOOKS_DIR / "arbor-stop-memory-hygiene"

MEMORY_HYGIENE_CASE_CORPUS: list[dict[str, Any]] = [
    {
        "id": "trigger-dirty-edit-stop",
        "situation": "after any Arbor-managed file edit before the assistant stops",
        "expected": "trigger",
        "git_state": "dirty",
        "arbor_managed": True,
        "checkpoint": "stop",
        "rationale": "uncommitted Arbor work needs a resume pointer",
    },
    {
        "id": "trigger-context-plan-note",
        "situation": "after local context notes or design notes are updated for the current task",
        "expected": "trigger",
        "git_state": "dirty",
        "arbor_managed": True,
        "checkpoint": "context_note",
        "rationale": "uncommitted context notes may be the only resume pointer",
    },
    {
        "id": "trigger-package-edit",
        "situation": "after Arbor package files, manifests, scripts, docs, or hook adapters change",
        "expected": "trigger",
        "git_state": "dirty",
        "arbor_managed": True,
        "checkpoint": "package_edit",
        "rationale": "package state is not durable yet",
    },
    {
        "id": "trigger-hook-repair",
        "situation": "after project hook registration or shared hook adapters are repaired",
        "expected": "trigger",
        "git_state": "dirty",
        "arbor_managed": True,
        "checkpoint": "hook_repair",
        "rationale": "the next session should know hook state changed",
    },
    {
        "id": "trigger-failed-check-dirty",
        "situation": "after a command or test fails while Arbor-managed work is still dirty",
        "expected": "trigger",
        "git_state": "dirty",
        "arbor_managed": True,
        "checkpoint": "failed_check",
        "rationale": "the failure is a next-step blocker",
    },
    {
        "id": "trigger-context-bugfix",
        "situation": "after a user reports an Arbor context or hook bug that starts a local fix",
        "expected": "trigger",
        "git_state": "dirty_or_pending",
        "arbor_managed": True,
        "checkpoint": "bugfix_start",
        "rationale": "bug context must survive interruptions",
    },
    {
        "id": "trigger-scope-change",
        "situation": "after a user changes scope, constraints, naming, or acceptance criteria for active Arbor work",
        "expected": "trigger",
        "git_state": "dirty_or_pending",
        "arbor_managed": True,
        "checkpoint": "scope_change",
        "rationale": "new constraints affect the active implementation",
    },
    {
        "id": "trigger-session-handoff",
        "situation": "before handing off to a future session with dirty Arbor artifacts",
        "expected": "trigger",
        "git_state": "dirty",
        "arbor_managed": True,
        "checkpoint": "skill_handoff",
        "rationale": "the next session should recover the current local context",
    },
    {
        "id": "trigger-user-review-checkpoint",
        "situation": "before asking the user to review a checkpoint while git status is dirty",
        "expected": "trigger",
        "git_state": "dirty",
        "arbor_managed": True,
        "checkpoint": "user_review",
        "rationale": "the checkpoint may pause the session",
    },
    {
        "id": "trigger-session-boundary",
        "situation": "before pausing, sleeping, archiving, compacting, or ending a session with dirty Arbor work",
        "expected": "trigger",
        "git_state": "dirty",
        "arbor_managed": True,
        "checkpoint": "session_boundary",
        "rationale": "session boundaries require recovery state",
    },
    {
        "id": "trigger-precommit",
        "situation": "before commit, push, PR, tag, publish, or cache sync with dirty Arbor state",
        "expected": "trigger",
        "git_state": "dirty_or_staged",
        "arbor_managed": True,
        "checkpoint": "durability_boundary",
        "rationale": "durable actions should see current in-flight memory first",
    },
    {
        "id": "trigger-cache-sync",
        "situation": "after syncing local plugin caches while package changes remain uncommitted",
        "expected": "trigger",
        "git_state": "dirty",
        "arbor_managed": True,
        "checkpoint": "cache_sync",
        "rationale": "runtime cache and source may diverge before commit",
    },
    {
        "id": "trigger-ignored-validation-assets",
        "situation": "after editing ignored local validation notes or fixtures that explain uncommitted package changes",
        "expected": "trigger",
        "git_state": "dirty_or_ignored",
        "arbor_managed": True,
        "checkpoint": "local_evidence",
        "rationale": "ignored evidence may be the only resume pointer",
    },
    {
        "id": "suppress-clean-complete",
        "situation": "clean git status and no unresolved conversation state",
        "expected": "suppress",
        "git_state": "clean",
        "arbor_managed": False,
        "checkpoint": "none",
        "rationale": "there is no uncommitted state to recover",
    },
    {
        "id": "suppress-direct-explanation",
        "situation": "direct one-off explanation with no project file changes",
        "expected": "suppress",
        "git_state": "clean",
        "arbor_managed": False,
        "checkpoint": "direct_answer",
        "rationale": "direct answers should not create memory churn",
    },
    {
        "id": "suppress-read-only",
        "situation": "read-only inspection that leaves no dirty files and no unresolved Arbor decision",
        "expected": "suppress",
        "git_state": "clean",
        "arbor_managed": False,
        "checkpoint": "read_only",
        "rationale": "inspection without active state does not need memory",
    },
    {
        "id": "suppress-committed-pruned",
        "situation": "finished work already committed and pushed, with memory pruned",
        "expected": "suppress",
        "git_state": "clean",
        "arbor_managed": True,
        "checkpoint": "complete",
        "rationale": "durable history replaced short-term memory",
    },
    {
        "id": "suppress-guide-only",
        "situation": "stable project-guide or map update that belongs only in AGENTS.md",
        "expected": "suppress",
        "git_state": "dirty",
        "arbor_managed": False,
        "checkpoint": "guide_drift",
        "rationale": "stable guide drift belongs to the AGENTS phase of Stop context maintenance, not memory",
    },
    {
        "id": "suppress-committed-evidence",
        "situation": "durable evidence already committed with no active follow-up",
        "expected": "suppress",
        "git_state": "clean",
        "arbor_managed": True,
        "checkpoint": "complete",
        "rationale": "there is no remaining active context",
    },
    {
        "id": "suppress-no-write-turn",
        "situation": "user explicitly forbids file writes for the current turn",
        "expected": "suppress",
        "git_state": "any",
        "arbor_managed": False,
        "checkpoint": "no_write",
        "rationale": "user write prohibition wins",
    },
    {
        "id": "suppress-unrelated-dirty",
        "situation": "dirty files are unrelated to Arbor and the user has not asked Arbor to manage them",
        "expected": "suppress",
        "git_state": "dirty_unrelated",
        "arbor_managed": False,
        "checkpoint": "out_of_scope",
        "rationale": "do not claim unrelated user changes as Arbor state",
    },
]

MEMORY_HYGIENE_POSITIVE_CASES = [
    str(case["situation"]) for case in MEMORY_HYGIENE_CASE_CORPUS if case.get("expected") == "trigger"
]

MEMORY_HYGIENE_NEGATIVE_CASES = [
    str(case["situation"]) for case in MEMORY_HYGIENE_CASE_CORPUS if case.get("expected") == "suppress"
]

GUIDE_DRIFT_CASE_CORPUS: list[dict[str, Any]] = [
    {
        "id": "trigger-new-top-level-directory",
        "situation": "after adding a new top-level source, tool, package, data, or docs directory",
        "expected": "trigger",
        "map_area": "Project Map",
        "rationale": "new durable entrypoints should be discoverable from AGENTS.md",
    },
    {
        "id": "trigger-removed-or-renamed-entrypoint",
        "situation": "after removing or renaming a top-level directory or stable mapped subpath named in AGENTS.md",
        "expected": "trigger",
        "map_area": "Project Map",
        "rationale": "stale map pointers mislead future startup context",
    },
    {
        "id": "trigger-new-skill-or-runtime-adapter",
        "situation": "after adding a new skill, hook adapter, runtime cache path, or shared helper module",
        "expected": "trigger",
        "map_area": "Project Map",
        "rationale": "durable entrypoints need an AGENTS map pointer",
    },
    {
        "id": "trigger-guide-drift-before-handoff",
        "situation": "before commit, publish, push, or handoff when project structure changed",
        "expected": "trigger",
        "map_area": "Project Map",
        "rationale": "durable actions should not preserve a stale project guide",
    },
    {
        "id": "trigger-project-map-drift-packet",
        "situation": "when the AGENTS drift packet reports `Project Map Drift Candidates` as `update-needed`",
        "expected": "trigger",
        "map_area": "Project Map",
        "rationale": "the packet has detected missing map candidates",
    },
    {
        "id": "suppress-transient-temp-files",
        "situation": "only transient cache, pycache, temporary output, or ignored scratch files changed",
        "expected": "suppress",
        "map_area": "none",
        "rationale": "temporary files do not belong in AGENTS.md",
    },
    {
        "id": "suppress-current-session-progress",
        "situation": "only in-flight implementation notes or unresolved current-session progress changed",
        "expected": "suppress",
        "map_area": "none",
        "rationale": "short-term progress belongs in .arbor/memory.md",
    },
    {
        "id": "suppress-no-durable-map-change",
        "situation": "git status is clean and the current Project Map already mentions the stable entrypoints",
        "expected": "suppress",
        "map_area": "none",
        "rationale": "there is no durable guide drift to apply",
    },
]

GUIDE_DRIFT_POSITIVE_CASES = [
    str(case["situation"]) for case in GUIDE_DRIFT_CASE_CORPUS if case.get("expected") == "trigger"
]

GUIDE_DRIFT_NEGATIVE_CASES = [
    str(case["situation"]) for case in GUIDE_DRIFT_CASE_CORPUS if case.get("expected") == "suppress"
]

ARBOR_HOOKS: list[dict[str, Any]] = [
    {
        "id": "arbor.session_startup_context",
        "owner": "arbor",
        "event": "session.start",
        "description": "Load project startup context in Arbor order.",
        "entrypoint": {
            "type": "skill-script",
            "skill": "arbor",
            "script": "scripts/run_session_startup_hook.py",
            "args": ["--root", "${PROJECT_ROOT}"],
            "optional_args": [
                {
                    "name": "--git-log-args",
                    "placeholder": "${GIT_LOG_ARGS}",
                    "description": "Agent-selected git log arguments forwarded to the startup collector.",
                }
            ],
        },
        "order": [
            str(PROJECT_GUIDE_PATH),
            "formatted git log",
            str(CANONICAL_MEMORY_PATH),
            "git status",
        ],
        "depth_policy": "agent-selected; no fixed read limits",
    },
    {
        "id": "arbor.in_session_memory_hygiene",
        "owner": "arbor",
        "event": "conversation.checkpoint",
        "description": "Refresh project-local recovery memory when current Arbor context would be hard to resume from durable state.",
        "entrypoint": {
            "type": "skill-script",
            "skill": "arbor",
            "script": "scripts/run_memory_hygiene_hook.py",
            "args": ["--root", "${PROJECT_ROOT}"],
            "optional_args": [
                {
                    "name": "--diff-args",
                    "placeholder": "${DIFF_ARGS}",
                    "description": "Agent-selected git diff arguments included in the memory hygiene packet.",
                }
            ],
        },
        "reads": [
            str(CANONICAL_MEMORY_PATH),
            "git status --short",
            "selected diffs when the agent decides they are needed",
            "recent conversation context available to the running agent",
        ],
        "writes": [str(CANONICAL_MEMORY_PATH)],
        "trigger_policy": {
            "mode": "high_recall_when_dirty_or_handoff",
            "positive_cases": MEMORY_HYGIENE_POSITIVE_CASES,
            "negative_cases": MEMORY_HYGIENE_NEGATIVE_CASES,
            "case_corpus": MEMORY_HYGIENE_CASE_CORPUS,
            "decision_rule": (
                "Trigger when Arbor-managed work may leave unresolved state before a stop, "
                "handoff, commit, publish, or session boundary; suppress only when the "
                "worktree is clean or the request is direct/read-only with no unresolved Arbor state."
            ),
        },
        "depth_policy": "agent-selected; no fixed read limits",
    },
    {
        "id": "arbor.goal_constraint_drift",
        "owner": "arbor",
        "event": "project.guide_drift",
        "description": "Update the stable project guide or map when goals, constraints, or map pointers change; safe Project Map drift is also checked during Stop context maintenance.",
        "entrypoint": {
            "type": "skill-script",
            "skill": "arbor",
            "script": "scripts/run_agents_guide_drift_hook.py",
            "args": ["--root", "${PROJECT_ROOT}"],
            "optional_args": [
                {
                    "name": "--doc",
                    "placeholder": "${DOC_PATH}",
                    "repeatable": True,
                    "description": "Agent-selected project-local doc included in the AGENTS guide drift packet.",
                }
            ],
        },
        "reads": [
            str(PROJECT_GUIDE_PATH),
            "top-level project structure",
            "mapped path validation",
            "git status --short --untracked-files=all",
            "project docs selected by the agent",
        ],
        "writes": [str(PROJECT_GUIDE_PATH)],
        "allowed_sections": ["Project Goal", "Project Constraints", "Project Map"],
        "trigger_policy": {
            "mode": "high_recall_for_durable_guide_or_project_map_drift",
            "positive_cases": GUIDE_DRIFT_POSITIVE_CASES,
            "negative_cases": GUIDE_DRIFT_NEGATIVE_CASES,
            "case_corpus": GUIDE_DRIFT_CASE_CORPUS,
            "decision_rule": (
                "Trigger when durable project goals, constraints, or project-map entrypoints may have changed. "
                "If the drift packet reports Project Map Drift Candidates as update-needed, update AGENTS.md "
                "Project Map before handoff unless the missing candidate or stale mapped path is intentionally excluded."
            ),
        },
        "depth_policy": "agent-selected; no fixed read limits",
    },
]

ARBOR_HOOK_IDS = {hook["id"] for hook in ARBOR_HOOKS}
ARBOR_CODEX_COMMAND_MARKERS = (
    ".codex/hooks/arbor-session-start",
    ".codex/hooks/arbor-stop-memory-hygiene",
)
ARBOR_CLAUDE_COMMAND_MARKERS = (
    ".claude/hooks/arbor-session-start",
    ".claude/hooks/arbor-stop-memory-hygiene",
)


def current_hook_platform() -> str:
    return "windows" if os.name == "nt" else "posix"


def current_python_executable() -> str:
    executable = sys.executable
    if not executable:
        raise HookRegistrationError("could not resolve an absolute Python executable for project hook registration")
    return str(Path(executable).expanduser().resolve())


def ensure_absolute_python_executable(executable: str, platform: str) -> str:
    if not executable or executable in {"python", "python3"}:
        raise HookRegistrationError("project hook commands require an absolute Python executable")
    if platform == "windows":
        if not PureWindowsPath(executable).is_absolute():
            raise HookRegistrationError("project hook commands require an absolute Python executable")
        return executable
    if platform == "posix":
        if not PurePosixPath(executable).is_absolute():
            raise HookRegistrationError("project hook commands require an absolute Python executable")
        return executable
    raise HookRegistrationError(f"unknown hook command platform: {platform}")


def command_arg(value: str, platform: str) -> str:
    if platform == "windows":
        return f'"{value.replace(chr(34), r"\"")}"'
    if platform == "posix":
        return shlex.quote(value)
    raise HookRegistrationError(f"unknown hook command platform: {platform}")


def codex_project_hook_command(
    wrapper_name: str,
    platform: str | None = None,
    python_executable: str | None = None,
) -> str:
    selected = platform or current_hook_platform()
    wrapper = f".codex/hooks/{wrapper_name}"
    executable = ensure_absolute_python_executable(python_executable or current_python_executable(), selected)
    python = command_arg(executable, selected)
    if selected == "windows":
        return f"{python} {command_arg(wrapper, selected)}"
    if selected == "posix":
        return f'{python} "$(git rev-parse --show-toplevel 2>/dev/null || pwd)/{wrapper}"'
    raise HookRegistrationError(f"unknown hook command platform: {selected}")


def claude_project_hook_command(
    wrapper_name: str,
    platform: str | None = None,
    python_executable: str | None = None,
) -> str:
    selected = platform or current_hook_platform()
    wrapper = f".claude/hooks/{wrapper_name}"
    executable = ensure_absolute_python_executable(python_executable or current_python_executable(), selected)
    python = command_arg(executable, selected)
    if selected == "windows":
        return f"{python} {command_arg(wrapper, selected)}"
    if selected == "posix":
        return f'{python} "${{CLAUDE_PROJECT_DIR:-$(pwd)}}/{wrapper}"'
    raise HookRegistrationError(f"unknown hook command platform: {selected}")


CODEX_PROJECT_HOOKS: dict[str, list[dict[str, Any]]] = {
    "SessionStart": [
        {
            "matcher": "startup|resume",
            "hooks": [
                {
                    "type": "command",
                    "command": codex_project_hook_command("arbor-session-start"),
                    "statusMessage": "Loading Arbor startup context",
                }
            ],
        }
    ],
    "Stop": [
        {
            "hooks": [
                {
                    "type": "command",
                    "command": codex_project_hook_command("arbor-stop-memory-hygiene"),
                    "timeout": 30,
                }
            ],
        }
    ],
}
CLAUDE_PROJECT_HOOKS: dict[str, list[dict[str, Any]]] = {
    "SessionStart": [
        {
            "matcher": "startup|resume",
            "hooks": [
                {
                    "type": "command",
                    "command": claude_project_hook_command("arbor-session-start"),
                }
            ],
        }
    ],
    "Stop": [
        {
            "hooks": [
                {
                    "type": "command",
                    "command": claude_project_hook_command("arbor-stop-memory-hygiene"),
                }
            ],
        }
    ],
}


@dataclass(frozen=True)
class HookRegistrationAction:
    path: Path
    status: str
    detail: str = ""


class HookRegistrationError(ValueError):
    """Raised when Arbor hooks cannot be registered cleanly."""


def hook_config_path(root: Path) -> Path:
    try:
        return project_path(resolve_project_root(root), CODEX_HOOK_CONFIG_PATH)
    except ValueError as exc:
        raise HookRegistrationError(str(exc)) from exc


def claude_settings_path(root: Path) -> Path:
    try:
        return project_path(resolve_project_root(root), CLAUDE_SETTINGS_PATH)
    except ValueError as exc:
        raise HookRegistrationError(str(exc)) from exc


def claude_hook_wrapper_path(root: Path, relative_path: Path) -> Path:
    try:
        return project_path(resolve_project_root(root), relative_path)
    except ValueError as exc:
        raise HookRegistrationError(str(exc)) from exc


def codex_hook_wrapper_path(root: Path, relative_path: Path) -> Path:
    try:
        return project_path(resolve_project_root(root), relative_path)
    except ValueError as exc:
        raise HookRegistrationError(str(exc)) from exc


def load_codex_hook_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    if not path.is_file():
        raise HookRegistrationError(f"cannot register hooks at {path}: expected a file but found a directory")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except UnicodeError as exc:
        raise HookRegistrationError(f"cannot read {path} as UTF-8 JSON: {exc}") from exc
    except JSONDecodeError as exc:
        raise HookRegistrationError(f"cannot parse {path}: {exc}") from exc
    except OSError as exc:
        raise HookRegistrationError(f"cannot read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise HookRegistrationError(f"cannot register hooks at {path}: expected a JSON object")
    return data


def is_legacy_arbor_intent(hook: Any) -> bool:
    return isinstance(hook, dict) and hook.get("owner") == "arbor" and hook.get("id") in ARBOR_HOOK_IDS


def normalize_codex_hook_config(config: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(config)
    existing_hooks = merged.get("hooks", {})
    if existing_hooks is None:
        merged["hooks"] = {}
        return merged
    if isinstance(existing_hooks, list):
        non_arbor = [hook for hook in existing_hooks if not is_legacy_arbor_intent(hook)]
        if non_arbor:
            raise HookRegistrationError(
                "cannot convert legacy Codex hook intent list: non-Arbor list entries cannot be preserved "
                "in Codex's executable hook schema"
            )
        merged.pop("version", None)
        merged["hooks"] = {}
        return merged
    if not isinstance(existing_hooks, dict):
        raise HookRegistrationError("cannot register Codex hooks: expected 'hooks' to be an object")
    return merged


def render_hook_config(config: dict[str, Any]) -> str:
    return json.dumps(config, indent=2, sort_keys=False) + "\n"


def load_claude_settings(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    if not path.is_file():
        raise HookRegistrationError(f"cannot register Claude hooks at {path}: expected a file but found a directory")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except UnicodeError as exc:
        raise HookRegistrationError(f"cannot read {path} as UTF-8 JSON: {exc}") from exc
    except JSONDecodeError as exc:
        raise HookRegistrationError(f"cannot parse {path}: {exc}") from exc
    except OSError as exc:
        raise HookRegistrationError(f"cannot read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise HookRegistrationError(f"cannot register Claude hooks at {path}: expected a JSON object")
    hooks = data.get("hooks", {})
    if hooks is not None and not isinstance(hooks, dict):
        raise HookRegistrationError(f"cannot register Claude hooks at {path}: expected 'hooks' to be an object")
    return data


def is_arbor_codex_handler(handler: Any) -> bool:
    if not isinstance(handler, dict):
        return False
    command = str(handler.get("command", ""))
    normalized_command = command.replace("\\", "/")
    return any(marker in normalized_command for marker in ARBOR_CODEX_COMMAND_MARKERS)


def is_arbor_claude_handler(handler: Any) -> bool:
    if not isinstance(handler, dict):
        return False
    command = str(handler.get("command", ""))
    normalized_command = command.replace("\\", "/")
    return any(marker in normalized_command for marker in ARBOR_CLAUDE_COMMAND_MARKERS)


def remove_existing_arbor_handlers(
    hooks: dict[str, Any],
    *,
    is_arbor_handler: Any,
) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            cleaned[event] = groups
            continue
        new_groups: list[Any] = []
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                new_groups.append(group)
                continue
            filtered_handlers = [handler for handler in group["hooks"] if not is_arbor_handler(handler)]
            if filtered_handlers:
                updated = deepcopy(group)
                updated["hooks"] = filtered_handlers
                new_groups.append(updated)
        if new_groups:
            cleaned[event] = new_groups
    return cleaned


def remove_existing_arbor_codex_handlers(hooks: dict[str, Any]) -> dict[str, Any]:
    return remove_existing_arbor_handlers(hooks, is_arbor_handler=is_arbor_codex_handler)


def remove_existing_arbor_claude_handlers(hooks: dict[str, Any]) -> dict[str, Any]:
    return remove_existing_arbor_handlers(hooks, is_arbor_handler=is_arbor_claude_handler)


def merge_codex_project_hooks(config: dict[str, Any]) -> dict[str, Any]:
    merged = normalize_codex_hook_config(config)
    existing_hooks = merged.get("hooks", {})
    if existing_hooks is None:
        existing_hooks = {}
    if not isinstance(existing_hooks, dict):
        raise HookRegistrationError("cannot register Codex hooks: expected 'hooks' to be an object")
    hooks = remove_existing_arbor_codex_handlers(existing_hooks)
    for event, groups in CODEX_PROJECT_HOOKS.items():
        existing_groups = hooks.get(event, [])
        if not isinstance(existing_groups, list):
            raise HookRegistrationError(f"cannot register Codex hooks: expected hooks.{event} to be a list")
        hooks[event] = [*existing_groups, *deepcopy(groups)]
    merged["hooks"] = hooks
    return merged


def merge_claude_project_hooks(settings: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(settings)
    existing_hooks = merged.get("hooks", {})
    if existing_hooks is None:
        existing_hooks = {}
    if not isinstance(existing_hooks, dict):
        raise HookRegistrationError("cannot register Claude hooks: expected 'hooks' to be an object")
    hooks = remove_existing_arbor_claude_handlers(existing_hooks)
    for event, groups in CLAUDE_PROJECT_HOOKS.items():
        existing_groups = hooks.get(event, [])
        if not isinstance(existing_groups, list):
            raise HookRegistrationError(f"cannot register Claude hooks: expected hooks.{event} to be a list")
        hooks[event] = [*existing_groups, *deepcopy(groups)]
    merged["hooks"] = hooks
    return merged


def render_project_hook_wrapper(adapter_name: str, runtime: str) -> str:
    runtime_label = "Claude Code" if runtime == INSTALL_RUNTIME_CLAUDE else "Codex"
    cache_home = f".{runtime}"
    return f'''#!/usr/bin/env python3
"""Project-local Arbor {runtime_label} hook wrapper.

This wrapper is installed under the project's runtime-specific hook directory.
It locates the enabled Arbor plugin cache at runtime and delegates to the
shared adapter script so project-local hooks do not duplicate adapter logic.
"""

from __future__ import annotations

import os
import json
import re
import subprocess
import sys
from pathlib import Path


ADAPTER_NAME = "{adapter_name}"
CACHE_HOME = "{cache_home}"
DEFAULT_ADAPTER_TIMEOUT_SECONDS = 25.0
RELEASE_VERSION_PATTERN = re.compile(r"\\d+\\.\\d+\\.\\d+")


def version_key(path: Path) -> tuple[int, ...]:
    parts: list[int] = []
    for part in path.name.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(-1)
    return tuple(parts)


def candidate_roots() -> list[Path]:
    roots: list[Path] = []
    for env_name in ("ARBOR_PLUGIN_ROOT", "PLUGIN_ROOT", "CODEX_PLUGIN_ROOT", "CLAUDE_PLUGIN_ROOT"):
        env_root = os.environ.get(env_name)
        if env_root:
            root = Path(env_root).expanduser().resolve()
            if looks_like_arbor_plugin_root(root) and root not in roots:
                roots.append(root)
    cache = Path.home() / CACHE_HOME / "plugins" / "cache" / "arbor" / "arbor"
    if cache.is_dir():
        roots.extend(
            sorted(
                (
                    child.resolve()
                    for child in cache.iterdir()
                    if child.is_dir()
                    and RELEASE_VERSION_PATTERN.fullmatch(child.name)
                    and looks_like_arbor_plugin_root(child.resolve())
                ),
                key=version_key,
                reverse=True,
            )
        )
    return roots


def looks_like_arbor_plugin_root(root: Path) -> bool:
    return (
        (root / ".codex-plugin" / "plugin.json").is_file()
        and (root / ".claude-plugin" / "plugin.json").is_file()
        and (root / "skills" / "arbor" / "SKILL.md").is_file()
    )


def resolve_adapter() -> tuple[Path, Path]:
    for root in candidate_roots():
        adapter = root / "hooks" / ADAPTER_NAME
        if adapter.is_file():
            return root, adapter
    raise RuntimeError(f"could not locate Arbor hook adapter {{ADAPTER_NAME!r}}")


def adapter_timeout_seconds() -> float:
    raw = os.environ.get("ARBOR_HOOK_ADAPTER_TIMEOUT_SECONDS")
    if not raw:
        return DEFAULT_ADAPTER_TIMEOUT_SECONDS
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_ADAPTER_TIMEOUT_SECONDS
    if value <= 0:
        return DEFAULT_ADAPTER_TIMEOUT_SECONDS
    return value


def allow_stop() -> None:
    print('{{"continue": true, "suppressOutput": true}}')


def stop_output_is_valid(stdout: str) -> bool:
    if not stdout.strip():
        return False
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return False
    return isinstance(payload, dict) and "continue" in payload


def emit_success_output(stdout: str) -> None:
    if ADAPTER_NAME == "stop-memory-hygiene" and not stop_output_is_valid(stdout):
        allow_stop()
        return
    if stdout:
        sys.stdout.write(stdout)


def main() -> int:
    try:
        root, adapter = resolve_adapter()
    except (RuntimeError, OSError):
        if ADAPTER_NAME == "stop-memory-hygiene":
            allow_stop()
        return 0
    env = os.environ.copy()
    env["ARBOR_PLUGIN_ROOT"] = str(root)
    env["PLUGIN_ROOT"] = str(root)
    env["CODEX_PLUGIN_ROOT"] = str(root)
    env["CLAUDE_PLUGIN_ROOT"] = str(root)
    try:
        proc = subprocess.run(
            [sys.executable, str(adapter)],
            input=sys.stdin.read(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            check=False,
            timeout=adapter_timeout_seconds(),
        )
    except subprocess.TimeoutExpired:
        if ADAPTER_NAME == "stop-memory-hygiene":
            allow_stop()
        return 0
    except OSError:
        if ADAPTER_NAME == "stop-memory-hygiene":
            allow_stop()
        return 0
    if proc.returncode != 0:
        if ADAPTER_NAME == "stop-memory-hygiene":
            allow_stop()
        return 0
    emit_success_output(proc.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def ensure_executable_file(path: Path, content: str, dry_run: bool) -> HookRegistrationAction:
    existed = path.exists()
    if existed and not path.is_file():
        raise HookRegistrationError(f"cannot initialize {path}: expected a file but found a directory")
    if path.parent.exists() and not path.parent.is_dir():
        raise HookRegistrationError(f"cannot initialize {path}: parent path is not a directory")
    try:
        current = path.read_text(encoding="utf-8") if existed else None
    except UnicodeError:
        current = None
    if current == content:
        if os.name != "nt" and not path.stat().st_mode & 0o111:
            if not dry_run:
                path.chmod(0o755)
            return HookRegistrationAction(path=path, status="would_chmod" if dry_run else "chmod")
        return HookRegistrationAction(path=path, status="exists")
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        path.chmod(0o755)
    if not existed:
        status = "would_create" if dry_run else "created"
    else:
        status = "would_update" if dry_run else "updated"
    return HookRegistrationAction(path=path, status=status)


def write_json_file(path: Path, before: dict[str, Any], after: dict[str, Any], dry_run: bool, detail: str) -> HookRegistrationAction:
    before_text = render_hook_config(before)
    after_text = render_hook_config(after)
    if before_text == after_text:
        return HookRegistrationAction(path=path, status="exists", detail=detail)
    existed = path.exists()
    if path.parent.exists() and not path.parent.is_dir():
        raise HookRegistrationError(f"cannot write {path}: parent path is not a directory")
    if not dry_run:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(after_text, encoding="utf-8")
        except OSError as exc:
            raise HookRegistrationError(f"cannot write {path}: {exc}") from exc
    if not existed:
        status = "would_create" if dry_run else "created"
    else:
        status = "would_update" if dry_run else "updated"
    return HookRegistrationAction(path=path, status=status, detail=detail)


def register_codex_project_hooks(root: Path, dry_run: bool = False) -> list[HookRegistrationAction]:
    root = root.resolve()
    path = hook_config_path(root)

    config = load_codex_hook_config(path)
    merged = merge_codex_project_hooks(config)
    actions = [
        write_json_file(path, config, merged, dry_run, "registered 2 Arbor Codex executable project hooks"),
        ensure_executable_file(
            codex_hook_wrapper_path(root, CODEX_SESSION_START_WRAPPER),
            render_project_hook_wrapper("session-start", INSTALL_RUNTIME_CODEX),
            dry_run,
        ),
        ensure_executable_file(
            codex_hook_wrapper_path(root, CODEX_STOP_WRAPPER),
            render_project_hook_wrapper("stop-memory-hygiene", INSTALL_RUNTIME_CODEX),
            dry_run,
        ),
    ]
    return actions


def register_claude_project_hooks(root: Path, dry_run: bool = False) -> list[HookRegistrationAction]:
    root = root.resolve()
    settings_path = claude_settings_path(root)
    settings = load_claude_settings(settings_path)
    merged = merge_claude_project_hooks(settings)
    actions = [
        write_json_file(settings_path, settings, merged, dry_run, "registered 2 Arbor Claude project hooks"),
        ensure_executable_file(
            claude_hook_wrapper_path(root, CLAUDE_SESSION_START_WRAPPER),
            render_project_hook_wrapper("session-start", INSTALL_RUNTIME_CLAUDE),
            dry_run,
        ),
        ensure_executable_file(
            claude_hook_wrapper_path(root, CLAUDE_STOP_WRAPPER),
            render_project_hook_wrapper("stop-memory-hygiene", INSTALL_RUNTIME_CLAUDE),
            dry_run,
        ),
    ]
    return actions


def resolve_registration_runtime(runtime: str) -> str:
    if runtime == RUNTIME_AUTO:
        return detect_install_runtime(Path(__file__)) or INSTALL_RUNTIME_CODEX
    if runtime in (INSTALL_RUNTIME_CODEX, INSTALL_RUNTIME_CLAUDE, RUNTIME_BOTH):
        return runtime
    raise HookRegistrationError(f"unknown --runtime mode: {runtime}")


def register_project_hooks(root: Path, dry_run: bool = False, runtime: str = RUNTIME_AUTO) -> list[HookRegistrationAction]:
    selected = resolve_registration_runtime(runtime)
    if selected == RUNTIME_BOTH:
        return [*register_codex_project_hooks(root, dry_run), *register_claude_project_hooks(root, dry_run)]
    if selected == INSTALL_RUNTIME_CLAUDE:
        return register_claude_project_hooks(root, dry_run)
    return register_codex_project_hooks(root, dry_run)


def render_actions(actions: Iterable[HookRegistrationAction]) -> str:
    lines = ["# Arbor Hook Registration", ""]
    for action in actions:
        suffix = f" ({action.detail})" if action.detail else ""
        lines.append(f"- {action.status}: {action.path}{suffix}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root to update.")
    parser.add_argument("--dry-run", action="store_true", help="Report hook registration without writing files.")
    parser.add_argument(
        "--runtime",
        choices=RUNTIME_CHOICES,
        default=RUNTIME_AUTO,
        help=(
            "Which project hook surface to initialize. auto detects the installed plugin cache "
            "runtime and falls back to Codex in development checkouts; both initializes .codex "
            "hooks plus .claude project hook files."
        ),
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        actions = register_project_hooks(args.root, dry_run=args.dry_run, runtime=args.runtime)
    except HookRegistrationError as exc:
        parser.error(str(exc))
    except OSError as exc:
        print(f"hook registration failed: {exc}", file=sys.stderr)
        return 1
    print(render_actions(actions))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
