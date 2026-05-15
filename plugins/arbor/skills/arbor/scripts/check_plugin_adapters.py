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


def validate_startup_bootstrap_contract(plugin_root: Path, errors: list[str]) -> None:
    codex = load_json(plugin_root / ".codex-plugin" / "plugin.json", errors)
    claude = load_json(plugin_root / ".claude-plugin" / "plugin.json", errors)
    agents_template = (plugin_root / "skills" / "arbor" / "references" / "agents-template.md").read_text(encoding="utf-8")
    arbor_skill = (plugin_root / "skills" / "arbor" / "SKILL.md").read_text(encoding="utf-8")

    for term in (
        "## Startup Protocol",
        "fresh or resumed session",
        "project overview questions",
        "recent formatted git history",
        ".arbor/memory.md",
        "git status --short",
        "Do not treat `.codex/hooks.json` as proof",
    ):
        check(errors, term in agents_template, f"agents template missing startup bootstrap term `{term}`")

    for term in (
        "answering what a project does",
        "project-overview prompts",
        "Do not assume `.codex/hooks.json` has already injected",
        "`AGENTS.md` Startup Protocol",
    ):
        check(errors, term in arbor_skill, f"arbor skill missing startup bootstrap term `{term}`")

    for manifest_name, manifest in (("Codex", codex), ("Claude", claude)):
        description = str(manifest.get("description", ""))
        check(
            errors,
            "project overview/resume requests" in description,
            f"{manifest_name} manifest description must mention project overview/resume startup context",
        )

    interface = codex.get("interface")
    if isinstance(interface, dict):
        prompts = interface.get("defaultPrompt", [])
        default_prompt = "\n".join(str(item) for item in prompts)
        check(errors, isinstance(prompts, list) and len(prompts) <= 3, "Codex defaultPrompt must contain at most 3 prompts")
        check(
            errors,
            "Resume or explain this repo with Arbor context" in default_prompt,
            "Codex defaultPrompt must include project overview startup-context example",
        )


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

    guide_hook = next(
        (hook for hook in ARBOR_HOOKS if isinstance(hook, dict) and hook.get("id") == "arbor.goal_constraint_drift"),
        None,
    )
    validate_guide_drift_hook_contract(errors, guide_hook)


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


def validate_guide_drift_hook_contract(errors: list[str], guide_hook: object) -> None:
    check(errors, isinstance(guide_hook, dict), "AGENTS guide drift hook must be registered")
    if not isinstance(guide_hook, dict):
        return

    reads_text = "\n".join(str(item) for item in guide_hook.get("reads", []))
    for term in (
        "top-level project structure",
        "mapped path validation",
        "git status --short --untracked-files=all",
    ):
        check(errors, term in reads_text, f"AGENTS guide drift hook reads missing `{term}`")

    trigger_policy = guide_hook.get("trigger_policy")
    check(errors, isinstance(trigger_policy, dict), "AGENTS guide drift hook must include trigger_policy")
    if not isinstance(trigger_policy, dict):
        return

    check(
        errors,
        "high_recall" in str(trigger_policy.get("mode", "")),
        "AGENTS guide drift trigger policy must be high recall",
    )
    positives = trigger_policy.get("positive_cases")
    negatives = trigger_policy.get("negative_cases")
    case_corpus = trigger_policy.get("case_corpus")
    check(errors, isinstance(positives, list) and len(positives) >= 5, "AGENTS guide drift needs trigger cases")
    check(errors, isinstance(negatives, list) and len(negatives) >= 3, "AGENTS guide drift needs suppress cases")
    policy_text = "\n".join(str(item) for item in (positives or [])) + "\n" + str(trigger_policy.get("decision_rule", ""))
    for term in (
        "new top-level",
        "new skill",
        "before release",
        "Project Map Drift Candidates",
        "update-needed",
    ):
        check(errors, term in policy_text, f"AGENTS guide drift trigger policy missing `{term}`")
    validate_guide_drift_case_corpus(errors, case_corpus)


