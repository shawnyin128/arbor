"""Hook entrypoints.

Each entrypoint takes the raw hook payload and returns ``(exit_code, stdout)``
so behavior can be tested without capturing process streams.

Every entrypoint follows the same rule: anything unexpected is a silent skip
with exit code 0. Plugin-level hooks fire in every project the user opens, so a
hook that fails loudly, blocks, or writes to an unrelated repository is a worse
outcome than a hook that does nothing.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from . import session, vcs
from .paths import is_arbor_project

SESSION_START_SOURCES = frozenset({"startup", "resume", "clear", "compact"})

# Tools that change the agent's task list. TodoWrite sends the whole list;
# the Task tools change one entry at a time.
TASK_TOOLS = frozenset({"TodoWrite", "TaskCreate", "TaskUpdate"})

# Hook payloads are occasionally delivered with a UTF-8 byte order mark.
BOM = chr(0xFEFF)

SKIP: tuple[int, str] = (0, "")


def parse_payload(raw: str) -> dict[str, Any] | None:
    """Parse hook stdin.

    Returns ``None`` for empty input, invalid JSON, or a non-object payload.
    Hook-registration interfaces probe commands with empty or placeholder input,
    and a BOM can precede the JSON, so none of those may raise.
    """
    if not raw:
        return None
    text = raw.lstrip(BOM).strip()
    if not text:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def project_root(payload: dict[str, Any]) -> Path | None:
    """Resolve the project root for this hook invocation.

    ``CLAUDE_PROJECT_DIR`` wins over the payload ``cwd``, because a hook's working
    directory is not a reliable indicator of the project root: it can be a
    subdirectory the session was launched from, and there are reported cases of
    it drifting mid-session. The payload value remains the fallback.
    """
    candidates = [os.environ.get("CLAUDE_PROJECT_DIR"), payload.get("cwd")]
    for candidate in candidates:
        if not isinstance(candidate, str) or not candidate.strip():
            continue
        try:
            root = Path(candidate)
        except (OSError, ValueError):
            continue
        if root.is_dir():
            return root
    return None


def session_start(raw: str) -> tuple[int, str]:
    """Render the context packet for a starting or resuming session."""
    from . import packet

    payload = parse_payload(raw)
    if payload is None:
        return SKIP
    source = payload.get("source")
    if isinstance(source, str) and source not in SESSION_START_SOURCES:
        return SKIP
    root = project_root(payload)
    if root is None or not is_arbor_project(root):
        return SKIP

    try:
        rendered, receipt = packet.build(root)
    except OSError:
        return SKIP
    if not rendered:
        return SKIP

    session_id = payload.get("session_id")
    session.record_start(
        root,
        session_id if isinstance(session_id, str) else "",
        source if isinstance(source, str) else "",
    )

    # `additionalContext` reaches the model; `systemMessage` reaches the user and
    # costs no context tokens. Splitting them keeps the injected block free of
    # anything written for a human to read.
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": rendered,
        },
        "systemMessage": receipt,
        "suppressOutput": True,
    }
    return 0, json.dumps(output, ensure_ascii=False)


NUDGE = (
    "Arbor: this session has changed the project but recorded nothing. If anything "
    "said so far was an aside worth keeping, a decision deferred, a design agreed "
    "but unbuilt, or an open question now answered, write it to `.arbor/ideas.md` "
    "or `.arbor/memory.md` now. If there is genuinely nothing, ignore this line."
)


def prompt_nudge(raw: str) -> tuple[int, str]:
    """Ask, once the session has work to show and nothing written down.

    This runs on every user message, which is the only moment adjacent to what the
    user actually said: an aside is not a request, so nothing routes on it, and a
    reminder delivered at SessionStart sits thousands of tokens away by the time it
    matters. It injects and never blocks. A Stop hook could also reach the model,
    but blocking a stop was measured to replace the assistant's final answer with
    the continuation, which costs the user more than the reminder is worth.
    """
    payload = parse_payload(raw)
    if payload is None:
        return SKIP
    root = project_root(payload)
    if root is None or not is_arbor_project(root):
        return SKIP

    try:
        prompts = session.count_prompt(root)
        if not session.nothing_recorded_yet(root, vcs.head(root), prompts):
            return SKIP
    except OSError:
        return SKIP

    session.record_nudge(root)
    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": NUDGE,
        },
        "suppressOutput": True,
    }
    return 0, json.dumps(output, ensure_ascii=False)


def todo_snapshot(raw: str) -> tuple[int, str]:
    """Persist the task list after the agent changed it.

    Two shapes exist across hosts. ``TodoWrite`` carries the whole list in its
    payload. The ``Task`` tools operate on one task at a time, so a single payload
    cannot describe the list; for those the host's own task files are read, which
    are authoritative anyway.
    """
    payload = parse_payload(raw)
    if payload is None:
        return SKIP
    tool_name = payload.get("tool_name")
    if not isinstance(tool_name, str) or tool_name not in TASK_TOOLS:
        return SKIP
    root = project_root(payload)
    if root is None or not is_arbor_project(root):
        return SKIP

    session_id = payload.get("session_id")
    session_id = session_id if isinstance(session_id, str) else ""
    head = vcs.head(root)

    if tool_name == "TodoWrite":
        tool_input = payload.get("tool_input")
        if not isinstance(tool_input, dict):
            return SKIP
        session.snapshot_todos(root, tool_input.get("todos"), session_id, head=head)
        return SKIP

    session.snapshot_host_tasks(root, session_id, head=head, event=f"PostToolUse:{tool_name}")
    return SKIP


def session_end(raw: str) -> tuple[int, str]:
    """Write the end-of-session handoff summary."""
    payload = parse_payload(raw)
    if payload is None:
        return SKIP
    root = project_root(payload)
    if root is None or not is_arbor_project(root):
        return SKIP

    status = vcs.status(root)
    reason = payload.get("reason")
    session_id = payload.get("session_id")
    if isinstance(session_id, str) and session_id:
        # Backstop: if a task changed without the tool hook firing, the host list
        # is still correct at the end of the session.
        session.snapshot_host_tasks(root, session_id, head=vcs.head(root), event="SessionEnd")
    session.record_handoff(
        root,
        reason=reason if isinstance(reason, str) else "",
        branch=status.branch,
        head=vcs.head(root) if status.is_repo else "",
        dirty_count=status.dirty_count,
        session_id=session_id if isinstance(session_id, str) else "",
    )
    return SKIP


ENTRYPOINTS = {
    "session-start": session_start,
    "prompt-nudge": prompt_nudge,
    "todo-snapshot": todo_snapshot,
    "session-end": session_end,
}
