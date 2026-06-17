#!/usr/bin/env python3
"""Validate Arbor's hookless trigger contract and stop-equivalent packets."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


sys.dont_write_bytecode = True

SCRIPT_ROOT = Path(__file__).resolve().parent
PLUGIN_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TIMEOUT_SECONDS = 30.0
TIMEOUT_ENV_VAR = "ARBOR_HOOKLESS_TRIGGER_CONTRACT_TIMEOUT_SECONDS"
START_MARKER = "<!-- ARBOR HOOKLESS RUNTIME CONTRACT START -->"
END_MARKER = "<!-- ARBOR HOOKLESS RUNTIME CONTRACT END -->"


def timeout_seconds() -> float:
    raw = os.environ.get(TIMEOUT_ENV_VAR)
    if not raw:
        return DEFAULT_TIMEOUT_SECONDS
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS
    return value if value > 0 else DEFAULT_TIMEOUT_SECONDS


def subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def run_command(args: list[str], cwd: Path | None = None) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            args,
            cwd=str(cwd) if cwd is not None else None,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=subprocess_env(),
            check=False,
            timeout=timeout_seconds(),
        )
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout if isinstance(exc.stdout, str) else ""
        return 124, f"command timed out after {timeout_seconds():g}s: {' '.join(args)}\n{output.strip()}"
    except OSError as exc:
        return 127, f"command failed to start: {' '.join(args)}: {exc}"
    return proc.returncode, proc.stdout


def record(failures: list[str], condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def assert_ordered(output: str, terms: list[str], failures: list[str], label: str) -> None:
    cursor = -1
    for term in terms:
        index = output.find(term, cursor + 1)
        if index == -1:
            failures.append(f"{label} missing ordered term: {term!r}")
            return
        cursor = index


def run_init(project: Path) -> tuple[int, str]:
    return run_command(
        [
            sys.executable,
            str(SCRIPT_ROOT / "init_project_memory.py"),
            "--root",
            str(project),
            "--claude-bridge",
            "off",
        ]
    )


def run_framework_check(project: Path) -> tuple[int, str]:
    return run_command(
        [
            sys.executable,
            str(SCRIPT_ROOT / "run_framework_check.py"),
            "--root",
            str(project),
            "--plugin-root",
            str(PLUGIN_ROOT),
            "--strict",
        ]
    )


def run_agents_quality(project: Path) -> tuple[int, str]:
    return run_command(
        [
            sys.executable,
            str(SCRIPT_ROOT / "check_agents_guide_quality.py"),
            "--root",
            str(project),
        ]
    )


def check_init_appends_hookless_contract(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="arbor-hookless-contract-init-") as tmp:
        project = Path(tmp)
        original = "# Existing Agent Guide\n\nKeep existing project rules.\n"
        (project / "AGENTS.md").write_text(original, encoding="utf-8")

        code, output = run_init(project)
        record(failures, code == 0, f"init_project_memory.py failed: {output.strip()}")
        agents = (project / "AGENTS.md").read_text(encoding="utf-8")
        record(failures, agents.startswith(original), "initialization must preserve existing AGENTS.md content")
        record(failures, START_MARKER in agents and END_MARKER in agents, "initialization must append the Arbor hookless runtime contract")
        record(failures, "run_session_startup_hook.py" in agents, "hookless contract must name the SessionStart-equivalent startup packet")
        record(failures, "run_hookless_finalization.py" in agents, "hookless contract must name the Stop-equivalent finalization packet")
        record(failures, "skills/arbor/scripts" in agents, "hookless contract must identify installed skill script location")
        record(
            failures,
            "<project-root>/scripts" in agents,
            "hookless contract must warn agents not to search project-local scripts for Arbor package helpers",
        )
        record(failures, "register_project_hooks.py" not in agents, "hookless contract must not instruct default hook registration")
        record(failures, not (project / ".codex").exists(), "hookless initialization must not create .codex")
        record(failures, not (project / ".claude").exists(), "hookless initialization must not create .claude")

        code, output = run_init(project)
        record(failures, code == 0, f"second init_project_memory.py failed: {output.strip()}")
        agents = (project / "AGENTS.md").read_text(encoding="utf-8")
        record(failures, agents.count(START_MARKER) == 1, "hookless contract must be idempotent")


def check_contract_does_not_pollute_project_map(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="arbor-hookless-contract-map-") as tmp:
        project = Path(tmp)
        (project / "README.md").write_text("# Existing Project\n", encoding="utf-8")
        (project / "AGENTS.md").write_text(
            "\n".join(
                [
                    "# Agent Guide",
                    "",
                    "## Project Goal",
                    "",
                    "Existing project.",
                    "",
                    "## Project Constraints",
                    "",
                    "- Keep existing project rules.",
                    "",
                    "## Project Map",
                    "",
                    "- `README.md`: overview.",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        code, output = run_init(project)
        record(failures, code == 0, f"init_project_memory.py failed for valid AGENTS.md: {output.strip()}")
        agents = (project / "AGENTS.md").read_text(encoding="utf-8")
        constraints_index = agents.find("## Project Constraints")
        map_index = agents.find("## Project Map")
        contract_index = agents.find(START_MARKER)
        record(
            failures,
            constraints_index != -1 and contract_index != -1 and constraints_index < contract_index < map_index,
            "hookless runtime contract must live under Project Constraints when that section exists",
        )

        quality_code, quality_output = run_agents_quality(project)
        record(
            failures,
            quality_code == 0,
            "hookless runtime contract must not pollute Project Map quality checks: " + quality_output.strip(),
        )


def check_framework_detects_missing_contract(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="arbor-hookless-contract-check-") as tmp:
        project = Path(tmp)
        (project / "AGENTS.md").write_text("# Existing Agent Guide\n", encoding="utf-8")
        (project / ".arbor").mkdir()
        (project / ".arbor" / "memory.md").write_text("# Session Memory\n\n## In-flight\n\n- None.\n", encoding="utf-8")

        code, output = run_framework_check(project)
        record(failures, code != 0, "strict framework check must fail when AGENTS.md lacks Arbor hookless contract")
        record(failures, "| AGENTS.md | yes | drift |" in output, "framework check must report AGENTS.md drift for a missing hookless contract")
        record(failures, "append hookless runtime contract" in output, "framework check must offer a hookless contract repair")


def check_startup_and_finalization_packets(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="arbor-hookless-packets-") as tmp:
        project = Path(tmp)
        code, output = run_init(project)
        record(failures, code == 0, f"init before packet checks failed: {output.strip()}")

        startup_code, startup_output = run_command(
            [sys.executable, str(SCRIPT_ROOT / "run_session_startup_hook.py"), "--root", str(project)]
        )
        record(failures, startup_code == 0, f"startup packet failed: {startup_output.strip()}")
        assert_ordered(
            startup_output,
            [
                "## 0. project identity",
                "## 1. AGENTS.md",
                "## 2. formatted git log",
                "## 3. .arbor/memory.md",
                "## 4. git status",
            ],
            failures,
            "startup packet",
        )

        finalization_code, finalization_output = run_command(
            [sys.executable, str(SCRIPT_ROOT / "run_hookless_finalization.py"), "--root", str(project)]
        )
        record(failures, finalization_code == 0, f"hookless finalization packet failed: {finalization_output.strip()}")
        record(failures, "# Hookless Finalization Context" in finalization_output, "finalization packet must identify itself")
        record(
            failures,
            "## Stop-Equivalent Maintenance" in finalization_output,
            "finalization packet must include Stop-equivalent maintenance evidence",
        )
        record(failures, "# Memory Hygiene Context" in finalization_output, "finalization packet must include memory hygiene context")
        record(failures, "# AGENTS Guide Drift Context" in finalization_output, "finalization packet must include AGENTS guide drift context")


def check_finalization_runs_stop_equivalent_maintenance(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="arbor-hookless-finalization-stop-") as tmp:
        project = Path(tmp)
        run_command(["git", "init", str(project)])
        (project / "README.md").write_text("# Existing Project\n", encoding="utf-8")
        (project / "AGENTS.md").write_text(
            "\n".join(
                [
                    "# Agent Guide",
                    "",
                    "## Project Goal",
                    "",
                    "Existing project.",
                    "",
                    "## Project Constraints",
                    "",
                    "- Keep existing project rules.",
                    "",
                    "## Project Map",
                    "",
                    "- `README.md`: overview.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (project / ".arbor").mkdir()
        (project / ".arbor" / "memory.md").write_text("# Session Memory\n\n## In-flight\n\n- None.\n", encoding="utf-8")
        code, output = run_init(project)
        record(failures, code == 0, f"init before finalization maintenance failed: {output.strip()}")

        finalization_code, finalization_output = run_command(
            [sys.executable, str(SCRIPT_ROOT / "run_hookless_finalization.py"), "--root", str(project)]
        )
        record(
            failures,
            finalization_code == 0,
            f"hookless finalization maintenance failed: {finalization_output.strip()}",
        )
        memory = (project / ".arbor" / "memory.md").read_text(encoding="utf-8")
        record(
            failures,
            "[hook:resume]" in memory,
            "hookless finalization must preserve old Stop memory fallback behavior for dirty Arbor-managed state",
        )
        record(
            failures,
            '"continue": true' in finalization_output,
            "hookless finalization must expose old Stop adapter allow-stop evidence",
        )


def check_finalization_repairs_project_map_drift(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="arbor-hookless-finalization-map-") as tmp:
        project = Path(tmp)
        run_command(["git", "init", str(project)])
        (project / "README.md").write_text("# Existing Project\n", encoding="utf-8")
        (project / "AGENTS.md").write_text(
            "\n".join(
                [
                    "# Agent Guide",
                    "",
                    "## Project Goal",
                    "",
                    "Existing project.",
                    "",
                    "## Project Constraints",
                    "",
                    "- Keep existing project rules.",
                    "",
                    "## Project Map",
                    "",
                    "- `README.md`: overview.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (project / ".arbor").mkdir()
        (project / ".arbor" / "memory.md").write_text("# Session Memory\n\n## In-flight\n\n- None.\n", encoding="utf-8")
        (project / "src").mkdir()
        (project / "src" / "main.py").write_text("print('hello')\n", encoding="utf-8")

        finalization_code, finalization_output = run_command(
            [sys.executable, str(SCRIPT_ROOT / "run_hookless_finalization.py"), "--root", str(project)]
        )
        record(
            failures,
            finalization_code == 0,
            f"hookless finalization Project Map repair failed: {finalization_output.strip()}",
        )
        agents = (project / "AGENTS.md").read_text(encoding="utf-8")
        record(
            failures,
            "- `src/`:" in agents,
            "hookless finalization must preserve old Stop Project Map drift repair behavior",
        )


def check_hookless_trigger_contract() -> list[str]:
    failures: list[str] = []
    check_init_appends_hookless_contract(failures)
    check_contract_does_not_pollute_project_map(failures)
    check_framework_detects_missing_contract(failures)
    check_startup_and_finalization_packets(failures)
    check_finalization_runs_stop_equivalent_maintenance(failures)
    check_finalization_repairs_project_map_drift(failures)
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()

    failures = check_hookless_trigger_contract()
    if failures:
        print("hookless trigger contract failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("hookless trigger contract passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