def validate_guide_drift_case_corpus(errors: list[str], case_corpus: object) -> None:
    check(errors, isinstance(case_corpus, list), "AGENTS guide drift hook must include case_corpus")
    if not isinstance(case_corpus, list):
        return

    trigger_cases = [case for case in case_corpus if isinstance(case, dict) and case.get("expected") == "trigger"]
    suppress_cases = [case for case in case_corpus if isinstance(case, dict) and case.get("expected") == "suppress"]
    check(errors, len(trigger_cases) >= 5, "AGENTS guide drift case_corpus must include at least 5 trigger cases")
    check(errors, len(suppress_cases) >= 3, "AGENTS guide drift case_corpus must include at least 3 suppress cases")

    ids: list[str] = []
    required_fields = {"id", "situation", "expected", "map_area", "rationale"}
    for index, case in enumerate(case_corpus, start=1):
        if not isinstance(case, dict):
            add_error(errors, f"AGENTS guide drift case_corpus entry {index} must be an object")
            continue
        missing = sorted(required_fields - case.keys())
        check(errors, not missing, f"AGENTS guide drift case {index} missing fields: {', '.join(missing)}")
        case_id = case.get("id")
        expected = case.get("expected")
        situation = case.get("situation")
        check(errors, isinstance(case_id, str) and bool(case_id.strip()), f"AGENTS guide drift case {index} needs id")
        check(errors, isinstance(situation, str) and bool(situation.strip()), f"AGENTS guide drift case {index} needs situation")
        check(errors, expected in {"trigger", "suppress"}, f"AGENTS guide drift case {index} expected must be trigger or suppress")
        if isinstance(case_id, str):
            ids.append(case_id)
    check(errors, len(ids) == len(set(ids)), "AGENTS guide drift case ids must be unique")


def validate_agents_guide_drift_smoke(plugin_root: Path, errors: list[str]) -> None:
    import sys

    script = plugin_root / "skills" / "arbor" / "scripts" / "run_agents_guide_drift_hook.py"
    smoke_cases = (
        (
            "missing tools directory",
            "# Agent Guide\n\n## Project Map\n\n- `src/`: existing code.\n",
            ("src", "tools"),
            ("Status: update-needed", "`tools/`"),
        ),
        (
            "stale legacy directory",
            "# Agent Guide\n\n## Project Map\n\n- `src/`: existing code.\n- `legacy/`: removed code.\n",
            ("src",),
            ("Status: update-needed", "stale mapped path entries", "`legacy/`"),
        ),
        (
            "prose mention is not a map entry",
            "# Agent Guide\n\n## Project Map\n\n- `src/`: existing code.\n\nProject tools are discussed in docs.\n",
            ("src", "tools"),
            ("Status: update-needed", "`tools/`"),
        ),
        (
            "stale stable subpath",
            "# Agent Guide\n\n## Project Map\n\n- `plugins/arbor/`: removed plugin package.\n",
            ("plugins/new",),
            ("Status: update-needed", "stale mapped path entries", "`plugins/arbor/`"),
        ),
    )
    with tempfile.TemporaryDirectory(prefix="arbor-guide-drift-") as tmp:
        base = Path(tmp)
        for index, (label, agents_text, dirs, required_terms) in enumerate(smoke_cases, start=1):
            project = base / f"case-{index}"
            project.mkdir()
            (project / "AGENTS.md").write_text(agents_text, encoding="utf-8")
            for dirname in dirs:
                (project / dirname).mkdir(parents=True)
            proc = subprocess.run(
                [sys.executable, str(script), "--root", str(project)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            check(errors, proc.returncode == 0, f"AGENTS guide drift smoke failed for {label}: {proc.stderr}")
            output = proc.stdout
            for term in (
                "Project Map Snapshot",
                "Project Map Drift Candidates",
                "before handoff or release",
                *required_terms,
            ):
                check(errors, term in output, f"AGENTS guide drift smoke {label} missing `{term}`")


def validate_claude_hook_structure(plugin_root: Path, errors: list[str]) -> None:
    hooks_json = load_json(plugin_root / "hooks" / "hooks.json", errors)
    hooks = hooks_json.get("hooks")
    check(errors, isinstance(hooks, dict), "hooks/hooks.json must define hooks object")
    if isinstance(hooks, dict):
        check(
            errors,
            set(hooks) == {"SessionStart", "Stop"},
            "Claude adapter should define exactly the SessionStart and Stop hooks",
        )
        session_hooks = hooks.get("SessionStart")
        check(errors, isinstance(session_hooks, list) and bool(session_hooks), "SessionStart hook must be a non-empty list")
        stop_hooks = hooks.get("Stop")
        check(errors, isinstance(stop_hooks, list) and bool(stop_hooks), "Stop hook must be a non-empty list")

    session_start = plugin_root / "hooks" / "session-start"
    check(errors, session_start.is_file(), "hooks/session-start must exist")
    check(errors, os.access(session_start, os.X_OK), "hooks/session-start must be executable")
    stop_adapter = plugin_root / "hooks" / "stop-memory-hygiene"
    check(errors, stop_adapter.is_file(), "hooks/stop-memory-hygiene must exist")
    check(errors, os.access(stop_adapter, os.X_OK), "hooks/stop-memory-hygiene must be executable")
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


def run_stop_hook(plugin_root: Path, project_root: Path, stop_hook_active: bool) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    payload = {
        "session_id": "adapter-smoke",
        "transcript_path": str(project_root / "transcript.jsonl"),
        "cwd": str(project_root),
        "hook_event_name": "Stop",
        "stop_hook_active": stop_hook_active,
    }
    return subprocess.run(
        [str(plugin_root / "hooks" / "stop-memory-hygiene")],
        input=json.dumps(payload),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=env,
    )


def _git(args: list[str], cwd: Path) -> None:
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "Arbor Adapter Smoke",
            "GIT_AUTHOR_EMAIL": "arbor@example.com",
            "GIT_COMMITTER_NAME": "Arbor Adapter Smoke",
            "GIT_COMMITTER_EMAIL": "arbor@example.com",
        }
    )
    subprocess.run(["git", *args], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, text=True, env=env)


