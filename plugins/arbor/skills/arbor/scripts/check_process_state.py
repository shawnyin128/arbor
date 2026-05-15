#!/usr/bin/env python3
"""Validate Arbor process-state facts for a project root.

This checker is deliberately read-only. It validates workflow evidence and
state ownership without choosing implementation strategy, test design, or the
next engineering action for the agent.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import textwrap
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from arbor_project_state import (
    CANONICAL_MEMORY_PATH,
    PROJECT_GUIDE_PATH,
    ProjectStateError,
    resolve_project_root,
)


FEATURE_REGISTRY_PATH = Path(".arbor") / "workflow" / "features.json"
REVIEW_DOCS_DIR = Path("docs") / "review"
ALLOWED_FEATURE_STATUSES = {
    "planned",
    "approved",
    "in_develop",
    "in_evaluate",
    "changes_requested",
    "done",
    "blocked",
}
OPEN_FEATURE_STATUSES = {"planned", "approved", "in_develop", "in_evaluate", "changes_requested"}
TERMINAL_FEATURE_STATUSES = {"done", "blocked"}

ROUND_PATTERNS = {
    "context": re.compile(r"^#+\s+.*Context/Test Plan\b", re.IGNORECASE | re.MULTILINE),
    "developer": re.compile(r"^#+\s+.*Developer Round\b", re.IGNORECASE | re.MULTILINE),
    "evaluator": re.compile(r"^#+\s+.*Evaluator Round\b", re.IGNORECASE | re.MULTILINE),
    "convergence": re.compile(r"^#+\s+.*Convergence Round\b", re.IGNORECASE | re.MULTILINE),
    "release": re.compile(r"^#+\s+.*Release Round\b", re.IGNORECASE | re.MULTILINE),
}


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    path: str
    message: str


@dataclass(frozen=True)
class FeatureRow:
    feature_id: str
    title: str
    status: str
    review_doc_path: Path | None
    index: int


@dataclass(frozen=True)
class ProcessStateReport:
    schema_version: str
    root: str
    status: str
    summary: dict[str, int]
    findings: list[Finding]


def add_finding(findings: list[Finding], severity: str, code: str, path: Path | str, message: str) -> None:
    findings.append(Finding(severity=severity, code=code, path=str(path), message=message))


def relative_inside_root(root: Path, raw_path: str, *, base_path: Path = Path()) -> Path | None:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return None
    if ".." in candidate.parts:
        return None
    resolved = (root / base_path / candidate).resolve()
    if resolved != root and root not in resolved.parents:
        return None
    return resolved


def is_review_doc_path(raw_path: str) -> bool:
    candidate = Path(raw_path)
    return (
        len(candidate.parts) >= 3
        and candidate.parts[0] == "docs"
        and candidate.parts[1] == "review"
        and candidate.suffix == ".md"
    )


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def managed_state_exists(root: Path) -> bool:
    return any(
        (root / rel_path).exists()
        for rel_path in (
            PROJECT_GUIDE_PATH,
            CANONICAL_MEMORY_PATH,
            FEATURE_REGISTRY_PATH,
            REVIEW_DOCS_DIR,
            Path(".codex") / "hooks.json",
            Path("CLAUDE.md"),
        )
    )


def extract_markdown_section(text: str, heading: str) -> str:
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$", re.IGNORECASE | re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return ""
    start = match.end()
    next_heading = re.search(r"^##\s+", text[start:], re.MULTILINE)
    if not next_heading:
        return text[start:]
    return text[start : start + next_heading.start()]


def section_has_content(section: str) -> bool:
    meaningful = []
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        normalized = line.strip("-* ").lower()
        if normalized in {"none", "n/a", "not applicable", "no unresolved state"}:
            continue
        meaningful.append(line)
    return bool(meaningful)


def validate_project_guide(root: Path, managed: bool, findings: list[Finding]) -> None:
    path = root / PROJECT_GUIDE_PATH
    if not managed:
        add_finding(findings, "info", "direct_no_workflow_state", PROJECT_GUIDE_PATH, "No Arbor workflow state found.")
        return
    if not path.exists():
        add_finding(findings, "error", "missing_project_guide", PROJECT_GUIDE_PATH, "Managed Arbor state requires AGENTS.md as the project guide.")
        return
    if not path.is_file():
        add_finding(findings, "error", "project_guide_path_conflict", PROJECT_GUIDE_PATH, "AGENTS.md exists but is not a file.")
        return
    text = read_text(path)
    if "## Project Map" not in text:
        add_finding(findings, "warning", "missing_project_map", PROJECT_GUIDE_PATH, "AGENTS.md has no Project Map section for durable orientation.")


def load_registry(root: Path, findings: list[Finding]) -> dict[str, Any] | None:
    path = root / FEATURE_REGISTRY_PATH
    if not path.exists():
        add_finding(findings, "info", "missing_feature_registry", FEATURE_REGISTRY_PATH, "No feature registry found; no managed feature queue is validated.")
        return None
    if not path.is_file():
        add_finding(findings, "error", "feature_registry_path_conflict", FEATURE_REGISTRY_PATH, "Feature registry path exists but is not a file.")
        return None
    try:
        data = json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        add_finding(findings, "error", "invalid_feature_registry_json", FEATURE_REGISTRY_PATH, f"Feature registry is not valid JSON: {exc}.")
        return None
    if not isinstance(data, dict):
        add_finding(findings, "error", "invalid_feature_registry_shape", FEATURE_REGISTRY_PATH, "Feature registry must be a JSON object.")
        return None
    return data


def validate_registry_rows(root: Path, registry: dict[str, Any] | None, findings: list[Finding]) -> list[FeatureRow]:
    if registry is None:
        return []
    raw_features = registry.get("features")
    if not isinstance(raw_features, list):
        add_finding(findings, "error", "invalid_features_list", FEATURE_REGISTRY_PATH, "Feature registry must contain a features list.")
        return []

    rows: list[FeatureRow] = []
    seen_ids: set[str] = set()
    for index, raw_feature in enumerate(raw_features):
        path_label = f"{FEATURE_REGISTRY_PATH}:features[{index}]"
        if not isinstance(raw_feature, dict):
            add_finding(findings, "error", "invalid_feature_row", path_label, "Feature row must be an object.")
            continue

        feature_id = raw_feature.get("id")
        title = raw_feature.get("title") or raw_feature.get("name")
        status = raw_feature.get("status")
        review_doc_raw = raw_feature.get("review_doc_path")

        if not isinstance(feature_id, str) or not feature_id.strip():
            add_finding(findings, "error", "missing_feature_id", path_label, "Feature row must have a non-empty id.")
            feature_id = f"<invalid:{index}>"
        elif feature_id in seen_ids:
            add_finding(findings, "error", "duplicate_feature_id", path_label, f"Duplicate feature id: {feature_id}.")
        seen_ids.add(feature_id)

        if not isinstance(title, str) or not title.strip():
            add_finding(findings, "warning", "missing_feature_title", path_label, f"Feature {feature_id} has no readable title.")
            title = ""

        if status not in ALLOWED_FEATURE_STATUSES:
            add_finding(findings, "error", "invalid_feature_status", path_label, f"Feature {feature_id} has unsupported status: {status!r}.")
            status = str(status or "")

        review_doc_path: Path | None = None
        if not isinstance(review_doc_raw, str) or not review_doc_raw.strip():
            add_finding(findings, "error", "missing_review_doc_path", path_label, f"Feature {feature_id} has no review_doc_path.")
        else:
            resolved = relative_inside_root(root, review_doc_raw)
            if resolved is None:
                add_finding(findings, "error", "unsafe_review_doc_path", path_label, f"Feature {feature_id} review_doc_path must stay inside the project root.")
            elif not is_review_doc_path(review_doc_raw):
                add_finding(
                    findings,
                    "error",
                    "review_doc_path_outside_review_dir",
                    path_label,
                    f"Feature {feature_id} review_doc_path must point to docs/review/*.md.",
                )
            else:
                review_doc_path = Path(review_doc_raw)

        rows.append(FeatureRow(feature_id=feature_id, title=title, status=status, review_doc_path=review_doc_path, index=index))

    active = registry.get("active_feature_id")
    if active is not None:
        if not isinstance(active, str) or active not in seen_ids:
            add_finding(findings, "error", "invalid_active_feature", FEATURE_REGISTRY_PATH, "active_feature_id must reference an existing feature id.")
    return rows


def required_rounds_for_status(status: str) -> tuple[str, ...]:
    if status in {"planned", "approved", "in_develop", "blocked"}:
        return ("context",)
    if status == "in_evaluate":
        return ("context", "developer")
    if status == "changes_requested":
        return ("context", "developer", "evaluator")
    if status == "done":
        return ("context", "developer", "evaluator", "convergence")
    return ()


def validate_review_docs(root: Path, features: list[FeatureRow], findings: list[Finding], *, require_release_round_for_done: bool) -> None:
    for feature in features:
        if feature.review_doc_path is None:
            continue
        display_path = feature.review_doc_path
        resolved = relative_inside_root(root, str(display_path))
        if resolved is None:
            continue
        if not resolved.exists():
            add_finding(
                findings,
                "error",
                "missing_review_doc",
                display_path,
                f"Feature {feature.feature_id} points to a review document that does not exist.",
            )
            continue
        if not resolved.is_file():
            add_finding(findings, "error", "review_doc_path_conflict", display_path, "Review document path exists but is not a file.")
            continue

        text = read_text(resolved)
        for round_name in required_rounds_for_status(feature.status):
            if not ROUND_PATTERNS[round_name].search(text):
                severity = "warning" if feature.status == "done" and round_name == "convergence" else "error"
                add_finding(
                    findings,
                    severity,
                    f"missing_{round_name}_round",
                    display_path,
                    f"Feature {feature.feature_id} with status {feature.status} requires a {round_name.replace('_', ' ')} section.",
                )
        if feature.status == "done" and not ROUND_PATTERNS["release"].search(text):
            severity = "error" if require_release_round_for_done else "warning"
            add_finding(
                findings,
                severity,
                "missing_release_round",
                display_path,
                f"Feature {feature.feature_id} is done but has no Release Round evidence in the review document.",
            )


def validate_memory(root: Path, features: list[FeatureRow], findings: list[Finding]) -> None:
    if not features:
        return
    open_features = [feature for feature in features if feature.status in OPEN_FEATURE_STATUSES]
    terminal_features = [feature for feature in features if feature.status in TERMINAL_FEATURE_STATUSES]
    memory_path = root / CANONICAL_MEMORY_PATH

    if open_features:
        if not memory_path.exists():
            add_finding(findings, "error", "missing_memory_for_open_work", CANONICAL_MEMORY_PATH, "Open Arbor workflow state requires short-term memory.")
            return
        if not memory_path.is_file():
            add_finding(findings, "error", "memory_path_conflict", CANONICAL_MEMORY_PATH, "Memory path exists but is not a file.")
            return
        memory_text = read_text(memory_path)
        in_flight = extract_markdown_section(memory_text, "In-flight")
        if not section_has_content(in_flight):
            add_finding(
                findings,
                "error",
                "missing_in_flight_memory",
                CANONICAL_MEMORY_PATH,
                "Open Arbor workflow state requires a compact In-flight memory entry.",
            )
        return

    if terminal_features and memory_path.exists() and memory_path.is_file():
        in_flight = extract_markdown_section(read_text(memory_path), "In-flight")
        if section_has_content(in_flight):
            add_finding(
                findings,
                "warning",
                "stale_memory_after_resolved_work",
                CANONICAL_MEMORY_PATH,
                "All registry features are terminal, but In-flight memory still contains unresolved-looking state.",
            )


def validate_process_state(root: Path, *, strict: bool = False, require_release_round_for_done: bool = False) -> ProcessStateReport:
    resolved = resolve_project_root(root)
    findings: list[Finding] = []
    managed = managed_state_exists(resolved)
    validate_project_guide(resolved, managed, findings)
    registry = load_registry(resolved, findings)
    features = validate_registry_rows(resolved, registry, findings)
    validate_review_docs(resolved, features, findings, require_release_round_for_done=require_release_round_for_done)
    validate_memory(resolved, features, findings)

    errors = sum(1 for finding in findings if finding.severity == "error")
    warnings = sum(1 for finding in findings if finding.severity == "warning")
    infos = sum(1 for finding in findings if finding.severity == "info")
    status = "fail" if errors or (strict and warnings) else "warn" if warnings else "pass"
    return ProcessStateReport(
        schema_version="arbor_process_state.v1",
        root=str(resolved),
        status=status,
        summary={"errors": errors, "warnings": warnings, "infos": infos, "features": len(features)},
        findings=findings,
    )


def render_text(report: ProcessStateReport) -> str:
    lines = [
        "# Arbor Process State Check",
        "",
        f"Root: {report.root}",
        f"Status: {report.status}",
        (
            "Summary: "
            f"{report.summary['errors']} error(s), "
            f"{report.summary['warnings']} warning(s), "
            f"{report.summary['infos']} info item(s), "
            f"{report.summary['features']} feature row(s)"
        ),
        "",
    ]
    if not report.findings:
        lines.append("No findings.")
    else:
        for finding in report.findings:
            lines.append(f"- [{finding.severity}] {finding.code} ({finding.path}): {finding.message}")
    return "\n".join(lines).rstrip() + "\n"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")


def seed_project(root: Path, *, memory: str = "- Current task: fixture.\n") -> None:
    write(
        root / "AGENTS.md",
        """
        # Agent Guide

        ## Project Goal

        Fixture project.

        ## Project Constraints

        - Keep Arbor lightweight.

        ## Project Map

        - `src/`: source.
        """,
    )
    write(
        root / ".arbor/memory.md",
        f"""
        # Session Memory

        ## Observations

        - Fixture observation.

        ## In-flight

        {memory}
        """,
    )


def seed_registry(root: Path, status: str, review_doc_path: str = "docs/review/feature.md") -> None:
    write(
        root / ".arbor/workflow/features.json",
        json.dumps(
            {
                "active_feature_id": "feature",
                "features": [
                    {
                        "id": "feature",
                        "title": "Fixture feature",
                        "status": status,
                        "review_doc_path": review_doc_path,
                    }
                ],
            },
            indent=2,
        ),
    )


def seed_review_doc(root: Path, *rounds: str) -> None:
    labels = {
        "context": "## Context/Test Plan\n\nAcceptance criteria:\n- Fixture works.\n",
        "developer": "## Developer Round 1\n\nDeveloper evidence.\n",
        "evaluator": "## Evaluator Round 1\n\nEvaluator evidence.\n",
        "convergence": "## Convergence Round 1\n\nConverged.\n",
        "release": "## Release Round 1\n\nRelease evidence.\n",
    }
    write(root / "docs/review/feature.md", "\n".join(labels[name] for name in rounds))


def expect_report(name: str, report: ProcessStateReport, *, status: str, code: str | None = None) -> None:
    if report.status != status:
        raise AssertionError(f"{name}: expected status {status}, got {report.status}: {report.findings!r}")
    if code and not any(finding.code == code for finding in report.findings):
        raise AssertionError(f"{name}: expected finding {code}, got {[finding.code for finding in report.findings]}")


def run_self_tests() -> None:
    with tempfile.TemporaryDirectory(prefix="arbor-process-state-") as tmp:
        base = Path(tmp)

        direct = base / "direct"
        direct.mkdir()
        expect_report("direct no-op", validate_process_state(direct), status="pass", code="direct_no_workflow_state")

        valid = base / "valid"
        valid.mkdir()
        seed_project(valid)
        seed_registry(valid, "in_evaluate")
        seed_review_doc(valid, "context", "developer")
        expect_report("valid open workflow", validate_process_state(valid), status="pass")

        malformed = base / "malformed"
        malformed.mkdir()
        seed_project(malformed)
        write(malformed / ".arbor/workflow/features.json", '{"features": {}}')
        expect_report("malformed registry", validate_process_state(malformed), status="fail", code="invalid_features_list")

        missing_doc = base / "missing-doc"
        missing_doc.mkdir()
        seed_project(missing_doc)
        seed_registry(missing_doc, "approved")
        expect_report("missing review doc", validate_process_state(missing_doc), status="fail", code="missing_review_doc")

        missing_developer = base / "missing-developer"
        missing_developer.mkdir()
        seed_project(missing_developer)
        seed_registry(missing_developer, "in_evaluate")
        seed_review_doc(missing_developer, "context")
        expect_report("missing developer round", validate_process_state(missing_developer), status="fail", code="missing_developer_round")

        stale_memory = base / "stale-memory"
        stale_memory.mkdir()
        seed_project(stale_memory)
        seed_registry(stale_memory, "done")
        seed_review_doc(stale_memory, "context", "developer", "evaluator", "convergence", "release")
        expect_report("stale memory after done", validate_process_state(stale_memory), status="warn", code="stale_memory_after_resolved_work")

        release_gap = base / "release-gap"
        release_gap.mkdir()
        seed_project(release_gap, memory="- None.\n")
        seed_registry(release_gap, "done")
        seed_review_doc(release_gap, "context", "developer", "evaluator", "convergence")
        expect_report(
            "strict release evidence gap",
            validate_process_state(release_gap, require_release_round_for_done=True),
            status="fail",
            code="missing_release_round",
        )

        unsafe_path = base / "unsafe-path"
        unsafe_path.mkdir()
        seed_project(unsafe_path)
        seed_registry(unsafe_path, "approved", "../outside.md")
        expect_report("unsafe review path", validate_process_state(unsafe_path), status="fail", code="unsafe_review_doc_path")

        wrong_review_dir = base / "wrong-review-dir"
        wrong_review_dir.mkdir()
        seed_project(wrong_review_dir)
        seed_registry(wrong_review_dir, "approved", "notes/feature.md")
        write(wrong_review_dir / "notes/feature.md", "## Context/Test Plan\n\nAcceptance criteria.\n")
        expect_report(
            "wrong review directory",
            validate_process_state(wrong_review_dir),
            status="fail",
            code="review_doc_path_outside_review_dir",
        )

    print("process state self-tests passed count=9")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root to validate.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of readable text.")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as a non-zero check result.")
    parser.add_argument(
        "--require-release-round-for-done",
        action="store_true",
        help="Require done features to have Release Round evidence. Useful for release gates.",
    )
    parser.add_argument("--self-test", action="store_true", help="Run built-in regression fixtures.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.self_test:
        run_self_tests()
        return 0
    try:
        report = validate_process_state(
            args.root,
            strict=args.strict,
            require_release_round_for_done=args.require_release_round_for_done,
        )
    except ProjectStateError as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps(asdict(report), indent=2))
    else:
        print(render_text(report), end="")
    return 1 if report.status == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
