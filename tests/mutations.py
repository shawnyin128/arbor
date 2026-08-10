#!/usr/bin/env python3
"""Verify the test suite fails when the implementation is broken.

A passing suite proves nothing on its own: a test that also passes against a
broken implementation is not testing anything. This script applies each mutation
below, runs the tests that claim to cover it, and requires them to fail.

Usage:

    python tests/mutations.py [extra pytest args...]

Extra arguments are passed through to pytest, which is how to supply
``--basetemp`` on a machine where the default temporary directory is not
writable. Source files are always restored, including after an interrupt.
"""

from __future__ import annotations

import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CORE = REPO_ROOT / "plugins" / "arbor" / "skills" / "arbor" / "scripts" / "arbor_core"
LAUNCHER = REPO_ROOT / "plugins" / "arbor" / "hooks" / "arbor-hook.cmd"


@dataclass(frozen=True)
class Mutation:
    """A plausible regression and the tests that must catch it."""

    label: str
    path: Path
    find: str
    replace: str
    selector: list[str]


MUTATIONS = [
    Mutation(
        "hooks stop gating on the .arbor opt-in directory",
        CORE / "hooks.py",
        "    if root is None or not is_arbor_project(root):\n        return SKIP\n\n    try:",
        "    if root is None:\n        return SKIP\n\n    try:",
        ["tests/test_hooks.py", "-k", "silent_in_project_without_arbor"],
    ),
    Mutation(
        "byte order mark is no longer stripped from payloads",
        CORE / "hooks.py",
        "    text = raw.lstrip(BOM).strip()",
        "    text = raw.strip()",
        ["tests/test_hooks.py", "-k", "byte_order_mark"],
    ),
    Mutation(
        "CLAUDE_PROJECT_DIR stops taking precedence over payload cwd",
        CORE / "hooks.py",
        '    candidates = [os.environ.get("CLAUDE_PROJECT_DIR"), payload.get("cwd")]',
        '    candidates = [payload.get("cwd")]',
        ["tests/test_hooks.py", "-k", "claude_project_dir_wins"],
    ),
    Mutation(
        "malformed todo payloads overwrite a good snapshot",
        CORE / "session.py",
        "    if not items and raw:\n        return None\n    return items",
        "    return items",
        ["tests/test_hooks.py::TestTodoSnapshot::test_malformed_todos_preserve_the_previous_snapshot"],
    ),
    Mutation(
        "session state is written outside an Arbor project",
        CORE / "session.py",
        "    if not directory.is_dir():\n        return False",
        "    directory.mkdir(parents=True, exist_ok=True)",
        ["tests/test_session.py", "-k", "refuses_to_create_state_outside"],
    ),
    Mutation(
        "budget drops the most important sections first",
        CORE / "packet.py",
        "    for section in sorted(sections, key=lambda item: item.priority, reverse=True):",
        "    for section in sorted(sections, key=lambda item: item.priority):",
        ["tests/test_packet.py", "-k", "drops_lowest_priority"],
    ),
    Mutation(
        "a wall-clock timestamp returns to injected context",
        CORE / "packet.py",
        "    lines.append(summary)",
        '    lines.append(summary + " at " + state.get("todos", {}).get("captured_at", ""))',
        ["tests/test_packet.py", "-k", "wall_clock"],
    ),
    Mutation(
        "over-budget packets are emitted instead of withheld",
        CORE / "packet.py",
        '    if len(preamble) > cap:\n        return ""',
        '    if False:\n        return ""',
        ["tests/test_packet.py", "-k", "never_exceeds or does_not_fit"],
    ),
    Mutation(
        "a backticked import counts as wiring the guide",
        CORE / "packet.py",
        '        if GUIDE_IMPORT in stripped and f"`{GUIDE_IMPORT}`" not in stripped:',
        "        if GUIDE_IMPORT in stripped:",
        ["tests/test_packet.py", "-k", "backticked"],
    ),
    Mutation(
        "init overwrites existing user files",
        CORE / "init.py",
        "    if target.exists():\n        if not target.is_file():\n"
        '            raise InitError(f"cannot initialize {label}: a directory exists at that path")\n'
        '        return Action(label, "exists")',
        "    if target.exists() and not target.is_file():\n"
        '        raise InitError(f"cannot initialize {label}: a directory exists at that path")',
        ["tests/test_init.py", "-k", "untouched or byte_identical"],
    ),
    Mutation(
        "legacy hook-written memory is treated as live context",
        CORE / "notes.py",
        "        if any(marker in item for marker in LEGACY_HOOK_MARKERS):\n"
        "            stale.append(item)\n            continue",
        "        pass",
        ["tests/test_notes.py", "-k", "legacy_hook_entries"],
    ),
    Mutation(
        "doctor stops reporting whether hooks fired",
        CORE / "doctor.py",
        '        rows.append(Row(label, WARN, "never fired in this project"))',
        '        rows.append(Row(label, OK, "assumed fine"))',
        ["tests/test_doctor.py", "-k", "never_ran"],
    ),
    Mutation(
        "staleness check trusts paths git never tracked, creating false alarms",
        CORE / "notes.py",
        "        if vcs.knows_path(root, anchor):\n            gone.append(anchor)",
        "        gone.append(anchor)",
        ["tests/test_notes.py", "-k", "never_tracked"],
    ),
    Mutation(
        "entry parsing goes back to indentation-blind",
        CORE / "notes.py",
        r'_ENTRY_START = re.compile(r"^[-*]\s+(?P<body>.*)$")',
        r'_ENTRY_START = re.compile(r"^\s*[-*]\s+(?P<body>.*)$")',
        ["tests/test_notes.py", "-k", "sub_bullet or continuation"],
    ),
    Mutation(
        "an outdated note is rendered as if it were current",
        CORE / "packet.py",
        '            lines.append(f"- {entry.text} [outdated: ',
        '            lines.append(f"- {entry.text}")  # ',
        ["tests/test_packet.py", "-k", "path_is_gone"],
    ),
    Mutation(
        "a conflicted notes file is presented as settled",
        CORE / "notes.py",
        "        conflicted=bool(_CONFLICT.search(text)),",
        "        conflicted=False,",
        ["tests/test_notes.py", "-k", "conflict_is_detected"],
    ),
    Mutation(
        "the budget warning only fires after the file is already over",
        CORE / "packet.py",
        "    if memory.line_count >= notes.LINE_BUDGET * notes.WARN_FRACTION:",
        "    if memory.line_count > notes.LINE_BUDGET * 99:",
        ["tests/test_packet.py", "-k", "still_room_to_act"],
    ),
    Mutation(
        "a rewritten history produces a diff instead of a warning",
        CORE / "packet.py",
        "    if not vcs.is_ancestor(root, last):",
        "    if False:",
        ["tests/test_packet.py", "-k", "rewritten"],
    ),
    Mutation(
        "task capture handles only TodoWrite, missing hosts that use the Task tools",
        CORE / "hooks.py",
        'TASK_TOOLS = frozenset({"TodoWrite", "TaskCreate", "TaskUpdate"})',
        'TASK_TOOLS = frozenset({"TodoWrite"})',
        ["tests/test_hooks.py", "-k", "captures_the_host_list"],
    ),
    Mutation(
        "the launcher gains carriage returns",
        LAUNCHER,
        "\n",
        "\r\n",
        ["tests/test_launcher.py", "-k", "carriage_returns"],
    ),
]


