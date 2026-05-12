#!/usr/bin/env python3
"""Shared Arbor project-state paths and initialization helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_GUIDE_PATH = Path("AGENTS.md")
CLAUDE_GUIDE_PATH = Path("CLAUDE.md")
CANONICAL_MEMORY_PATH = Path(".arbor") / "memory.md"
LEGACY_CODEX_MEMORY_PATH = Path(".codex") / "memory.md"
CODEX_HOOK_CONFIG_PATH = Path(".codex") / "hooks.json"

INSTALL_RUNTIME_CODEX = "codex"
INSTALL_RUNTIME_CLAUDE = "claude"


@dataclass(frozen=True)
class ProjectFileAction:
    path: Path
    status: str
    detail: str = ""


class ProjectStateError(ValueError):
    """Raised when Arbor project-state files cannot be handled safely."""


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
        if not dry_run:
            canonical.parent.mkdir(parents=True, exist_ok=True)
            canonical.write_text(legacy.read_text(encoding="utf-8"), encoding="utf-8")
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
