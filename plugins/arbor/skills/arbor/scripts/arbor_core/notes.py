"""Agent-written notes: ``.arbor/memory.md`` and ``.arbor/ideas.md``.

These files hold what a hook cannot observe — why work stopped, what is still
undecided, and ideas the user parked in passing. Arbor only ever reads them; the
agent writes them with its normal editing tools.

Reading is deliberately tolerant. Entries left behind by the hook-written memory
of earlier Arbor versions are reported as stale rather than treated as live
context, so upgrading a project does not resurface machine-generated noise.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

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

_BULLET = re.compile(r"^\s*[-*]\s+(?P<body>.+?)\s*$")


@dataclass(frozen=True)
class Notes:
    """Parsed contents of one agent-written notes file."""

    exists: bool = False
    readable: bool = True
    entries: list[str] = field(default_factory=list)
    stale: list[str] = field(default_factory=list)
    line_count: int = 0

    @property
    def has_content(self) -> bool:
        return bool(self.entries)


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


def _parse(path: Path, headings: tuple[str, ...]) -> Notes:
    if not path.is_file():
        return Notes(exists=False)
    text = read_text_or_empty(path)
    if not text and path.stat().st_size > 0:
        return Notes(exists=True, readable=False)

    body = _section_body(text, headings)
    entries: list[str] = []
    stale: list[str] = []
    for line in body.splitlines():
        match = _BULLET.match(line)
        if not match:
            continue
        item = match.group("body").strip()
        if _is_placeholder(item):
            continue
        if any(marker in item for marker in LEGACY_HOOK_MARKERS):
            stale.append(item)
            continue
        entries.append(item)
    return Notes(
        exists=True,
        readable=True,
        entries=entries,
        stale=stale,
        line_count=len(text.splitlines()),
    )


def read_memory(root: Path) -> Notes:
    """Parse ``.arbor/memory.md``."""
    return _parse(root / MEMORY_FILE, MEMORY_HEADINGS)


def read_ideas(root: Path) -> Notes:
    """Parse ``.arbor/ideas.md``."""
    return _parse(root / IDEAS_FILE, (IDEAS_HEADING,))
