"""Bounded git probes.

Every probe is timeout-bounded and failure-tolerant: a hook must never hang or
crash a session because git is slow, missing, or pointed at a non-repository.
Failures degrade to "unknown", which callers render as an omitted section.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .paths import env_float

DEFAULT_TIMEOUT_SECONDS = 5.0
_TIMEOUT_ENV = "ARBOR_GIT_TIMEOUT_SECONDS"

# `git status --short --branch` header, e.g.
#   ## feature...origin/feature [ahead 2, behind 1]
#   ## HEAD (no branch)
_BRANCH_HEADER = re.compile(
    r"^## (?P<branch>[^.\s]+(?:\.[^.\s]+)*?)(?:\.\.\.(?P<upstream>\S+))?(?: \[(?P<track>[^\]]+)\])?$"
)


@dataclass(frozen=True)
class Status:
    """Working-tree position and dirty paths from a single git call."""

    is_repo: bool = False
    branch: str = ""
    upstream: str = ""
    ahead: int = 0
    behind: int = 0
    entries: list[tuple[str, str]] = field(default_factory=list)

    @property
    def dirty_count(self) -> int:
        return len(self.entries)


def _run(root: Path, args: list[str]) -> str | None:
    """Run a git command under ``root``; return stdout, or ``None`` on failure."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=env_float(_TIMEOUT_ENV, DEFAULT_TIMEOUT_SECONDS),
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    return proc.stdout if proc.returncode == 0 else None


def _parse_track(track: str) -> tuple[int, int]:
    ahead = behind = 0
    for match in re.finditer(r"(ahead|behind) (\d+)", track):
        if match.group(1) == "ahead":
            ahead = int(match.group(2))
        else:
            behind = int(match.group(2))
    return ahead, behind


def status(root: Path) -> Status:
    """Collect branch, upstream divergence, and dirty entries in one git call."""
    output = _run(root, ["status", "--short", "--branch", "--untracked-files=all"])
    if output is None:
        return Status()

    branch = upstream = ""
    ahead = behind = 0
    entries: list[tuple[str, str]] = []
    for line in output.splitlines():
        if line.startswith("## "):
            match = _BRANCH_HEADER.match(line)
            if match:
                branch = match.group("branch") or ""
                upstream = match.group("upstream") or ""
                ahead, behind = _parse_track(match.group("track") or "")
            else:
                branch = line[3:].strip()
            continue
        if len(line) > 3:
            entries.append((line[:2], line[3:].strip()))
    return Status(
        is_repo=True,
        branch=branch,
        upstream=upstream,
        ahead=ahead,
        behind=behind,
        entries=entries,
    )


def recent_commits(root: Path, limit: int) -> list[str]:
    """Return up to ``limit`` recent commits as ``"<short-hash> <date> <subject>"``."""
    output = _run(root, ["log", f"-{limit}", "--no-merges", "--date=short", "--pretty=format:%h %ad %s"])
    if not output:
        return []
    return [line for line in output.splitlines() if line.strip()]


def head(root: Path) -> str:
    """Return the short HEAD hash, or ``""`` when unavailable."""
    output = _run(root, ["rev-parse", "--short", "HEAD"])
    return output.strip() if output else ""
