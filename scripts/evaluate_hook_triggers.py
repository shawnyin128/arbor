#!/usr/bin/env python3
"""Execute Arbor hook trigger scenarios through registered project hooks."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import eval_fixtures  # noqa: E402
import simulated_dispatcher  # noqa: E402


HOOK_CONFIG_PATH = Path(".codex") / "hooks.json"
STATE_PATHS = (Path("AGENTS.md"), Path(".codex") / "memory.md")


class HarnessError(ValueError):
    """Raised when hook trigger evaluation cannot proceed cleanly."""


@dataclass(frozen=True)
class StateSnapshot:
    files: dict[str, str | None]


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise HarnessError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise HarnessError(f"cannot parse {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise HarnessError(f"expected JSON object in {path}")
    return data


def snapshot_project_state(root: Path) -> StateSnapshot:
    files: dict[str, str | None] = {}
    for relative_path in STATE_PATHS:
        path = root / relative_path
        if path.is_file():
            files[str(relative_path)] = path.read_text(encoding="utf-8")
        else:
            files[str(relative_path)] = None
    return StateSnapshot(files)


def assertion(name: str, passed: bool, detail: str = "") -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def assert_contains(output: str, needle: str, name: str) -> dict[str, Any]:
    return assertion(name, needle in output, f"expected {needle!r}")


def assert_order(output: str, needles: list[str], name: str) -> dict[str, Any]:
    positions: list[int] = []
    for needle in needles:
        position = output.find(needle)
        if position < 0:
            return assertion(name, False, f"missing {needle!r}")
        positions.append(position)
    return assertion(name, positions == sorted(positions), "expected stable section order")


def assert_state_unchanged(before: StateSnapshot, after: StateSnapshot) -> dict[str, Any]:
    return assertion("project_memory_files_unchanged", after.files == before.files)


def load_registered_hooks(root: Path) -> dict[str, dict[str, Any]]:
    config = read_json(root / HOOK_CONFIG_PATH)
    hooks = config.get("hooks")
    if not isinstance(hooks, list):
        raise HarnessError(f"expected hooks list in {root / HOOK_CONFIG_PATH}")
    registered: dict[str, dict[str, Any]] = {}
    for hook in hooks:
        if isinstance(hook, dict) and hook.get("owner") == "arbor" and isinstance(hook.get("id"), str):
            registered[hook["id"]] = hook
    return registered


def resolve_hook_command(root: Path, hook: dict[str, Any], optional_args: list[str]) -> list[str]:
    entrypoint = hook.get("entrypoint")
    if not isinstance(entrypoint, dict):
        raise HarnessError(f"hook {hook.get('id')} has no entrypoint")
    if entrypoint.get("type") != "skill-script":
        raise HarnessError(f"unsupported entrypoint type for hook {hook.get('id')}: {entrypoint.get('type')}")
    skill = entrypoint.get("skill")
    script = entrypoint.get("script")
    args = entrypoint.get("args", [])
    if skill != "arbor" or not isinstance(script, str) or not isinstance(args, list):
        raise HarnessError(f"invalid entrypoint for hook {hook.get('id')}")

    script_path = ROOT / "skills" / skill / script
    if not script_path.is_file():
        raise HarnessError(f"registered hook script does not exist: {script_path}")

    resolved_args = [str(root) if arg == "${PROJECT_ROOT}" else str(arg) for arg in args]
    return [sys.executable, str(script_path), *resolved_args, *optional_args]


def is_outside_root_path(root: Path, arg: str) -> bool:
    path = Path(arg)
    if not path.is_absolute():
        return False
    resolved = path.resolve()
    return resolved != root and root not in resolved.parents


def expects_outside_root_rejection(root: Path, hook_id: str, optional_args: list[str]) -> bool:
    return hook_id == "arbor.goal_constraint_drift" and any(is_outside_root_path(root, arg) for arg in optional_args)


def assert_hook_output(
    hook_id: str,
    proc: subprocess.CompletedProcess[str],
    before: StateSnapshot,
    after: StateSnapshot,
    root: Path,
    optional_args: list[str],
) -> list[dict[str, Any]]:
    checks = [assert_state_unchanged(before, after)]
    outside_rejection = expects_outside_root_rejection(root, hook_id, optional_args)

    if outside_rejection:
        checks.extend(
            [
                assertion("outside_root_rejected", proc.returncode != 0, "expected non-zero exit"),
                assert_contains(proc.stderr, "outside project root", "outside_root_error_reported"),
                assertion("outside_root_content_not_leaked", "outside root content should never be leaked" not in proc.stdout),
            ]
        )
        return checks

    checks.append(assertion("hook_process_succeeded", proc.returncode == 0, proc.stderr))
    if hook_id == "arbor.session_startup_context":
        checks.extend(
            [
                assert_contains(proc.stdout, "# Project Startup Context", "startup_header"),
                assert_order(
                    proc.stdout,
                    ["## 1. AGENTS.md", "## 2. formatted git log", "## 3. .codex/memory.md", "## 4. git status"],
                    "startup_section_order",
                ),
            ]
        )
    elif hook_id == "arbor.in_session_memory_hygiene":
        checks.extend(
            [
                assert_contains(proc.stdout, "# Memory Hygiene Context", "memory_header"),
                assert_contains(proc.stdout, "## 1. .codex/memory.md", "memory_section"),
                assert_contains(proc.stdout, "## 2. git status", "memory_git_status_section"),
                assert_contains(proc.stdout, "## 3. git diff --stat", "memory_unstaged_diff_stat_section"),
                assert_contains(proc.stdout, "## 4. git diff --cached --stat", "memory_staged_diff_stat_section"),
            ]
        )
    elif hook_id == "arbor.goal_constraint_drift":
        checks.extend(
            [
                assert_contains(proc.stdout, "# AGENTS Guide Drift Context", "agents_drift_header"),
                assert_contains(proc.stdout, "## 1. AGENTS.md", "agents_section"),
                assert_contains(proc.stdout, "## 2. git status", "agents_git_status_section"),
            ]
        )
        if optional_args:
            checks.append(assert_contains(proc.stdout, "selected project doc", "agents_selected_doc_section"))
    else:
        checks.append(assertion("known_hook_id", False, f"unsupported hook id: {hook_id}"))
    return checks


def execute_registered_hook(root: Path, hook_id: str, optional_args: list[str] | None = None) -> dict[str, Any]:
    optional_args = list(optional_args or [])
    hooks = load_registered_hooks(root)
    if hook_id not in hooks:
        raise HarnessError(f"registered hook not found: {hook_id}")
    command = resolve_hook_command(root, hooks[hook_id], optional_args)
    before = snapshot_project_state(root)
    proc = subprocess.run(command, cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    after = snapshot_project_state(root)
    assertions = assert_hook_output(hook_id, proc, before, after, root, optional_args)
    return {
        "hook_id": hook_id,
        "command": command,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "assertions": assertions,
        "passed": all(item["passed"] for item in assertions),
    }


def evaluate_scenario(scenario_id: str, work_root: Path) -> dict[str, Any]:
    scenarios = simulated_dispatcher.load_scenario_corpus()
    if scenario_id not in scenarios:
        raise HarnessError(f"unknown scenario id: {scenario_id}")
    scenario = scenarios[scenario_id]
    fixture_name = scenario.expectation["fixture"]
    fixture_root = work_root.resolve() / f"{scenario_id}-{fixture_name}"
    fixture = eval_fixtures.build_fixture(fixture_name, fixture_root)
    dispatch = simulated_dispatcher.simulate_dispatch(scenario, fixture.summary)

    executions = [
        execute_registered_hook(fixture.root, hook_id, dispatch["optional_args"].get(hook_id, []))
        for hook_id in dispatch["hooks"]
    ]
    return {
        "scenario_id": scenario_id,
        "expression": scenario.expression,
        "expected_label": scenario.expected_label,
        "fixture": fixture.summary,
        "dispatcher": dispatch,
        "executions": executions,
        "passed": all(execution["passed"] for execution in executions),
    }


def compact_execution(execution: dict[str, Any]) -> dict[str, Any]:
    failed_assertions = [
        item for item in execution["assertions"]
        if not item["passed"]
    ]
    return {
        "hook_id": execution["hook_id"],
        "returncode": execution["returncode"],
        "passed": execution["passed"],
        "assertion_count": len(execution["assertions"]),
        "failed_assertions": failed_assertions,
    }


def compact_scenario_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "scenario_id": result["scenario_id"],
        "expected_label": result["expected_label"],
        "fixture": result["fixture"]["fixture"],
        "decision": result["dispatcher"]["decision"],
        "hooks": result["dispatcher"]["hooks"],
        "requires_agent_judgment": result["dispatcher"]["requires_agent_judgment"],
        "executions": [compact_execution(execution) for execution in result["executions"]],
        "passed": result["passed"],
    }


def increment(counter: dict[str, int], key: str) -> None:
    counter[key] = counter.get(key, 0) + 1


def summarize_corpus_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    decision_counts: dict[str, int] = {}
    hook_counts: dict[str, int] = {}
    assertion_failures: list[dict[str, Any]] = []
    selected_hook_executions = 0
    passed_hook_executions = 0
    outside_root_rejections = 0
    outside_root_rejections_passed = 0
    outside_root_leaks = 0
    unintended_write_failures = 0

    for result in results:
        increment(decision_counts, result["dispatcher"]["decision"])
        for execution in result["executions"]:
            selected_hook_executions += 1
            if execution["passed"]:
                passed_hook_executions += 1
            increment(hook_counts, execution["hook_id"])
            by_name = {item["name"]: item for item in execution["assertions"]}
            if "outside_root_rejected" in by_name:
                outside_root_rejections += 1
                if by_name["outside_root_rejected"]["passed"] and by_name.get("outside_root_content_not_leaked", {}).get("passed"):
                    outside_root_rejections_passed += 1
                if not by_name.get("outside_root_content_not_leaked", {}).get("passed", False):
                    outside_root_leaks += 1
            if not by_name.get("project_memory_files_unchanged", {}).get("passed", True):
                unintended_write_failures += 1
            for item in execution["assertions"]:
                if not item["passed"]:
                    assertion_failures.append(
                        {
                            "scenario_id": result["scenario_id"],
                            "hook_id": execution["hook_id"],
                            "assertion": item,
                        }
                    )

    total_scenarios = len(results)
    passed_scenarios = sum(1 for result in results if result["passed"])
    scenarios_with_hooks = sum(1 for result in results if result["executions"])
    hook_execution_pass_rate = (
        passed_hook_executions / selected_hook_executions
        if selected_hook_executions
        else 1.0
    )
    return {
        "total_scenarios": total_scenarios,
        "passed_scenarios": passed_scenarios,
        "failed_scenarios": [result["scenario_id"] for result in results if not result["passed"]],
        "decision_counts": decision_counts,
        "hook_counts": hook_counts,
        "scenarios_with_hooks": scenarios_with_hooks,
        "scenarios_without_hooks": total_scenarios - scenarios_with_hooks,
        "selected_hook_executions": selected_hook_executions,
        "passed_hook_executions": passed_hook_executions,
        "hook_execution_pass_rate": hook_execution_pass_rate,
        "outside_root_rejections": outside_root_rejections,
        "outside_root_rejections_passed": outside_root_rejections_passed,
        "outside_root_leaks": outside_root_leaks,
        "unintended_write_failures": unintended_write_failures,
        "assertion_failures": assertion_failures,
        "semantic_metrics": {
            "reported": False,
            "reason": "Dispatcher output is sidecar-backed; this report measures harness and hook execution plumbing, not real semantic trigger quality.",
        },
    }


def evaluate_corpus(work_root: Path, include_details: bool = False) -> dict[str, Any]:
    scenarios = simulated_dispatcher.load_scenario_corpus()
    results = [evaluate_scenario(scenario_id, work_root) for scenario_id in sorted(scenarios)]
    report = {
        "report_type": "sidecar_backed_hook_execution",
        "summary": summarize_corpus_results(results),
    }
    if include_details:
        report["scenarios"] = results
    else:
        report["scenarios"] = [compact_scenario_result(result) for result in results]
    report["passed"] = report["summary"]["passed_scenarios"] == report["summary"]["total_scenarios"]
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--scenario-id", help="Scenario id from the trigger scenario corpus.")
    target.add_argument("--all", action="store_true", help="Run every scenario in the trigger scenario corpus.")
    parser.add_argument("--work-root", type=Path, required=True, help="Directory where temporary fixture roots are created.")
    parser.add_argument("--include-details", action="store_true", help="Include full hook stdout/stderr for corpus reports.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.all:
            result = evaluate_corpus(args.work_root, include_details=args.include_details)
        else:
            result = evaluate_scenario(args.scenario_id, args.work_root)
    except (HarnessError, eval_fixtures.FixtureError, simulated_dispatcher.DispatchError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
