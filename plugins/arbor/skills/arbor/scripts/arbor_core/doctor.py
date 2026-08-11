"""``arbor doctor``: report the state of Arbor's surfaces.

Doctor reports and never repairs. It is the one place that answers "did the
hooks actually fire?", using the receipts hooks leave in ``session.json``,
and "is the injected packet within budget?", by building the real packet.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from . import notes, packet, session, vcs
from .paths import (
    ARBOR_DIR,
    CLAUDE_BRIDGE,
    GUIDE_IMPORT,
    IDEAS_FILE,
    MEMORY_FILE,
    PROJECT_GUIDE,
    SESSION_FILE,
    is_arbor_project,
    plugin_version,
    plural,
    read_text_or_empty,
)

OK = "ok"
WARN = "warn"
FAIL = "fail"
MISSING = "missing"

# Commands is required because running Arbor's init means the user will not run
# Claude Code's `/init`, and commands are the first of the two content areas that
# `/init` produces.
REQUIRED_GUIDE_SECTIONS = ("Project Goal", "Commands", "Project Constraints", "Project Map")

PLACEHOLDER_MARKERS = (
    "has not recorded a stable project goal",
    "has not recorded a durable project map",
    "has not recorded the commands for this repository",
    "inspect the repository itself before answering",
)

# The task-capture receipt is keyed by whichever tool the host exposes, so it is
# reported by family rather than by one exact name.
HOOK_EVENTS = ("SessionStart", "task capture", "SessionEnd")
TASK_RECEIPT_PREFIX = "PostToolUse:"


@dataclass
class Row:
    """One reported surface."""

    surface: str
    status: str
    detail: str


def _section_body(text: str, heading: str) -> str | None:
    match = re.search(
        rf"(?ms)^##\s+{re.escape(heading)}\s*$\n(?P<body>.*?)(?=^##\s|\Z)", text
    )
    return match.group("body") if match else None


def _guide_row(root: Path) -> Row:
    path = root / PROJECT_GUIDE
    if not path.is_file():
        return Row(str(PROJECT_GUIDE), MISSING, "run arbor init")
    text = read_text_or_empty(path)
    if not text:
        return Row(str(PROJECT_GUIDE), FAIL, "empty or not decodable as UTF-8")

    problems = []
    missing_sections = [name for name in REQUIRED_GUIDE_SECTIONS if _section_body(text, name) is None]
    if missing_sections:
        problems.append(f"missing section(s): {', '.join(missing_sections)}")
    if any(marker in text.lower() for marker in PLACEHOLDER_MARKERS):
        problems.append("still contains template placeholder text")

    # Every backticked path in the guide is a claim about the tree, wherever it
    # appears. The map is not privileged: a path named in Project Constraints
    # misleads exactly as much when it goes stale.
    claimed = notes.anchors(text)
    stale = [path for path in claimed if not (root / path).exists() and vcs.knows_path(root, path)]
    if stale:
        problems.append(f"names {plural(len(stale), 'path')} git knows but disk does not: {', '.join(stale)}")

    if problems:
        return Row(str(PROJECT_GUIDE), WARN, "; ".join(problems))
    return Row(str(PROJECT_GUIDE), OK, f"{plural(len(claimed), 'path claim')}, all present")


def _bridge_row(root: Path) -> Row:
    path = root / CLAUDE_BRIDGE
    if not path.is_file():
        return Row(str(CLAUDE_BRIDGE), MISSING, f"run arbor init to create it with {GUIDE_IMPORT}")
    if not packet.guide_is_wired(root):
        return Row(
            str(CLAUDE_BRIDGE),
            FAIL,
            f"does not import {GUIDE_IMPORT}, so AGENTS.md is never loaded",
        )
    line_count = len(read_text_or_empty(path).splitlines())
    detail = f"imports {GUIDE_IMPORT}, {line_count} lines"
    if line_count > 200:
        return Row(str(CLAUDE_BRIDGE), WARN, f"{detail}; keep it under 200 lines")
    return Row(str(CLAUDE_BRIDGE), OK, detail)


def _memory_row(root: Path) -> Row:
    memory = notes.read_memory(root)
    label = MEMORY_FILE.as_posix()
    if not memory.exists:
        return Row(label, MISSING, "run arbor init")
    if not memory.readable:
        return Row(label, FAIL, "not decodable as UTF-8")
    if memory.conflicted:
        return Row(label, FAIL, "has an unresolved merge conflict; reconcile it before trusting it")
    problems = []
    outdated = {
        anchor
        for entry in memory.entries
        for anchor in notes.missing_anchors(root, entry)
    }
    if outdated:
        problems.append(f"names {plural(len(outdated), 'path')} that no longer exist: {', '.join(sorted(outdated))}")
    if memory.stale:
        problems.append(f"{plural(len(memory.stale), 'legacy hook-written entry', 'legacy hook-written entries')} to prune")
    # Size is reported, never judged. There is no line budget: an entry leaves
    # this file when it is resolved, not when the file reaches some length.
    detail = (
        f"{plural(len(memory.entries), 'unresolved entry', 'unresolved entries')}, "
        f"{memory.line_count} lines"
    )
    if problems:
        return Row(label, WARN, f"{detail}; {'; '.join(problems)}")
    return Row(label, OK, detail)


def _ideas_row(root: Path) -> Row:
    ideas = notes.read_ideas(root)
    label = IDEAS_FILE.as_posix()
    if not ideas.exists:
        return Row(label, MISSING, "run arbor init")
    if not ideas.readable:
        return Row(label, FAIL, "not decodable as UTF-8")
    return Row(label, OK, f"{len(ideas.entries)} parked")


def _session_row(root: Path, state: dict) -> Row:
    label = SESSION_FILE.as_posix()
    path = root / SESSION_FILE
    if not path.is_file():
        return Row(label, MISSING, "no hook has run in this project yet")
    if not state.get("receipts") and not state.get("todos"):
        return Row(label, WARN, "present but empty or unreadable; it will be rebuilt")
    todos = session.todo_items(state)
    unfinished = session.unfinished_todos(state)
    return Row(label, OK, f"{plural(len(todos), 'captured task')}, {len(unfinished)} unfinished")


def _hook_rows(state: dict) -> list[Row]:
    receipts = state.get("receipts", {})
    rows = []
    for event in HOOK_EVENTS:
        if event == "task capture":
            matches = {
                key: value
                for key, value in receipts.items()
                if key.startswith(TASK_RECEIPT_PREFIX) and isinstance(value, dict)
            }
            entry = max(matches.values(), key=lambda item: item.get("at", "")) if matches else {}
            label = "task capture hook"
            if entry:
                tools = ", ".join(sorted(key.split(":", 1)[1] for key in matches))
                detail = f"last fired {entry.get('at', 'unknown')} via {tools} (plugin {entry.get('version', 'unknown')})"
                rows.append(Row(label, OK, detail))
                continue
        else:
            entry = session.receipt(state, event)
            label = f"{event} hook"
            if entry:
                version = entry.get("version", "unknown")
                rows.append(Row(label, OK, f"last fired {entry.get('at', 'unknown')} (plugin {version})"))
                continue
        rows.append(Row(label, WARN, "never fired in this project"))
    return rows


def _packet_row(root: Path) -> Row:
    rendered, _ = packet.build(root)
    size = len(rendered)
    limit = packet.budget()
    detail = f"{size} of {limit} chars"
    if size > limit:
        return Row("context packet", WARN, f"{detail}; the tail will spill to a file on disk")
    return Row("context packet", OK, detail)


def collect(root: Path) -> list[Row]:
    """Build every doctor row for ``root``."""
    if not is_arbor_project(root):
        return [Row(ARBOR_DIR.as_posix(), MISSING, "not an Arbor project; run arbor init")]

    state = session.load(root)
    rows = [
        Row(ARBOR_DIR.as_posix(), OK, "present"),
        _guide_row(root),
        _bridge_row(root),
        _memory_row(root),
        _ideas_row(root),
        _session_row(root, state),
    ]
    rows.extend(_hook_rows(state))
    rows.append(_packet_row(root))
    return rows


def result(rows: list[Row]) -> str:
    """Reduce rows to ``ok`` or ``needs_attention``."""
    return OK if all(row.status == OK for row in rows) else "needs_attention"


def render(root: Path, rows: list[Row]) -> str:
    """Render the doctor report."""
    lines = [
        "**Arbor Doctor**",
        f"Project: {root}",
        f"Plugin: {plugin_version()}",
        "",
        "| Surface | Status | Detail |",
        "| --- | --- | --- |",
    ]
    for row in rows:
        lines.append(f"| {row.surface} | {row.status} | {row.detail} |")
    lines.extend(["", f"Result: {result(rows)}"])
    return "\n".join(lines) + "\n"
