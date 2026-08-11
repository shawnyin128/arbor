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
    """One question, the section it exercises, and how to score the result.

    Most probes score the answer text. A probe with ``writes_to`` scores the
    fixture instead: the preamble asks the agent to append a passing idea to a
    file, and only the file can show whether it did.
    """

    name: str
    section: str
    native: bool
    question: str
    needles: tuple[str, ...]
    forbidden: tuple[str, ...] = ()
    writes_to: str = ""

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
    Probe(
        name="preamble",
        section="(protocol preamble)",
        native=False,
        question=(
            "Unrelated aside before we start: at some point we should memo-ize the "
            "parsed AST between runs so repeated parses get cheaper. Anyway, what I "
            "actually need: tell me in one sentence what src/tokenizer.py does."
        ),
        needles=("ast",),
        writes_to=".arbor/ideas.md",
    ),
)


# The guide experiment varies AGENTS.md instead of the packet, to answer a
# separate question: does a Project Map earn its characters, and does stating
# placement rules beat listing directories? The layout is deliberately one a
# newcomer would guess wrong, since a map can only help where guessing fails.
GUIDE_ARMS = ("none", "census", "rules")

GUIDE_HEAD = (
    "# Agent Guide\n\n"
    "## Project Goal\n\nA text pipeline for the A/B harness.\n\n"
    "## Project Constraints\n\n- Nothing here is real code.\n"
)

GUIDE_MAPS = {
    "none": "",
    # Descriptive: what Codex's /init asks for and what Arbor's template used to.
    "census": (
        "\n## Project Map\n\n"
        "- `internal/`: internal packages.\n"
        "- `src/`: application source.\n"
        "- `lib/`: shared helpers.\n"
        "- `tools/`: developer tooling.\n"
        "- `tests/`: tests.\n"
    ),
    # Prescriptive: rules and boundaries, which is what 2.2.0 asks for instead.
    "rules": (
        "\n## Project Map\n\n"
        "- All lexing lives in `internal/lex/scanner.py`. A new token rule goes in\n"
        "  its `RULES` table, never in a new file.\n"
        "- `src/` holds only the CLI entry point and must not import from `lib/`.\n"
        "- `lib/` is vendored third-party code. Never edit it.\n"
    ),
}

