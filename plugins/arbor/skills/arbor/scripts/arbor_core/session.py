"""Machine-owned session state in ``.arbor/session.json``.

Only hooks write this file. It holds the todo snapshot, the end-of-session
handoff summary, and one receipt per hook invocation so that whether a hook
actually fired is auditable rather than assumed.

Writes are atomic and never create ``.arbor`` themselves: plugin-level hooks
fire in every project the user opens, and a project opts into Arbor by having
that directory. Enforcing it here as well as in the hook gate means a gating bug
still cannot leave state in an unrelated repository.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import SCHEMA_VERSION
from . import vcs
from .paths import ARBOR_DIR, IDEAS_FILE, MEMORY_FILE, SESSION_FILE, host_tasks_dir, plugin_version

TODO_STATUSES = ("in_progress", "pending", "completed")


def utc_now() -> str:
    """Return the current UTC time as a seconds-precision ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def empty_state() -> dict[str, Any]:
    """Return a valid, empty session record."""
    return {
        "schema": SCHEMA_VERSION,
        "updated_at": "",
        "session": {},
        "todos": {},
        "handoff": {},
        "receipts": {},
    }


def load(root: Path) -> dict[str, Any]:
    """Read the session record.

    A missing, unreadable, malformed, or foreign-schema file yields an empty
    record rather than an error, so a corrupt file can never break a hook or
    propagate into rendered context.
    """
    path = root / SESSION_FILE
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return empty_state()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return empty_state()
    if not isinstance(data, dict) or data.get("schema") != SCHEMA_VERSION:
        return empty_state()

    state = empty_state()
    for key in ("session", "todos", "handoff", "receipts"):
        value = data.get(key)
        if isinstance(value, dict):
            state[key] = value
    updated = data.get("updated_at")
    state["updated_at"] = updated if isinstance(updated, str) else ""
    return state


def save(root: Path, state: dict[str, Any]) -> bool:
    """Atomically write the session record.

    Returns ``False`` without writing when the project has not opted into Arbor
    or the write fails; hooks treat that as a silent skip.
    """
    directory = root / ARBOR_DIR
    if not directory.is_dir():
        return False
    state["schema"] = SCHEMA_VERSION
    state["updated_at"] = utc_now()
    payload = json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True) + "\n"

    handle = None
    temp_path = None
    try:
        fd, temp_name = tempfile.mkstemp(prefix=".session-", suffix=".tmp", dir=str(directory))
        temp_path = Path(temp_name)
        handle = os.fdopen(fd, "w", encoding="utf-8", newline="\n")
        handle.write(payload)
        handle.close()
        handle = None
        os.replace(temp_path, root / SESSION_FILE)
        return True
    except OSError:
        if handle is not None:
            handle.close()
        if temp_path is not None:
            try:
                temp_path.unlink()
            except OSError:
                pass
        return False


def record_receipt(state: dict[str, Any], event: str) -> None:
    """Stamp a hook invocation into the record."""
    receipts = state.setdefault("receipts", {})
    receipts[event] = {"at": utc_now(), "version": plugin_version()}