def validate_stop_memory_hygiene_smoke(plugin_root: Path, errors: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="arbor-claude-stop-adapter-") as tmp:
        project = Path(tmp)
        (project / ".arbor").mkdir()
        (project / ".arbor" / "memory.md").write_text("# Arbor Memory\n\n- Pending note.\n", encoding="utf-8")
        (project / "AGENTS.md").write_text("# Project Guide\n", encoding="utf-8")
        _git(["init"], project)
        _git(["add", "-A"], project)
        _git(["commit", "-m", "init"], project)

        # Clean worktree: the adapter must stay silent and allow the stop.
        clean_proc = run_stop_hook(plugin_root, project, stop_hook_active=False)
        check(errors, clean_proc.returncode == 0, f"Stop clean smoke failed: {clean_proc.stderr.strip()}")
        check(errors, clean_proc.stdout == "", "Stop adapter must stay silent on a clean worktree")

        # Dirty worktree: the adapter must block with the memory hygiene packet.
        (project / "feature.txt").write_text("work in progress\n", encoding="utf-8")
        dirty_proc = run_stop_hook(plugin_root, project, stop_hook_active=False)
        check(errors, dirty_proc.returncode == 0, f"Stop dirty smoke failed: {dirty_proc.stderr.strip()}")
        try:
            decision = json.loads(dirty_proc.stdout)
        except json.JSONDecodeError:
            add_error(errors, "Stop adapter must emit JSON when blocking a dirty worktree")
            decision = {}
        check(errors, decision.get("decision") == "block", "Stop adapter must block when the worktree is dirty")
        check(
            errors,
            "# Memory Hygiene Context" in str(decision.get("reason", "")),
            "Stop block reason must carry the memory hygiene packet",
        )

        # stop_hook_active guard: the adapter must never block a continuation.
        active_proc = run_stop_hook(plugin_root, project, stop_hook_active=True)
        check(errors, active_proc.returncode == 0, f"Stop active smoke failed: {active_proc.stderr.strip()}")
        check(errors, active_proc.stdout == "", "Stop adapter must allow the stop when stop_hook_active is set")

    # Non-Arbor project: the adapter must stay silent even when dirty.
    with tempfile.TemporaryDirectory(prefix="arbor-claude-stop-nonarbor-") as tmp:
        project = Path(tmp)
        _git(["init"], project)
        (project / "feature.txt").write_text("unrelated work\n", encoding="utf-8")
        proc = run_stop_hook(plugin_root, project, stop_hook_active=False)
        check(errors, proc.returncode == 0, f"Stop non-Arbor smoke failed: {proc.stderr.strip()}")
        check(errors, proc.stdout == "", "Stop adapter must stay silent in a non-Arbor project")


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


def validate_rendered_checkpoint_contract(plugin_root: Path, errors: list[str]) -> None:
    required = {
        "skills/brainstorm/SKILL.md": [
            "do not stop with only chat prose",
            "create a durable brainstorm checkpoint",
            "Missing details become an explicit pending question",
            "Use the following section headings exactly",
            "Understanding And Recommendation",
            "Suggested Small Steps",
            "How I Would Validate Each Step",
            "Expected Delivery",
        ],
        "skills/intake/SKILL.md": [
            "active engineering planning continuations",
            "the downstream visible answer must be the standard brainstorm checkpoint",
            "Understanding And Recommendation",
            "Suggested Small Steps",
            "How I Would Validate Each Step",
            "Expected Delivery",
        ],
        "skills/evaluate/SKILL.md": [
            "The normal visible final response MUST include these exact Markdown headings",
            "`**Findings First**`",
            "`**Scenario Tests**`",
            "A shorter prose-only",
            "evaluation is not an acceptable `evaluate` checkpoint",
        ],
    }
    for rel_path, terms in required.items():
        text = (plugin_root / rel_path).read_text(encoding="utf-8")
        for term in terms:
            check(errors, term in text, f"{rel_path} missing rendered checkpoint contract term `{term}`")


