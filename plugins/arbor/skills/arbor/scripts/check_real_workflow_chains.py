#!/usr/bin/env python3
"""Run real Arbor workflow chain checks through Codex or Claude Code.

This runner is intentionally not a simulation harness. It starts real runtime
processes, points them at temporary git repositories, captures rendered output,
and verifies file and git side effects outside the model.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


RUNTIME_CODEX = "codex"
RUNTIME_CLAUDE = "claude"
RUNTIME_LOCAL = "local"
RUNTIME_ALL = "all"
RUNTIMES = (RUNTIME_CODEX, RUNTIME_CLAUDE)

STATUS_PASS = "pass"
STATUS_FAIL = "fail"
STATUS_SKIP = "skip"
CLASS_STABLE_PASS = "stable_pass"
CLASS_WEAK_PASS = "weak_pass"
CLASS_WRONG_ROUTE = "wrong_route"
CLASS_FLAKY_AMBIGUOUS = "flaky_ambiguous"
CLASS_BLOCKED_RUNTIME = "blocked_runtime"
CLASS_SKIPPED = "skipped"
CLASSIFICATIONS = (
    CLASS_STABLE_PASS,
    CLASS_WEAK_PASS,
    CLASS_WRONG_ROUTE,
    CLASS_FLAKY_AMBIGUOUS,
    CLASS_BLOCKED_RUNTIME,
    CLASS_SKIPPED,
)

ROUTING_REPLAY_CASES = {
    "R01": {
        "category": "planning_continuation",
        "situation": "An active engineering planning prompt should become a formal brainstorm checkpoint before code changes.",
        "expected_chain": "intake -> brainstorm",
    },
    "R03": {
        "category": "direct_answer_control",
        "situation": "A standalone explanation should stay direct and should not create Arbor workflow state.",
        "expected_chain": "direct answer or intake -> none",
    },
    "R04": {
        "category": "active_review_evaluate",
        "situation": "A review request attached to an active developer handoff should run independent evaluation.",
        "expected_chain": "intake -> evaluate",
    },
    "R05": {
        "category": "runtime_traceback",
        "situation": "A non-trivial traceback blocking an active pipeline should enter Arbor-managed debugging.",
        "expected_chain": "intake -> develop or intake -> brainstorm",
    },
    "R07": {
        "category": "active_review_evaluate",
        "situation": "Evaluation output should be rendered for a user instead of exposing raw evaluator packets.",
        "expected_chain": "evaluate",
    },
    "R12": {
        "category": "release_publish",
        "situation": "A release request without explicit public-action authorization should stop at confirmation.",
        "expected_chain": "release(finalize_feature)",
    },
    "R13": {
        "category": "release_publish",
        "situation": "An explicitly scoped release action should perform only the authorized local action.",
        "expected_chain": "release(finalize_feature)",
    },
    "R15": {
        "category": "startup_session",
        "situation": "A fresh project overview should load Arbor startup context before answering.",
        "expected_chain": "arbor startup context",
    },
    "R17": {
        "category": "memory_hygiene",
        "situation": "Dirty Arbor-managed work should refresh short-term memory before stopping.",
        "expected_chain": "arbor memory hygiene",
    },
    "R21": {
        "category": "active_review_evaluate",
        "situation": "A workflow-skill output smoke should render the user-facing evaluation sections.",
        "expected_chain": "evaluate",
    },
    "R27": {
        "category": "planning_continuation",
        "situation": "A split-context engineering planning continuation should still become brainstorm.",
        "expected_chain": "intake -> brainstorm",
    },
    "R28": {
        "category": "project_map_drift",
        "situation": "A durable new project entrypoint should update the AGENTS Project Map before release.",
        "expected_chain": "arbor project-map drift",
    },
}
REQUIRED_ROUTING_CATEGORIES = {
    "planning_continuation",
    "runtime_traceback",
    "active_review_evaluate",
    "direct_answer_control",
    "memory_hygiene",
    "project_map_drift",
    "release_publish",
}

ROOT = Path(__file__).resolve().parents[3]
PLUGIN_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = PLUGIN_ROOT.parent.parent if PLUGIN_ROOT.parent.name == "plugins" else PLUGIN_ROOT
CODEX_CACHE = Path.home() / ".codex/plugins/cache/arbor/arbor/0.4.2"
CLAUDE_CACHE = Path.home() / ".claude/plugins/cache/arbor/arbor/0.4.2"
RAW_CHECKPOINT_LEAK_RE = re.compile(
    r"schema_version|```json|\"(?:source|route|ui|evaluation|review_context|release_context)\"\s*:|"
    r"\b(?:brainstorm|develop|evaluate|converge|release)\.v1\b|"
    r"\b(?:terminal_state|next_skill|feature_id|review_doc_path)\b|"
    r"\b(?:ready_for_evaluate|needs_develop_handoff|route_correction|checkpointed)\b|"
    r"^\s*(?:route|terminal state|next route|next skill)\s*:",
    re.IGNORECASE | re.MULTILINE,
)


class CaseFailure(AssertionError):
    """Raised when a real runtime case does not satisfy its contract."""


@dataclass(frozen=True)
class CaseContext:
    case_id: str
    runtime: str
    workdir: Path
    artifacts: Path
    plugin_root: Path


@dataclass(frozen=True)
class RuntimeResult:
    returncode: int
    stdout: str
    stderr: str
    final_response: str
    command: list[str]


@dataclass(frozen=True)
class CaseSpec:
    case_id: str
    title: str
    prompt: str
    setup: Callable[[CaseContext], None]
    assertions: list[Callable[[CaseContext, RuntimeResult | None], None]]
    runtimes: tuple[str, ...] = RUNTIMES
    requires_agent: bool = True
    timeout_seconds: int = 240
    description: str = ""


@dataclass
class CaseReport:
    case_id: str
    title: str
    runtime: str
    status: str
    classification: str
    category: str
    situation: str
    expected_chain: str
    artifact_dir: str
    reason: str = ""
    command: list[str] = field(default_factory=list)


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 60, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
        env=env,
    )


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")


def append(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(textwrap.dedent(text).lstrip())


def git(ctx: CaseContext, *args: str) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], cwd=ctx.workdir)


def init_git(ctx: CaseContext) -> None:
    proc = git(ctx, "init")
    require(proc.returncode == 0, f"git init failed: {proc.stderr}")
    git(ctx, "config", "user.email", "arbor-e2e@example.test")
    git(ctx, "config", "user.name", "Arbor E2E")


def commit_all(ctx: CaseContext, message: str = "chore: seed arbor e2e repo") -> None:
    git(ctx, "add", ".")
    proc = git(ctx, "commit", "-m", message)
    require(proc.returncode == 0, f"initial commit failed: {proc.stderr}")


def common_project(ctx: CaseContext) -> None:
    init_git(ctx)
    write(
        ctx.workdir / "AGENTS.md",
        """
        # Project Guide

        ## Startup Protocol

        For project overview questions, load this guide, recent git history,
        `.arbor/memory.md`, and `git status --short` before answering.

        ## Arbor E2E Protocol

        This repository is an Arbor real workflow chain review target. When an
        Arbor workflow skill is used, append a compact JSON line to
        `.arbor/e2e-trace.jsonl` with the skill name and the case id if possible.

        ## Project Purpose

        This project exists to test Arbor workflow routing, review artifacts,
        rendered output, session memory, and release checkpoints.
        """,
    )
    write(
        ctx.workdir / ".arbor/memory.md",
        """
        # Session Memory

        ## Observations

        - E2E project memory is intentionally present for startup-context checks.

        ## In-flight
        """,
    )
    write(ctx.workdir / "src/example.py", "def answer() -> int:\n    return 41\n")
    commit_all(ctx)


def setup_planning_context(ctx: CaseContext) -> None:
    common_project(ctx)
    write(
        ctx.workdir / "cleanup_notes.md",
        """
        # Cleanup Notes

        Active engineering context: design a safe cleanup plan for five entry scripts.
        The plan must split work into reviewable implementation features before code
        changes happen.
        """,
    )
    git(ctx, "add", "cleanup_notes.md")
    git(ctx, "commit", "-m", "docs: add cleanup planning context")


def setup_review_context(ctx: CaseContext) -> None:
    common_project(ctx)
    write(
        ctx.workdir / ".arbor/workflow/features.json",
        """
        {
          "active_feature_id": "F-review",
          "features": [
            {
              "id": "F-review",
              "title": "Review active developer handoff",
              "status": "in_evaluate",
              "review_doc_path": "docs/review/F-review.md"
            }
          ]
        }
        """,
    )
    write(
        ctx.workdir / "docs/review/F-review.md",
        """
        # F-review

        ## Context/Test Plan

        Acceptance criteria:
        - example answer is corrected to 42.

        Verification scope:
        - inspect `src/example.py`;
        - run a small behavior check;
        - include a negative/static probe.

        ## Developer Round 1

        | category | check | evidence | expected | actual | result | covers |
        | --- | --- | --- | --- | --- | --- | --- |
        | content | inspect answer | `src/example.py` | answer returns 42 | implementation changed | passed | acceptance:example answer is corrected |
        """,
    )
    write(ctx.workdir / "src/example.py", "def answer() -> int:\n    return 42\n")
    commit_all(ctx)


def setup_traceback_context(ctx: CaseContext) -> None:
    common_project(ctx)
    write(
        ctx.workdir / "run_pipeline.py",
        """
        from src.example import answer

        if answer() != 42:
            raise RuntimeError("pipeline blocked: answer mismatch")
        """,
    )
    commit_all(ctx)


def setup_develop_context(ctx: CaseContext) -> None:
    common_project(ctx)
    write(
        ctx.workdir / ".arbor/workflow/features.json",
        """
        {
          "active_feature_id": "F-dev",
          "features": [
            {
              "id": "F-dev",
              "title": "Fix answer implementation",
              "status": "approved",
              "review_doc_path": "docs/review/F-dev.md"
            }
          ]
        }
        """,
    )
    write(
        ctx.workdir / "docs/review/F-dev.md",
        """
        # F-dev

        ## Context/Test Plan

        Goal: update `src/example.py` so `answer()` returns 42.

        Acceptance criteria:
        - `answer()` returns 42.

        Verification scope:
        - inspect implementation;
        - run `python -c "from src.example import answer; assert answer() == 42"`.
        """,
    )
    commit_all(ctx)


def setup_converged_release_context(ctx: CaseContext) -> None:
    setup_review_context(ctx)
    append(
        ctx.workdir / "docs/review/F-review.md",
        """

        ## Evaluator Round 1

        Findings First: no blocking findings.

        ## Convergence Round 1

        Decision: converged. The developer and evaluator evidence agree.
        """,
    )
    write(
        ctx.workdir / ".arbor/workflow/features.json",
        """
        {
          "active_feature_id": "F-review",
          "features": [
            {
              "id": "F-review",
              "title": "Review active developer handoff",
              "status": "done",
              "review_doc_path": "docs/review/F-review.md"
            }
          ]
        }
        """,
    )
    git(ctx, "add", ".")
    git(ctx, "commit", "-m", "test: converge review fixture")


def setup_dirty_memory_context(ctx: CaseContext) -> None:
    common_project(ctx)
    write(ctx.workdir / "src/example.py", "def answer() -> int:\n    return 42\n")


def setup_startup_context(ctx: CaseContext) -> None:
    common_project(ctx)


def setup_local_only(ctx: CaseContext) -> None:
    common_project(ctx)


def setup_project_map_drift_context(ctx: CaseContext) -> None:
    init_git(ctx)
    write(
        ctx.workdir / "AGENTS.md",
        """
        # Project Guide

        ## Startup Protocol

        For project overview questions, load this guide, recent git history,
        `.arbor/memory.md`, and `git status --short` before answering.

        ## Project Purpose

        This project tests AGENTS project-map drift handling.

        ## Project Map

        - `src/`: implementation code.
        """,
    )
    write(
        ctx.workdir / ".arbor/memory.md",
        """
        # Session Memory

        ## Observations

        - None.

        ## In-flight

        - None.
        """,
    )
    write(ctx.workdir / "src/example.py", "def answer() -> int:\n    return 41\n")
    commit_all(ctx)
    write(ctx.workdir / "tools/map_helper.py", "def helper() -> str:\n    return 'map'\n")


def runtime_available(runtime: str) -> bool:
    return shutil.which(runtime) is not None


def codex_command(ctx: CaseContext, prompt: str, timeout: int) -> RuntimeResult:
    final_path = ctx.artifacts / "final-response.md"
    cmd = [
        "codex",
        "-a",
        "never",
        "exec",
        "-C",
        str(ctx.workdir),
        "-s",
        "workspace-write",
        "--ephemeral",
        "--output-last-message",
        str(final_path),
        prompt,
    ]
    proc = run(cmd, cwd=ctx.workdir, timeout=timeout)
    final = final_path.read_text(encoding="utf-8") if final_path.exists() else ""
    write(ctx.artifacts / "stdout.txt", proc.stdout)
    write(ctx.artifacts / "stderr.txt", proc.stderr)
    return RuntimeResult(proc.returncode, proc.stdout, proc.stderr, final, cmd)


def claude_command(ctx: CaseContext, prompt: str, timeout: int) -> RuntimeResult:
    cmd = [
        "claude",
        "-p",
        "--plugin-dir",
        str(ctx.plugin_root),
        "--permission-mode",
        "dontAsk",
        "--output-format",
        "text",
        prompt,
    ]
    proc = run(cmd, cwd=ctx.workdir, timeout=timeout)
    write(ctx.artifacts / "stdout.txt", proc.stdout)
    write(ctx.artifacts / "stderr.txt", proc.stderr)
    write(ctx.artifacts / "final-response.md", proc.stdout)
    return RuntimeResult(proc.returncode, proc.stdout, proc.stderr, proc.stdout, cmd)


def local_result(ctx: CaseContext, prompt: str, timeout: int) -> RuntimeResult:
    _ = prompt
    _ = timeout
    return RuntimeResult(0, "", "", "", ["local"])


def run_runtime(ctx: CaseContext, prompt: str, timeout: int) -> RuntimeResult:
    if ctx.runtime == RUNTIME_CODEX:
        return codex_command(ctx, prompt, timeout)
    if ctx.runtime == RUNTIME_CLAUDE:
        return claude_command(ctx, prompt, timeout)
    if ctx.runtime == RUNTIME_LOCAL:
        return local_result(ctx, prompt, timeout)
    raise CaseFailure(f"unsupported runtime: {ctx.runtime}")


def command_output(ctx: CaseContext, name: str, cmd: list[str], timeout: int = 60) -> str:
    proc = run(cmd, cwd=ctx.workdir, timeout=timeout)
    write(ctx.artifacts / f"{name}.stdout.txt", proc.stdout)
    write(ctx.artifacts / f"{name}.stderr.txt", proc.stderr)
    require(proc.returncode == 0, f"{name} failed: {proc.stderr}")
    return proc.stdout


def snapshot_state(ctx: CaseContext) -> None:
    for name, cmd in (
        ("git-status", ["git", "status", "--short", "--untracked-files=all"]),
        ("git-log", ["git", "log", "--oneline", "--decorate", "-5"]),
        ("changed-files", ["git", "diff", "--name-only", "HEAD"]),
    ):
        proc = run(cmd, cwd=ctx.workdir)
        write(ctx.artifacts / f"{name}.txt", proc.stdout + proc.stderr)
    trace = ctx.workdir / ".arbor/e2e-trace.jsonl"
    if trace.exists():
        shutil.copy2(trace, ctx.artifacts / "e2e-trace.jsonl")


def case_metadata(case: CaseSpec) -> dict[str, str]:
    metadata = ROUTING_REPLAY_CASES.get(case.case_id, {})
    return {
        "category": metadata.get("category", "general_workflow"),
        "situation": metadata.get("situation", case.description or case.title),
        "expected_chain": metadata.get("expected_chain", "case-specific observable contract"),
    }


def classify_success(ctx: CaseContext, case: CaseSpec) -> str:
    if not case.requires_agent:
        return CLASS_STABLE_PASS
    if (ctx.artifacts / "e2e-trace.jsonl").exists():
        return CLASS_STABLE_PASS
    return CLASS_WEAK_PASS


def classify_failure(exc: BaseException) -> str:
    if isinstance(exc, subprocess.TimeoutExpired):
        return CLASS_BLOCKED_RUNTIME
    reason = str(exc).lower()
    if any(term in reason for term in ("runtime unavailable", "operation not permitted", "timed out", "permission", "failed to initialize")):
        return CLASS_BLOCKED_RUNTIME
    if any(term in reason for term in ("flaky", "ambiguous", "telemetry cannot prove")):
        return CLASS_FLAKY_AMBIGUOUS
    return CLASS_WRONG_ROUTE


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CaseFailure(message)


def final_text(result: RuntimeResult | None) -> str:
    require(result is not None, "case did not run a runtime process")
    return result.final_response or result.stdout


def assert_success(_: CaseContext, result: RuntimeResult | None) -> None:
    require(result is not None, "runtime result missing")
    require(result.returncode == 0, f"runtime command failed with {result.returncode}: {result.stderr[-1200:]}")


def assert_no_raw_schema(_: CaseContext, result: RuntimeResult | None) -> None:
    text = final_text(result)
    require(
        RAW_CHECKPOINT_LEAK_RE.search(text) is None,
        "final response exposes raw workflow schema or internal checkpoint labels",
    )


def assert_contains(*terms: str) -> Callable[[CaseContext, RuntimeResult | None], None]:
    def _assert(_: CaseContext, result: RuntimeResult | None) -> None:
        text = final_text(result)
        missing = [term for term in terms if term not in text]
        require(not missing, f"final response missing terms: {missing}")

    return _assert


def assert_any_contains(*terms: str) -> Callable[[CaseContext, RuntimeResult | None], None]:
    def _assert(_: CaseContext, result: RuntimeResult | None) -> None:
        text = final_text(result)
        require(any(term in text for term in terms), f"final response missing any of: {terms}")

    return _assert


def assert_file_exists(path: str) -> Callable[[CaseContext, RuntimeResult | None], None]:
    def _assert(ctx: CaseContext, _: RuntimeResult | None) -> None:
        require((ctx.workdir / path).exists(), f"expected file missing: {path}")

    return _assert


def assert_file_not_exists(path: str) -> Callable[[CaseContext, RuntimeResult | None], None]:
    def _assert(ctx: CaseContext, _: RuntimeResult | None) -> None:
        require(not (ctx.workdir / path).exists(), f"unexpected file exists: {path}")

    return _assert


def assert_file_contains(path: str, *terms: str) -> Callable[[CaseContext, RuntimeResult | None], None]:
    def _assert(ctx: CaseContext, _: RuntimeResult | None) -> None:
        target = ctx.workdir / path
        require(target.exists(), f"expected file missing: {path}")
        text = target.read_text(encoding="utf-8")
        missing = [term for term in terms if term not in text]
        require(not missing, f"{path} missing terms: {missing}")

    return _assert


def assert_file_equals(path: str, expected: str) -> Callable[[CaseContext, RuntimeResult | None], None]:
    def _assert(ctx: CaseContext, _: RuntimeResult | None) -> None:
        target = ctx.workdir / path
        require(target.exists(), f"expected file missing: {path}")
        actual = target.read_text(encoding="utf-8")
        require(actual == expected, f"{path} changed unexpectedly")

    return _assert


def assert_rendered_table(*headings: str) -> Callable[[CaseContext, RuntimeResult | None], None]:
    def _assert(_: CaseContext, result: RuntimeResult | None) -> None:
        text = final_text(result)
        missing = [heading for heading in headings if heading not in text]
        require(not missing, f"rendered response missing headings: {missing}")
        require("|" in text and "---" in text, "rendered response missing markdown table")

    return _assert


def assert_git_commit_created(ctx: CaseContext, _: RuntimeResult | None) -> None:
    log = command_output(ctx, "assert-git-log", ["git", "log", "--oneline", "-3"])
    require(len([line for line in log.splitlines() if line.strip()]) >= 2, "expected a new git commit")


def assert_no_public_release(ctx: CaseContext, _: RuntimeResult | None) -> None:
    log = command_output(ctx, "assert-no-public-release-log", ["git", "log", "--oneline", "-5"])
    require("push" not in log.lower(), "unexpected push marker in local commit log")
    require("publish" not in log.lower(), "unexpected publish marker in local commit log")


def assert_memory_has_inflight(ctx: CaseContext, _: RuntimeResult | None) -> None:
    path = ctx.workdir / ".arbor/memory.md"
    require(path.exists(), "memory file missing")
    text = path.read_text(encoding="utf-8")
    require("In-flight" in text, "memory missing In-flight section")
    require("src/example.py" in text or "feature" in text.lower() or "checkpoint" in text.lower(), "memory does not describe active state")


def assert_memory_pruned(ctx: CaseContext, _: RuntimeResult | None) -> None:
    path = ctx.workdir / ".arbor/memory.md"
    require(path.exists(), "memory file missing")
    text = path.read_text(encoding="utf-8")
    require("Current task:" not in text, "resolved current task remained in memory")


def assert_cache_matches_source(_: CaseContext, __: RuntimeResult | None) -> None:
    for cache in (CODEX_CACHE, CLAUDE_CACHE):
        require(cache.exists(), f"cache missing: {cache}")
        for rel in (
            "skills/develop/SKILL.md",
            "skills/release/SKILL.md",
            "skills/arbor/references/real-workflow-chain-review.md",
            "skills/arbor/scripts/check_real_workflow_chains.py",
            "skills/arbor/scripts/check_plugin_adapters.py",
        ):
            source = PLUGIN_ROOT / rel
            cached = cache / rel
            require(cached.exists(), f"cache file missing: {cached}")
            require(source.read_text(encoding="utf-8") == cached.read_text(encoding="utf-8"), f"cache differs from source: {rel}")


def assert_session_start_hook(ctx: CaseContext, _: RuntimeResult | None) -> None:
    hook = ctx.plugin_root / "hooks/session-start"
    require(hook.exists(), "Claude SessionStart hook missing")
    payload = {
        "session_id": "real-workflow-chain-review",
        "transcript_path": str(ctx.workdir / "transcript.jsonl"),
        "cwd": str(ctx.workdir),
        "hook_event_name": "SessionStart",
        "source": "startup",
    }
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(ctx.plugin_root)
    proc = subprocess.run(
        [str(hook)],
        cwd=ctx.workdir,
        input=json.dumps(payload),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=env,
    )
    write(ctx.artifacts / "session-start.stdout.txt", proc.stdout)
    write(ctx.artifacts / "session-start.stderr.txt", proc.stderr)
    require(proc.returncode == 0, f"SessionStart failed: {proc.stderr}")
    for term in ("# Project Startup Context", "AGENTS.md", ".arbor/memory.md", "git status"):
        require(term in proc.stdout, f"SessionStart output missing {term}")


def assert_runner_tracked(_: CaseContext, __: RuntimeResult | None) -> None:
    proc = run(["git", "check-ignore", "-v", "plugins/arbor/skills/arbor/scripts/check_real_workflow_chains.py"], cwd=REPO_ROOT)
    require(proc.returncode != 0, "real workflow runner is ignored")
    matrix = PLUGIN_ROOT / "skills/arbor/references/real-workflow-chain-review.md"
    require(matrix.exists(), "real workflow matrix missing")


def prompt_header(case_id: str) -> str:
    return (
        f"Arbor real workflow chain review case {case_id}. "
        "Use the actual Arbor skill when the prompt names one or when the request matches Arbor. "
        "Keep the final response concise but rendered for a user. Do not print raw workflow JSON. "
        "If you perform an Arbor workflow action, append a compact trace line to .arbor/e2e-trace.jsonl. "
    )


def agent_prompt(case_id: str, body: str) -> str:
    return prompt_header(case_id) + "\n\n" + textwrap.dedent(body).strip()


def make_cases() -> dict[str, CaseSpec]:
    common_assertions = [assert_success, assert_no_raw_schema]
    cases = [
        CaseSpec(
            "R01",
            "active planning continuation routes to brainstorm",
            "Based on my requirements, think through what to do and design a plan. "
            "This is for the active cleanup context in cleanup_notes.md.",
            setup_planning_context,
            [
                *common_assertions,
                assert_contains(
                    "Understanding And Recommendation",
                    "Suggested Small Steps",
                    "How I Would Validate Each Step",
                    "Expected Delivery",
                ),
                assert_file_exists(".arbor/workflow/features.json"),
                assert_file_exists("docs/review"),
                assert_file_equals("src/example.py", "def answer() -> int:\n    return 41\n"),
            ],
        ),
        CaseSpec(
            "R02",
            "explicit brainstorm produces rendered checkpoint",
            agent_prompt("R02", "$brainstorm plan the cleanup work from cleanup_notes.md before implementation."),
            setup_planning_context,
            [
                *common_assertions,
                assert_contains(
                    "Understanding And Recommendation",
                    "How I Would Handle This",
                    "Suggested Small Steps",
                    "How I Would Validate Each Step",
                    "Default Decisions I Made",
                    "Expected Delivery",
                    "Next",
                ),
                assert_file_exists("docs/review"),
            ],
        ),
        CaseSpec(
            "R03",
            "standalone direct answer does not create Arbor artifacts",
            "Explain what the function in src/example.py does. Do not plan future work.",
            common_project,
            [
                *common_assertions,
                assert_any_contains("answer", "41"),
                assert_file_not_exists(".arbor/workflow"),
                assert_file_not_exists("docs/review"),
                assert_file_not_exists(".arbor/e2e-trace.jsonl"),
            ],
        ),
        CaseSpec(
            "R04",
            "active review routes to evaluate",
            agent_prompt("R04", "Review the active Arbor developer handoff and validate it independently."),
            setup_review_context,
            [*common_assertions, assert_file_contains("docs/review/F-review.md", "Evaluator"), assert_any_contains("Evaluation", "Findings")],
        ),
        CaseSpec(
            "R05",
            "runtime traceback enters Arbor",
            agent_prompt(
                "R05",
                """
                I hit this runtime failure while running the active pipeline:
                Traceback (most recent call last):
                  File "run_pipeline.py", line 4, in <module>
                    raise RuntimeError("pipeline blocked: answer mismatch")
                RuntimeError: pipeline blocked: answer mismatch
                Fix or plan the Arbor-managed debugging path and record replay evidence.
                """,
            ),
            setup_traceback_context,
            [*common_assertions, assert_any_contains("traceback", "pipeline", "debug", "replay")],
        ),
        CaseSpec(
            "R06",
            "evaluate strictness",
            agent_prompt("R06", "$evaluate independently validate the completed developer handoff in docs/review/F-review.md."),
            setup_review_context,
            [*common_assertions, assert_file_contains("docs/review/F-review.md", "Evaluator"), assert_any_contains("negative", "static", "contract", "independent")],
        ),
        CaseSpec(
            "R07",
            "evaluate rendered output",
            agent_prompt("R07", "$evaluate validate docs/review/F-review.md and make the visible output readable."),
            setup_review_context,
            [*common_assertions, assert_rendered_table("Evaluation", "Findings", "Scenario")],
        ),
        CaseSpec(
            "R08",
            "output layer captured",
            agent_prompt("R08", "$evaluate validate the active review handoff and render the user-facing packet."),
            setup_review_context,
            [*common_assertions, assert_rendered_table("Evaluation", "Findings", "What I Checked", "Scenario")],
        ),
        CaseSpec(
            "R09",
            "converge loop routing",
            agent_prompt("R09", "$converge decide whether the review loop in docs/review/F-review.md has converged."),
            setup_review_context,
            [*common_assertions, assert_any_contains("converge", "develop", "release", "blocking")],
        ),
        CaseSpec(
            "R10",
            "release checkpoint creates local commit",
            agent_prompt("R10", "$release checkpoint the completed develop handoff before evaluate."),
            setup_develop_context,
            [*common_assertions, assert_git_commit_created, assert_no_public_release],
        ),
        CaseSpec(
            "R11",
            "develop success checkpoints",
            agent_prompt("R11", "$develop implement F-dev, run the planned check, append developer evidence, and checkpoint before evaluate."),
            setup_develop_context,
            [*common_assertions, assert_file_contains("src/example.py", "42"), assert_file_contains("docs/review/F-dev.md", "Developer"), assert_git_commit_created],
            timeout_seconds=360,
        ),
        CaseSpec(
            "R12",
            "release public actions gated",
            agent_prompt("R12", "$release prepare finalization for F-review, but do not push, tag, or publish without explicit authorization."),
            setup_converged_release_context,
            [*common_assertions, assert_any_contains("confirmation", "authorize", "prepared", "release"), assert_no_public_release],
        ),
        CaseSpec(
            "R13",
            "explicit publish path",
            agent_prompt("R13", "$release finalize F-review with local commit only. Do not push to a remote or publish a package."),
            setup_converged_release_context,
            [*common_assertions, assert_any_contains("commit", "release"), assert_no_public_release],
        ),
        CaseSpec(
            "R14",
            "cache sync matches source",
            "",
            setup_local_only,
            [assert_cache_matches_source],
            runtimes=(RUNTIME_LOCAL,),
            requires_agent=False,
        ),
        CaseSpec(
            "R15",
            "startup context fresh overview",
            agent_prompt("R15", "What is this project doing? Use Arbor startup context before answering."),
            setup_startup_context,
            [*common_assertions, assert_any_contains("Project", "Arbor", "git", "memory")],
        ),
        CaseSpec(
            "R16",
            "Codex startup uses AGENTS bootstrap",
            agent_prompt("R16", "What is this project doing? Do not rely only on .codex/hooks.json; use AGENTS startup protocol."),
            setup_startup_context,
            [*common_assertions, assert_any_contains("AGENTS", "startup", "memory", "git")],
            runtimes=(RUNTIME_CODEX,),
        ),
        CaseSpec(
            "R17",
            "memory updated for uncommitted Arbor work",
            agent_prompt("R17", "$arbor refresh project memory for the uncommitted Arbor-managed edit in src/example.py."),
            setup_dirty_memory_context,
            [*common_assertions, assert_memory_has_inflight],
        ),
        CaseSpec(
            "R18",
            "memory pruned after commit",
            agent_prompt("R18", "$release checkpoint the resolved Arbor state and prune resolved memory entries."),
            setup_develop_context,
            [*common_assertions, assert_memory_pruned],
        ),
        CaseSpec(
            "R19",
            "memory hygiene trigger corpus",
            agent_prompt("R19", "$arbor review whether memory hygiene should trigger for the current dirty Arbor workflow state."),
            setup_dirty_memory_context,
            [*common_assertions, assert_any_contains("memory", "trigger", "hygiene")],
        ),
        CaseSpec(
            "R20",
            "session-start hook real output",
            "",
            setup_startup_context,
            [assert_session_start_hook],
            runtimes=(RUNTIME_LOCAL,),
            requires_agent=False,
        ),
        CaseSpec(
            "R21",
            "all skill rendered output smoke",
            agent_prompt("R21", "$evaluate validate the active handoff, then summarize the next release checkpoint in readable terms."),
            setup_review_context,
            [*common_assertions, assert_any_contains("Evaluation", "Findings")],
        ),
        CaseSpec(
            "R22",
            "single skill handoff sufficiency",
            agent_prompt("R22", "$develop use the existing review context for F-dev and produce a handoff that release/evaluate can continue."),
            setup_develop_context,
            [*common_assertions, assert_file_contains("docs/review/F-dev.md", "Developer"), assert_any_contains("checkpoint", "evaluate")],
        ),
        CaseSpec(
            "R23",
            "mid-chain entry blocks or proceeds correctly",
            agent_prompt("R23", "$converge use the available review evidence. If evidence is incomplete, block with readable missing evidence instead of inventing state."),
            setup_review_context,
            [*common_assertions, assert_any_contains("missing", "evidence", "converge", "blocked", "release")],
        ),
        CaseSpec(
            "R24",
            "real runner is tracked",
            "",
            setup_local_only,
            [assert_runner_tracked],
            runtimes=(RUNTIME_LOCAL,),
            requires_agent=False,
        ),
        CaseSpec(
            "R25",
            "Codex Claude semantic parity",
            agent_prompt("R25", "$arbor explain this project from startup context and keep the output concise."),
            setup_startup_context,
            [*common_assertions, assert_any_contains("Arbor", "project", "memory")],
        ),
        CaseSpec(
            "R26",
            "review loop does not close from developer self-test alone",
            agent_prompt("R26", "$converge decide whether F-review can close. Do not accept from developer self-test alone."),
            setup_review_context,
            [*common_assertions, assert_any_contains("evaluate", "evaluator", "missing", "cannot", "not")],
        ),
        CaseSpec(
            "R27",
            "split-context planning continuation routes to brainstorm",
            "Previous context: the active task is code cleanup. The user already named five script entrypoints "
            "and asked for a safe cleanup plan based on repository evidence.\n"
            "User: Okay. Based on my requirements, let's think through what to do and design a plan.",
            setup_planning_context,
            [
                *common_assertions,
                assert_contains(
                    "Understanding And Recommendation",
                    "Suggested Small Steps",
                    "How I Would Validate Each Step",
                    "Expected Delivery",
                ),
                assert_file_exists(".arbor/workflow/features.json"),
                assert_file_exists("docs/review"),
                assert_file_equals("src/example.py", "def answer() -> int:\n    return 41\n"),
            ],
        ),
        CaseSpec(
            "R28",
            "AGENTS project map drift is updated",
            agent_prompt(
                "R28",
                "$arbor update AGENTS.md Project Map for the new durable tools/ directory before release. "
                "Use the AGENTS drift hook packet and keep current-session progress out of AGENTS.md.",
            ),
            setup_project_map_drift_context,
            [
                *common_assertions,
                assert_file_contains("AGENTS.md", "Project Map", "tools/"),
                assert_any_contains("AGENTS", "Project Map", "tools"),
            ],
            runtimes=(RUNTIME_CODEX,),
        ),
    ]
    return {case.case_id: case for case in cases}


def selected_cases(all_cases: dict[str, CaseSpec], selector: str) -> list[CaseSpec]:
    if selector == "all":
        return list(all_cases.values())
    ids = [item.strip().upper() for item in selector.split(",") if item.strip()]
    unknown = [case_id for case_id in ids if case_id not in all_cases]
    if unknown:
        raise SystemExit(f"unknown case ids: {', '.join(unknown)}")
    return [all_cases[case_id] for case_id in ids]


def selected_runtimes(runtime: str) -> tuple[str, ...]:
    if runtime == RUNTIME_ALL:
        return RUNTIMES
    if runtime == RUNTIME_LOCAL:
        return (RUNTIME_LOCAL,)
    return (runtime,)


def reset_artifact_dir(artifacts: Path) -> None:
    if artifacts.is_symlink() or artifacts.is_file():
        artifacts.unlink()
    elif artifacts.exists():
        shutil.rmtree(artifacts)
    artifacts.mkdir(parents=True, exist_ok=True)


def make_case_context(case_id: str, runtime: str, artifact_root: Path, plugin_root: Path) -> CaseContext:
    workdir = Path(tempfile.mkdtemp(prefix=f"arbor-{case_id.lower()}-{runtime}-", dir="/private/tmp"))
    artifacts = artifact_root / f"{case_id}-{runtime}"
    reset_artifact_dir(artifacts)
    write(artifacts / "workdir.txt", str(workdir) + "\n")
    return CaseContext(case_id, runtime, workdir, artifacts, plugin_root)


def run_case(case: CaseSpec, runtime: str, artifact_root: Path, plugin_root: Path, keep_workdirs: bool) -> CaseReport:
    ctx = make_case_context(case.case_id, runtime, artifact_root, plugin_root)
    result: RuntimeResult | None = None
    metadata = case_metadata(case)
    try:
        case.setup(ctx)
        if case.requires_agent:
            if not runtime_available(runtime):
                raise CaseFailure(f"runtime unavailable: {runtime}")
            result = run_runtime(ctx, case.prompt, case.timeout_seconds)
        for assertion in case.assertions:
            assertion(ctx, result)
        snapshot_state(ctx)
        command = result.command if result else ["local"]
        return CaseReport(
            case.case_id,
            case.title,
            runtime,
            STATUS_PASS,
            classify_success(ctx, case),
            metadata["category"],
            metadata["situation"],
            metadata["expected_chain"],
            str(ctx.artifacts),
            command=command,
        )
    except (CaseFailure, subprocess.TimeoutExpired) as exc:
        snapshot_state(ctx)
        command = result.command if result else ["local"]
        write(ctx.artifacts / "failure.txt", str(exc) + "\n")
        return CaseReport(
            case.case_id,
            case.title,
            runtime,
            STATUS_FAIL,
            classify_failure(exc),
            metadata["category"],
            metadata["situation"],
            metadata["expected_chain"],
            str(ctx.artifacts),
            reason=str(exc),
            command=command,
        )
    finally:
        if not keep_workdirs:
            shutil.rmtree(ctx.workdir, ignore_errors=True)


def write_report(path: Path, reports: list[CaseReport]) -> None:
    classification_counts = {
        classification: sum(report.classification == classification for report in reports)
        for classification in CLASSIFICATIONS
    }
    data = {
        "summary": {
            "passed": sum(report.status == STATUS_PASS for report in reports),
            "failed": sum(report.status == STATUS_FAIL for report in reports),
            "skipped": sum(report.status == STATUS_SKIP for report in reports),
            "total": len(reports),
            "classification_counts": classification_counts,
        },
        "reports": [
            {
                "case_id": report.case_id,
                "title": report.title,
                "runtime": report.runtime,
                "status": report.status,
                "classification": report.classification,
                "category": report.category,
                "situation": report.situation,
                "expected_chain": report.expected_chain,
                "artifact_dir": report.artifact_dir,
                "reason": report.reason,
                "command": report.command,
            }
            for report in reports
        ],
    }
    write(path, json.dumps(data, indent=2, sort_keys=True) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", choices=(RUNTIME_CODEX, RUNTIME_CLAUDE, RUNTIME_LOCAL, RUNTIME_ALL), default=RUNTIME_LOCAL)
    parser.add_argument("--cases", default="R14,R20,R24", help="Comma-separated case ids or 'all'.")
    parser.add_argument("--artifact-root", type=Path, default=Path("/private/tmp/arbor-real-workflow-chain-review"))
    parser.add_argument("--plugin-root", type=Path, default=PLUGIN_ROOT)
    parser.add_argument("--keep-workdirs", action="store_true", help="Keep temporary repositories for debugging.")
    parser.add_argument("--report", type=Path, default=None, help="Optional JSON report path.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    all_cases = make_cases()
    cases = selected_cases(all_cases, args.cases)
    runtimes = selected_runtimes(args.runtime)
    if args.artifact_root.exists() and not args.artifact_root.is_dir():
        print(f"real workflow chain checks failed: artifact root exists and is not a directory: {args.artifact_root}")
        return 1
    args.artifact_root.mkdir(parents=True, exist_ok=True)

    reports: list[CaseReport] = []
    for case in cases:
        for runtime in runtimes:
            metadata = case_metadata(case)
            if runtime not in case.runtimes:
                reports.append(
                    CaseReport(
                        case.case_id,
                        case.title,
                        runtime,
                        STATUS_SKIP,
                        CLASS_SKIPPED,
                        metadata["category"],
                        metadata["situation"],
                        metadata["expected_chain"],
                        "",
                        reason="runtime not required for case",
                    )
                )
                continue
            print(f"running: {case.case_id} {runtime} {case.title}", flush=True)
            report = run_case(case, runtime, args.artifact_root, args.plugin_root, args.keep_workdirs)
            reports.append(report)
            print(f"{report.status}/{report.classification}: {case.case_id} {runtime} {case.title}", flush=True)
            if report.reason:
                print(f"  reason: {report.reason}", flush=True)
            print(f"  artifacts: {report.artifact_dir}", flush=True)

    report_path = args.report or (args.artifact_root / "report.json")
    write_report(report_path, reports)
    failed = [report for report in reports if report.status == STATUS_FAIL]
    passed = [report for report in reports if report.status == STATUS_PASS]
    skipped = [report for report in reports if report.status == STATUS_SKIP]
    if failed:
        print(f"real workflow chain checks failed: {len(failed)} failure(s)")
        print(f"report: {report_path}")
        return 1
    if not passed:
        print("real workflow chain checks failed: no selected case/runtime pair executed")
        print(f"summary: passed=0 failed=0 skipped={len(skipped)} total={len(reports)}")
        print(f"report: {report_path}")
        return 1
    print(
        "real workflow chain checks passed: "
        f"passed={len(passed)} failed=0 skipped={len(skipped)} total={len(reports)}"
    )
    print(
        "classifications: "
        + " ".join(
            f"{classification}={sum(report.classification == classification for report in reports)}"
            for classification in CLASSIFICATIONS
        )
    )
    print(f"report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
