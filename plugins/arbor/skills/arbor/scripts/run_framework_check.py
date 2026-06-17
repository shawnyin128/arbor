#!/usr/bin/env python3
"""Run deterministic Arbor framework checks and optional safe repairs."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


sys.dont_write_bytecode = True

from arbor_project_state import (
    CANONICAL_MEMORY_PATH,
    CLAUDE_GUIDE_PATH,
    INSTALL_RUNTIME_CLAUDE,
    INSTALL_RUNTIME_CODEX,
    PROJECT_GUIDE_PATH,
    ProjectStateError,
    has_hookless_runtime_contract,
    project_path,
    resolve_project_root,
)
from diagnose_project_hooks import HookState, diagnose
from init_project_memory import CLAUDE_BRIDGE_AUTO, CLAUDE_BRIDGE_CHOICES, CLAUDE_BRIDGE_ON, init_project_memory
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
}
RESULT_PASS = "pass"
RESULT_NEEDS_REPAIR = "needs_repair"
RESULT_BLOCKED = "blocked"


@dataclass(frozen=True)
class FrameworkRow:
    surface: str
    required: str
    status: str
    evidence: str
    repair: str

    def __post_init__(self) -> None:
        if self.status not in ALLOWED_STATUS:
            raise ValueError(f"invalid framework status: {self.status}")
        if self.required not in {"yes", "no"}:
            raise ValueError(f"invalid framework required value: {self.required}")


@dataclass(frozen=True)
class FrameworkCheck:
    root: Path
    mode: str
    runtime: str
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


def hook_row(surface: str, state: HookState, *, required: bool) -> FrameworkRow:
    mapping = {
        "missing": "missing",
        "intent-only": "drift",
        "executable-incomplete": "drift",
        "executable-untrusted": "blocked",
        "executable-ready": "pass",
        "project-Claude-missing": "missing",
        "project-Claude-incomplete": "drift",
        "project-Claude-ready": "pass",
        "shared-adapters-ready": "pass",
        "shared-adapters-unknown": "not_applicable",
        "shared-adapters-drift": "drift",
        "shared-adapters-incomplete": "drift",
        "shared-adapters-probe-failed": "drift",
    }
    if state.status in mapping:
        status = mapping[state.status]
    elif "invalid" in state.status:
        status = "fail"
    elif "missing" in state.status:
        status = "missing"
    elif "incomplete" in state.status:
        status = "drift"
    else:
        status = "fail"
    if not required and status == "missing":
        status = "not_applicable"
    repair = "none" if status in {"pass", "not_applicable"} else state.next_action
    return FrameworkRow(surface, "yes" if required else "no", status, one_line(state.detail), one_line(repair))


def build_rows(
    root: Path,
    plugin_root: Path | None,
    *,
    runtime: str,
    codex_trusted: bool,
    include_hooks: bool,
) -> list[FrameworkRow]:
    rows: list[FrameworkRow] = []

    agents = project_path(root, PROJECT_GUIDE_PATH)
    if agents.is_file():
        try:
            agents_text = agents.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            rows.append(
                FrameworkRow(
                    "AGENTS.md",
                    "yes",
                    "fail",
                    f"{rel(root, agents)} cannot be read as UTF-8: {one_line(str(exc))}",
                    "repair project guide encoding before running Arbor",
                )
            )
        else:
            if has_hookless_runtime_contract(agents_text):
                rows.append(FrameworkRow("AGENTS.md", "yes", "pass", rel(root, agents), "none"))
            else:
                rows.append(
                    FrameworkRow(
                        "AGENTS.md",
                        "yes",
                        "drift",
                        f"{rel(root, agents)} lacks Arbor hookless runtime contract",
                        "run init_project_memory.py to append hookless runtime contract",
                    )
                )
    elif agents.exists():
        rows.append(
            FrameworkRow(
                "AGENTS.md",
                "yes",
                "fail",
                f"{rel(root, agents)} is not a file",
                "replace path conflict with a file",
            )
        )
    else:
        rows.append(
            FrameworkRow(
                "AGENTS.md",
                "yes",
                "missing",
                f"{rel(root, agents)} is absent",
                "run init_project_memory.py",
            )
        )

    memory = project_path(root, CANONICAL_MEMORY_PATH)
    if memory.is_file():
        rows.append(FrameworkRow(".arbor/memory.md", "yes", "pass", rel(root, memory), "none"))
    elif memory.exists():
        rows.append(
            FrameworkRow(
                ".arbor/memory.md",
                "yes",
                "fail",
                f"{rel(root, memory)} is not a file",
                "replace path conflict with a file",
            )
        )
    else:
        rows.append(
            FrameworkRow(
                ".arbor/memory.md",
                "yes",
                "missing",
                f"{rel(root, memory)} is absent",
                "run init_project_memory.py",
            )
        )

    claude_bridge = project_path(root, CLAUDE_GUIDE_PATH)
    if runtime_applies(runtime, INSTALL_RUNTIME_CLAUDE):
        if claude_bridge.is_file():
            rows.append(FrameworkRow("CLAUDE.md", "yes", "pass", rel(root, claude_bridge), "none"))
        elif claude_bridge.exists():
            rows.append(
                FrameworkRow(
                    "CLAUDE.md",
                    "yes",
                    "fail",
                    f"{rel(root, claude_bridge)} is not a file",
                    "replace path conflict with a file",
                )
            )
        else:
            rows.append(
                FrameworkRow(
                    "CLAUDE.md",
                    "yes",
                    "missing",
                    f"{rel(root, claude_bridge)} is absent",
                    "run init_project_memory.py --claude-bridge on",
                )
            )
    else:
        rows.append(
            FrameworkRow(
                "CLAUDE.md",
                "no",
                "not_applicable",
                "runtime selection does not include Claude Code",
                "none",
            )
        )

    if include_hooks:
        hook_state = diagnose(root, plugin_root, codex_trusted=codex_trusted)
        rows.append(
            hook_row(
                ".codex/hooks.json + .codex/hooks/",
                hook_state.codex,
                required=runtime_applies(runtime, INSTALL_RUNTIME_CODEX),
            )
        )
        rows.append(
            hook_row(
                ".claude/settings.json + .claude/hooks/",
                hook_state.claude_project,
                required=runtime_applies(runtime, INSTALL_RUNTIME_CLAUDE),
            )
        )
        rows.append(hook_row("shared hook adapters", hook_state.shared_adapters, required=True))
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
    include_hooks: bool,
) -> FrameworkCheck:
    resolved = resolve_project_root(root)
    selected_runtime = resolve_registration_runtime(runtime)
    sources = [
        str(project_path(resolved, PROJECT_GUIDE_PATH)),
        str(project_path(resolved, CANONICAL_MEMORY_PATH)),
        str(project_path(resolved, CLAUDE_GUIDE_PATH)),
    ]
    if include_hooks:
        sources.extend(
            [
                str(project_path(resolved, Path(".codex") / "hooks.json")),
                str(project_path(resolved, Path(".claude") / "settings.json")),
            ]
        )
    before_rows = build_rows(
        resolved,
        plugin_root,
        runtime=selected_runtime,
        codex_trusted=codex_trusted,
        include_hooks=include_hooks,
    )
    repairs_applied = 0
    rows = before_rows
    if mode == MODE_REPAIR:
        effective_bridge = claude_bridge
        if effective_bridge == CLAUDE_BRIDGE_AUTO and runtime_applies(selected_runtime, INSTALL_RUNTIME_CLAUDE):
            effective_bridge = CLAUDE_BRIDGE_ON
        init_actions = init_project_memory(resolved, claude_bridge=effective_bridge)
        repairs_applied += count_repairs(init_actions)
        if include_hooks:
            hook_actions = register_project_hooks(resolved, runtime=selected_runtime)
            repairs_applied += count_repairs(hook_actions)
        rows = build_rows(
            resolved,
            plugin_root,
            runtime=selected_runtime,
            codex_trusted=codex_trusted,
            include_hooks=include_hooks,
        )
    return FrameworkCheck(
        root=resolved,
        mode=mode,
        runtime=selected_runtime,
        sources_checked=sources,
        rows=rows,
        repairs_applied=repairs_applied,
        before_rows=before_rows if mode == MODE_REPAIR else None,
    )


def result_status(rows: list[FrameworkRow]) -> str:
    required_rows = [row for row in rows if row.required == "yes"]
    if any(row.status in {"fail", "blocked"} for row in required_rows):
        return RESULT_BLOCKED
    if any(row.status in {"missing", "drift"} for row in required_rows):
        return RESULT_NEEDS_REPAIR
    return RESULT_PASS


def render_table(rows: list[FrameworkRow]) -> list[str]:
    lines = [
        "| Surface | Required | Status | Evidence | Repair |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(f"| {row.surface} | {row.required} | {row.status} | {row.evidence} | {row.repair} |")
    return lines


def render_report(check: FrameworkCheck) -> str:
    visible_mode = "detect-only" if check.mode == MODE_CHECK else "repair"
    lines = [
        "**Arbor Framework Check**",
        f"Project root: {check.root}",
        f"Mode: {visible_mode}",
        "Runtime: " + check.runtime,
    ]
    if check.mode == MODE_REPAIR:
        assert check.before_rows is not None
        lines.extend(
            [
                f"Repairs applied: {check.repairs_applied}",
                f"Before: {result_status(check.before_rows)}",
                f"After: {result_status(check.rows)}",
            ]
        )
    lines.append("")
    lines.extend(render_table(check.rows))
    lines.append("")
    lines.append(f"Result: {result_status(check.rows)}")
    return "\n".join(lines) + "\n"


def selected_runtime_label(rows: list[FrameworkRow]) -> str:
    codex_required = any(row.surface.startswith(".codex/") and row.required == "yes" for row in rows)
    claude_required = any(row.surface.startswith(".claude/") and row.required == "yes" for row in rows)
    if codex_required and claude_required:
        return "both"
    if claude_required:
        return "claude"
    return "codex"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root to inspect.")
    parser.add_argument("--plugin-root", type=Path, default=None, help="Arbor plugin root for shared hook adapter checks.")
    parser.add_argument("--mode", choices=MODE_CHOICES, default=MODE_CHECK, help="check is read-only; repair applies safe Arbor framework repairs.")
    parser.add_argument("--runtime", choices=RUNTIME_CHOICES, default="auto", help="Runtime hook surface to check or repair.")
    parser.add_argument("--codex-trusted", action="store_true", help="Assert Codex project hooks are already trusted in /hooks.")
    parser.add_argument("--claude-bridge", choices=CLAUDE_BRIDGE_CHOICES, default="auto", help="Claude bridge mode for repair.")
    parser.add_argument("--include-hooks", action="store_true", help="Include legacy project hook diagnosis and repair surfaces.")
    parser.add_argument("--strict", action="store_true", help="Exit nonzero unless the final Result is pass.")
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
            include_hooks=args.include_hooks,
        )
    except (ProjectStateError, HookRegistrationError, OSError, ValueError) as exc:
        print(f"arbor framework check failed: {exc}", file=sys.stderr)
        return 1
    print(render_report(report), end="")
    if args.strict and result_status(report.rows) != RESULT_PASS:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
