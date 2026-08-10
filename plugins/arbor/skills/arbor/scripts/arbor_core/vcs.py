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


def is_ancestor(root: Path, commit: str) -> bool:
    """Report whether ``commit`` is still reachable from HEAD.

    A stored commit can vanish from the current history through a rebase or a
    force-push. Checking first is what separates "here is what changed" from a
    confidently wrong diff against a commit that is no longer on this branch.
    """
    if not commit:
        return False
    # `--is-ancestor` answers through its exit status and prints nothing, so an
    # empty string means yes and None (nonzero exit) means no.
    return _run(root, ["merge-base", "--is-ancestor", commit, "HEAD"]) == ""


def commits_since(root: Path, commit: str, limit: int) -> list[str]:
    """Return commits added since ``commit``, newest first.

    Two dots, not three. Three dots asks "what is on this branch since it
    forked", which is the right question for a pull request and the wrong one
    here. Callers gate on :func:`is_ancestor` first, and once that holds the two
    forms are provably equivalent, so this is a choice about saying what is meant
    rather than a behavioural difference.
    """
    output = _run(root, ["log", f"-{limit}", "--no-merges", "--pretty=format:%h %s", f"{commit}..HEAD"])
    if not output:
        return []
    return [line for line in output.splitlines() if line.strip()]


def count_commits_since(root: Path, commit: str) -> int:
    """Count commits added since ``commit``."""
    output = _run(root, ["rev-list", "--count", f"{commit}..HEAD"])
    try:
        return int(output.strip()) if output else 0
    except ValueError:
        return 0


def changed_paths_since(root: Path, commit: str, limit: int) -> tuple[list[str], int]:
    """Summarize files changed since ``commit`` as ``(lines, total)``.

    ``--compact-summary`` is used because a created, deleted, or renamed file is
    the highest-signal fact per character: those are the changes that invalidate
    a project map or a note, unlike a line-count delta inside a file that still
    exists.
    """
    output = _run(root, ["diff", "--compact-summary", f"{commit}..HEAD"])
    if not output:
        return [], 0
    rows = [line for line in output.splitlines() if "|" in line]
    total = len(rows)
    lines = []
    for row in rows[:limit]:
        name, _, rest = row.partition("|")
        marker = ""
        if "(new)" in name:
            marker = " (new)"
        elif "(gone)" in name:
            marker = " (gone)"
        cleaned = name.replace("(new)", "").replace("(gone)", "").strip()
        lines.append(f"{cleaned}{marker}")
    return lines, total


def knows_path(root: Path, relative: str) -> bool:
    """Report whether any commit reachable from HEAD touched ``relative``.

    This is what separates a note that names a real file from a note that
    happens to contain a slash. A branch name like ``feature/parser`` or a
    directory that was never committed is unknown to git, so it is not treated
    as a path claim at all; a tracked file that has since been deleted is.
    """
    output = _run(root, ["rev-list", "-1", "HEAD", "--", relative])
    return bool(output and output.strip())
