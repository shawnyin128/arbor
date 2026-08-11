#!/usr/bin/env python3
"""Measure whether Arbor's injected packet beats the context the host already gives.

Each probe asks one question with a checkable answer. Arm ``off`` renames
``.arbor/`` so the SessionStart hook no-ops; arm ``on`` leaves it in place. Both
arms keep identical bytes on disk, so a probe that the host already answers
should score the same in both, while a probe only Arbor answers should need
fewer turns in arm ``on``.

The fixture keeps ``.arbor/`` untracked and gitignored. Renaming a tracked
directory would show up in ``git status``, which the host injects into every
session, and that difference would confound every probe.

Requires an authenticated ``claude`` CLI and spends real tokens, so this is a
manual script rather than part of the pytest suite.

Usage:
    python tests/ab_harness.py --reps 3
    python tests/ab_harness.py --probes flight,tree --reps 5 --model sonnet
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

for _stream, _errors in ((sys.stdout, "replace"), (sys.stderr, "replace")):
    try:
        _stream.reconfigure(encoding="utf-8", errors=_errors)
    except (AttributeError, OSError, ValueError):
        pass

REPO = Path(__file__).resolve().parent.parent
ARBOR_CLI = REPO / "plugins" / "arbor" / "skills" / "arbor" / "scripts" / "arbor.py"

# Tools a probe may use. Write and Edit are withheld so a run cannot alter the
# fixture, and Bash is narrowed to read-only git so no arbitrary command runs.
ALLOWED_TOOLS = (
    "Read Glob Grep "
    "Bash(git log:*) Bash(git status:*) Bash(git diff:*) Bash(git show:*)"
)

PENDING_TASK = "Wire the streaming reader into the CLI"
OPEN_DECISION = "whether to keep the legacy adapter until the parser lands"
NEWEST_IDEA = "Cache the token index between runs"
COMMITTED_DELETION = "src/legacy_adapter.py"
UNCOMMITTED_DELETION = "src/dropped.py"
COMMITS_SINCE = 3


@dataclass
class Probe:
    """One question, the section it exercises, and how to score an answer."""

    name: str
    section: str
    native: bool
    question: str
    needles: tuple[str, ...]
    forbidden: tuple[str, ...] = ()

    def scores(self, answer: str) -> bool:
        """Whether the answer names every required fact and no disqualifying one."""
        low = answer.lower()
        if any(bad.lower() in low for bad in self.forbidden):
            return False
        return all(needle.lower() in low for needle in self.needles)


PROBES: tuple[Probe, ...] = (
    Probe(
        name="flight",
        section="In flight",
        native=False,
        question=(
            "Exactly one task was left unfinished when the previous session ended. "
            "Reply with only that task's text, nothing else."
        ),
        needles=("streaming reader",),
    ),
    Probe(
        name="since",
        section="Since last session",
        native=False,
        question=(
            "Commits landed after the previous session ended. Reply with exactly "
            "one line in the form N|path where N is how many commits landed and "
            "path is the tracked file those commits deleted."
        ),
        needles=(str(COMMITS_SINCE), "legacy_adapter"),
    ),
    Probe(
        name="unresolved",
        section="Unresolved",
        native=False,
        question=(
            "One decision about this project is recorded as still unresolved. "
            "Reply with only that decision, in one sentence."
        ),
        needles=("legacy adapter",),
    ),
    Probe(
        name="parked",
        section="Parked ideas",
        native=False,
        question=(
            "Ideas have been parked for later. Reply with how many are parked, "
            "then a colon, then the full text of the most recently added one."
        ),
        needles=("2", "token index"),
    ),
    Probe(
        name="tree",
        section="Working tree",
        native=True,
        question=(
            "One tracked file has been deleted from the working tree but the "
            "deletion is not committed. Reply with only that file's path."
        ),
        needles=("dropped.py",),
        forbidden=("legacy_adapter",),
    ),
    Probe(
        name="commits",
        section="Recent commits",
        native=True,
        question=(
            "Reply with only the subject line of the most recent commit on this "
            "branch, nothing else."
        ),
        needles=("retire the legacy adapter",),
    ),
    Probe(
        name="position",
        section="Position",
        native=True,
        question=(
            "Reply with only the name of the branch this working copy is on, "
            "nothing else."
        ),
        needles=("feature/streaming",),
    ),
)


@dataclass
class Result:
    """One probe run in one arm."""

    probe: str
    arm: str
    correct: bool
    turns: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    answer: str
    injected: bool = False
    error: str = ""


@dataclass
class Fixture:
    """A throwaway project plus the pristine state to restore between runs."""

    root: Path
    pristine_session: bytes = b""
    files: dict[str, bytes] = field(default_factory=dict)


def claude_cli() -> str:
    """Absolute path to the ``claude`` CLI.

    Windows resolves the launcher through ``PATHEXT``, which ``CreateProcess``
    does not apply, so passing the bare name to ``subprocess`` fails.
    """
    resolved = shutil.which("claude")
    if resolved is None:
        raise SystemExit("the `claude` CLI is not on PATH; this harness needs it")
    return resolved


def remove_tree(path: Path) -> None:
    """Delete ``path`` and prove it is gone.

    Git marks objects read-only, which makes a plain delete fail on Windows.
    ``ignore_errors`` would swallow that and leave a half-built fixture behind,
    so the read-only bit is cleared and the result is verified.
    """
    if not path.exists():
        return

    def clear_readonly(func, target, _exc):
        os.chmod(target, 0o700)
        func(target)

    for _ in range(3):
        shutil.rmtree(path, onexc=clear_readonly)
        if not path.exists():
            return
    raise SystemExit(f"could not remove the old fixture at {path}; remove it by hand")


def git(root: Path, *args: str) -> str:
    """Run git in ``root`` and return stdout, raising on a non-zero exit."""
    done = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return done.stdout


def write(path: Path, text: str) -> None:
    """Write ``text`` with LF endings, creating parents."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def build_fixture(root: Path) -> Fixture:
    """Create the probe project: enough history to hide the session boundary.

    The host injects the five most recent commits, so the recorded boundary sits
    deeper than five commits back. Otherwise arm ``off`` could read the boundary
    straight out of the host's own block.
    """
    remove_tree(root)
    root.mkdir(parents=True)

    subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
    git(root, "config", "user.email", "probe@example.invalid")
    git(root, "config", "user.name", "Arbor AB Probe")
    git(root, "checkout", "-q", "-b", "feature/streaming")

    # `.arbor/` stays untracked so switching arms cannot move `git status`.
    write(root / ".gitignore", ".arbor/\n.arbor-off/\n")
    write(root / "README.md", "# probe\n\nA throwaway project for Arbor's A/B harness.\n")
    write(root / "src" / "tokenizer.py", "def tokenize(text):\n    return text.split()\n")
    write(root / "src" / "legacy_adapter.py", "def adapt(value):\n    return value\n")
    write(root / "src" / "dropped.py", "def dropped():\n    return None\n")
    write(root / "tests" / "test_tokenizer.py", "def test_tokenize():\n    assert True\n")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "feat: add the tokenizer and the legacy adapter")

    for n in range(1, 9):
        write(root / "src" / "tokenizer.py", f"def tokenize(text):\n    return text.split()  # r{n}\n")
        git(root, "add", "-A")
        git(root, "commit", "-qm", f"refactor: tune the tokenizer, round {n}")

    boundary = git(root, "rev-parse", "--short", "HEAD").strip()

    write(root / ".arbor" / ".gitignore", "# Machine-written session state.\nsession.json\n")
    write(
        root / ".arbor" / "memory.md",
        "# Session Memory\n\n## Unresolved\n\n"
        f"- Still open: {OPEN_DECISION}, because `src/tokenizer.py` has not settled.\n",
    )
    write(
        root / ".arbor" / "ideas.md",
        "# Parked Ideas\n\n## Parked\n\n"
        "- Move the tokenizer onto a streaming interface.\n"
        f"- {NEWEST_IDEA}.\n",
    )
    write(
        root / "AGENTS.md",
        "# Agent Guide\n\n## Project Goal\n\nA throwaway project for Arbor's A/B harness.\n\n"
        "## Project Constraints\n\n- Nothing here is real code.\n\n"
        "## Project Map\n\n- `README.md`: overview.\n- `src/`: source.\n- `tests/`: tests.\n",
    )
    write(root / "CLAUDE.md", "@AGENTS.md\n\n## Claude Code\n\nA probe fixture.\n")

    # Snapshot the task list through the real hook, at the boundary commit.
    payload = {
        "tool_name": "TodoWrite",
        "session_id": "ab-harness-seed",
        "cwd": str(root),
        "tool_input": {
            "todos": [
                {"content": "Read the tokenizer tests", "status": "completed"},
                {"content": "Split the tokenizer helpers", "status": "completed"},
                {"content": PENDING_TASK, "status": "pending"},
            ]
        },
    }
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(root), PYTHONIOENCODING="utf-8")
    env.pop("CLAUDE_CONFIG_DIR", None)
    seeded = subprocess.run(
        [sys.executable, str(ARBOR_CLI), "hook", "todo-snapshot"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        cwd=str(root),
    )
    if seeded.returncode != 0:
        raise SystemExit(f"seeding the task snapshot failed: {seeded.stderr[:400]}")

    state = root / ".arbor" / "session.json"
    if not state.is_file():
        raise SystemExit("the task-capture hook wrote no session.json; fixture is invalid")
    recorded = json.loads(state.read_text(encoding="utf-8"))
    if recorded.get("todos", {}).get("captured_head") != boundary:
        raise SystemExit("the snapshot did not record the boundary commit; fixture is invalid")

    # Exactly three commits after the boundary. The deletion goes last so one
    # ordering serves both the `since` probe and the `commits` probe.
    write(root / "src" / "streaming.py", "def stream(chunks):\n    yield from chunks\n")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "feat: add the streaming reader")
    write(root / "tests" / "test_streaming.py", "def test_stream():\n    assert True\n")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "test: cover the streaming reader")
    (root / COMMITTED_DELETION).unlink()
    git(root, "add", "-A")
    git(root, "commit", "-qm", "refactor: retire the legacy adapter")

    # A dirty tree with one uncommitted deletion for the `tree` probe.
    (root / UNCOMMITTED_DELETION).unlink()
    write(root / "src" / "tokenizer.py", "def tokenize(text):\n    return text.split()  # wip\n")

    fixture = Fixture(root=root, pristine_session=state.read_bytes())
    for tracked in ("src/tokenizer.py",):
        fixture.files[tracked] = (root / tracked).read_bytes()
    return fixture


