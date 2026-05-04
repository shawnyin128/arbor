#!/usr/bin/env python3
"""Validate the repo-local Arbor plugin marketplace and installable payload."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CODEX_BIN = Path("/Applications/Codex.app/Contents/Resources/codex")
MARKETPLACE_PATH = Path(".agents") / "plugins" / "marketplace.json"
PLUGIN_MANIFEST_PATH = Path(".codex-plugin") / "plugin.json"
REQUIRED_HOOK_IDS = {
    "arbor.session_startup_context",
    "arbor.in_session_memory_hygiene",
    "arbor.goal_constraint_drift",
}
TRANSIENT_PAYLOAD_DIR_NAMES = {
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}
TRANSIENT_PAYLOAD_FILE_NAMES = {
    ".coverage",
    ".DS_Store",
}
TRANSIENT_PAYLOAD_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".swp",
    ".swo",
    ".tmp",
    ".temp",
}
EXPECTED_PAYLOAD_FILES = {
    ".codex-plugin/plugin.json",
    "hooks.json",
    "skills/arbor/SKILL.md",
    "skills/arbor/agents/openai.yaml",
    "skills/arbor/references/agents-template.md",
    "skills/arbor/references/memory-template.md",
    "skills/arbor/references/project-hooks-template.md",
    "skills/arbor/scripts/collect_project_context.py",
    "skills/arbor/scripts/init_project_memory.py",
    "skills/arbor/scripts/register_project_hooks.py",
    "skills/arbor/scripts/run_agents_guide_drift_hook.py",
    "skills/arbor/scripts/run_memory_hygiene_hook.py",
    "skills/arbor/scripts/run_session_startup_hook.py",
}
EXPECTED_PAYLOAD_DIRS = {
    parent.as_posix()
    for relative_file in EXPECTED_PAYLOAD_FILES
    for parent in Path(relative_file).parents
    if parent.as_posix() != "."
}


class PluginInstallValidationError(ValueError):
    """Raised when the local plugin installation surface is invalid."""


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise PluginInstallValidationError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise PluginInstallValidationError(f"cannot parse {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise PluginInstallValidationError(f"expected JSON object in {path}")
    return data


def validate_marketplace(repo_root: Path) -> dict[str, Any]:
    marketplace_path = repo_root / MARKETPLACE_PATH
    marketplace = read_json_object(marketplace_path)
    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list):
        raise PluginInstallValidationError("marketplace plugins must be a list")
    arbor_entries = [entry for entry in plugins if isinstance(entry, dict) and entry.get("name") == "arbor"]
    if len(arbor_entries) != 1:
        raise PluginInstallValidationError(f"expected exactly one arbor marketplace entry, found {len(arbor_entries)}")
    entry = arbor_entries[0]
    source = entry.get("source")
    if not isinstance(source, dict) or source.get("source") != "local":
        raise PluginInstallValidationError("arbor marketplace entry must use local source")
    if source.get("path") != "./plugins/arbor":
        raise PluginInstallValidationError("arbor marketplace source path must be ./plugins/arbor")
    policy = entry.get("policy")
    if not isinstance(policy, dict):
        raise PluginInstallValidationError("arbor marketplace entry must include policy")
    if policy.get("installation") != "AVAILABLE":
        raise PluginInstallValidationError("arbor marketplace installation policy must be AVAILABLE")
    if policy.get("authentication") != "ON_INSTALL":
        raise PluginInstallValidationError("arbor marketplace authentication policy must be ON_INSTALL")
    return {"name": marketplace.get("name"), "entry": entry, "path": str(marketplace_path)}


def validate_manifest(plugin_root: Path) -> dict[str, Any]:
    manifest = read_json_object(plugin_root / PLUGIN_MANIFEST_PATH)
    if manifest.get("name") != "arbor":
        raise PluginInstallValidationError("plugin manifest name must be arbor")
    if manifest.get("skills") != "./skills/":
        raise PluginInstallValidationError("plugin manifest skills path must be ./skills/")
    if manifest.get("hooks") != "./hooks.json":
        raise PluginInstallValidationError("plugin manifest hooks path must be ./hooks.json")
    interface = manifest.get("interface")
    if not isinstance(interface, dict):
        raise PluginInstallValidationError("plugin manifest must include interface metadata")
    prompts = interface.get("defaultPrompt")
    if not isinstance(prompts, list) or len(prompts) > 3:
        raise PluginInstallValidationError("interface.defaultPrompt must be a list with at most 3 entries")
    too_long = [prompt for prompt in prompts if not isinstance(prompt, str) or len(prompt) > 128]
    if too_long:
        raise PluginInstallValidationError("interface.defaultPrompt entries must be strings at most 128 characters")
    return {"name": manifest["name"], "version": manifest.get("version"), "display_name": interface.get("displayName")}


def iter_payload_entries(plugin_root: Path) -> list[Path]:
    return sorted(plugin_root.rglob("*"))


def transient_payload_reason(relative_path: Path) -> str | None:
    for part in relative_path.parts:
        if part in TRANSIENT_PAYLOAD_DIR_NAMES:
            return f"transient cache directory {part}"
    name = relative_path.name
    if name in TRANSIENT_PAYLOAD_FILE_NAMES:
        return f"transient file {name}"
    if name.endswith("~"):
        return "editor backup file"
    if relative_path.suffix in TRANSIENT_PAYLOAD_SUFFIXES:
        return f"transient file suffix {relative_path.suffix}"
    return None


def validate_payload_inventory(plugin_root: Path) -> dict[str, Any]:
    files: list[Path] = []
    symlink_entries: list[str] = []
    unsupported_entries: list[str] = []
    unexpected_dirs: list[str] = []
    transient_artifacts: list[str] = []
    for path in iter_payload_entries(plugin_root):
        relative_path = path.relative_to(plugin_root)
        reason = transient_payload_reason(relative_path)
        if reason is not None:
            transient_artifacts.append(f"{relative_path} ({reason})")
        if path.is_symlink():
            symlink_entries.append(relative_path.as_posix())
            continue
        if path.is_dir():
            if relative_path.as_posix() not in EXPECTED_PAYLOAD_DIRS:
                unexpected_dirs.append(relative_path.as_posix())
            continue
        if path.is_file():
            files.append(path)
            continue
        unsupported_entries.append(relative_path.as_posix())
    if transient_artifacts:
        raise PluginInstallValidationError(
            "transient payload artifact(s) found: " + ", ".join(sorted(transient_artifacts))
        )
    if symlink_entries:
        raise PluginInstallValidationError(f"symlink payload entry not allowed: {sorted(symlink_entries)}")
    if unsupported_entries:
        raise PluginInstallValidationError(f"unsupported payload entry type(s): {sorted(unsupported_entries)}")
    if unexpected_dirs:
        raise PluginInstallValidationError(f"unexpected packaged payload directories: {sorted(unexpected_dirs)}")
    relative_files = [path.relative_to(plugin_root).as_posix() for path in files]
    unexpected_files = sorted(set(relative_files) - EXPECTED_PAYLOAD_FILES)
    if unexpected_files:
        raise PluginInstallValidationError(f"unexpected packaged payload file(s): {unexpected_files}")
    missing_files = sorted(EXPECTED_PAYLOAD_FILES - set(relative_files))
    if missing_files:
        raise PluginInstallValidationError(f"missing packaged payload file(s): {missing_files}")
    return {
        "file_count": len(files),
        "files": relative_files,
        "matches_expected_payload": True,
    }


def validate_plugin_payload(plugin_root: Path) -> dict[str, Any]:
    inventory = validate_payload_inventory(plugin_root)
    skill_root = (plugin_root / "skills" / "arbor").resolve()
    if not (skill_root / "SKILL.md").is_file():
        raise PluginInstallValidationError("packaged arbor skill is missing SKILL.md")
    hooks_path = plugin_root / "hooks.json"
    hooks_config = read_json_object(hooks_path)
    hooks = hooks_config.get("hooks")
    if not isinstance(hooks, list):
        raise PluginInstallValidationError("plugin hooks.json must include hooks list")
    if len(hooks) != len(REQUIRED_HOOK_IDS):
        raise PluginInstallValidationError(f"packaged hooks must contain exactly {len(REQUIRED_HOOK_IDS)} entries")
    hook_ids: list[str] = []
    for index, hook in enumerate(hooks):
        if not isinstance(hook, dict):
            raise PluginInstallValidationError(f"hook entry must be an object at index {index}")
        hook_id = hook.get("id")
        if not isinstance(hook_id, str):
            raise PluginInstallValidationError(f"hook entry must include string id at index {index}")
        hook_ids.append(hook_id)
    duplicate_hook_ids = sorted({hook_id for hook_id in hook_ids if hook_ids.count(hook_id) > 1})
    if duplicate_hook_ids:
        raise PluginInstallValidationError(f"duplicate packaged hook ids: {duplicate_hook_ids}")
    if set(hook_ids) != REQUIRED_HOOK_IDS:
        raise PluginInstallValidationError(f"packaged hooks mismatch: {sorted(hook_ids)}")
    scripts: list[str] = []
    for hook in hooks:
        entrypoint = hook.get("entrypoint")
        if not isinstance(entrypoint, dict):
            raise PluginInstallValidationError(f"hook {hook.get('id')} missing entrypoint")
        if entrypoint.get("type") != "skill-script":
            raise PluginInstallValidationError(f"hook {hook.get('id')} must use skill-script entrypoint")
        if entrypoint.get("skill") != "arbor":
            raise PluginInstallValidationError(f"hook {hook.get('id')} must target arbor skill")
        script = entrypoint.get("script")
        if not isinstance(script, str):
            raise PluginInstallValidationError(f"hook {hook.get('id')} script must be a string")
        script_path = (skill_root / script).resolve()
        if script_path != skill_root and skill_root not in script_path.parents:
            raise PluginInstallValidationError(f"hook script escapes packaged skill root: {script}")
        if script_path.suffix != ".py":
            raise PluginInstallValidationError(f"hook script must be a Python file: {script}")
        if not script_path.is_file():
            raise PluginInstallValidationError(f"hook script missing in packaged skill: {script}")
        scripts.append(script)
    return {"hook_ids": sorted(hook_ids), "scripts": sorted(scripts), "inventory": inventory}


def run_plugin_smoke(plugin_root: Path) -> dict[str, Any]:
    skill_root = plugin_root / "skills" / "arbor"
    init_script = skill_root / "scripts" / "init_project_memory.py"
    with tempfile.TemporaryDirectory() as tmp:
        project_root = Path(tmp) / "project"
        project_root.mkdir()
        pycache_root = Path(tmp) / "pycache"
        smoke_env = dict(os.environ)
        smoke_env["PYTHONPYCACHEPREFIX"] = str(pycache_root)
        proc = subprocess.run(
            [sys.executable, str(init_script), "--root", str(project_root)],
            cwd=plugin_root,
            env=smoke_env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if proc.returncode != 0:
            raise PluginInstallValidationError(f"packaged skill smoke failed: {proc.stderr}")
        if not (project_root / "AGENTS.md").is_file() or not (project_root / ".codex" / "memory.md").is_file():
            raise PluginInstallValidationError("packaged skill smoke did not initialize AGENTS.md and .codex/memory.md")

        hook_smokes = [
            ("arbor.session_startup_context", "scripts/run_session_startup_hook.py", "# Project Startup Context"),
            ("arbor.in_session_memory_hygiene", "scripts/run_memory_hygiene_hook.py", "# Memory Hygiene Context"),
            ("arbor.goal_constraint_drift", "scripts/run_agents_guide_drift_hook.py", "# AGENTS Guide Drift Context"),
        ]
        hook_results: list[dict[str, Any]] = []
        for hook_id, script, expected_header in hook_smokes:
            hook_proc = subprocess.run(
                [sys.executable, str(skill_root / script), "--root", str(project_root)],
                cwd=plugin_root,
                env=smoke_env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if hook_proc.returncode != 0:
                raise PluginInstallValidationError(f"packaged hook smoke failed for {hook_id}: {hook_proc.stderr}")
            if expected_header not in hook_proc.stdout:
                raise PluginInstallValidationError(f"packaged hook smoke missing header for {hook_id}")
            hook_results.append({"hook_id": hook_id, "returncode": hook_proc.returncode})
        return {
            "returncode": proc.returncode,
            "initialized": ["AGENTS.md", ".codex/memory.md"],
            "hook_smokes": hook_results,
        }


def run_codex_marketplace_install_probe(repo_root: Path, codex_bin: Path = CODEX_BIN) -> dict[str, Any]:
    if not codex_bin.is_file():
        raise PluginInstallValidationError(f"codex binary not found: {codex_bin}")
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp) / "home"
        home.mkdir()
        proc = subprocess.run(
            [str(codex_bin), "plugin", "marketplace", "add", str(repo_root)],
            cwd=repo_root,
            env={"HOME": str(home), "PATH": "/usr/bin:/bin:/usr/sbin:/sbin"},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if proc.returncode != 0:
            raise PluginInstallValidationError(
                "codex marketplace add failed: "
                f"stdout={proc.stdout.strip()} stderr={proc.stderr.strip()}"
            )
        config_path = home / ".codex" / "config.toml"
        if not config_path.is_file():
            raise PluginInstallValidationError("codex marketplace add did not create isolated config.toml")
        config_text = config_path.read_text(encoding="utf-8")
        if "arbor-local" not in config_text:
            raise PluginInstallValidationError("isolated Codex config does not include arbor-local marketplace")
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "config_created": str(config_path),
        }


def validate_plugin_install(repo_root: Path, include_codex_probe: bool = False) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    plugin_root = repo_root / "plugins" / "arbor"
    return {
        "marketplace": validate_marketplace(repo_root),
        "manifest": validate_manifest(plugin_root),
        "payload": validate_plugin_payload(plugin_root),
        "packaged_skill_smoke": run_plugin_smoke(plugin_root),
        "codex_marketplace_probe": (
            run_codex_marketplace_install_probe(repo_root)
            if include_codex_probe
            else {"skipped": True}
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root containing the local Arbor marketplace.")
    parser.add_argument("--codex-probe", action="store_true", help="Run isolated Codex CLI marketplace add probe.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = validate_plugin_install(args.root, include_codex_probe=args.codex_probe)
    except PluginInstallValidationError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
