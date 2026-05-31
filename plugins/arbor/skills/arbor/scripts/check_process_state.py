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
import subprocess
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
    "absorbed",
    "superseded",
    "merged",
    "deferred",
}
OPEN_FEATURE_STATUSES = {"planned", "approved", "in_develop", "in_evaluate", "changes_requested"}
RECONCILED_FEATURE_STATUSES = {"absorbed", "superseded", "merged", "deferred"}
TARGETED_RECONCILED_FEATURE_STATUSES = {"absorbed", "superseded", "merged"}
TERMINAL_FEATURE_STATUSES = {"done", "blocked", *RECONCILED_FEATURE_STATUSES}

ROUND_PATTERNS = {
    "context": re.compile(r"^#+\s+.*Context/Test Plan\b", re.IGNORECASE | re.MULTILINE),
    "developer": re.compile(r"^#+\s+.*Developer Round\b", re.IGNORECASE | re.MULTILINE),
    "evaluator": re.compile(r"^#+\s+.*Evaluator Round\b", re.IGNORECASE | re.MULTILINE),
    "convergence": re.compile(r"^#+\s+.*Convergence Round\b", re.IGNORECASE | re.MULTILINE),
    "release": re.compile(r"^#+\s+.*Release Round\b", re.IGNORECASE | re.MULTILINE),
}
MARKDOWN_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
CHECKPOINT_RELEASE_RE = re.compile(
    r"\bcheckpoint[_ -]?(?:develop|evaluate)\b|\bdeveloper checkpoint\b|\bevaluator checkpoint\b",
    re.IGNORECASE,
)
COMMIT_HASH_RE = re.compile(r"\b[0-9a-f]{7,40}\b", re.IGNORECASE)
MISSING_COMMIT_RE = re.compile(
    r"\bno git commit\b|\bno commit was created\b|\bwithout commit\b|"
    r"\bcommit was not created\b|\bcould not\b.*\bcommit\b|\bcommit\b.*\bfailed\b",
    re.IGNORECASE,
)


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
    raw: dict[str, Any]


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