def set_arm(fixture: Fixture, arm: str) -> None:
    """Put ``.arbor/`` in place for arm ``on`` and out of the way for arm ``off``."""
    live = fixture.root / ".arbor"
    parked = fixture.root / ".arbor-off"
    if arm == "on":
        if parked.is_dir() and not live.exists():
            parked.rename(live)
    else:
        if live.is_dir() and not parked.exists():
            live.rename(parked)


def reset(fixture: Fixture, arm: str) -> None:
    """Restore the state a run mutates, so every run starts identical.

    Arbor's own hooks stamp receipts and a handoff into ``session.json``, so
    without this the second run in an arm sees different state from the first.
    """
    directory = fixture.root / (".arbor" if arm == "on" else ".arbor-off")
    state = directory / "session.json"
    if directory.is_dir():
        state.write_bytes(fixture.pristine_session)
    for tracked, blob in fixture.files.items():
        (fixture.root / tracked).write_bytes(blob)
    if (fixture.root / UNCOMMITTED_DELETION).exists():
        (fixture.root / UNCOMMITTED_DELETION).unlink()


def fired(fixture: Fixture, arm: str) -> bool:
    """Whether Arbor's SessionStart hook ran during the run that just finished.

    Without this a hook that quietly failed to fire would be scored as "Arbor
    added nothing", which is the one conclusion this harness must never reach by
    accident. ``reset`` restores the pristine state before every run, so a
    SessionStart receipt can only come from the run itself.
    """
    if arm == "off":
        return False
    state = fixture.root / ".arbor" / "session.json"
    if not state.is_file():
        return False
    try:
        receipts = json.loads(state.read_text(encoding="utf-8")).get("receipts", {})
    except (OSError, json.JSONDecodeError):
        return False
    return any(name.startswith("SessionStart") for name in receipts)