GUIDE_PROBES = (
    Probe(
        name="locate",
        section="(find the file to change)",
        native=True,
        question=(
            "Which single file implements tokenization in this project? "
            "Reply with only its path, nothing else."
        ),
        needles=("internal/lex/scanner.py",),
    ),
    Probe(
        name="place",
        section="(where new code goes)",
        native=True,
        question=(
            "I need to add one new token rule for hexadecimal literals. Reply with "
            "only the path of the file I should edit, nothing else."
        ),
        needles=("internal/lex/scanner.py",),
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
    wrote: str = ""
    injected: bool = False
    error: str = ""


@dataclass
class Fixture:
    """A throwaway project plus the pristine state to restore between runs."""

    root: Path
    pristine_session: bytes = b""
    pristine_notes: dict[str, bytes] = field(default_factory=dict)
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
    for note in ("memory.md", "ideas.md"):
        fixture.pristine_notes[note] = (root / ".arbor" / note).read_bytes()
    for tracked in ("src/tokenizer.py",):
        fixture.files[tracked] = (root / tracked).read_bytes()
    return fixture


def build_guide_fixture(root: Path) -> Fixture:
    """Create a project whose layout a newcomer would guess wrong.

    Tokenizing lives under `internal/lex/`, while `src/`, `lib/` and `tools/` all
    hold plausible decoys. Without that mismatch a map has nothing to contribute,
    and the experiment would only prove the layout was already obvious.
    """
    remove_tree(root)
    root.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
    git(root, "config", "user.email", "probe@example.invalid")
    git(root, "config", "user.name", "Arbor AB Probe")

    write(root / "README.md", "# pipeline\n\nA text pipeline.\n")
    write(
        root / "internal" / "lex" / "scanner.py",
        '"""Turn source text into tokens."""\n\n'
        "RULES = [\n"
        '    ("NUMBER", r"[0-9]+"),\n'
        '    ("NAME", r"[A-Za-z_]+"),\n'
        "]\n\n\n"
        "def scan(text):\n"
        "    return [(kind, pattern) for kind, pattern in RULES]\n",
    )
    write(root / "internal" / "lex" / "__init__.py", "from .scanner import scan\n")
    write(
        root / "src" / "cli.py",
        "from internal.lex import scan\n\n\n"
        "def main(argv):\n"
        "    return scan(argv[0])\n",
    )
    write(root / "lib" / "vendored_parser.py", "def parse(tokens):\n    return tokens\n")
    write(root / "tools" / "bench.py", "def bench():\n    return None\n")
    write(root / "tests" / "test_scan.py", "def test_scan():\n    assert True\n")
    write(root / "CLAUDE.md", "@AGENTS.md\n\n## Claude Code\n\nA probe fixture.\n")
    write(root / "AGENTS.md", GUIDE_HEAD)
    git(root, "add", "-A")
    git(root, "commit", "-qm", "feat: add the pipeline")
    return Fixture(root=root)


def set_guide_arm(fixture: Fixture, arm: str) -> None:
    """Write the AGENTS.md variant for ``arm``, leaving the tree otherwise identical."""
    (fixture.root / "AGENTS.md").write_text(
        GUIDE_HEAD + GUIDE_MAPS[arm], encoding="utf-8", newline="\n"
    )


def run_guide_probe(fixture: Fixture, probe: Probe, arm: str, model: str) -> Result:
    """Ask one guide probe with one AGENTS.md variant in place."""
    set_guide_arm(fixture, arm)
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
        probe=probe.name,
        arm=arm,
        correct=probe.scores(answer.replace("\\", "/")),
        turns=int(payload.get("num_turns") or 0),
        input_tokens=sum(
            int(usage.get(key) or 0)
            for key in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
        ),
        output_tokens=int(usage.get("output_tokens") or 0),
        cost_usd=float(payload.get("total_cost_usd") or 0.0),
        answer=answer.strip().replace("\n", " ")[:160],
        injected=True,
    )


def report_guide(results: list[Result]) -> None:
    """Print correctness and turns per probe per AGENTS.md variant."""
    print()
    header = f"{'probe':10s}" + "".join(f"{arm + ' ok':>11s}{arm + ' turns':>12s}" for arm in GUIDE_ARMS)
    print(header)
    print("-" * len(header))
    for probe in GUIDE_PROBES:
        line = f"{probe.name:10s}"
        for arm in GUIDE_ARMS:
            rows = [r for r in results if r.probe == probe.name and r.arm == arm]
            ok = f"{sum(r.correct for r in rows)}/{len(rows)}" if rows else "-"
            turns = [r.turns for r in rows if not r.error]
            med = f"{statistics.median(turns):.0f}" if turns else "-"
            line += f"{ok:>11s}{med:>12s}"
        print(line)
    print(f"\n{len(results)} runs, {sum(r.cost_usd for r in results):.2f} USD reported by the host")
    print("\nAnswers given, for auditing the scorer:")
    for row in results:
        print(f"  {'ok ' if row.correct else 'BAD'} {row.probe:8s} {row.arm:7s} {row.answer!r}")


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
    if directory.is_dir():
        (directory / "session.json").write_bytes(fixture.pristine_session)
        for note, blob in fixture.pristine_notes.items():
            (directory / note).write_bytes(blob)
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
        f"{ALLOWED_TOOLS} Write Edit" if probe.writes_to else ALLOWED_TOOLS,
        "--disallowedTools",
        "NotebookEdit WebFetch WebSearch Task"
        if probe.writes_to
        else "Write Edit NotebookEdit WebFetch WebSearch Task",
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

    # A probe that names a file is a claim about what the agent wrote, not about
    # what it said, so it is scored against the file and nothing else. Mentioning
    # the idea in the reply is exactly the near-miss this must not count.
    wrote = ""
    if probe.writes_to:
        directory = ".arbor" if arm == "on" else ".arbor-off"
        target = fixture.root / probe.writes_to.replace(".arbor", directory, 1)
        current = target.read_bytes() if target.is_file() else b""
        pristine = fixture.pristine_notes.get(target.name, b"")
        if current != pristine:
            wrote = current.decode("utf-8", errors="replace")

    return Result(
        injected=fired(fixture, arm),
        probe=probe.name,
        arm=arm,
        correct=probe.scores(wrote if probe.writes_to else answer),
        wrote=wrote.strip().replace("\n", " | ")[:300],
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

    print("\nResults, for auditing the scorer:")
    for row in results:
        mark = "ok " if row.correct else "BAD"
        probe = by_probe.get(row.probe)
        scored = row.wrote if probe is not None and probe.writes_to else row.answer
        print(f"  {mark} {row.probe:11s} {row.arm:3s} {scored!r}")
        if probe is not None and probe.writes_to and not row.wrote:
            print(f"      (file unchanged; reply was {row.answer[:110]!r})")


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
    parser.add_argument(
        "--experiment",
        default="packet",
        choices=("packet", "guide"),
        help="packet: is the injected packet worth it. guide: is a Project Map worth it.",
    )
    args = parser.parse_args()

    if args.experiment == "guide":
        target = Path(args.fixture) if args.fixture else REPO.parent / "arbor-ab-guide"
        print(f"building guide fixture at {target}")
        fixture = build_guide_fixture(target)
        results: list[Result] = []
        total = len(GUIDE_PROBES) * len(GUIDE_ARMS) * args.reps
        done = 0
        for probe in GUIDE_PROBES:
            for arm in GUIDE_ARMS:
                for _ in range(args.reps):
                    done += 1
                    print(f"[{done}/{total}] {probe.name}/{arm} ... ", end="", flush=True)
                    row = run_guide_probe(fixture, probe, arm, args.model)
                    results.append(row)
                    print("ok" if row.correct else ("ERR" if row.error else "wrong"))
        report_guide(results)
        if args.json:
            Path(args.json).write_text(
                json.dumps([vars(r) for r in results], indent=2), encoding="utf-8"
            )
        return 0

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
