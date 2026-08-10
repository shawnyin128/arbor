"""``arbor init``: create Arbor's files without ever overwriting user content.

Initialization is additive. Existing files are left byte-identical, so running
init twice changes nothing the second time. The one exception is a targeted,
additive edit: appending the ``@AGENTS.md`` import to a ``CLAUDE.md`` that lacks
it, because without that line the durable project guide is never loaded.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import packet
from .paths import (
    ARBOR_DIR,
    CLAUDE_BRIDGE,
    GUIDE_IMPORT,
    IDEAS_FILE,
    MEMORY_FILE,
    PROJECT_GUIDE,
    read_text_or_empty,
    template_path,
    write_text_lf,
)

GITIGNORE_FILE = ARBOR_DIR / ".gitignore"

# Machine-written state churns on every todo change, so it is kept out of review
# while the agent-written notes beside it stay committed and diffable.
GITIGNORE_BODY = """# Machine-written session state. Arbor rewrites this file on every
# todo change and at session end; it is not useful in review.
session.json
"""

TEMPLATES = {
    PROJECT_GUIDE: "agents-template.md",
    CLAUDE_BRIDGE: "claude-template.md",
    MEMORY_FILE: "memory-template.md",
    IDEAS_FILE: "ideas-template.md",
}

BRIDGE_APPEND = f"""
{GUIDE_IMPORT}
"""


class InitError(Exception):
    """Raised when initialization cannot proceed safely."""


@dataclass
class Action:
    """One initialization outcome."""

    path: str
    status: str
    detail: str = ""


def _load_template(name: str) -> str:
    path = template_path(name)
    if path is None:
        raise InitError(f"packaged template not found: {name}")
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise InitError(f"could not read packaged template {name}: {exc}") from exc


def _ensure_file(root: Path, relative: Path, content: str, dry_run: bool) -> Action:
    target = root / relative
    label = relative.as_posix()
    if target.exists():
        if not target.is_file():
            raise InitError(f"cannot initialize {label}: a directory exists at that path")
        return Action(label, "exists")
    if dry_run:
        return Action(label, "would_create")
    try:
        write_text_lf(target, content)
    except OSError as exc:
        raise InitError(f"could not create {label}: {exc}") from exc
    return Action(label, "created")


def _wire_bridge(root: Path, dry_run: bool) -> Action:
    """Append the guide import to an existing ``CLAUDE.md`` that lacks it."""
    label = CLAUDE_BRIDGE.as_posix()
    if packet.guide_is_wired(root):
        return Action(label, "exists", f"already imports {GUIDE_IMPORT}")
    existing = read_text_or_empty(root / CLAUDE_BRIDGE)
    if dry_run:
        return Action(label, "would_update", f"append {GUIDE_IMPORT}")
    updated = existing.rstrip("\n") + "\n" + BRIDGE_APPEND
    try:
        write_text_lf(root / CLAUDE_BRIDGE, updated)
    except OSError as exc:
        raise InitError(f"could not update {label}: {exc}") from exc
    return Action(label, "updated", f"appended {GUIDE_IMPORT}")


def run(root: Path, dry_run: bool = False) -> list[Action]:
    """Initialize Arbor in ``root`` and report what happened."""
    if not root.is_dir():
        raise InitError(f"project root does not exist: {root}")

    actions: list[Action] = []

    directory = root / ARBOR_DIR
    if directory.exists() and not directory.is_dir():
        raise InitError(f"cannot initialize {ARBOR_DIR.as_posix()}: a file exists at that path")
    if directory.is_dir():
        actions.append(Action(ARBOR_DIR.as_posix(), "exists"))
    elif dry_run:
        actions.append(Action(ARBOR_DIR.as_posix(), "would_create"))
    else:
        try:
            directory.mkdir(parents=True)
        except OSError as exc:
            raise InitError(f"could not create {ARBOR_DIR.as_posix()}: {exc}") from exc
        actions.append(Action(ARBOR_DIR.as_posix(), "created"))

    for relative, template in TEMPLATES.items():
        if relative == CLAUDE_BRIDGE and (root / CLAUDE_BRIDGE).is_file():
            actions.append(_wire_bridge(root, dry_run))
            continue
        actions.append(_ensure_file(root, relative, _load_template(template), dry_run))

    actions.append(_ensure_file(root, GITIGNORE_FILE, GITIGNORE_BODY, dry_run))
    return actions


def render(root: Path, actions: list[Action]) -> str:
    """Render the initialization report."""
    lines = [
        "**Arbor Init**",
        f"Project: {root}",
        "",
        "| Path | Status | Detail |",
        "| --- | --- | --- |",
    ]
    for action in actions:
        lines.append(f"| {action.path} | {action.status} | {action.detail} |")
    return "\n".join(lines) + "\n"
