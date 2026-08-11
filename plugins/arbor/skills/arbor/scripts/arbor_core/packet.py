"""The SessionStart context packet.

Arbor injects only volatile state, and only the part of it the host does not
already supply. The durable project guide arrives natively through ``CLAUDE.md``
importing ``AGENTS.md``, and the host appends a git block of its own carrying the
branch, the full short status, and the five most recent commits, so none of that
is worth transporting twice.

Sections are bounded when they are built and emitted highest value first. There
is no budget-driven dropping: over-budget hook output keeps its head, spills the
rest to a file, and says so in context, so front-loading is what protects the
information that matters.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import notes, session, vcs
from .paths import (
    CLAUDE_BRIDGE,
    GUIDE_IMPORT,
    env_int,
    plural,
    read_text_or_empty,
)

DEFAULT_BUDGET = 9500
_BUDGET_ENV = "ARBOR_CONTEXT_BUDGET"

MAX_TODOS = 12
MAX_SINCE_COMMITS = 5
MAX_SINCE_PATHS = 8
MAX_IDEAS = 3

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
    """One packet section."""

    key: str
    title: str
    body: str

    def render(self) -> str:
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


def _upstream_section(status: vcs.Status) -> Section | None:
    """Report divergence from the upstream branch, and nothing else.

    The host's own git block already names the branch and lists the working tree
    and the recent commits. Divergence is the one position fact it never carries,
    and only actual divergence is worth saying: "level with" and "no upstream"
    describe a situation that needs no action.
    """
    if not status.is_repo or not status.upstream:
        return None
    if not status.ahead and not status.behind:
        return None
    drift = []
    if status.ahead:
        drift.append(f"{status.ahead} ahead")
    if status.behind:
        drift.append(f"{status.behind} behind")
    return Section("upstream", "Upstream", f"{', '.join(drift)} of {status.upstream}")


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
    return Section("todos", "In flight", "\n".join(lines))


def _memory_section(memory: notes.Notes, root: Path) -> Section | None:
    if not memory.readable:
        return Section(
            "memory",
            "Unresolved",
            "`.arbor/memory.md` could not be decoded as UTF-8; treat it as damaged, not as resume context.",
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
    return Section("memory", "Unresolved", "\n".join(lines))


def _ideas_section(ideas: notes.Notes) -> Section | None:
    if not ideas.entries:
        return None
    recent = ideas.entries[-MAX_IDEAS:]
    lines = [f"{len(ideas.entries)} parked; most recent:"]
    lines.extend(f"- {entry.text}" for entry in reversed(recent))
    return Section("ideas", "Parked ideas", "\n".join(lines))


def _since_section(root: Path, state: dict, head: str) -> Section | None:
    """Report what landed since the last session's recorded HEAD.

    Nobody else ships this, and the only reason Arbor can is that it already
    stamps the commit alongside its todo snapshot and handoff.
    """
    if not head:
        return None
    last = state.get("handoff", {}).get("head") or state.get("todos", {}).get("captured_head") or ""
    if not last or last == head:
        return None

    if not vcs.is_ancestor(root, last):
        # A rewritten history is more important than any diff computed from it,
        # and it is exactly when a resumed session's assumptions are stale.
        return Section(
            "since",
            "Since last session",
            f"History was rewritten: the commit recorded last session ({last}) is no longer "
            "reachable from HEAD, so anything remembered about the tree may not apply.",
        )

    count = vcs.count_commits_since(root, last)
    if not count:
        return None
    lines = [f"{plural(count, 'commit')} since {last}"]
    lines.extend(f"- {entry}" for entry in vcs.commits_since(root, last, MAX_SINCE_COMMITS))
    if count > MAX_SINCE_COMMITS:
        lines.append(f"- (+{count - MAX_SINCE_COMMITS} more)")
    changed, total = vcs.changed_paths_since(root, last, MAX_SINCE_PATHS)
    if changed:
        lines.append(f"{plural(total, 'file')} changed:")
        lines.extend(f"  {entry}" for entry in changed)
        if total > MAX_SINCE_PATHS:
            lines.append(f"  (+{total - MAX_SINCE_PATHS} more)")
    return Section("since", "Since last session", "\n".join(lines))


def build_sections(root: Path) -> list[Section]:
    """Collect every non-empty packet section, highest value first.

    Nothing here may carry a wall-clock value. The packet is injected context, so
    a value that changes while the project does not would invalidate the prompt
    prefix cache on every session for no informational gain.
    """
    status = vcs.status(root)
    head = vcs.head(root) if status.is_repo else ""
    state = session.load(root)
    candidates = [
        _todo_section(state, head),
        _since_section(root, state, head),
        _memory_section(notes.read_memory(root), root),
        _ideas_section(notes.read_ideas(root)),
        _upstream_section(status),
    ]
    return [section for section in candidates if section is not None]


def _protocol(root: Path) -> str:
    lines = list(PROTOCOL)
    if not guide_is_wired(root):
        lines.append(GUIDE_WARNING)
    return "\n".join(lines)


def render(root: Path, sections: list[Section]) -> str:
    """Render the packet with its preamble, highest-value section first."""
    preamble = f"{HEADER}\n\n{_protocol(root)}\n"
    return "\n".join([preamble, *(section.render() for section in sections)])


def summary(sections: list[Section], size: int) -> str:
    """Describe what was injected, for the user-visible receipt.

    This goes to ``systemMessage``, which the user sees and the model never
    does, so it costs no context tokens. It is the cheapest possible proof that
    the hook actually ran.
    """
    if not sections:
        return f"Arbor: no volatile state to restore ({size} chars)"
    loaded = ", ".join(section.title.lower() for section in sections)
    return f"Arbor loaded {loaded}; {size} chars"


def build(root: Path) -> tuple[str, str]:
    """Build the SessionStart packet and its receipt line for ``root``."""
    sections = build_sections(root)
    rendered = render(root, sections)
    return rendered, summary(sections, len(rendered))
