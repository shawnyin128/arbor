#!/usr/bin/env python3
"""Validate filled Arbor runtime smoke evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path


sys.dont_write_bytecode = True

REQUIRED_SECTIONS = (
    "## Hard Gate",
    "## Cache And Install State",
    "## Hook Runtime Smoke",
    "## Deterministic Substitute Evidence",
    "## Known Risks",
)
REQUIRED_AUDIT_FIELDS = ("Commit", "Date", "Operator")
PLACEHOLDER_VALUES = {"", "pending", "none", "n/a", "not applicable", "unknown"}
RELEASE_VERSION_PATTERN = re.compile(r"\d+\.\d+\.\d+")
REQUIRED_SUBSTITUTE_TERMS = (
    "Project wrapper execution with plugin-root env",
    "Project wrapper execution through fake Codex cache",
    "Project wrapper execution through fake Claude cache",
    "Multi-version cache selection with broken older adapter",
    "POSIX command rendering",
)
REQUIRED_SMOKE_MATRIX = (
    ("Codex", "Windows", "SessionStart"),
    ("Codex", "Windows", "Stop"),
    ("Claude Code", "Windows", "SessionStart"),
    ("Claude Code", "Windows", "Stop"),
    ("Codex", "macOS/Linux", "SessionStart"),
    ("Codex", "macOS/Linux", "Stop"),
    ("Claude Code", "macOS/Linux", "SessionStart"),
    ("Claude Code", "macOS/Linux", "Stop"),
)


def has_pending_placeholder(text: str) -> bool:
    return bool(re.search(r"(?i)\b(pending|YYYY-MM-DD)\b", text))


def section_text(text: str, heading: str) -> str:
    start = text.find(heading)
    if start == -1:
        return ""
    next_match = re.search(r"(?m)^##\s+", text[start + len(heading) :])
    if next_match is None:
        return text[start + len(heading) :]
    return text[start + len(heading) : start + len(heading) + next_match.start()]


def smoke_table_rows(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in section_text(text, "## Hook Runtime Smoke").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells or cells[0] in {"---", "Runtime"}:
            continue
        rows.append(cells)
    return rows


def cell_is_passing(value: str) -> bool:
    normalized = value.strip().lower()
    return normalized in {"yes", "pass", "passed", "ok", "ready"}


def cache_discovery_path_is_concrete(value: str) -> bool:
    normalized = value.strip()
    if normalized.lower() in {"", "pending", "not run", "none"}:
        return False
    return bool(
        re.match(r"^[A-Za-z]:[\\/]", normalized)
        or normalized.startswith("/")
        or normalized.startswith("\\\\")
    )


def evidence_version(text: str) -> str | None:
    match = re.search(r"(?im)^Version:\s*([^\s]+)\s*$", text)
    if match is None:
        return None
    return match.group(1).strip()


def metadata_value(text: str, label: str) -> str | None:
    match = re.search(rf"(?im)^{re.escape(label)}:\s*(.+?)\s*$", text)
    if match is None:
        return None
    value = match.group(1).strip()
    if not value:
        return None
    return value


def metadata_values(text: str, label: str) -> list[str]:
    return [match.group(1).strip() for match in re.finditer(rf"(?im)^{re.escape(label)}:\s*(.*?)\s*$", text)]


def section_count(text: str, heading: str) -> int:
    return len(re.findall(rf"(?m)^{re.escape(heading)}\s*$", text))


def commit_is_concrete(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F]{7,40}", value.strip()))


def date_is_iso_day(value: str) -> bool:
    raw = value.strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return False
    try:
        dt.date.fromisoformat(raw)
    except ValueError:
        return False
    return True


def operator_is_concrete(value: str) -> bool:
    return value.strip().lower().rstrip(".") not in PLACEHOLDER_VALUES


def path_has_version_segment(path_text: str, version: str) -> bool:
    segments = [segment for segment in re.split(r"[\\/]+", path_text.strip()) if segment]
    return version in segments


def smoke_row_has_unresolved_risk(cells: list[str]) -> bool:
    if len(cells) < 9:
        return True
    trusted = cells[3].strip().lower()
    fired = cells[4].strip().lower()
    absolute_python = cells[5].strip().lower()
    unavailable = cells[8].strip().lower()
    if "not run" in fired or unavailable not in {"", "none", "n/a", "not applicable"}:
        return True
    return not (cell_is_passing(trusted) and cell_is_passing(fired) and cell_is_passing(absolute_python))


def smoke_row_key(cells: list[str]) -> tuple[str, str, str] | None:
    if len(cells) < 3:
        return None
    return cells[0].strip(), cells[1].strip(), cells[2].strip()


def risks_are_none(risk_lines: list[str]) -> bool:
    normalized = [line.strip().lstrip("-* ").strip().lower().rstrip(".") for line in risk_lines]
    return bool(normalized) and all(line == "none" for line in normalized)


def risks_mix_none_with_explicit_risks(risk_lines: list[str]) -> bool:
    normalized = [line.strip().lstrip("-* ").strip().lower().rstrip(".") for line in risk_lines]
    return "none" in normalized and any(line != "none" for line in normalized)


def status_after_colon(line: str) -> str:
    if ":" not in line:
        return ""
    return line.rsplit(":", 1)[1].strip()


def install_state_strict_lines(cache_state: str) -> list[str]:
    lines: list[str] = []
    for raw_line in cache_state.splitlines():
        line = raw_line.strip()
        lowered = line.lower()
        if not line.startswith("-"):
            continue
        if "check_install_state.py" in line and "--strict" in line:
            lines.append(line)
            continue
        if "single-runtime install checks" in lowered:
            lines.append(line)
    return lines


def install_state_strict_checks_pass(cache_state: str) -> bool:
    lines = install_state_strict_lines(cache_state)
    if not lines:
        return False
    return all(cell_is_passing(status_after_colon(line)) for line in lines)


def cache_state_line_status(cache_state: str, label: str) -> str | None:
    label_lower = label.lower()
    for raw_line in cache_state.splitlines():
        line = raw_line.strip()
        if not line.startswith("-"):
            continue
        if label_lower in line.lower():
            return status_after_colon(line).lower()
    return None


def cell_is_negative(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower().rstrip(".") in {"no", "none", "false", "absent", "not present"}


def section_line_status(section: str, label: str) -> str | None:
    label_lower = label.lower()
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line.startswith("-"):
            continue
        if label_lower in line.lower():
            return status_after_colon(line)
    return None


def command_line_status(section: str, command_name: str) -> str | None:
    command_lower = command_name.lower()
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line.startswith("-"):
            continue
        if command_lower in line.lower():
            return status_after_colon(line)
    return None


def validate_evidence(path: Path) -> list[str]:
    failures: list[str] = []
    text = path.read_text(encoding="utf-8")
    version_values = metadata_values(text, "Version")
    version = version_values[0] if version_values and version_values[0] else None
    if len(version_values) != 1:
        failures.append("runtime smoke evidence must include exactly one Version")
    if version is None:
        failures.append("runtime smoke evidence must include a concrete Version")
    elif RELEASE_VERSION_PATTERN.fullmatch(version) is None:
        failures.append("runtime smoke evidence Version must be a release version like X.Y.Z")
    for metadata_label in REQUIRED_AUDIT_FIELDS:
        values = metadata_values(text, metadata_label)
        value = values[0] if values and values[0] else None
        if len(values) != 1:
            failures.append(f"runtime smoke evidence must include exactly one {metadata_label}")
        if value is None:
            failures.append(f"runtime smoke evidence must include a concrete {metadata_label}")
        elif metadata_label == "Commit" and not commit_is_concrete(value):
            failures.append("runtime smoke evidence Commit must be a concrete git commit")
        elif metadata_label == "Date" and not date_is_iso_day(value):
            failures.append("runtime smoke evidence Date must use YYYY-MM-DD")
        elif metadata_label == "Operator" and not operator_is_concrete(value):
            failures.append("runtime smoke evidence Operator must identify the operator")

    for section in REQUIRED_SECTIONS:
        count = section_count(text, section)
        if count == 0:
            failures.append(f"missing required section: {section}")
        elif count != 1:
            failures.append(f"runtime smoke evidence must include exactly one {section} section")

    if has_pending_placeholder(text):
        failures.append("evidence still contains pending/template placeholders")

    hard_gate = section_text(text, "## Hard Gate")
    quality_gate_status = command_line_status(hard_gate, "check_quality_gate.py")
    if quality_gate_status is None or not cell_is_passing(quality_gate_status):
        failures.append("Hard Gate section must record passing quality gate evidence")
    self_validation_status = command_line_status(hard_gate, "check_runtime_smoke_evidence.py")
    if self_validation_status is None or not cell_is_passing(self_validation_status):
        failures.append("Hard Gate section must record passing runtime smoke self-validation")
    result_match = re.search(r"(?im)^-\s*Result:\s*([a-z_]+)\b", hard_gate)
    if result_match is None:
        failures.append("Hard Gate section must include a concrete Result")
    elif result_match.group(1).lower() == "blocked":
        failures.append("Hard Gate section must not be blocked")
    elif result_match.group(1).lower() not in {"pass", "accepted"}:
        failures.append("Hard Gate section Result must be pass or accepted")

    cache_state = section_text(text, "## Cache And Install State")
    if "check_install_state.py" not in cache_state or "--strict" not in cache_state:
        failures.append("Cache And Install State must record strict install-state command evidence")
    elif not install_state_strict_checks_pass(cache_state):
        failures.append("Cache And Install State strict checks must pass")
    dirty_sync = cache_state_line_status(cache_state, "Dirty source sync guard")
    if dirty_sync is None:
        failures.append("Cache And Install State must record dirty source sync guard evidence")
    elif not cell_is_passing(dirty_sync):
        failures.append("Cache And Install State dirty source sync guard must pass")
    dirty_strict = cache_state_line_status(cache_state, "Dirty source strict guard")
    if dirty_strict is None:
        failures.append("Cache And Install State must record dirty source strict guard evidence")
    elif not cell_is_passing(dirty_strict):
        failures.append("Cache And Install State dirty source strict guard must pass")
    if not cell_is_negative(cache_state_line_status(cache_state, "Legacy plugin-level `hooks/hooks.json` present")):
        failures.append("Cache And Install State must report no legacy plugin-level hook manifests")
    if not cell_is_negative(cache_state_line_status(cache_state, "`__pycache__` / `*.pyc` present in synced cache")):
        failures.append("Cache And Install State must report no transient cache artifacts")

    rows = smoke_table_rows(text)
    if not rows:
        failures.append("Hook Runtime Smoke must include at least one evidence table row")
    required_smoke_keys = set(REQUIRED_SMOKE_MATRIX)
    smoke_key_counts: dict[tuple[str, str, str], int] = {}
    for row in rows:
        key = smoke_row_key(row)
        if key is None:
            continue
        smoke_key_counts[key] = smoke_key_counts.get(key, 0) + 1
    present_smoke_keys = set(smoke_key_counts)
    for runtime, os_name, event in REQUIRED_SMOKE_MATRIX:
        if (runtime, os_name, event) not in present_smoke_keys:
            failures.append(f"Hook Runtime Smoke must include {runtime} {os_name} {event} evidence")
        elif smoke_key_counts[(runtime, os_name, event)] != 1:
            failures.append(f"Hook Runtime Smoke must include exactly one {runtime} {os_name} {event} evidence row")
    for runtime, os_name, event in sorted(present_smoke_keys - required_smoke_keys):
        failures.append(f"Hook Runtime Smoke contains unexpected {runtime} {os_name} {event} evidence")
    for index, cells in enumerate(rows, start=1):
        if len(cells) < 9:
            failures.append(f"Hook Runtime Smoke row {index} must include all evidence columns")
            continue
        trusted = cells[3].lower()
        fired = cells[4].lower()
        absolute_python = cells[5].lower()
        cache_path = cells[6].strip()
        cache_path_lower = cache_path.lower()
        evidence = cells[7].lower()
        unavailable = cells[8].lower()
        fired_is_passing = cell_is_passing(fired)
        fired_is_not_run = "not run" in fired
        if not fired_is_passing and not fired_is_not_run:
            failures.append(f"Hook Runtime Smoke row {index} Fired must be a passing marker or not run")
        if fired_is_passing and not cell_is_passing(trusted):
            failures.append(f"Hook Runtime Smoke row {index} fired but is not trusted")
        if fired_is_passing and not cell_is_passing(absolute_python):
            failures.append(f"Hook Runtime Smoke row {index} fired but wrapper command does not use absolute Python")
        if fired_is_passing and cache_path_lower in {"", "pending", "not run", "none"}:
            failures.append(f"Hook Runtime Smoke row {index} fired but lacks concrete cache discovery path")
        elif fired_is_passing and not cache_discovery_path_is_concrete(cache_path):
            failures.append(f"Hook Runtime Smoke row {index} fired but lacks absolute cache discovery path")
        elif fired_is_passing and version and not path_has_version_segment(cache_path, version):
            failures.append(f"Hook Runtime Smoke row {index} cache discovery path does not match evidence Version {version}")
        if fired_is_passing and evidence in {"", "pending", "not run", "none", "n/a", "not applicable"}:
            failures.append(f"Hook Runtime Smoke row {index} fired but lacks concrete evidence")
        if fired_is_passing and unavailable not in {"", "none", "n/a", "not applicable"}:
            failures.append(f"Hook Runtime Smoke row {index} fired but still has an unavailable reason")
        if fired_is_not_run and unavailable in {"", "pending", "none", "n/a", "not applicable"}:
            failures.append(f"Hook Runtime Smoke row {index} was not run but lacks a concrete unavailable reason")

    substitutes = section_text(text, "## Deterministic Substitute Evidence")
    substitute_failed = False
    for term in REQUIRED_SUBSTITUTE_TERMS:
        status = section_line_status(substitutes, term)
        if status is None:
            failures.append(f"Deterministic Substitute Evidence missing {term!r}")
            substitute_failed = True
        elif not cell_is_passing(status):
            substitute_failed = True
    if substitute_failed and not any(failure.startswith("Deterministic Substitute Evidence missing") for failure in failures):
        failures.append("Deterministic Substitute Evidence checks must pass")

    known_risks = section_text(text, "## Known Risks")
    risk_lines = [line for line in known_risks.splitlines() if line.strip().startswith("-")]
    if not risk_lines:
        failures.append("Known Risks must include at least one explicit risk or '- none'")
    elif risks_mix_none_with_explicit_risks(risk_lines):
        failures.append("Known Risks cannot mix none with explicit risks")
    elif risks_are_none(risk_lines) and any(smoke_row_has_unresolved_risk(cells) for cells in rows):
        failures.append("Known Risks cannot be none when runtime smoke rows are not fully passing")

    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path, help="Filled runtime smoke evidence markdown file.")
    args = parser.parse_args(argv)

    try:
        failures = validate_evidence(args.evidence)
    except (OSError, UnicodeError) as exc:
        print(f"runtime smoke evidence check failed: {exc}", file=sys.stderr)
        return 1

    if failures:
        print("runtime smoke evidence check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("runtime smoke evidence check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
