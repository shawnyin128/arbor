#!/usr/bin/env python3
"""Validate Arbor's context-core plugin adapters."""

from __future__ import annotations

import json
import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import importlib.machinery
import importlib.util
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True


PLUGIN_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = PLUGIN_ROOT.parents[1]
SKILLS_ROOT = PLUGIN_ROOT / "skills"
SCRIPTS_ROOT = SKILLS_ROOT / "arbor" / "scripts"
REFERENCES_ROOT = SKILLS_ROOT / "arbor" / "references"
PLUGIN_LEVEL_HOOK_MANIFEST = PLUGIN_ROOT / "hooks" / "hooks.json"
HANGING_WRAPPER_ASSERTION_TIMEOUT_SECONDS = 3.0

FORBIDDEN_SKILL_NAMES = {
    "brainstorm",
    "feedback",
    "converge",
    "develop",
    "evaluate",
    "release",
}

REQUIRED_REFERENCE_FILES = {
    "agents-template.md",
    "claude-template.md",
    "memory-template.md",
    "project-hooks-template.md",
    "runtime-smoke-template.md",
}

REQUIRED_SCRIPT_FILES = {
    "arbor_project_state.py",
    "check_agents_guide_quality.py",
    "check_cache_sync_adapters.py",
    "check_codex_hookless_trigger_scenarios.py",
    "check_context_boundary.py",
    "check_hookless_repair_smoke.py",
    "check_hookless_trigger_contract.py",
    "check_install_state.py",
    "check_plugin_adapters.py",
    "check_project_wrapper_smoke.py",
    "check_project_wrapper_smoke_adapters.py",
    "check_python_syntax.py",
    "check_quality_gate.py",
    "check_release_readiness.py",
    "check_runtime_smoke_evidence_adapters.py",
    "check_runtime_smoke_evidence.py",
    "check_source_hygiene.py",
    "check_skill_packages.py",
    "collect_project_context.py",
    "diagnose_project_hooks.py",
    "init_project_memory.py",
    "register_project_hooks.py",
    "run_agents_guide_drift_hook.py",
    "run_framework_check.py",
    "run_hookless_finalization.py",
    "run_memory_hygiene_hook.py",
    "run_session_startup_hook.py",
    "sync_local_plugin_cache.py",
}

FORBIDDEN_TEXT = (
    "$brainstorm",
    "$feedback",
    "$converge",
    "/arbor:brainstorm",
    "/arbor:feedback",
    "/arbor:converge",
    ".arbor/workflow/features.json",
    "managed quality loop",
    "workflow JSON",
)


def add_error(errors: list[str], message: str) -> None:
    errors.append(message)