def normalize_todos(raw: Any) -> list[dict[str, str]] | None:
    """Validate a ``TodoWrite`` todos array.

    Returns the normalized items, or ``None`` when the payload is not a
    recognizable todo list. ``None`` means "leave the existing snapshot alone":
    an unexpected shape must never overwrite good state with garbage.
    """
    if not isinstance(raw, list):
        return None
    items: list[dict[str, str]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        content = entry.get("content")
        status = entry.get("status")
        if not isinstance(content, str) or not content.strip():
            continue
        if status not in TODO_STATUSES:
            continue
        item = {"content": content.strip(), "status": status}
        active = entry.get("activeForm")
        if isinstance(active, str) and active.strip():
            item["activeForm"] = active.strip()
        items.append(item)
    if not items and raw:
        return None
    return items


def read_host_tasks(session_id: str) -> list[dict[str, str]] | None:
    """Read the host's own task list for a session.

    Returns ``None`` when there is no such list, so callers can leave an existing
    snapshot alone rather than replacing it with nothing.
    """
    directory = host_tasks_dir(session_id)
    if directory is None:
        return None
    entries: list[tuple[int, dict[str, str]]] = []
    try:
        files = sorted(directory.glob("*.json"))
    except OSError:
        return None
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        subject = data.get("subject")
        status = data.get("status")
        if not isinstance(subject, str) or not subject.strip():
            continue
        if status not in TODO_STATUSES:
            continue
        item = {"content": subject.strip(), "status": status}
        active = data.get("activeForm")
        if isinstance(active, str) and active.strip():
            item["activeForm"] = active.strip()
        try:
            order = int(str(data.get("id", path.stem)))
        except ValueError:
            order = 0
        entries.append((order, item))
    if not entries:
        return None
    return [item for _order, item in sorted(entries, key=lambda pair: pair[0])]


def _store_todos(root: Path, items: list[dict[str, str]], session_id: str, head: str, event: str) -> bool:
    state = load(root)
    state["todos"] = {"captured_at": utc_now(), "captured_head": head, "items": items}
    if session_id:
        state.setdefault("session", {})["id"] = session_id
    record_receipt(state, event)
    return save(root, state)


def snapshot_todos(root: Path, raw: Any, session_id: str = "", head: str = "") -> bool:
    """Replace the todo snapshot from a ``TodoWrite`` payload.

    ``head`` records the commit the snapshot was taken at, which lets the packet
    express staleness as commit distance instead of a wall-clock timestamp.

    Returns ``True`` when the snapshot was written.
    """
    items = normalize_todos(raw)
    if items is None:
        return False
    return _store_todos(root, items, session_id, head, "PostToolUse:TodoWrite")


def snapshot_host_tasks(root: Path, session_id: str, head: str = "", event: str = "PostToolUse:Task") -> bool:
    """Replace the todo snapshot from the host's own task files."""
    items = read_host_tasks(session_id)
    if items is None:
        return False
    return _store_todos(root, items, session_id, head, event)


def todo_items(state: dict[str, Any], status: str | None = None) -> list[dict[str, str]]:
    """Return snapshot items, optionally filtered by status."""
    raw = state.get("todos", {}).get("items")
    if not isinstance(raw, list):
        return []
    items = [item for item in raw if isinstance(item, dict)]
    if status is None:
        return items
    return [item for item in items if item.get("status") == status]


def unfinished_todos(state: dict[str, Any]) -> list[dict[str, str]]:
    """Return in-progress items first, then pending ones."""
    return todo_items(state, "in_progress") + todo_items(state, "pending")


def record_handoff(root: Path, reason: str, branch: str, head: str, dirty_count: int, session_id: str = "") -> bool:
    """Write the end-of-session summary."""
    state = load(root)
    state["handoff"] = {
        "at": utc_now(),
        "reason": reason,
        "branch": branch,
        "head": head,
        "dirty_count": dirty_count,
        "unfinished": len(unfinished_todos(state)),
    }
    session = state.setdefault("session", {})
    session["ended_at"] = utc_now()
    if session_id:
        session["id"] = session_id
    record_receipt(state, "SessionEnd")
    return save(root, state)


def notes_fingerprint(root: Path) -> str:
    """Fingerprint the agent-written notes, for detecting that they changed.

    Content rather than mtime, because a rewrite that restores the same bytes has
    recorded nothing, and because git checkouts move mtimes without changing text.
    """
    digest = hashlib.sha256()
    for relative in (MEMORY_FILE, IDEAS_FILE):
        try:
            digest.update((root / relative).read_bytes())
        except OSError:
            digest.update(b"\0")
    return digest.hexdigest()[:16]


def record_start(root: Path, session_id: str, source: str) -> bool:
    """Stamp the SessionStart receipt and note the new session."""
    state = load(root)
    session = state.setdefault("session", {})
    session["started_at"] = utc_now()
    session["source"] = source
    if session_id:
        session["id"] = session_id
    # The baseline the prompt nudge compares against: anything written to the
    # notes after this point counts as this session having recorded something.
    session["notes_at_start"] = notes_fingerprint(root)
    session["head_at_start"] = vcs.head(root)
    record_receipt(state, "SessionStart")
    return save(root, state)


# A session has to get somewhere before an unwritten note means anything, but a
# commit is the wrong bar: the case this exists for is an afternoon of design that
# produced conversation and no commit yet. Turns count as progress too.
NUDGE_AFTER_PROMPTS = 3


def count_prompt(root: Path) -> int:
    """Record that the user sent a message, and return the count for this session."""
    state = load(root)
    session = state.setdefault("session", {})
    count = session.get("prompts")
    session["prompts"] = (count if isinstance(count, int) else 0) + 1
    save(root, state)
    return session["prompts"]


def nothing_recorded_yet(root: Path, head: str, prompts: int) -> bool:
    """Whether this session got somewhere and wrote none of it down.

    Both halves matter. Without the first, a session that has barely started gets
    asked about notes it could not have. Without the second, a session that already
    recorded something keeps being asked.
    """
    state = load(root)
    session = state.get("session", {})
    if not isinstance(session, dict) or not session.get("started_at"):
        return False
    if notes_fingerprint(root) != session.get("notes_at_start"):
        return False

    moved = bool(head) and head != session.get("head_at_start")
    captured = state.get("todos", {}).get("captured_at", "")
    tasks_changed = isinstance(captured, str) and captured >= session["started_at"]
    return bool(moved or tasks_changed or prompts >= NUDGE_AFTER_PROMPTS)


def receipt(state: dict[str, Any], event: str) -> dict[str, str]:
    """Return one receipt, or an empty mapping when the hook never fired."""
    value = state.get("receipts", {}).get(event)
    return value if isinstance(value, dict) else {}
