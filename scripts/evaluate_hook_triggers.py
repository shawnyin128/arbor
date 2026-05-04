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
import plugin_trigger_adapters  # noqa: E402
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


def evaluate_scenario(
    scenario_id: str,
    work_root: Path,
    trigger_adapter: str = "sidecar-baseline",
    runtime_options: plugin_trigger_adapters.RuntimeAdapterOptions | None = None,
    capture_adapter_errors: bool = False,
) -> dict[str, Any]:
    scenarios = simulated_dispatcher.load_scenario_corpus()
    if scenario_id not in scenarios:
        raise HarnessError(f"unknown scenario id: {scenario_id}")
    scenario = scenarios[scenario_id]
    fixture_name = scenario.expectation["fixture"]
    fixture_root = work_root.resolve() / f"{scenario_id}-{fixture_name}"
    fixture = eval_fixtures.build_fixture(fixture_name, fixture_root)
    try:
        trigger_decision = plugin_trigger_adapters.trigger_with_adapter(
            trigger_adapter,
            scenario,
            fixture.root,
            fixture.summary,
            runtime_options=runtime_options,
        )
    except plugin_trigger_adapters.AdapterError as exc:
        if not capture_adapter_errors:
            raise
        error_message = str(exc)[:plugin_trigger_adapters.RUNTIME_DETAIL_MAX_CHARS]
        return {
            "scenario_id": scenario_id,
            "expression": scenario.expression,
            "expected_label": scenario.expected_label,
            "fixture": fixture.summary,
            "trigger_adapter": trigger_adapter,
            "trigger_decision": {
                "hooks": [],
                "decision": "ambiguous",
                "confidence": "low",
                "requires_agent_judgment": True,
                "optional_args": {},
                "reason": f"Plugin trigger adapter contract error: {error_message}",
            },
            "adapter_error": {
                "type": type(exc).__name__,
                "message": error_message,
            },
            "executions": [],
            "passed": False,
        }

    executions = [
        execute_registered_hook(fixture.root, hook_id, trigger_decision["optional_args"].get(hook_id, []))
        for hook_id in trigger_decision["hooks"]
    ]
    return {
        "scenario_id": scenario_id,
        "expression": scenario.expression,
        "expected_label": scenario.expected_label,
        "fixture": fixture.summary,
        "trigger_adapter": trigger_adapter,
        "trigger_decision": trigger_decision,
        "executions": executions,
        "passed": all(execution["passed"] for execution in executions),
    }


def parse_expected_hooks(value: str) -> list[str]:
    if not value.strip():
        return []
    hooks = [hook.strip() for hook in value.split(",") if hook.strip()]
    unknown_hooks = sorted(set(hooks) - plugin_trigger_adapters.ARBOR_HOOK_IDS)
    if unknown_hooks:
        raise argparse.ArgumentTypeError(f"unknown Arbor hook id(s): {', '.join(unknown_hooks)}")
    return hooks


def parse_scenario_ids(value: str) -> list[str]:
    scenario_ids = [item.strip() for item in value.split(",") if item.strip()]
    if not scenario_ids:
        raise argparse.ArgumentTypeError("must include at least one scenario id")
    scenarios = simulated_dispatcher.load_scenario_corpus()
    unknown_ids = [scenario_id for scenario_id in scenario_ids if scenario_id not in scenarios]
    if unknown_ids:
        raise argparse.ArgumentTypeError(f"unknown scenario id(s): {', '.join(unknown_ids)}")
    return scenario_ids


