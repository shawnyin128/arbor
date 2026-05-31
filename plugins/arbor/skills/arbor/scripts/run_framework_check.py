#!/usr/bin/env python3
"""Run deterministic Arbor framework checks and optional safe repairs."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from arbor_project_state import (
    CANONICAL_MEMORY_PATH,
    CLAUDE_GUIDE_PATH,
    INSTALL_RUNTIME_CLAUDE,
    INSTALL_RUNTIME_CODEX,
    PROJECT_GUIDE_PATH,
    ProjectStateError,
    project_path,
    resolve_project_root,
)
from collect_project_context import classify_memory
from diagnose_project_hooks import HookState, diagnose
from init_project_memory import CLAUDE_BRIDGE_CHOICES, init_project_memory
from register_project_hooks import RUNTIME_CHOICES, HookRegistrationError, register_project_hooks, resolve_registration_runtime


MODE_CHECK = "check"
MODE_REPAIR = "repair"
MODE_CHOICES = (MODE_CHECK, MODE_REPAIR)
RENDERED_DETECT_ONLY_MODE = "Mode: detect-only"
RENDERED_REPAIR_MODE = "Mode: repair"
AUTO_ACTION_STATUSES = {
    "created",
    "updated",
    "chmod",
    "migrated_from_legacy",
    "would_create",
    "would_update",
    "would_chmod",
    "would_migrate_from_legacy",
}
ALLOWED_STATUS = {
    "pass",
    "fail",
    "missing",
    "drift",
    "blocked",
    "not_applicable",
    "empty",
    "placeholder",
    "hook-managed",
    "explicit",
    "suspicious-cross-project",
}
ALLOWED_FIXABILITY = {"auto", "needs_confirm", "manual", "none"}


@dataclass(frozen=True)
class FrameworkRow:
    category: str
    check: str
    status: str
    evidence: str
    fixability: str
    repair_action: str

    def __post_init__(self) -> None:
        if self.status not in ALLOWED_STATUS:
            raise ValueError(f"invalid framework status: {self.status}")
        if self.fixability not in ALLOWED_FIXABILITY:
            raise ValueError(f"invalid framework fixability: {self.fixability}")


@dataclass(frozen=True)
class FrameworkCheck:
    root: Path
    mode: str
    sources_checked: list[str]
    rows: list[FrameworkRow]
    repairs_applied: int = 0
    before_rows: list[FrameworkRow] | None = None


def rel(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def one_line(text: str, limit: int = 140) -> str:
    normalized = " ".join(str(text).split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."


def runtime_applies(runtime: str, target: str) -> bool:
    return runtime in (target, "both")


def hook_row(category: str, check: str, state: HookState) -> FrameworkRow:
    mapping = {
        "missing": ("missing", "auto"),
        "intent-only": ("drift", "auto"),
        "executable-incomplete": ("drift", "auto"),
        "executable-untrusted": ("blocked", "manual"),
        "executable-ready": ("pass", "none"),
        "project-Claude-missing": ("missing", "auto"),
        "project-Claude-incomplete": ("drift", "auto"),
        "project-Claude-ready": ("pass", "none"),
        "Claude-plugin-ready": ("pass", "none"),
        "Claude-plugin-unknown": ("not_applicable", "none"),
    }
    if state.status in mapping:
        status, fixability = mapping[state.status]
    elif "invalid" in state.status:
        status, fixability = "fail", "manual"
    elif "missing" in state.status:
        status, fixability = "missing", "manual"
    elif "incomplete" in state.status:
        status, fixability = "drift", "manual"
    else:
        status, fixability = "fail", "manual"
    action = "none" if fixability == "none" else state.next_action
    return FrameworkRow(category, check, status, one_line(state.detail), fixability, one_line(action))


def build_rows(root: Path, plugin_root: Path | None, *, runtime: str, codex_trusted: bool) -> list[FrameworkRow]:
    rows: list[FrameworkRow] = []
    rows.append(
        FrameworkRow(
            "project identity",
            "project root is a directory",
            "pass",
            str(root),
            "none",
            "none",
        )
    )

    agents = project_path(root, PROJECT_GUIDE_PATH)
    if agents.is_file():
        rows.append(FrameworkRow("startup context", "AGENTS.md", "pass", rel(root, agents), "none", "none"))
    elif agents.exists():
        rows.append(
            FrameworkRow(
                "startup context",
                "AGENTS.md",
                "fail",
                f"{rel(root, agents)} is not a file",
                "manual",
                "replace path conflict with a file",
            )
        )
    else:
        rows.append(
            FrameworkRow(
                "startup context",
                "AGENTS.md",
                "missing",
                f"{rel(root, agents)} is absent",
                "auto",
                "run init_project_memory.py",
            )
        )

    memory = project_path(root, CANONICAL_MEMORY_PATH)
    if memory.is_file():
        text = memory.read_text(encoding="utf-8")
        status, reason = classify_memory(text, root)
        rows.append(FrameworkRow("memory", ".arbor/memory.md", status, one_line(reason), "none", "none"))
    elif memory.exists():
        rows.append(
            FrameworkRow(
                "memory",
                ".arbor/memory.md",
                "fail",
                f"{rel(root, memory)} is not a file",
                "manual",
                "replace path conflict with a file",
            )
        )
    else:
        rows.append(
            FrameworkRow(
                "memory",
                ".arbor/memory.md",
                "missing",
                f"{rel(root, memory)} is absent",
                "auto",
                "run init_project_memory.py",
            )
        )

    claude_bridge = project_path(root, CLAUDE_GUIDE_PATH)
    if runtime_applies(runtime, INSTALL_RUNTIME_CLAUDE):
        if claude_bridge.is_file():
            rows.append(FrameworkRow("runtime: Claude bridge", "CLAUDE.md bridge", "pass", rel(root, claude_bridge), "none", "none"))
        elif claude_bridge.exists():
            rows.append(
                FrameworkRow(
                    "runtime: Claude bridge",
                    "CLAUDE.md bridge",
                    "fail",
                    f"{rel(root, claude_bridge)} is not a file",
                    "manual",
                    "replace path conflict with a file",
                )
            )
        else:
            rows.append(
                FrameworkRow(
                    "runtime: Claude bridge",
                    "CLAUDE.md bridge",
                    "missing",
                    f"{rel(root, claude_bridge)} is absent",
                    "auto",
                    "run init_project_memory.py --claude-bridge on",
                )
            )
    else:
        rows.append(
            FrameworkRow(
                "runtime: Claude bridge",
                "CLAUDE.md bridge",
                "not_applicable",
                "runtime selection does not include Claude Code",
                "none",
                "none",
            )
        )

    hook_state = diagnose(root, plugin_root, codex_trusted=codex_trusted)
    codex = hook_row("runtime: Codex project hooks", ".codex hook config and wrappers", hook_state.codex)
    if not runtime_applies(runtime, INSTALL_RUNTIME_CODEX) and codex.status == "missing":
        codex = FrameworkRow(
            codex.category,
            codex.check,
            "not_applicable",
            "runtime selection does not include Codex",
            "none",
            "none",
        )
    rows.append(codex)

    claude_project = hook_row(
        "runtime: Claude project hooks",
        ".claude hook config and wrappers",
        hook_state.claude_project,
    )
    if not runtime_applies(runtime, INSTALL_RUNTIME_CLAUDE) and claude_project.status == "missing":
        claude_project = FrameworkRow(
            claude_project.category,
            claude_project.check,
            "not_applicable",
            "runtime selection does not include Claude Code",
            "none",
            "none",
        )
    rows.append(claude_project)
    rows.append(hook_row("runtime: Claude plugin hooks", "packaged plugin hook manifest", hook_state.claude_plugin))
    return rows


def count_repairs(actions: Iterable[object]) -> int:
    count = 0
    for action in actions:
        if str(getattr(action, "status", "")) in AUTO_ACTION_STATUSES:
            count += 1
    return count


def run_check(
    root: Path,
    plugin_root: Path | None,
    *,
    runtime: str,
    codex_trusted: bool,
    mode: str,
    claude_bridge: str,
) -> FrameworkCheck:
    resolved = resolve_project_root(root)
    selected_runtime = resolve_registration_runtime(runtime)
    sources = [
        str(project_path(resolved, PROJECT_GUIDE_PATH)),
        str(project_path(resolved, CANONICAL_MEMORY_PATH)),
        str(project_path(resolved, CLAUDE_GUIDE_PATH)),
        str(project_path(resolved, Path(".codex") / "hooks.json")),
        str(project_path(resolved, Path(".claude") / "settings.json")),
    ]
    before_rows = build_rows(resolved, plugin_root, runtime=selected_runtime, codex_trusted=codex_trusted)
    repairs_applied = 0
    rows = before_rows
    if mode == MODE_REPAIR:
        init_actions = init_project_memory(resolved, claude_bridge=claude_bridge)
        repairs_applied += count_repairs(init_actions)
        hook_actions = register_project_hooks(resolved, runtime=selected_runtime)
        repairs_applied += count_repairs(hook_actions)
        rows = build_rows(resolved, plugin_root, runtime=selected_runtime, codex_trusted=codex_trusted)
    return FrameworkCheck(
        root=resolved,
        mode=mode,
        sources_checked=sources,
        rows=rows,
        repairs_applied=repairs_applied,
        before_rows=before_rows if mode == MODE_REPAIR else None,
    )


def summary(rows: list[FrameworkRow]) -> str:
    ordered = ("pass", "missing", "drift", "fail", "blocked", "not_applicable")
    counts = {status: 0 for status in ordered}
    for row in rows:
        if row.status in counts:
            counts[row.status] += 1
    return " · ".join(f"{counts[status]} {status}" for status in ordered if counts[status])


def repair_summary(rows: list[FrameworkRow]) -> str:
    ordered = ("auto", "needs_confirm", "manual", "none")
    counts = {fixability: 0 for fixability in ordered}
    for row in rows:
        counts[row.fixability] += 1
    return " · ".join(f"{counts[value]} {value}" for value in ordered if counts[value])


def render_table(rows: list[FrameworkRow]) -> list[str]:
    lines = [
        "| Category | Check | Status | Evidence | Fixability | Repair action |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row.category} | {row.check} | {row.status} | {row.evidence} | {row.fixability} | {row.repair_action} |"
        )
    return lines


def render_report(check: FrameworkCheck) -> str:
    visible_mode = "detect-only" if check.mode == MODE_CHECK else "repair"
    lines = [
        "**Arbor Framework Check**",
        f"Project root: {check.root}",
        f"Mode: {visible_mode}",
        "Sources checked: " + ", ".join(check.sources_checked),
    ]
    if check.mode == MODE_REPAIR:
        assert check.before_rows is not None
        lines.extend(
            [
                f"Repairs applied: {check.repairs_applied}",
                f"Before: {summary(check.before_rows)}",
                f"After: {summary(check.rows)}",
            ]
        )
    lines.append("")
    lines.extend(render_table(check.rows))
    lines.append("")
    lines.append(f"Summary: {summary(check.rows)}")
    lines.append(f"Repair: {repair_summary(check.rows)}")
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root to inspect.")
    parser.add_argument("--plugin-root", type=Path, default=None, help="Arbor plugin root for packaged hook checks.")
    parser.add_argument("--mode", choices=MODE_CHOICES, default=MODE_CHECK, help="check is read-only; repair applies safe Arbor framework repairs.")
    parser.add_argument("--runtime", choices=RUNTIME_CHOICES, default="auto", help="Runtime hook surface to check or repair.")
    parser.add_argument("--codex-trusted", action="store_true", help="Assert Codex project hooks are already trusted in /hooks.")
    parser.add_argument("--claude-bridge", choices=CLAUDE_BRIDGE_CHOICES, default="auto", help="Claude bridge mode for repair.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        report = run_check(
            args.root,
            args.plugin_root,
            runtime=args.runtime,
            codex_trusted=args.codex_trusted,
            mode=args.mode,
            claude_bridge=args.claude_bridge,
        )
    except (ProjectStateError, HookRegistrationError, OSError, ValueError) as exc:
        print(f"arbor framework check failed: {exc}", file=sys.stderr)
        return 1
    print(render_report(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
