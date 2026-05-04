#!/usr/bin/env python3
"""Probe Arbor as an installed Codex plugin in an isolated runtime."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CODEX_BIN = Path("/Applications/Codex.app/Contents/Resources/codex")
PLUGIN_ID = 'arbor@arbor-local'
MARKETPLACE_NAME = "arbor-local"
PLUGIN_NAME = "arbor"
REQUIRED_HOOK_IDS = {
    "arbor.session_startup_context",
    "arbor.in_session_memory_hygiene",
    "arbor.goal_constraint_drift",
}
EXPECTED_FILES = [
    "AGENTS.md",
    ".codex/memory.md",
    ".codex/hooks.json",
]
DEFAULT_PROMPT = (
    "Use $arbor to initialize Arbor in this project and register project hooks. "
    "Use python3 if you execute bundled scripts. Reply with ARBOR_RUNTIME_PROBE_OK "
    "after AGENTS.md, .codex/memory.md, and .codex/hooks.json exist."
)
AUTH_FILES = ("auth.json",)


class PluginRuntimeProbeError(ValueError):
    """Raised when the runtime probe cannot be configured."""


def isolated_codex_env(home: Path) -> dict[str, str]:
    return {
        "HOME": str(home),
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
    }


def run_command(args: list[str], cwd: Path, env: dict[str, str], timeout_seconds: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        env=env,
        text=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout_seconds,
    )


def ensure_codex_binary(codex_bin: Path) -> None:
    if not codex_bin.is_file():
        raise PluginRuntimeProbeError(f"codex binary not found: {codex_bin}")


def add_marketplace(repo_root: Path, home: Path, codex_bin: Path, timeout_seconds: int) -> dict[str, Any]:
    proc = run_command(
        [str(codex_bin), "plugin", "marketplace", "add", str(repo_root)],
        cwd=repo_root,
        env=isolated_codex_env(home),
        timeout_seconds=timeout_seconds,
    )
    config_path = home / ".codex" / "config.toml"
    status = "ok" if proc.returncode == 0 and config_path.is_file() else "failed"
    return {
        "status": status,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "config_path": str(config_path),
    }


def enable_arbor_plugin(home: Path) -> dict[str, Any]:
    config_path = home / ".codex" / "config.toml"
    if not config_path.is_file():
        return {"status": "failed", "reason": "missing isolated Codex config.toml"}
    config_text = config_path.read_text(encoding="utf-8")
    if "[marketplaces.arbor-local]" not in config_text:
        return {"status": "failed", "reason": "missing arbor-local marketplace"}
    plugin_header = f'[plugins."{PLUGIN_ID}"]'
    if plugin_header not in config_text:
        suffix = "" if config_text.endswith("\n") else "\n"
        config_text = f'{config_text}{suffix}\n{plugin_header}\nenabled = true\n'
        config_path.write_text(config_text, encoding="utf-8")
    return {
        "status": "ok",
        "plugin_id": PLUGIN_ID,
        "config_path": str(config_path),
    }


def trust_project(home: Path, project_root: Path) -> dict[str, Any]:
    config_path = home / ".codex" / "config.toml"
    if not config_path.is_file():
        return {"status": "failed", "reason": "missing isolated Codex config.toml"}
    config_text = config_path.read_text(encoding="utf-8")
    project_header = f'[projects."{project_root.resolve()}"]'
    if project_header not in config_text:
        suffix = "" if config_text.endswith("\n") else "\n"
        config_text = f'{config_text}{suffix}\n{project_header}\ntrust_level = "trusted"\n'
        config_path.write_text(config_text, encoding="utf-8")
    return {
        "status": "ok",
        "project_root": str(project_root.resolve()),
        "config_path": str(config_path),
    }


def read_json_file(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise PluginRuntimeProbeError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise PluginRuntimeProbeError(f"cannot parse {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise PluginRuntimeProbeError(f"expected JSON object in {path}")
    return data


def resolve_marketplace_plugin_root(
    repo_root: Path,
    marketplace_name: str = MARKETPLACE_NAME,
    plugin_name: str = PLUGIN_NAME,
) -> Path:
    marketplace_path = repo_root / ".agents" / "plugins" / "marketplace.json"
    marketplace = read_json_file(marketplace_path)
    if marketplace.get("name") != marketplace_name:
        raise PluginRuntimeProbeError(f"unexpected marketplace name in {marketplace_path}: {marketplace.get('name')}")
    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list):
        raise PluginRuntimeProbeError(f"marketplace plugins must be a list: {marketplace_path}")
    for plugin in plugins:
        if not isinstance(plugin, dict) or plugin.get("name") != plugin_name:
            continue
        source = plugin.get("source")
        if not isinstance(source, dict) or source.get("source") != "local":
            raise PluginRuntimeProbeError(f"marketplace plugin {plugin_name} must use a local source")
        relative_path = source.get("path")
        if not isinstance(relative_path, str):
            raise PluginRuntimeProbeError(f"marketplace plugin {plugin_name} source.path must be a string")
        plugin_root = (repo_root / relative_path).resolve()
        if not plugin_root.is_dir():
            raise PluginRuntimeProbeError(f"plugin source path is not a directory: {plugin_root}")
        return plugin_root
    raise PluginRuntimeProbeError(f"plugin {plugin_name} not found in marketplace {marketplace_name}")


def plugin_manifest_version(plugin_root: Path) -> str:
    manifest = read_json_file(plugin_root / ".codex-plugin" / "plugin.json")
    version = manifest.get("version")
    if not isinstance(version, str) or not version.strip():
        raise PluginRuntimeProbeError(f"plugin manifest must include a version: {plugin_root}")
    return version


def materialize_local_plugin_cache(
    repo_root: Path,
    home: Path,
    marketplace_name: str = MARKETPLACE_NAME,
    plugin_name: str = PLUGIN_NAME,
) -> dict[str, Any]:
    plugin_root = resolve_marketplace_plugin_root(repo_root, marketplace_name, plugin_name)
    version = plugin_manifest_version(plugin_root)
    cache_root = home / ".codex" / "plugins" / "cache" / marketplace_name / plugin_name
    cache_entry = cache_root / version
    if cache_entry.exists():
        shutil.rmtree(cache_entry)
    cache_root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(plugin_root, cache_entry)
    manifest_path = cache_entry / ".codex-plugin" / "plugin.json"
    if not manifest_path.is_file():
        return {
            "status": "failed",
            "reason": "materialized plugin cache entry is missing plugin.json",
            "cache_entry": str(cache_entry),
        }
    return {
        "status": "ok",
        "plugin_id": f"{plugin_name}@{marketplace_name}",
        "version": version,
        "source": str(plugin_root),
        "cache_entry": str(cache_entry),
    }


def copy_runtime_auth(auth_source_home: Path | None, target_home: Path) -> dict[str, Any]:
    if auth_source_home is None:
        return {"status": "skipped", "reason": "no auth source home provided"}
    source_codex = auth_source_home / ".codex"
    target_codex = target_home / ".codex"
    copied_files: list[str] = []
    missing_files: list[str] = []
    target_codex.mkdir(parents=True, exist_ok=True)
    for filename in AUTH_FILES:
        source = source_codex / filename
        if not source.is_file():
            missing_files.append(filename)
            continue
        shutil.copy2(source, target_codex / filename)
        copied_files.append(filename)
    if missing_files:
        return {
            "status": "failed",
            "reason": "missing auth file(s)",
            "source_home": str(auth_source_home),
            "copied_files": copied_files,
            "missing_files": missing_files,
        }
    return {
        "status": "ok",
        "source_home": str(auth_source_home),
        "copied_files": copied_files,
    }


def classify_exec_failure(proc: subprocess.CompletedProcess[str]) -> str:
    combined = f"{proc.stdout}\n{proc.stderr}".lower()
    if "failed to lookup address information" in combined or "could not resolve host" in combined:
        return "network_unavailable"
    if "api key" in combined or "not logged in" in combined or "login" in combined or "authentication" in combined:
        return "auth_required"
    if "plugin" in combined and ("failed" in combined or "error" in combined):
        return "plugin_runtime_error"
    return "runtime_failed"


def read_registered_arbor_hooks(project_root: Path) -> tuple[set[str], str | None]:
    hooks_path = project_root / ".codex" / "hooks.json"
    try:
        hooks_config = json.loads(hooks_path.read_text(encoding="utf-8"))
    except OSError as exc:
        return set(), f"cannot read .codex/hooks.json: {exc}"
    except json.JSONDecodeError as exc:
        return set(), f"cannot parse .codex/hooks.json: {exc}"
    hooks = hooks_config.get("hooks")
    if not isinstance(hooks, list):
        return set(), ".codex/hooks.json does not contain a hooks list"
    hook_ids = {
        hook.get("id")
        for hook in hooks
        if isinstance(hook, dict) and hook.get("owner") == "arbor" and isinstance(hook.get("id"), str)
    }
    return hook_ids, None


def existing_expected_files(project_root: Path) -> list[str]:
    return [path for path in EXPECTED_FILES if (project_root / path).is_file()]


def installed_plugin_injection_seen(home: Path, stdout: str, stderr: str) -> bool:
    combined = f"{stdout}\n{stderr}"
    cache_root = home / ".codex" / "plugins" / "cache" / MARKETPLACE_NAME / PLUGIN_NAME
    return str(cache_root) in combined and "skills/arbor/SKILL.md" in combined


def run_exec_probe(
    project_root: Path,
    home: Path,
    codex_bin: Path,
    prompt: str,
    timeout_seconds: int,
    sandbox_mode: str = "workspace-write",
) -> dict[str, Any]:
    project_root.mkdir(parents=True, exist_ok=True)
    preexisting_files = existing_expected_files(project_root)
    if preexisting_files:
        return {
            "status": "failed",
            "reason": "probe project must not contain pre-existing Arbor side-effect files",
            "returncode": None,
            "marker_seen": False,
            "injection_seen": False,
            "preexisting_files": preexisting_files,
            "created_files": preexisting_files,
            "missing_files": [path for path in EXPECTED_FILES if path not in preexisting_files],
            "registered_hook_ids": [],
            "missing_hook_ids": sorted(REQUIRED_HOOK_IDS),
            "hook_error": None,
            "stdout": "",
            "stderr": "",
        }
    try:
        proc = run_command(
            [
                str(codex_bin),
                "exec",
                "--ephemeral",
                "--json",
                "-s",
                sandbox_mode,
                "--skip-git-repo-check",
                "--cd",
                str(project_root),
                prompt,
            ],
            cwd=project_root,
            env=isolated_codex_env(home),
            timeout_seconds=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "blocked",
            "reason": "timeout",
            "returncode": None,
            "marker_seen": False,
            "injection_seen": installed_plugin_injection_seen(
                home,
                exc.stdout if isinstance(exc.stdout, str) else "",
                exc.stderr if isinstance(exc.stderr, str) else "",
            ),
            "preexisting_files": [],
            "created_files": existing_expected_files(project_root),
            "missing_files": [path for path in EXPECTED_FILES if not (project_root / path).is_file()],
            "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "").strip() if isinstance(exc.stderr, str) else "",
        }
    created_files = [path for path in EXPECTED_FILES if (project_root / path).is_file()]
    missing_files = [path for path in EXPECTED_FILES if path not in created_files]
    marker_seen = "ARBOR_RUNTIME_PROBE_OK" in proc.stdout
    injection_seen = installed_plugin_injection_seen(home, proc.stdout, proc.stderr)
    hook_ids, hook_error = read_registered_arbor_hooks(project_root) if ".codex/hooks.json" in created_files else (set(), None)
    missing_hook_ids = sorted(REQUIRED_HOOK_IDS - hook_ids)
    hooks_registered = not hook_error and not missing_hook_ids
    if proc.returncode == 0 and marker_seen and injection_seen and not missing_files and hooks_registered:
        status = "passed"
        reason = "plugin skill initialized project files and emitted the probe marker"
    else:
        status = "blocked" if proc.returncode != 0 else "failed"
        if proc.returncode != 0:
            reason = classify_exec_failure(proc)
        elif missing_files:
            reason = "expected plugin side effects were not observed"
        elif missing_hook_ids or hook_error:
            reason = "expected Arbor hook registrations were not observed"
        elif not injection_seen:
            reason = "expected installed Arbor skill injection was not observed"
        elif not marker_seen:
            reason = "probe marker was not emitted"
        else:
            reason = "expected plugin side effects were not observed"
    return {
        "status": status,
        "reason": reason,
        "returncode": proc.returncode,
        "marker_seen": marker_seen,
        "injection_seen": injection_seen,
        "preexisting_files": [],
        "created_files": created_files,
        "missing_files": missing_files,
        "registered_hook_ids": sorted(hook_ids),
        "missing_hook_ids": missing_hook_ids,
        "hook_error": hook_error,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def run_plugin_runtime_probe(
    repo_root: Path,
    codex_bin: Path = CODEX_BIN,
    attempt_exec: bool = False,
    project_root: Path | None = None,
    prompt: str = DEFAULT_PROMPT,
    timeout_seconds: int = 60,
    auth_source_home: Path | None = None,
    temp_parent: Path | None = None,
    sandbox_mode: str = "workspace-write",
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    ensure_codex_binary(codex_bin)
    temp_parent = temp_parent.resolve() if temp_parent is not None else repo_root
    with tempfile.TemporaryDirectory(prefix="arbor-runtime-", dir=temp_parent) as tmp:
        home = Path(tmp) / "home"
        home.mkdir()
        project = project_root or (Path(tmp) / "project")
        marketplace = add_marketplace(repo_root, home, codex_bin, timeout_seconds)
        plugin_cache = (
            materialize_local_plugin_cache(repo_root, home)
            if marketplace["status"] == "ok"
            else {"status": "skipped", "reason": "marketplace add failed"}
        )
        auth = (
            copy_runtime_auth(auth_source_home.expanduser().resolve(), home)
            if marketplace["status"] == "ok" and auth_source_home is not None
            else copy_runtime_auth(None, home)
        )
        plugin_enable = (
            enable_arbor_plugin(home)
            if marketplace["status"] == "ok" and plugin_cache["status"] == "ok"
            else {"status": "skipped", "reason": "plugin cache unavailable"}
        )
        project_trust = trust_project(home, project)
        auth_ready = auth_source_home is None or auth["status"] == "ok"
        exec_probe = (
            run_exec_probe(project, home, codex_bin, prompt, timeout_seconds, sandbox_mode=sandbox_mode)
            if attempt_exec and plugin_enable["status"] == "ok" and project_trust["status"] == "ok" and auth_ready
            else {
                "status": "skipped",
                "reason": (
                    "auth copy failed"
                    if attempt_exec and plugin_enable["status"] == "ok" and not auth_ready
                    else "project trust failed"
                    if attempt_exec and plugin_enable["status"] == "ok" and project_trust["status"] != "ok"
                    else "use --attempt-exec to run codex exec"
                ),
            }
        )
        return {
            "repo_root": str(repo_root),
            "project_root": str(project),
            "isolated_home": str(home),
            "marketplace": marketplace,
            "plugin_cache": plugin_cache,
            "auth": auth,
            "plugin_enable": plugin_enable,
            "project_trust": project_trust,
            "exec_probe": exec_probe,
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root containing the local Arbor marketplace.")
    parser.add_argument("--codex-bin", type=Path, default=CODEX_BIN, help="Codex CLI binary to probe.")
    parser.add_argument("--attempt-exec", action="store_true", help="Attempt a real codex exec run against the plugin.")
    parser.add_argument("--project-root", type=Path, help="Project root for the exec probe. Defaults to a temporary project.")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="Prompt used for the exec probe.")
    parser.add_argument("--timeout", type=int, default=60, help="Per-command timeout in seconds.")
    parser.add_argument(
        "--temp-parent",
        type=Path,
        help="Directory where the isolated HOME and default project are created. Defaults to the repo root.",
    )
    parser.add_argument(
        "--sandbox",
        default="workspace-write",
        choices=["read-only", "workspace-write", "danger-full-access"],
        help="Sandbox mode passed to codex exec for the runtime probe.",
    )
    parser.add_argument(
        "--auth-source-home",
        type=Path,
        help="Optional home directory whose .codex/auth.json is copied into the isolated runtime HOME.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = run_plugin_runtime_probe(
            repo_root=args.root,
            codex_bin=args.codex_bin,
            attempt_exec=args.attempt_exec,
            project_root=args.project_root,
            prompt=args.prompt,
            timeout_seconds=args.timeout,
            auth_source_home=args.auth_source_home,
            temp_parent=args.temp_parent,
            sandbox_mode=args.sandbox,
        )
    except (PluginRuntimeProbeError, subprocess.TimeoutExpired) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
