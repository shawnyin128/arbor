#!/usr/bin/env python3
"""Sidecar-backed simulated dispatcher for Arbor hook trigger evaluation."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MARKDOWN = ROOT / "docs" / "reviews" / "hook-trigger-scenarios.md"
DEFAULT_SIDECAR = ROOT / "docs" / "reviews" / "hook-trigger-scenarios.json"

DECISIONS = {"trigger", "none", "ambiguous"}
CONFIDENCE = {"high", "medium", "low"}


class DispatchError(ValueError):
    """Raised when a scenario cannot be dispatched cleanly."""


@dataclass(frozen=True)
class TriggerScenario:
    scenario_id: str
    expression: str
    expected_label: str
    note: str
    expectation: dict[str, Any]


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise DispatchError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise DispatchError(f"cannot parse {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise DispatchError(f"expected JSON object in {path}")
    return data


def parse_trigger_scenario_markdown(path: Path) -> dict[str, dict[str, str]]:
    row_pattern = re.compile(r"^\| ([A-Z0-9]+-P\d{3}) \| (.*?) \| (H1|H2|H3|NONE|MULTI) \| (.*?) \|$")
    scenarios: dict[str, dict[str, str]] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise DispatchError(f"cannot read {path}: {exc}") from exc

    for line in lines:
        match = row_pattern.match(line)
        if not match:
            continue
        scenario_id, expression, expected_label, note = match.groups()
        if expression.startswith('"') and expression.endswith('"'):
            expression = expression[1:-1]
        scenarios[scenario_id] = {
            "expression": expression,
            "expected_label": expected_label,
            "note": note,
        }
    return scenarios


def expanded_expectation(sidecar: dict[str, Any], scenario_id: str, expected_label: str) -> dict[str, Any]:
    defaults = sidecar.get("default_expectations", {})
    if expected_label not in defaults:
        raise DispatchError(f"missing default expectation for label: {expected_label}")
    expectation = dict(defaults[expected_label])
    expectation.update(sidecar.get("overrides", {}).get(scenario_id, {}))
    return expectation


def load_scenario_corpus(
    markdown_path: Path = DEFAULT_MARKDOWN,
    sidecar_path: Path = DEFAULT_SIDECAR,
) -> dict[str, TriggerScenario]:
    markdown = parse_trigger_scenario_markdown(markdown_path)
    sidecar = load_json(sidecar_path)
    scenarios: dict[str, TriggerScenario] = {}
    for scenario_id, scenario in markdown.items():
        expectation = expanded_expectation(sidecar, scenario_id, scenario["expected_label"])
        scenarios[scenario_id] = TriggerScenario(
            scenario_id=scenario_id,
            expression=scenario["expression"],
            expected_label=scenario["expected_label"],
            note=scenario["note"],
            expectation=expectation,
        )
    return scenarios


def select_decision(expectation: dict[str, Any]) -> str:
    allowed = expectation["allowed_decisions"]
    if expectation["expected_hooks"]:
        return "trigger"
    if allowed == ["none"]:
        return "none"
    if expectation["requires_agent_judgment"] and "ambiguous" in allowed:
        return "ambiguous"
    if "none" in allowed:
        return "none"
    if "ambiguous" in allowed:
        return "ambiguous"
    return "trigger"


def select_hooks(decision: str, expectation: dict[str, Any]) -> list[str]:
    if decision != "trigger":
        return []
    if expectation["expected_hooks"]:
        return list(expectation["expected_hooks"])
    return list(expectation["optional_expected_hooks"])


def resolve_optional_args(args: list[str], fixture_summary: dict[str, Any] | None) -> list[str]:
    resolved: list[str] = []
    for arg in args:
        if arg.startswith("/outside/") and fixture_summary and fixture_summary.get("outside_path"):
            resolved.append(str(fixture_summary["outside_path"]))
        else:
            resolved.append(arg)
    return resolved


def select_optional_args(
    hooks: list[str],
    expectation: dict[str, Any],
    fixture_summary: dict[str, Any] | None = None,
) -> dict[str, list[str]]:
    configured = expectation.get("optional_args", {})
    return {
        hook_id: resolve_optional_args(list(configured[hook_id]), fixture_summary)
        for hook_id in hooks
        if hook_id in configured
    }


def select_confidence(decision: str, expectation: dict[str, Any]) -> str:
    if decision == "ambiguous":
        return "low"
    if expectation["requires_agent_judgment"]:
        return "medium"
    return "high"


def simulate_dispatch(
    scenario: TriggerScenario,
    fixture_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    expectation = scenario.expectation
    decision = select_decision(expectation)
    hooks = select_hooks(decision, expectation)
    optional_args = select_optional_args(hooks, expectation, fixture_summary)
    confidence = select_confidence(decision, expectation)

    if decision not in expectation["allowed_decisions"]:
        raise DispatchError(f"simulated decision {decision} is not allowed for {scenario.scenario_id}")
    forbidden = set(expectation["forbidden_hooks"])
    selected = set(hooks)
    if selected & forbidden:
        raise DispatchError(f"simulated hooks conflict with forbidden hooks for {scenario.scenario_id}")

    return {
        "hooks": hooks,
        "decision": decision,
        "confidence": confidence,
        "requires_agent_judgment": bool(expectation["requires_agent_judgment"] or decision == "ambiguous"),
        "optional_args": optional_args,
        "reason": (
            f"Sidecar-backed simulated dispatch for {scenario.scenario_id} "
            f"({scenario.expected_label}): {scenario.note}"
        ),
    }


def dispatch_scenario(
    scenario_id: str,
    markdown_path: Path = DEFAULT_MARKDOWN,
    sidecar_path: Path = DEFAULT_SIDECAR,
    fixture_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    scenarios = load_scenario_corpus(markdown_path, sidecar_path)
    if scenario_id not in scenarios:
        raise DispatchError(f"unknown scenario id: {scenario_id}")
    return simulate_dispatch(scenarios[scenario_id], fixture_summary)


def load_fixture_summary(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    return load_json(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario-id", required=True, help="Scenario id from the trigger scenario corpus.")
    parser.add_argument("--scenarios", type=Path, default=DEFAULT_MARKDOWN, help="Markdown scenario corpus path.")
    parser.add_argument("--sidecar", type=Path, default=DEFAULT_SIDECAR, help="JSON scenario sidecar path.")
    parser.add_argument("--fixture-summary", type=Path, help="Optional JSON summary emitted by eval_fixtures.py.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        fixture_summary = load_fixture_summary(args.fixture_summary)
        result = dispatch_scenario(args.scenario_id, args.scenarios, args.sidecar, fixture_summary)
    except DispatchError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
