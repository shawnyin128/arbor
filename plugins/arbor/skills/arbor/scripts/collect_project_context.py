#!/usr/bin/env python3
"""Collect project startup context in the Arbor order."""

from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


sys.dont_write_bytecode = True

from arbor_project_state import (
    CANONICAL_MEMORY_PATH,
    LEGACY_CODEX_MEMORY_PATH,
    PROJECT_GUIDE_PATH,
)

DEFAULT_GIT_LOG_ARGS = ["--date=iso", "--pretty=format:%H%x09%ad%x09%s"]
DEFAULT_GIT_TIMEOUT_SECONDS = 10.0
HOOK_MEMORY_MARKERS = ("[hook:fallback]", "[hook:resume]")
PLACEHOLDER_MEMORY_PATTERNS = (
    "no active arbor resume context recorded yet",
    "no unresolved state",
    "none.",
)


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


def git_timeout_seconds() -> float:
    raw = os.environ.get("ARBOR_STARTUP_GIT_TIMEOUT_SECONDS")
    if not raw:
        return DEFAULT_GIT_TIMEOUT_SECONDS
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_GIT_TIMEOUT_SECONDS
    if value <= 0:
        return DEFAULT_GIT_TIMEOUT_SECONDS
    return value


def run_git_section(title: str, root: Path, args: list[str]) -> ContextSection:
    timeout = git_timeout_seconds()
    command = "git " + " ".join(args)
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return ContextSection(
            title,
            f"[git timed out after {timeout:g}s]",
            "git-timeout",
            command,
            f"timed out after {timeout:g}s",
        )
    except OSError as exc:
        return ContextSection(
            title,
            f"[git failed to start: {exc}]",
            "git-launch-error",
            command,
            f"failed to start: {exc}",
        )
    output = proc.stdout.rstrip("\n")
    error = proc.stderr.rstrip("\n")
    if proc.returncode == 0:
        return ContextSection(title, output, "ok" if output else "empty", command)
    if output and error:
        body = f"{output}\n\n[git exited {proc.returncode}]\n{error}"
    else:
        body = f"[git exited {proc.returncode}]\n{error or output}"
    return ContextSection(title, body, "git-error", command, f"exit {proc.returncode}")


def git_output(root: Path, args: list[str]) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=git_timeout_seconds(),
        )
    except subprocess.TimeoutExpired:
        return ""
    except OSError:
        return ""
    return proc.stdout.strip() if proc.returncode == 0 else ""


def read_text_if_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8") if path.is_file() else ""
    except (OSError, UnicodeDecodeError):
        return ""


def collect_identity_section(root: Path) -> ContextSection:
    git_root = git_output(root, ["rev-parse", "--show-toplevel"])
    head = git_output(root, ["rev-parse", "--short", "HEAD"])
    branch = git_output(root, ["branch", "--show-current"])
    body = "\n".join(
        [
            f"Project root: {root}",
            f"Git root: {git_root or 'not a git repository'}",
            f"Git branch: {branch or 'unknown'}",
            f"Git HEAD: {head or 'none'}",
        ]
    )
    return ContextSection("0. project identity", body, "ok", str(root))


def read_file(path: Path) -> str:
    return read_file_section("", path).body


def run_git(root: Path, args: list[str]) -> str:
    return run_git_section("", root, args).body


def read_memory_section(title: str, root: Path) -> ContextSection:
    canonical = root / CANONICAL_MEMORY_PATH
    if canonical.exists():
        section = read_file_section(title, canonical)
        return annotate_memory_section(section, root)
    legacy = root / LEGACY_CODEX_MEMORY_PATH
    if legacy.exists():
        section = read_file_section(title, legacy)
        annotated = annotate_memory_section(section, root)
        return ContextSection(
            title=title,
            body=annotated.body,
            status=f"legacy-{annotated.status}",
            source=str(legacy),
            detail=join_details(
                annotated.detail,
                f"canonical {CANONICAL_MEMORY_PATH} is missing; run explicit Arbor initialization to migrate",
            ),
        )
    return read_file_section(title, canonical)


def join_details(*details: str) -> str:
    return "; ".join(detail for detail in details if detail)


def normalize_identity_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def project_labels(root: Path) -> set[str]:
    labels = {normalize_identity_text(root.name)}
    agents = read_text_if_file(root / PROJECT_GUIDE_PATH)
    match = re.search(r"(?ms)^## Project Goal\s*\n(?P<body>.*?)(?=^## |\Z)", agents)
    if match:
        body = normalize_identity_text(match.group("body"))
        if body:
            labels.add(body)
    return {label for label in labels if label}


def memory_project_markers(text: str) -> list[str]:
    markers: list[str] = []
    for match in re.finditer(r"(?mi)^\s*(?:[-*]\s*)?(?:project|repo|repository)\s*:\s*(?P<label>.+?)\s*$", text):
        label = match.group("label").strip()
        if label:
            markers.append(label)
    return markers


def classify_memory(text: str, root: Path) -> tuple[str, str]:
    stripped = text.strip()
    if not stripped:
        return "empty", "memory file is empty"
    lowered = stripped.lower()
    if any(pattern in lowered for pattern in PLACEHOLDER_MEMORY_PATTERNS):
        return "placeholder", "memory says no active resume context"
    if any(marker in stripped for marker in HOOK_MEMORY_MARKERS):
        return "hook-managed", "memory entry was written by an Arbor hook"

    labels = project_labels(root)
    markers = memory_project_markers(stripped)
    for marker in markers:
        normalized = normalize_identity_text(marker)
        if normalized and not any(normalized in label or label in normalized for label in labels):
            return (
                "suspicious-cross-project",
                f"memory declares project `{marker}` which does not match project root `{root.name}`",
            )
    return "explicit", "memory contains explicit in-flight or observation text"


def annotate_memory_section(section: ContextSection, root: Path) -> ContextSection:
    if section.status != "ok":
        classification = "unreadable" if section.status == "read-error" else section.status
        reason = "memory content could not be inspected"
    else:
        classification, reason = classify_memory(section.body, root)
    warning = ""
    if classification == "suspicious-cross-project":
        warning = (
            "WARNING: Treat this memory as suspicious until repaired. Do not summarize "
            "it as current project state or use it to recommend feature/release next actions."
        )
    inspection_lines = [
        "Arbor Memory Inspection:",
        f"- classification: {classification}",
        f"- reason: {reason}",
    ]
    if warning:
        inspection_lines.append(f"- warning: {warning}")
    body = "\n".join(inspection_lines) + "\n\n" + section.body
    status = f"memory-{classification}" if section.status == "ok" else section.status
    return ContextSection(section.title, body, status, section.source, join_details(section.detail, f"memory_state={classification}"))


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
        collect_identity_section(root),
        read_file_section("1. AGENTS.md", root / PROJECT_GUIDE_PATH),
        run_git_section("2. formatted git log", root, ["log", *log_args]),
        read_memory_section("3. .arbor/memory.md", root),
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