def git_commit_exists(root: Path, commit_hash: str) -> bool:
    if not (root / ".git").exists():
        return True
    proc = subprocess.run(
        ["git", "cat-file", "-e", f"{commit_hash}^{{commit}}"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return proc.returncode == 0


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
        if normalized in {
            "none",
            "n/a",
            "not applicable",
            "no unresolved state",
            "no active arbor resume context recorded yet.",
            "no undecided short-term observations recorded yet.",
        }:
            continue
        if normalized.startswith("stop hook fallback: dirty arbor worktree detected before stop"):
            continue
        meaningful.append(line)
    return bool(meaningful)


def worktree_has_uncommitted_state(root: Path) -> bool:
    proc = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        return False
    return bool(proc.stdout.strip())


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
            if status in RECONCILED_FEATURE_STATUSES:
                review_doc_path = None
            else:
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

        rows.append(
            FeatureRow(
                feature_id=feature_id,
                title=title,
                status=status,
                review_doc_path=review_doc_path,
                index=index,
                raw=raw_feature,
            )
        )

    active = registry.get("active_feature_id")
    if active is not None:
        if not isinstance(active, str) or active not in seen_ids:
            add_finding(findings, "error", "invalid_active_feature", FEATURE_REGISTRY_PATH, "active_feature_id must reference an existing feature id.")
    return rows


def has_text_or_items(raw_feature: dict[str, Any], *keys: str) -> bool:
    for key in keys:
        value = raw_feature.get(key)
        if isinstance(value, str) and value.strip():
            return True
        if isinstance(value, list) and any(str(item).strip() for item in value):
            return True
    return False


def validate_feature_queue_state(registry: dict[str, Any] | None, features: list[FeatureRow], findings: list[Finding]) -> None:
    if registry is None or not features:
        return

    active = registry.get("active_feature_id")
    by_id = {feature.feature_id: feature for feature in features}
    active_feature = by_id.get(active) if isinstance(active, str) else None
    open_features = [feature for feature in features if feature.status in OPEN_FEATURE_STATUSES]
    if active_feature is not None and active_feature.status in TERMINAL_FEATURE_STATUSES and open_features:
        open_ids = ", ".join(feature.feature_id for feature in open_features[:5])
        add_finding(
            findings,
            "warning",
            "active_feature_terminal_with_open_queue",
            FEATURE_REGISTRY_PATH,
            f"active_feature_id points to terminal feature {active_feature.feature_id!r} while open queued feature(s) remain: {open_ids}.",
        )

    for feature in open_features:
        raw = feature.raw
        missing: list[str] = []
        if "priority" not in raw and "order" not in raw:
            missing.append("priority or order")
        dependencies = raw.get("depends_on", raw.get("dependencies"))
        if not isinstance(dependencies, list):
            missing.append("dependency list")
        if not has_text_or_items(raw, "acceptance_summary", "acceptance_criteria", "acceptance_refs"):
            missing.append("acceptance summary")
        if not has_text_or_items(raw, "test_scope_summary", "verification_scope", "test_plan_summary"):
            missing.append("test scope summary")
        if missing:
            add_finding(
                findings,
                "warning",
                "missing_queue_metadata",
                f"{FEATURE_REGISTRY_PATH}:features[{feature.index}]",
                f"Open feature {feature.feature_id} is missing queue metadata: {', '.join(missing)}.",
            )

    for feature in features:
        if feature.status not in RECONCILED_FEATURE_STATUSES:
            continue
        raw = feature.raw
        path_label = f"{FEATURE_REGISTRY_PATH}:features[{feature.index}]"
        target = raw.get("reconciled_by") or raw.get("absorbed_by") or raw.get("superseded_by") or raw.get("merged_into")
        if feature.status in TARGETED_RECONCILED_FEATURE_STATUSES:
            if not isinstance(target, str) or not target.strip():
                add_finding(
                    findings,
                    "error",
                    "missing_reconciliation_target",
                    path_label,
                    f"Reconciled feature {feature.feature_id} with status {feature.status} must identify the feature that replaced or absorbed it.",
                )
            elif target == feature.feature_id:
                add_finding(
                    findings,
                    "error",
                    "self_reconciliation_target",
                    path_label,
                    f"Reconciled feature {feature.feature_id} cannot point to itself.",
                )
            elif target not in by_id:
                add_finding(
                    findings,
                    "error",
                    "invalid_reconciliation_target",
                    path_label,
                    f"Reconciled feature {feature.feature_id} points to unknown feature {target!r}.",
                )
        if feature.status == "deferred" and not has_text_or_items(raw, "deferred_reason", "reconciliation_reason", "reason"):
            add_finding(
                findings,
                "error",
                "missing_deferred_reason",
                path_label,
                f"Deferred feature {feature.feature_id} must record why it is not in the active queue.",
            )


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


def iter_release_sections(text: str) -> list[str]:
    headings = list(MARKDOWN_HEADING_RE.finditer(text))
    sections: list[str] = []
    for index, heading in enumerate(headings):
        title = heading.group(2)
        if not re.search(r"\bRelease Round\b", title, re.IGNORECASE):
            continue
        level = len(heading.group(1))
        end = len(text)
        for next_heading in headings[index + 1 :]:
            if len(next_heading.group(1)) <= level:
                end = next_heading.start()
                break
        sections.append(text[heading.start() : end])
    return sections


def validate_release_checkpoint_commit_evidence(root: Path, display_path: Path, text: str, findings: list[Finding]) -> None:
    for index, section in enumerate(iter_release_sections(text), start=1):
        if not CHECKPOINT_RELEASE_RE.search(section):
            continue
        if MISSING_COMMIT_RE.search(section):
            add_finding(
                findings,
                "error",
                "checkpoint_release_missing_commit",
                display_path,
                f"Release Round {index} describes a checkpoint but says no git commit was created.",
            )
            continue
        hashes = COMMIT_HASH_RE.findall(section)
        if not hashes:
            add_finding(
                findings,
                "error",
                "checkpoint_release_missing_commit_hash",
                display_path,
                f"Release Round {index} describes a checkpoint but does not include a commit hash.",
            )
            continue
        missing = [commit_hash for commit_hash in hashes if not git_commit_exists(root, commit_hash)]
        if missing:
            add_finding(
                findings,
                "error",
                "checkpoint_release_commit_not_in_history",
                display_path,
                f"Release Round {index} references commit hash(es) not found in git history: {', '.join(missing)}.",
            )


def validate_review_docs(
    root: Path,
    features: list[FeatureRow],
    findings: list[Finding],
    *,
    require_release_round_for_done: bool,
    require_checkpoint_commit_evidence: bool,
) -> None:
    checkpoint_docs_checked: set[Path] = set()
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
        if require_checkpoint_commit_evidence and resolved not in checkpoint_docs_checked:
            validate_release_checkpoint_commit_evidence(root, display_path, text, findings)
            checkpoint_docs_checked.add(resolved)


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

    if terminal_features and memory_path.exists() and memory_path.is_file() and not worktree_has_uncommitted_state(root):
        in_flight = extract_markdown_section(read_text(memory_path), "In-flight")
        if section_has_content(in_flight):
            add_finding(
                findings,
                "warning",
                "stale_memory_after_resolved_work",
                CANONICAL_MEMORY_PATH,
                "All registry features are terminal, but In-flight memory still contains unresolved-looking state.",
            )


def validate_process_state(
    root: Path,
    *,
    strict: bool = False,
    require_release_round_for_done: bool = False,
    require_checkpoint_commit_evidence: bool = False,
) -> ProcessStateReport:
    resolved = resolve_project_root(root)
    findings: list[Finding] = []
    managed = managed_state_exists(resolved)
    validate_project_guide(resolved, managed, findings)
    registry = load_registry(resolved, findings)
    features = validate_registry_rows(resolved, registry, findings)
    validate_feature_queue_state(registry, features, findings)
    validate_review_docs(
        resolved,
        features,
        findings,
        require_release_round_for_done=require_release_round_for_done,
        require_checkpoint_commit_evidence=require_checkpoint_commit_evidence,
    )
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
                        "priority": 1,
                        "depends_on": [],
                        "acceptance_summary": "Fixture acceptance.",
                        "test_scope_summary": "Fixture test scope.",
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
        "checkpoint_release_no_commit": "## Release Round 1\n\nMode: checkpoint_evaluate.\nNo git commit was created because the user did not request commit or push.\n",
        "checkpoint_release_with_hash": "## Release Round 1\n\nMode: checkpoint_evaluate.\nCheckpoint commit: abc1234.\n",
        "release_preamble_before_checkpoint": "# Release Skill Review\n\n| Custom commit-safety mutation replay | Failed |\n\n## Release Round 1\n\nMode: checkpoint_develop.\nCheckpoint commit: abc1234.\n",
        "checkpoint_release_subheading_hash": "## Release Round 1\n\n### Checkpoint Status\n\n| Field | Value |\n| --- | --- |\n| Release mode | `checkpoint_evaluate` |\n| Checkpoint commit | `abc1234` |\n",
        "checkpoint_release_nested_level_hash": "# Feature Review\n\n## Parent Section\n\n### Release Round 1\n\n#### Checkpoint Status\n\n| Field | Value |\n| --- | --- |\n| Release mode | `checkpoint_evaluate` |\n| Checkpoint commit | `abc1234` |\n",
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

        absorbed_valid = base / "absorbed-valid"
        absorbed_valid.mkdir()
        seed_project(absorbed_valid, memory="None\n")
        write(
            absorbed_valid / ".arbor/workflow/features.json",
            json.dumps(
                {
                    "active_feature_id": "pilot",
                    "features": [
                        {
                            "id": "old-skeleton",
                            "title": "Old skeleton",
                            "status": "absorbed",
                            "reconciled_by": "pilot",
                            "reconciliation_reason": "The pilot feature covers the skeleton scope.",
                            "priority": 1,
                            "depends_on": [],
                        },
                        {
                            "id": "pilot",
                            "title": "Pilot feature",
                            "status": "done",
                            "review_doc_path": "docs/review/pilot.md",
                            "priority": 2,
                            "depends_on": [],
                            "acceptance_summary": "Pilot acceptance.",
                            "test_scope_summary": "Pilot test scope.",
                        },
                    ],
                },
                indent=2,
            ),
        )
        write(
            absorbed_valid / "docs/review/pilot.md",
            """
            ## Context/Test Plan
            Acceptance criteria.
            ## Developer Round 1
            Developer evidence.
            ## Evaluator Round 1
            Evaluator evidence.
            ## Convergence Round 1
            Converged.
            ## Release Round 1
            Finalized.
            """,
        )
        expect_report("absorbed feature with valid target", validate_process_state(absorbed_valid), status="pass")

        absorbed_missing_target = base / "absorbed-missing-target"
        absorbed_missing_target.mkdir()
        seed_project(absorbed_missing_target, memory="None\n")
        write(
            absorbed_missing_target / ".arbor/workflow/features.json",
            json.dumps(
                {
                    "active_feature_id": "old-skeleton",
                    "features": [
                        {
                            "id": "old-skeleton",
                            "title": "Old skeleton",
                            "status": "absorbed",
                            "reconciled_by": "missing-pilot",
                            "reconciliation_reason": "Fixture missing target.",
                        }
                    ],
                },
                indent=2,
            ),
        )
        expect_report(
            "absorbed feature missing target",
            validate_process_state(absorbed_missing_target),
            status="fail",
            code="invalid_reconciliation_target",
        )

        deferred_missing_reason = base / "deferred-missing-reason"
        deferred_missing_reason.mkdir()
        seed_project(deferred_missing_reason, memory="None\n")
        write(
            deferred_missing_reason / ".arbor/workflow/features.json",
            json.dumps(
                {
                    "active_feature_id": "later",
                    "features": [
                        {
                            "id": "later",
                            "title": "Later feature",
                            "status": "deferred",
                        }
                    ],
                },
                indent=2,
            ),
        )
        expect_report(
            "deferred feature missing reason",
            validate_process_state(deferred_missing_reason),
            status="fail",
            code="missing_deferred_reason",
        )

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

        checkpoint_gap = base / "checkpoint-gap"
        checkpoint_gap.mkdir()
        seed_project(checkpoint_gap)
        seed_registry(checkpoint_gap, "done")
        seed_review_doc(
            checkpoint_gap,
            "context",
            "developer",
            "evaluator",
            "convergence",
            "checkpoint_release_no_commit",
        )
        expect_report(
            "checkpoint release without commit",
            validate_process_state(checkpoint_gap, require_checkpoint_commit_evidence=True),
            status="fail",
            code="checkpoint_release_missing_commit",
        )

        checkpoint_hash = base / "checkpoint-hash"
        checkpoint_hash.mkdir()
        seed_project(checkpoint_hash)
        seed_registry(checkpoint_hash, "done")
        seed_review_doc(
            checkpoint_hash,
            "context",
            "developer",
            "evaluator",
            "convergence",
            "checkpoint_release_with_hash",
        )
        expect_report(
            "checkpoint release with hash",
            validate_process_state(checkpoint_hash, require_checkpoint_commit_evidence=True),
            status="warn",
            code="stale_memory_after_resolved_work",
        )

        checkpoint_preamble = base / "checkpoint-preamble"
        checkpoint_preamble.mkdir()
        seed_project(checkpoint_preamble)
        seed_registry(checkpoint_preamble, "done")
        seed_review_doc(
            checkpoint_preamble,
            "context",
            "developer",
            "evaluator",
            "convergence",
            "release_preamble_before_checkpoint",
        )
        expect_report(
            "checkpoint release parser ignores preamble",
            validate_process_state(checkpoint_preamble, require_checkpoint_commit_evidence=True),
            status="warn",
            code="stale_memory_after_resolved_work",
        )

        checkpoint_subheading = base / "checkpoint-subheading"
        checkpoint_subheading.mkdir()
        seed_project(checkpoint_subheading)
        seed_registry(checkpoint_subheading, "done")
        seed_review_doc(
            checkpoint_subheading,
            "context",
            "developer",
            "evaluator",
            "convergence",
            "checkpoint_release_subheading_hash",
        )
        expect_report(
            "checkpoint release parser includes subheadings",
            validate_process_state(checkpoint_subheading, require_checkpoint_commit_evidence=True),
            status="warn",
            code="stale_memory_after_resolved_work",
        )

        checkpoint_nested = base / "checkpoint-nested"
        checkpoint_nested.mkdir()
        seed_project(checkpoint_nested)
        seed_registry(checkpoint_nested, "done")
        seed_review_doc(
            checkpoint_nested,
            "context",
            "developer",
            "evaluator",
            "convergence",
            "checkpoint_release_nested_level_hash",
        )
        expect_report(
            "checkpoint release parser handles nested heading levels",
            validate_process_state(checkpoint_nested, require_checkpoint_commit_evidence=True),
            status="warn",
            code="stale_memory_after_resolved_work",
        )

        active_done_with_queue = base / "active-done-with-queue"
        active_done_with_queue.mkdir()
        seed_project(active_done_with_queue)
        write(
            active_done_with_queue / ".arbor/workflow/features.json",
            json.dumps(
                {
                    "active_feature_id": "first",
                    "features": [
                        {
                            "id": "first",
                            "title": "First feature",
                            "status": "done",
                            "review_doc_path": "docs/review/first.md",
                            "priority": 1,
                            "depends_on": [],
                            "acceptance_summary": "First acceptance.",
                            "test_scope_summary": "First test scope.",
                        },
                        {
                            "id": "second",
                            "title": "Second feature",
                            "status": "planned",
                            "review_doc_path": "docs/review/second.md",
                            "priority": 2,
                            "depends_on": ["first"],
                            "acceptance_summary": "Second acceptance.",
                            "test_scope_summary": "Second test scope.",
                        },
                    ],
                },
                indent=2,
            ),
        )
        write(
            active_done_with_queue / "docs/review/first.md",
            """
            ## Context/Test Plan

            Acceptance criteria.

            ## Developer Round 1

            Developer evidence.

            ## Evaluator Round 1

            Evaluator evidence.

            ## Convergence Round 1

            Converged.

            ## Release Round 1

            Finalized.
            """,
        )
        write(active_done_with_queue / "docs/review/second.md", "## Context/Test Plan\n\nAcceptance criteria.\n")
        expect_report(
            "active terminal feature with open queue",
            validate_process_state(active_done_with_queue),
            status="warn",
            code="active_feature_terminal_with_open_queue",
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

    print("process state self-tests passed count=18")


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
    parser.add_argument(
        "--require-checkpoint-commit-evidence",
        action="store_true",
        help="Require checkpoint Release Rounds to include git commit evidence that exists in history.",
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
            require_checkpoint_commit_evidence=args.require_checkpoint_commit_evidence,
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
