#!/usr/bin/env python3
"""Run Arbor's deterministic v2 quality hard gate."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

sys.dont_write_bytecode = True


SCRIPT_ROOT = Path(__file__).resolve().parent
PLUGIN_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = PLUGIN_ROOT.parents[1]
DEFAULT_CHECK_TIMEOUT_SECONDS = 120.0


@dataclass(frozen=True)
class GateCheck:
    name: str
    command: list[str] | None
    allow_framework_trust_block: bool = False
    skip_note: str = ""


@dataclass(frozen=True)
class GateOutcome:
    ok: bool
    status: str
    note: str
    output: str


def framework_result(output: str) -> str | None:
    match = re.search(r"(?im)^Result:\s*([a-z_]+)\s*$", output)
    return match.group(1).lower() if match else None


def framework_table_rows(output: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    headers: list[str] | None = None
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells:
            continue
        if cells[0] == "Surface":
            headers = cells
            continue
        if cells[0] == "---" or headers is None or len(cells) != len(headers):
            continue
        rows.append(dict(zip(headers, cells)))
    return rows


def framework_block_is_only_codex_trust(output: str) -> bool:
    if framework_result(output) != "blocked":
        return False

    non_pass_required_rows = [
        row
        for row in framework_table_rows(output)
        if row.get("Required") == "yes" and row.get("Status") != "pass"
    ]
    if len(non_pass_required_rows) != 1:
        return False

    row = non_pass_required_rows[0]
    return (
        row.get("Surface") == ".codex/hooks.json + .codex/hooks/"
        and row.get("Status") == "blocked"
        and "Codex /hooks trust cannot be proven from files" in row.get("Evidence", "")
    )


def subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def check_timeout_seconds() -> float:
    raw = os.environ.get("ARBOR_QUALITY_GATE_TIMEOUT_SECONDS")
    if not raw:
        return DEFAULT_CHECK_TIMEOUT_SECONDS
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_CHECK_TIMEOUT_SECONDS
    if value <= 0:
        return DEFAULT_CHECK_TIMEOUT_SECONDS
    return value


def run_check(check: GateCheck) -> GateOutcome:
    if check.command is None:
        return GateOutcome(True, "skipped", check.skip_note, "")

    timeout = check_timeout_seconds()
    try:
        proc = subprocess.run(
            check.command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=subprocess_env(),
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout if isinstance(exc.stdout, str) else ""
        detail = output.strip()
        suffix = f"\n{detail}" if detail else ""
        return GateOutcome(False, "fail", "", f"command timed out after {timeout:g}s{suffix}")
    except OSError as exc:
        return GateOutcome(False, "fail", "", f"command failed to start: {exc}")
    output = proc.stdout.strip()
    if check.allow_framework_trust_block:
        result = framework_result(output)
        if result == "pass":
            if proc.returncode == 0:
                return GateOutcome(True, "pass", "", output)
            return GateOutcome(False, "fail", "", output)
        if framework_block_is_only_codex_trust(output):
            return GateOutcome(True, "accepted", "Codex /hooks trust not proven from files", output)
        return GateOutcome(False, "fail", "", output)
    if proc.returncode == 0:
        return GateOutcome(True, "pass", "", output)
    return GateOutcome(False, "fail", "", output)


def gate_checks(root: Path, plugin_root: Path) -> list[GateCheck]:
    python = sys.executable
    script_root = plugin_root / "skills" / "arbor" / "scripts"
    checks = [
        GateCheck("python syntax", [python, str(script_root / "check_python_syntax.py")]),
        GateCheck("source hygiene", [python, str(script_root / "check_source_hygiene.py")]),
        GateCheck("diff hygiene", ["git", "-C", str(root), "diff", "--check"]),
        GateCheck("context boundary", [python, str(script_root / "check_context_boundary.py")]),
        GateCheck("project wrapper smoke", [python, str(script_root / "check_project_wrapper_smoke.py")]),
        GateCheck("hookless repair smoke", [python, str(script_root / "check_hookless_repair_smoke.py")]),
        GateCheck("plugin adapters", [python, str(script_root / "check_plugin_adapters.py")]),
        GateCheck("skill packages", [python, str(script_root / "check_skill_packages.py")]),
    ]
    if (root / "AGENTS.md").is_file():
        checks.append(
            GateCheck("AGENTS guide quality", [python, str(script_root / "check_agents_guide_quality.py"), "--root", str(root)])
        )
    else:
        checks.append(
            GateCheck(
                "AGENTS guide quality",
                None,
                skip_note="AGENTS.md is project-local runtime state and is ignored in published checkouts",
            )
        )
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="Project root to validate.")
    parser.add_argument("--plugin-root", type=Path, default=PLUGIN_ROOT, help="Arbor plugin root.")
    args = parser.parse_args()

    failures: list[str] = []
    accepted_notes: list[str] = []
    print("Arbor quality hard gate")
    for check in gate_checks(args.root.resolve(), args.plugin_root.resolve()):
        outcome = run_check(check)
        note = f" ({outcome.note})" if outcome.note else ""
        print(f"- {check.name}: {outcome.status}{note}")
        if outcome.status == "accepted" and outcome.note:
            accepted_notes.append(outcome.note)
        if not outcome.ok:
            failures.append(f"{check.name} failed:\n{outcome.output}")

    if failures:
        print("")
        print("quality gate failed:")
        for failure in failures:
            print(failure)
        return 1
    print("")
    if accepted_notes:
        print("quality gate passed with accepted caveats")
        for note in accepted_notes:
            print(f"- {note}")
    else:
        print("quality gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
