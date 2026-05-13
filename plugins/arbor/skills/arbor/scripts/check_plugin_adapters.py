#!/usr/bin/env python3
"""Validate Arbor plugin adapter structure and Claude hook smoke behavior."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def add_error(errors: list[str], message: str) -> None:
    errors.append(message)


def check(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        add_error(errors, message)


def load_json(path: Path, errors: list[str]) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        add_error(errors, f"missing JSON file: {path}")
        return {}
    except json.JSONDecodeError as exc:
        add_error(errors, f"invalid JSON in {path}: {exc}")
        return {}
    if not isinstance(data, dict):
        add_error(errors, f"JSON file must contain an object: {path}")
        return {}
    return data


def plugin_root_from_script() -> Path:
    return Path(__file__).resolve().parents[3]


def repo_root_from_plugin(plugin_root: Path) -> Path | None:
    if plugin_root.parent.name == "plugins":
        return plugin_root.parent.parent
    return None


def validate_manifests(plugin_root: Path, errors: list[str]) -> None:
    codex = load_json(plugin_root / ".codex-plugin" / "plugin.json", errors)
    claude = load_json(plugin_root / ".claude-plugin" / "plugin.json", errors)
    if not codex or not claude:
        return

    for field in ("name", "version", "description", "homepage", "repository", "license"):
        check(
            errors,
            codex.get(field) == claude.get(field),
            f"manifest field {field!r} must match between Codex and Claude manifests",
        )

    check(errors, codex.get("skills") == "./skills/", "Codex manifest must point at ./skills/")
    check(errors, isinstance(claude.get("keywords"), list), "Claude manifest must include keyword list")
    check(errors, "claude-code" in claude.get("keywords", []), "Claude manifest should include claude-code keyword")

    repo_root = repo_root_from_plugin(plugin_root)
    if repo_root is None:
        return
    marketplace = load_json(repo_root / ".claude-plugin" / "marketplace.json", errors)
    plugins = marketplace.get("plugins")
    check(errors, isinstance(plugins, list), "Claude marketplace must define plugins list")
    if isinstance(plugins, list):
        matches = [entry for entry in plugins if isinstance(entry, dict) and entry.get("name") == codex.get("name")]
        check(errors, len(matches) == 1, "Claude marketplace must contain exactly one Arbor entry")
        if matches:
            entry = matches[0]
            check(errors, entry.get("source") == "./plugins/arbor", "Claude marketplace source must point at ./plugins/arbor")


def validate_project_hook_contract(plugin_root: Path, errors: list[str]) -> None:
    import sys

    scripts_dir = plugin_root / "skills" / "arbor" / "scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from register_project_hooks import ARBOR_HOOKS
    finally:
        sys.path.pop(0)

    memory_hook = next(
        (hook for hook in ARBOR_HOOKS if isinstance(hook, dict) and hook.get("id") == "arbor.in_session_memory_hygiene"),
        None,
    )
    check(errors, isinstance(memory_hook, dict), "memory hygiene hook must be registered")
    if not isinstance(memory_hook, dict):
        return

    trigger_policy = memory_hook.get("trigger_policy")
    check(errors, isinstance(trigger_policy, dict), "memory hygiene hook must include trigger_policy")
    if not isinstance(trigger_policy, dict):
        return

    positives = trigger_policy.get("positive_cases")
    negatives = trigger_policy.get("negative_cases")
    case_corpus = trigger_policy.get("case_corpus")
    check(errors, isinstance(positives, list) and len(positives) >= 18, "memory hygiene hook needs broad positive trigger cases")
    check(errors, isinstance(negatives, list) and len(negatives) >= 6, "memory hygiene hook needs negative trigger contrast cases")
    if isinstance(positives, list):
        positive_text = "\n".join(str(item) for item in positives)
        for term in (
            "after any Arbor-managed file edit",
            "before handing off from develop",
            "before pausing",
            "before running release preflight",
            "after syncing local plugin caches",
            "ignored local review",
        ):
            check(errors, term in positive_text, f"memory hygiene positive cases missing `{term}`")
    if isinstance(negatives, list):
        negative_text = "\n".join(str(item) for item in negatives)
        for term in (
            "clean git status",
            "direct one-off explanation",
            "read-only inspection",
            "user explicitly forbids file writes",
            "unrelated to Arbor",
        ):
            check(errors, term in negative_text, f"memory hygiene negative cases missing `{term}`")
    check(
        errors,
        "high_recall" in str(trigger_policy.get("mode", "")),
        "memory hygiene trigger policy must be high recall",
    )
    validate_memory_hygiene_case_corpus(errors, case_corpus)


def validate_memory_hygiene_case_corpus(errors: list[str], case_corpus: object) -> None:
    check(errors, isinstance(case_corpus, list), "memory hygiene hook must include a machine-checkable case_corpus list")
    if not isinstance(case_corpus, list):
        return

    trigger_cases = [case for case in case_corpus if isinstance(case, dict) and case.get("expected") == "trigger"]
    suppress_cases = [case for case in case_corpus if isinstance(case, dict) and case.get("expected") == "suppress"]
    check(errors, len(trigger_cases) >= 20, "memory hygiene case_corpus must include at least 20 trigger cases")
    check(errors, len(suppress_cases) >= 8, "memory hygiene case_corpus must include at least 8 suppress cases")

    ids: list[str] = []
    seen_situations: set[str] = set()
    required_fields = {"id", "situation", "expected", "git_state", "arbor_managed", "checkpoint", "rationale"}
    for index, case in enumerate(case_corpus, start=1):
        if not isinstance(case, dict):
            add_error(errors, f"memory hygiene case_corpus entry {index} must be an object")
            continue
        missing = sorted(required_fields - case.keys())
        check(errors, not missing, f"memory hygiene case {index} missing fields: {', '.join(missing)}")

        case_id = case.get("id")
        situation = case.get("situation")
        expected = case.get("expected")
        check(errors, isinstance(case_id, str) and bool(case_id.strip()), f"memory hygiene case {index} needs a non-empty id")
        check(errors, isinstance(situation, str) and bool(situation.strip()), f"memory hygiene case {index} needs a situation")
        check(errors, expected in {"trigger", "suppress"}, f"memory hygiene case {index} expected must be trigger or suppress")
        check(errors, isinstance(case.get("git_state"), str), f"memory hygiene case {index} needs a git_state string")
        check(errors, isinstance(case.get("arbor_managed"), bool), f"memory hygiene case {index} needs arbor_managed boolean")
        check(errors, isinstance(case.get("checkpoint"), str), f"memory hygiene case {index} needs checkpoint string")
        check(errors, isinstance(case.get("rationale"), str), f"memory hygiene case {index} needs rationale string")
        if isinstance(case_id, str):
            ids.append(case_id)
        if isinstance(situation, str):
            check(errors, situation not in seen_situations, f"duplicate memory hygiene situation: {situation}")
            seen_situations.add(situation)

    check(errors, len(ids) == len(set(ids)), "memory hygiene case ids must be unique")
    trigger_text = "\n".join(str(case.get("checkpoint", "")) + " " + str(case.get("situation", "")) for case in trigger_cases)
    suppress_text = "\n".join(str(case.get("checkpoint", "")) + " " + str(case.get("situation", "")) for case in suppress_cases)
    for term in (
        "develop",
        "evaluate",
        "converge",
        "release",
        "session_boundary",
        "cache_sync",
        "failed_check",
        "local_evidence",
    ):
        check(errors, term in trigger_text, f"memory hygiene trigger case_corpus missing scenario class `{term}`")
    for term in ("direct", "read_only", "no_write", "out_of_scope", "unrelated"):
        check(errors, term in suppress_text, f"memory hygiene suppress case_corpus missing scenario class `{term}`")


def validate_claude_hook_structure(plugin_root: Path, errors: list[str]) -> None:
    hooks_json = load_json(plugin_root / "hooks" / "hooks.json", errors)
    hooks = hooks_json.get("hooks")
    check(errors, isinstance(hooks, dict), "hooks/hooks.json must define hooks object")
    if isinstance(hooks, dict):
        check(errors, set(hooks) == {"SessionStart"}, "Claude adapter should only define SessionStart in this release")
        session_hooks = hooks.get("SessionStart")
        check(errors, isinstance(session_hooks, list) and bool(session_hooks), "SessionStart hook must be a non-empty list")

    session_start = plugin_root / "hooks" / "session-start"
    check(errors, session_start.is_file(), "hooks/session-start must exist")
    check(errors, os.access(session_start, os.X_OK), "hooks/session-start must be executable")
    check(errors, not (plugin_root / "hooks" / "pre-compact").exists(), "PreCompact adapter must not ship in this release")
    check(errors, not (plugin_root / "agents").exists(), "plugin-level agents directory is out of scope for this release")


def run_session_start(plugin_root: Path, project_root: Path, source: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    payload = {
        "session_id": "adapter-smoke",
        "transcript_path": str(project_root / "transcript.jsonl"),
        "cwd": str(project_root),
        "hook_event_name": "SessionStart",
        "source": source,
    }
    return subprocess.run(
        [str(plugin_root / "hooks" / "session-start")],
        input=json.dumps(payload),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=env,
    )


def validate_session_start_smoke(plugin_root: Path, errors: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="arbor-claude-adapter-") as tmp:
        project = Path(tmp)
        (project / ".arbor").mkdir()
        (project / "AGENTS.md").write_text("# Project Guide\n\n" + ("Guide line.\n" * 1400), encoding="utf-8")
        (project / ".arbor" / "memory.md").write_text("# Arbor Memory\n\n- Pending note.\n", encoding="utf-8")
        subprocess.run(["git", "init"], cwd=project, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, text=True)

        proc = run_session_start(plugin_root, project, "startup")
        check(errors, proc.returncode == 0, f"SessionStart startup smoke failed: {proc.stderr.strip()}")
        output = proc.stdout
        check(errors, len(output) <= 9500, "SessionStart startup output must stay within adapter budget")
        for expected in ("# Project Startup Context", "## 1. AGENTS.md", "## 2. formatted git log", "## 3. .arbor/memory.md", "## 4. git status"):
            check(errors, expected in output, f"SessionStart startup output missing {expected!r}")
        check(errors, "truncated - Arbor SessionStart context exceeded" in output, "large startup packet should include truncation notice")

        clear_proc = run_session_start(plugin_root, project, "clear")
        check(errors, clear_proc.returncode == 0, f"SessionStart clear smoke failed: {clear_proc.stderr.strip()}")
        check(errors, clear_proc.stdout == "", "SessionStart clear source must not inject context")


def validate_in_flight_memory_contract(plugin_root: Path, errors: list[str]) -> None:
    required = {
        "skills/arbor/SKILL.md": [
            "Every Arbor-managed workflow that leaves uncommitted project changes must ensure `.arbor/memory.md` exists",
            "Do not rely only on runtime hooks",
        ],
        "skills/arbor/references/memory-template.md": [
            "Any uncommitted Arbor-managed workflow state must have a short in-flight entry here",
        ],
        "skills/brainstorm/SKILL.md": [
            "Before stopping with uncommitted Arbor workflow changes, ensure `.arbor/memory.md` exists",
        ],
        "skills/develop/SKILL.md": [
            "**Update in-flight memory**",
            "If uncommitted Arbor workflow changes remain, did I create or refresh `.arbor/memory.md`",
        ],
        "skills/evaluate/SKILL.md": [
            "**Update in-flight memory**",
            "If uncommitted Arbor workflow changes remain, did I create or refresh `.arbor/memory.md`",
        ],
        "skills/converge/SKILL.md": [
            "**Update in-flight memory**",
            "If uncommitted Arbor workflow changes remain, did I create or refresh `.arbor/memory.md`",
        ],
        "skills/release/SKILL.md": [
            "**Update session memory**",
            "Do not leave unresolved uncommitted Arbor workflow state without an up-to-date `.arbor/memory.md`",
        ],
    }
    for rel_path, terms in required.items():
        text = (plugin_root / rel_path).read_text(encoding="utf-8")
        for term in terms:
            check(errors, term in text, f"{rel_path} missing in-flight memory contract term `{term}`")


def main() -> int:
    errors: list[str] = []
    plugin_root = plugin_root_from_script()
    validate_manifests(plugin_root, errors)
    validate_project_hook_contract(plugin_root, errors)
    validate_claude_hook_structure(plugin_root, errors)
    validate_session_start_smoke(plugin_root, errors)
    validate_in_flight_memory_contract(plugin_root, errors)

    if errors:
        print("plugin adapter checks failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("plugin adapter checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