def run_probe(fixture: Fixture, probe: Probe, arm: str, model: str) -> Result:
    """Run one probe in one arm and score the answer."""
    set_arm(fixture, arm)
    reset(fixture, arm)

    command = [
        claude_cli(),
        "-p",
        probe.question,
        "--output-format",
        "json",
        "--allowedTools",
        ALLOWED_TOOLS,
        "--disallowedTools",
        "Write Edit NotebookEdit WebFetch WebSearch Task",
    ]
    if model:
        command += ["--model", model]

    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    env.pop("CLAUDE_PROJECT_DIR", None)
    done = subprocess.run(
        command,
        cwd=str(fixture.root),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=600,
    )
    blank = Result(probe.name, arm, False, 0, 0, 0, 0.0, "")
    if not done.stdout.strip():
        blank.error = (done.stderr or "no stdout").strip()[:300]
        return blank
    try:
        payload = json.loads(done.stdout)
    except json.JSONDecodeError:
        blank.error = f"unparseable stdout: {done.stdout[:200]}"
        return blank

    usage = payload.get("usage") or {}
    answer = payload.get("result") or ""
    return Result(
        injected=fired(fixture, arm),
        probe=probe.name,
        arm=arm,
        correct=probe.scores(answer),
        turns=int(payload.get("num_turns") or 0),
        input_tokens=sum(
            int(usage.get(key) or 0)
            for key in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
        ),
        output_tokens=int(usage.get("output_tokens") or 0),
        cost_usd=float(payload.get("total_cost_usd") or 0.0),
        answer=answer.strip().replace("\n", " ")[:160],
        error="" if not payload.get("is_error") else "host reported is_error",
    )