def restore(path: Path, original: bytes) -> None:
    """Put a mutated file back, and refuse to continue if it cannot be done.

    A restore can fail transiently — on Windows a subprocess spawned by the tests
    may still hold the file open. Leaving a mutation on disk is the worst possible
    outcome for this script, because the mutation is a deliberate defect: one such
    failure silently disabled the opt-in gate that keeps hooks out of unrelated
    projects. Retry, verify the bytes, and abort loudly rather than continue.
    """
    for attempt in range(5):
        try:
            path.write_bytes(original)
        except OSError:
            time.sleep(0.2 * (attempt + 1))
            continue
        if path.read_bytes() == original:
            return
    raise SystemExit(
        f"FATAL: could not restore {path}. It is still mutated on disk. "
        f"Run `git checkout -- {path.relative_to(REPO_ROOT).as_posix()}` before doing anything else."
    )


def apply(mutation: Mutation, text: str) -> str:
    if mutation.path == LAUNCHER and mutation.find == "\n":
        return text.replace("\n", "\r\n")
    return text.replace(mutation.find, mutation.replace, 1)


def main(argv: list[str]) -> int:
    escaped: list[str] = []
    for mutation in MUTATIONS:
        original = mutation.path.read_bytes()
        # Match against LF text regardless of how the working tree was checked
        # out. With autocrlf on, a file restored by git arrives with CRLF, and a
        # pattern written with newline escapes would silently stop matching; this
        # script would then report a stale pattern instead of a real result. The
        # restore writes the original bytes back, so the checkout form is kept.
        text = original.decode("utf-8").replace("\r\n", "\n")
        if mutation.find not in text:
            escaped.append(f"{mutation.label}: pattern no longer present in {mutation.path.name}")
            print(f"  STALE       {mutation.label}")
            continue
        mutation.path.write_bytes(apply(mutation, text).encode("utf-8"))
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", *mutation.selector, "-x", "-q", *argv],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
        finally:
            restore(mutation.path, original)
        if proc.returncode == 0:
            escaped.append(f"{mutation.label}: {' '.join(mutation.selector)} still passed")
            print(f"  NOT CAUGHT  {mutation.label}")
        else:
            print(f"  caught      {mutation.label}")

    print()
    if escaped:
        print("Mutations the suite failed to catch:")
        for item in escaped:
            print(f"- {item}")
        return 1
    print(f"all {len(MUTATIONS)} mutations were caught")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
