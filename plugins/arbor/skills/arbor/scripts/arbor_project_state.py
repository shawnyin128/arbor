#!/usr/bin/env python3
"""Shared Arbor project-state paths and initialization helpers."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


sys.dont_write_bytecode = True

PROJECT_GUIDE_PATH = Path("AGENTS.md")
CLAUDE_GUIDE_PATH = Path("CLAUDE.md")
CANONICAL_MEMORY_PATH = Path(".arbor") / "memory.md"
LEGACY_CODEX_MEMORY_PATH = Path(".codex") / "memory.md"
CODEX_HOOK_CONFIG_PATH = Path(".codex") / "hooks.json"
CODEX_HOOKS_DIR = Path(".codex") / "hooks"
CLAUDE_SETTINGS_PATH = Path(".claude") / "settings.json"
CLAUDE_HOOKS_DIR = Path(".claude") / "hooks"

INSTALL_RUNTIME_CODEX = "codex"
INSTALL_RUNTIME_CLAUDE = "claude"
HOOKLESS_CONTRACT_START = "<!-- ARBOR HOOKLESS RUNTIME CONTRACT START -->"
HOOKLESS_CONTRACT_END = "<!-- ARBOR HOOKLESS RUNTIME CONTRACT END -->"


def hookless_runtime_contract() -> str:
    """Return the durable AGENTS.md bootstrap block for hookless Arbor."""
    return "\n".join(
        [
            HOOKLESS_CONTRACT_START,
            "Arbor hookless runtime contract:",
            "",
            "Arbor package scripts live under the installed Arbor skill root at skills/arbor/scripts.",
            "Resolve the newest installed Arbor skill root from the runtime cache, for example",
            "%USERPROFILE%/.codex/plugins/cache/arbor/arbor/*/skills/arbor on Codex or",
            "~/.claude/plugins/cache/arbor/arbor/*/skills/arbor on Claude Code.",
            "Do not look for these scripts under <project-root>/scripts or <plugin-root>/scripts.",
            "Use a direct Python executable for Arbor context helpers. On Windows, do not wrap these",
            "commands in conda run; it can recode captured stdout and corrupt large UTF-8 context packets.",
            "If python is not on PATH, call the absolute interpreter directly, such as <conda-base>/python.exe.",
            "",
            "Arbor startup: before answering a non-trivial project task or resume question, run",
            "python <arbor-skill-root>/scripts/run_session_startup_hook.py --root <project-root>.",
            "If that script is unavailable, manually read in this order: AGENTS.md; recent formatted git log;",
            ".arbor/memory.md; git status --short.",
            "",
            "Arbor finalization: before the final response for a non-trivial task, handoff, or dirty-worktree turn, run",
            "python <arbor-skill-root>/scripts/run_hookless_finalization.py --root <project-root>.",
            "That command runs the Stop-equivalent maintenance path first, then emits memory hygiene and AGENTS",
            "Project Map drift context.",
            "Use its output to decide whether any additional .arbor/memory.md or AGENTS.md edit is needed.",
            "",
            "Do not register or repair project hooks unless the user explicitly asks for legacy hook repair.",
            "Arbor context is orientation and recovery only; it must not choose planning, debugging, review, or",
            "branch-finishing methodology by itself.",
            HOOKLESS_CONTRACT_END,
        ]
    )


@dataclass(frozen=True)
class ProjectFileAction:
    path: Path
    status: str
    detail: str = ""


class ProjectStateError(ValueError):
    """Raised when Arbor project-state files cannot be handled safely."""


def has_hookless_runtime_contract(text: str) -> bool:
    return HOOKLESS_CONTRACT_START in text and HOOKLESS_CONTRACT_END in text


def append_hookless_runtime_contract(text: str) -> str:
    contract = hookless_runtime_contract()
    body = text.rstrip()
    if not body:
        return contract + "\n"

    constraints_match = re.search(r"(?m)^##\s+Project Constraints\s*$", body)
    if constraints_match:
        body_start = constraints_match.end()
        if body_start < len(body) and body[body_start] == "\n":
            body_start += 1
        next_heading = re.search(r"(?m)^##\s+", body[body_start:])
        insert_at = body_start + next_heading.start() if next_heading else len(body)
        before = body[:insert_at].rstrip()
        after = body[insert_at:].lstrip("\n")
        if after:
            return before + "\n\n" + contract + "\n\n" + after + "\n"
        return before + "\n\n" + contract + "\n"

    return body + "\n\n" + contract + "\n"


def resolve_project_root(root: Path) -> Path:
    resolved = root.resolve()
    if not resolved.exists():
        raise ProjectStateError(f"project root does not exist: {resolved}")
    if not resolved.is_dir():
        raise ProjectStateError(f"project root is not a directory: {resolved}")
    return resolved


def ensure_under_root(root: Path, path: Path) -> None:
    if path != root and root not in path.parents:
        raise ProjectStateError(f"refusing to write outside project root: {path}")


def project_path(root: Path, relative_path: Path) -> Path:
    resolved_root = resolve_project_root(root)
    resolved_path = (resolved_root / relative_path).resolve()
    ensure_under_root(resolved_root, resolved_path)
    return resolved_path


def ensure_file(path: Path, content: str, dry_run: bool) -> ProjectFileAction:
    if path.exists():
        if not path.is_file():
            raise ProjectStateError(f"cannot initialize {path}: expected a file but found a directory")
        return ProjectFileAction(path=path, status="exists")
    if path.parent.exists() and not path.parent.is_dir():
        raise ProjectStateError(f"cannot initialize {path}: parent path is not a directory")
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return ProjectFileAction(path=path, status="would_create" if dry_run else "created")


def ensure_project_guide_file(root: Path, template: str, dry_run: bool) -> ProjectFileAction:
    target = project_path(resolve_project_root(root), PROJECT_GUIDE_PATH)
    content = append_hookless_runtime_contract(template)
    if not target.exists():
        return ensure_file(target, content, dry_run)
    if not target.is_file():
        raise ProjectStateError(f"cannot initialize {target}: expected a file but found a directory")
    try:
        existing = target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ProjectStateError(f"cannot inspect {target}: could not read UTF-8 project guide: {exc}") from exc
    if has_hookless_runtime_contract(existing):
        return ProjectFileAction(path=target, status="exists")
    updated = append_hookless_runtime_contract(existing)
    if not dry_run:
        target.write_text(updated, encoding="utf-8")
    return ProjectFileAction(
        path=target,
        status="would_update" if dry_run else "updated",
        detail="appended Arbor hookless runtime contract",
    )


def ensure_memory_file(root: Path, template: str, dry_run: bool) -> list[ProjectFileAction]:
    resolved_root = resolve_project_root(root)
    canonical = project_path(resolved_root, CANONICAL_MEMORY_PATH)
    legacy = project_path(resolved_root, LEGACY_CODEX_MEMORY_PATH)

    if canonical.exists():
        if not canonical.is_file():
            raise ProjectStateError(f"cannot use {canonical}: expected a file but found a directory")
        actions = [ProjectFileAction(path=canonical, status="exists")]
        if legacy.exists():
            legacy_status = "legacy_ignored" if legacy.is_file() else "legacy_path_conflict"
            actions.append(
                ProjectFileAction(
                    path=legacy,
                    status=legacy_status,
                    detail=f"canonical memory is {CANONICAL_MEMORY_PATH}",
                )
            )
        return actions

    if legacy.exists():
        if not legacy.is_file():
            raise ProjectStateError(f"cannot migrate {legacy}: expected a file but found a directory")
        if canonical.parent.exists() and not canonical.parent.is_dir():
            raise ProjectStateError(f"cannot initialize {canonical}: parent path is not a directory")
        try:
            legacy_text = legacy.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ProjectStateError(f"cannot migrate {legacy}: could not read UTF-8 legacy memory: {exc}") from exc
        if not dry_run:
            canonical.parent.mkdir(parents=True, exist_ok=True)
            canonical.write_text(legacy_text, encoding="utf-8")
        status = "would_migrate_from_legacy" if dry_run else "migrated_from_legacy"
        return [
            ProjectFileAction(
                path=canonical,
                status=status,
                detail=f"copied from {LEGACY_CODEX_MEMORY_PATH}; legacy file preserved",
            ),
            ProjectFileAction(
                path=legacy,
                status="legacy_preserved",
                detail=f"canonical memory is {CANONICAL_MEMORY_PATH}",
            ),
        ]

    return [ensure_file(canonical, template, dry_run)]


def detect_install_runtime(reference: Path | None = None) -> str | None:
    """Identify the host runtime from the file's installed cache path.

    Codex copies installed plugins under ``~/.codex/plugins/cache/...``;
    Claude Code copies them under ``~/.claude/plugins/cache/...``. The cache
    prefix is fixed by each runtime at install time and survives across
    invocations regardless of how the script is launched (hook subprocess,
    Bash tool subprocess, or direct manual run).

    The match requires ``.claude``/``.codex`` to be immediately followed by
    ``plugins`` in the path components, so a development checkout that
    happens to live under ``.claude/worktrees/...`` or ``.codex/<other>/``
    is not misclassified.

    Returns ``"codex"`` or ``"claude"`` when the reference path lives
    inside one of those caches; returns ``None`` for development checkouts
    or any other location, so callers can fall back to a conservative
    default.

    This is the canonical Arbor self-adaptation primitive: scripts that
    need a runtime-specific default should call this helper rather than
    sniffing environment variables, which are only set inside hook
    subprocesses.
    """
    target = (reference if reference is not None else Path(__file__)).resolve()
    parts = target.parts
    for i in range(len(parts) - 1):
        if parts[i + 1] != "plugins":
            continue
        if parts[i] == ".claude":
            return INSTALL_RUNTIME_CLAUDE
        if parts[i] == ".codex":
            return INSTALL_RUNTIME_CODEX
    return None


def ensure_claude_bridge(root: Path, template: str, dry_run: bool) -> ProjectFileAction:
    """Create ``CLAUDE.md`` from a bridge template when it is missing.

    The bridge points Claude Code at Arbor's canonical project guide
    (``AGENTS.md``) and short-term memory (``.arbor/memory.md``). It is
    never overwritten when it already exists; users keep full control of
    their ``CLAUDE.md`` once it has any content.
    """
    resolved_root = resolve_project_root(root)
    target = project_path(resolved_root, CLAUDE_GUIDE_PATH)
    return ensure_file(target, template, dry_run)
