"""Agent-written notes: ``.arbor/memory.md`` and ``.arbor/ideas.md``.

These files hold what a hook cannot observe — why work stopped, what is still
undecided, and ideas the user parked in passing. Arbor only ever reads them; the
agent writes them with its normal editing tools.

Reading is deliberately tolerant. Entries left behind by the hook-written memory
of earlier Arbor versions are reported as stale rather than treated as live
context, so upgrading a project does not resurface machine-generated noise.

An entry that names a file is making a claim about how the code looked when it
was written. Those claims are checked, because injecting a confidently wrong
note is worse than injecting nothing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from . import vcs
from .paths import IDEAS_FILE, MEMORY_FILE, read_text_or_empty

MEMORY_HEADINGS = ("Unresolved", "In-flight")
IDEAS_HEADING = "Parked"

LEGACY_HOOK_MARKERS = ("[hook:resume]", "[hook:fallback]")

_PLACEHOLDERS = frozenset(
    {
        "none",
        "n/a",
        "not applicable",
        "nothing",
        "no unresolved state",
        "no pending uncommitted context recorded yet",
        "no active arbor resume context recorded yet",
        "no undecided short-term observations recorded yet",
        "no parked ideas recorded yet",
        "no unresolved decisions recorded yet",
    }
)

# A top-level bullet starts an entry. Anything indented under it continues that
# entry, so a nested sub-bullet is not mistaken for a separate note.
_ENTRY_START = re.compile(r"^[-*]\s+(?P<body>.*)$")
_BACKTICK = re.compile(r"`([^`\n]+)`")
# Unresolved merge markers. The entry parser skips them, which means both sides
# of a conflict read as ordinary notes and the conflicted state is invisible
# unless it is reported explicitly.
_CONFLICT = re.compile(r"(?m)^(<{7} |={7}$|>{7} )")


@dataclass(frozen=True)
class Entry:
    """One note, plus the paths it claims exist."""

    text: str
    anchors: tuple[str, ...] = ()


@dataclass(frozen=True)
class Notes:
    """Parsed contents of one agent-written notes file."""

    exists: bool = False
    readable: bool = True
    conflicted: bool = False
    entries: list[Entry] = field(default_factory=list)
    stale: list[str] = field(default_factory=list)
    line_count: int = 0

    @property
    def has_content(self) -> bool:
        return bool(self.entries)

    @property
    def texts(self) -> list[str]:
        return [entry.text for entry in self.entries]


def _is_placeholder(body: str) -> bool:
    normalized = body.strip().rstrip(".").strip().lower()
    return normalized in _PLACEHOLDERS


def _section_body(text: str, headings: tuple[str, ...]) -> str:
    """Return the body under the first matching ``## <heading>`` section."""
    for heading in headings:
        pattern = re.compile(rf"(?ms)^##\s+{re.escape(heading)}\s*$\n(?P<body>.*?)(?=^##\s|\Z)")
        match = pattern.search(text)
        if match:
            return match.group("body")
    return ""


def anchors(text: str) -> tuple[str, ...]:
    """Extract the path-like tokens an entry claims exist.

    Only backticked tokens containing a slash qualify. A bare filename is too
    ambiguous to check — it may be written relative to a subdirectory — and a
    token containing whitespace is a command, not a path.
    """
    found: list[str] = []
    for token in _BACKTICK.findall(text):
        candidate = token.strip()
        if not candidate or any(char.isspace() for char in candidate):
            continue
        if "/" not in candidate or "://" in candidate:
            continue
        if candidate.startswith("-"):
            continue
        normalized = candidate.rstrip("/")
        if normalized and normalized not in found:
            found.append(normalized)
    return tuple(found)


def _split_entries(body: str) -> list[str]:
    """Split a section body into entries, folding indented continuations in."""
    entries: list[str] = []
    current: list[str] | None = None
    for raw in body.splitlines():
        match = _ENTRY_START.match(raw)
        if match:
            if current is not None:
                entries.append(" ".join(current))
            current = [match.group("body").strip()]
            continue
        if current is not None:
            stripped = raw.strip()
            if not stripped:
                continue
            if raw[:1].isspace():
                current.append(stripped.lstrip("-*").strip() if stripped.startswith(("-", "*")) else stripped)
            else:
                entries.append(" ".join(current))
                current = None
    if current is not None:
        entries.append(" ".join(current))
    return [entry.strip() for entry in entries if entry.strip()]


def _parse(path: Path, headings: tuple[str, ...]) -> Notes:
    if not path.is_file():
        return Notes(exists=False)
    text = read_text_or_empty(path)
    if not text and path.stat().st_size > 0:
        return Notes(exists=True, readable=False)

    entries: list[Entry] = []
    stale: list[str] = []
    for item in _split_entries(_section_body(text, headings)):
        if _is_placeholder(item):
            continue
        if any(marker in item for marker in LEGACY_HOOK_MARKERS):
            stale.append(item)
            continue
        entries.append(Entry(text=item, anchors=anchors(item)))
    return Notes(
        exists=True,
        readable=True,
        conflicted=bool(_CONFLICT.search(text)),
        entries=entries,
        stale=stale,
        line_count=len(text.splitlines()),
    )


def missing_anchors(root: Path, entry: Entry) -> list[str]:
    """Return the entry's anchors that git has recorded but that are now gone.

    An anchor absent from disk *and* unknown to git is not reported: it is more
    likely a branch name or an untracked scratch path than a broken claim, and a
    false alarm in injected context is a distractor that measurably costs more
    than the missing warning saves.
    """
    gone: list[str] = []
    for anchor in entry.anchors:
        if (root / anchor).exists():
            continue
        if vcs.knows_path(root, anchor):
            gone.append(anchor)
    return gone


def read_memory(root: Path) -> Notes:
    """Parse ``.arbor/memory.md``."""
    return _parse(root / MEMORY_FILE, MEMORY_HEADINGS)


def read_ideas(root: Path) -> Notes:
    """Parse ``.arbor/ideas.md``."""
    return _parse(root / IDEAS_FILE, (IDEAS_HEADING,))
