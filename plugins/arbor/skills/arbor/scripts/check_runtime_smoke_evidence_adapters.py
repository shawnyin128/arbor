#!/usr/bin/env python3
"""Validate Arbor's runtime-smoke evidence checker."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True


PLUGIN_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = PLUGIN_ROOT.parents[1]
SCRIPTS_ROOT = PLUGIN_ROOT / "skills" / "arbor" / "scripts"
REFERENCES_ROOT = PLUGIN_ROOT / "skills" / "arbor" / "references"


def add_error(errors: list[str], message: str) -> None:
    errors.append(message)


def check(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        add_error(errors, message)


def bytecode_suppressed_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def run_command_status(command: list[str]) -> tuple[int, str]:
    try:
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=bytecode_suppressed_env(),
            timeout=60,
            check=False,
        )
    except OSError as exc:
        return 127, f"command failed to start: {' '.join(command)}: {exc}\n"
    except subprocess.TimeoutExpired as exc:
        return 124, f"command timed out: {' '.join(command)}: {exc}\n"
    return result.returncode, result.stdout or ""


def complete_runtime_smoke_evidence() -> str:
    return (
        "# Arbor Runtime Smoke Evidence\n\n"
        "Version: 2.0.0\n"
        "Commit: 0123456\n"
        "Date: 2026-06-12\n"
        "Operator: Arbor Check\n\n"
        "## Hard Gate\n\n"
        "- `python3 plugins/arbor/skills/arbor/scripts/check_quality_gate.py`: pass\n"
        "- `python3 plugins/arbor/skills/arbor/scripts/check_runtime_smoke_evidence.py <this-file>`: pass\n"
        "- Result: pass\n"
        "- Accepted caveats: Codex /hooks trust not proven from files\n\n"
        "## Cache And Install State\n\n"
        "- `python3 plugins/arbor/skills/arbor/scripts/check_install_state.py --strict`: pass\n"
        "- Single-runtime install checks (`--runtime codex|claude|both`): pass\n"
        "- Codex cache path: C:/Users/example/.codex/plugins/cache/arbor/arbor/2.0.0\n"
        "- Claude cache path: not run - Claude Code unavailable on this machine\n"
        "- Cache version selected by project wrapper: 2.0.0\n"
        "- Dirty source sync guard: pass\n"
        "- Dirty source strict guard: pass\n"
        "- Legacy plugin-level `hooks/hooks.json` present: no\n"
        "- `__pycache__` / `*.pyc` present in synced cache: no\n\n"
        "## Deterministic Substitute Evidence\n\n"
        "- Project wrapper execution with plugin-root env: pass\n"
        "- Project wrapper execution through fake Codex cache: pass\n"
        "- Project wrapper execution through fake Claude cache: pass\n"
        "- Multi-version cache selection with broken older adapter: pass\n"
        "- POSIX command rendering: pass\n\n"
        "## Hook Runtime Smoke\n\n"
        "| Runtime | Platform | Event | Trusted | Fired | Wrapper or launcher uses absolute Python | Cache discovery path | Evidence | Unavailable reason |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
        "| Codex | Windows | SessionStart | yes | yes | yes | C:/Users/example/.codex/plugins/cache/arbor/arbor/2.0.0 | startup context rendered | none |\n"
        "| Codex | Windows | Stop | yes | yes | yes | C:/Users/example/.codex/plugins/cache/arbor/arbor/2.0.0 | memory hygiene completed | none |\n"
        "| Claude Code | Windows | SessionStart | not run | not run | yes | not run | not run | Claude Code unavailable on this machine |\n"
        "| Claude Code | Windows | Stop | not run | not run | yes | not run | not run | Claude Code unavailable on this machine |\n"
        "| Codex | macOS/Linux | SessionStart | not run | not run | yes | not run | not run | macOS/Linux runtime not available on this machine |\n"
        "| Codex | macOS/Linux | Stop | not run | not run | yes | not run | not run | macOS/Linux runtime not available on this machine |\n"
        "| Claude Code | macOS/Linux | SessionStart | not run | not run | yes | not run | not run | macOS/Linux runtime not available on this machine |\n"
        "| Claude Code | macOS/Linux | Stop | not run | not run | yes | not run | not run | macOS/Linux runtime not available on this machine |\n\n"
        "## Known Risks\n\n"
        "- Claude Code and macOS/Linux runtime smoke not run on this Windows machine.\n"
    )


def assert_evidence_case(
    errors: list[str],
    script: Path,
    root: Path,
    name: str,
    evidence: str | bytes,
    expected_code: int,
    expected_output: str,
    message: str,
) -> None:
    path = root / f"{name}.md"
    if isinstance(evidence, bytes):
        path.write_bytes(evidence)
    else:
        path.write_text(evidence, encoding="utf-8")
    code, output = run_command_status([sys.executable, str(script), str(path)])
    check(errors, code == expected_code, f"{message}: expected exit {expected_code}, got {code}\n{output}")
    check(errors, expected_output in output, f"{message}: expected output containing {expected_output!r}\n{output}")


def validate_runtime_smoke_evidence_checker(errors: list[str]) -> None:
    script = SCRIPTS_ROOT / "check_runtime_smoke_evidence.py"
    if not script.is_file():
        add_error(errors, "runtime smoke evidence checker must be published")
        return

    with tempfile.TemporaryDirectory(prefix="arbor-runtime-evidence-adapter-") as tmp:
        root = Path(tmp)
        template = REFERENCES_ROOT / "runtime-smoke-template.md"
        if not template.is_file():
            add_error(errors, "runtime smoke evidence template must be published")
            return
        complete = complete_runtime_smoke_evidence()

        assert_evidence_case(
            errors,
            script,
            root,
            "pending",
            template.read_text(encoding="utf-8"),
            1,
            "pending",
            "runtime smoke evidence checker must reject pending template evidence",
        )
        assert_evidence_case(
            errors,
            script,
            root,
            "complete",
            complete,
            0,
            "runtime smoke evidence check passed",
            "runtime smoke evidence checker must accept filled evidence",
        )

        cases = [
            (
                "missing-version",
                complete.replace("Version: 2.0.0\n", ""),
                "runtime smoke evidence must include a concrete Version",
                "runtime smoke evidence checker must reject evidence without a version",
            ),
            (
                "duplicate-version",
                complete.replace("Version: 2.0.0\n", "Version: 2.0.0\nVersion: 2.0.0\n"),
                "runtime smoke evidence must include exactly one Version",
                "runtime smoke evidence checker must reject duplicate Version metadata",
            ),
            (
                "invalid-commit",
                complete.replace("Commit: 0123456", "Commit: pending"),
                "runtime smoke evidence Commit must be a concrete git commit",
                "runtime smoke evidence checker must reject invalid Commit metadata",
            ),
            (
                "invalid-date",
                complete.replace("Date: 2026-06-12", "Date: June 12"),
                "runtime smoke evidence Date must use YYYY-MM-DD",
                "runtime smoke evidence checker must reject invalid Date metadata",
            ),
            (
                "vague-operator",
                complete.replace("Operator: Arbor Check", "Operator: n/a"),
                "runtime smoke evidence Operator must identify the operator",
                "runtime smoke evidence checker must reject vague Operator metadata",
            ),
            (
                "duplicate-known-risks",
                complete.replace(
                    "## Known Risks\n\n- Claude Code and macOS/Linux runtime smoke not run on this Windows machine.\n",
                    "## Known Risks\n\n- Claude Code and macOS/Linux runtime smoke not run on this Windows machine.\n\n## Known Risks\n\n- Duplicate section should be rejected.\n",
                ),
                "runtime smoke evidence must include exactly one ## Known Risks section",
                "runtime smoke evidence checker must reject duplicate required sections",
            ),
            (
                "missing-self-validation",
                complete.replace(
                    "- `python3 plugins/arbor/skills/arbor/scripts/check_runtime_smoke_evidence.py <this-file>`: pass\n",
                    "",
                ),
                "Hard Gate section must record passing runtime smoke self-validation",
                "runtime smoke evidence checker must reject missing self-validation evidence",
            ),
            (
                "failed-quality-gate",
                complete.replace(
                    "- `python3 plugins/arbor/skills/arbor/scripts/check_quality_gate.py`: pass",
                    "- `python3 plugins/arbor/skills/arbor/scripts/check_quality_gate.py`: fail",
                ),
                "Hard Gate section must record passing quality gate evidence",
                "runtime smoke evidence checker must reject failed quality gate evidence",
            ),
            (
                "blocked-hard-gate",
                complete.replace("- Result: pass", "- Result: blocked"),
                "Hard Gate section must not be blocked",
                "runtime smoke evidence checker must reject blocked hard-gate results",
            ),
            (
                "install-drift",
                complete.replace(
                    "- `python3 plugins/arbor/skills/arbor/scripts/check_install_state.py --strict`: pass",
                    "- `python3 plugins/arbor/skills/arbor/scripts/check_install_state.py --strict`: drift",
                ),
                "Cache And Install State strict checks must pass",
                "runtime smoke evidence checker must reject non-passing install-state strict evidence",
            ),
            (
                "dirty-sync-override",
                complete.replace("- Dirty source sync guard: pass", "- Dirty source sync guard: overridden"),
                "Cache And Install State dirty source sync guard must pass",
                "runtime smoke evidence checker must reject dirty-source sync override evidence",
            ),
            (
                "legacy-cache",
                complete.replace(
                    "- Legacy plugin-level `hooks/hooks.json` present: no",
                    "- Legacy plugin-level `hooks/hooks.json` present: yes",
                ),
                "Cache And Install State must report no legacy plugin-level hook manifests",
                "runtime smoke evidence checker must reject legacy plugin hook cache evidence",
            ),
            (
                "transient-cache",
                complete.replace(
                    "- `__pycache__` / `*.pyc` present in synced cache: no",
                    "- `__pycache__` / `*.pyc` present in synced cache: yes",
                ),
                "Cache And Install State must report no transient cache artifacts",
                "runtime smoke evidence checker must reject transient cache artifact evidence",
            ),
            (
                "substitute-failure",
                complete.replace(
                    "- Project wrapper execution through fake Codex cache: pass",
                    "- Project wrapper execution through fake Codex cache: fail",
                ),
                "Deterministic Substitute Evidence checks must pass",
                "runtime smoke evidence checker must reject non-passing deterministic substitute evidence",
            ),
            (
                "missing-matrix-row",
                complete.replace(
                    "| Codex | Windows | Stop | yes | yes | yes | C:/Users/example/.codex/plugins/cache/arbor/arbor/2.0.0 | memory hygiene completed | none |\n",
                    "",
                ),
                "Hook Runtime Smoke must include Codex Windows Stop evidence",
                "runtime smoke evidence checker must reject missing matrix rows",
            ),
            (
                "duplicate-matrix-row",
                complete.replace(
                    "| Codex | Windows | SessionStart | yes | yes | yes | C:/Users/example/.codex/plugins/cache/arbor/arbor/2.0.0 | startup context rendered | none |\n",
                    "| Codex | Windows | SessionStart | yes | yes | yes | C:/Users/example/.codex/plugins/cache/arbor/arbor/2.0.0 | startup context rendered | none |\n"
                    "| Codex | Windows | SessionStart | yes | yes | yes | C:/Users/example/.codex/plugins/cache/arbor/arbor/2.0.0 | duplicate runtime proof | none |\n",
                ),
                "Hook Runtime Smoke must include exactly one Codex Windows SessionStart evidence row",
                "runtime smoke evidence checker must reject duplicate matrix rows",
            ),
            (
                "unexpected-matrix-row",
                complete.replace(
                    "| Claude Code | macOS/Linux | Stop | not run | not run | yes | not run | not run | macOS/Linux runtime not available on this machine |\n\n",
                    "| Claude Code | macOS/Linux | Stop | not run | not run | yes | not run | not run | macOS/Linux runtime not available on this machine |\n"
                    "| Other Runtime | Windows | Stop | not run | not run | yes | not run | not run | Extra runtime not part of Arbor release matrix |\n\n",
                ),
                "Hook Runtime Smoke contains unexpected Other Runtime Windows Stop evidence",
                "runtime smoke evidence checker must reject rows outside the release matrix",
            ),
            (
                "vague-unavailable-reason",
                complete.replace(
                    "| Claude Code | Windows | SessionStart | not run | not run | yes | not run | not run | Claude Code unavailable on this machine |",
                    "| Claude Code | Windows | SessionStart | not run | not run | yes | not run | not run | n/a |",
                ),
                "Hook Runtime Smoke row 3 was not run but lacks a concrete unavailable reason",
                "runtime smoke evidence checker must reject vague unavailable reasons",
            ),
            (
                "ambiguous-fired-value",
                complete.replace(
                    "| Claude Code | Windows | SessionStart | not run | not run | yes | not run | not run | Claude Code unavailable on this machine |",
                    "| Claude Code | Windows | SessionStart | not run | no | yes | not run | not run | Claude Code unavailable on this machine |",
                ),
                "Hook Runtime Smoke row 3 Fired must be a passing marker or not run",
                "runtime smoke evidence checker must reject ambiguous Fired values",
            ),
            (
                "hidden-risk",
                complete.replace("- Claude Code and macOS/Linux runtime smoke not run on this Windows machine.", "- none"),
                "Known Risks cannot be none",
                "runtime smoke evidence checker must reject hidden not-run runtime risks",
            ),
            (
                "mixed-none-and-risk",
                complete.replace(
                    "## Known Risks\n\n- Claude Code and macOS/Linux runtime smoke not run on this Windows machine.",
                    "## Known Risks\n\n- none\n- Claude Code and macOS/Linux runtime smoke not run on this Windows machine.",
                ),
                "Known Risks cannot mix none with explicit risks",
                "runtime smoke evidence checker must reject mixed none and explicit risks",
            ),
            (
                "missing-cache-discovery",
                complete.replace(
                    "| Codex | Windows | SessionStart | yes | yes | yes | C:/Users/example/.codex/plugins/cache/arbor/arbor/2.0.0 | startup context rendered | none |",
                    "| Codex | Windows | SessionStart | yes | yes | yes | not run | startup context rendered | none |",
                ),
                "Hook Runtime Smoke row 1 fired but lacks concrete cache discovery path",
                "runtime smoke evidence checker must reject fired rows without cache discovery evidence",
            ),
            (
                "relative-cache-discovery",
                complete.replace(
                    "| Codex | Windows | SessionStart | yes | yes | yes | C:/Users/example/.codex/plugins/cache/arbor/arbor/2.0.0 | startup context rendered | none |",
                    "| Codex | Windows | SessionStart | yes | yes | yes | relative/cache | startup context rendered | none |",
                ),
                "Hook Runtime Smoke row 1 fired but lacks absolute cache discovery path",
                "runtime smoke evidence checker must reject relative cache discovery paths",
            ),
            (
                "mismatched-cache-version",
                complete.replace(
                    "| Codex | Windows | SessionStart | yes | yes | yes | C:/Users/example/.codex/plugins/cache/arbor/arbor/2.0.0 | startup context rendered | none |",
                    "| Codex | Windows | SessionStart | yes | yes | yes | C:/Users/example/.codex/plugins/cache/arbor/arbor/1.1.1 | startup context rendered | none |",
                ),
                "Hook Runtime Smoke row 1 cache discovery path does not match evidence Version 2.0.0",
                "runtime smoke evidence checker must reject fired cache paths for the wrong version",
            ),
            (
                "passing-fired-marker-without-proof",
                complete.replace(
                    "| Codex | Windows | SessionStart | yes | yes | yes | C:/Users/example/.codex/plugins/cache/arbor/arbor/2.0.0 | startup context rendered | none |",
                    "| Codex | Windows | SessionStart | yes | ok | yes | not run | not run | none |",
                ),
                "Hook Runtime Smoke row 1 fired but lacks concrete cache discovery path",
                "runtime smoke evidence checker must reject passing fired markers without proof",
            ),
            (
                "fired-without-evidence",
                complete.replace(
                    "| Codex | Windows | SessionStart | yes | yes | yes | C:/Users/example/.codex/plugins/cache/arbor/arbor/2.0.0 | startup context rendered | none |",
                    "| Codex | Windows | SessionStart | yes | yes | yes | C:/Users/example/.codex/plugins/cache/arbor/arbor/2.0.0 | none | none |",
                ),
                "Hook Runtime Smoke row 1 fired but lacks concrete evidence",
                "runtime smoke evidence checker must reject fired rows with no concrete evidence",
            ),
            (
                "fired-with-unavailable-reason",
                complete.replace(
                    "| Codex | Windows | SessionStart | yes | yes | yes | C:/Users/example/.codex/plugins/cache/arbor/arbor/2.0.0 | startup context rendered | none |",
                    "| Codex | Windows | SessionStart | yes | yes | yes | C:/Users/example/.codex/plugins/cache/arbor/arbor/2.0.0 | startup context rendered | runtime unavailable |",
                ),
                "Hook Runtime Smoke row 1 fired but still has an unavailable reason",
                "runtime smoke evidence checker must reject fired rows with unavailable reasons",
            ),
            (
                "untrusted-fired",
                complete.replace(
                    "| Codex | Windows | SessionStart | yes | yes | yes | C:/Users/example/.codex/plugins/cache/arbor/arbor/2.0.0 | startup context rendered | none |",
                    "| Codex | Windows | SessionStart | no | yes | yes | C:/Users/example/.codex/plugins/cache/arbor/arbor/2.0.0 | startup context rendered | none |",
                ),
                "Hook Runtime Smoke row 1 fired but is not trusted",
                "runtime smoke evidence checker must reject fired rows without runtime trust proof",
            ),
            (
                "relative-python-fired",
                complete.replace(
                    "| Codex | Windows | SessionStart | yes | yes | yes | C:/Users/example/.codex/plugins/cache/arbor/arbor/2.0.0 | startup context rendered | none |",
                    "| Codex | Windows | SessionStart | yes | yes | no | C:/Users/example/.codex/plugins/cache/arbor/arbor/2.0.0 | startup context rendered | none |",
                ),
                "Hook Runtime Smoke row 1 fired but wrapper or launcher does not use absolute Python",
                "runtime smoke evidence checker must reject fired rows without absolute Python proof",
            ),
        ]

        for name, evidence, expected_output, message in cases:
            assert_evidence_case(errors, script, root, name, evidence, 1, expected_output, message)

        assert_evidence_case(
            errors,
            script,
            root,
            "invalid-encoding",
            b"\xff\xfe\x00\xff",
            1,
            "runtime smoke evidence check failed:",
            "runtime smoke evidence checker must reject invalid encoding cleanly",
        )


def main() -> int:
    errors: list[str] = []
    validate_runtime_smoke_evidence_checker(errors)

    if errors:
        print("runtime smoke evidence adapter checks failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("runtime smoke evidence adapter checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
