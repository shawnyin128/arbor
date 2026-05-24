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


def contains_term(text: str, term: str) -> bool:
    return term in text or " ".join(term.split()) in " ".join(text.split())


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
    init_script = (plugin_root / "skills" / "arbor" / "scripts" / "init_project_memory.py").read_text(encoding="utf-8")

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
        "Runtime-specific adapter initialization is separate from canonical project state",
        "existing `AGENTS.md` and `.arbor/memory.md` are not proof that the Claude adapter was initialized",
        "`.codex/hooks.json` is not a Claude hook registration",
        ".claude/settings.json",
        ".claude/hooks/",
        "plugin-bundled hooks are not proof that Claude project hooks are active",
    ):
        check(errors, term in arbor_skill, f"arbor skill missing startup bootstrap term `{term}`")

    for term in (
        "runtime-specific bridge files",
        "idempotent across runtimes",
        "Existing canonical files therefore do not short-circuit adapter setup",
        "Hook setup is runtime-specific and separate",
        ".claude/settings.json",
        ".claude/hooks",
    ):
        check(errors, term in init_script, f"init_project_memory missing cross-runtime initialization term `{term}`")

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


def validate_cross_runtime_initialization_contract(plugin_root: Path, errors: list[str]) -> None:
    import sys

    scripts_dir = plugin_root / "skills" / "arbor" / "scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        from init_project_memory import CLAUDE_BRIDGE_OFF, CLAUDE_BRIDGE_ON, init_project_memory
        from register_project_hooks import INSTALL_RUNTIME_CLAUDE, INSTALL_RUNTIME_CODEX, register_project_hooks
    finally:
        sys.path.pop(0)

    with tempfile.TemporaryDirectory(prefix="arbor-cross-runtime-init-") as tmp:
        project = Path(tmp) / "project"
        project.mkdir()

        init_project_memory(project, claude_bridge=CLAUDE_BRIDGE_OFF)
        agents = project / "AGENTS.md"
        memory = project / ".arbor" / "memory.md"
        claude = project / "CLAUDE.md"
        resolved_claude = claude.resolve()
        check(errors, agents.is_file(), "Codex-style initialization should create AGENTS.md")
        check(errors, memory.is_file(), "Codex-style initialization should create .arbor/memory.md")
        check(errors, not claude.exists(), "Codex-style initialization should not create CLAUDE.md by default")

        register_project_hooks(project, runtime=INSTALL_RUNTIME_CODEX)
        codex_hooks = project / ".codex" / "hooks.json"
        check(errors, codex_hooks.is_file(), "Codex hook registration should create .codex/hooks.json")

        custom_agents = "# Custom Guide\n\nKeep me.\n"
        agents.write_text(custom_agents, encoding="utf-8")
        actions = init_project_memory(project, claude_bridge=CLAUDE_BRIDGE_ON)
        register_project_hooks(project, runtime=INSTALL_RUNTIME_CLAUDE)
        claude_settings = project / ".claude" / "settings.json"
        claude_session = project / ".claude" / "hooks" / "arbor-session-start"
        claude_stop = project / ".claude" / "hooks" / "arbor-stop-memory-hygiene"
        check(errors, claude.is_file(), "Claude initialization after Codex initialization should create CLAUDE.md")
        check(errors, claude_settings.is_file(), "Claude hook initialization after Codex initialization should create .claude/settings.json")
        check(errors, claude_session.is_file(), "Claude hook initialization should create .claude/hooks/arbor-session-start")
        check(errors, claude_stop.is_file(), "Claude hook initialization should create .claude/hooks/arbor-stop-memory-hygiene")
        check(errors, agents.read_text(encoding="utf-8") == custom_agents, "Claude bridge initialization must not overwrite AGENTS.md")
        check(errors, codex_hooks.is_file(), "Claude follow-up initialization must not remove Codex hook intents")
        settings = json.loads(claude_settings.read_text(encoding="utf-8"))
        settings_text = json.dumps(settings)
        for term in ("SessionStart", "Stop", ".claude/hooks/arbor-session-start", ".claude/hooks/arbor-stop-memory-hygiene"):
            check(errors, term in settings_text, f"Claude project hook settings missing `{term}`")
        check(
            errors,
            any(action.path == resolved_claude and action.status == "created" for action in actions),
            "Claude follow-up initialization should report created CLAUDE.md",
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
    check(
        errors,
        not (plugin_root / "hooks" / "hooks.json").exists(),
        "Claude hooks must be registered into project .claude/settings.json, not auto-registered from plugin hooks/hooks.json",
    )

    session_start = plugin_root / "hooks" / "session-start"
    check(errors, session_start.is_file(), "hooks/session-start must exist")
    check(errors, os.access(session_start, os.X_OK), "hooks/session-start must be executable")
    stop_adapter = plugin_root / "hooks" / "stop-memory-hygiene"
    check(errors, stop_adapter.is_file(), "hooks/stop-memory-hygiene must exist")
    check(errors, os.access(stop_adapter, os.X_OK), "hooks/stop-memory-hygiene must be executable")
    check(errors, not (plugin_root / "hooks" / "pre-compact").exists(), "PreCompact adapter must not ship in this release")
    check(errors, not (plugin_root / "agents").exists(), "plugin-level agents directory is out of scope for this release")


def validate_public_entrypoint_contract(plugin_root: Path, errors: list[str]) -> None:
    skills_root = plugin_root / "skills"
    check(errors, (skills_root / "feedback" / "SKILL.md").is_file(), "feedback skill must be present")
    check(errors, not (skills_root / "intake").exists(), "hidden intake skill must not ship")

    brainstorm = (skills_root / "brainstorm" / "SKILL.md").read_text(encoding="utf-8")
    feedback = (skills_root / "feedback" / "SKILL.md").read_text(encoding="utf-8")
    converge = (skills_root / "converge" / "SKILL.md").read_text(encoding="utf-8")
    release = (skills_root / "release" / "SKILL.md").read_text(encoding="utf-8")
    agents_template = (skills_root / "arbor" / "references" / "agents-template.md").read_text(encoding="utf-8")
    real_runner = (skills_root / "arbor" / "scripts" / "check_real_workflow_chains.py").read_text(encoding="utf-8")
    readme = (plugin_root.parent.parent / "README.md").read_text(encoding="utf-8")
    codex = load_json(plugin_root / ".codex-plugin" / "plugin.json", errors)

    for term in (
        "ready_for_converge",
        "`route.next_skill`: `brainstorm`, `converge`, `none`",
        "Do not route ordinary user prompts to public `develop`, public `evaluate`, or public `release`",
    ):
        check(errors, contains_term(brainstorm, term), f"brainstorm public-entrypoint contract missing `{term}`")
    check(errors, "ready_for_develop" not in brainstorm, "brainstorm must not expose ready_for_develop")
    check(errors, "`route.next_skill`: `brainstorm`, `develop`, `evaluate`" not in brainstorm, "brainstorm must not allow public develop/evaluate routes")

    for term in (
        "Invocation And Acceptance Contract",
        "Accept and route as feedback only",
        "does not force a non-feedback request",
        "Do not trigger from keywords alone",
        "The next owner is limited to `brainstorm`, `converge`, or direct response",
        "Do not expose `develop`, `evaluate`, or `release` as public next steps",
    ):
        check(errors, contains_term(feedback, term), f"feedback public-entrypoint contract missing `{term}`")

    for term in (
        "`converge` as the public quality-loop orchestrator",
        "Do not expose `develop` or `evaluate` as public next steps",
        "internal `develop` and `evaluate`",
    ):
        check(errors, contains_term(converge, term), f"converge public-entrypoint contract missing `{term}`")

    for term in (
        "Internal-only Arbor checkpoint/finalization gate",
        "do not select for ordinary user prompts",
        "Do not advertise or accept `release` as a public workflow entrypoint",
    ):
        check(errors, contains_term(release, term), f"release internal-entrypoint contract missing `{term}`")

    for term in (
        "Workflow Entrypoint Protocol",
        "explicit Arbor public entrypoint",
        "skill frontmatter, canonical examples, and checklist",
        "Public entrypoints are `brainstorm`, `feedback`, and `converge`",
        "`develop` and `evaluate` are internal stages owned by `converge`; `release` is internal",
    ):
        check(errors, contains_term(agents_template, term), f"agents template missing public entrypoint term `{term}`")
    for forbidden in (
        "Describe the stable project objective here",
        "Record durable engineering, workflow, validation, style, and collaboration constraints here",
        "Use this as the entrypoint to durable project context, not as the whole long-term memory store.",
        "Document major directories, modules, commands, architecture boundaries, and where to start reading.",
    ):
        check(errors, forbidden not in agents_template, f"agents template still exposes placeholder text `{forbidden}`")

    for forbidden in ("Codex:        $release", "Claude Code:  /arbor:release", "$release finalize"):
        check(errors, forbidden not in readme, f"README must not advertise public release invocation `{forbidden}`")

    interface = codex.get("interface")
    if isinstance(interface, dict):
        long_description = str(interface.get("longDescription", ""))
        for term in (
            "before routing approved work to converge",
            "needs-evidence",
            "does not trigger from keywords alone",
            "Develop, evaluate, and release are internal stages",
            "users should not be asked to invoke release directly",
        ):
            check(errors, contains_term(long_description, term), f"Codex longDescription missing public entrypoint term `{term}`")

    for forbidden in ('"$develop ', '"$evaluate ', '"$release ', "CJK_EVALUATE_PROMPT"):
        check(errors, forbidden not in real_runner, f"real workflow chain runner must not use public {forbidden}")


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


def run_stop_hook(
    plugin_root: Path,
    project_root: Path,
    stop_hook_active: bool,
    memory_hygiene_mode: str | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    if memory_hygiene_mode is not None:
        env["ARBOR_STOP_MEMORY_HYGIENE_MODE"] = memory_hygiene_mode
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


def assert_stop_allows(errors: list[str], proc: subprocess.CompletedProcess[str], label: str) -> dict[str, Any]:
    try:
        output = json.loads(proc.stdout)
    except json.JSONDecodeError:
        add_error(errors, f"{label}: Stop adapter must emit non-blocking JSON")
        return {}
    check(errors, output.get("continue") is True, f"{label}: Stop adapter must explicitly allow stop")
    check(errors, output.get("decision") != "block", f"{label}: Stop adapter must not block")
    check(errors, output.get("suppressOutput") is True, f"{label}: Stop adapter should request suppressed hook output")
    return output


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

        # Clean worktree: the adapter must emit non-blocking JSON and allow the stop.
        clean_proc = run_stop_hook(plugin_root, project, stop_hook_active=False)
        check(errors, clean_proc.returncode == 0, f"Stop clean smoke failed: {clean_proc.stderr.strip()}")
        assert_stop_allows(errors, clean_proc, "Stop clean smoke")

        # Dirty worktree: the adapter must allow stop by default so Stop hook
        # continuations cannot replace the assistant's real final response. It
        # should still write a bounded fallback if memory has no In-flight entry.
        (project / "feature.txt").write_text("work in progress\n", encoding="utf-8")
        dirty_proc = run_stop_hook(plugin_root, project, stop_hook_active=False)
        check(errors, dirty_proc.returncode == 0, f"Stop dirty smoke failed: {dirty_proc.stderr.strip()}")
        assert_stop_allows(errors, dirty_proc, "Stop dirty smoke")
        memory_after_dirty = (project / ".arbor" / "memory.md").read_text(encoding="utf-8")
        check(
            errors,
            "stop hook fallback: dirty Arbor worktree detected before stop" in memory_after_dirty,
            "Stop adapter must quietly add a fallback In-flight memory entry when one is missing",
        )

        # Opt-in blocking mode keeps the old memory-hygiene packet path
        # available for Claude installs that explicitly choose it.
        block_proc = run_stop_hook(plugin_root, project, stop_hook_active=False, memory_hygiene_mode="block")
        check(errors, block_proc.returncode == 0, f"Stop block-mode smoke failed: {block_proc.stderr.strip()}")
        try:
            decision = json.loads(block_proc.stdout)
        except json.JSONDecodeError:
            add_error(errors, "Stop adapter must emit JSON when opt-in blocking mode is enabled")
            decision = {}
        check(errors, decision.get("decision") == "block", "Stop adapter must block in opt-in mode when the worktree is dirty")
        check(
            errors,
            "# Memory Hygiene Context" in str(decision.get("reason", "")),
            "Stop opt-in block reason must carry the memory hygiene packet",
        )

        # stop_hook_active guard: the adapter must never block a continuation.
        active_proc = run_stop_hook(plugin_root, project, stop_hook_active=True)
        check(errors, active_proc.returncode == 0, f"Stop active smoke failed: {active_proc.stderr.strip()}")
        assert_stop_allows(errors, active_proc, "Stop active smoke")

        explicit_memory = "# Session Memory\n\n## In-flight\n\n- existing workflow handoff remains authoritative.\n"
        (project / ".arbor" / "memory.md").write_text(explicit_memory, encoding="utf-8")
        explicit_proc = run_stop_hook(plugin_root, project, stop_hook_active=False)
        check(errors, explicit_proc.returncode == 0, f"Stop explicit-memory smoke failed: {explicit_proc.stderr.strip()}")
        assert_stop_allows(errors, explicit_proc, "Stop explicit-memory smoke")
        check(
            errors,
            (project / ".arbor" / "memory.md").read_text(encoding="utf-8") == explicit_memory,
            "Stop adapter must not overwrite an existing meaningful In-flight memory entry",
        )

    # Non-Arbor project: the adapter must allow stop even when dirty.
    with tempfile.TemporaryDirectory(prefix="arbor-claude-stop-nonarbor-") as tmp:
        project = Path(tmp)
        _git(["init"], project)
        (project / "feature.txt").write_text("unrelated work\n", encoding="utf-8")
        proc = run_stop_hook(plugin_root, project, stop_hook_active=False)
        check(errors, proc.returncode == 0, f"Stop non-Arbor smoke failed: {proc.stderr.strip()}")
        assert_stop_allows(errors, proc, "Stop non-Arbor smoke")


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
        "skills/feedback/SKILL.md": [
            "**Update in-flight memory when needed**",
            "if uncommitted Arbor workflow changes remain because this feedback decision created local evidence or state",
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
            check(errors, contains_term(text, term), f"{rel_path} missing in-flight memory contract term `{term}`")


def validate_rendered_checkpoint_contract(plugin_root: Path, errors: list[str]) -> None:
    protocol = plugin_root / "skills" / "arbor" / "references" / "rendered-checkpoint-protocol.md"
    check(errors, protocol.is_file(), "rendered checkpoint protocol reference must exist")
    if protocol.is_file():
        protocol_text = protocol.read_text(encoding="utf-8")
        for term in (
            "applies only to Arbor workflow checkpoints and decision points",
            "apply to direct answers",
            "raw workflow JSON",
            "route assignments",
            "terminal-state labels",
            "unexplained feature ids",
            "final rendered response text",
            "preflight only",
            "Final Response Preflight",
            "Visible Response Language",
            "user's active chat language",
            "localized heading equivalents",
            "exact text it is about to send",
            "Static fixture checks are not a substitute",
        ):
            check(errors, contains_term(protocol_text, term), f"rendered checkpoint protocol missing term `{term}`")

    required = {
        "skills/arbor/SKILL.md": [
            "Rendered Checkpoint Guard",
            "references/rendered-checkpoint-protocol.md",
            "final rendered response",
            "Static fixture checks are preflight",
        ],
        "skills/brainstorm/SKILL.md": [
            "do not stop with only chat prose",
            "create a durable brainstorm checkpoint",
            "Missing details become an explicit pending question",
            "Use the following section headings exactly",
            "Understanding And Recommendation",
            "Suggested Small Steps",
            "How I Would Validate Each Step",
            "Expected Delivery",
            "localized heading equivalents",
            "user's active chat language",
            "Final response preflight",
            "captured final text",
            "status-paragraph",
            "artifact-list",
        ],
        "skills/feedback/SKILL.md": [
            "The normal visible final response MUST include these exact Markdown headings",
            "`**Feedback Decision**`",
            "`**Why This Route**`",
            "`**What I Need Or Will Use**`",
            "`**Next Step**`",
            "localized heading equivalents",
            "user's active chat language",
            "Final response preflight",
            "captured final text",
            "prose-only summary",
        ],
        "skills/feedback/references/feedback-boundary.md": [
            "Do not print the raw `feedback.v1` packet",
            "route fields",
            "terminal-state labels",
            "localized heading equivalents",
            "Final response preflight",
            "prose-only summary",
        ],
        "skills/develop/SKILL.md": [
            "The normal visible final response MUST include these exact Markdown headings",
            "`**What I Completed**`",
            "`**How I Self-Tested**`",
            "localized heading equivalents",
            "user's active chat language",
            "Final response preflight",
            "captured final text",
            "prose-only summary",
        ],
        "skills/evaluate/SKILL.md": [
            "The normal visible final response MUST include these exact Markdown headings",
            "`**Findings First**`",
            "`**Scenario Tests**`",
            "localized heading equivalents",
            "user's active chat language",
            "A shorter prose-only",
            "evaluation is not an acceptable `evaluate` checkpoint",
            "Final response preflight",
            "exact final assistant",
            "workflow, process-control, routing, plugin, prompt-routing, or output-layer changes",
            "checker or harness negative probe",
            "weak pass",
        ],
        "skills/converge/SKILL.md": [
            "The normal visible final response MUST include these exact Markdown headings",
            "`**Convergence Decision**`",
            "`**Why This Decision**`",
            "`**Agreement Check**`",
            "`**Goal Alignment**`",
            "`**Remaining Issues**`",
            "`**Next Step**`",
            "localized heading equivalents",
            "user's active chat language",
            "Final response preflight",
            "exact final assistant",
            "shorter prose-only convergence checkpoint is not acceptable",
        ],
        "skills/converge/references/converge-boundary.md": [
            "The normal visible final response MUST include these exact Markdown headings",
            "`**Convergence Decision**`",
            "`**Goal Alignment**`",
            "Markdown tables under `Agreement Check` and `Remaining Issues`",
            "localized heading equivalents",
            "user's active chat language",
            "Final response preflight",
            "A shorter prose-only convergence checkpoint is not acceptable",
        ],
        "skills/release/SKILL.md": [
            "User-Visible Status",
            "user's active chat language",
            "Final response preflight",
            "captured final text",
            "generic",
        ],
    }
    repo_root = repo_root_from_plugin(plugin_root)
    if repo_root is not None:
        required["README.md"] = [
            "rendered workflow checkpoints",
            "references/rendered-checkpoint-protocol.md",
            "user's active chat language",
            "localized heading equivalents",
            "real runtime replay",
            "static fixture checks and JSON schema checks",
        ]
    for rel_path, terms in required.items():
        base = repo_root if rel_path == "README.md" and repo_root is not None else plugin_root
        text = (base / rel_path).read_text(encoding="utf-8")
        for term in terms:
            check(errors, contains_term(text, term), f"{rel_path} missing rendered checkpoint contract term `{term}`")


def validate_guidance_placement_contract(plugin_root: Path, errors: list[str]) -> None:
    reference = plugin_root / "skills" / "arbor" / "references" / "guidance-placement-guard.md"
    check(errors, reference.is_file(), "guidance placement guard reference must exist")
    if reference.is_file():
        text = reference.read_text(encoding="utf-8")
        for term in (
            "Arbor improves the agent's working conditions",
            "`AGENTS.md`",
            "`CLAUDE.md`",
            "`.arbor/memory.md`",
            "Arbor skills and skill references",
            "`docs/review/`",
            "Git history",
            "MCP tools, CLI tools, URLs, or task-specific docs",
            "impose fixed reading limits",
            "require plan-first behavior",
            "require subagents, worktrees, fan-out execution, or automations",
            "turn hooks into workflow decision makers",
        ):
            check(errors, term in text, f"guidance placement guard missing term `{term}`")

    required = {
        "skills/arbor/SKILL.md": [
            "Guidance Placement Guard",
            "references/guidance-placement-guard.md",
            "removing it would likely cause repeated mistakes",
            "Do not impose fixed reading limits",
            "mandatory plan-first behavior",
            "mandatory subagents",
        ],
        "skills/arbor/references/agents-template.md": [
            "Keep this file concise",
            "task-specific workflows",
            "referenced project docs",
            "Link to volatile external context",
        ],
        "skills/arbor/references/claude-template.md": [
            "short bridge",
            "Task-specific workflows",
            "not in this bridge",
        ],
        "skills/arbor/references/process-state-authority.md": [
            "Guidance placement follows the same ownership model",
            "checkpoint Release Round commit evidence",
            "--require-checkpoint-commit-evidence",
            "concise startup map",
            "volatile external context",
            "fixed reading limits",
            "implementation strategy",
        ],
    }
    repo_root = repo_root_from_plugin(plugin_root)
    if repo_root is not None:
        required["README.md"] = [
            "task-specific workflows",
            "frequently changing external context",
            "The placement rule is deliberately narrow",
            "guidance-placement-guard.md",
            "not how the agent must reason or implement",
        ]

    for rel_path, terms in required.items():
        base = repo_root if rel_path == "README.md" and repo_root is not None else plugin_root
        text = (base / rel_path).read_text(encoding="utf-8")
        for term in terms:
            check(errors, contains_term(text, term), f"{rel_path} missing guidance placement term `{term}`")


def validate_done_when_verification_thread_contract(plugin_root: Path, errors: list[str]) -> None:
    reference = plugin_root / "skills" / "arbor" / "references" / "done-when-verification-thread.md"
    check(errors, reference.is_file(), "done-when verification thread reference must exist")
    if reference.is_file():
        text = reference.read_text(encoding="utf-8")
        for term in (
            "done-when criteria",
            "artifact-appropriate verification",
            "label weak pass evidence",
            "Check that required verification evidence exists before finalization or publish",
            "Do not force one test type",
            "route small direct tasks into Arbor",
        ):
            check(errors, term in text, f"done-when verification thread missing term `{term}`")

    required = {
        "skills/arbor/SKILL.md": [
            "Done-When Verification Thread",
            "references/done-when-verification-thread.md",
            "task-appropriate done-when criteria",
            "mapping self-tests to those criteria",
            "evidence existence rather than correctness re-evaluation",
            "must not force one test type",
        ],
        "skills/brainstorm/SKILL.md": [
            "Done-When Verification Thread",
            "done-when criteria",
            "artifact-appropriate verification",
            "do not force one test type",
            "Keep small direct tasks outside the managed verification thread",
        ],
        "skills/develop/SKILL.md": [
            "Done-When Verification Thread",
            "map self-tests to done-when criteria",
            "verification gap",
            "do not force one test type",
            "no uncovered done-when criteria",
        ],
        "skills/evaluate/SKILL.md": [
            "done-when criteria",
            "independently challenge the done-when criteria",
            "visible mapping from evaluator evidence",
            "weak pass",
            "exact runtime proof",
        ],
        "skills/converge/SKILL.md": [
            "Done-When Verification Thread",
            "done-when criteria remain satisfied",
            "weak pass",
            "return the appropriate evidence or planning route",
        ],
        "skills/release/SKILL.md": [
            "done-when criteria when present",
            "verification evidence exists before finalization or publish",
            "without re-evaluating correctness",
            "verification_evidence",
        ],
    }
    repo_root = repo_root_from_plugin(plugin_root)
    if repo_root is not None:
        required["README.md"] = [
            "done-when verification thread",
            "done-when criteria",
            "labels weak pass substitutes",
            "checks that verification evidence exists before finalization or publish",
            "does not force one test type",
            "small direct tasks",
        ]

    for rel_path, terms in required.items():
        base = repo_root if rel_path == "README.md" and repo_root is not None else plugin_root
        text = (base / rel_path).read_text(encoding="utf-8")
        for term in terms:
            check(errors, term in text, f"{rel_path} missing done-when verification term `{term}`")


def validate_loop_health_advisory_contract(plugin_root: Path, errors: list[str]) -> None:
    reference = plugin_root / "skills" / "arbor" / "references" / "loop-health-advisory.md"
    check(errors, reference.is_file(), "loop-health advisory reference must exist")
    if reference.is_file():
        text = reference.read_text(encoding="utf-8")
        for term in (
            "repeated same-class failures",
            "evidence conflicts",
            "weak replay evidence",
            "context contamination",
            "fresh-session handoff",
            "must not automatically clear context",
            "Subagents and worktrees remain optional strategies",
            "normal correction loops should continue",
        ):
            check(errors, term in text, f"loop-health advisory reference missing term `{term}`")

    required = {
        "skills/arbor/SKILL.md": [
            "Loop Health Advisory",
            "references/loop-health-advisory.md",
            "repeated same-class failures",
            "weak replay evidence",
            "context contamination",
            "fresh-session handoff",
            "must not automatically clear context",
            "normal correction loops should continue",
        ],
        "skills/evaluate/SKILL.md": [
            "Loop Health Advisory",
            "evidence conflicts",
            "weak replay evidence",
            "context contamination",
            "does not grant permission to patch implementation files",
            "recommend a fresh-session handoff",
            "Subagents and worktrees remain optional strategies",
            "normal correction loop",
        ],
        "skills/evaluate/references/evaluate-boundary.md": [
            "Loop Health Advisory",
            "evidence conflicts",
            "weak replay evidence",
            "context contamination",
            "must not patch implementation files directly",
            "fresh-session handoff",
            "Subagents and worktrees remain optional strategies",
            "normal correction loop",
        ],
        "skills/converge/SKILL.md": [
            "Loop Health Advisory",
            "repeated same-class failures",
            "evidence conflicts",
            "weak replay evidence",
            "context contamination",
            "fresh-session handoff",
            "Do not escalate a normal correction loop",
            "Do not automatically clear context",
            "Subagents and worktrees remain optional strategies",
        ],
        "skills/converge/references/converge-boundary.md": [
            "Loop Health Advisory",
            "repeated same-class failures",
            "evidence conflicts",
            "weak replay evidence",
            "context contamination",
            "fresh-session handoff",
            "must not automatically clear context",
            "normal correction loop should continue",
        ],
    }
    repo_root = repo_root_from_plugin(plugin_root)
    if repo_root is not None:
        required["README.md"] = [
            "loop-health advisory",
            "repeated same-class failures",
            "evidence conflicts",
            "weak replay evidence",
            "context contamination",
            "fresh-session handoff",
            "does not automatically clear context",
            "Subagents and worktrees remain optional strategies",
            "normal correction loop",
        ]

    for rel_path, terms in required.items():
        base = repo_root if rel_path == "README.md" and repo_root is not None else plugin_root
        text = (base / rel_path).read_text(encoding="utf-8")
        for term in terms:
            check(errors, term in text, f"{rel_path} missing loop-health advisory term `{term}`")


def validate_decision_trace_handoff_contract(plugin_root: Path, errors: list[str]) -> None:
    reference = plugin_root / "skills" / "arbor" / "references" / "decision-trace-handoff.md"
    check(errors, reference.is_file(), "decision trace handoff reference must exist")
    if reference.is_file():
        text = reference.read_text(encoding="utf-8")
        for term in (
            "key decisions",
            "rejected options",
            "allowed implementation discretion",
            "decision invariants",
            "implementation-time decisions",
            "decision deviations",
            "decision drift",
            "hidden decision conflict",
            "must not require subagents or worktrees",
            "not a default multi-agent orchestration",
        ):
            check(errors, term in text, f"decision trace handoff reference missing term `{term}`")

    required = {
        "skills/arbor/SKILL.md": [
            "Decision Trace Handoff",
            "references/decision-trace-handoff.md",
            "key decisions",
            "decision invariants",
            "not a default multi-agent orchestration",
        ],
        "skills/brainstorm/SKILL.md": [
            "Decision Trace Handoff",
            "key decisions",
            "rejected options",
            "allowed implementation discretion",
            "decision invariants",
        ],
        "skills/brainstorm/references/brainstorm-boundary.md": [
            "decision trace handoff",
            "key decisions",
            "rejected options",
            "allowed implementation discretion",
            "decision invariants",
        ],
        "skills/develop/SKILL.md": [
            "Decision Trace Handoff",
            "implementation-time decisions",
            "decision deviations",
            "decision invariants",
            "needs_brainstorm",
        ],
        "skills/develop/references/develop-boundary.md": [
            "Decision Trace Handoff",
            "implementation-time decisions",
            "decision deviations",
            "decision invariants",
            "needs_brainstorm",
        ],
        "skills/evaluate/SKILL.md": [
            "decision drift",
            "hidden decision conflict",
            "implementation-time decisions",
            "does not fix implementation directly",
        ],
        "skills/evaluate/references/evaluate-boundary.md": [
            "decision drift",
            "hidden decision conflict",
            "implementation-time decisions",
            "does not fix implementation directly",
        ],
        "skills/converge/SKILL.md": [
            "decision trace consistency",
            "decision drift",
            "decision invariants",
            "return the appropriate evidence or planning route",
        ],
        "skills/converge/references/converge-boundary.md": [
            "decision trace consistency",
            "decision drift",
            "decision invariants",
            "return the appropriate evidence or planning route",
        ],
    }
    repo_root = repo_root_from_plugin(plugin_root)
    if repo_root is not None:
        required["README.md"] = [
            "decision trace handoff",
            "key decisions",
            "implementation-time decisions",
            "decision drift",
            "does not require subagents or worktrees",
        ]

    for rel_path, terms in required.items():
        base = repo_root if rel_path == "README.md" and repo_root is not None else plugin_root
        text = (base / rel_path).read_text(encoding="utf-8")
        for term in terms:
            check(errors, term in text, f"{rel_path} missing decision trace handoff term `{term}`")


def validate_delegation_packet_effort_budget_contract(plugin_root: Path, errors: list[str]) -> None:
    reference = plugin_root / "skills" / "arbor" / "references" / "delegation-packet-effort-budget.md"
    check(errors, reference.is_file(), "delegation packet and effort budget reference must exist")
    if reference.is_file():
        text = reference.read_text(encoding="utf-8")
        for term in (
            "objective",
            "output format",
            "tools/sources",
            "boundaries",
            "effort budget",
            "context pointers",
            "stop conditions",
            "when not to delegate",
            "Direct answers, simple edits, tightly coupled coding, and tightly coupled workflow changes remain single-threaded by default",
            "must not require subagents or worktrees",
            "must not require fan-out execution",
        ):
            check(errors, term in text, f"delegation packet reference missing term `{term}`")

    required = {
        "skills/arbor/SKILL.md": [
            "Delegation Packet And Effort Budget",
            "references/delegation-packet-effort-budget.md",
            "objective",
            "output format",
            "tools/sources",
            "boundaries",
            "effort budget",
            "stop conditions",
            "Direct answers, simple edits, tightly coupled coding, and tightly coupled workflow changes remain single-threaded by default",
            "must not require subagents or worktrees",
        ],
        "skills/brainstorm/SKILL.md": [
            "Delegation Packet And Effort Budget",
            "objective",
            "output format",
            "tools/sources",
            "boundaries",
            "effort budget",
            "when not to delegate",
            "must not require subagents or worktrees",
        ],
        "skills/brainstorm/references/brainstorm-boundary.md": [
            "Delegation Packet And Effort Budget",
            "objective",
            "output format",
            "tools/sources",
            "boundaries",
            "effort budget",
            "when not to delegate",
            "must not require subagents or worktrees",
        ],
        "skills/develop/SKILL.md": [
            "Delegation Packet And Effort Budget",
            "objective",
            "output format",
            "tools/sources",
            "boundaries",
            "effort budget",
            "single-threaded by default",
            "must not require subagents or worktrees",
        ],
        "skills/develop/references/develop-boundary.md": [
            "Delegation Packet And Effort Budget",
            "objective",
            "output format",
            "tools/sources",
            "boundaries",
            "effort budget",
            "single-threaded by default",
            "must not require subagents or worktrees",
        ],
        "skills/evaluate/SKILL.md": [
            "optional delegation packet",
            "objective",
            "output format",
            "tools/sources",
            "boundaries",
            "effort budget",
            "Do not require delegation for acceptance",
            "tightly coupled workflow changes remain single-threaded by default",
        ],
        "skills/evaluate/references/evaluate-boundary.md": [
            "optional delegation packet",
            "objective",
            "output format",
            "tools/sources",
            "boundaries",
            "effort budget",
            "Do not require delegation",
            "tightly coupled workflow changes",
        ],
        "skills/converge/SKILL.md": [
            "Do not require delegation to mark work done",
            "optional delegation packet",
            "objective",
            "output format",
            "boundaries",
            "effort budget",
        ],
        "skills/converge/references/converge-boundary.md": [
            "optional delegation packet and effort budget",
            "when delegation was used",
        ],
    }
    repo_root = repo_root_from_plugin(plugin_root)
    if repo_root is not None:
        required["README.md"] = [
            "delegation packet and effort budget",
            "objective",
            "output format",
            "tools/sources",
            "boundaries",
            "effort budget",
            "context pointers",
            "stop conditions",
            "does not require subagents or worktrees",
            "single-threaded by default",
        ]

    for rel_path, terms in required.items():
        base = repo_root if rel_path == "README.md" and repo_root is not None else plugin_root
        text = (base / rel_path).read_text(encoding="utf-8")
        for term in terms:
            check(errors, term in text, f"{rel_path} missing delegation packet term `{term}`")


def validate_outcome_eval_observability_contract(plugin_root: Path, errors: list[str]) -> None:
    reference = plugin_root / "skills" / "arbor" / "references" / "outcome-eval-observability.md"
    check(errors, reference.is_file(), "outcome eval observability reference must exist")
    if reference.is_file():
        text = reference.read_text(encoding="utf-8")
        for term in (
            "final state",
            "checkpoint outcomes",
            "rendered output",
            "review evidence",
            "process-state checks",
            "git commits, file side effects",
            "real runtime replay",
            "trace evidence",
            "weak pass",
            "must not require LLM judges",
            "fixed path matching",
            "exact turn-by-turn path",
            "one universal test type",
        ):
            check(errors, term in text, f"outcome eval observability reference missing term `{term}`")

    required = {
        "skills/arbor/SKILL.md": [
            "Outcome Evaluation And Observability",
            "references/outcome-eval-observability.md",
            "final state",
            "checkpoint outcomes",
            "rendered output",
            "trace evidence",
            "must not require LLM judges",
            "fixed path matching",
            "exact turn-by-turn replay",
            "weak pass",
        ],
        "skills/evaluate/SKILL.md": [
            "Outcome Evaluation And Observability",
            "outcome-first",
            "final state",
            "checkpoint outcomes",
            "rendered output",
            "review evidence",
            "process state",
            "git/file side effects",
            "realistic replay",
            "trace evidence",
            "Do not require LLM judges",
            "fixed path matching",
            "exact turn-by-turn replay",
            "weak pass",
        ],
        "skills/develop/SKILL.md": [
            "observable outcomes",
            "final state",
            "checkpoint outcomes",
            "rendered output",
            "review evidence",
            "process state",
            "git/file side effects",
            "realistic replay",
            "trace evidence",
            "weak-pass gap",
            "Do not require LLM judges",
            "fixed path matching",
            "exact turn-by-turn replay",
        ],
        "skills/develop/references/develop-boundary.md": [
            "observable outcome coverage",
            "final state",
            "checkpoint outcomes",
            "rendered output",
            "review evidence",
            "process state",
            "git/file side effects",
            "realistic replay",
            "trace evidence",
            "deferred weak-pass gaps",
        ],
        "skills/evaluate/references/evaluate-boundary.md": [
            "Outcome Evaluation And Observability",
            "outcome-first",
            "final state",
            "checkpoint outcomes",
            "rendered output",
            "review evidence",
            "process-state checks",
            "git commits, file side effects",
            "realistic replay",
            "trace evidence",
            "Do not require fixed path matching",
            "LLM judges",
            "weak pass",
        ],
        "skills/converge/SKILL.md": [
            "Outcome Evaluation And Observability",
            "outcome evidence",
            "final state",
            "checkpoint outcomes",
            "rendered output",
            "review evidence",
            "process state",
            "git/file side effects",
            "realistic replay",
            "trace evidence",
            "fixed path matching",
            "weak-pass gaps",
        ],
        "skills/converge/references/converge-boundary.md": [
            "Outcome Evidence",
            "outcome-first",
            "final state",
            "checkpoint outcomes",
            "rendered output",
            "review evidence",
            "process state",
            "git/file side effects",
            "realistic replay",
            "trace evidence",
            "fixed path matching",
            "weak pass",
        ],
        "skills/release/SKILL.md": [
            "outcome and observability evidence",
            "rendered output",
            "review evidence",
            "process state",
            "git/file side effects",
            "realistic replay",
            "weak-pass gap",
            "trace evidence",
            "Do not require LLM judges",
            "fixed path matching",
            "exact turn-by-turn replay",
        ],
        "skills/release/references/release-boundary.md": [
            "Outcome And Observability Evidence",
            "outcome and observability evidence",
            "rendered output",
            "review evidence",
            "process state",
            "git/file side effects",
            "realistic replay",
            "weak-pass gap",
            "trace evidence",
            "fixed path matching",
            "LLM judges",
        ],
        "skills/arbor/references/real-workflow-chain-review.md": [
            "Outcome evaluation",
            "final state",
            "checkpoint outcomes",
            "rendered output",
            "review evidence",
            "process state",
            "git/file side effects",
            "realistic replay",
            "trace evidence",
            "weak-pass gaps",
            "fixed path matching",
            "LLM judges",
        ],
    }
    repo_root = repo_root_from_plugin(plugin_root)
    if repo_root is not None:
        required["README.md"] = [
            "outcome-first",
            "final state",
            "checkpoint outcomes",
            "rendered output",
            "review evidence",
            "process state",
            "git/file side effects",
            "realistic replay",
            "trace evidence",
            "weak-pass gaps",
            "outcome-eval-observability.md",
            "does not require LLM judges",
            "fixed path matching",
        ]

    for rel_path, terms in required.items():
        base = repo_root if rel_path == "README.md" and repo_root is not None else plugin_root
        text = (base / rel_path).read_text(encoding="utf-8")
        for term in terms:
            check(errors, term in text, f"{rel_path} missing outcome eval observability term `{term}`")


def validate_develop_checkpoint_commit_contract(plugin_root: Path, errors: list[str]) -> None:
    repo_root = repo_root_from_plugin(plugin_root)
    required = {
        "skills/develop/SKILL.md": [
            "automatic local developer checkpoint commit before internal `evaluate`",
            "`release(checkpoint_develop)` creates the local checkpoint commit",
            "policy authorization for a local checkpoint commit",
        ],
        "skills/develop/references/develop-boundary.md": [
            "automatic local developer checkpoint commit before internal `evaluate`",
            "policy authorization for a local developer checkpoint commit",
        ],
        "skills/release/SKILL.md": [
            "policy-authorized checkpoint commits",
            "For `checkpoint_develop`, that means creating a local checkpoint commit",
            "`checkpoint_evaluate`",
            "Local checkpoint commits after successful develop are internal workflow actions",
            "finalization commits and public actions require explicit user authorization",
            "allowing policy-authorized checkpoint commits",
        ],
        "skills/release/references/release-boundary.md": [
            "create a local checkpoint commit after `develop.ready_for_evaluate`",
            "local git commits are internal workflow actions authorized by active workflow checkpoint policy",
            "block rather than silently continue",
            "`checkpoint_develop` or `checkpoint_evaluate` lacks local commit authorization",
        ],
    }
    if repo_root is not None:
        required["README.md"] = [
            "release(checkpoint_develop: local commit)",
            "automatic local checkpoint commit before internal `evaluate`",
            "gating finalization commit, push, PR, tag, and publish behind explicit user authorization",
        ]

    for rel_path, terms in required.items():
        base = repo_root if rel_path == "README.md" and repo_root is not None else plugin_root
        text = (base / rel_path).read_text(encoding="utf-8")
        for term in terms:
            check(errors, contains_term(text, term), f"{rel_path} missing develop checkpoint commit term `{term}`")


def validate_release_version_management_contract(plugin_root: Path, errors: list[str]) -> None:
    repo_root = repo_root_from_plugin(plugin_root)
    required = {
        "skills/release/SKILL.md": [
            "version_management",
            "actual version management method",
            "bump_required",
            "target_version",
            "plugin_manifest_semver",
            "package_json",
            "pyproject_pep440",
            "git_tag",
        ],
        "skills/release/references/release-boundary.md": [
            "## Version Management",
            "actual version management method",
            "target_version",
            "bump_required",
            "Cache verification must compare the cache path derived from the manifest version",
        ],
        "skills/arbor/scripts/check_real_workflow_chains.py": [
            "plugin_version_from_manifest",
            "PLUGIN_VERSION",
            'Path.home() / ".codex/plugins/cache/arbor/arbor" / PLUGIN_VERSION',
            'Path.home() / ".claude/plugins/cache/arbor/arbor" / PLUGIN_VERSION',
        ],
    }
    if repo_root is not None:
        required["README.md"] = [
            "actual version management method",
            "target version",
            "versioned artifact changed",
            "cache sync",
        ]

    for rel_path, terms in required.items():
        base = repo_root if rel_path == "README.md" and repo_root is not None else plugin_root
        text = (base / rel_path).read_text(encoding="utf-8")
        for term in terms:
            check(errors, term in text, f"{rel_path} missing release version management term `{term}`")


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
        "stable pass",
        "weak pass",
        "wrong route",
        "flaky/ambiguous",
        "blocked runtime",
    ):
        check(errors, term in text, f"real workflow chain review missing term `{term}`")
    for term in (
        "artifacts.unlink()",
        "shutil.rmtree(artifacts)",
        "artifact root exists and is not a directory",
        "no selected case/runtime pair executed",
        "ROUTING_REPLAY_CASES",
        "REQUIRED_ROUTING_CATEGORIES",
        "classification_counts",
        "CLASS_STABLE_PASS",
        "CLASS_WEAK_PASS",
        "CLASS_WRONG_ROUTE",
        "CLASS_FLAKY_AMBIGUOUS",
        "CLASS_BLOCKED_RUNTIME",
        "SKILL_RENDER_CONTRACTS",
        'assert_skill_rendered_checkpoint("converge")',
        "assert_response_language_cjk",
        "assert_git_commits_created",
        "initial-git-commit-count",
        "R29",
        "R30",
        "R31",
    ):
        check(errors, term in runner_text, f"real workflow chain runner missing artifact/skip hygiene term `{term}`")
    for category in (
        "planning_continuation",
        "runtime_traceback",
        "quality_loop_converge",
        "direct_answer_control",
        "memory_hygiene",
        "project_map_drift",
        "release_publish",
        "feedback_triage",
    ):
        check(errors, category in runner_text, f"real workflow chain runner missing routing category `{category}`")
    for case_number in range(1, 29):
        case_id = f"R{case_number:02d}"
        check(errors, f"| {case_id} |" in text, f"real workflow chain review missing case {case_id}")
        check(errors, f'"{case_id}"' in runner_text, f"real workflow chain runner missing case {case_id}")
    check(errors, "| R32 |" in text, "real workflow chain review missing feedback triage case R32")
    check(errors, '"R32"' in runner_text, "real workflow chain runner missing feedback triage case R32")


def main() -> int:
    errors: list[str] = []
    plugin_root = plugin_root_from_script()
    validate_manifests(plugin_root, errors)
    validate_startup_bootstrap_contract(plugin_root, errors)
    validate_project_hook_contract(plugin_root, errors)
    validate_agents_guide_drift_smoke(plugin_root, errors)
    validate_claude_hook_structure(plugin_root, errors)
    validate_public_entrypoint_contract(plugin_root, errors)
    validate_session_start_smoke(plugin_root, errors)
    validate_stop_memory_hygiene_smoke(plugin_root, errors)
    validate_in_flight_memory_contract(plugin_root, errors)
    validate_rendered_checkpoint_contract(plugin_root, errors)
    validate_guidance_placement_contract(plugin_root, errors)
    validate_done_when_verification_thread_contract(plugin_root, errors)
    validate_loop_health_advisory_contract(plugin_root, errors)
    validate_decision_trace_handoff_contract(plugin_root, errors)
    validate_delegation_packet_effort_budget_contract(plugin_root, errors)
    validate_outcome_eval_observability_contract(plugin_root, errors)
    validate_develop_checkpoint_commit_contract(plugin_root, errors)
    validate_release_version_management_contract(plugin_root, errors)
    validate_cross_runtime_initialization_contract(plugin_root, errors)
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
