"""The SessionStart context packet.

Arbor injects only volatile state. The durable project guide reaches the model
natively through ``CLAUDE.md`` importing ``AGENTS.md``, which also survives
compaction, so spending injection budget on it would pay transport cost for
content the host already loads.

Sections are bounded when they are built and dropped whole, lowest priority
first, if the packet still exceeds its budget. A dropped section is replaced by
the command or file that recovers it, so dropping defers information instead of
losing it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import notes, session, vcs
from .paths import (
    CLAUDE_BRIDGE,
    GUIDE_IMPORT,
    SESSION_FILE,
    env_int,
    plural,
    read_text_or_empty,
)

DEFAULT_BUDGET = 9500
_BUDGET_ENV = "ARBOR_CONTEXT_BUDGET"

MAX_TODOS = 12
MAX_TREE_ENTRIES = 12
MAX_IDEAS = 3
MAX_COMMITS = 5

HEADER = "# Arbor Session Context"

PROTOCOL = (
    "Volatile project state recovered by Arbor. The durable project guide loads "
    "separately through `CLAUDE.md`. Use this to re-enter the work, not as a "
    "reason to invoke planning, review, or workflow tools.",
    "- Notes below describe the project as it was when they were written. A file "
    "or symbol one of them names may have since been renamed or removed, so "
    "confirm it still exists before acting on it.",
    "- Before this session ends, record anything still undecided in "
    "`.arbor/memory.md`, and remove entries that are now resolved.",
    "- When the user floats an idea that is not part of the current task, append "
    "one line to `.arbor/ideas.md` instead of acting on it.",
)

GUIDE_WARNING = (
    "- `CLAUDE.md` does not import `AGENTS.md`, so the durable project guide is "
    "not being loaded. Run Arbor init or add `@AGENTS.md` to `CLAUDE.md`."
)


@dataclass
class Section:
    """One packet section with its drop priority and recovery hint."""

    key: str
    title: str
    priority: int
    body: str
    hint: str
    dropped: bool = False

    def render(self) -> str:
        if self.dropped:
            return f"## {self.title}\n[omitted for context budget - {self.hint}]\n"
        return f"## {self.title}\n{self.body.rstrip()}\n"


def budget() -> int:
    """Return the injection budget in characters."""
    return env_int(_BUDGET_ENV, DEFAULT_BUDGET)


def guide_is_wired(root: Path) -> bool:
    """Report whether ``CLAUDE.md`` imports ``AGENTS.md``.

    The import must be outside backticks to take effect, matching how Claude Code
    parses memory imports.
    """
    text = read_text_or_empty(root / CLAUDE_BRIDGE)
    if not text:
        return False
    for line in text.splitlines():
        stripped = line.strip()
        if GUIDE_IMPORT in stripped and f"`{GUIDE_IMPORT}`" not in stripped:
            return True
    return False


def _position_section(status: vcs.Status, head: str) -> Section | None:
    if not status.is_repo:
        return None
    parts = []
    if status.branch:
        parts.append(f"branch {status.branch}")
    if head:
        parts.append(f"HEAD {head}")
    if status.upstream:
        if status.ahead or status.behind:
            drift = []
            if status.ahead:
                drift.append(f"{status.ahead} ahead")
            if status.behind:
                drift.append(f"{status.behind} behind")
            parts.append(f"{', '.join(drift)} of {status.upstream}")
        else:
            parts.append(f"level with {status.upstream}")
    else:
        parts.append("no upstream")
    if not parts:
        return None
    return Section("position", "Position", 1, ", ".join(parts), "run `git status -sb`")


def _todo_section(state: dict, head: str) -> Section | None:
    items = session.todo_items(state)
    if not items:
        return None
    unfinished = session.unfinished_todos(state)
    done = len(session.todo_items(state, "completed"))

    lines = []
    summary = f"{len(unfinished)} unfinished, {done} done"
    captured_head = state.get("todos", {}).get("captured_head", "")
    if head and captured_head and captured_head != head:
        summary += ", captured before the latest commit"
    lines.append(summary)
    if unfinished:
        for item in unfinished[:MAX_TODOS]:
            marker = ">" if item.get("status") == "in_progress" else " "
            lines.append(f"- [{marker}] {item.get('content', '')}")
        if len(unfinished) > MAX_TODOS:
            lines.append(f"- (+{len(unfinished) - MAX_TODOS} more)")
    else:
        lines.append("- every captured task was completed")
    return Section("todos", "In flight", 2, "\n".join(lines), f"read `{SESSION_FILE.as_posix()}`")


def _memory_section(memory: notes.Notes, root: Path) -> Section | None:
    if not memory.readable:
        return Section(
            "memory",
            "Unresolved",
            3,
            "`.arbor/memory.md` could not be decoded as UTF-8; treat it as damaged, not as resume context.",
            "repair `.arbor/memory.md`",
        )
    if not memory.entries:
        return None
    lines = []
    if memory.conflicted:
        # Both sides of the conflict are listed below, because the entry parser
        # skips the markers. Saying so is what stops that from looking settled.
        lines.append(
            "- NOTE: `.arbor/memory.md` has an unresolved merge conflict; "
            "both sides are listed here and the file needs reconciling."
        )
    for entry in memory.entries:
        gone = notes.missing_anchors(root, entry)
        if gone:
            # The note is still shown: it may hold the only record of why the
            # path was removed. What changes is that it no longer reads as a
            # current description of the tree.
            lines.append(f"- {entry.text} [outdated: {', '.join(f'`{path}`' for path in gone)} no longer exists]")
        else:
            lines.append(f"- {entry.text}")
    if memory.stale:
        ignored = plural(len(memory.stale), "legacy hook-written entry", "legacy hook-written entries")
        lines.append(f"- ({ignored} ignored; prune them)")
    if memory.line_count >= notes.LINE_BUDGET * notes.WARN_FRACTION:
        lines.append(
            f"- (`.arbor/memory.md` is at {memory.line_count} of {notes.LINE_BUDGET} lines; "
            "prune a resolved entry before adding another)"
        )
    return Section("memory", "Unresolved", 3, "\n".join(lines), "read `.arbor/memory.md`")


def _tree_section(status: vcs.Status) -> Section | None:
    if not status.entries:
        return None
    lines = [plural(status.dirty_count, "changed path")]
    for code, path in status.entries[:MAX_TREE_ENTRIES]:
        lines.append(f"{code} {path}")
    if status.dirty_count > MAX_TREE_ENTRIES:
        lines.append(f"(+{status.dirty_count - MAX_TREE_ENTRIES} more)")
    return Section("tree", "Working tree", 4, "\n".join(lines), "run `git status --short`")


def _ideas_section(ideas: notes.Notes) -> Section | None:
    if not ideas.entries:
        return None
    recent = ideas.entries[-MAX_IDEAS:]
    lines = [f"{len(ideas.entries)} parked; most recent:"]
    lines.extend(f"- {entry.text}" for entry in reversed(recent))
    return Section("ideas", "Parked ideas", 5, "\n".join(lines), "read `.arbor/ideas.md`")


def _commits_section(root: Path) -> Section | None:
    commits = vcs.recent_commits(root, MAX_COMMITS)
    if not commits:
        return None
    return Section("commits", "Recent commits", 6, "\n".join(commits), "run `git log -10 --oneline`")


def build_sections(root: Path) -> list[Section]:
    """Collect every non-empty packet section in render order.

    Nothing here may carry a wall-clock value. The packet is injected context, so
    a value that changes while the project does not would invalidate the prompt
    prefix cache on every session for no informational gain.
    """
    status = vcs.status(root)
    head = vcs.head(root) if status.is_repo else ""
    state = session.load(root)
    candidates = [
        _position_section(status, head),
        _todo_section(state, head),
        _memory_section(notes.read_memory(root), root),
        _tree_section(status),
        _ideas_section(notes.read_ideas(root)),
        _commits_section(root),
    ]
    return [section for section in candidates if section is not None]


def _protocol(root: Path) -> str:
    lines = list(PROTOCOL)
    if not guide_is_wired(root):
        lines.append(GUIDE_WARNING)
    return "\n".join(lines)


def render(root: Path, sections: list[Section], limit: int | None = None) -> str:
    """Render the packet, dropping low-priority sections to fit the budget.

    Returns ``""`` when not even the protocol fits. The host discards
    over-budget hook output silently, so emitting a half-written instruction
    would lose the whole packet anyway while looking like it succeeded.
    """
    cap = budget() if limit is None else limit
    preamble = f"{HEADER}\n\n{_protocol(root)}\n"
    if len(preamble) > cap:
        return ""

    def assemble() -> str:
        return "\n".join([preamble, *(section.render() for section in sections)])

    packet = assemble()
    if len(packet) <= cap:
        return packet

    for section in sorted(sections, key=lambda item: item.priority, reverse=True):
        section.dropped = True
        packet = assemble()
        if len(packet) <= cap:
            return packet

    # Every section is reduced to a hint line and the packet still does not fit.
    return preamble


def summary(sections: list[Section], size: int) -> str:
    """Describe what was injected, for the user-visible receipt.

    This goes to ``systemMessage``, which the user sees and the model never
    does, so it costs no context tokens. It is the cheapest possible proof that
    the hook actually ran.
    """
    loaded = [section.title.lower() for section in sections if not section.dropped]
    omitted = [section.title.lower() for section in sections if section.dropped]
    if not loaded and not omitted:
        return f"Arbor: no volatile state to restore ({size} chars)"
    parts = [f"Arbor loaded {', '.join(loaded)}" if loaded else "Arbor loaded nothing"]
    if omitted:
        parts.append(f"omitted {', '.join(omitted)} for budget")
    parts.append(f"{size} chars")
    return "; ".join(parts)


def build(root: Path, limit: int | None = None) -> tuple[str, str]:
    """Build the SessionStart packet and its receipt line for ``root``."""
    sections = build_sections(root)
    rendered = render(root, sections, limit)
    return rendered, summary(sections, len(rendered))
