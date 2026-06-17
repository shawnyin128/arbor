#!/usr/bin/env python3
"""Run real Codex hookless trigger scenarios.

Default mode is a fast skip. Pass ``--run-codex`` only when a change materially
rewrites Arbor's hookless context path, trigger wording, or scenario harness.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


sys.dont_write_bytecode = True

SCRIPT_ROOT = Path(__file__).resolve().parent
PLUGIN_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = PLUGIN_ROOT.parents[1]
DEFAULT_CODEX_TIMEOUT_SECONDS = 900.0
START_MARKER = "<!-- ARBOR HOOKLESS RUNTIME CONTRACT START -->"


@dataclass(frozen=True)
class Scenario:
    name: str
    prompt: str
    expected_paths: tuple[str, ...]
    expected_agents_terms: tuple[str, ...] = ()
    expected_memory_terms: tuple[str, ...] = ()
    rationale_label: str = "FINAL_RATIONALE"


@dataclass(frozen=True)
class ScenarioResult:
    name: str
    project_root: Path
    events_path: Path
    last_message_path: Path
    failures: list[str]


def codex_timeout_seconds() -> float:
    raw = os.environ.get("ARBOR_CODEX_SCENARIO_TIMEOUT_SECONDS")
    if not raw:
        return DEFAULT_CODEX_TIMEOUT_SECONDS
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_CODEX_TIMEOUT_SECONDS
    return value if value > 0 else DEFAULT_CODEX_TIMEOUT_SECONDS


def command_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def run_command(args: list[str], cwd: Path | None = None, input_text: str | None = None) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            args,
            cwd=str(cwd) if cwd is not None else None,
            input=input_text,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=command_env(),
            check=False,
            timeout=codex_timeout_seconds(),
        )
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout if isinstance(exc.stdout, str) else ""
        return 124, f"command timed out after {codex_timeout_seconds():g}s: {' '.join(args)}\n{output.strip()}"
    except OSError as exc:
        return 127, f"command failed to start: {' '.join(args)}: {exc}"
    return proc.returncode, proc.stdout


def run_command_to_file(
    args: list[str],
    output_path: Path,
    cwd: Path | None = None,
    input_text: str | None = None,
) -> tuple[int, str]:
    try:
        with output_path.open("w", encoding="utf-8") as output_file:
            proc = subprocess.run(
                args,
                cwd=str(cwd) if cwd is not None else None,
                input=input_text,
                text=True,
                stdout=output_file,
                stderr=subprocess.STDOUT,
                env=command_env(),
                check=False,
                timeout=codex_timeout_seconds(),
            )
    except subprocess.TimeoutExpired:
        output = output_path.read_text(encoding="utf-8", errors="replace") if output_path.is_file() else ""
        return 124, output
    except OSError as exc:
        return 127, f"command failed to start: {' '.join(args)}: {exc}"
    return proc.returncode, output_path.read_text(encoding="utf-8", errors="replace")


def codex_base_command() -> list[str]:
    codex = shutil.which("codex")
    if not codex:
        raise RuntimeError("codex executable not found on PATH")
    return [codex]


def valid_agents_text() -> str:
    return "\n".join(
        [
            "# Agent Guide",
            "",
            "## Project Goal",
            "",
            "Scenario project for Arbor hookless trigger validation.",
            "",
            "## Project Constraints",
            "",
            "- Follow repository instructions before making project changes.",
            "",
            "## Project Map",
            "",
            "- `README.md`: overview.",
            "",
        ]
    )


def initialize_project(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    run_command(["git", "init"], cwd=root)
    run_command(["git", "config", "user.email", "arbor@example.invalid"], cwd=root)
    run_command(["git", "config", "user.name", "Arbor Scenario"], cwd=root)
    (root / "README.md").write_text("# Scenario Project\n", encoding="utf-8")
    (root / "AGENTS.md").write_text(valid_agents_text(), encoding="utf-8")
    (root / ".arbor").mkdir()
    (root / ".arbor" / "memory.md").write_text("# Session Memory\n\n## In-flight\n\n- None.\n", encoding="utf-8")

    code, output = run_command(
        [
            sys.executable,
            str(SCRIPT_ROOT / "init_project_memory.py"),
            "--root",
            str(root),
            "--claude-bridge",
            "off",
        ]
    )
    if code != 0:
        raise RuntimeError(f"init_project_memory.py failed: {output.strip()}")
    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    if START_MARKER not in agents:
        raise RuntimeError("initialized AGENTS.md lacks Arbor hookless runtime contract")

    run_command(["git", "add", "."], cwd=root)
    run_command(["git", "commit", "-m", "initialize scenario project"], cwd=root)


def scenarios() -> list[Scenario]:
    return [
        Scenario(
            name="natural-durable-entrypoint",
            prompt=(
                "Follow the repository instructions exactly. Create a new durable source entrypoint at "
                "`src/main.py` containing a tiny `hello()` function that returns `'hello from scenario'`. "
                "Do not add tests or extra files for this scenario. "
                "Before the final answer, include a compact `FINAL_RATIONALE` JSON object explaining the "
                "project-instruction chain you followed and any maintenance command you ran."
            ),
            expected_paths=("src/main.py",),
            expected_agents_terms=("- `src/`:",),
        ),
        Scenario(
            name="arbor-managed-checkpoint",
            prompt=(
                "Follow the repository instructions exactly. Create `.arbor/checkpoint.txt` with one line: "
                "`scenario checkpoint`. Before the final answer, include a compact `FINAL_RATIONALE` JSON "
                "object explaining the project-instruction chain you followed and any maintenance command you ran."
            ),
            expected_paths=(".arbor/checkpoint.txt",),
            expected_memory_terms=("[hook:resume]",),
        ),
    ]


def run_codex_scenario(scenario: Scenario, scenario_dir: Path, keep_projects: bool) -> ScenarioResult:
    project_root = scenario_dir / "project"
    evidence_dir = scenario_dir / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    initialize_project(project_root)

    events_path = evidence_dir / "codex-events.jsonl"
    last_message_path = evidence_dir / "codex-last-message.txt"
    command = [
        *codex_base_command(),
        "exec",
        "--cd",
        str(project_root),
        "--skip-git-repo-check",
        "--sandbox",
        "workspace-write",
        "--output-last-message",
        str(last_message_path),
        "--json",
        "-",
    ]
    code, event_text = run_command_to_file(command, events_path, input_text=scenario.prompt)
    last_message = last_message_path.read_text(encoding="utf-8", errors="replace") if last_message_path.is_file() else ""

    failures: list[str] = []
    if code != 0 and not (code == 124 and '"type":"turn.completed"' in event_text):
        failures.append(f"codex exec exited {code}")
    if "# Project Startup Context" not in event_text:
        failures.append("Codex events did not show a successful Project Startup Context packet")
    if "# Hookless Finalization Context" not in event_text:
        failures.append("Codex events did not show a successful Hookless Finalization Context packet")
    if scenario.rationale_label not in last_message:
        failures.append(f"final message did not include {scenario.rationale_label}")
    for rel_path in scenario.expected_paths:
        if not (project_root / rel_path).is_file():
            failures.append(f"expected file was not created: {rel_path}")
    if scenario.expected_agents_terms:
        agents = (project_root / "AGENTS.md").read_text(encoding="utf-8", errors="replace")
        for term in scenario.expected_agents_terms:
            if term not in agents:
                failures.append(f"AGENTS.md did not contain expected term: {term}")
    if scenario.expected_memory_terms:
        memory = (project_root / ".arbor" / "memory.md").read_text(encoding="utf-8", errors="replace")
        for term in scenario.expected_memory_terms:
            if term not in memory:
                failures.append(f".arbor/memory.md did not contain expected term: {term}")

    if not keep_projects and not failures:
        shutil.rmtree(project_root, ignore_errors=True)
    return ScenarioResult(scenario.name, project_root, events_path, last_message_path, failures)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-codex", action="store_true", help="Actually launch codex exec scenario runs.")
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Number of times to run each scenario when --run-codex is set.",
    )
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        help="Directory for scenario projects and Codex JSONL evidence. Defaults to a temp directory.",
    )
    parser.add_argument("--keep-projects", action="store_true", help="Keep passing scenario project directories.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error("--repeat must be >= 1")
    if not args.run_codex:
        print("real Codex hookless trigger scenarios skipped; pass --run-codex to execute")
        return 0

    root = args.evidence_dir
    if root is None:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        root = Path(tempfile.mkdtemp(prefix=f"arbor-codex-hookless-{stamp}-"))
    else:
        root.mkdir(parents=True, exist_ok=True)

    all_results: list[ScenarioResult] = []
    for repeat_index in range(1, args.repeat + 1):
        for scenario in scenarios():
            scenario_dir = root / f"{scenario.name}-{repeat_index}"
            result = run_codex_scenario(scenario, scenario_dir, args.keep_projects)
            all_results.append(result)

    failures = [result for result in all_results if result.failures]
    print(f"real Codex hookless trigger scenarios evidence: {root}")
    for result in all_results:
        status = "pass" if not result.failures else "fail"
        print(f"- {result.name}: {status}")
        print(f"  events: {result.events_path}")
        print(f"  last: {result.last_message_path}")
        if result.failures:
            for failure in result.failures:
                print(f"  - {failure}")
            print(f"  project: {result.project_root}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