def check(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        add_error(errors, message)


def bytecode_suppressed_env(env: dict[str, str] | None = None) -> dict[str, str]:
    command_env = os.environ.copy()
    command_env["PYTHONDONTWRITEBYTECODE"] = "1"
    if env:
        command_env.update(env)
        command_env["PYTHONDONTWRITEBYTECODE"] = "1"
    return command_env


def load_text(path: Path, errors: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        add_error(errors, f"missing file: {path.relative_to(REPO_ROOT)}")
    except OSError as exc:
        add_error(errors, f"could not read {path.relative_to(REPO_ROOT)}: {exc}")
    return ""


def load_json(path: Path, errors: list[str]) -> dict[str, Any]:
    text = load_text(path, errors)
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        add_error(errors, f"invalid JSON in {path.relative_to(REPO_ROOT)}: {exc}")
        return {}
    if not isinstance(data, dict):
        add_error(errors, f"JSON file must contain an object: {path.relative_to(REPO_ROOT)}")
        return {}
    return data


def run_command(
    args: list[str],
    errors: list[str],
    *,
    input_text: str | None = None,
    env: dict[str, str] | None = None,
    timeout_seconds: float | None = None,
) -> str:
    try:
        proc = subprocess.run(
            args,
            input=input_text,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=bytecode_suppressed_env(env),
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        joined = " ".join(args)
        add_error(errors, f"command timed out: {joined}: {output.strip()}")
        return output
    if proc.returncode != 0:
        joined = " ".join(args)
        detail = proc.stderr.strip() or proc.stdout.strip() or "no output"
        add_error(errors, f"command failed ({proc.returncode}): {joined}: {detail}")
    return proc.stdout


def run_git(root: Path, errors: list[str], *args: str) -> str:
    return run_command(["git", "-C", str(root), *args], errors)


def run_command_status(
    args: list[str],
    *,
    input_text: str | None = None,
    env: dict[str, str] | None = None,
) -> tuple[int, str]:
    proc = subprocess.run(
        args,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=bytecode_suppressed_env(env),
        check=False,
    )
    return proc.returncode, proc.stdout


def validate_single_skill(errors: list[str]) -> None:
    skill_dirs = sorted(path.name for path in SKILLS_ROOT.iterdir() if (path / "SKILL.md").is_file())
    check(errors, skill_dirs == ["arbor"], f"published skills must be exactly ['arbor'], got {skill_dirs}")
    for name in FORBIDDEN_SKILL_NAMES:
        check(errors, not (SKILLS_ROOT / name).exists(), f"forbidden skill directory exists: skills/{name}")

    skill = load_text(SKILLS_ROOT / "arbor" / "SKILL.md", errors)
    check(errors, skill.startswith("---\n"), "arbor skill must have YAML frontmatter")
    check(errors, "name: arbor" in skill, "arbor skill frontmatter must name the arbor skill")
    check(errors, "description:" in skill, "arbor skill frontmatter must include a description")
    check(errors, "## Startup Workflow" in skill, "arbor skill must document startup workflow")
    check(errors, "## Framework Repair Mode" in skill, "arbor skill must document repair mode")
    check(errors, "## Session Memory" in skill, "arbor skill must document session memory")
    check(errors, "## AGENTS.md Management" in skill, "arbor skill must document AGENTS management")
    check(errors, "run_session_startup_hook.py" in skill, "arbor skill must name the hookless startup entrypoint")
    check(errors, "run_hookless_finalization.py" in skill, "arbor skill must name the hookless finalization entrypoint")
    check(errors, "default runtime path is hookless" in skill, "arbor skill must make hookless runtime the default")


def validate_manifests(errors: list[str]) -> None:
    codex = load_json(PLUGIN_ROOT / ".codex-plugin" / "plugin.json", errors)
    claude = load_json(PLUGIN_ROOT / ".claude-plugin" / "plugin.json", errors)
    if not codex or not claude:
        return

    for field in ("name", "version", "description", "homepage", "repository", "license"):
        check(errors, codex.get(field) == claude.get(field), f"manifest field {field!r} must match")

    check(errors, codex.get("skills") == "./skills/", "Codex manifest must point at ./skills/")
    check(errors, "hooks" not in codex, "Codex manifest must not publish plugin-level hooks")
    check(errors, "hooks" not in claude, "Claude manifest must not publish plugin-level hooks")
    check(errors, "project-context" in claude.get("keywords", []), "Claude manifest should include project-context keyword")
    check(errors, "feedback" not in claude.get("keywords", []), "Claude manifest must not include old feedback keyword")

    interface = codex.get("interface")
    check(errors, isinstance(interface, dict), "Codex manifest must include interface object")
    if isinstance(interface, dict):
        prompts = interface.get("defaultPrompt")
        check(errors, isinstance(prompts, list) and len(prompts) <= 3, "defaultPrompt must contain at most 3 prompts")
        joined_prompt = "\n".join(str(item) for item in prompts or [])
        check(errors, "Initialize Arbor in this project" in joined_prompt, "defaultPrompt must include init prompt")
        check(errors, "framework check" in joined_prompt, "defaultPrompt must include framework check prompt")
        check(errors, "project hook" not in joined_prompt.lower(), "defaultPrompt must not steer default usage toward project hooks")
        check(errors, "hookless runtime contract" in joined_prompt, "defaultPrompt must include hookless runtime contract repair")
        long_description = str(interface.get("longDescription", ""))
        check(errors, len(long_description) <= 700, "Codex longDescription must stay concise")

    for path in (
        PLUGIN_ROOT / ".codex-plugin" / "plugin.json",
        PLUGIN_ROOT / ".claude-plugin" / "plugin.json",
        REPO_ROOT / ".agents" / "plugins" / "marketplace.json",
        REPO_ROOT / ".claude-plugin" / "marketplace.json",
    ):
        text = load_text(path, errors)
        for forbidden in FORBIDDEN_TEXT:
            check(errors, forbidden.lower() not in text.lower(), f"{path.relative_to(REPO_ROOT)} contains {forbidden!r}")


def validate_marketplace_entries(errors: list[str]) -> None:
    codex_path = REPO_ROOT / ".agents" / "plugins" / "marketplace.json"
    claude_path = REPO_ROOT / ".claude-plugin" / "marketplace.json"
    codex = load_json(codex_path, errors)
    claude = load_json(claude_path, errors)
    if not codex or not claude:
        return

    check(errors, codex.get("name") == "arbor", "Codex marketplace name must be arbor")
    check(errors, claude.get("name") == "arbor", "Claude marketplace name must be arbor")

    codex_plugins = codex.get("plugins")
    claude_plugins = claude.get("plugins")
    check(errors, isinstance(codex_plugins, list) and len(codex_plugins) == 1, "Codex marketplace must publish exactly one Arbor plugin")
    check(errors, isinstance(claude_plugins, list) and len(claude_plugins) == 1, "Claude marketplace must publish exactly one Arbor plugin")
    if not isinstance(codex_plugins, list) or not codex_plugins or not isinstance(claude_plugins, list) or not claude_plugins:
        return

    codex_entry = codex_plugins[0]
    claude_entry = claude_plugins[0]
    check(errors, isinstance(codex_entry, dict), "Codex marketplace plugin entry must be an object")
    check(errors, isinstance(claude_entry, dict), "Claude marketplace plugin entry must be an object")
    if not isinstance(codex_entry, dict) or not isinstance(claude_entry, dict):
        return

    codex_source = codex_entry.get("source")
    codex_source_path = codex_source.get("path") if isinstance(codex_source, dict) else None
    claude_source_path = claude_entry.get("source")
    expected_source = "./plugins/arbor"
    check(errors, codex_entry.get("name") == "arbor", "Codex marketplace plugin entry name must be arbor")
    check(errors, claude_entry.get("name") == "arbor", "Claude marketplace plugin entry name must be arbor")
    check(errors, codex_source_path == expected_source, "Codex marketplace source path must be ./plugins/arbor")
    check(errors, claude_source_path == expected_source, "Claude marketplace source path must be ./plugins/arbor")
    check(errors, (REPO_ROOT / expected_source).is_dir(), "marketplace local Arbor plugin source must exist")

    codex_policy = codex_entry.get("policy")
    check(errors, isinstance(codex_policy, dict), "Codex marketplace plugin entry must include policy object")
    if isinstance(codex_policy, dict):
        check(errors, codex_policy.get("installation") == "AVAILABLE", "Codex marketplace installation policy must be AVAILABLE")
    check(errors, codex_entry.get("category") in {"Engineering", "Coding"}, "Codex marketplace category must stay coding-related")
    check(errors, claude_entry.get("category") in {"Engineering", "Coding"}, "Claude marketplace category must stay coding-related")

    codex_interface = codex.get("interface")
    codex_description = ""
    if isinstance(codex_interface, dict):
        codex_description = str(codex_interface.get("description", ""))
    claude_description = str(claude_entry.get("description", ""))
    check(errors, "project" in codex_description.lower() or "context" in codex_description.lower(), "Codex marketplace description must describe project context")
    check(errors, "project" in claude_description.lower() or "context" in claude_description.lower(), "Claude marketplace description must describe project context")


def validate_reference_and_script_inventory(errors: list[str]) -> None:
    references = {path.name for path in REFERENCES_ROOT.iterdir() if path.is_file()}
    scripts = {path.name for path in SCRIPTS_ROOT.iterdir() if path.is_file()}
    check(errors, REQUIRED_REFERENCE_FILES <= references, "required Arbor reference files are missing")
    check(errors, REQUIRED_SCRIPT_FILES <= scripts, "required Arbor script files are missing")
    check(errors, not PLUGIN_LEVEL_HOOK_MANIFEST.exists(), "plugin-level hook manifest must not be published")
    check(errors, "check_quality_gate.py" in scripts, "quality gate runner must be published")
    check(errors, "check_process_state.py" not in scripts, "old process-state checker must not be published")
    check(errors, "check_real_workflow_chains.py" not in scripts, "old real-chain checker must not be published")
    check(errors, "real-workflow-chain-review.md" not in references, "old real-chain reference must not be published")
    agents_template = load_text(REFERENCES_ROOT / "agents-template.md", errors)
    normalized_agents_template = " ".join(agents_template.split()).lower()
    check(errors, "## Startup Protocol" not in agents_template, "AGENTS template must not publish a full Startup Protocol section")
    check(errors, "## Project Map" in agents_template, "AGENTS template must keep Project Map as the durable orientation surface")
    check(errors, "hookless runtime contract" in normalized_agents_template, "AGENTS template must name the hookless runtime contract as the normal startup path")
    check(errors, "SessionStart hook" not in agents_template, "AGENTS template must not name the legacy SessionStart hook as the normal startup path")
    for script in sorted(SCRIPTS_ROOT.glob("*.py")):
        text = load_text(script, errors)
        marker = "sys.dont_write_bytecode = True"
        check(errors, marker in text, f"{script.name} must suppress Python bytecode artifacts")
        marker_index = text.find(marker)
        local_imports = [
            index
            for module in (
                "from arbor_project_state",
                "from diagnose_project_hooks",
                "from init_project_memory",
                "from register_project_hooks",
            )
            if (index := text.find(module)) != -1
        ]
        if marker_index != -1 and local_imports:
            check(
                errors,
                marker_index < min(local_imports),
                f"{script.name} must suppress bytecode before importing local Arbor modules",
            )


def resource_link_paths(skill_text: str) -> list[str]:
    paths: list[str] = []
    in_resources = False
    for line in skill_text.splitlines():
        if line.strip() == "## Resources":
            in_resources = True
            continue
        if in_resources and line.startswith("## "):
            break
        if not in_resources or "`" not in line:
            continue
        parts = line.split("`")
        for index in range(1, len(parts), 2):
            candidate = parts[index].strip()
            if candidate.startswith(("references/", "scripts/")):
                paths.append(candidate)
    return paths


def validate_skill_resource_links(errors: list[str]) -> None:
    skill_root = SKILLS_ROOT / "arbor"
    skill_text = load_text(skill_root / "SKILL.md", errors)
    resource_paths = resource_link_paths(skill_text)
    check(errors, resource_paths, "arbor skill Resources must list package-local references and scripts")

    for resource in resource_paths:
        path = skill_root / Path(resource)
        check(errors, path.is_file(), f"arbor skill Resource link must exist: {resource}")

    required_public_resources = {
        "references/memory-template.md",
        "references/agents-template.md",
        "references/claude-template.md",
        "references/project-hooks-template.md",
        "references/runtime-smoke-template.md",
        "scripts/check_quality_gate.py",
        "scripts/check_codex_hookless_trigger_scenarios.py",
        "scripts/check_hookless_trigger_contract.py",
        "scripts/check_cache_sync_adapters.py",
        "scripts/check_install_state.py",
        "scripts/check_project_wrapper_smoke.py",
        "scripts/check_runtime_smoke_evidence.py",
        "scripts/run_session_startup_hook.py",
        "scripts/run_hookless_finalization.py",
        "scripts/run_framework_check.py",
        "scripts/register_project_hooks.py",
        "scripts/diagnose_project_hooks.py",
    }
    listed = set(resource_paths)
    for resource in sorted(required_public_resources):
        check(errors, resource in listed, f"arbor skill Resources must list {resource}")


def validate_skill_package_checker(errors: list[str]) -> None:
    script = SCRIPTS_ROOT / "check_skill_packages.py"
    spec = importlib.util.spec_from_file_location("arbor_check_skill_packages_probe", script)
    if spec is None or spec.loader is None:
        add_error(errors, "could not load check_skill_packages.py for timeout validation")
        return
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    with tempfile.TemporaryDirectory(prefix="arbor-skill-package-timeout-") as tmp:
        root = Path(tmp)
        skill_dir = root / "arbor"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: arbor\n---\n", encoding="utf-8")
        validator = root / "quick_validate.py"
        validator.write_text("# validator fixture\n", encoding="utf-8")

        def fake_find_quick_validate() -> Path:
            return validator

        def fake_default_skill_dirs(skills_root: Path) -> list[Path]:
            return [skill_dir]

        def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
            if "timeout" not in kwargs:
                raise AssertionError("missing timeout")
            raise subprocess.TimeoutExpired(cmd=kwargs.get("args", args[0] if args else []), timeout=kwargs["timeout"])

        original_argv = sys.argv[:]
        original_find = module.find_quick_validate
        original_default_dirs = module.default_skill_dirs
        original_run = module.subprocess.run
        try:
            sys.argv = ["check_skill_packages.py"]
            module.find_quick_validate = fake_find_quick_validate
            module.default_skill_dirs = fake_default_skill_dirs
            module.subprocess.run = fake_run
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                try:
                    code = module.main()
                except AssertionError as exc:
                    add_error(errors, f"skill package checker must pass a validator timeout: {exc}")
                    return
                except subprocess.TimeoutExpired as exc:
                    add_error(errors, f"skill package checker must not propagate validator timeouts: {exc}")
                    return
        finally:
            sys.argv = original_argv
            module.find_quick_validate = original_find
            module.default_skill_dirs = original_default_dirs
            module.subprocess.run = original_run

        output = stderr.getvalue()
        check(errors, code == 1, "skill package checker must fail when quick_validate times out")
        check(errors, "timed out" in output, "skill package checker must explain quick_validate timeouts")

    with tempfile.TemporaryDirectory(prefix="arbor-skill-package-launch-error-") as tmp:
        root = Path(tmp)
        skill_dir = root / "arbor"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: arbor\n---\n", encoding="utf-8")
        validator = root / "quick_validate.py"
        validator.write_text("# validator fixture\n", encoding="utf-8")

        def fake_find_quick_validate() -> Path:
            return validator

        def fake_default_skill_dirs(skills_root: Path) -> list[Path]:
            return [skill_dir]

        def fake_run(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
            raise OSError("simulated quick_validate launch failure")

        original_argv = sys.argv[:]
        original_find = module.find_quick_validate
        original_default_dirs = module.default_skill_dirs
        original_run = module.subprocess.run
        try:
            sys.argv = ["check_skill_packages.py"]
            module.find_quick_validate = fake_find_quick_validate
            module.default_skill_dirs = fake_default_skill_dirs
            module.subprocess.run = fake_run
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                try:
                    code = module.main()
                except OSError as exc:
                    add_error(errors, f"skill package checker must not propagate validator launch failures: {exc}")
                    code = 99
        finally:
            sys.argv = original_argv
            module.find_quick_validate = original_find
            module.default_skill_dirs = original_default_dirs
            module.subprocess.run = original_run

        output = stderr.getvalue()
        check(errors, code == 1, "skill package checker must fail when quick_validate cannot start")
        check(
            errors,
            "simulated quick_validate launch failure" in output,
            "skill package checker must explain quick_validate launch failures",
        )


def validate_text_boundary(errors: list[str]) -> None:
    paths = [
        REPO_ROOT / "README.md",
        SKILLS_ROOT / "arbor" / "SKILL.md",
        *sorted(REFERENCES_ROOT.glob("*.md")),
        *sorted(REFERENCES_ROOT.glob("*.json")),
        *sorted(path for path in (PLUGIN_ROOT / "hooks").iterdir() if path.is_file()),
    ]
    for path in paths:
        text = load_text(path, errors)
        for forbidden in FORBIDDEN_TEXT:
            check(errors, forbidden.lower() not in text.lower(), f"{path.relative_to(REPO_ROOT)} contains {forbidden!r}")


def validate_readme_quality_contract(errors: list[str]) -> None:
    readme = load_text(REPO_ROOT / "README.md", errors)
    normalized = " ".join(readme.split())
    for term in (
        "The hard gate is the source-ready quality contract",
        "checks package boundaries",
        "Python syntax without bytecode artifacts",
        "source hygiene for tracked and untracked published text files",
        "Python syntax validation treats invalid UTF-8 hook adapter sources as failures",
        "only the lightweight `arbor` skill is published",
        "plugin-level hook registrations are absent",
        "The release readiness gate adds installed-runtime proof",
        "matching Codex and Claude Code source manifest versions",
        "source manifest versions in `X.Y.Z` release form",
        "clean published source surface",
        "Codex and Claude marketplace source paths that point",
        "strict install-state checks for Codex and Claude Code caches",
        "validated runtime smoke evidence file",
        "exactly one row for each template matrix entry",
        "no extra runtime rows",
        "A passing hard gate alone is not proof",
        "Its `Commit:` must match the release source `HEAD`",
        "7-or-more-character hexadecimal git commit",
        "`Date:` must use `YYYY-MM-DD`",
        "identifying the operator",
        "Runtime smoke evidence records its own validator command passing",
        "full Codex and Claude Code event matrix",
        "Fired rows must include runtime trust proof",
        "absolute Python wrapper-or-launcher proof",
        "cache path that supplied the hook adapter",
        "Drift, missing caches, dirty source, or `not run` install-state checks mean the runtime evidence is not yet publishable",
        "Automatic cache discovery considers only complete Arbor plugin roots in `X.Y.Z`",
        "Install-state selected-cache reporting mirrors project wrappers: only complete",
        "Strict mode also refuses non-`X.Y.Z` source manifest versions",
        "The skill package checker also bounds each `quick_validate.py` invocation",
        "Validator launch failures are reported as normal skill package failures",
        "The context boundary check reads published text files as UTF-8 only",
        "Published JSON surfaces must be JSON objects",
        "timeouts or launch failures as `shared-adapters-probe-failed`",
        "Diagnosis rejects incomplete `--plugin-root` directories before probing shared",
        "Subprocess launch failures also fail the affected row",
        "Release readiness subprocess launch failures must fail the affected row",
        "soft-fail policy on timeout, adapter discovery failure, or adapter launch failure",
        "Local plugin cache sync also requires matching `X.Y.Z` Codex and Claude source manifest versions",
        "stages cache copies before replacing installed cache directories",
        "preserves the existing installed cache if staging copy or final replacement fails",
        "refreshes cached hook adapters and removes legacy plugin-level hook manifests only inside existing `X.Y.Z` release cache directories",
        "Local plugin cache sync bounds its git dirty-source and commit probes",
        "Initialization templates must be readable UTF-8 package files",
        "Hook configuration files that cannot be read as UTF-8 are reported as invalid",
        "Registration and repair also fail cleanly on unreadable hook configuration encodings",
    ):
        check(errors, term in normalized, f"README quality contract missing {term!r}")


def validate_hook_runtime_documentation_contract(errors: list[str]) -> None:
    docs = {
        "README.md": REPO_ROOT / "README.md",
        "skills/arbor/SKILL.md": SKILLS_ROOT / "arbor" / "SKILL.md",
        "skills/arbor/references/project-hooks-template.md": REFERENCES_ROOT / "project-hooks-template.md",
    }
    required_terms = (
        "plugin-root environment paths that cannot be inspected",
        "startup helper timeouts or launch failures",
        "git probes and guide checks that time out or fail to start",
        "block-mode memory helper timeouts or launch failures",
    )
    for label, path in docs.items():
        normalized = " ".join(load_text(path, errors).split()).lower()
        for term in required_terms:
            check(errors, term in normalized, f"{label} hook runtime contract missing {term!r}")


def validate_startup_memory_documentation_contract(errors: list[str]) -> None:
    docs = {
        "README.md": REPO_ROOT / "README.md",
        "skills/arbor/SKILL.md": SKILLS_ROOT / "arbor" / "SKILL.md",
    }
    required_terms = (
        "unreadable memory is reported as unreadable",
        "must not be treated as explicit resume context",
        "dry-run validates legacy memory readability",
    )
    for label, path in docs.items():
        normalized = " ".join(load_text(path, errors).split()).lower()
        for term in required_terms:
            check(errors, term in normalized, f"{label} startup memory contract missing {term!r}")


def validate_framework_install_documentation_contract(errors: list[str]) -> None:
    docs = {
        "README.md": REPO_ROOT / "README.md",
        "skills/arbor/SKILL.md": SKILLS_ROOT / "arbor" / "SKILL.md",
    }
    required_terms = (
        "source manifests must be json objects",
        "source or cache digest failures are reported as install-state drift",
        "not as tracebacks",
    )
    for label, path in docs.items():
        normalized = " ".join(load_text(path, errors).split()).lower()
        for term in required_terms:
            check(errors, term in normalized, f"{label} framework/install contract missing {term!r}")


def validate_quality_gate_framework_exception(errors: list[str]) -> None:
    module_path = SCRIPTS_ROOT / "check_quality_gate.py"
    spec = importlib.util.spec_from_file_location("arbor_check_quality_gate_probe", module_path)
    if spec is None or spec.loader is None:
        add_error(errors, "could not load check_quality_gate.py for framework exception validation")
        return
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    trust_only = """**Arbor Framework Check**
| Surface | Required | Status | Evidence | Repair |
| --- | --- | --- | --- | --- |
| AGENTS.md | yes | pass | AGENTS.md | none |
| .codex/hooks.json + .codex/hooks/ | yes | blocked | command hooks and wrappers exist, but Codex /hooks trust cannot be proven from files | verify trust |
| .claude/settings.json + .claude/hooks/ | yes | pass | ready | none |
| shared hook adapters | yes | pass | ready | none |

Result: blocked
"""
    extra_failure = """**Arbor Framework Check**
| Surface | Required | Status | Evidence | Repair |
| --- | --- | --- | --- | --- |
| AGENTS.md | yes | fail | AGENTS.md is a directory | replace path conflict |
| .codex/hooks.json + .codex/hooks/ | yes | blocked | command hooks and wrappers exist, but Codex /hooks trust cannot be proven from files | verify trust |
| shared hook adapters | yes | pass | ready | none |

Result: blocked
"""
    wrong_surface = """**Arbor Framework Check**
| Surface | Required | Status | Evidence | Repair |
| --- | --- | --- | --- | --- |
| .claude/settings.json + .claude/hooks/ | yes | blocked | invalid JSON | fix settings |

Result: blocked
"""
    no_result = trust_only.replace("Result: blocked", "")

    check(errors, module.framework_result(trust_only) == "blocked", "quality gate must parse rendered framework Result")
    check(errors, module.framework_block_is_only_codex_trust(trust_only), "quality gate must accept only the Codex trust caveat")
    check(errors, not module.framework_block_is_only_codex_trust(extra_failure), "quality gate must reject Codex trust caveat plus another required failure")
    check(errors, not module.framework_block_is_only_codex_trust(wrong_surface), "quality gate must reject blocked non-Codex surfaces")
    check(errors, module.framework_result(no_result) is None, "quality gate must not invent a missing framework Result")
    check(errors, not module.framework_block_is_only_codex_trust(no_result), "quality gate must reject framework output with no Result")


def validate_quality_gate_is_artifact_free(errors: list[str]) -> None:
    module_path = SCRIPTS_ROOT / "check_quality_gate.py"
    spec = importlib.util.spec_from_file_location("arbor_check_quality_gate_artifact_probe", module_path)
    if spec is None or spec.loader is None:
        add_error(errors, "could not load check_quality_gate.py for artifact-free validation")
        return
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    checks = module.gate_checks(REPO_ROOT, PLUGIN_ROOT)
    names = [check.name for check in checks]
    commands = [" ".join(check.command) for check in checks if check.command is not None]
    check(errors, "python syntax" in names, "quality gate must use artifact-free Python syntax validation")
    check(errors, "source hygiene" in names, "quality gate must validate source hygiene beyond git diff --check")
    check(
        errors,
        any("check_source_hygiene.py" in command for command in commands),
        "quality gate must run check_source_hygiene.py for tracked and untracked published files",
    )
    check(errors, all("compileall" not in command for command in commands), "quality gate must not create __pycache__ via compileall")
    subprocess_env = getattr(module, "subprocess_env", None)
    check(errors, callable(subprocess_env), "quality gate must expose bytecode-suppressed subprocess env")
    if callable(subprocess_env):
        check(
            errors,
            subprocess_env().get("PYTHONDONTWRITEBYTECODE") == "1",
            "quality gate subprocesses must not write Python bytecode artifacts",
        )
    hookless_commands = [check.command for check in checks if check.name == "hookless repair smoke" and check.command is not None]
    check(errors, hookless_commands, "quality gate must run the hookless repair smoke")
    for command in hookless_commands:
        check(
            errors,
            any("check_hookless_repair_smoke.py" in part for part in command),
            "quality gate must invoke the hookless repair smoke script",
        )
    trigger_commands = [check.command for check in checks if check.name == "hookless trigger contract" and check.command is not None]
    check(errors, trigger_commands, "quality gate must run the hookless trigger contract")
    for command in trigger_commands:
        check(
            errors,
            any("check_hookless_trigger_contract.py" in part for part in command),
            "quality gate must invoke the hookless trigger contract script",
        )

    syntax_module_path = SCRIPTS_ROOT / "check_python_syntax.py"
    syntax_spec = importlib.util.spec_from_file_location("arbor_check_python_syntax_probe", syntax_module_path)
    if syntax_spec is None or syntax_spec.loader is None:
        add_error(errors, "could not load check_python_syntax.py for encoding validation")
    else:
        syntax_module = importlib.util.module_from_spec(syntax_spec)
        sys.modules[syntax_spec.name] = syntax_module
        syntax_spec.loader.exec_module(syntax_module)
        with tempfile.TemporaryDirectory(prefix="arbor-python-syntax-encoding-") as tmp:
            root = Path(tmp)
            hook_adapter = root / "session-start"
            hook_adapter.write_bytes(b"\xff#!/usr/bin/env python3\n")
            syntax_failures = syntax_module.validate_roots([root])
            check(
                errors,
                any("decode" in failure for failure in syntax_failures),
                "Python syntax check must fail invalid UTF-8 hook adapter sources instead of skipping them",
            )

    original_timeout = os.environ.get("ARBOR_QUALITY_GATE_TIMEOUT_SECONDS")
    os.environ["ARBOR_QUALITY_GATE_TIMEOUT_SECONDS"] = "0.1"
    try:
        slow_outcome = module.run_check(
            module.GateCheck(
                "slow check",
                [sys.executable, "-c", "import time; time.sleep(0.4)"],
            )
        )
    finally:
        if original_timeout is None:
            os.environ.pop("ARBOR_QUALITY_GATE_TIMEOUT_SECONDS", None)
        else:
            os.environ["ARBOR_QUALITY_GATE_TIMEOUT_SECONDS"] = original_timeout
    check(errors, not slow_outcome.ok, "quality gate subprocess timeouts must fail the check")
    check(errors, "timed out" in slow_outcome.output, "quality gate subprocess timeouts must explain the timeout")

    original_subprocess_run = module.subprocess.run

    def raise_subprocess_oserror(_command: list[str], *_args: Any, **_kwargs: Any) -> Any:
        raise OSError("simulated quality gate command launch failure")

    module.subprocess.run = raise_subprocess_oserror
    try:
        try:
            launch_outcome = module.run_check(
                module.GateCheck(
                    "launch failure check",
                    [sys.executable, "-c", "pass"],
                )
            )
        except OSError as exc:
            add_error(errors, f"quality gate subprocess launch failures must not propagate: {exc}")
            launch_outcome = module.GateOutcome(False, "fail", "", "")
    finally:
        module.subprocess.run = original_subprocess_run
    check(errors, not launch_outcome.ok, "quality gate subprocess launch failures must fail the check")
    check(
        errors,
        "simulated quality gate command launch failure" in launch_outcome.output,
        "quality gate subprocess launch failures must explain the launch error",
    )


def validate_quality_harness_modularity(errors: list[str]) -> None:
    module_script = SCRIPTS_ROOT / "check_cache_sync_adapters.py"
    check(errors, module_script.is_file(), "cache sync adapter validation must live in its own module script")
    if module_script.is_file():
        module_text = module_script.read_text(encoding="utf-8")
        main_text = Path(__file__).read_text(encoding="utf-8")
        forbidden_definition = "def " + "validate_cache_sync_"
        check(
            errors,
            "check_plugin_adapters.py" not in module_text,
            "cache sync adapter module must be self-contained instead of importing the main adapter checker",
        )
        check(
            errors,
            "sync_local_plugin_cache.py" in module_text,
            "cache sync adapter module must validate the cache-sync implementation directly",
        )
        check(
            errors,
            forbidden_definition not in main_text,
            "main adapter checker must not define cache-sync-specific validation functions",
        )
        output = run_command([sys.executable, str(module_script)], errors)
        check(errors, "cache sync adapter checks passed" in output, "cache sync adapter module must report pass evidence")

    wrapper_smoke_adapter_script = SCRIPTS_ROOT / "check_project_wrapper_smoke_adapters.py"
    check(
        errors,
        wrapper_smoke_adapter_script.is_file(),
        "project wrapper smoke adapter validation must live in its own module script",
    )
    main_text = Path(__file__).read_text(encoding="utf-8")
    forbidden_wrapper_smoke_definition = "def " + "validate_project_wrapper_smoke_script"
    check(
        errors,
        forbidden_wrapper_smoke_definition not in main_text,
        "main adapter checker must not define project-wrapper-smoke-specific validation functions",
    )
    if wrapper_smoke_adapter_script.is_file():
        module_text = wrapper_smoke_adapter_script.read_text(encoding="utf-8")
        check(
            errors,
            "check_plugin_adapters.py" not in module_text,
            "project wrapper smoke adapter module must be self-contained instead of importing the main adapter checker",
        )
        check(
            errors,
            "check_project_wrapper_smoke.py" in module_text,
            "project wrapper smoke adapter module must validate the wrapper-smoke implementation directly",
        )
        output = run_command([sys.executable, str(wrapper_smoke_adapter_script)], errors)
        check(
            errors,
            "project wrapper smoke adapter checks passed" in output,
            "project wrapper smoke adapter module must report pass evidence",
        )

    runtime_evidence_adapter_script = SCRIPTS_ROOT / "check_runtime_smoke_evidence_adapters.py"
    check(
        errors,
        runtime_evidence_adapter_script.is_file(),
        "runtime smoke evidence adapter validation must live in its own module script",
    )
    forbidden_runtime_evidence_definition = "def " + "validate_runtime_smoke_evidence_checker"
    check(
        errors,
        forbidden_runtime_evidence_definition not in main_text,
        "main adapter checker must not define runtime-smoke-evidence-specific validation functions",
    )
    if runtime_evidence_adapter_script.is_file():
        module_text = runtime_evidence_adapter_script.read_text(encoding="utf-8")
        check(
            errors,
            "check_plugin_adapters.py" not in module_text,
            "runtime smoke evidence adapter module must be self-contained instead of importing the main adapter checker",
        )
        check(
            errors,
            "check_runtime_smoke_evidence.py" in module_text,
            "runtime smoke evidence adapter module must validate the evidence checker implementation directly",
        )
        output = run_command([sys.executable, str(runtime_evidence_adapter_script)], errors)
        check(
            errors,
            "runtime smoke evidence adapter checks passed" in output,
            "runtime smoke evidence adapter module must report pass evidence",
        )

def validate_source_hygiene_checker(errors: list[str]) -> None:
    module_path = SCRIPTS_ROOT / "check_source_hygiene.py"
    if not module_path.is_file():
        add_error(errors, "source hygiene checker script must be published")
        return
    spec = importlib.util.spec_from_file_location("arbor_check_source_hygiene_probe", module_path)
    if spec is None or spec.loader is None:
        add_error(errors, "could not load check_source_hygiene.py for source hygiene validation")
        return
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    with tempfile.TemporaryDirectory(prefix="arbor-source-hygiene-") as tmp:
        root = Path(tmp)
        readme = root / "README.md"
        readme.write_text("# Fixture\n", encoding="utf-8")
        plugin_root = root / "plugins" / "arbor"
        script_root = plugin_root / "skills" / "arbor" / "scripts"
        script_root.mkdir(parents=True)
        bad_script = script_root / "new_untracked_script.py"
        bad_script.write_text("print('bad')  \n<<<<<<< HEAD\n", encoding="utf-8")
        missing_newline = plugin_root / "skills" / "arbor" / "SKILL.md"
        missing_newline.parent.mkdir(parents=True, exist_ok=True)
        missing_newline.write_text("---\nname: arbor\n---", encoding="utf-8")
        assets = plugin_root / "assets"
        assets.mkdir()
        (assets / "icon.png").write_bytes(b"\x89PNG\r\n\x1a\n")

        failures = module.validate_roots([readme, plugin_root])
        check(
            errors,
            any("trailing whitespace" in failure and "new_untracked_script.py" in failure for failure in failures),
            "source hygiene checker must catch trailing whitespace in newly added published files",
        )
        check(
            errors,
            any("conflict marker" in failure and "new_untracked_script.py" in failure for failure in failures),
            "source hygiene checker must catch merge conflict markers in published files",
        )
        check(
            errors,
            any("final newline" in failure and "SKILL.md" in failure for failure in failures),
            "source hygiene checker must catch missing final newlines in published files",
        )
        check(
            errors,
            not any("icon.png" in failure for failure in failures),
            "source hygiene checker must skip binary assets instead of reporting decode failures",
        )


def validate_runtime_smoke_template(errors: list[str]) -> None:
    text = load_text(REFERENCES_ROOT / "runtime-smoke-template.md", errors)
    normalized = " ".join(text.split())
    for term in (
        "## Hard Gate",
        "Version:",
        "Commit:",
        "Date:",
        "Operator:",
        "concrete `X.Y.Z` plugin version under release",
        "Audit metadata and required sections must each appear exactly once",
        "hexadecimal git commit prefix or full hash",
        "matches the release source `HEAD`",
        "`Date:` must use `YYYY-MM-DD`",
        "operator identity",
        "evidence remains auditable",
        "Each audit metadata field and required section must appear exactly once",
        "Result must be pass or accepted",
        "self-validation command",
        "## Cache And Install State",
        "Cache version selected by project wrapper",
        "check_install_state.py",
        "--strict",
        "--runtime codex|claude|both",
        "Strict install/cache checks must pass",
        "Dirty-source sync and strict guards must pass",
        "Dirty source sync guard",
        "Dirty source strict guard",
        "Cache detail blockers must be absent",
        "Legacy plugin-level `hooks/hooks.json` present",
        "`__pycache__` / `*.pyc` present in synced cache",
        "## Hook Runtime Smoke",
        "Trusted",
        "Fired",
        "Wrapper or launcher uses absolute Python",
        "Cache discovery path",
        "Fired rows must include absolute local cache discovery paths",
        "Fired rows must prove runtime trust and absolute Python wrapper-or-launcher use",
        "Keep all template rows",
        "exactly one row for each template matrix entry",
        "No extra runtime rows",
        "Unavailable reason",
        "not run",
        "Known Risks cannot be `none` when any runtime smoke row is not fully passing",
        "## Deterministic Substitute Evidence",
        "Project wrapper execution with plugin-root env",
        "Project wrapper execution through fake Codex cache",
        "Project wrapper execution through fake Claude cache",
        "Multi-version cache selection with broken older adapter",
        "POSIX command rendering",
        "Deterministic substitute checks must pass",
    ):
        check(errors, term in normalized, f"runtime smoke template missing {term!r}")


def current_source_version() -> str:
    manifest = json.loads((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8-sig"))
    version = manifest.get("version")
    if not isinstance(version, str) or not version:
        raise RuntimeError("Codex manifest must declare a version")
    return version


def next_patch_version(version: str) -> str:
    major, minor, patch = (int(part) for part in version.split("."))
    return f"{major}.{minor}.{patch + 1}"


def complete_runtime_smoke_evidence() -> str:
    version = current_source_version()
    return (
        "# Arbor Runtime Smoke Evidence\n\n"
        f"Version: {version}\n"
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
        f"- Codex cache path: C:/Users/example/.codex/plugins/cache/arbor/arbor/{version}\n"
        "- Claude cache path: not run - Claude Code unavailable on this machine\n"
        f"- Cache version selected by project wrapper: {version}\n"
        "- Dirty source sync guard: pass\n"
        "- Dirty source strict guard: pass\n"
        "- Legacy plugin-level `hooks/hooks.json` present: no\n"
        "- `__pycache__` / `*.pyc` present in synced cache: no\n\n"
        "## Hook Runtime Smoke\n\n"
        "| Runtime | OS | Event | Trusted | Fired | Wrapper or launcher uses absolute Python | Cache discovery path | Evidence | Unavailable reason |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
        f"| Codex | Windows | SessionStart | yes | yes | yes | C:/Users/example/.codex/plugins/cache/arbor/arbor/{version} | startup context rendered | none |\n"
        f"| Codex | Windows | Stop | yes | yes | yes | C:/Users/example/.codex/plugins/cache/arbor/arbor/{version} | memory hygiene completed | none |\n"
        "| Claude Code | Windows | SessionStart | not run | not run | yes | not run | not run | Claude Code unavailable on this machine |\n"
        "| Claude Code | Windows | Stop | not run | not run | yes | not run | not run | Claude Code unavailable on this machine |\n"
        "| Codex | macOS/Linux | SessionStart | not run | not run | yes | not run | not run | macOS/Linux runtime not available on this machine |\n"
        "| Codex | macOS/Linux | Stop | not run | not run | yes | not run | not run | macOS/Linux runtime not available on this machine |\n"
        "| Claude Code | macOS/Linux | SessionStart | not run | not run | yes | not run | not run | macOS/Linux runtime not available on this machine |\n"
        "| Claude Code | macOS/Linux | Stop | not run | not run | yes | not run | not run | macOS/Linux runtime not available on this machine |\n\n"
        "## Deterministic Substitute Evidence\n\n"
        "- Project wrapper execution with plugin-root env: pass\n"
        "- Project wrapper execution through fake Codex cache: pass\n"
        "- Project wrapper execution through fake Claude cache: pass\n"
        "- Multi-version cache selection with broken older adapter: pass\n"
        "- POSIX command rendering: pass\n\n"
        "## Known Risks\n\n"
        "- Claude Code and macOS/Linux runtime smoke not run on this Windows machine.\n"
    )


def runtime_smoke_evidence_for_commit(commit: str) -> str:
    return complete_runtime_smoke_evidence().replace("Commit: 0123456\n", f"Commit: {commit}\n")


def write_temp_marketplaces(root: Path) -> None:
    codex = root / ".agents" / "plugins" / "marketplace.json"
    claude = root / ".claude-plugin" / "marketplace.json"
    codex.parent.mkdir(parents=True, exist_ok=True)
    claude.parent.mkdir(parents=True, exist_ok=True)
    codex.write_text(
        '{"name":"arbor","plugins":[{"name":"arbor","source":{"source":"local","path":"./plugins/arbor"},"policy":{"installation":"AVAILABLE"},"category":"Engineering"}]}\n',
        encoding="utf-8",
    )
    claude.write_text(
        '{"name":"arbor","plugins":[{"name":"arbor","source":"./plugins/arbor","category":"Coding"}]}\n',
        encoding="utf-8",
    )


def validate_release_readiness_check(errors: list[str]) -> None:
    script = SCRIPTS_ROOT / "check_release_readiness.py"
    check(errors, script.is_file(), "release readiness checker script is missing")
    if not script.is_file():
        return
    release_version = current_source_version()
    mismatched_version = next_patch_version(release_version)

    spec = importlib.util.spec_from_file_location("arbor_check_release_readiness_timeout_probe", script)
    if spec is None or spec.loader is None:
        add_error(errors, "could not load check_release_readiness.py for timeout validation")
        return
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    original_timeout = os.environ.get("ARBOR_RELEASE_READINESS_TIMEOUT_SECONDS")
    os.environ["ARBOR_RELEASE_READINESS_TIMEOUT_SECONDS"] = "0.1"
    try:
        slow_outcome = module.run_check(
            module.ReadinessCheck(
                "slow readiness check",
                [sys.executable, "-c", "import time; time.sleep(0.4)"],
            )
        )
    finally:
        if original_timeout is None:
            os.environ.pop("ARBOR_RELEASE_READINESS_TIMEOUT_SECONDS", None)
        else:
            os.environ["ARBOR_RELEASE_READINESS_TIMEOUT_SECONDS"] = original_timeout
    check(errors, slow_outcome.status == "fail", "release readiness subprocess timeouts must fail the check")
    check(errors, "timed out" in slow_outcome.output, "release readiness subprocess timeouts must explain the timeout")

    original_subprocess_run = module.subprocess.run

    def raise_subprocess_oserror(_command: list[str], *_args: Any, **_kwargs: Any) -> Any:
        raise OSError("simulated readiness command launch failure")

    module.subprocess.run = raise_subprocess_oserror
    try:
        try:
            launch_outcome = module.run_check(
                module.ReadinessCheck(
                    "launch failure readiness check",
                    [sys.executable, "-c", "pass"],
                )
            )
        except OSError as exc:
            add_error(errors, f"release readiness subprocess launch failures must not propagate: {exc}")
            launch_outcome = module.ReadinessOutcome("launch failure readiness check", "fail", "")
    finally:
        module.subprocess.run = original_subprocess_run
    check(errors, launch_outcome.status == "fail", "release readiness subprocess launch failures must fail the check")
    check(
        errors,
        "simulated readiness command launch failure" in launch_outcome.output,
        "release readiness subprocess launch failures must explain the launch error",
    )

    with tempfile.TemporaryDirectory(prefix="arbor-release-readiness-git-timeout-") as tmp:
        root = Path(tmp) / "repo"
        source = root / "plugins" / "arbor"
        source.mkdir(parents=True)
        (root / "README.md").write_text("clean public README\n", encoding="utf-8")
        write_temp_marketplaces(root)
        original_subprocess_run = module.subprocess.run

        def raise_git_timeout(command: list[str], *_args: Any, **_kwargs: Any) -> Any:
            if command and command[0] == "git":
                raise subprocess.TimeoutExpired(command, timeout=0.1)
            return original_subprocess_run(command, *_args, **_kwargs)

        module.subprocess.run = raise_git_timeout
        try:
            try:
                published_outcome = module.run_published_source_check(root, source)
            except subprocess.TimeoutExpired as exc:
                add_error(errors, f"published source git status timeouts must not propagate: {exc}")
                published_outcome = module.ReadinessOutcome("published source", "fail", "")
        finally:
            module.subprocess.run = original_subprocess_run
    check(errors, published_outcome.status == "fail", "published source git status timeouts must fail readiness")
    check(errors, "timed out" in published_outcome.output, "published source git status timeouts must explain the timeout")

    with tempfile.TemporaryDirectory(prefix="arbor-release-readiness-git-launch-") as tmp:
        root = Path(tmp) / "repo"
        source = root / "plugins" / "arbor"
        source.mkdir(parents=True)
        (root / "README.md").write_text("clean public README\n", encoding="utf-8")
        write_temp_marketplaces(root)
        original_subprocess_run = module.subprocess.run

        def raise_git_launch_failure(command: list[str], *_args: Any, **_kwargs: Any) -> Any:
            if command and command[0] == "git":
                raise OSError("simulated published source git launch failure")
            return original_subprocess_run(command, *_args, **_kwargs)

        module.subprocess.run = raise_git_launch_failure
        try:
            try:
                published_launch_outcome = module.run_published_source_check(root, source)
            except OSError as exc:
                add_error(errors, f"published source git status launch failures must not propagate: {exc}")
                published_launch_outcome = module.ReadinessOutcome("published source", "fail", "")
        finally:
            module.subprocess.run = original_subprocess_run
        check(errors, published_launch_outcome.status == "fail", "published source git status launch failures must fail readiness")
        check(
            errors,
            "simulated published source git launch failure" in published_launch_outcome.output,
            "published source git status launch failures must explain the launch error",
        )

    with tempfile.TemporaryDirectory(prefix="arbor-release-readiness-current-state-") as tmp:
        current_state_cache_root = Path(tmp)
        code, output = run_command_status(
            [
                sys.executable,
                str(script),
                "--skip-quality-gate",
                "--codex-cache-base",
                str(current_state_cache_root / "codex-cache"),
                "--claude-cache-base",
                str(current_state_cache_root / "claude-cache"),
            ]
        )
    check(errors, code == 1, "release readiness checker must fail when install-state or runtime smoke evidence is missing")
    for term in (
        "Arbor release readiness",
        "install-state codex: fail",
        "install-state claude: fail",
        "runtime smoke evidence: missing",
        "release readiness failed",
    ):
        check(errors, term in output, f"release readiness current-state output missing {term!r}")

    with tempfile.TemporaryDirectory(prefix="arbor-release-readiness-pass-") as tmp:
        root = Path(tmp)
        source = root / "plugins" / "arbor"
        codex_cache_base = root / "codex-cache"
        claude_cache_base = root / "claude-cache"
        copy_plugin_to_cache(source)
        copy_plugin_to_cache(codex_cache_base / release_version)
        copy_plugin_to_cache(claude_cache_base / release_version)
        (root / "README.md").write_text("clean public README\n", encoding="utf-8")
        write_temp_marketplaces(root)
        evidence = root / "runtime-smoke.md"
        run_git(root, errors, "init")
        run_git(root, errors, "config", "user.email", "arbor@example.invalid")
        run_git(root, errors, "config", "user.name", "Arbor Check")
        evidence.write_text(complete_runtime_smoke_evidence(), encoding="utf-8")
        run_git(root, errors, "add", ".")
        run_git(root, errors, "commit", "-m", "clean release source")
        head = run_git(root, errors, "rev-parse", "HEAD").strip()
        evidence.write_text(runtime_smoke_evidence_for_commit(head), encoding="utf-8")
        pass_code, pass_output = run_command_status(
            [
                sys.executable,
                str(script),
                "--skip-quality-gate",
                "--root",
                str(root),
                "--plugin-root",
                str(source),
                "--codex-cache-base",
                str(codex_cache_base),
                "--claude-cache-base",
                str(claude_cache_base),
                "--runtime-smoke-evidence",
                str(evidence),
            ]
        )
        check(errors, pass_code == 0, f"release readiness checker must pass with clean temp source/cache/evidence: {pass_output.strip()}")
        check(errors, "release readiness passed" in pass_output, "release readiness checker must report pass evidence")

    with tempfile.TemporaryDirectory(prefix="arbor-release-readiness-wrong-marketplace-") as tmp:
        root = Path(tmp)
        source = root / "plugins" / "arbor"
        codex_cache_base = root / "codex-cache"
        claude_cache_base = root / "claude-cache"
        copy_plugin_to_cache(source)
        copy_plugin_to_cache(codex_cache_base / release_version)
        copy_plugin_to_cache(claude_cache_base / release_version)
        (root / "README.md").write_text("clean public README\n", encoding="utf-8")
        write_temp_marketplaces(root)
        codex_marketplace = root / ".agents" / "plugins" / "marketplace.json"
        codex_data = json.loads(codex_marketplace.read_text(encoding="utf-8"))
        codex_data["plugins"][0]["source"]["path"] = "./plugins/not-arbor"
        codex_marketplace.write_text(json.dumps(codex_data, indent=2) + "\n", encoding="utf-8")
        evidence = root / "runtime-smoke.md"
        run_git(root, errors, "init")
        run_git(root, errors, "config", "user.email", "arbor@example.invalid")
        run_git(root, errors, "config", "user.name", "Arbor Check")
        evidence.write_text(complete_runtime_smoke_evidence(), encoding="utf-8")
        run_git(root, errors, "add", ".")
        run_git(root, errors, "commit", "-m", "wrong marketplace source")
        head = run_git(root, errors, "rev-parse", "HEAD").strip()
        evidence.write_text(runtime_smoke_evidence_for_commit(head), encoding="utf-8")
        wrong_marketplace_code, wrong_marketplace_output = run_command_status(
            [
                sys.executable,
                str(script),
                "--skip-quality-gate",
                "--root",
                str(root),
                "--plugin-root",
                str(source),
                "--codex-cache-base",
                str(codex_cache_base),
                "--claude-cache-base",
                str(claude_cache_base),
                "--runtime-smoke-evidence",
                str(evidence),
            ]
        )
        check(errors, wrong_marketplace_code == 1, "release readiness checker must reject wrong marketplace source paths")
        check(errors, "marketplace source: fail" in wrong_marketplace_output, "release readiness checker must report marketplace source failures")
        check(
            errors,
            "./plugins/not-arbor" in wrong_marketplace_output,
            "release readiness checker must explain wrong marketplace source paths",
        )

    with tempfile.TemporaryDirectory(prefix="arbor-release-readiness-wrong-smoke-commit-") as tmp:
        root = Path(tmp)
        source = root / "plugins" / "arbor"
        codex_cache_base = root / "codex-cache"
        claude_cache_base = root / "claude-cache"
        copy_plugin_to_cache(source)
        copy_plugin_to_cache(codex_cache_base / release_version)
        copy_plugin_to_cache(claude_cache_base / release_version)
        (root / "README.md").write_text("clean public README\n", encoding="utf-8")
        write_temp_marketplaces(root)
        evidence = root / "runtime-smoke-wrong-commit.md"
        evidence.write_text(complete_runtime_smoke_evidence(), encoding="utf-8")
        run_git(root, errors, "init")
        run_git(root, errors, "config", "user.email", "arbor@example.invalid")
        run_git(root, errors, "config", "user.name", "Arbor Check")
        run_git(root, errors, "add", ".")
        run_git(root, errors, "commit", "-m", "clean release source")
        wrong_commit_code, wrong_commit_output = run_command_status(
            [
                sys.executable,
                str(script),
                "--skip-quality-gate",
                "--root",
                str(root),
                "--plugin-root",
                str(source),
                "--codex-cache-base",
                str(codex_cache_base),
                "--claude-cache-base",
                str(claude_cache_base),
                "--runtime-smoke-evidence",
                str(evidence),
            ]
        )
        check(errors, wrong_commit_code == 1, "release readiness checker must reject runtime smoke evidence for the wrong source commit")
        check(errors, "runtime smoke commit: fail" in wrong_commit_output, "release readiness checker must report runtime smoke commit failures")
        check(
            errors,
            "does not match release source HEAD" in wrong_commit_output,
            "release readiness checker must explain source/evidence commit mismatch",
        )

    with tempfile.TemporaryDirectory(prefix="arbor-release-readiness-mismatched-source-manifests-") as tmp:
        root = Path(tmp)
        source = root / "plugins" / "arbor"
        codex_cache_base = root / "codex-cache"
        claude_cache_base = root / "claude-cache"
        copy_plugin_to_cache(source)
        claude_manifest = source / ".claude-plugin" / "plugin.json"
        claude_data = json.loads(claude_manifest.read_text(encoding="utf-8-sig"))
        claude_data["version"] = mismatched_version
        claude_manifest.write_text(json.dumps(claude_data, indent=2) + "\n", encoding="utf-8")
        shutil.copytree(source, codex_cache_base / release_version)
        shutil.copytree(source, claude_cache_base / release_version)
        (root / "README.md").write_text("clean public README\n", encoding="utf-8")
        write_temp_marketplaces(root)
        evidence = root / "runtime-smoke.md"
        run_git(root, errors, "init")
        run_git(root, errors, "config", "user.email", "arbor@example.invalid")
        run_git(root, errors, "config", "user.name", "Arbor Check")
        evidence.write_text(complete_runtime_smoke_evidence(), encoding="utf-8")
        run_git(root, errors, "add", ".")
        run_git(root, errors, "commit", "-m", "mismatched source manifests")
        head = run_git(root, errors, "rev-parse", "HEAD").strip()
        evidence.write_text(runtime_smoke_evidence_for_commit(head), encoding="utf-8")
        mismatched_manifest_code, mismatched_manifest_output = run_command_status(
            [
                sys.executable,
                str(script),
                "--skip-quality-gate",
                "--root",
                str(root),
                "--plugin-root",
                str(source),
                "--codex-cache-base",
                str(codex_cache_base),
                "--claude-cache-base",
                str(claude_cache_base),
                "--runtime-smoke-evidence",
                str(evidence),
            ]
        )
        check(errors, mismatched_manifest_code == 1, "release readiness checker must reject mismatched source manifest versions")
        check(errors, "source manifests: fail" in mismatched_manifest_output, "release readiness checker must report source manifest failures")
        check(
            errors,
            f"Codex source version {release_version} does not match Claude source version {mismatched_version}" in mismatched_manifest_output,
            "release readiness checker must explain source manifest version mismatch",
        )

    with tempfile.TemporaryDirectory(prefix="arbor-release-readiness-invalid-source-manifest-shape-") as tmp:
        root = Path(tmp)
        source = root / "plugins" / "arbor"
        codex_cache_base = root / "codex-cache"
        claude_cache_base = root / "claude-cache"
        copy_plugin_to_cache(source)
        (source / ".codex-plugin" / "plugin.json").write_text('["not", "an", "object"]\n', encoding="utf-8")
        shutil.copytree(source, codex_cache_base / release_version)
        shutil.copytree(source, claude_cache_base / release_version)
        (root / "README.md").write_text("clean public README\n", encoding="utf-8")
        write_temp_marketplaces(root)
        evidence = root / "runtime-smoke.md"
        run_git(root, errors, "init")
        run_git(root, errors, "config", "user.email", "arbor@example.invalid")
        run_git(root, errors, "config", "user.name", "Arbor Check")
        evidence.write_text(complete_runtime_smoke_evidence(), encoding="utf-8")
        run_git(root, errors, "add", ".")
        run_git(root, errors, "commit", "-m", "invalid source manifest shape")
        head = run_git(root, errors, "rev-parse", "HEAD").strip()
        evidence.write_text(runtime_smoke_evidence_for_commit(head), encoding="utf-8")
        invalid_shape_code, invalid_shape_output = run_command_status(
            [
                sys.executable,
                str(script),
                "--skip-quality-gate",
                "--root",
                str(root),
                "--plugin-root",
                str(source),
                "--codex-cache-base",
                str(codex_cache_base),
                "--claude-cache-base",
                str(claude_cache_base),
                "--runtime-smoke-evidence",
                str(evidence),
            ]
        )
        check(errors, invalid_shape_code == 1, "release readiness checker must reject non-object source manifests")
        check(errors, "source manifests: fail" in invalid_shape_output, "release readiness checker must report non-object source manifest failures")
        check(errors, "expected JSON object" in invalid_shape_output, "release readiness checker must explain non-object source manifests")
        check(errors, "Traceback" not in invalid_shape_output, "release readiness checker must not traceback on non-object source manifests")

    with tempfile.TemporaryDirectory(prefix="arbor-release-readiness-dev-source-version-") as tmp:
        root = Path(tmp)
        source = root / "plugins" / "arbor"
        codex_cache_base = root / "codex-cache"
        claude_cache_base = root / "claude-cache"
        copy_plugin_to_cache(source)
        for manifest in (
            source / ".codex-plugin" / "plugin.json",
            source / ".claude-plugin" / "plugin.json",
        ):
            manifest_data = json.loads(manifest.read_text(encoding="utf-8-sig"))
            manifest_data["version"] = "dev"
            manifest.write_text(json.dumps(manifest_data, indent=2) + "\n", encoding="utf-8")
        shutil.copytree(source, codex_cache_base / "dev")
        shutil.copytree(source, claude_cache_base / "dev")
        (root / "README.md").write_text("clean public README\n", encoding="utf-8")
        write_temp_marketplaces(root)
        evidence = root / "runtime-smoke.md"
        run_git(root, errors, "init")
        run_git(root, errors, "config", "user.email", "arbor@example.invalid")
        run_git(root, errors, "config", "user.name", "Arbor Check")
        evidence.write_text(complete_runtime_smoke_evidence().replace(release_version, "dev"), encoding="utf-8")
        run_git(root, errors, "add", ".")
        run_git(root, errors, "commit", "-m", "dev source version")
        head = run_git(root, errors, "rev-parse", "HEAD").strip()
        evidence.write_text(runtime_smoke_evidence_for_commit(head).replace(release_version, "dev"), encoding="utf-8")
        dev_version_code, dev_version_output = run_command_status(
            [
                sys.executable,
                str(script),
                "--skip-quality-gate",
                "--root",
                str(root),
                "--plugin-root",
                str(source),
                "--codex-cache-base",
                str(codex_cache_base),
                "--claude-cache-base",
                str(claude_cache_base),
                "--runtime-smoke-evidence",
                str(evidence),
            ]
        )
        check(errors, dev_version_code == 1, "release readiness checker must reject non-release source manifest versions")
        check(errors, "source manifests: fail" in dev_version_output, "release readiness checker must report non-release source version failures")
        check(
            errors,
            "plugin source version must be a release version" in dev_version_output,
            "release readiness checker must explain non-release source manifest versions",
        )

    with tempfile.TemporaryDirectory(prefix="arbor-release-readiness-wrong-smoke-version-") as tmp:
        root = Path(tmp)
        source = root / "plugins" / "arbor"
        codex_cache_base = root / "codex-cache"
        claude_cache_base = root / "claude-cache"
        copy_plugin_to_cache(source)
        copy_plugin_to_cache(codex_cache_base / release_version)
        copy_plugin_to_cache(claude_cache_base / release_version)
        (root / "README.md").write_text("clean public README\n", encoding="utf-8")
        write_temp_marketplaces(root)
        evidence = root / "runtime-smoke-wrong-version.md"
        evidence.write_text(complete_runtime_smoke_evidence(), encoding="utf-8")
        run_git(root, errors, "init")
        run_git(root, errors, "config", "user.email", "arbor@example.invalid")
        run_git(root, errors, "config", "user.name", "Arbor Check")
        run_git(root, errors, "add", ".")
        run_git(root, errors, "commit", "-m", "clean release source")
        head = run_git(root, errors, "rev-parse", "HEAD").strip()
        evidence.write_text(runtime_smoke_evidence_for_commit(head).replace(release_version, "1.1.1"), encoding="utf-8")
        wrong_version_code, wrong_version_output = run_command_status(
            [
                sys.executable,
                str(script),
                "--skip-quality-gate",
                "--root",
                str(root),
                "--plugin-root",
                str(source),
                "--codex-cache-base",
                str(codex_cache_base),
                "--claude-cache-base",
                str(claude_cache_base),
                "--runtime-smoke-evidence",
                str(evidence),
            ]
        )
        check(errors, wrong_version_code == 1, "release readiness checker must reject runtime smoke evidence for the wrong source version")
        check(errors, "runtime smoke version: fail" in wrong_version_output, "release readiness checker must report runtime smoke version failures")
        check(
            errors,
            f"runtime smoke evidence Version 1.1.1 does not match plugin source version {release_version}" in wrong_version_output,
            "release readiness checker must explain source/evidence version mismatch",
        )

    with tempfile.TemporaryDirectory(prefix="arbor-release-readiness-dirty-published-") as tmp:
        repo = Path(tmp)
        source = repo / "plugins" / "arbor"
        codex_cache_base = repo / "codex-cache"
        claude_cache_base = repo / "claude-cache"
        copy_plugin_to_cache(source)
        copy_plugin_to_cache(codex_cache_base / release_version)
        copy_plugin_to_cache(claude_cache_base / release_version)
        (repo / "README.md").write_text("clean public README\n", encoding="utf-8")
        write_temp_marketplaces(repo)
        evidence = repo / "runtime-smoke.md"
        evidence.write_text(complete_runtime_smoke_evidence(), encoding="utf-8")
        run_git(repo, errors, "init")
        run_git(repo, errors, "config", "user.email", "arbor@example.invalid")
        run_git(repo, errors, "config", "user.name", "Arbor Check")
        run_git(repo, errors, "add", ".")
        run_git(repo, errors, "commit", "-m", "clean release source")
        head = run_git(repo, errors, "rev-parse", "HEAD").strip()
        evidence.write_text(runtime_smoke_evidence_for_commit(head), encoding="utf-8")
        (repo / "README.md").write_text("dirty public README\n", encoding="utf-8")

        dirty_code, dirty_output = run_command_status(
            [
                sys.executable,
                str(script),
                "--skip-quality-gate",
                "--root",
                str(repo),
                "--plugin-root",
                str(source),
                "--codex-cache-base",
                str(codex_cache_base),
                "--claude-cache-base",
                str(claude_cache_base),
                "--runtime-smoke-evidence",
                str(evidence),
            ]
        )
        check(errors, dirty_code == 1, "release readiness checker must fail when published source files are dirty")
        check(errors, "published source: fail" in dirty_output, "release readiness checker must report dirty published source")

    with tempfile.TemporaryDirectory(prefix="arbor-release-readiness-missing-published-") as tmp:
        repo = Path(tmp)
        source = repo / "plugins" / "arbor"
        codex_cache_base = repo / "codex-cache"
        claude_cache_base = repo / "claude-cache"
        copy_plugin_to_cache(source)
        copy_plugin_to_cache(codex_cache_base / release_version)
        copy_plugin_to_cache(claude_cache_base / release_version)
        (repo / "README.md").write_text("clean public README\n", encoding="utf-8")
        evidence = repo / "runtime-smoke.md"
        evidence.write_text(complete_runtime_smoke_evidence(), encoding="utf-8")
        run_git(repo, errors, "init")
        run_git(repo, errors, "config", "user.email", "arbor@example.invalid")
        run_git(repo, errors, "config", "user.name", "Arbor Check")
        run_git(repo, errors, "add", ".")
        run_git(repo, errors, "commit", "-m", "missing marketplace release source")
        head = run_git(repo, errors, "rev-parse", "HEAD").strip()
        evidence.write_text(runtime_smoke_evidence_for_commit(head), encoding="utf-8")

        missing_code, missing_output = run_command_status(
            [
                sys.executable,
                str(script),
                "--skip-quality-gate",
                "--root",
                str(repo),
                "--plugin-root",
                str(source),
                "--codex-cache-base",
                str(codex_cache_base),
                "--claude-cache-base",
                str(claude_cache_base),
                "--runtime-smoke-evidence",
                str(evidence),
            ]
        )
        check(errors, missing_code == 1, "release readiness checker must fail when published source files are missing")
        check(errors, "missing published source" in missing_output, "release readiness checker must explain missing published source")


def write_install_state_source(root: Path) -> None:
    (root / ".codex-plugin").mkdir(parents=True)
    (root / ".claude-plugin").mkdir(parents=True)
    (root / "hooks").mkdir()
    (root / "skills" / "arbor").mkdir(parents=True)
    manifest = '{"name": "arbor", "version": "2.0.0"}\n'
    (root / ".codex-plugin" / "plugin.json").write_text(manifest, encoding="utf-8")
    (root / ".claude-plugin" / "plugin.json").write_text(manifest, encoding="utf-8")
    (root / "hooks" / "session-start").write_text("#!/usr/bin/env python3\nprint('session')\n", encoding="utf-8")
    (root / "hooks" / "stop-memory-hygiene").write_text("#!/usr/bin/env python3\nprint('stop')\n", encoding="utf-8")
    (root / "skills" / "arbor" / "SKILL.md").write_text("---\nname: arbor\n---\n# Arbor\n", encoding="utf-8")


def validate_install_state_checker(errors: list[str]) -> None:
    module_path = SCRIPTS_ROOT / "check_install_state.py"
    if not module_path.is_file():
        add_error(errors, "install-state checker must be published")
        return
    spec = importlib.util.spec_from_file_location("arbor_check_install_state_probe", module_path)
    if spec is None or spec.loader is None:
        add_error(errors, "could not load check_install_state.py for install-state validation")
        return
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    original_subprocess_run = module.subprocess.run

    def raise_install_state_timeout(command: list[str], *_args: Any, **_kwargs: Any) -> Any:
        if command and command[0] == "git":
            raise subprocess.TimeoutExpired(command, timeout=0.1)
        return original_subprocess_run(command, *_args, **_kwargs)

    module.subprocess.run = raise_install_state_timeout
    try:
        try:
            timed_out_root = module.git_root_for(REPO_ROOT)
        except subprocess.TimeoutExpired as exc:
            add_error(errors, f"install-state git root timeouts must not propagate: {exc}")
            timed_out_root = object()
    finally:
        module.subprocess.run = original_subprocess_run
    check(errors, timed_out_root is None, "install-state git root timeouts must return no git root")

    def raise_install_state_root_launch(command: list[str], *_args: Any, **_kwargs: Any) -> Any:
        if command and command[0] == "git":
            raise OSError("simulated install-state git root launch failure")
        return original_subprocess_run(command, *_args, **_kwargs)

    module.subprocess.run = raise_install_state_root_launch
    try:
        try:
            launch_failed_root = module.git_root_for(REPO_ROOT)
        except OSError as exc:
            add_error(errors, f"install-state git root launch failures must not propagate: {exc}")
            launch_failed_root = object()
    finally:
        module.subprocess.run = original_subprocess_run
    check(errors, launch_failed_root is None, "install-state git root launch failures must return no git root")

    class FakeGitProc:
        def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    root_for_status = REPO_ROOT.resolve()
    source_for_status = PLUGIN_ROOT.resolve()

    def raise_install_state_status_timeout(command: list[str], *_args: Any, **_kwargs: Any) -> Any:
        if command and command[0] == "git" and "rev-parse" in command:
            return FakeGitProc(0, str(root_for_status))
        if command and command[0] == "git" and "status" in command:
            raise subprocess.TimeoutExpired(command, timeout=0.1)
        return original_subprocess_run(command, *_args, **_kwargs)

    module.subprocess.run = raise_install_state_status_timeout
    try:
        try:
            module.git_source_dirty(source_for_status)
        except subprocess.TimeoutExpired as exc:
            add_error(errors, f"install-state git status timeouts must not propagate: {exc}")
        except RuntimeError as exc:
            check(errors, "timed out" in str(exc), "install-state git status timeout errors must explain the timeout")
        else:
            add_error(errors, "install-state git status timeouts must fail dirty-source inspection")
    finally:
        module.subprocess.run = original_subprocess_run

    def raise_install_state_status_launch(command: list[str], *_args: Any, **_kwargs: Any) -> Any:
        if command and command[0] == "git" and "rev-parse" in command:
            return FakeGitProc(0, str(root_for_status))
        if command and command[0] == "git" and "status" in command:
            raise OSError("simulated install-state git status launch failure")
        return original_subprocess_run(command, *_args, **_kwargs)

    module.subprocess.run = raise_install_state_status_launch
    try:
        try:
            module.git_source_dirty(source_for_status)
        except OSError as exc:
            add_error(errors, f"install-state git status launch failures must not propagate: {exc}")
        except RuntimeError as exc:
            check(errors, "failed to start" in str(exc), "install-state git status launch failures must explain the launch error")
        else:
            add_error(errors, "install-state git status launch failures must fail dirty-source inspection")
    finally:
        module.subprocess.run = original_subprocess_run

    with tempfile.TemporaryDirectory(prefix="arbor-install-state-check-") as tmp:
        root = Path(tmp)
        source = root / "source"
        source.mkdir()
        write_install_state_source(source)
        (source / ".codex-plugin" / "plugin.json").write_text('{"name": "arbor", "version": "2.0.0"}\n', encoding="utf-8-sig")
        (source / ".claude-plugin" / "plugin.json").write_text('{"name": "arbor", "version": "2.0.0"}\n', encoding="utf-8-sig")
        codex_base = root / "codex-cache"
        missing = module.runtime_cache_state(source, codex_base, "codex")
        check(errors, missing.status == "missing", "install-state checker must report missing version caches")
        check(errors, missing.source_version == "2.0.0", "install-state checker must accept UTF-8 BOM plugin manifests")

        shutil.copytree(source, codex_base / "dev")
        dev_cache_only = module.runtime_cache_state(source, codex_base, "codex")
        check(errors, dev_cache_only.status == "missing", "install-state checker must ignore non-release caches when expected cache is missing")
        check(
            errors,
            dev_cache_only.selected_cache_version is None,
            "install-state selected cache version must mirror wrappers and ignore non-release cache directories",
        )

        cache = codex_base / "2.0.0"
        shutil.copytree(source, cache)
        ready = module.runtime_cache_state(source, codex_base, "codex")
        check(errors, ready.status == "ready", "install-state checker must report matching caches as ready")
        check(errors, ready.selected_cache_version == "2.0.0", "install-state checker must select release caches over ignored dev caches")

        (source / "skills" / "arbor" / "SKILL.md").write_text("---\nname: arbor\n---\n# Arbor\n", encoding="utf-8")
        (cache / "skills" / "arbor" / "SKILL.md").write_bytes(b"---\r\nname: arbor\r\n---\r\n# Arbor\r\n")
        line_ending_ready = module.runtime_cache_state(source, codex_base, "codex")
        check(errors, line_ending_ready.status == "ready", "install-state checker must ignore CRLF/LF-only text differences")

        claude_install_marker = cache / ".in_use" / "session"
        claude_install_marker.parent.mkdir()
        claude_install_marker.write_text("official installer marker\n", encoding="utf-8")
        in_use_ready = module.runtime_cache_state(source, codex_base, "codex")
        check(errors, in_use_ready.status == "ready", "install-state checker must ignore Claude Code .in_use installer state")
        shutil.rmtree(cache / ".in_use")

        original_digest_tree = module.digest_tree

        def raise_source_digest_failure(root_path: Path) -> str:
            if Path(root_path).resolve() == source.resolve():
                raise OSError("simulated source digest read failure")
            return original_digest_tree(root_path)

        module.digest_tree = raise_source_digest_failure
        try:
            try:
                source_digest_failure = module.runtime_cache_state(source, codex_base, "codex")
            except OSError as exc:
                add_error(errors, f"install-state source digest failures must not propagate: {exc}")
                source_digest_failure = None
            if source_digest_failure is not None:
                check(errors, source_digest_failure.status == "drift", "install-state checker must flag source digest failures as drift")
                check(
                    errors,
                    any("could not digest source tree" in issue for issue in source_digest_failure.issues),
                    "install-state checker must explain source digest failures",
                )
        finally:
            module.digest_tree = original_digest_tree

        def raise_cache_digest_failure(root_path: Path) -> str:
            if Path(root_path).resolve() == cache.resolve():
                raise OSError("simulated cache digest read failure")
            return original_digest_tree(root_path)

        module.digest_tree = raise_cache_digest_failure
        try:
            try:
                cache_digest_failure = module.runtime_cache_state(source, codex_base, "codex")
            except OSError as exc:
                add_error(errors, f"install-state cache digest failures must not propagate: {exc}")
                cache_digest_failure = None
            if cache_digest_failure is not None:
                check(errors, cache_digest_failure.status == "drift", "install-state checker must flag cache digest failures as drift")
                check(
                    errors,
                    any("could not digest expected cache" in issue for issue in cache_digest_failure.issues),
                    "install-state checker must explain cache digest failures",
                )
        finally:
            module.digest_tree = original_digest_tree

        incomplete_newer_cache = codex_base / "2.1.0"
        write_broken_cache_adapter(incomplete_newer_cache, "session-start")
        incomplete_newer_ready = module.runtime_cache_state(source, codex_base, "codex")
        check(
            errors,
            incomplete_newer_ready.status == "ready",
            "install-state checker must ignore incomplete higher-version release caches",
        )
        check(
            errors,
            incomplete_newer_ready.selected_cache_version == "2.0.0",
            "install-state selected cache version must mirror wrappers and skip incomplete release caches",
        )
        shutil.rmtree(incomplete_newer_cache)

        claude_base = root / "claude-cache"
        codex_only_code, codex_only_output = run_command_status(
            [
                sys.executable,
                str(module_path),
                "--source",
                str(source),
                "--codex-cache-base",
                str(codex_base),
                "--claude-cache-base",
                str(claude_base),
                "--runtime",
                "codex",
                "--strict",
                "--json",
            ]
        )
        check(errors, codex_only_code == 0, "install-state strict mode must support Codex-only release checks")
        if codex_only_code == 0:
            codex_only = json.loads(codex_only_output)
            check(errors, sorted(codex_only.get("runtimes", {}).keys()) == ["codex"], "install-state runtime filter must emit only selected Codex state")

        claude_only_missing_code, _claude_only_missing_output = run_command_status(
            [
                sys.executable,
                str(module_path),
                "--source",
                str(source),
                "--codex-cache-base",
                str(codex_base),
                "--claude-cache-base",
                str(claude_base),
                "--runtime",
                "claude",
                "--strict",
            ]
        )
        check(errors, claude_only_missing_code == 1, "install-state strict mode must fail when the selected Claude cache is missing")

        shutil.copytree(source, claude_base / "2.0.0")
        strict_ready_code, _strict_ready_output = run_command_status(
            [
                sys.executable,
                str(module_path),
                "--source",
                str(source),
                "--codex-cache-base",
                str(codex_base),
                "--claude-cache-base",
                str(claude_base),
                "--strict",
            ]
        )
        check(errors, strict_ready_code == 0, "install-state strict mode must pass when all runtime caches are ready")

        newer_cache = codex_base / "2.1.0"
        shutil.copytree(source, newer_cache)
        selected_drift = module.runtime_cache_state(source, codex_base, "codex")
        check(errors, selected_drift.status == "drift", "install-state checker must flag newer cache versions selected by wrappers")
        check(errors, any("newest release cache version is 2.1.0" in issue for issue in selected_drift.issues), "install-state checker must explain selected cache version drift")
        strict_drift_code, strict_drift_output = run_command_status(
            [
                sys.executable,
                str(module_path),
                "--source",
                str(source),
                "--codex-cache-base",
                str(codex_base),
                "--claude-cache-base",
                str(claude_base),
                "--strict",
            ]
        )
        check(errors, strict_drift_code == 1, "install-state strict mode must fail when cache drift is present")
        check(errors, "install-state strict check failed" in strict_drift_output, "install-state strict mode must explain failure")
        shutil.rmtree(newer_cache)

        (cache / "hooks" / "hooks.json").write_text('{"legacy": true}\n', encoding="utf-8")
        legacy = module.runtime_cache_state(source, codex_base, "codex")
        check(errors, legacy.status == "drift", "install-state checker must flag legacy plugin-level hook manifests")
        check(errors, any("legacy plugin-level hooks/hooks.json" in issue for issue in legacy.issues), "install-state checker must explain legacy hook drift")
        (cache / "hooks" / "hooks.json").unlink()

        (cache / "__pycache__").mkdir()
        (cache / "__pycache__" / "stale.pyc").write_bytes(b"stale")
        transient = module.runtime_cache_state(source, codex_base, "codex")
        check(errors, transient.status == "drift", "install-state checker must flag transient cache artifacts")
        check(errors, any("__pycache__" in issue or ".pyc" in issue for issue in transient.issues), "install-state checker must explain transient cache artifacts")
        shutil.rmtree(cache / "__pycache__")

        (cache / "skills" / "arbor" / "SKILL.md").write_text("stale\n", encoding="utf-8")
        drift = module.runtime_cache_state(source, codex_base, "codex")
        check(errors, drift.status == "drift", "install-state checker must flag content drift between source and cache")
        check(errors, any("content digest differs" in issue for issue in drift.issues), "install-state checker must explain content drift")

        output = run_command(
            [
                sys.executable,
                str(module_path),
                "--source",
                str(source),
                "--codex-cache-base",
                str(codex_base),
                "--claude-cache-base",
                str(root / "missing-claude-cache"),
                "--json",
            ],
            errors,
        )
        data = json.loads(output)
        check(errors, data.get("version") == "2.0.0", "install-state checker JSON must include source version")
        check(errors, data.get("runtimes", {}).get("codex", {}).get("status") == "drift", "install-state checker JSON must include runtime status")
        strict_missing_code, _strict_missing_output = run_command_status(
            [
                sys.executable,
                str(module_path),
                "--source",
                str(source),
                "--codex-cache-base",
                str(codex_base),
                "--claude-cache-base",
                str(root / "missing-claude-cache"),
                "--strict",
            ]
        )
        check(errors, strict_missing_code == 1, "install-state strict mode must fail when a runtime cache is missing")

    with tempfile.TemporaryDirectory(prefix="arbor-install-state-dirty-source-") as tmp:
        root = Path(tmp)
        repo = root / "repo"
        source = repo / "plugins" / "arbor"
        source.mkdir(parents=True)
        write_install_state_source(source)
        run_git(repo, errors, "init")
        run_git(repo, errors, "config", "user.email", "arbor@example.invalid")
        run_git(repo, errors, "config", "user.name", "Arbor Check")
        run_git(repo, errors, "add", ".")
        run_git(repo, errors, "commit", "-m", "initial")

        codex_base = root / "codex-cache"
        claude_base = root / "claude-cache"
        shutil.copytree(source, codex_base / "2.0.0")
        shutil.copytree(source, claude_base / "2.0.0")
        strict_clean_code, _strict_clean_output = run_command_status(
            [
                sys.executable,
                str(module_path),
                "--source",
                str(source),
                "--codex-cache-base",
                str(codex_base),
                "--claude-cache-base",
                str(claude_base),
                "--strict",
            ]
        )
        check(errors, strict_clean_code == 0, "install-state strict mode must pass for clean source and matching caches")

        (source / "skills" / "arbor" / "SKILL.md").write_text("---\nname: arbor\n---\n# Dirty Arbor\n", encoding="utf-8")
        shutil.rmtree(codex_base / "2.0.0")
        shutil.rmtree(claude_base / "2.0.0")
        shutil.copytree(source, codex_base / "2.0.0")
        shutil.copytree(source, claude_base / "2.0.0")
        strict_dirty_code, strict_dirty_output = run_command_status(
            [
                sys.executable,
                str(module_path),
                "--source",
                str(source),
                "--codex-cache-base",
                str(codex_base),
                "--claude-cache-base",
                str(claude_base),
                "--strict",
            ]
        )
        check(errors, strict_dirty_code == 1, "install-state strict mode must fail for dirty source even when caches match")
        check(errors, "dirty plugin source" in strict_dirty_output, "install-state strict mode must explain dirty source failures")

        strict_dirty_dev_code, _strict_dirty_dev_output = run_command_status(
            [
                sys.executable,
                str(module_path),
                "--source",
                str(source),
                "--codex-cache-base",
                str(codex_base),
                "--claude-cache-base",
                str(claude_base),
                "--strict",
                "--allow-dirty-source",
            ]
        )
        check(errors, strict_dirty_dev_code == 0, "install-state strict mode must allow an explicit dirty-source development override")

    with tempfile.TemporaryDirectory(prefix="arbor-install-state-dev-version-") as tmp:
        root = Path(tmp)
        repo = root / "repo"
        source = repo / "plugins" / "arbor"
        source.mkdir(parents=True)
        write_install_state_source(source)
        dev_manifest = '{"name": "arbor", "version": "dev"}\n'
        (source / ".codex-plugin" / "plugin.json").write_text(dev_manifest, encoding="utf-8")
        (source / ".claude-plugin" / "plugin.json").write_text(dev_manifest, encoding="utf-8")
        run_git(repo, errors, "init")
        run_git(repo, errors, "config", "user.email", "arbor@example.invalid")
        run_git(repo, errors, "config", "user.name", "Arbor Check")
        run_git(repo, errors, "add", ".")
        run_git(repo, errors, "commit", "-m", "dev manifest source")

        codex_base = root / "codex-cache"
        claude_base = root / "claude-cache"
        shutil.copytree(source, codex_base / "dev")
        shutil.copytree(source, claude_base / "dev")
        dev_non_strict_code, dev_non_strict_output = run_command_status(
            [
                sys.executable,
                str(module_path),
                "--source",
                str(source),
                "--codex-cache-base",
                str(codex_base),
                "--claude-cache-base",
                str(claude_base),
            ]
        )
        check(errors, dev_non_strict_code == 0, "install-state non-strict mode must still diagnose non-release versions")
        check(errors, "Version: dev" in dev_non_strict_output, "install-state non-strict output must show the diagnosed non-release version")

        dev_strict_code, dev_strict_output = run_command_status(
            [
                sys.executable,
                str(module_path),
                "--source",
                str(source),
                "--codex-cache-base",
                str(codex_base),
                "--claude-cache-base",
                str(claude_base),
                "--strict",
            ]
        )
        check(errors, dev_strict_code == 1, "install-state strict mode must reject non-release source manifest versions")
        check(
            errors,
            "source manifest version must be a release version" in dev_strict_output,
            "install-state strict mode must explain non-release source manifest versions",
        )


def validate_context_boundary_script(errors: list[str]) -> None:
    run_command([sys.executable, str(SCRIPTS_ROOT / "check_context_boundary.py")], errors)
    script = SCRIPTS_ROOT / "check_context_boundary.py"
    spec = importlib.util.spec_from_file_location("arbor_check_context_boundary_probe", script)
    if spec is None or spec.loader is None:
        add_error(errors, "could not load check_context_boundary.py for encoding validation")
        return
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    published_files = module.published_text_files()
    check(
        errors,
        SKILLS_ROOT / "arbor" / "agents" / "openai.yaml" in published_files,
        "context boundary check must scan the published Arbor agent yaml",
    )

    with tempfile.TemporaryDirectory(prefix="arbor-context-boundary-encoding-") as tmp:
        invalid_text = Path(tmp) / "README.md"
        invalid_text.write_bytes(b"\xffnot-utf8")
        failures: list[str] = []
        try:
            text = module.load_text(invalid_text, failures)
        except TypeError:
            add_error(errors, "context boundary load_text must accept a failures list for clean encoding errors")
            return
        except UnicodeError as exc:
            add_error(errors, f"context boundary check must report invalid UTF-8 without traceback: {exc}")
            return
        check(errors, text == "", "context boundary check must not fall back to platform-default text decoding")
        check(errors, any("UTF-8" in failure for failure in failures), "context boundary check must explain invalid UTF-8 text")

    with tempfile.TemporaryDirectory(prefix="arbor-context-boundary-json-shape-") as tmp:
        non_object_json = Path(tmp) / "plugin.json"
        non_object_json.write_text("[]\n", encoding="utf-8")
        failures = []
        if not hasattr(module, "load_json_object"):
            add_error(errors, "context boundary check must expose JSON-object validation for published JSON surfaces")
        else:
            try:
                parsed = module.load_json_object(non_object_json, failures)
            except Exception as exc:
                add_error(errors, f"context boundary check must reject non-object JSON without traceback: {exc}")
                parsed = {}
            check(errors, parsed == {}, "context boundary check must not accept non-object published JSON")
            check(
                errors,
                any("JSON object" in failure for failure in failures),
                "context boundary check must explain non-object published JSON",
            )

    with tempfile.TemporaryDirectory(prefix="arbor-context-boundary-skill-inventory-") as tmp:
        skills_root = Path(tmp) / "skills"
        (skills_root / "arbor").mkdir(parents=True)
        (skills_root / "arbor" / "SKILL.md").write_text("---\nname: arbor\n---\n", encoding="utf-8")
        (skills_root / "extra").mkdir()
        (skills_root / "extra" / "SKILL.md").write_text("---\nname: extra\n---\n", encoding="utf-8")
        failures = []
        if not hasattr(module, "validate_skill_inventory"):
            add_error(errors, "context boundary check must validate the exact published skill inventory")
        else:
            try:
                module.validate_skill_inventory(skills_root, failures)
            except Exception as exc:
                add_error(errors, f"context boundary skill inventory validation must not traceback: {exc}")
            check(
                errors,
                any("published skills must be exactly ['arbor']" in failure for failure in failures),
                "context boundary check must reject extra published skills",
            )


def validate_hook_probe_payloads(errors: list[str]) -> None:
    env = os.environ.copy()
    env["ARBOR_PLUGIN_ROOT"] = str(PLUGIN_ROOT)
    for adapter_name in ("session-start", "stop-memory-hygiene"):
        adapter = PLUGIN_ROOT / "hooks" / adapter_name
        check(errors, adapter.is_file(), f"missing hook adapter: hooks/{adapter_name}")
        for payload in ("", "null", "[]", '"probe"', "{not-json"):
            run_command([sys.executable, str(adapter)], errors, input_text=payload, env=env)


def hook_commands(data: dict[str, Any]) -> list[str]:
    commands: list[str] = []
    hooks = data.get("hooks", {})
    if not isinstance(hooks, dict):
        return commands
    for groups in hooks.values():
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict):
                continue
            handlers = group.get("hooks", [])
            if not isinstance(handlers, list):
                continue
            for handler in handlers:
                if isinstance(handler, dict) and isinstance(handler.get("command"), str):
                    commands.append(handler["command"])
    return commands


def normalized_hook_marker_count(commands: list[str], marker: str) -> int:
    return sum(1 for command in commands if marker in command.replace("\\", "/"))


def validate_project_hook_registration(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="arbor-adapter-check-") as tmp:
        root = Path(tmp)
        (root / "AGENTS.md").write_text(
            "# Agent Guide\n\n"
            "## Project Goal\n\nAdapter smoke project.\n\n"
            "## Project Constraints\n\n- Keep checks deterministic.\n\n"
            "## Project Map\n\n- `README.md`: overview.\n",
            encoding="utf-8",
        )
        (root / ".arbor").mkdir()
        (root / ".arbor" / "memory.md").write_text("# Session Memory\n\n## In-flight\n\n- None.\n", encoding="utf-8")
        run_command(
            [
                sys.executable,
                str(SCRIPTS_ROOT / "register_project_hooks.py"),
                "--root",
                str(root),
                "--runtime",
                "both",
            ],
            errors,
        )
        codex_hooks = load_json(root / ".codex" / "hooks.json", errors)
        claude_settings = load_json(root / ".claude" / "settings.json", errors)
        codex_text = json.dumps(codex_hooks)
        claude_text = json.dumps(claude_settings)
        codex_commands = hook_commands(codex_hooks)
        claude_commands = hook_commands(claude_settings)
        normalized_codex_commands = [command.replace("\\", "/") for command in codex_commands]
        is_windows = os.name == "nt"
        registering_python = str(Path(sys.executable).expanduser().resolve())
        codex_command_suffix = ".cmd" if is_windows else ""
        check(
            errors,
            any(f".codex/hooks/arbor-session-start{codex_command_suffix}" in command for command in normalized_codex_commands),
            "Codex SessionStart wrapper command missing",
        )
        check(
            errors,
            any(f".codex/hooks/arbor-stop-memory-hygiene{codex_command_suffix}" in command for command in normalized_codex_commands),
            "Codex Stop wrapper command missing",
        )
        check(errors, ".claude/hooks/arbor-session-start" in claude_text, "Claude SessionStart wrapper command missing")
        check(errors, ".claude/hooks/arbor-stop-memory-hygiene" in claude_text, "Claude Stop wrapper command missing")
        if is_windows:
            codex_launchers = [
                root / ".codex" / "hooks" / "arbor-session-start.cmd",
                root / ".codex" / "hooks" / "arbor-stop-memory-hygiene.cmd",
            ]
            check(
                errors,
                all(path.is_file() and registering_python in path.read_text(encoding="utf-8") for path in codex_launchers),
                "Codex Windows launchers must include the registering Python executable",
            )
        else:
            check(
                errors,
                all(".cmd" not in command for command in normalized_codex_commands),
                "POSIX Codex hook commands must not call Windows .cmd launchers",
            )
            check(
                errors,
                codex_commands and all(registering_python in command for command in codex_commands),
                "POSIX Codex hook commands must include the registering Python executable",
            )
        check(errors, claude_commands and all(registering_python in command for command in claude_commands), "Claude hook commands must include the registering Python executable")
        check(errors, all(not command.lower().startswith("python ") for command in codex_commands), "Codex hook commands must not use bare python")
        check(errors, all(not command.lower().startswith("python ") for command in claude_commands), "Claude hook commands must not use bare python")
        required_wrappers = [
            root / ".codex" / "hooks" / "arbor-session-start",
            root / ".codex" / "hooks" / "arbor-stop-memory-hygiene",
            root / ".claude" / "hooks" / "arbor-session-start",
            root / ".claude" / "hooks" / "arbor-stop-memory-hygiene",
        ]
        if is_windows:
            required_wrappers.extend(
                [
                    root / ".codex" / "hooks" / "arbor-session-start.cmd",
                    root / ".codex" / "hooks" / "arbor-stop-memory-hygiene.cmd",
                ]
            )
        for wrapper in required_wrappers:
            check(errors, wrapper.is_file(), f"missing project hook wrapper: {wrapper}")
        second_registration = run_command(
            [
                sys.executable,
                str(SCRIPTS_ROOT / "register_project_hooks.py"),
                "--root",
                str(root),
                "--runtime",
                "both",
            ],
            errors,
        )
        check(errors, "- chmod:" not in second_registration, "project hook registration must be idempotent without chmod churn")

        corrupt_codex_wrapper = root / ".codex" / "hooks" / "arbor-session-start"
        corrupt_claude_wrapper = root / ".claude" / "hooks" / "arbor-stop-memory-hygiene"
        corrupt_codex_wrapper.write_bytes(b"\xff\xfe\x00broken")
        corrupt_claude_wrapper.write_bytes(b"\xff\xfe\x00broken")
        repair_registration = run_command(
            [
                sys.executable,
                str(SCRIPTS_ROOT / "register_project_hooks.py"),
                "--root",
                str(root),
                "--runtime",
                "both",
            ],
            errors,
        )
        check(errors, "Traceback" not in repair_registration, "registration must not traceback on corrupt wrapper encoding")
        check(errors, "- updated:" in repair_registration, "registration must refresh corrupt wrapper text")
        try:
            repaired_codex_wrapper = corrupt_codex_wrapper.read_text(encoding="utf-8")
        except UnicodeError:
            repaired_codex_wrapper = ""
        try:
            repaired_claude_wrapper = corrupt_claude_wrapper.read_text(encoding="utf-8")
        except UnicodeError:
            repaired_claude_wrapper = ""
        check(errors, "Project-local Arbor Codex hook wrapper" in repaired_codex_wrapper, "registration must rewrite corrupt Codex wrapper content")
        check(errors, "Project-local Arbor Claude Code hook wrapper" in repaired_claude_wrapper, "registration must rewrite corrupt Claude wrapper content")

    with tempfile.TemporaryDirectory(prefix="arbor-stale-hook-cleanup-check-") as tmp:
        root = Path(tmp)
        (root / ".codex").mkdir()
        (root / ".claude").mkdir()
        (root / ".codex" / "hooks.json").write_text(
            json.dumps(
                {
                    "hooks": {
                        "SessionStart": [
                            {
                                "hooks": [
                                    {"type": "command", "command": 'python ".codex\\hooks\\arbor-session-start"'},
                                    {"type": "command", "command": "echo custom-codex-session"},
                                ]
                            }
                        ],
                        "Stop": [
                            {
                                "hooks": [
                                    {"type": "command", "command": 'python ".codex\\hooks\\arbor-stop-memory-hygiene"'}
                                ]
                            }
                        ],
                    }
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (root / ".claude" / "settings.json").write_text(
            json.dumps(
                {
                    "hooks": {
                        "SessionStart": [
                            {
                                "hooks": [
                                    {"type": "command", "command": 'python ".claude\\hooks\\arbor-session-start"'},
                                    {"type": "command", "command": "echo custom-claude-session"},
                                ]
                            }
                        ],
                        "Stop": [
                            {
                                "hooks": [
                                    {"type": "command", "command": 'python ".claude\\hooks\\arbor-stop-memory-hygiene"'}
                                ]
                            }
                        ],
                    }
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        run_command(
            [
                sys.executable,
                str(SCRIPTS_ROOT / "register_project_hooks.py"),
                "--root",
                str(root),
                "--runtime",
                "both",
            ],
            errors,
        )
        codex_commands = hook_commands(load_json(root / ".codex" / "hooks.json", errors))
        claude_commands = hook_commands(load_json(root / ".claude" / "settings.json", errors))
        check(errors, "echo custom-codex-session" in codex_commands, "Codex registration must preserve non-Arbor hooks")
        check(errors, "echo custom-claude-session" in claude_commands, "Claude registration must preserve non-Arbor hooks")
        check(
            errors,
            normalized_hook_marker_count(codex_commands, ".codex/hooks/arbor-session-start") == 1,
            "Codex registration must replace stale backslash SessionStart commands instead of duplicating them",
        )
        check(
            errors,
            normalized_hook_marker_count(codex_commands, ".codex/hooks/arbor-stop-memory-hygiene") == 1,
            "Codex registration must replace stale backslash Stop commands instead of duplicating them",
        )
        check(
            errors,
            normalized_hook_marker_count(claude_commands, ".claude/hooks/arbor-session-start") == 1,
            "Claude registration must replace stale backslash SessionStart commands instead of duplicating them",
        )
        check(
            errors,
            normalized_hook_marker_count(claude_commands, ".claude/hooks/arbor-stop-memory-hygiene") == 1,
            "Claude registration must replace stale backslash Stop commands instead of duplicating them",
        )

    with tempfile.TemporaryDirectory(prefix="arbor-bom-hook-config-check-") as tmp:
        root = Path(tmp)
        (root / ".codex").mkdir()
        (root / ".claude").mkdir()
        (root / ".codex" / "hooks.json").write_text('{"hooks": {}}\n', encoding="utf-8-sig")
        (root / ".claude" / "settings.json").write_text('{"hooks": {}}\n', encoding="utf-8-sig")
        output = run_command(
            [
                sys.executable,
                str(SCRIPTS_ROOT / "register_project_hooks.py"),
                "--root",
                str(root),
                "--runtime",
                "both",
            ],
            errors,
        )
        check(errors, "registered 2 Arbor Codex executable project hooks" in output, "registration must accept UTF-8 BOM Codex hook JSON")
        check(errors, "registered 2 Arbor Claude project hooks" in output, "registration must accept UTF-8 BOM Claude hook JSON")


def replace_hook_command(data: dict[str, Any], event: str, marker: str, replacement_command: str) -> bool:
    hooks = data.get("hooks", {})
    if not isinstance(hooks, dict):
        return False
    groups = hooks.get(event, [])
    if not isinstance(groups, list):
        return False
    for group in groups:
        if not isinstance(group, dict):
            continue
        handlers = group.get("hooks", [])
        if not isinstance(handlers, list):
            continue
        for handler in handlers:
            existing_command = str(handler.get("command", ""))
            if isinstance(handler, dict) and marker.replace("\\", "/") in existing_command.replace("\\", "/"):
                handler["command"] = replacement_command
                return True
    return False


def validate_hook_diagnosis_classification(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="arbor-diagnose-check-") as tmp:
        root = Path(tmp) / "project"
        root.mkdir()
        (root / "AGENTS.md").write_text(valid_agents_for_smoke(), encoding="utf-8")
        (root / ".arbor").mkdir()
        (root / ".arbor" / "memory.md").write_text("# Session Memory\n\n## In-flight\n\n- None.\n", encoding="utf-8")
        run_command(
            [
                sys.executable,
                str(SCRIPTS_ROOT / "register_project_hooks.py"),
                "--root",
                str(root),
                "--runtime",
                "both",
            ],
            errors,
        )

        codex_path = root / ".codex" / "hooks.json"
        codex_hooks = load_json(codex_path, errors)
        check(
            errors,
            replace_hook_command(codex_hooks, "SessionStart", ".codex/hooks/arbor-session-start", 'python ".codex/hooks/arbor-session-start"'),
            "diagnosis smoke must be able to replace Codex SessionStart command",
        )
        codex_path.write_text(json.dumps(codex_hooks, indent=2) + "\n", encoding="utf-8")

        claude_path = root / ".claude" / "settings.json"
        claude_settings = load_json(claude_path, errors)
        check(
            errors,
            replace_hook_command(claude_settings, "Stop", ".claude/hooks/arbor-stop-memory-hygiene", 'python ".claude/hooks/arbor-stop-memory-hygiene"'),
            "diagnosis smoke must be able to replace Claude Stop command",
        )
        claude_path.write_text(json.dumps(claude_settings, indent=2) + "\n", encoding="utf-8")

        fake_plugin = Path(tmp) / "plugin"
        copy_plugin_to_cache(fake_plugin)
        (fake_plugin / "hooks" / "hooks.json").write_text('{"legacy": true}\n', encoding="utf-8")

        output = run_command(
            [
                sys.executable,
                str(SCRIPTS_ROOT / "diagnose_project_hooks.py"),
                "--root",
                str(root),
                "--plugin-root",
                str(fake_plugin),
                "--json",
            ],
            errors,
        )
        try:
            diagnosis = json.loads(output)
        except json.JSONDecodeError as exc:
            add_error(errors, f"diagnose_project_hooks.py --json emitted invalid JSON: {exc}")
            return
        check(errors, diagnosis.get("codex", {}).get("status") == "executable-incomplete", "diagnosis must flag stale Codex project hook commands")
        check(errors, "session=stale" in diagnosis.get("codex", {}).get("detail", ""), "diagnosis must identify stale Codex SessionStart command")
        check(errors, diagnosis.get("claude_project", {}).get("status") == "project-Claude-incomplete", "diagnosis must flag stale Claude project hook commands")
        check(errors, "stop=stale" in diagnosis.get("claude_project", {}).get("detail", ""), "diagnosis must identify stale Claude Stop command")
        check(errors, diagnosis.get("shared_adapters", {}).get("status") == "shared-adapters-drift", "diagnosis must flag legacy plugin-level hook manifests")

        incomplete_plugin = Path(tmp) / "incomplete-plugin"
        copy_plugin_to_cache(incomplete_plugin)
        shutil.rmtree(incomplete_plugin / ".codex-plugin")
        incomplete_output = run_command(
            [
                sys.executable,
                str(SCRIPTS_ROOT / "diagnose_project_hooks.py"),
                "--root",
                str(root),
                "--plugin-root",
                str(incomplete_plugin),
                "--json",
            ],
            errors,
        )
        try:
            incomplete_diagnosis = json.loads(incomplete_output)
        except json.JSONDecodeError as exc:
            add_error(errors, f"diagnose_project_hooks.py incomplete plugin-root output was invalid JSON: {exc}")
            return
        incomplete_shared = incomplete_diagnosis.get("shared_adapters", {})
        check(
            errors,
            incomplete_shared.get("status") == "shared-adapters-incomplete",
            "diagnosis must reject incomplete plugin roots even when adapter files exist",
        )
        check(
            errors,
            "plugin root" in incomplete_shared.get("detail", ""),
            "diagnosis must explain incomplete plugin roots",
        )

    with tempfile.TemporaryDirectory(prefix="arbor-diagnose-stale-wrapper-check-") as tmp:
        root = Path(tmp) / "project"
        root.mkdir()
        (root / "AGENTS.md").write_text(valid_agents_for_smoke(), encoding="utf-8")
        (root / ".arbor").mkdir()
        (root / ".arbor" / "memory.md").write_text("# Session Memory\n\n## In-flight\n\n- None.\n", encoding="utf-8")
        run_command(
            [
                sys.executable,
                str(SCRIPTS_ROOT / "register_project_hooks.py"),
                "--root",
                str(root),
                "--runtime",
                "codex",
            ],
            errors,
        )
        (root / ".codex" / "hooks" / "arbor-session-start").write_text(
            "#!/usr/bin/env python3\nraise SystemExit(91)\n",
            encoding="utf-8",
        )
        output = run_command(
            [
                sys.executable,
                str(SCRIPTS_ROOT / "diagnose_project_hooks.py"),
                "--root",
                str(root),
                "--plugin-root",
                str(PLUGIN_ROOT),
                "--json",
            ],
            errors,
        )
        try:
            diagnosis = json.loads(output)
        except json.JSONDecodeError as exc:
            add_error(errors, f"diagnose_project_hooks.py stale wrapper output was invalid JSON: {exc}")
            return
        check(errors, diagnosis.get("codex", {}).get("status") == "executable-incomplete", "diagnosis must flag stale Codex project wrapper content")
        check(errors, "wrappers session=stale" in diagnosis.get("codex", {}).get("detail", ""), "diagnosis must identify stale Codex wrapper content")

    with tempfile.TemporaryDirectory(prefix="arbor-diagnose-invalid-wrapper-encoding-check-") as tmp:
        root = Path(tmp) / "project"
        root.mkdir()
        (root / "AGENTS.md").write_text(valid_agents_for_smoke(), encoding="utf-8")
        (root / ".arbor").mkdir()
        (root / ".arbor" / "memory.md").write_text("# Session Memory\n\n## In-flight\n\n- None.\n", encoding="utf-8")
        run_command(
            [
                sys.executable,
                str(SCRIPTS_ROOT / "register_project_hooks.py"),
                "--root",
                str(root),
                "--runtime",
                "codex",
            ],
            errors,
        )
        (root / ".codex" / "hooks" / "arbor-session-start").write_bytes(b"\xff\xfe\x00\xff")
        output = run_command(
            [
                sys.executable,
                str(SCRIPTS_ROOT / "diagnose_project_hooks.py"),
                "--root",
                str(root),
                "--plugin-root",
                str(PLUGIN_ROOT),
                "--json",
            ],
            errors,
        )
        try:
            diagnosis = json.loads(output)
        except json.JSONDecodeError as exc:
            add_error(errors, f"diagnose_project_hooks.py invalid-encoding wrapper output was invalid JSON: {exc}")
            return
        check(errors, diagnosis.get("codex", {}).get("status") == "executable-incomplete", "diagnosis must flag invalid-encoding Codex wrapper content")
        check(errors, "wrappers session=stale" in diagnosis.get("codex", {}).get("detail", ""), "diagnosis must classify invalid-encoding wrapper content as stale")

    with tempfile.TemporaryDirectory(prefix="arbor-diagnose-invalid-config-encoding-check-") as tmp:
        root = Path(tmp) / "project"
        root.mkdir()
        (root / "AGENTS.md").write_text(valid_agents_for_smoke(), encoding="utf-8")
        (root / ".arbor").mkdir()
        (root / ".arbor" / "memory.md").write_text("# Session Memory\n\n## In-flight\n\n- None.\n", encoding="utf-8")
        run_command(
            [
                sys.executable,
                str(SCRIPTS_ROOT / "register_project_hooks.py"),
                "--root",
                str(root),
                "--runtime",
                "codex",
            ],
            errors,
        )
        (root / ".codex" / "hooks.json").write_bytes(b"\xff\xfe\x00\xff")
        output = run_command(
            [
                sys.executable,
                str(SCRIPTS_ROOT / "diagnose_project_hooks.py"),
                "--root",
                str(root),
                "--plugin-root",
                str(PLUGIN_ROOT),
                "--json",
            ],
            errors,
        )
        try:
            diagnosis = json.loads(output)
        except json.JSONDecodeError as exc:
            add_error(errors, f"diagnose_project_hooks.py invalid-encoding config output was invalid JSON: {exc}")
            return
        check(errors, diagnosis.get("codex", {}).get("status") == "invalid", "diagnosis must flag invalid-encoding Codex hook config")
        codex_detail = diagnosis.get("codex", {}).get("detail", "")
        check(errors, "invalid_encoding" in codex_detail, "diagnosis must explain invalid hook config encoding")
        check(errors, "Traceback" not in output, "diagnosis must not leak tracebacks for invalid hook config encoding")

    with tempfile.TemporaryDirectory(prefix="arbor-diagnose-crlf-wrapper-check-") as tmp:
        root = Path(tmp) / "project"
        root.mkdir()
        (root / "AGENTS.md").write_text(valid_agents_for_smoke(), encoding="utf-8")
        (root / ".arbor").mkdir()
        (root / ".arbor" / "memory.md").write_text("# Session Memory\n\n## In-flight\n\n- None.\n", encoding="utf-8")
        run_command(
            [
                sys.executable,
                str(SCRIPTS_ROOT / "register_project_hooks.py"),
                "--root",
                str(root),
                "--runtime",
                "codex",
            ],
            errors,
        )
        wrapper_path = root / ".codex" / "hooks" / "arbor-session-start"
        wrapper_text = wrapper_path.read_text(encoding="utf-8")
        wrapper_path.write_bytes(wrapper_text.replace("\n", "\r\n").encode("utf-8"))
        output = run_command(
            [
                sys.executable,
                str(SCRIPTS_ROOT / "diagnose_project_hooks.py"),
                "--root",
                str(root),
                "--plugin-root",
                str(PLUGIN_ROOT),
                "--json",
            ],
            errors,
        )
        try:
            diagnosis = json.loads(output)
        except json.JSONDecodeError as exc:
            add_error(errors, f"diagnose_project_hooks.py CRLF wrapper output was invalid JSON: {exc}")
            return
        check(errors, diagnosis.get("codex", {}).get("status") == "executable-untrusted", "diagnosis must tolerate CRLF-only wrapper content differences")

    with tempfile.TemporaryDirectory(prefix="arbor-diagnose-adapter-timeout-check-") as tmp:
        root = Path(tmp) / "project"
        root.mkdir()
        (root / "AGENTS.md").write_text(valid_agents_for_smoke(), encoding="utf-8")
        (root / ".arbor").mkdir()
        (root / ".arbor" / "memory.md").write_text("# Session Memory\n\n## In-flight\n\n- None.\n", encoding="utf-8")
        fake_plugin = Path(tmp) / "plugin"
        copy_plugin_to_cache(fake_plugin)
        write_hanging_cache_adapter(fake_plugin, "session-start")
        timeout_env = os.environ.copy()
        timeout_env["ARBOR_HOOK_ADAPTER_PROBE_TIMEOUT_SECONDS"] = "0.2"
        output = run_command(
            [
                sys.executable,
                str(SCRIPTS_ROOT / "diagnose_project_hooks.py"),
                "--root",
                str(root),
                "--plugin-root",
                str(fake_plugin),
                "--json",
            ],
            errors,
            env=timeout_env,
            timeout_seconds=1.0,
        )
        try:
            diagnosis = json.loads(output)
        except json.JSONDecodeError as exc:
            add_error(errors, f"diagnose_project_hooks.py hanging adapter output was invalid JSON: {exc}")
            return
        shared = diagnosis.get("shared_adapters", {})
        check(errors, shared.get("status") == "shared-adapters-probe-failed", "diagnosis must flag hanging shared adapter probes")
        check(errors, "timed out" in shared.get("detail", ""), "diagnosis must explain shared adapter probe timeouts")

    module_path = SCRIPTS_ROOT / "diagnose_project_hooks.py"
    spec = importlib.util.spec_from_file_location("arbor_diagnose_project_hooks_probe_failure", module_path)
    if spec is None or spec.loader is None:
        add_error(errors, "could not load diagnose_project_hooks.py for adapter launch failure validation")
        return
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    original_subprocess_run = module.subprocess.run

    def raise_adapter_oserror(_command: list[str], *_args: Any, **_kwargs: Any) -> Any:
        raise OSError("simulated adapter probe launch failure")

    with tempfile.TemporaryDirectory(prefix="arbor-diagnose-adapter-launch-error-check-") as tmp:
        root = Path(tmp)
        plugin = root / "plugin"
        copy_plugin_to_cache(plugin)
        module.subprocess.run = raise_adapter_oserror
        try:
            try:
                probe_state = module.adapter_probe_state(
                    plugin,
                    plugin / "hooks" / "session-start",
                    plugin / "hooks" / "stop-memory-hygiene",
                )
            except OSError as exc:
                add_error(errors, f"shared adapter probe launch failures must not propagate: {exc}")
                probe_state = ""
        finally:
            module.subprocess.run = original_subprocess_run
        check(errors, "failed to start" in probe_state, "shared adapter probe launch failures must be reported")
        check(errors, "simulated adapter probe launch failure" in probe_state, "shared adapter probe launch failures must explain the launch error")


def run_project_wrapper(
    wrapper: Path,
    payload: dict[str, Any],
    errors: list[str],
    env: dict[str, str],
    *,
    timeout_seconds: float | None = None,
) -> str:
    try:
        proc = subprocess.run(
            [sys.executable, str(wrapper)],
            input=json.dumps(payload),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=bytecode_suppressed_env(env),
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        add_error(errors, f"project hook wrapper timed out: {wrapper}: {output.strip()}")
        return output
    if proc.returncode != 0:
        add_error(errors, f"project hook wrapper exited {proc.returncode}: {wrapper}: {proc.stdout.strip()}")
    return proc.stdout


def copy_plugin_to_cache(cache_root: Path) -> None:
    if cache_root.exists():
        shutil.rmtree(cache_root)
    shutil.copytree(
        PLUGIN_ROOT,
        cache_root,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", ".mypy_cache"),
    )


def write_broken_cache_adapter(cache_root: Path, adapter_name: str) -> None:
    hook_dir = cache_root / "hooks"
    hook_dir.mkdir(parents=True, exist_ok=True)
    (hook_dir / adapter_name).write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "print('stale Arbor cache adapter selected', file=sys.stderr)\n"
        "raise SystemExit(91)\n",
        encoding="utf-8",
    )


def write_hanging_cache_adapter(cache_root: Path, adapter_name: str) -> None:
    hook_dir = cache_root / "hooks"
    hook_dir.mkdir(parents=True, exist_ok=True)
    (hook_dir / adapter_name).write_text(
        "#!/usr/bin/env python3\n"
        "import time\n"
        "time.sleep(5)\n",
        encoding="utf-8",
    )


def write_invalid_success_cache_adapter(cache_root: Path, adapter_name: str) -> None:
    hook_dir = cache_root / "hooks"
    hook_dir.mkdir(parents=True, exist_ok=True)
    (hook_dir / adapter_name).write_text(
        "#!/usr/bin/env python3\n"
        "print('not json from stale Arbor cache')\n",
        encoding="utf-8",
    )


def write_success_with_stderr_cache_adapter(cache_root: Path, adapter_name: str) -> None:
    hook_dir = cache_root / "hooks"
    hook_dir.mkdir(parents=True, exist_ok=True)
    (hook_dir / adapter_name).write_text(
        "#!/usr/bin/env python3\n"
        "import json\n"
        "import sys\n"
        "print(json.dumps({'continue': True, 'suppressOutput': True}))\n"
        "print('stale Arbor cache diagnostic on stderr', file=sys.stderr)\n",
        encoding="utf-8",
    )


def fake_home_env(base_env: dict[str, str], home: Path) -> dict[str, str]:
    env = dict(base_env)
    for name in ("ARBOR_PLUGIN_ROOT", "PLUGIN_ROOT", "CODEX_PLUGIN_ROOT", "CLAUDE_PLUGIN_ROOT"):
        env.pop(name, None)
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    return env


def validate_project_hook_wrappers_execute(errors: list[str]) -> None:
    env = os.environ.copy()
    env["ARBOR_PLUGIN_ROOT"] = str(PLUGIN_ROOT)
    env["PLUGIN_ROOT"] = str(PLUGIN_ROOT)
    env["CODEX_PLUGIN_ROOT"] = str(PLUGIN_ROOT)
    env["CLAUDE_PLUGIN_ROOT"] = str(PLUGIN_ROOT)

    with tempfile.TemporaryDirectory(prefix="arbor-wrapper-exec-check-") as tmp:
        root = Path(tmp)
        run_command(["git", "init", str(root)], errors)
        (root / "README.md").write_text("# Wrapper Smoke\n", encoding="utf-8")
        (root / "AGENTS.md").write_text(valid_agents_for_smoke(), encoding="utf-8")
        (root / ".arbor").mkdir()
        (root / ".arbor" / "memory.md").write_text("# Session Memory\n\n## In-flight\n\n- None.\n", encoding="utf-8")
        run_command(
            [
                sys.executable,
                str(SCRIPTS_ROOT / "register_project_hooks.py"),
                "--root",
                str(root),
                "--runtime",
                "both",
            ],
            errors,
        )

        for wrapper_rel in (
            ".codex/hooks/arbor-session-start",
            ".claude/hooks/arbor-session-start",
        ):
            wrapper = root / wrapper_rel
            startup = run_project_wrapper(wrapper, {"cwd": str(root), "source": "startup"}, errors, env)
            check(errors, "# Project Startup Context" in startup, f"{wrapper_rel} must emit startup context")
            clear = run_project_wrapper(wrapper, {"cwd": str(root), "source": "clear"}, errors, env)
            check(errors, clear.strip() == "", f"{wrapper_rel} clear source must stay quiet")

        for wrapper_rel in (
            ".codex/hooks/arbor-stop-memory-hygiene",
            ".claude/hooks/arbor-stop-memory-hygiene",
        ):
            wrapper = root / wrapper_rel
            stop_output = run_project_wrapper(wrapper, {"cwd": str(root), "read_only": True}, errors, env)
            check(errors, '"continue": true' in stop_output, f"{wrapper_rel} read-only stop must allow stop")

        for wrapper_rel, expected_output, message in (
            (".codex/hooks/arbor-session-start", "", "SessionStart wrapper must soft-skip when adapter launch fails"),
            (".claude/hooks/arbor-stop-memory-hygiene", '"continue": true', "Stop wrapper must allow stop when adapter launch fails"),
        ):
            wrapper = root / wrapper_rel
            module_name = f"arbor_wrapper_launch_failure_{wrapper_rel.replace('/', '_').replace('.', '_').replace('-', '_')}"
            wrapper_loader = importlib.machinery.SourceFileLoader(module_name, str(wrapper))
            wrapper_spec = importlib.util.spec_from_loader(
                module_name,
                wrapper_loader,
            )
            if wrapper_spec is None or wrapper_spec.loader is None:
                add_error(errors, f"could not load generated wrapper for launch-failure validation: {wrapper_rel}")
                continue
            wrapper_module = importlib.util.module_from_spec(wrapper_spec)
            sys.modules[wrapper_spec.name] = wrapper_module
            wrapper_spec.loader.exec_module(wrapper_module)
            original_run = wrapper_module.subprocess.run
            original_stdin = sys.stdin

            def raise_wrapper_adapter_oserror(_command: list[str], *_args: Any, **_kwargs: Any) -> Any:
                raise OSError("simulated wrapper adapter launch failure")

            wrapper_module.subprocess.run = raise_wrapper_adapter_oserror
            sys.stdin = io.StringIO(json.dumps({"cwd": str(root), "read_only": True}))
            stdout = io.StringIO()
            try:
                with contextlib.redirect_stdout(stdout):
                    try:
                        code = wrapper_module.main()
                    except OSError as exc:
                        add_error(errors, f"generated wrapper must not propagate adapter launch failures: {exc}")
                        code = 99
            finally:
                wrapper_module.subprocess.run = original_run
                sys.stdin = original_stdin
            check(errors, code == 0, message)
            check(errors, expected_output in stdout.getvalue(), message)

        for wrapper_rel, expected_output, message in (
            (".codex/hooks/arbor-session-start", "", "SessionStart wrapper must soft-skip when adapter discovery fails"),
            (".claude/hooks/arbor-stop-memory-hygiene", '"continue": true', "Stop wrapper must allow stop when adapter discovery fails"),
        ):
            wrapper = root / wrapper_rel
            module_name = f"arbor_wrapper_discovery_failure_{wrapper_rel.replace('/', '_').replace('.', '_').replace('-', '_')}"
            wrapper_loader = importlib.machinery.SourceFileLoader(module_name, str(wrapper))
            wrapper_spec = importlib.util.spec_from_loader(
                module_name,
                wrapper_loader,
            )
            if wrapper_spec is None or wrapper_spec.loader is None:
                add_error(errors, f"could not load generated wrapper for discovery-failure validation: {wrapper_rel}")
                continue
            wrapper_module = importlib.util.module_from_spec(wrapper_spec)
            sys.modules[wrapper_spec.name] = wrapper_module
            wrapper_spec.loader.exec_module(wrapper_module)
            original_resolve_adapter = wrapper_module.resolve_adapter
            original_stdin = sys.stdin

            def raise_wrapper_discovery_oserror() -> Any:
                raise OSError("simulated wrapper adapter discovery failure")

            wrapper_module.resolve_adapter = raise_wrapper_discovery_oserror
            sys.stdin = io.StringIO(json.dumps({"cwd": str(root), "read_only": True}))
            stdout = io.StringIO()
            try:
                with contextlib.redirect_stdout(stdout):
                    try:
                        code = wrapper_module.main()
                    except OSError as exc:
                        add_error(errors, f"generated wrapper must not propagate adapter discovery failures: {exc}")
                        code = 99
            finally:
                wrapper_module.resolve_adapter = original_resolve_adapter
                sys.stdin = original_stdin
            check(errors, code == 0, message)
            check(errors, expected_output in stdout.getvalue(), message)

        missing_cache_env = fake_home_env(os.environ.copy(), root / "missing-cache-home")
        missing_codex_startup = run_project_wrapper(
            root / ".codex" / "hooks" / "arbor-session-start",
            {"cwd": str(root), "source": "startup"},
            errors,
            missing_cache_env,
        )
        check(errors, missing_codex_startup.strip() == "", "Codex SessionStart wrapper must soft-skip when Arbor cache is missing")
        missing_claude_stop = run_project_wrapper(
            root / ".claude" / "hooks" / "arbor-stop-memory-hygiene",
            {"cwd": str(root), "read_only": True},
            errors,
            missing_cache_env,
        )
        check(errors, '"continue": true' in missing_claude_stop, "Claude Stop wrapper must allow stop when Arbor cache is missing")

        dev_cache_home = root / "dev-cache-home"
        copy_plugin_to_cache(dev_cache_home / ".codex" / "plugins" / "cache" / "arbor" / "arbor" / "dev")
        copy_plugin_to_cache(dev_cache_home / ".claude" / "plugins" / "cache" / "arbor" / "arbor" / "dev")
        dev_cache_env = fake_home_env(os.environ.copy(), dev_cache_home)
        dev_cache_codex_startup = run_project_wrapper(
            root / ".codex" / "hooks" / "arbor-session-start",
            {"cwd": str(root), "source": "startup"},
            errors,
            dev_cache_env,
        )
        check(errors, dev_cache_codex_startup.strip() == "", "Codex SessionStart wrapper must ignore non-release cache directories")
        dev_cache_claude_startup = run_project_wrapper(
            root / ".claude" / "hooks" / "arbor-session-start",
            {"cwd": str(root), "source": "startup"},
            errors,
            dev_cache_env,
        )
        check(errors, dev_cache_claude_startup.strip() == "", "Claude SessionStart wrapper must ignore non-release cache directories")

        incomplete_high_home = root / "incomplete-high-cache-home"
        write_broken_cache_adapter(
            incomplete_high_home / ".codex" / "plugins" / "cache" / "arbor" / "arbor" / "2.0.1",
            "session-start",
        )
        write_broken_cache_adapter(
            incomplete_high_home / ".claude" / "plugins" / "cache" / "arbor" / "arbor" / "2.0.1",
            "session-start",
        )
        copy_plugin_to_cache(incomplete_high_home / ".codex" / "plugins" / "cache" / "arbor" / "arbor" / "2.0.0")
        copy_plugin_to_cache(incomplete_high_home / ".claude" / "plugins" / "cache" / "arbor" / "arbor" / "2.0.0")
        incomplete_high_env = fake_home_env(os.environ.copy(), incomplete_high_home)
        incomplete_high_codex_startup = run_project_wrapper(
            root / ".codex" / "hooks" / "arbor-session-start",
            {"cwd": str(root), "source": "startup"},
            errors,
            incomplete_high_env,
        )
        check(
            errors,
            "# Project Startup Context" in incomplete_high_codex_startup,
            "Codex SessionStart wrapper must skip incomplete higher-version caches",
        )
        incomplete_high_claude_startup = run_project_wrapper(
            root / ".claude" / "hooks" / "arbor-session-start",
            {"cwd": str(root), "source": "startup"},
            errors,
            incomplete_high_env,
        )
        check(
            errors,
            "# Project Startup Context" in incomplete_high_claude_startup,
            "Claude SessionStart wrapper must skip incomplete higher-version caches",
        )

        broken_home = root / "broken-cache-home"
        broken_codex_cache = broken_home / ".codex" / "plugins" / "cache" / "arbor" / "arbor" / "2.0.0"
        broken_claude_cache = broken_home / ".claude" / "plugins" / "cache" / "arbor" / "arbor" / "2.0.0"
        copy_plugin_to_cache(broken_codex_cache)
        copy_plugin_to_cache(broken_claude_cache)
        write_broken_cache_adapter(broken_codex_cache, "session-start")
        write_broken_cache_adapter(broken_claude_cache, "stop-memory-hygiene")
        broken_cache_env = fake_home_env(os.environ.copy(), broken_home)
        broken_codex_startup = run_project_wrapper(
            root / ".codex" / "hooks" / "arbor-session-start",
            {"cwd": str(root), "source": "startup"},
            errors,
            broken_cache_env,
        )
        check(errors, broken_codex_startup.strip() == "", "Codex SessionStart wrapper must soft-skip when the cache adapter fails")
        broken_claude_stop = run_project_wrapper(
            root / ".claude" / "hooks" / "arbor-stop-memory-hygiene",
            {"cwd": str(root), "read_only": True},
            errors,
            broken_cache_env,
        )
        check(errors, '"continue": true' in broken_claude_stop, "Claude Stop wrapper must allow stop when the cache adapter fails")
        check(errors, "stale Arbor cache adapter selected" not in broken_claude_stop, "Stop wrapper must suppress failed adapter diagnostics")

        hanging_home = root / "hanging-cache-home"
        hanging_codex_cache = hanging_home / ".codex" / "plugins" / "cache" / "arbor" / "arbor" / "2.0.0"
        hanging_claude_cache = hanging_home / ".claude" / "plugins" / "cache" / "arbor" / "arbor" / "2.0.0"
        copy_plugin_to_cache(hanging_codex_cache)
        copy_plugin_to_cache(hanging_claude_cache)
        write_hanging_cache_adapter(hanging_codex_cache, "session-start")
        write_hanging_cache_adapter(hanging_claude_cache, "stop-memory-hygiene")
        hanging_cache_env = fake_home_env(os.environ.copy(), hanging_home)
        hanging_cache_env["ARBOR_HOOK_ADAPTER_TIMEOUT_SECONDS"] = "0.2"
        hanging_codex_startup = run_project_wrapper(
            root / ".codex" / "hooks" / "arbor-session-start",
            {"cwd": str(root), "source": "startup"},
            errors,
            hanging_cache_env,
            timeout_seconds=HANGING_WRAPPER_ASSERTION_TIMEOUT_SECONDS,
        )
        check(errors, hanging_codex_startup.strip() == "", "Codex SessionStart wrapper must soft-skip when the cache adapter times out")
        hanging_claude_stop = run_project_wrapper(
            root / ".claude" / "hooks" / "arbor-stop-memory-hygiene",
            {"cwd": str(root), "read_only": True},
            errors,
            hanging_cache_env,
            timeout_seconds=HANGING_WRAPPER_ASSERTION_TIMEOUT_SECONDS,
        )
        check(errors, '"continue": true' in hanging_claude_stop, "Claude Stop wrapper must allow stop when the cache adapter times out")

        invalid_success_home = root / "invalid-success-cache-home"
        invalid_success_claude_cache = (
            invalid_success_home / ".claude" / "plugins" / "cache" / "arbor" / "arbor" / "2.0.0"
        )
        copy_plugin_to_cache(invalid_success_claude_cache)
        write_invalid_success_cache_adapter(invalid_success_claude_cache, "stop-memory-hygiene")
        invalid_success_env = fake_home_env(os.environ.copy(), invalid_success_home)
        invalid_success_stop = run_project_wrapper(
            root / ".claude" / "hooks" / "arbor-stop-memory-hygiene",
            {"cwd": str(root), "read_only": True},
            errors,
            invalid_success_env,
        )
        try:
            invalid_success_stop_json = json.loads(invalid_success_stop)
        except json.JSONDecodeError as exc:
            invalid_success_stop_json = {}
            add_error(errors, f"Claude Stop wrapper must return valid JSON when a cache adapter emits invalid success output: {exc}")
        check(
            errors,
            invalid_success_stop_json.get("continue") is True,
            "Claude Stop wrapper must allow stop when a cache adapter emits invalid success output",
        )
        check(
            errors,
            "not json from stale Arbor cache" not in invalid_success_stop,
            "Claude Stop wrapper must suppress invalid successful adapter output",
        )

        stderr_success_home = root / "stderr-success-cache-home"
        stderr_success_claude_cache = (
            stderr_success_home / ".claude" / "plugins" / "cache" / "arbor" / "arbor" / "2.0.0"
        )
        copy_plugin_to_cache(stderr_success_claude_cache)
        write_success_with_stderr_cache_adapter(stderr_success_claude_cache, "stop-memory-hygiene")
        stderr_success_env = fake_home_env(os.environ.copy(), stderr_success_home)
        stderr_success_stop = run_project_wrapper(
            root / ".claude" / "hooks" / "arbor-stop-memory-hygiene",
            {"cwd": str(root), "read_only": True},
            errors,
            stderr_success_env,
        )
        try:
            stderr_success_stop_json = json.loads(stderr_success_stop)
        except json.JSONDecodeError as exc:
            stderr_success_stop_json = {}
            add_error(errors, f"Claude Stop wrapper must keep successful adapter stderr out of JSON output: {exc}")
        check(
            errors,
            stderr_success_stop_json.get("continue") is True,
            "Claude Stop wrapper must preserve valid allow-stop stdout when adapter writes stderr",
        )
        check(
            errors,
            "stale Arbor cache diagnostic on stderr" not in stderr_success_stop,
            "Claude Stop wrapper must suppress successful adapter stderr",
        )

        fake_home = root / "fake-home"
        write_broken_cache_adapter(fake_home / ".codex" / "plugins" / "cache" / "arbor" / "arbor" / "1.9.0", "session-start")
        write_broken_cache_adapter(fake_home / ".codex" / "plugins" / "cache" / "arbor" / "arbor" / "1.9.0", "stop-memory-hygiene")
        write_broken_cache_adapter(fake_home / ".claude" / "plugins" / "cache" / "arbor" / "arbor" / "1.9.0", "session-start")
        write_broken_cache_adapter(fake_home / ".claude" / "plugins" / "cache" / "arbor" / "arbor" / "1.9.0", "stop-memory-hygiene")
        copy_plugin_to_cache(fake_home / ".codex" / "plugins" / "cache" / "arbor" / "arbor" / "2.0.0")
        copy_plugin_to_cache(fake_home / ".claude" / "plugins" / "cache" / "arbor" / "arbor" / "2.0.0")
        cache_env = fake_home_env(os.environ.copy(), fake_home)

        codex_cache_startup = run_project_wrapper(
            root / ".codex" / "hooks" / "arbor-session-start",
            {"cwd": str(root), "source": "startup"},
            errors,
            cache_env,
        )
        check(errors, "# Project Startup Context" in codex_cache_startup, "Codex wrapper must resolve adapter from cache without plugin-root env")
        claude_cache_startup = run_project_wrapper(
            root / ".claude" / "hooks" / "arbor-session-start",
            {"cwd": str(root), "source": "startup"},
            errors,
            cache_env,
        )
        check(errors, "# Project Startup Context" in claude_cache_startup, "Claude wrapper must resolve adapter from cache without plugin-root env")
        codex_cache_stop = run_project_wrapper(
            root / ".codex" / "hooks" / "arbor-stop-memory-hygiene",
            {"cwd": str(root), "read_only": True},
            errors,
            cache_env,
        )
        check(errors, '"continue": true' in codex_cache_stop, "Codex Stop wrapper must resolve adapter from cache without plugin-root env")
        claude_cache_stop = run_project_wrapper(
            root / ".claude" / "hooks" / "arbor-stop-memory-hygiene",
            {"cwd": str(root), "read_only": True},
            errors,
            cache_env,
        )
        check(errors, '"continue": true' in claude_cache_stop, "Claude Stop wrapper must resolve adapter from cache without plugin-root env")

        polluted_env = fake_home_env(os.environ.copy(), fake_home)
        bad_env_root = root / "bad-env-plugin-root"
        write_broken_cache_adapter(bad_env_root, "session-start")
        polluted_env["ARBOR_PLUGIN_ROOT"] = str(bad_env_root)
        polluted_env["PLUGIN_ROOT"] = str(bad_env_root)
        polluted_env["CODEX_PLUGIN_ROOT"] = str(bad_env_root)
        polluted_env["CLAUDE_PLUGIN_ROOT"] = str(bad_env_root)
        polluted_startup = run_project_wrapper(
            root / ".codex" / "hooks" / "arbor-session-start",
            {"cwd": str(root), "source": "startup"},
            errors,
            polluted_env,
        )
        check(errors, "# Project Startup Context" in polluted_startup, "Codex wrapper must skip broken plugin-root env and fall back to cache")


def run_init(root: Path, errors: list[str], *args: str) -> str:
    return run_command(
        [sys.executable, str(SCRIPTS_ROOT / "init_project_memory.py"), "--root", str(root), *args],
        errors,
    )


def snapshot_files(root: Path, paths: tuple[str, ...]) -> dict[str, str | None]:
    snapshot: dict[str, str | None] = {}
    for rel in paths:
        path = root / rel
        snapshot[rel] = path.read_text(encoding="utf-8") if path.is_file() else None
    return snapshot


def validate_initialization_idempotency(errors: list[str]) -> None:
    watched = ("AGENTS.md", ".arbor/memory.md", "CLAUDE.md")
    module_path = SCRIPTS_ROOT / "init_project_memory.py"
    spec = importlib.util.spec_from_file_location("arbor_init_project_memory_template_probe", module_path)
    if spec is None or spec.loader is None:
        add_error(errors, "could not load init_project_memory.py for template error validation")
    else:
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        original_reference_dir = module.REFERENCE_DIR
        original_argv = sys.argv[:]

        with tempfile.TemporaryDirectory(prefix="arbor-init-template-error-") as tmp:
            root = Path(tmp)
            reference_dir = root / "references"
            project = root / "project"
            reference_dir.mkdir()
            project.mkdir()
            (reference_dir / "memory-template.md").write_bytes(b"\xffbad-template")
            (reference_dir / "agents-template.md").write_text("# Agent Guide\n", encoding="utf-8")
            module.REFERENCE_DIR = reference_dir
            sys.argv = ["init_project_memory.py", "--root", str(project), "--claude-bridge", "off"]
            stderr = io.StringIO()
            try:
                with contextlib.redirect_stderr(stderr):
                    try:
                        code = module.main()
                    except SystemExit as exc:
                        code = int(exc.code) if isinstance(exc.code, int) else 1
                    except UnicodeDecodeError as exc:
                        add_error(errors, f"init CLI must not leak template UnicodeDecodeError: {exc}")
                        code = 99
            finally:
                module.REFERENCE_DIR = original_reference_dir
                sys.argv = original_argv
            output = stderr.getvalue()
            check(errors, code == 2, "init CLI template read failures must exit through parser error")
            check(errors, "could not read Arbor template" in output, "init CLI template read failures must explain the broken template")
            check(errors, "Traceback" not in output, "init CLI template read failures must not emit tracebacks")

    with tempfile.TemporaryDirectory(prefix="arbor-init-check-") as tmp:
        root = Path(tmp)
        run_init(root, errors, "--claude-bridge", "on")
        first = snapshot_files(root, watched)
        run_init(root, errors, "--claude-bridge", "on")
        second = snapshot_files(root, watched)
        check(errors, first == second, "initialization must be idempotent when rerun")
        check(errors, first["AGENTS.md"] is not None, "init must create AGENTS.md")
        check(errors, first[".arbor/memory.md"] is not None, "init must create .arbor/memory.md")
        check(errors, first["CLAUDE.md"] is not None, "init must create CLAUDE.md when bridge is on")

    with tempfile.TemporaryDirectory(prefix="arbor-existing-check-") as tmp:
        root = Path(tmp)
        (root / "AGENTS.md").write_text("# User Guide\n\nUser authored.\n", encoding="utf-8")
        (root / ".arbor").mkdir()
        (root / ".arbor" / "memory.md").write_text("# User Memory\n\nKeep me.\n", encoding="utf-8")
        before = snapshot_files(root, ("AGENTS.md", ".arbor/memory.md"))
        run_init(root, errors, "--claude-bridge", "off")
        after = snapshot_files(root, ("AGENTS.md", ".arbor/memory.md"))
        before_agents = before["AGENTS.md"] or ""
        after_agents = after["AGENTS.md"] or ""
        check(errors, after[".arbor/memory.md"] == before[".arbor/memory.md"], "init must preserve existing .arbor/memory.md")
        check(errors, after_agents.startswith(before_agents.rstrip()), "init must preserve existing AGENTS.md user content")
        check(errors, after_agents.count("<!-- ARBOR HOOKLESS RUNTIME CONTRACT START -->") == 1, "init must append one Arbor hookless runtime contract to existing AGENTS.md")

    with tempfile.TemporaryDirectory(prefix="arbor-legacy-memory-check-") as tmp:
        root = Path(tmp)
        (root / ".codex").mkdir()
        (root / ".codex" / "memory.md").write_text("# Legacy Memory\n\nCarry forward.\n", encoding="utf-8")
        run_init(root, errors, "--claude-bridge", "off")
        memory = (root / ".arbor" / "memory.md").read_text(encoding="utf-8")
        check(errors, "Carry forward." in memory, "init must migrate legacy .codex/memory.md when canonical memory is missing")

    with tempfile.TemporaryDirectory(prefix="arbor-legacy-memory-encoding-check-") as tmp:
        root = Path(tmp)
        (root / ".codex").mkdir()
        (root / ".codex" / "memory.md").write_bytes(b"\xff\xfe\x00")
        legacy_encoding_code, legacy_encoding_output = run_command_status(
            [sys.executable, str(SCRIPTS_ROOT / "init_project_memory.py"), "--root", str(root), "--claude-bridge", "off"]
        )
        check(errors, legacy_encoding_code == 2, "init must fail cleanly when legacy memory cannot be decoded")
        check(errors, "cannot migrate" in legacy_encoding_output, "init must explain invalid legacy memory migration failures")
        check(errors, "Traceback" not in legacy_encoding_output, "init must not emit tracebacks for invalid legacy memory")

    with tempfile.TemporaryDirectory(prefix="arbor-legacy-memory-dry-run-check-") as tmp:
        root = Path(tmp)
        (root / ".codex").mkdir()
        (root / ".codex" / "memory.md").write_bytes(b"\xff\xfe\x00")
        dry_run_code, dry_run_output = run_command_status(
            [
                sys.executable,
                str(SCRIPTS_ROOT / "init_project_memory.py"),
                "--root",
                str(root),
                "--claude-bridge",
                "off",
                "--dry-run",
            ]
        )
        check(errors, dry_run_code == 2, "init dry-run must fail cleanly when legacy memory cannot be decoded")
        check(errors, "cannot migrate" in dry_run_output, "init dry-run must explain invalid legacy memory migration failures")
        check(errors, "would_migrate_from_legacy" not in dry_run_output, "init dry-run must not claim unreadable legacy memory can be migrated")


def run_framework(root: Path, errors: list[str], *args: str, allow_failure: bool = False) -> str:
    command = [
        sys.executable,
        str(SCRIPTS_ROOT / "run_framework_check.py"),
        "--root",
        str(root),
        "--plugin-root",
        str(PLUGIN_ROOT),
        *args,
    ]
    if not allow_failure:
        return run_command(command, errors)

    proc = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=bytecode_suppressed_env(),
        check=False,
    )
    return proc.stdout


def validate_framework_repair_boundaries(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="arbor-framework-check-") as tmp:
        root = Path(tmp)
        before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
        run_framework(root, errors, "--runtime", "both")
        after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
        check(errors, before == after, "detect-only framework check must not mutate files")

    with tempfile.TemporaryDirectory(prefix="arbor-framework-repair-") as tmp:
        root = Path(tmp)
        run_framework(root, errors, "--mode", "repair", "--runtime", "both", "--claude-bridge", "on")
        for rel in (
            "AGENTS.md",
            ".arbor/memory.md",
            "CLAUDE.md",
        ):
            check(errors, (root / rel).is_file(), f"repair must create {rel}")
        for rel in (
            ".codex/hooks.json",
            ".codex/hooks/arbor-session-start",
            ".codex/hooks/arbor-stop-memory-hygiene",
            ".claude/settings.json",
            ".claude/hooks/arbor-session-start",
            ".claude/hooks/arbor-stop-memory-hygiene",
        ):
            check(errors, not (root / rel).exists(), f"default hookless repair must not create {rel}")

    with tempfile.TemporaryDirectory(prefix="arbor-framework-legacy-hook-repair-") as tmp:
        root = Path(tmp)
        run_framework(root, errors, "--mode", "repair", "--runtime", "both", "--claude-bridge", "on", "--include-hooks")
        for rel in (
            "AGENTS.md",
            ".arbor/memory.md",
            "CLAUDE.md",
            ".codex/hooks.json",
            ".codex/hooks/arbor-session-start",
            ".codex/hooks/arbor-stop-memory-hygiene",
            ".claude/settings.json",
            ".claude/hooks/arbor-session-start",
            ".claude/hooks/arbor-stop-memory-hygiene",
        ):
            check(errors, (root / rel).is_file(), f"legacy hook repair must create {rel}")

    with tempfile.TemporaryDirectory(prefix="arbor-invalid-json-check-") as tmp:
        root = Path(tmp)
        (root / ".codex").mkdir()
        (root / ".codex" / "hooks.json").write_text("{not-json", encoding="utf-8")
        output = run_framework(root, errors, "--mode", "repair", "--runtime", "codex", "--include-hooks", allow_failure=True)
        hooks_json = (root / ".codex" / "hooks.json").read_text(encoding="utf-8")
        check(errors, hooks_json == "{not-json", "repair must not rewrite invalid JSON")
        check(errors, "invalid" in output.lower(), "invalid JSON must be reported visibly")

    with tempfile.TemporaryDirectory(prefix="arbor-framework-strict-fail-") as tmp:
        root = Path(tmp)
        strict_code, strict_output = run_command_status(
            [
                sys.executable,
                str(SCRIPTS_ROOT / "run_framework_check.py"),
                "--root",
                str(root),
                "--plugin-root",
                str(PLUGIN_ROOT),
                "--runtime",
                "both",
                "--strict",
            ]
        )
        check(errors, strict_code == 1, "framework check strict mode must fail when Result is not pass")
        check(errors, "Result: needs_repair" in strict_output, "framework strict failure must still render the framework result")

    with tempfile.TemporaryDirectory(prefix="arbor-framework-strict-pass-") as tmp:
        root = Path(tmp)
        strict_pass_code, strict_pass_output = run_command_status(
            [
                sys.executable,
                str(SCRIPTS_ROOT / "run_framework_check.py"),
                "--root",
                str(root),
                "--plugin-root",
                str(PLUGIN_ROOT),
                "--mode",
                "repair",
                "--runtime",
                "claude",
                "--claude-bridge",
                "on",
                "--strict",
            ]
        )
        check(errors, strict_pass_code == 0, f"framework check strict mode must pass when Result is pass: {strict_pass_output.strip()}")
        check(errors, "Result: pass" in strict_pass_output, "framework strict success must render Result: pass")


def run_adapter(adapter_name: str, payload: str, errors: list[str], env: dict[str, str] | None = None) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(PLUGIN_ROOT / "hooks" / adapter_name)],
        input=payload,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=bytecode_suppressed_env(env),
        check=False,
    )
    if proc.returncode != 0:
        add_error(errors, f"{adapter_name} exited {proc.returncode}: {proc.stdout.strip()}")
    return proc.returncode, proc.stdout


def load_hook_adapter_module(adapter_name: str) -> Any:
    path = PLUGIN_ROOT / "hooks" / adapter_name
    loader = importlib.machinery.SourceFileLoader(f"arbor_hook_adapter_{adapter_name.replace('-', '_')}", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def valid_agents_for_smoke() -> str:
    return (
        "# Agent Guide\n\n"
        "## Project Goal\n\nSmoke project.\n\n"
        "## Project Constraints\n\n- Keep checks deterministic.\n\n"
        "## Project Map\n\n- `README.md`: overview.\n"
    )


def agents_for_smoke_with_map_entries(entries: list[str]) -> str:
    return (
        "# Agent Guide\n\n"
        "## Project Goal\n\nSmoke project.\n\n"
        "## Project Constraints\n\n- Keep checks deterministic.\n\n"
        "## Project Map\n\n"
        + "".join(entries)
    )


def validate_project_map_canonical_contract(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="arbor-project-map-canonical-check-") as tmp:
        root = Path(tmp)
        (root / "README.md").write_text("# Smoke\n", encoding="utf-8")
        (root / "src").mkdir()
        (root / "src" / "main.py").write_text("print('hello')\n", encoding="utf-8")
        (root / "AGENTS.md").write_text(
            agents_for_smoke_with_map_entries(
                [
                    "- `README.md`: overview.\n",
                    "- `src/main.py`: source entrypoint.\n",
                ]
            ),
            encoding="utf-8",
        )

        nested_code, nested_output = run_command_status(
            [sys.executable, str(SCRIPTS_ROOT / "check_agents_guide_quality.py"), "--root", str(root)]
        )
        check(errors, nested_code != 0, "AGENTS quality must reject nested Project Map entries that stand in for top-level entries")
        check(errors, "missing_project_map_entry" in nested_output, "AGENTS quality must require the top-level Project Map token")
        check(errors, "non_top_level_project_map_entry" in nested_output, "AGENTS quality must explain nested Project Map entries")

        (root / "AGENTS.md").write_text(
            agents_for_smoke_with_map_entries(
                [
                    "- `README.md`: overview.\n",
                    "- `src/`: source tree.\n",
                ]
            ),
            encoding="utf-8",
        )
        canonical_code, canonical_output = run_command_status(
            [sys.executable, str(SCRIPTS_ROOT / "check_agents_guide_quality.py"), "--root", str(root)]
        )
        check(
            errors,
            canonical_code == 0,
            "AGENTS quality must accept canonical top-level Project Map entries: " + canonical_output.strip(),
        )

    env = os.environ.copy()
    env["ARBOR_PLUGIN_ROOT"] = str(PLUGIN_ROOT)
    with tempfile.TemporaryDirectory(prefix="arbor-stop-canonical-map-repair-check-") as tmp:
        root = Path(tmp)
        run_git(root, errors, "init")
        run_git(root, errors, "config", "user.email", "arbor@example.invalid")
        run_git(root, errors, "config", "user.name", "Arbor Check")
        (root / "README.md").write_text("# Smoke\n", encoding="utf-8")
        (root / "src").mkdir()
        (root / "src" / "main.py").write_text("print('hello')\n", encoding="utf-8")
        (root / "AGENTS.md").write_text(
            agents_for_smoke_with_map_entries(
                [
                    "- `README.md`: overview.\n",
                    "- `src/main.py`: source entrypoint.\n",
                ]
            ),
            encoding="utf-8",
        )
        (root / ".arbor").mkdir()
        (root / ".arbor" / "memory.md").write_text("# Session Memory\n\n## In-flight\n\n- None.\n", encoding="utf-8")
        run_git(root, errors, "add", ".")
        run_git(root, errors, "commit", "-m", "canonicalize generated project map")
        (root / "AGENTS.md").write_text(
            agents_for_smoke_with_map_entries(
                [
                    "- `README.md`: overview.\n",
                    "- `src/main.py`: generated non-canonical source entrypoint.\n",
                ]
            ),
            encoding="utf-8",
        )

        repair_code, repair_output = run_adapter("stop-memory-hygiene", json.dumps({"cwd": str(root)}), errors, env)
        repaired_agents = (root / "AGENTS.md").read_text(encoding="utf-8")
        check(errors, repair_code == 0, "Stop canonical Project Map repair must not surface as a hook failure")
        check(errors, "- `src/`:" in repaired_agents, "Stop must add the canonical top-level Project Map entry")
        check(errors, "- `src/main.py`:" not in repaired_agents, "Stop must remove non-canonical nested Project Map entries")
        check(errors, '"continue": true' in repair_output, "Stop canonical Project Map repair must allow stop")


def validate_session_start_and_stop_behavior(errors: list[str]) -> None:
    env = os.environ.copy()
    env["ARBOR_PLUGIN_ROOT"] = str(PLUGIN_ROOT)
    with tempfile.TemporaryDirectory(prefix="arbor-session-stop-check-") as tmp:
        root = Path(tmp)
        run_command(["git", "init", str(root)], errors)
        (root / "README.md").write_text("# Smoke\n", encoding="utf-8")
        (root / "AGENTS.md").write_text(valid_agents_for_smoke(), encoding="utf-8")
        (root / ".arbor").mkdir()
        (root / ".arbor" / "memory.md").write_text("# Session Memory\n\n## In-flight\n\n- None.\n", encoding="utf-8")

        _, startup = run_adapter("session-start", json.dumps({"cwd": str(root), "source": "startup"}), errors, env)
        check(errors, "# Project Startup Context" in startup, "SessionStart startup must emit context")
        check(errors, startup.find("## 1. AGENTS.md") < startup.find("## 2. formatted git log"), "SessionStart must emit AGENTS before git log")
        check(errors, startup.find("## 2. formatted git log") < startup.find("## 3. .arbor/memory.md"), "SessionStart must emit git log before memory")
        check(errors, startup.find("## 3. .arbor/memory.md") < startup.find("## 4. git status"), "SessionStart must emit memory before git status")

        with tempfile.TemporaryDirectory(prefix="arbor-bad-adapter-env-root-") as bad_tmp:
            bad_env_root = Path(bad_tmp)
            bad_env = env.copy()
            for name in ("ARBOR_PLUGIN_ROOT", "PLUGIN_ROOT", "CODEX_PLUGIN_ROOT", "CLAUDE_PLUGIN_ROOT"):
                bad_env[name] = str(bad_env_root)
            bad_env_code, bad_env_startup = run_adapter(
                "session-start",
                json.dumps({"cwd": str(root), "source": "startup"}),
                errors,
                bad_env,
            )
            check(errors, bad_env_code == 0, "SessionStart adapter must ignore incomplete plugin-root env values")
            check(errors, "# Project Startup Context" in bad_env_startup, "SessionStart adapter must fall back to its packaged plugin root")

            bad_env_stop = bad_env.copy()
            bad_env_stop["ARBOR_STOP_MEMORY_HYGIENE_MODE"] = "block"
            bad_env_stop_code, bad_env_stop_output = run_adapter(
                "stop-memory-hygiene",
                json.dumps({"cwd": str(root)}),
                errors,
                bad_env_stop,
            )
            check(errors, bad_env_stop_code == 0, "Stop adapter must ignore incomplete plugin-root env values")
            check(errors, "shared memory hygiene script not found" not in bad_env_stop_output, "Stop adapter must fall back to its packaged plugin root")

        _, clear = run_adapter("session-start", json.dumps({"cwd": str(root), "source": "clear"}), errors, env)
        check(errors, clear.strip() == "", "SessionStart clear source must stay quiet")

        missing_cwd = root / "missing-worktree"
        missing_code, missing_startup = run_adapter("session-start", json.dumps({"cwd": str(missing_cwd), "source": "startup"}), errors, env)
        check(errors, missing_code == 0, "SessionStart unavailable cwd must not surface as a hook failure")
        check(errors, "# Project Startup Context" not in missing_startup, "SessionStart unavailable cwd must not inject stale startup context")

        malformed_start_code, malformed_startup = run_adapter("session-start", json.dumps({"cwd": [], "source": "startup"}), errors, env)
        check(errors, malformed_start_code == 0, "SessionStart malformed cwd must not surface as a hook failure")
        check(errors, "# Project Startup Context" not in malformed_startup, "SessionStart malformed cwd must not inject stale startup context")
        object_cwd_start_code, object_cwd_startup = run_adapter("session-start", json.dumps({"cwd": {"path": str(root)}, "source": "startup"}), errors, env)
        check(errors, object_cwd_start_code == 0, "SessionStart object cwd must not surface as a hook failure")
        check(errors, "# Project Startup Context" not in object_cwd_startup, "SessionStart object cwd must not inject stale startup context")

        session_module = load_hook_adapter_module("session-start")
        original_session_subprocess_run = session_module.subprocess.run
        original_session_stdin = session_module.sys.stdin
        original_session_looks_like = session_module.looks_like_arbor_plugin_root
        original_arbor_plugin_root_env = os.environ.get("ARBOR_PLUGIN_ROOT")

        bom_session_stdout = io.StringIO()
        bom_session_stderr = io.StringIO()
        session_module.sys.stdin = io.StringIO("\ufeff" + json.dumps({"cwd": str(root), "source": "startup"}))
        try:
            with contextlib.redirect_stdout(bom_session_stdout), contextlib.redirect_stderr(bom_session_stderr):
                bom_session_code = session_module.main()
        except json.JSONDecodeError as exc:
            add_error(errors, f"SessionStart BOM-prefixed hook payloads must not raise JSONDecodeError: {exc}")
            bom_session_code = 1
        finally:
            session_module.sys.stdin = original_session_stdin
        check(errors, bom_session_code == 0, "SessionStart BOM-prefixed hook payload must exit 0")
        check(
            errors,
            "# Project Startup Context" in bom_session_stdout.getvalue(),
            "SessionStart must tolerate UTF-8 BOM-prefixed hook payloads",
        )

        def raise_session_env_root_oserror(root_path: Path) -> bool:
            raise OSError("simulated SessionStart env root stat failure")

        session_module.looks_like_arbor_plugin_root = raise_session_env_root_oserror
        os.environ["ARBOR_PLUGIN_ROOT"] = str(root / "bad-env-root")
        try:
            try:
                resolved_session_root = session_module.resolve_plugin_root()
            except OSError as exc:
                add_error(errors, f"SessionStart adapter plugin-root env errors must not propagate: {exc}")
                resolved_session_root = Path("propagated")
            check(errors, resolved_session_root == PLUGIN_ROOT, "SessionStart adapter must ignore plugin-root env filesystem errors")
        finally:
            session_module.looks_like_arbor_plugin_root = original_session_looks_like
            if original_arbor_plugin_root_env is None:
                os.environ.pop("ARBOR_PLUGIN_ROOT", None)
            else:
                os.environ["ARBOR_PLUGIN_ROOT"] = original_arbor_plugin_root_env

        def raise_session_timeout(command: list[str], *_args: Any, **_kwargs: Any) -> Any:
            raise subprocess.TimeoutExpired(command, timeout=0.1)

        session_module.subprocess.run = raise_session_timeout
        session_stdout = io.StringIO()
        session_stderr = io.StringIO()
        session_module.sys.stdin = io.StringIO(json.dumps({"cwd": str(root), "source": "startup"}))
        try:
            try:
                with contextlib.redirect_stdout(session_stdout), contextlib.redirect_stderr(session_stderr):
                    session_timeout_code = session_module.main()
            except subprocess.TimeoutExpired as exc:
                add_error(errors, f"SessionStart startup helper timeout must not propagate: {exc}")
                session_timeout_code = 1
            check(errors, session_timeout_code == 0, "SessionStart startup helper timeout must soft-skip")
            check(errors, session_stdout.getvalue() == "", "SessionStart startup helper timeout must not inject partial context")
        finally:
            session_module.subprocess.run = original_session_subprocess_run
            session_module.sys.stdin = original_session_stdin

        def raise_session_launch_failure(command: list[str], *_args: Any, **_kwargs: Any) -> Any:
            raise OSError("simulated SessionStart helper launch failure")

        session_module.subprocess.run = raise_session_launch_failure
        session_stdout = io.StringIO()
        session_stderr = io.StringIO()
        session_module.sys.stdin = io.StringIO(json.dumps({"cwd": str(root), "source": "startup"}))
        try:
            try:
                with contextlib.redirect_stdout(session_stdout), contextlib.redirect_stderr(session_stderr):
                    session_launch_code = session_module.main()
            except OSError as exc:
                add_error(errors, f"SessionStart startup helper launch failures must not propagate: {exc}")
                session_launch_code = 1
            check(errors, session_launch_code == 0, "SessionStart startup helper launch failure must soft-skip")
            check(errors, session_stdout.getvalue() == "", "SessionStart startup helper launch failure must not inject partial context")
        finally:
            session_module.subprocess.run = original_session_subprocess_run
            session_module.sys.stdin = original_session_stdin

        before = (root / ".arbor" / "memory.md").read_text(encoding="utf-8")
        _, stop_output = run_adapter("stop-memory-hygiene", json.dumps({"cwd": str(root), "read_only": True}), errors, env)
        after = (root / ".arbor" / "memory.md").read_text(encoding="utf-8")
        check(errors, before == after, "Stop read-only payload must not mutate memory")
        check(errors, '"continue": true' in stop_output, "Stop read-only payload must allow stop")

        malformed_stop_code, malformed_stop_output = run_adapter("stop-memory-hygiene", json.dumps({"cwd": []}), errors, env)
        check(errors, malformed_stop_code == 0, "Stop malformed cwd must not surface as a hook failure")
        check(errors, '"continue": true' in malformed_stop_output, "Stop malformed cwd must allow stop")
        object_cwd_stop_code, object_cwd_stop_output = run_adapter("stop-memory-hygiene", json.dumps({"cwd": {"path": str(root)}}), errors, env)
        check(errors, object_cwd_stop_code == 0, "Stop object cwd must not surface as a hook failure")
        check(errors, '"continue": true' in object_cwd_stop_output, "Stop object cwd must allow stop")

        stop_module = load_hook_adapter_module("stop-memory-hygiene")
        original_stop_subprocess_run = stop_module.subprocess.run
        original_stop_looks_like = stop_module.looks_like_arbor_plugin_root
        original_stop_stdin = stop_module.sys.stdin

        (root / ".arbor" / "memory.md").write_text("# Session Memory\n\n## In-flight\n\n- None.\n", encoding="utf-8")
        bom_memory_before = (root / ".arbor" / "memory.md").read_text(encoding="utf-8")
        bom_stop_stdout = io.StringIO()
        bom_stop_stderr = io.StringIO()
        stop_module.sys.stdin = io.StringIO("\ufeff" + json.dumps({"cwd": str(root)}))
        try:
            with contextlib.redirect_stdout(bom_stop_stdout), contextlib.redirect_stderr(bom_stop_stderr):
                bom_stop_code = stop_module.main()
        except json.JSONDecodeError as exc:
            add_error(errors, f"Stop BOM-prefixed hook payloads must not raise JSONDecodeError: {exc}")
            bom_stop_code = 1
        finally:
            stop_module.sys.stdin = original_stop_stdin
        bom_memory_after = (root / ".arbor" / "memory.md").read_text(encoding="utf-8")
        check(errors, bom_stop_code == 0, "Stop BOM-prefixed hook payload must exit 0")
        check(errors, "[hook:resume]" in bom_memory_after, "Stop BOM-prefixed payloads must still run quiet memory maintenance")
        check(errors, bom_memory_before != bom_memory_after, "Stop BOM-prefixed payloads must not silently skip maintenance")
        check(errors, '"continue": true' in bom_stop_stdout.getvalue(), "Stop BOM-prefixed payloads must allow stop")

        def raise_stop_env_root_oserror(root_path: Path) -> bool:
            raise OSError("simulated Stop env root stat failure")

        stop_module.looks_like_arbor_plugin_root = raise_stop_env_root_oserror
        os.environ["ARBOR_PLUGIN_ROOT"] = str(root / "bad-stop-env-root")
        try:
            try:
                resolved_stop_root = stop_module.resolve_plugin_root()
            except OSError as exc:
                add_error(errors, f"Stop adapter plugin-root env errors must not propagate: {exc}")
                resolved_stop_root = Path("propagated")
            check(errors, resolved_stop_root == PLUGIN_ROOT, "Stop adapter must ignore plugin-root env filesystem errors")
        finally:
            stop_module.looks_like_arbor_plugin_root = original_stop_looks_like
            if original_arbor_plugin_root_env is None:
                os.environ.pop("ARBOR_PLUGIN_ROOT", None)
            else:
                os.environ["ARBOR_PLUGIN_ROOT"] = original_arbor_plugin_root_env

        def raise_stop_timeout(command: list[str], *_args: Any, **_kwargs: Any) -> Any:
            raise subprocess.TimeoutExpired(command, timeout=0.1)

        stop_module.subprocess.run = raise_stop_timeout
        try:
            try:
                timed_out_status = stop_module.git_status_lines(root)
            except subprocess.TimeoutExpired as exc:
                add_error(errors, f"Stop git status timeout must not propagate: {exc}")
                timed_out_status = ["propagated"]
            check(errors, timed_out_status == [], "Stop git status timeout must return no status lines")
            try:
                guide_ok, guide_output = stop_module.run_agents_guide_quality_check(root, PLUGIN_ROOT)
            except subprocess.TimeoutExpired as exc:
                add_error(errors, f"Stop AGENTS guide quality timeout must not propagate: {exc}")
                guide_ok, guide_output = False, "propagated"
            check(errors, guide_ok is True and guide_output == "", "Stop AGENTS guide quality timeout must soft-skip")
        finally:
            stop_module.subprocess.run = original_stop_subprocess_run

        def raise_stop_launch_failure(command: list[str], *_args: Any, **_kwargs: Any) -> Any:
            raise OSError("simulated Stop helper launch failure")

        stop_module.subprocess.run = raise_stop_launch_failure
        try:
            try:
                launch_failed_status = stop_module.git_status_lines(root)
            except OSError as exc:
                add_error(errors, f"Stop git status launch failures must not propagate: {exc}")
                launch_failed_status = ["propagated"]
            check(errors, launch_failed_status == [], "Stop git status launch failure must return no status lines")
            try:
                guide_ok, guide_output = stop_module.run_agents_guide_quality_check(root, PLUGIN_ROOT)
            except OSError as exc:
                add_error(errors, f"Stop AGENTS guide quality launch failures must not propagate: {exc}")
                guide_ok, guide_output = False, "propagated"
            check(errors, guide_ok is True and guide_output == "", "Stop AGENTS guide quality launch failure must soft-skip")
        finally:
            stop_module.subprocess.run = original_stop_subprocess_run

        original_stop_git_status_lines = stop_module.git_status_lines
        original_stop_guide_check = stop_module.run_agents_guide_quality_check
        original_stop_mode = os.environ.get("ARBOR_STOP_MEMORY_HYGIENE_MODE")
        stop_module.git_status_lines = lambda _root: []
        stop_module.run_agents_guide_quality_check = lambda _root, _plugin_root: (True, "")
        stop_module.subprocess.run = raise_stop_launch_failure
        stop_module.sys.stdin = io.StringIO(json.dumps({"cwd": str(root)}))
        os.environ["ARBOR_STOP_MEMORY_HYGIENE_MODE"] = "block"
        stop_block_stdout = io.StringIO()
        stop_block_stderr = io.StringIO()
        try:
            try:
                with contextlib.redirect_stdout(stop_block_stdout), contextlib.redirect_stderr(stop_block_stderr):
                    stop_block_launch_code = stop_module.main()
            except OSError as exc:
                add_error(errors, f"Stop block-mode shared helper launch failures must not propagate: {exc}")
                stop_block_launch_code = 1
            check(errors, stop_block_launch_code == 0, "Stop block-mode shared helper launch failure must allow stop")
            check(errors, '"continue": true' in stop_block_stdout.getvalue(), "Stop block-mode shared helper launch failure must emit allow-stop JSON")
        finally:
            stop_module.subprocess.run = original_stop_subprocess_run
            stop_module.sys.stdin = original_stop_stdin
            stop_module.git_status_lines = original_stop_git_status_lines
            stop_module.run_agents_guide_quality_check = original_stop_guide_check
            if original_stop_mode is None:
                os.environ.pop("ARBOR_STOP_MEMORY_HYGIENE_MODE", None)
            else:
                os.environ["ARBOR_STOP_MEMORY_HYGIENE_MODE"] = original_stop_mode

        (root / "README.md").write_text("# Smoke\n\nDirty context.\n", encoding="utf-8")
        _, dirty_stop = run_adapter("stop-memory-hygiene", json.dumps({"cwd": str(root)}), errors, env)
        memory = (root / ".arbor" / "memory.md").read_text(encoding="utf-8")
        check(errors, "[hook:resume]" in memory, "Stop dirty Arbor context must create a concise resume pointer")
        check(errors, '"continue": true' in dirty_stop, "Stop dirty Arbor context must allow stop by default")

    with tempfile.TemporaryDirectory(prefix="arbor-stop-soft-fail-check-") as tmp:
        root = Path(tmp)
        run_command(["git", "init", str(root)], errors)
        (root / "README.md").write_text("# Smoke\n", encoding="utf-8")
        (root / "AGENTS.md").write_text(valid_agents_for_smoke(), encoding="utf-8")
        (root / ".arbor").mkdir()
        (root / ".arbor" / "memory.md").write_bytes(b"\xff\xfe\x00")
        (root / "README.md").write_text("# Smoke\n\nDirty context.\n", encoding="utf-8")
        stop_code, stop_output = run_adapter("stop-memory-hygiene", json.dumps({"cwd": str(root)}), errors, env)
        check(errors, stop_code == 0, "Stop local maintenance read errors must not surface as hook failures")
        check(errors, '"continue": true' in stop_output, "Stop local maintenance read errors must still allow stop")

    with tempfile.TemporaryDirectory(prefix="arbor-stop-clean-map-check-") as tmp:
        root = Path(tmp)
        run_git(root, errors, "init")
        run_git(root, errors, "config", "user.email", "arbor@example.invalid")
        run_git(root, errors, "config", "user.name", "Arbor Check")
        (root / "README.md").write_text("# Smoke\n", encoding="utf-8")
        (root / "AGENTS.md").write_text(valid_agents_for_smoke(), encoding="utf-8")
        (root / ".arbor").mkdir()
        (root / ".arbor" / "memory.md").write_text("# Session Memory\n\n## In-flight\n\n- None.\n", encoding="utf-8")
        (root / "src").mkdir()
        (root / "src" / "main.py").write_text("print('hello')\n", encoding="utf-8")
        run_git(root, errors, "add", ".")
        run_git(root, errors, "commit", "-m", "clean project with unmapped src")
        before_agents = (root / "AGENTS.md").read_text(encoding="utf-8")
        clean_stop_code, clean_stop_output = run_adapter("stop-memory-hygiene", json.dumps({"cwd": str(root)}), errors, env)
        after_agents = (root / "AGENTS.md").read_text(encoding="utf-8")
        check(errors, clean_stop_code == 0, "Stop clean project map check must not surface as a hook failure")
        check(errors, before_agents == after_agents, "Stop clean direct turns must not mutate AGENTS.md for pre-existing map drift")
        check(errors, '"continue": true' in clean_stop_output, "Stop clean project map check must allow stop")

    with tempfile.TemporaryDirectory(prefix="arbor-stop-new-entrypoint-map-check-") as tmp:
        root = Path(tmp)
        run_git(root, errors, "init")
        run_git(root, errors, "config", "user.email", "arbor@example.invalid")
        run_git(root, errors, "config", "user.name", "Arbor Check")
        (root / "README.md").write_text("# Smoke\n", encoding="utf-8")
        (root / "AGENTS.md").write_text(valid_agents_for_smoke(), encoding="utf-8")
        (root / ".arbor").mkdir()
        memory_path = root / ".arbor" / "memory.md"
        memory_path.write_text("# Session Memory\n\n## In-flight\n\n- None.\n", encoding="utf-8")
        run_git(root, errors, "add", ".")
        run_git(root, errors, "commit", "-m", "clean initialized project")
        (root / "src").mkdir()
        (root / "src" / "main.py").write_text("print('hello')\n", encoding="utf-8")
        before_memory = memory_path.read_text(encoding="utf-8")
        new_entrypoint_code, new_entrypoint_output = run_adapter(
            "stop-memory-hygiene",
            json.dumps({"cwd": str(root)}),
            errors,
            env,
        )
        updated_agents = (root / "AGENTS.md").read_text(encoding="utf-8")
        after_memory = memory_path.read_text(encoding="utf-8")
        check(errors, new_entrypoint_code == 0, "Stop new durable entrypoint drift must not surface as a hook failure")
        check(errors, "- `src/`:" in updated_agents, "Stop must update AGENTS Project Map for a newly added durable top-level entrypoint")
        check(errors, before_memory == after_memory, "Stop Project Map-only drift must not mutate Arbor memory")
        check(errors, '"continue": true' in new_entrypoint_output, "Stop new durable entrypoint drift must allow stop")

    with tempfile.TemporaryDirectory(prefix="arbor-stop-output-artifact-map-check-") as tmp:
        root = Path(tmp)
        run_git(root, errors, "init")
        run_git(root, errors, "config", "user.email", "arbor@example.invalid")
        run_git(root, errors, "config", "user.name", "Arbor Check")
        (root / "README.md").write_text("# Smoke\n", encoding="utf-8")
        (root / "AGENTS.md").write_text(valid_agents_for_smoke(), encoding="utf-8")
        (root / ".arbor").mkdir()
        (root / ".arbor" / "memory.md").write_text("# Session Memory\n\n## In-flight\n\n- None.\n", encoding="utf-8")
        run_git(root, errors, "add", ".")
        run_git(root, errors, "commit", "-m", "clean initialized project")
        (root / "outputs").mkdir()
        (root / "outputs" / "scratch.txt").write_text("scratch\n", encoding="utf-8")
        before_agents = (root / "AGENTS.md").read_text(encoding="utf-8")
        artifact_code, artifact_output = run_adapter("stop-memory-hygiene", json.dumps({"cwd": str(root)}), errors, env)
        after_agents = (root / "AGENTS.md").read_text(encoding="utf-8")
        check(errors, artifact_code == 0, "Stop ignored output artifact drift must not surface as a hook failure")
        check(errors, before_agents == after_agents, "Stop must not add ignored output artifact directories to AGENTS Project Map")
        check(errors, '"continue": true' in artifact_output, "Stop ignored output artifact drift must allow stop")

    with tempfile.TemporaryDirectory(prefix="arbor-stop-unrelated-dirty-check-") as tmp:
        root = Path(tmp)
        run_git(root, errors, "init")
        run_git(root, errors, "config", "user.email", "arbor@example.invalid")
        run_git(root, errors, "config", "user.name", "Arbor Check")
        (root / "README.md").write_text("# Smoke\n", encoding="utf-8")
        (root / "AGENTS.md").write_text(
            valid_agents_for_smoke() + "- `src/`: source code.\n",
            encoding="utf-8",
        )
        (root / ".arbor").mkdir()
        memory_path = root / ".arbor" / "memory.md"
        memory_path.write_text("# Session Memory\n\n## In-flight\n\n- None.\n", encoding="utf-8")
        (root / "src").mkdir()
        (root / "src" / "main.py").write_text("print('hello')\n", encoding="utf-8")
        run_git(root, errors, "add", ".")
        run_git(root, errors, "commit", "-m", "clean initialized project")
        (root / "src" / "main.py").write_text("print('changed')\n", encoding="utf-8")
        before_memory = memory_path.read_text(encoding="utf-8")
        unrelated_stop_code, unrelated_stop_output = run_adapter("stop-memory-hygiene", json.dumps({"cwd": str(root)}), errors, env)
        after_memory = memory_path.read_text(encoding="utf-8")
        check(errors, unrelated_stop_code == 0, "Stop unrelated dirty source must not surface as a hook failure")
        check(errors, before_memory == after_memory, "Stop unrelated dirty source must not mutate Arbor memory")
        check(errors, '"continue": true' in unrelated_stop_output, "Stop unrelated dirty source must allow stop")

    with tempfile.TemporaryDirectory(prefix="arbor-stop-business-plugin-path-check-") as tmp:
        root = Path(tmp)
        run_git(root, errors, "init")
        run_git(root, errors, "config", "user.email", "arbor@example.invalid")
        run_git(root, errors, "config", "user.name", "Arbor Check")
        (root / "README.md").write_text("# Smoke\n", encoding="utf-8")
        (root / "AGENTS.md").write_text(
            valid_agents_for_smoke() + "- `plugins/`: application plugins.\n",
            encoding="utf-8",
        )
        (root / ".arbor").mkdir()
        memory_path = root / ".arbor" / "memory.md"
        memory_path.write_text("# Session Memory\n\n## In-flight\n\n- None.\n", encoding="utf-8")
        (root / "plugins" / "arbor").mkdir(parents=True)
        (root / "plugins" / "arbor" / "widget.txt").write_text("business plugin\n", encoding="utf-8")
        run_git(root, errors, "add", ".")
        run_git(root, errors, "commit", "-m", "clean app plugin path")
        (root / "plugins" / "arbor" / "widget.txt").write_text("changed business plugin\n", encoding="utf-8")
        before_business_memory = memory_path.read_text(encoding="utf-8")
        business_stop_code, business_stop_output = run_adapter("stop-memory-hygiene", json.dumps({"cwd": str(root)}), errors, env)
        after_business_memory = memory_path.read_text(encoding="utf-8")
        check(errors, business_stop_code == 0, "Stop business plugins/arbor path must not surface as a hook failure")
        check(errors, before_business_memory == after_business_memory, "Stop business plugins/arbor path must not mutate Arbor memory")
        check(errors, '"continue": true' in business_stop_output, "Stop business plugins/arbor path must allow stop")

    with tempfile.TemporaryDirectory(prefix="arbor-stop-renamed-memory-check-") as tmp:
        root = Path(tmp)
        run_git(root, errors, "init")
        run_git(root, errors, "config", "user.email", "arbor@example.invalid")
        run_git(root, errors, "config", "user.name", "Arbor Check")
        (root / "README.md").write_text("# Smoke\n", encoding="utf-8")
        (root / "AGENTS.md").write_text(valid_agents_for_smoke(), encoding="utf-8")
        (root / ".arbor").mkdir()
        memory_path = root / ".arbor" / "memory.md"
        memory_path.write_text("# Session Memory\n\n## In-flight\n\n- None.\n", encoding="utf-8")
        run_git(root, errors, "add", ".")
        run_git(root, errors, "commit", "-m", "clean memory")
        run_git(root, errors, "mv", ".arbor/memory.md", "memory-old.md")
        renamed_stop_code, renamed_stop_output = run_adapter("stop-memory-hygiene", json.dumps({"cwd": str(root)}), errors, env)
        check(errors, renamed_stop_code == 0, "Stop renamed Arbor memory must not surface as a hook failure")
        check(errors, memory_path.is_file(), "Stop renamed Arbor memory must recreate project memory")
        if memory_path.is_file():
            recreated_memory = memory_path.read_text(encoding="utf-8")
            check(errors, "[hook:resume]" in recreated_memory, "Stop renamed Arbor memory must preserve a resume pointer")
        check(errors, '"continue": true' in renamed_stop_output, "Stop renamed Arbor memory must allow stop")

    with tempfile.TemporaryDirectory(prefix="arbor-stop-deleted-memory-dir-check-") as tmp:
        root = Path(tmp)
        run_git(root, errors, "init")
        run_git(root, errors, "config", "user.email", "arbor@example.invalid")
        run_git(root, errors, "config", "user.name", "Arbor Check")
        (root / "README.md").write_text("# Smoke\n", encoding="utf-8")
        (root / "AGENTS.md").write_text(valid_agents_for_smoke(), encoding="utf-8")
        (root / ".arbor").mkdir()
        memory_path = root / ".arbor" / "memory.md"
        memory_path.write_text("# Session Memory\n\n## In-flight\n\n- None.\n", encoding="utf-8")
        run_git(root, errors, "add", ".")
        run_git(root, errors, "commit", "-m", "clean memory")
        shutil.rmtree(root / ".arbor")
        deleted_dir_stop_code, deleted_dir_stop_output = run_adapter(
            "stop-memory-hygiene",
            json.dumps({"cwd": str(root)}),
            errors,
            env,
        )
        check(errors, deleted_dir_stop_code == 0, "Stop deleted Arbor memory dir must not surface as a hook failure")
        check(errors, memory_path.is_file(), "Stop deleted Arbor memory dir must recreate project memory")
        if memory_path.is_file():
            restored_memory = memory_path.read_text(encoding="utf-8")
            check(errors, "[hook:resume]" in restored_memory, "Stop deleted Arbor memory dir must preserve a resume pointer")
        check(errors, '"continue": true' in deleted_dir_stop_output, "Stop deleted Arbor memory dir must allow stop")

    with tempfile.TemporaryDirectory(prefix="arbor-stop-quoted-status-path-check-") as tmp:
        root = Path(tmp)
        run_git(root, errors, "init")
        run_git(root, errors, "config", "user.email", "arbor@example.invalid")
        run_git(root, errors, "config", "user.name", "Arbor Check")
        (root / "README.md").write_text("# Smoke\n", encoding="utf-8")
        (root / "AGENTS.md").write_text(valid_agents_for_smoke(), encoding="utf-8")
        (root / ".arbor").mkdir()
        memory_path = root / ".arbor" / "memory.md"
        memory_path.write_text("# Session Memory\n\n## In-flight\n\n- None.\n", encoding="utf-8")
        spaced_note = root / ".arbor" / "resume note.md"
        spaced_note.write_text("note\n", encoding="utf-8")
        run_git(root, errors, "add", ".")
        run_git(root, errors, "commit", "-m", "clean spaced arbor path")
        spaced_note.unlink()
        before_quoted_path_memory = memory_path.read_text(encoding="utf-8")
        quoted_path_stop_code, quoted_path_stop_output = run_adapter(
            "stop-memory-hygiene",
            json.dumps({"cwd": str(root)}),
            errors,
            env,
        )
        check(errors, quoted_path_stop_code == 0, "Stop quoted Arbor status paths must not surface as a hook failure")
        if memory_path.is_file():
            quoted_path_memory = memory_path.read_text(encoding="utf-8")
            check(errors, "[hook:resume]" in quoted_path_memory, "Stop quoted Arbor status paths must preserve a resume pointer")
            check(errors, before_quoted_path_memory != quoted_path_memory, "Stop quoted Arbor status paths must refresh memory")
        check(errors, '"continue": true' in quoted_path_stop_output, "Stop quoted Arbor status paths must allow stop")


def validate_cross_platform_hook_commands(errors: list[str]) -> None:
    sys.path.insert(0, str(SCRIPTS_ROOT))
    try:
        import register_project_hooks as hooks
    finally:
        try:
            sys.path.remove(str(SCRIPTS_ROOT))
        except ValueError:
            pass

    windows_python = r"C:\Program Files\Python313\python.exe"
    windows_project = r"C:\Projects\Arbor"
    posix_python = "/opt/python/bin/python3"

    codex_windows = hooks.codex_project_hook_command(
        "arbor-session-start",
        platform="windows",
        python_executable=windows_python,
        project_root=windows_project,
    )
    check(errors, windows_python not in codex_windows, "Windows Codex hook command must delegate Python quoting to a .cmd launcher")
    check(errors, not codex_windows.startswith('"'), "Windows Codex hook command must not quote no-space .cmd launcher paths")
    check(errors, codex_windows.endswith(r".codex\hooks\arbor-session-start.cmd"), "Windows Codex hook command must call a project .cmd launcher")

    claude_windows = hooks.claude_project_hook_command(
        "arbor-stop-memory-hygiene",
        platform="windows",
        python_executable=windows_python,
    )
    check(errors, windows_python in claude_windows, "Windows Claude hook command must include absolute Python path")
    check(errors, ".claude/hooks/arbor-stop-memory-hygiene" in claude_windows, "Windows Claude hook command must call project wrapper")

    windows_shell_meta_python = r"C:\Tools&Stuff\python.exe"
    codex_windows_shell_meta = hooks.codex_project_hook_command(
        "arbor-session-start",
        platform="windows",
        python_executable=windows_shell_meta_python,
        project_root=r"C:\Project Space\Arbor",
    )
    check(
        errors,
        codex_windows_shell_meta == r'cmd.exe /d /c call "C:\Project Space\Arbor\.codex\hooks\arbor-session-start.cmd"',
        "Windows Codex hook command must use cmd.exe call for project .cmd launchers when the project path has spaces",
    )
    codex_launcher = hooks.render_windows_cmd_launcher(windows_shell_meta_python, "arbor-session-start")
    check(
        errors,
        f'"{windows_shell_meta_python}" "%~dp0arbor-session-start"' in codex_launcher,
        "Windows Codex launcher must quote the Python executable and same-directory wrapper",
    )
    claude_windows_shell_meta = hooks.claude_project_hook_command(
        "arbor-stop-memory-hygiene",
        platform="windows",
        python_executable=windows_shell_meta_python,
    )
    check(
        errors,
        claude_windows_shell_meta.startswith(f'"{windows_shell_meta_python}" '),
        "Windows Claude hook command must quote Python paths with shell metacharacters",
    )

    codex_posix = hooks.codex_project_hook_command(
        "arbor-session-start",
        platform="posix",
        python_executable=posix_python,
    )
    check(errors, "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" in codex_posix, "POSIX Codex command must use project-root fallback")
    check(errors, posix_python in codex_posix, "POSIX Codex command must include provided Python path")

    claude_posix = hooks.claude_project_hook_command(
        "arbor-stop-memory-hygiene",
        platform="posix",
        python_executable=posix_python,
    )
    check(errors, "CLAUDE_PROJECT_DIR" in claude_posix, "POSIX Claude command must use CLAUDE_PROJECT_DIR")
    check(errors, "$(pwd)" in claude_posix, "POSIX Claude command must fall back to pwd when CLAUDE_PROJECT_DIR is unavailable")
    check(errors, ".claude/hooks/arbor-stop-memory-hygiene" in claude_posix, "POSIX Claude command must call project wrapper")

    original_current_hook_platform = hooks.current_hook_platform
    original_current_python_executable = hooks.current_python_executable
    try:
        hooks.current_hook_platform = lambda: "posix"
        hooks.current_python_executable = lambda: posix_python
        with tempfile.TemporaryDirectory(prefix="arbor-forced-posix-registration-check-") as tmp:
            root = Path(tmp)
            hooks.register_project_hooks(root, runtime="both")
            codex_hooks = load_json(root / ".codex" / "hooks.json", errors)
            claude_settings = load_json(root / ".claude" / "settings.json", errors)
            codex_commands = hook_commands(codex_hooks)
            claude_commands = hook_commands(claude_settings)
            normalized_codex_commands = [command.replace("\\", "/") for command in codex_commands]
            check(
                errors,
                any(".codex/hooks/arbor-session-start" in command for command in normalized_codex_commands),
                "forced POSIX Codex registration must call the SessionStart wrapper",
            )
            check(
                errors,
                all(".cmd" not in command for command in normalized_codex_commands),
                "forced POSIX Codex registration must not call Windows .cmd launchers",
            )
            check(
                errors,
                codex_commands and all(posix_python in command for command in codex_commands),
                "forced POSIX Codex registration must include the resolved Python executable",
            )
            check(
                errors,
                claude_commands and all(".claude/hooks/" in command.replace("\\", "/") for command in claude_commands),
                "forced POSIX registration must preserve Claude wrapper commands",
            )
            check(
                errors,
                not (root / ".codex" / "hooks" / "arbor-session-start.cmd").exists()
                and not (root / ".codex" / "hooks" / "arbor-stop-memory-hygiene.cmd").exists(),
                "forced POSIX registration must not create Windows .cmd launchers",
            )
    finally:
        hooks.current_hook_platform = original_current_hook_platform
        hooks.current_python_executable = original_current_python_executable

    for platform, executable in (
        ("windows", "python"),
        ("windows", "Scripts\\python.exe"),
        ("posix", "python3"),
        ("posix", "venv/bin/python"),
    ):
        try:
            hooks.codex_project_hook_command(
                "arbor-session-start",
                platform=platform,
                python_executable=executable,
            )
        except hooks.HookRegistrationError as exc:
            check(errors, "absolute Python executable" in str(exc), "hook command Python validation error must explain absolute-path requirement")
        else:
            add_error(errors, f"hook command generation must reject non-absolute Python executable {executable!r} for {platform}")

    module_path = SCRIPTS_ROOT / "register_project_hooks.py"
    spec = importlib.util.spec_from_file_location("arbor_register_project_hooks_cli_error_probe", module_path)
    if spec is None or spec.loader is None:
        add_error(errors, "could not load register_project_hooks.py for CLI error validation")
        return
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    with tempfile.TemporaryDirectory(prefix="arbor-register-invalid-config-encoding-check-") as tmp:
        root = Path(tmp)
        codex_config = root / "hooks.json"
        claude_settings = root / "settings.json"
        codex_config.write_bytes(b"\xff\xfe\x00\xff")
        claude_settings.write_bytes(b"\xff\xfe\x00\xff")
        for loader, path, label in (
            (module.load_codex_hook_config, codex_config, "Codex hooks config"),
            (module.load_claude_settings, claude_settings, "Claude settings"),
        ):
            try:
                loader(path)
            except module.HookRegistrationError as exc:
                check(errors, "UTF-8" in str(exc), f"registration must explain invalid {label} encoding")
            except UnicodeError as exc:
                add_error(errors, f"registration must not leak UnicodeError for invalid {label} encoding: {exc}")
            else:
                add_error(errors, f"registration must reject invalid {label} encoding")

    original_register = module.register_project_hooks
    original_argv = sys.argv[:]
    stderr = io.StringIO()

    def raise_permission_error(*_args: Any, **_kwargs: Any) -> list[Any]:
        raise PermissionError("simulated hook wrapper write denial")

    module.register_project_hooks = raise_permission_error
    sys.argv = ["register_project_hooks.py", "--root", "."]
    try:
        with contextlib.redirect_stderr(stderr):
            try:
                code = module.main()
            except PermissionError as exc:
                add_error(errors, f"register_project_hooks CLI must not leak PermissionError tracebacks: {exc}")
                code = 99
    finally:
        module.register_project_hooks = original_register
        sys.argv = original_argv
    error_output = stderr.getvalue()
    check(errors, code == 1, "register_project_hooks CLI write failures must exit 1")
    check(errors, "simulated hook wrapper write denial" in error_output, "register_project_hooks CLI write failures must explain the underlying error")
    check(errors, "Traceback" not in error_output, "register_project_hooks CLI write failures must not emit Python tracebacks")


def validate_startup_context_resilience(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="arbor-startup-resilience-check-") as tmp:
        root = Path(tmp)
        output = run_command(
            [sys.executable, str(SCRIPTS_ROOT / "collect_project_context.py"), "--root", str(root)],
            errors,
        )
        check(errors, "# Project Startup Context" in output, "startup collector must render context for non-git directories")
        check(errors, "Git root: not a git repository" in output, "startup collector must identify non-git directories")
        check(errors, "## 1. AGENTS.md" in output and "Status: missing" in output, "startup collector must report missing AGENTS.md")
        check(errors, "## 2. formatted git log" in output and "Status: git-error" in output, "startup collector must report git log errors")
        check(errors, "## 3. .arbor/memory.md" in output, "startup collector must include memory section even when missing")
        check(errors, "## 4. git status" in output, "startup collector must include git status section")

    module_path = SCRIPTS_ROOT / "collect_project_context.py"
    spec = importlib.util.spec_from_file_location("arbor_collect_project_context_timeout_probe", module_path)
    if spec is None or spec.loader is None:
        add_error(errors, "could not load collect_project_context.py for startup timeout validation")
        return
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    original_subprocess_run = module.subprocess.run

    def raise_startup_git_timeout(command: list[str], *_args: Any, **_kwargs: Any) -> Any:
        if command and command[0] == "git":
            raise subprocess.TimeoutExpired(command, timeout=0.1)
        return original_subprocess_run(command, *_args, **_kwargs)

    with tempfile.TemporaryDirectory(prefix="arbor-startup-git-timeout-check-") as tmp:
        root = Path(tmp)
        (root / "AGENTS.md").write_text(valid_agents_for_smoke(), encoding="utf-8")
        module.subprocess.run = raise_startup_git_timeout
        try:
            try:
                timeout_output = module.render_context(module.collect_startup_context(root))
            except subprocess.TimeoutExpired as exc:
                add_error(errors, f"startup collector git timeouts must not propagate: {exc}")
                timeout_output = ""
        finally:
            module.subprocess.run = original_subprocess_run
        check(errors, "## 1. AGENTS.md" in timeout_output, "startup collector must keep file context when git commands time out")
        check(errors, "Status: git-timeout" in timeout_output, "startup collector must report git timeouts as section status")

    def raise_startup_git_launch(command: list[str], *_args: Any, **_kwargs: Any) -> Any:
        if command and command[0] == "git":
            raise OSError("simulated startup git launch failure")
        return original_subprocess_run(command, *_args, **_kwargs)

    with tempfile.TemporaryDirectory(prefix="arbor-startup-git-launch-check-") as tmp:
        root = Path(tmp)
        (root / "AGENTS.md").write_text(valid_agents_for_smoke(), encoding="utf-8")
        module.subprocess.run = raise_startup_git_launch
        try:
            try:
                launch_output = module.render_context(module.collect_startup_context(root))
            except OSError as exc:
                add_error(errors, f"startup collector git launch failures must not propagate: {exc}")
                launch_output = ""
        finally:
            module.subprocess.run = original_subprocess_run
        check(errors, "## 1. AGENTS.md" in launch_output, "startup collector must keep file context when git commands fail to start")
        check(errors, "Status: git-launch-error" in launch_output, "startup collector must report git launch failures as section status")
        check(errors, "simulated startup git launch failure" in launch_output, "startup collector must explain git launch failures")

    with tempfile.TemporaryDirectory(prefix="arbor-cross-memory-check-") as tmp:
        root = Path(tmp)
        run_command(["git", "init", str(root)], errors)
        (root / "AGENTS.md").write_text(valid_agents_for_smoke(), encoding="utf-8")
        (root / ".arbor").mkdir()
        (root / ".arbor" / "memory.md").write_text(
            "# Session Memory\n\n## Observations\n\n- Project: Completely Different Repo\n\n## In-flight\n\n- Keep me.\n",
            encoding="utf-8",
        )
        output = run_command(
            [sys.executable, str(SCRIPTS_ROOT / "collect_project_context.py"), "--root", str(root)],
            errors,
        )
        check(errors, "classification: suspicious-cross-project" in output, "startup collector must flag suspicious cross-project memory")
        check(errors, "WARNING: Treat this memory as suspicious" in output, "startup collector must warn before using suspicious memory")

    with tempfile.TemporaryDirectory(prefix="arbor-unreadable-memory-check-") as tmp:
        root = Path(tmp)
        run_command(["git", "init", str(root)], errors)
        (root / "AGENTS.md").write_text(valid_agents_for_smoke(), encoding="utf-8")
        (root / ".arbor").mkdir()
        (root / ".arbor" / "memory.md").write_bytes(b"\xff\xfe\x00")
        output = run_command(
            [sys.executable, str(SCRIPTS_ROOT / "collect_project_context.py"), "--root", str(root)],
            errors,
        )
        check(errors, "Status: read-error" in output, "startup collector must report unreadable memory as a read error")
        check(errors, "classification: unreadable" in output, "startup collector must classify unreadable memory as unreadable")
        check(errors, "memory_state=explicit" not in output, "startup collector must not classify unreadable memory diagnostics as explicit memory")


def validate_framework_check_smoke(errors: list[str]) -> None:
    output = run_command(
        [
            sys.executable,
            str(SCRIPTS_ROOT / "run_framework_check.py"),
            "--root",
            str(REPO_ROOT),
            "--plugin-root",
            str(PLUGIN_ROOT),
            "--runtime",
            "both",
        ],
        errors,
    )
    for term in (
        "**Arbor Framework Check**",
        "Mode: detect-only",
        "| Surface | Required | Status | Evidence | Repair |",
        "AGENTS.md",
        ".arbor/memory.md",
        "CLAUDE.md",
        "Result:",
    ):
        check(errors, term in output, f"framework check smoke output missing {term!r}")
    check(errors, "shared hook adapters" not in output, "default framework check smoke must stay hookless")

    legacy_output = run_command(
        [
            sys.executable,
            str(SCRIPTS_ROOT / "run_framework_check.py"),
            "--root",
            str(REPO_ROOT),
            "--plugin-root",
            str(PLUGIN_ROOT),
            "--runtime",
            "both",
            "--include-hooks",
        ],
        errors,
    )
    for term in (
        ".codex/hooks.json + .codex/hooks/",
        ".claude/settings.json + .claude/hooks/",
        "shared hook adapters",
    ):
        check(errors, term in legacy_output, f"legacy framework check smoke output missing {term!r}")


def main() -> int:
    errors: list[str] = []
    validate_single_skill(errors)
    validate_manifests(errors)
    validate_marketplace_entries(errors)
    validate_reference_and_script_inventory(errors)
    validate_skill_resource_links(errors)
    validate_skill_package_checker(errors)
    validate_text_boundary(errors)
    validate_readme_quality_contract(errors)
    validate_hook_runtime_documentation_contract(errors)
    validate_startup_memory_documentation_contract(errors)
    validate_framework_install_documentation_contract(errors)
    validate_quality_gate_framework_exception(errors)
    validate_quality_gate_is_artifact_free(errors)
    validate_quality_harness_modularity(errors)
    validate_source_hygiene_checker(errors)
    validate_runtime_smoke_template(errors)
    validate_release_readiness_check(errors)
    validate_install_state_checker(errors)
    validate_context_boundary_script(errors)
    validate_hook_probe_payloads(errors)
    validate_project_hook_registration(errors)
    validate_hook_diagnosis_classification(errors)
    validate_project_hook_wrappers_execute(errors)
    validate_initialization_idempotency(errors)
    validate_framework_repair_boundaries(errors)
    validate_project_map_canonical_contract(errors)
    validate_session_start_and_stop_behavior(errors)
    validate_cross_platform_hook_commands(errors)
    validate_startup_context_resilience(errors)
    validate_framework_check_smoke(errors)

    if errors:
        print("plugin adapter checks failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("plugin adapter checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
