#!/usr/bin/env python3
"""Render Arbor's Stop-equivalent hookless finalization packet."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


sys.dont_write_bytecode = True

from arbor_project_state import ProjectStateError, resolve_project_root
from run_agents_guide_drift_hook import (
    AgentsGuideDriftHookError,
    parse_doc_paths,
    run_agents_guide_drift_hook,
)
from run_memory_hygiene_hook import parse_optional_git_args, run_memory_hygiene_hook


PLUGIN_ROOT = Path(__file__).resolve().parents[3]
STOP_ADAPTER = PLUGIN_ROOT / "hooks" / "stop-memory-hygiene"
DEFAULT_STOP_MAINTENANCE_TIMEOUT_SECONDS = 20.0


@dataclass(frozen=True)
class StopMaintenanceResult:
    status: str
    source: str
    body: str
    detail: str = ""


class HooklessFinalizationError(ValueError):
    """Raised when the hookless Stop-equivalent path cannot run safely."""


def maintenance_timeout_seconds() -> float:
    raw = os.environ.get("ARBOR_HOOKLESS_FINALIZATION_TIMEOUT_SECONDS")
    if not raw:
        return DEFAULT_STOP_MAINTENANCE_TIMEOUT_SECONDS
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_STOP_MAINTENANCE_TIMEOUT_SECONDS
    return value if value > 0 else DEFAULT_STOP_MAINTENANCE_TIMEOUT_SECONDS


def run_stop_equivalent_maintenance(root: Path, transcript_path: Path | None = None, no_write: bool = False) -> StopMaintenanceResult:
    if not STOP_ADAPTER.is_file():
        raise HooklessFinalizationError(f"Stop adapter not found: {STOP_ADAPTER}")

    payload: dict[str, object] = {"cwd": str(root)}
    if transcript_path is not None:
        payload["transcript_path"] = str(transcript_path)
    if no_write:
        payload["no_write"] = True

    timeout = maintenance_timeout_seconds()
    try:
        proc = subprocess.run(
            [sys.executable, str(STOP_ADAPTER)],
            input=json.dumps(payload),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout if isinstance(exc.stdout, str) else ""
        raise HooklessFinalizationError(
            f"Stop-equivalent maintenance timed out after {timeout:g}s: {output.strip()}"
        ) from exc
    except OSError as exc:
        raise HooklessFinalizationError(f"Stop-equivalent maintenance failed to start: {exc}") from exc

    output = proc.stdout.strip()
    if proc.returncode != 0:
        raise HooklessFinalizationError(
            f"Stop-equivalent maintenance exited {proc.returncode}: {output or 'no output'}"
        )
    return StopMaintenanceResult(
        status="pass",
        source=str(STOP_ADAPTER),
        body=output or "(adapter stayed silent)",
    )


def render_stop_maintenance_result(result: StopMaintenanceResult) -> str:
    lines = [
        "## Stop-Equivalent Maintenance",
        "",
        f"Status: {result.status}",
        f"Source: {result.source}",
    ]
    if result.detail:
        lines.append(f"Detail: {result.detail}")
    lines.extend(["", result.body, ""])
    return "\n".join(lines)


def run_hookless_finalization(
    root: Path,
    diff_args: list[str] | None = None,
    doc_paths: list[Path] | None = None,
    transcript_path: Path | None = None,
    no_write: bool = False,
) -> str:
    resolved = resolve_project_root(root)
    stop_result = run_stop_equivalent_maintenance(resolved, transcript_path, no_write)
    memory_packet = run_memory_hygiene_hook(resolved, diff_args)
    guide_packet = run_agents_guide_drift_hook(resolved, doc_paths)
    lines = [
        "# Hookless Finalization Context",
        "",
        "## Agent Instructions",
        "",
        "- Treat this as Arbor's Stop-equivalent path when runtime hooks are not installed.",
        "- The Stop-Equivalent Maintenance section has already run the same quiet maintenance adapter used by the old Stop hook.",
        "- Use the Memory Hygiene Context to decide whether `.arbor/memory.md` needs a concise resume update.",
        "- Use the AGENTS Guide Drift Context to decide whether durable Project Map drift needs an `AGENTS.md` edit.",
        "- Do not edit memory or AGENTS.md when the packet shows no resume-relevant or durable-guide change.",
        "- Do not register hooks from this packet.",
        "",
        render_stop_maintenance_result(stop_result).rstrip(),
        "",
        memory_packet.rstrip(),
        "",
        guide_packet.rstrip(),
        "",
    ]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root to inspect.")
    parser.add_argument("--diff-args", help="Optional safe git diff arguments for the memory hygiene packet.")
    parser.add_argument(
        "--doc",
        action="append",
        help="Optional project-local doc for AGENTS guide drift context. Repeat to include multiple docs.",
    )
    parser.add_argument("--doc-paths", help=argparse.SUPPRESS)
    parser.add_argument("--transcript-path", type=Path, help="Optional runtime transcript path for Stop-equivalent maintenance.")
    parser.add_argument("--no-write", action="store_true", help="Render context without allowing Stop-equivalent maintenance writes.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        diff_args = parse_optional_git_args(args.diff_args)
        doc_paths = parse_doc_paths(args.doc, args.doc_paths)
        print(
            run_hookless_finalization(
                args.root,
                diff_args,
                doc_paths,
                transcript_path=args.transcript_path,
                no_write=args.no_write,
            ),
            end="",
        )
    except (argparse.ArgumentTypeError, AgentsGuideDriftHookError, HooklessFinalizationError, ProjectStateError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
