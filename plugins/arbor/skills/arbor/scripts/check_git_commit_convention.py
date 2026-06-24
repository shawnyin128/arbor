#!/usr/bin/env python3
"""Check Git commit messages against Conventional Commits 1.0.0."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


sys.dont_write_bytecode = True


DEFAULT_GIT_TIMEOUT_SECONDS = 10.0
CONVENTIONAL_SUBJECT_RE = re.compile(
    r"^(?P<type>[A-Za-z][A-Za-z0-9-]*)(?:\((?P<scope>[^()\r\n:]+)\))?(?P<breaking>!)?: (?P<description>\S.*)$"
)
BREAKING_FOOTER_RE = re.compile(r"^BREAKING(?: |-)?CHANGE: \S.*$")
ANY_BREAKING_FOOTER_RE = re.compile(r"^breaking(?: |-)?change:", re.IGNORECASE)


@dataclass(frozen=True)
class CommitMessageCheck:
    ref: str
    subject: str
    failures: tuple[str, ...]


@dataclass(frozen=True)
class CommitConventionReport:
    status: str
    source: str
    checked: int
    checks: tuple[CommitMessageCheck, ...]
    detail: str = ""


def git_timeout_seconds() -> float:
    raw = os.environ.get("ARBOR_GIT_CONVENTION_TIMEOUT_SECONDS")
    if not raw:
        return DEFAULT_GIT_TIMEOUT_SECONDS
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_GIT_TIMEOUT_SECONDS
    return value if value > 0 else DEFAULT_GIT_TIMEOUT_SECONDS


def conventional_failures(message: str) -> tuple[str, ...]:
    normalized = message.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    if not normalized.strip():
        return ("message is empty",)

    lines = normalized.split("\n")
    subject = lines[0]
    failures: list[str] = []
    if not CONVENTIONAL_SUBJECT_RE.fullmatch(subject):
        failures.append("subject must match <type>[optional scope][!]: <description>")

    for line in lines[1:]:
        if ANY_BREAKING_FOOTER_RE.match(line) and not BREAKING_FOOTER_RE.fullmatch(line):
            failures.append("BREAKING CHANGE footer must be uppercase and include a description")
            break

    return tuple(failures)


def check_message(message: str, ref: str = "message") -> CommitMessageCheck:
    subject = message.replace("\r\n", "\n").replace("\r", "\n").split("\n", 1)[0].strip()
    return CommitMessageCheck(ref=ref, subject=subject or "(empty)", failures=conventional_failures(message))


def run_git(root: Path, args: list[str]) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=git_timeout_seconds(),
        )
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout if isinstance(exc.stdout, str) else ""
        return 124, output, f"git timed out after {git_timeout_seconds():g}s"
    except OSError as exc:
        return 127, "", f"git failed to start: {exc}"
    return proc.returncode, proc.stdout, proc.stderr


def parse_git_records(raw: str) -> list[tuple[str, str, str]]:
    records: list[tuple[str, str, str]] = []
    for item in raw.split("\x1e"):
        item = item.strip("\n")
        if not item:
            continue
        parts = item.split("\x1f", 2)
        if len(parts) != 3:
            continue
        commit_hash, subject, body = parts
        records.append((commit_hash.strip(), subject.strip(), body.strip()))
    return records


def check_recent_commits(root: Path, last: int = 1, revision_range: str | None = None) -> CommitConventionReport:
    if last <= 0 and revision_range is None:
        return CommitConventionReport("skipped", "git log", 0, (), "no commits requested")

    args = ["log", "--no-merges", "--format=%H%x1f%s%x1f%B%x1e"]
    if revision_range:
        args.append(revision_range)
    else:
        args.append(f"--max-count={last}")
    code, stdout, stderr = run_git(root, args)
    source = "git " + " ".join(args)
    if code != 0:
        detail = (stderr or stdout or f"git exited {code}").strip()
        return CommitConventionReport("skipped", source, 0, (), detail)

    checks = tuple(
        check_message(body or subject, ref=commit_hash[:12])
        for commit_hash, subject, body in parse_git_records(stdout)
    )
    if not checks:
        return CommitConventionReport("skipped", source, 0, (), "no non-merge commits found")
    status = "fail" if any(check.failures for check in checks) else "pass"
    return CommitConventionReport(status, source, len(checks), checks)


def git_has_uncommitted_changes(root: Path) -> bool | None:
    code, stdout, _stderr = run_git(root, ["status", "--porcelain=v1", "--untracked-files=all"])
    if code != 0:
        return None
    return bool(stdout.strip())


def render_report(report: CommitConventionReport) -> str:
    lines = [
        "# Git Commit Convention Check",
        "",
        f"Status: {report.status}",
        f"Source: {report.source}",
        f"Checked: {report.checked}",
    ]
    if report.detail:
        lines.append(f"Detail: {report.detail}")
    lines.append("")
    if report.status == "pass":
        lines.append("- All checked non-merge commits follow Conventional Commits 1.0.0.")
    elif report.status == "skipped":
        lines.append("- No commit messages were checked.")
    else:
        lines.append("- Non-conventional commit messages:")
        for check in report.checks:
            if not check.failures:
                continue
            lines.append(f"  - {check.ref}: {check.subject}")
            for failure in check.failures:
                lines.append(f"    - {failure}")
    return "\n".join(lines).rstrip() + "\n"


def render_startup_context(report: CommitConventionReport) -> str:
    lines = [render_report(report).rstrip()]
    if report.status == "fail":
        lines.extend(
            [
                "",
                "Agent note: recent Git history is less useful for Arbor recovery until the latest commit subject is conventional.",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def render_finalization_context(root: Path) -> str:
    report = check_recent_commits(root, last=1)
    dirty = git_has_uncommitted_changes(root)
    status = "fail" if report.status == "fail" else "action-needed" if dirty else report.status
    lines = [
        "## Git Commit Convention Context",
        "",
        f"Status: {status}",
        f"Source: {report.source}",
    ]
    if report.detail:
        lines.append(f"Detail: {report.detail}")
    lines.extend(
        [
            "",
            "- Arbor uses Conventional Commits 1.0.0 so startup git history remains useful recovery context.",
            "- Before creating a commit, draft the subject and run `check_git_commit_convention.py --message \"<subject>\"`.",
            "- Do not create native git hooks from this context; this is a hookless agent gate.",
        ]
    )
    if dirty:
        lines.append("- Uncommitted changes are present; run the message gate before committing this work.")
    elif dirty is None:
        lines.append("- Git status could not be inspected; run the message gate before any commit.")
    else:
        lines.append("- No uncommitted changes detected.")
    lines.extend(["", render_report(report).rstrip(), ""])
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--message", help="Commit message text to validate before creating a commit.")
    mode.add_argument("--range", dest="revision_range", help="Git revision range to validate, for example HEAD~3..HEAD.")
    mode.add_argument("--last", type=int, help="Number of recent non-merge commits to validate. Defaults to 1.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Git repository root to inspect.")
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    parser = build_parser()
    args = parser.parse_args()

    if args.message is not None:
        check = check_message(args.message)
        report = CommitConventionReport(
            "fail" if check.failures else "pass",
            "message",
            1,
            (check,),
        )
    else:
        report = check_recent_commits(
            args.root.resolve(),
            last=args.last if args.last is not None else 1,
            revision_range=args.revision_range,
        )

    print(render_report(report), end="")
    return 1 if report.status == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