def validate_develop_checkpoint_commit_contract(plugin_root: Path, errors: list[str]) -> None:
    repo_root = repo_root_from_plugin(plugin_root)
    required = {
        "skills/develop/SKILL.md": [
            "automatic local developer checkpoint commit before `evaluate`",
            "`release(checkpoint_develop)` creates the local checkpoint commit",
            "policy authorization for a local checkpoint commit",
        ],
        "skills/develop/references/develop-boundary.md": [
            "automatic local developer checkpoint commit before `evaluate`",
            "policy authorization for a local developer checkpoint commit",
        ],
        "skills/release/SKILL.md": [
            "policy-authorized checkpoint commits",
            "For `checkpoint_develop`, that means creating a local checkpoint commit",
            "Local checkpoint commits after successful develop are internal workflow actions",
            "finalization commits and public actions require explicit user authorization",
            "allowing policy-authorized checkpoint commits",
        ],
        "skills/release/references/release-boundary.md": [
            "create a local checkpoint commit after `develop.ready_for_evaluate`",
            "local git commits are internal workflow actions authorized by active workflow checkpoint policy",
            "block rather than silently continue if `checkpoint_develop` lacks local commit authorization",
        ],
    }
    if repo_root is not None:
        required["README.md"] = [
            "release(checkpoint_develop: local commit)",
            "automatic local checkpoint commit before `evaluate`",
            "gating finalization commit, push, PR, tag, and publish behind explicit user authorization",
        ]

    for rel_path, terms in required.items():
        base = repo_root if rel_path == "README.md" and repo_root is not None else plugin_root
        text = (base / rel_path).read_text(encoding="utf-8")
        for term in terms:
            check(errors, term in text, f"{rel_path} missing develop checkpoint commit term `{term}`")


def validate_real_workflow_chain_review_contract(plugin_root: Path, errors: list[str]) -> None:
    real_review = plugin_root / "skills" / "arbor" / "references" / "real-workflow-chain-review.md"
    real_runner = plugin_root / "skills" / "arbor" / "scripts" / "check_real_workflow_chains.py"
    check(errors, real_review.is_file(), "real workflow chain review matrix must be published as a skill reference")
    check(errors, real_runner.is_file(), "real workflow chain runner must be published as a skill script")
    if not real_review.is_file():
        return

    text = real_review.read_text(encoding="utf-8")
    runner_text = real_runner.read_text(encoding="utf-8") if real_runner.is_file() else ""
    for term in (
        "real Codex or Claude Code process",
        "captured final rendered response text",
        "Static checks and JSONL fixture checks are preflight only",
        "Ignored simulation fixtures and baseline scripts",
        "real workflow chain review passed",
    ):
        check(errors, term in text, f"real workflow chain review missing term `{term}`")
    for term in (
        "artifacts.unlink()",
        "shutil.rmtree(artifacts)",
        "artifact root exists and is not a directory",
        "no selected case/runtime pair executed",
    ):
        check(errors, term in runner_text, f"real workflow chain runner missing artifact/skip hygiene term `{term}`")
    for case_number in range(1, 29):
        case_id = f"R{case_number:02d}"
        check(errors, f"| {case_id} |" in text, f"real workflow chain review missing case {case_id}")
        check(errors, f'"{case_id}"' in runner_text, f"real workflow chain runner missing case {case_id}")


def main() -> int:
    errors: list[str] = []
    plugin_root = plugin_root_from_script()
    validate_manifests(plugin_root, errors)
    validate_startup_bootstrap_contract(plugin_root, errors)
    validate_project_hook_contract(plugin_root, errors)
    validate_agents_guide_drift_smoke(plugin_root, errors)
    validate_claude_hook_structure(plugin_root, errors)
    validate_session_start_smoke(plugin_root, errors)
    validate_stop_memory_hygiene_smoke(plugin_root, errors)
    validate_in_flight_memory_contract(plugin_root, errors)
    validate_rendered_checkpoint_contract(plugin_root, errors)
    validate_develop_checkpoint_commit_contract(plugin_root, errors)
    validate_real_workflow_chain_review_contract(plugin_root, errors)

    if errors:
        print("plugin adapter checks failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("plugin adapter checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
