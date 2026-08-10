"""Project and plugin path resolution for Arbor."""

from __future__ import annotations

import json
import os
from pathlib import Path

PROJECT_GUIDE = Path("AGENTS.md")
CLAUDE_BRIDGE = Path("CLAUDE.md")
ARBOR_DIR = Path(".arbor")
MEMORY_FILE = ARBOR_DIR / "memory.md"
IDEAS_FILE = ARBOR_DIR / "ideas.md"
SESSION_FILE = ARBOR_DIR / "session.json"

GUIDE_IMPORT = "@AGENTS.md"

_UNKNOWN_VERSION = "unknown"


def is_arbor_project(root: Path) -> bool:
    """Report whether ``root`` has opted into Arbor.

    Presence of the ``.arbor`` directory is the only opt-in signal. Plugin-level
    hooks fire in every project the user opens, so every hook entrypoint gates
    on this before doing anything observable.
    """
    return (root / ARBOR_DIR).is_dir()


def host_tasks_dir(session_id: str) -> Path | None:
    """Locate the host's own task files for a session.

    Claude Code keeps one JSON file per task under
    ``<config>/tasks/<session-id>/<n>.json``. That directory is the authoritative
    list, which matters because the task tools operate on a single task at a time:
    a hook payload for one create or update cannot describe the whole list.

    Returns ``None`` when the directory does not exist, which is the normal case
    for a session that never created a task and for hosts that do not keep this
    state at all.
    """
    if not session_id:
        return None
    configured = os.environ.get("CLAUDE_CONFIG_DIR")
    base = Path(configured).expanduser() if configured else Path.home() / ".claude"
    try:
        directory = base / "tasks" / session_id
        return directory if directory.is_dir() else None
    except (OSError, RuntimeError):
        return None


def plugin_root(start: Path | None = None) -> Path | None:
    """Locate the installed plugin root by walking up to its manifest."""
    current = (start or Path(__file__)).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".claude-plugin" / "plugin.json").is_file():
            return candidate
    return None


def plugin_version(start: Path | None = None) -> str:
    """Read the plugin version, or ``"unknown"`` when it cannot be determined."""
    root = plugin_root(start)
    if root is None:
        return _UNKNOWN_VERSION
    try:
        manifest = json.loads((root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return _UNKNOWN_VERSION
    version = manifest.get("version") if isinstance(manifest, dict) else None
    return version if isinstance(version, str) and version else _UNKNOWN_VERSION


def template_path(name: str, start: Path | None = None) -> Path | None:
    """Resolve a packaged reference template by filename."""
    root = plugin_root(start)
    if root is None:
        return None
    candidate = root / "skills" / "arbor" / "references" / name
    return candidate if candidate.is_file() else None


def write_text_lf(path: Path, text: str) -> None:
    """Write UTF-8 text with LF endings so generated files stay byte-stable."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def read_text_or_empty(path: Path) -> str:
    """Read UTF-8 text, returning ``""`` for missing or undecodable files."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def plural(count: int, singular: str, plural_form: str | None = None) -> str:
    """Format a count with a correctly pluralized noun."""
    if count == 1:
        return f"{count} {singular}"
    return f"{count} {plural_form or singular + 's'}"


def env_float(name: str, default: float) -> float:
    """Read a positive float from the environment, falling back on any error."""
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def env_int(name: str, default: int) -> int:
    """Read a positive int from the environment, falling back on any error."""
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default
