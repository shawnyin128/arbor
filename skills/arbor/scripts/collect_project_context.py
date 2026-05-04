#!/usr/bin/env python3
"""Collect project startup context in the Arbor order."""

from __future__ import annotations

import argparse
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path


DEFAULT_GIT_LOG_ARGS = ["--date=iso", "--pretty=format:%H%x09%ad%x09%s"]


@dataclass(frozen=True)
class ContextSection:
    title: str
    body: str
    status: str
    source: str
    detail: str = ""


def read_file_section(title: str, path: Path) -> ContextSection:
    if not path.exists():
        return ContextSection(title, f"Missing: {path}", "missing", str(path))
    if path.is_dir():
        return ContextSection(
            title,
            f"Expected a file but found a directory: {path}",
            "path-conflict",
            str(path),
        )
    try:
        body = path.read_text(encoding="utf-8")
    except OSError as exc:
        return ContextSection(title, f"Could not read {path}: {exc}", "read-error", str(path), str(exc))
    except UnicodeDecodeError as exc:
        return ContextSection(title, f"Could not decode {path} as UTF-8: {exc}", "read-error", str(path), str(exc))
    return ContextSection(title, body, "ok" if body else "empty", str(path))


def run_git_section(title: str, root: Path, args: list[str]) -> ContextSection:
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    output = proc.stdout.rstrip("\n")
    error = proc.stderr.rstrip("\n")
    command = "git " + " ".join(args)
    if proc.returncode == 0:
        return ContextSection(title, output, "ok" if output else "empty", command)
    if output and error:
        body = f"{output}\n\n[git exited {proc.returncode}]\n{error}"
    else:
        body = f"[git exited {proc.returncode}]\n{error or output}"
    return ContextSection(title, body, "git-error", command, f"exit {proc.returncode}")


def read_file(path: Path) -> str:
    return read_file_section("", path).body


def run_git(root: Path, args: list[str]) -> str:
    return run_git_section("", root, args).body


def parse_git_log_args(raw: str | list[str] | None) -> list[str]:
    if not raw:
        return list(DEFAULT_GIT_LOG_ARGS)
    if isinstance(raw, list):
        if not raw:
            return list(DEFAULT_GIT_LOG_ARGS)
        raw = " ".join(raw)
    try:
        return shlex.split(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid --git-log-args: {exc}") from exc


def collect_startup_context(root: Path, git_log_args: list[str] | None = None) -> list[ContextSection]:
    root = root.resolve()
    log_args = git_log_args if git_log_args is not None else list(DEFAULT_GIT_LOG_ARGS)
    return [
        read_file_section("1. AGENTS.md", root / "AGENTS.md"),
        run_git_section("2. formatted git log", root, ["log", *log_args]),
        read_file_section("3. .codex/memory.md", root / ".codex" / "memory.md"),
        run_git_section("4. git status", root, ["status", "--short"]),
    ]


def render_context(sections: list[ContextSection]) -> str:
    lines = ["# Project Startup Context", ""]
    for section in sections:
        lines.append(f"## {section.title}")
        lines.append("")
        lines.append(f"Status: {section.status}")
        lines.append(f"Source: {section.source}")
        if section.detail:
            lines.append(f"Detail: {section.detail}")
        lines.append("")
        lines.append(section.body)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root to inspect.")
    parser.add_argument(
        "--git-log-args",
        help=(
            "Optional git log arguments selected by the agent. "
            "When omitted, the script formats the full available log without a count limit."
        ),
    )
    return parser


def parse_args() -> argparse.Namespace:
    return build_parser().parse_args()


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        git_log_args = parse_git_log_args(args.git_log_args)
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))
    sections = collect_startup_context(args.root, git_log_args)
    print(render_context(sections), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