def apply_smoke_expectations(
    result: dict[str, Any],
    expected_decision: str | None = None,
    expected_hooks: list[str] | None = None,
    require_runtime_available: bool = False,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    trigger_decision = result["trigger_decision"]
    if require_runtime_available:
        blocker = runtime_blocker_reason(trigger_decision)
        checks.append(
            assertion(
                "runtime_available",
                blocker is None,
                "runtime available" if blocker is None else f"blocked by {blocker}",
            )
        )
    if expected_decision is not None:
        actual_decision = trigger_decision["decision"]
        checks.append(
            assertion(
                "expected_decision",
                actual_decision == expected_decision,
                f"expected {expected_decision!r}, observed {actual_decision!r}",
            )
        )
    if expected_hooks is not None:
        actual_hooks = sorted(trigger_decision["hooks"])
        expected = sorted(expected_hooks)
        checks.append(
            assertion(
                "expected_hooks",
                actual_hooks == expected,
                f"expected {expected!r}, observed {actual_hooks!r}",
            )
        )
    if not checks:
        return result
    return {
        **result,
        "smoke_assertions": checks,
        "passed": result["passed"] and all(check["passed"] for check in checks),
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
    compact = {
        "scenario_id": result["scenario_id"],
        "expected_label": result["expected_label"],
        "fixture": result["fixture"]["fixture"],
        "trigger_adapter": result["trigger_adapter"],
        "decision": result["trigger_decision"]["decision"],
        "hooks": result["trigger_decision"]["hooks"],
        "optional_args": result["trigger_decision"].get("optional_args", {}),
        "requires_agent_judgment": result["trigger_decision"]["requires_agent_judgment"],
        "executions": [compact_execution(execution) for execution in result["executions"]],
        "passed": result["passed"],
    }
    if "adapter_error" in result:
        compact["adapter_error"] = result["adapter_error"]
    return compact


def progress_event(result: dict[str, Any], index: int, total: int) -> dict[str, Any]:
    trigger_decision = result["trigger_decision"]
    return {
        "index": index,
        "total": total,
        "scenario_id": result["scenario_id"],
        "expected_label": result["expected_label"],
        "trigger_adapter": result["trigger_adapter"],
        "decision": trigger_decision["decision"],
        "hooks": trigger_decision["hooks"],
        "runtime_blocker": runtime_blocker_reason(trigger_decision),
        "adapter_error": result.get("adapter_error"),
        "execution_count": len(result["executions"]),
        "passed": result["passed"],
    }


def append_progress(progress_jsonl: Path | None, event: dict[str, Any]) -> None:
    if progress_jsonl is None:
        return
    progress_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with progress_jsonl.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")


def write_report_json(report_json: Path | None, result: dict[str, Any]) -> None:
    if report_json is None:
        return
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def increment(counter: dict[str, int], key: str) -> None:
    counter[key] = counter.get(key, 0) + 1


def runtime_blocker_reason(trigger_decision: dict[str, Any]) -> str | None:
    reason = trigger_decision.get("reason")
    if (
        trigger_decision.get("decision") == "ambiguous"
        and trigger_decision.get("hooks") == []
        and trigger_decision.get("requires_agent_judgment") is True
        and isinstance(reason, str)
        and reason.startswith("Plugin runtime unavailable: ")
    ):
        blocker = reason.removeprefix("Plugin runtime unavailable: ")
        blocker = blocker.split(". Semantic hook selection was not measured.", 1)[0]
        return blocker.split("; detail:", 1)[0]
    return None


def runtime_availability_gate(trigger_adapter: str, results: list[dict[str, Any]] | None) -> dict[str, Any]:
    if trigger_adapter != "plugin-runtime-codex-exec":
        return {
            "passed": False,
            "status": "not_applicable",
            "reason": "Runtime availability applies only to a real plugin runtime trigger adapter.",
        }
    if results is None:
        return {
            "passed": False,
            "status": "unknown",
            "reason": "Runtime availability requires corpus results.",
        }
    if not results:
        return {
            "passed": False,
            "status": "no_results",
            "total_scenarios": 0,
            "blocked_scenario_count": 0,
            "blocker_counts": {},
            "blocked_scenarios": [],
            "reason": "Runtime availability requires at least one evaluated scenario.",
        }

    blocker_counts: dict[str, int] = {}
    blocked_scenarios: list[dict[str, str]] = []
    for result in results:
        blocker = runtime_blocker_reason(result["trigger_decision"])
        if blocker is None:
            continue
        increment(blocker_counts, blocker)
        blocked_scenarios.append({"scenario_id": result["scenario_id"], "reason": blocker})

    passed = not blocked_scenarios
    return {
        "passed": passed,
        "status": "available" if passed else "blocked",
        "total_scenarios": len(results),
        "blocked_scenario_count": len(blocked_scenarios),
        "blocker_counts": blocker_counts,
        "blocked_scenarios": blocked_scenarios,
        "reason": "No runtime blocker decisions were observed." if passed else "Runtime blocker decisions are excluded from semantic scoring.",
    }


def adapter_eligibility_gate(trigger_adapter: str) -> dict[str, Any]:
    if trigger_adapter == "plugin-runtime-codex-exec":
        return {
            "passed": True,
            "status": "eligible",
            "reason": "Adapter decisions come from the installed plugin runtime path.",
        }
    if trigger_adapter == "sidecar-baseline":
        reason = "Trigger decisions are sidecar-backed; this report measures harness and hook execution plumbing, not real plugin semantic trigger quality."
    elif trigger_adapter == "plugin-runtime-stub":
        reason = "Plugin-runtime stub abstains from semantic hook selection; this report validates adapter wiring and non-circular input only."
    else:
        reason = "Semantic metrics require a non-stub plugin runtime trigger adapter."
    return {"passed": False, "status": "ineligible", "reason": reason}


def hook_execution_gate(summary: dict[str, Any] | None) -> dict[str, Any]:
    if summary is None:
        return {
            "passed": False,
            "status": "unknown",
            "reason": "Hook execution gate requires corpus execution summary.",
        }
    passed = (
        summary["hook_execution_pass_rate"] == 1.0
        and summary["outside_root_leaks"] == 0
        and summary["unintended_write_failures"] == 0
        and not summary["assertion_failures"]
    )
    return {
        "passed": passed,
        "status": "clean" if passed else "failed",
        "hook_execution_pass_rate": summary["hook_execution_pass_rate"],
        "outside_root_leaks": summary["outside_root_leaks"],
        "unintended_write_failures": summary["unintended_write_failures"],
        "assertion_failure_count": len(summary["assertion_failures"]),
        "reason": "Hook execution assertions are clean." if passed else "Hook execution failures must be resolved before semantic scoring.",
    }


def adapter_contract_gate(results: list[dict[str, Any]] | None) -> dict[str, Any]:
    if results is None:
        return {
            "passed": False,
            "status": "unknown",
            "reason": "Adapter contract gate requires corpus results.",
        }
    failures = [
        {
            "scenario_id": result["scenario_id"],
            "message": result.get("adapter_error", {}).get("message", "adapter contract error"),
        }
        for result in results
        if "adapter_error" in result
    ]
    return {
        "passed": not failures,
        "status": "clean" if not failures else "failed",
        "adapter_error_count": len(failures),
        "adapter_error_scenarios": failures,
        "reason": "Adapter trigger decisions matched the contract." if not failures else "Adapter contract errors must be resolved before semantic scoring.",
    }


def ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def scenario_semantic_outcome(result: dict[str, Any], scenario: simulated_dispatcher.TriggerScenario) -> dict[str, Any]:
    trigger_decision = result["trigger_decision"]
    expectation = scenario.expectation
    selected_hooks = set(trigger_decision["hooks"])
    expected_hooks = set(expectation["expected_hooks"])
    optional_hooks = set(expectation["optional_expected_hooks"])
    forbidden_hooks = set(expectation["forbidden_hooks"])
    allowed_decisions = set(expectation["allowed_decisions"])
    forbidden_selected = sorted(selected_hooks & forbidden_hooks)
    raw_missing_required = sorted(expected_hooks - selected_hooks)
    missing_required = list(raw_missing_required)
    unexpected_hooks = sorted(selected_hooks - expected_hooks - optional_hooks)
    decision = trigger_decision["decision"]
    decision_allowed = decision in allowed_decisions
    trigger_shape_valid = decision == "trigger" or not selected_hooks
    # Preserve raw metric inputs separately from scenario-failure presentation.
    # Allowed ambiguous abstention may be accepted, but it is not a required-hook hit.
    if decision == "ambiguous" and "ambiguous" in allowed_decisions:
        missing_required = []

    return {
        "scenario_id": result["scenario_id"],
        "expected_label": scenario.expected_label,
        "decision": decision,
        "decision_allowed": decision_allowed,
        "selected_hooks": sorted(selected_hooks),
        "expected_hooks": sorted(expected_hooks),
        "optional_expected_hooks": sorted(optional_hooks),
        "forbidden_selected": forbidden_selected,
        "raw_missing_required_hooks": raw_missing_required,
        "missing_required_hooks": missing_required,
        "unexpected_hooks": unexpected_hooks,
        "requires_agent_judgment": bool(expectation["requires_agent_judgment"]),
        "passed": bool(decision_allowed and trigger_shape_valid and not forbidden_selected and not missing_required),
    }


def compute_semantic_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    scenarios = simulated_dispatcher.load_scenario_corpus()
    outcomes = [
        scenario_semantic_outcome(result, scenarios[result["scenario_id"]])
        for result in results
    ]
    hook_stats = {
        hook_id: {"selected": 0, "true_positive": 0, "false_positive": 0, "required": 0, "recalled": 0}
        for hook_id in sorted(plugin_trigger_adapters.ARBOR_HOOK_IDS)
    }
    none_total = 0
    none_false_positive = 0
    near_miss_total = 0
    near_miss_false_positive = 0
    ambiguous_total = 0
    ambiguous_accepted = 0
    multi_total = 0
    multi_exact_required = 0
    multi_required_present = 0
    multi_required_total = 0

    for result, outcome in zip(results, outcomes):
        scenario = scenarios[result["scenario_id"]]
        expectation = scenario.expectation
        selected = set(outcome["selected_hooks"])
        expected = set(outcome["expected_hooks"])
        optional = set(outcome["optional_expected_hooks"])

        for hook_id, stats in hook_stats.items():
            if hook_id in selected:
                stats["selected"] += 1
                if hook_id in expected or hook_id in optional:
                    stats["true_positive"] += 1
                else:
                    stats["false_positive"] += 1
            if hook_id in expected and not expectation["requires_agent_judgment"]:
                stats["required"] += 1
                if hook_id in selected:
                    stats["recalled"] += 1

        if scenario.expected_label == "NONE" or expectation["allowed_decisions"] == ["none"]:
            none_total += 1
            if result["trigger_decision"]["decision"] == "trigger" or selected:
                none_false_positive += 1
        if result["scenario_id"].startswith("NM-"):
            near_miss_total += 1
            if result["trigger_decision"]["decision"] == "trigger" or selected:
                near_miss_false_positive += 1
        if expectation["requires_agent_judgment"] or "ambiguous" in expectation["allowed_decisions"]:
            ambiguous_total += 1
            if outcome["decision_allowed"] and not outcome["forbidden_selected"] and not outcome["unexpected_hooks"]:
                ambiguous_accepted += 1
        if scenario.expected_label == "MULTI" or len(expected | optional) > 1:
            multi_total += 1
            required_present = len(selected & expected)
            required_total = len(expected)
            multi_required_present += required_present
            multi_required_total += required_total
            if not outcome["raw_missing_required_hooks"] and not outcome["forbidden_selected"] and not outcome["unexpected_hooks"]:
                multi_exact_required += 1

    per_hook = {
        hook_id: {
            **stats,
            "precision": ratio(stats["true_positive"], stats["selected"]),
            "recall": ratio(stats["recalled"], stats["required"]),
        }
        for hook_id, stats in hook_stats.items()
    }
    failures = [
        {
            "scenario_id": outcome["scenario_id"],
            "decision": outcome["decision"],
            "selected_hooks": outcome["selected_hooks"],
            "raw_missing_required_hooks": outcome["raw_missing_required_hooks"],
            "missing_required_hooks": outcome["missing_required_hooks"],
            "forbidden_selected": outcome["forbidden_selected"],
            "unexpected_hooks": outcome["unexpected_hooks"],
        }
        for outcome in outcomes
        if not outcome["passed"]
    ]
    return {
        "scenario_count": len(results),
        "passed_scenarios": sum(1 for outcome in outcomes if outcome["passed"]),
        "failed_scenarios": failures,
        "per_hook": per_hook,
        "none_false_positive_rate": ratio(none_false_positive, none_total),
        "none_false_positive_count": none_false_positive,
        "none_scenario_count": none_total,
        "near_miss_false_positive_rate": ratio(near_miss_false_positive, near_miss_total),
        "near_miss_false_positive_count": near_miss_false_positive,
        "near_miss_scenario_count": near_miss_total,
        "ambiguous_acceptance_rate": ratio(ambiguous_accepted, ambiguous_total),
        "ambiguous_accepted_count": ambiguous_accepted,
        "ambiguous_scenario_count": ambiguous_total,
        "multi_hook_required_recall": ratio(multi_required_present, multi_required_total),
        "multi_hook_required_selected_count": multi_required_present,
        "multi_hook_required_total": multi_required_total,
        "multi_hook_exact_required_rate": ratio(multi_exact_required, multi_total),
        "multi_hook_exact_required_count": multi_exact_required,
        "multi_hook_scenario_count": multi_total,
        "stability": {
            "reported": False,
            "reason": "Stability requires repeated real runtime runs and is not computed from a single corpus pass.",
        },
    }


def semantic_metric_status(
    trigger_adapter: str,
    results: list[dict[str, Any]] | None = None,
    execution_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gates = {
        "adapter_eligibility": adapter_eligibility_gate(trigger_adapter),
        "adapter_contract": adapter_contract_gate(results),
        "runtime_availability": runtime_availability_gate(trigger_adapter, results),
        "hook_execution": hook_execution_gate(execution_summary),
    }
    ready = all(gate["passed"] for gate in gates.values())
    status = {
        "reported": ready,
        "ready_for_semantic_metrics": ready,
        "reason": "Semantic trigger metrics are reported." if ready else "Semantic trigger metrics are withheld until every scoring gate passes.",
        "gates": gates,
    }
    if ready and results is not None:
        metrics = compute_semantic_metrics(results)
        status["metrics"] = metrics
        status["passed"] = not metrics["failed_scenarios"]
    else:
        status["passed"] = False
    return status


def trigger_decision_signature(result: dict[str, Any]) -> dict[str, Any]:
    if "trigger_decision" in result:
        decision = result["trigger_decision"]
        decision_value = decision["decision"]
        hooks = decision.get("hooks", [])
        optional_args = decision.get("optional_args", {})
    else:
        decision_value = result["decision"]
        hooks = result.get("hooks", [])
        optional_args = result.get("optional_args", {})
    return {
        "decision": decision_value,
        "hooks": sorted(hooks),
        "optional_args": {
            hook_id: list(args)
            for hook_id, args in sorted(optional_args.items())
            if isinstance(args, list)
        },
    }


def compute_repeated_runtime_stability(reports: list[dict[str, Any]], trigger_adapter: str) -> dict[str, Any]:
    run_count = len(reports)
    if trigger_adapter != "plugin-runtime-codex-exec":
        return {
            "reported": False,
            "reason": "Stability requires repeated real plugin runtime corpus runs.",
            "run_count": run_count,
        }
    if run_count < 2:
        return {
            "reported": False,
            "reason": "Stability requires at least two real runtime corpus runs.",
            "run_count": run_count,
        }

    not_ready_runs = []
    for index, report in enumerate(reports, start=1):
        semantic_metrics = report.get("summary", {}).get("semantic_metrics", {})
        if not semantic_metrics.get("reported"):
            not_ready_runs.append(
                {
                    "run_index": index,
                    "reason": semantic_metrics.get("reason", "semantic metrics were not reported"),
                    "gates": semantic_metrics.get("gates", {}),
                }
            )
    if not_ready_runs:
        return {
            "reported": False,
            "reason": "Stability is withheld until every repeated run reports semantic metrics.",
            "run_count": run_count,
            "not_ready_runs": not_ready_runs,
        }

    scenario_sets = [
        {scenario["scenario_id"] for scenario in report.get("scenarios", [])}
        for report in reports
    ]
    if not scenario_sets or any(scenario_set != scenario_sets[0] for scenario_set in scenario_sets):
        return {
            "reported": False,
            "reason": "Stability requires every repeated run to contain the same scenario ids.",
            "run_count": run_count,
        }

    signatures_by_run = []
    for report in reports:
        signatures_by_run.append(
            {
                scenario["scenario_id"]: trigger_decision_signature(scenario)
                for scenario in report.get("scenarios", [])
            }
        )

    unstable_scenarios = []
    for scenario_id in sorted(scenario_sets[0]):
        signatures = [run[scenario_id] for run in signatures_by_run]
        if any(signature != signatures[0] for signature in signatures[1:]):
            unstable_scenarios.append(
                {
                    "scenario_id": scenario_id,
                    "signatures": [
                        {"run_index": index, **signature}
                        for index, signature in enumerate(signatures, start=1)
                    ],
                }
            )

    scenario_count = len(scenario_sets[0])
    stable_count = scenario_count - len(unstable_scenarios)
    return {
        "reported": True,
        "reason": "Stability is reported from repeated gate-ready real runtime corpus runs.",
        "run_count": run_count,
        "scenario_count": scenario_count,
        "stable_scenario_count": stable_count,
        "unstable_scenario_count": len(unstable_scenarios),
        "stability_rate": ratio(stable_count, scenario_count),
        "unstable_scenarios": unstable_scenarios,
    }


def summarize_corpus_results(results: list[dict[str, Any]], trigger_adapter: str) -> dict[str, Any]:
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
        increment(decision_counts, result["trigger_decision"]["decision"])
        if "adapter_error" in result:
            continue
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
    summary = {
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
    }
    summary["semantic_metrics"] = semantic_metric_status(trigger_adapter, results, summary)
    return summary


def evaluate_corpus(
    work_root: Path,
    include_details: bool = False,
    trigger_adapter: str = "sidecar-baseline",
    runtime_options: plugin_trigger_adapters.RuntimeAdapterOptions | None = None,
    scenario_ids: list[str] | None = None,
    progress_jsonl: Path | None = None,
) -> dict[str, Any]:
    scenarios = simulated_dispatcher.load_scenario_corpus()
    selected_ids = scenario_ids or sorted(scenarios)
    if progress_jsonl is not None and progress_jsonl.exists():
        progress_jsonl.unlink()
    results = []
    total = len(selected_ids)
    for index, scenario_id in enumerate(selected_ids, start=1):
        result = evaluate_scenario(
            scenario_id,
            work_root,
            trigger_adapter=trigger_adapter,
            runtime_options=runtime_options,
            capture_adapter_errors=True,
        )
        results.append(result)
        append_progress(progress_jsonl, progress_event(result, index, total))
    report = {
        "report_type": "sidecar_baseline_hook_execution" if trigger_adapter == "sidecar-baseline" else "plugin_trigger_adapter_hook_execution",
        "trigger_adapter": trigger_adapter,
        "scenario_scope": "all" if scenario_ids is None else "selected",
        "summary": summarize_corpus_results(results, trigger_adapter),
    }
    if include_details:
        report["scenarios"] = results
    else:
        report["scenarios"] = [compact_scenario_result(result) for result in results]
    execution_passed = report["summary"]["passed_scenarios"] == report["summary"]["total_scenarios"]
    semantic_metrics = report["summary"]["semantic_metrics"]
    semantic_passed = (
        not semantic_metrics["ready_for_semantic_metrics"]
        if trigger_adapter != "plugin-runtime-codex-exec"
        else semantic_metrics["reported"] and semantic_metrics["passed"]
    )
    report["passed"] = execution_passed and semantic_passed
    return report


def evaluate_repeated_corpus(
    work_root: Path,
    repeat_runs: int,
    include_details: bool = False,
    trigger_adapter: str = "sidecar-baseline",
    runtime_options: plugin_trigger_adapters.RuntimeAdapterOptions | None = None,
    progress_jsonl: Path | None = None,
) -> dict[str, Any]:
    if repeat_runs < 1:
        raise HarnessError("--repeat-runs must be at least 1")
    reports = [
        evaluate_corpus(
            work_root / f"run-{run_index:03d}",
            include_details=include_details,
            trigger_adapter=trigger_adapter,
            runtime_options=runtime_options,
            progress_jsonl=(
                progress_jsonl.with_name(f"{progress_jsonl.stem}-run-{run_index:03d}{progress_jsonl.suffix}")
                if progress_jsonl is not None
                else None
            ),
        )
        for run_index in range(1, repeat_runs + 1)
    ]
    summary = {
        "run_count": repeat_runs,
        "passed_runs": sum(1 for report in reports if report["passed"]),
        "semantic_metrics_reported_runs": sum(
            1
            for report in reports
            if report["summary"]["semantic_metrics"].get("reported")
        ),
    }
    summary["stability"] = compute_repeated_runtime_stability(reports, trigger_adapter)
    return {
        "report_type": "repeated_hook_trigger_corpus",
        "trigger_adapter": trigger_adapter,
        "repeat_runs": repeat_runs,
        "summary": summary,
        "runs": reports,
        "passed": summary["passed_runs"] == repeat_runs,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--scenario-id", help="Scenario id from the trigger scenario corpus.")
    target.add_argument("--scenario-ids", type=parse_scenario_ids, help="Comma-separated scenario ids from the trigger scenario corpus.")
    target.add_argument("--all", action="store_true", help="Run every scenario in the trigger scenario corpus.")
    parser.add_argument("--work-root", type=Path, required=True, help="Directory where temporary fixture roots are created.")
    parser.add_argument("--trigger-adapter", choices=plugin_trigger_adapters.TRIGGER_ADAPTERS, default="sidecar-baseline", help="Plugin trigger adapter used to produce observed hook decisions.")
    parser.add_argument("--include-details", action="store_true", help="Include full hook stdout/stderr for corpus reports.")
    parser.add_argument("--repeat-runs", type=int, default=1, help="Run the full corpus repeatedly and aggregate stability.")
    parser.add_argument("--codex-bin", type=Path, default=plugin_trigger_adapters.CODEX_BIN, help="Codex CLI binary used by plugin-runtime-codex-exec.")
    parser.add_argument("--runtime-timeout", type=positive_int, default=60, help="Per-scenario Codex runtime timeout in seconds for plugin-runtime-codex-exec.")
    parser.add_argument("--auth-source-home", type=Path, help="Optional home directory whose .codex/auth.json is copied into each isolated plugin runtime HOME.")
    parser.add_argument("--expect-decision", choices=sorted(plugin_trigger_adapters.DECISIONS), help="Single-scenario smoke gate: require the observed trigger decision.")
    parser.add_argument("--expect-hooks", type=parse_expected_hooks, help="Single-scenario smoke gate: require an exact comma-separated hook id set. Use an empty string for no hooks.")
    parser.add_argument("--require-runtime-available", action="store_true", help="Single-scenario smoke gate: fail if the trigger decision is a runtime blocker.")
    parser.add_argument("--progress-jsonl", type=Path, help="Write one compact JSONL progress event after each evaluated scenario.")
    parser.add_argument("--report-json", type=Path, help="Write the final report JSON to a durable path in addition to stdout.")
    return parser


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    runtime_options = plugin_trigger_adapters.RuntimeAdapterOptions(
        codex_bin=args.codex_bin,
        timeout_seconds=args.runtime_timeout,
        auth_source_home=args.auth_source_home,
    )
    smoke_gate_requested = (
        args.expect_decision is not None
        or args.expect_hooks is not None
        or args.require_runtime_available
    )
    try:
        if args.all:
            if smoke_gate_requested:
                raise HarnessError("smoke expectation flags can only be used with --scenario-id")
            if args.repeat_runs > 1:
                result = evaluate_repeated_corpus(
                    args.work_root,
                    args.repeat_runs,
                    include_details=args.include_details,
                    trigger_adapter=args.trigger_adapter,
                    runtime_options=runtime_options,
                    progress_jsonl=args.progress_jsonl,
                )
            else:
                result = evaluate_corpus(
                    args.work_root,
                    include_details=args.include_details,
                    trigger_adapter=args.trigger_adapter,
                    runtime_options=runtime_options,
                    progress_jsonl=args.progress_jsonl,
                )
        elif args.scenario_ids:
            if args.repeat_runs != 1:
                raise HarnessError("--repeat-runs can only be used with --all")
            if smoke_gate_requested:
                raise HarnessError("smoke expectation flags can only be used with --scenario-id")
            result = evaluate_corpus(
                args.work_root,
                include_details=args.include_details,
                trigger_adapter=args.trigger_adapter,
                runtime_options=runtime_options,
                scenario_ids=args.scenario_ids,
                progress_jsonl=args.progress_jsonl,
            )
        else:
            if args.repeat_runs != 1:
                raise HarnessError("--repeat-runs can only be used with --all")
            result = evaluate_scenario(
                args.scenario_id,
                args.work_root,
                trigger_adapter=args.trigger_adapter,
                runtime_options=runtime_options,
            )
            result = apply_smoke_expectations(
                result,
                expected_decision=args.expect_decision,
                expected_hooks=args.expect_hooks,
                require_runtime_available=args.require_runtime_available,
            )
    except (HarnessError, eval_fixtures.FixtureError, plugin_trigger_adapters.AdapterError, simulated_dispatcher.DispatchError) as exc:
        parser.error(str(exc))
    write_report_json(args.report_json, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