def report(results: list[Result], probes: tuple[Probe, ...]) -> None:
    """Print the per-probe comparison and the verdict each measurement supports."""
    by_probe = {probe.name: probe for probe in probes}
    print()
    print(f"{'probe':11s} {'section':20s} {'native':6s} "
          f"{'off ok':7s} {'on ok':7s} {'off turns':9s} {'on turns':9s} "
          f"{'off tok':8s} {'on tok':8s}")
    print("-" * 96)
    for name, probe in by_probe.items():
        arm = {a: [r for r in results if r.probe == name and r.arm == a] for a in ("off", "on")}
        if not arm["off"] and not arm["on"]:
            continue

        def rate(rows: list[Result]) -> str:
            return f"{sum(r.correct for r in rows)}/{len(rows)}" if rows else "-"

        def med(rows: list[Result], attr: str) -> str:
            values = [getattr(r, attr) for r in rows if not r.error]
            return f"{statistics.median(values):.0f}" if values else "-"

        print(f"{name:11s} {probe.section:20s} {'yes' if probe.native else 'no':6s} "
              f"{rate(arm['off']):7s} {rate(arm['on']):7s} "
              f"{med(arm['off'], 'turns'):9s} {med(arm['on'], 'turns'):9s} "
              f"{med(arm['off'], 'input_tokens'):8s} {med(arm['on'], 'input_tokens'):8s}")

    silent = [r for r in results if r.arm == "on" and not r.injected and not r.error]
    if silent:
        print(f"\nWARNING: {len(silent)} arm-`on` run(s) left no SessionStart receipt, "
              "so no packet reached them. Their rows measure nothing.")
        for row in silent[:8]:
            print(f"  {row.probe}")

    failures = [r for r in results if r.error]
    if failures:
        print(f"\n{len(failures)} run(s) failed:")
        for row in failures[:8]:
            print(f"  {row.probe}/{row.arm}: {row.error}")

    spend = sum(r.cost_usd for r in results)
    print(f"\n{len(results)} runs, {spend:.2f} USD reported by the host")

    print("\nAnswers given, for auditing the scorer:")
    for row in results:
        mark = "ok " if row.correct else "BAD"
        print(f"  {mark} {row.probe:11s} {row.arm:3s} {row.answer!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reps", type=int, default=3, help="runs per probe per arm")
    parser.add_argument("--probes", default="", help="comma-separated probe names")
    parser.add_argument("--model", default="sonnet", help="model alias, or '' for the default")
    parser.add_argument(
        "--fixture",
        default="",
        help="where to build the throwaway project (default: a sibling of this repo)",
    )
    parser.add_argument("--json", default="", help="also write raw results here")
    args = parser.parse_args()

    chosen = PROBES
    if args.probes:
        wanted = {name.strip() for name in args.probes.split(",") if name.strip()}
        unknown = wanted - {probe.name for probe in PROBES}
        if unknown:
            parser.error(f"unknown probe(s): {', '.join(sorted(unknown))}")
        chosen = tuple(probe for probe in PROBES if probe.name in wanted)

    if shutil.which("claude") is None:
        print("the `claude` CLI is not on PATH; this harness needs it", file=sys.stderr)
        return 2

    target = Path(args.fixture) if args.fixture else REPO.parent / "arbor-ab-fixture"
    print(f"building fixture at {target}")
    fixture = build_fixture(target)

    results: list[Result] = []
    total = len(chosen) * 2 * args.reps
    done = 0
    for probe in chosen:
        for arm in ("off", "on"):
            for _ in range(args.reps):
                done += 1
                print(f"[{done}/{total}] {probe.name}/{arm} ... ", end="", flush=True)
                row = run_probe(fixture, probe, arm, args.model)
                results.append(row)
                print("ok" if row.correct else ("ERR" if row.error else "wrong"))

    set_arm(fixture, "on")
    report(results, chosen)

    if args.json:
        Path(args.json).write_text(
            json.dumps([vars(r) for r in results], indent=2), encoding="utf-8"
        )
        print(f"\nraw results written to {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
