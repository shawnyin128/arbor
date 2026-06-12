#!/usr/bin/env python3
"""Smoke generated Arbor project hook wrappers in controlled local fixtures."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

SCRIPT_ROOT = Path(__file__).resolve().parent
PLUGIN_ROOT = Path(__file__).resolve().parents[3]
CODEX_CACHE_SUFFIX = "plugins/cache/arbor/arbor"
CLAUDE_CACHE_SUFFIX = "plugins/cache/arbor/arbor"
DEFAULT_WRAPPER_TIMEOUT_SECONDS = 30.0
TIMEOUT_ENV_VAR = "ARBOR_PROJECT_WRAPPER_SMOKE_TIMEOUT_SECONDS"
RELEASE_VERSION_PATTERN = re.compile(r"\d+\.\d+\.\d+")


def subprocess_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if extra:
        env.update(extra)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def wrapper_timeout_seconds() -> float:
    raw = os.environ.get(TIMEOUT_ENV_VAR)
    if not raw:
        return DEFAULT_WRAPPER_TIMEOUT_SECONDS
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_WRAPPER_TIMEOUT_SECONDS
    if value <= 0:
        return DEFAULT_WRAPPER_TIMEOUT_SECONDS
    return value


def run_command(args: list[str], *, input_text: str | None = None, env: dict[str, str] | None = None) -> tuple[int, str]:
    timeout = wrapper_timeout_seconds()
    try:
        proc = subprocess.run(
            args,
            input=input_text,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=subprocess_env(env),
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout if isinstance(exc.stdout, str) else ""
        detail = f": {output.strip()}" if output.strip() else ""
        return 124, f"command timed out after {timeout:g}s: {' '.join(args)}{detail}"
    except OSError as exc:
        return 127, f"command failed to start: {' '.join(args)}: {exc}"
    return proc.returncode, proc.stdout


def record_check(failures: list[str], condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def manifest_version(path: Path) -> str:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except OSError as exc:
        raise RuntimeError(f"could not read manifest {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON manifest {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"manifest must be a JSON object: {path}")
    version = data.get("version")
    if not isinstance(version, str) or not version:
        raise RuntimeError(f"manifest must declare a version: {path}")
    return version


def source_manifest_version(plugin_root: Path) -> str:
    codex_version = manifest_version(plugin_root / ".codex-plugin" / "plugin.json")
    claude_version = manifest_version(plugin_root / ".claude-plugin" / "plugin.json")
    if codex_version != claude_version:
        raise RuntimeError(
            f"Codex source version {codex_version} does not match Claude source version {claude_version}"
        )
    if RELEASE_VERSION_PATTERN.fullmatch(codex_version) is None:
        raise RuntimeError(f"source manifest version must be a release version like X.Y.Z: {codex_version}")
    return codex_version


def next_patch_version(version: str) -> str:
    major, minor, patch = (int(part) for part in version.split("."))
    return f"{major}.{minor}.{patch + 1}"


def valid_agents() -> str:
    return (
        "# Agent Guide\n\n"
        "## Project Goal\n\n"
        "This fixture validates Arbor project wrapper smoke behavior.\n\n"
        "## Project Constraints\n\n"
        "- Normal startup context is loaded by the Arbor SessionStart hook.\n"
        "- Keep fixture state local.\n\n"
        "## Project Map\n\n"
        "- `src/`: fixture source.\n"
    )


def prepare_project(root: Path, plugin_root: Path, failures: list[str]) -> None:
    code, output = run_command(["git", "init", str(root)])
    record_check(failures, code == 0, f"could not initialize smoke git project: {output.strip()}")
    (root / "README.md").write_text("# Wrapper Smoke\n", encoding="utf-8")
    (root / "AGENTS.md").write_text(valid_agents(), encoding="utf-8")
    (root / ".arbor").mkdir()
    (root / ".arbor" / "memory.md").write_text("# Session Memory\n\n## In-flight\n\n- None.\n", encoding="utf-8")
    code, output = run_command(
        [
            sys.executable,
            str(SCRIPT_ROOT / "register_project_hooks.py"),
            "--root",
            str(root),
            "--runtime",
            "both",
        ]
    )
    record_check(failures, code == 0, f"register_project_hooks.py failed during wrapper smoke: {output.strip()}")


def copy_plugin_cache(plugin_root: Path, cache_root: Path) -> None:
    if cache_root.exists():
        shutil.rmtree(cache_root)
    shutil.copytree(
        plugin_root,
        cache_root,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", ".mypy_cache"),
    )


def write_broken_cache_adapter(cache_root: Path, adapter_name: str) -> None:
    hook_dir = cache_root / "hooks"
    hook_dir.mkdir(parents=True, exist_ok=True)
    (hook_dir / adapter_name).write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "print('broken smoke cache selected', file=sys.stderr)\n"
        "raise SystemExit(91)\n",
        encoding="utf-8",
    )


def fake_home_env(home: Path) -> dict[str, str]:
    return {
        "HOME": str(home),
        "USERPROFILE": str(home),
        "ARBOR_PLUGIN_ROOT": "",
        "PLUGIN_ROOT": "",
        "CODEX_PLUGIN_ROOT": "",
        "CLAUDE_PLUGIN_ROOT": "",
    }


def plugin_root_env(plugin_root: Path) -> dict[str, str]:
    value = str(plugin_root)
    return {
        "ARBOR_PLUGIN_ROOT": value,
        "PLUGIN_ROOT": value,
        "CODEX_PLUGIN_ROOT": value,
        "CLAUDE_PLUGIN_ROOT": value,
    }


def run_wrapper(wrapper: Path, payload: dict[str, Any], env: dict[str, str]) -> tuple[int, str]:
    return run_command(
        [sys.executable, str(wrapper)],
        input_text=json.dumps(payload),
        env=env,
    )


def assert_startup_context(failures: list[str], label: str, wrapper: Path, root: Path, env: dict[str, str]) -> None:
    code, output = run_wrapper(wrapper, {"cwd": str(root), "source": "startup"}, env)
    record_check(failures, code == 0, f"{label} SessionStart wrapper exited {code}: {output.strip()}")
    record_check(failures, "# Project Startup Context" in output, f"{label} SessionStart wrapper did not emit startup context")


def assert_stop_allows(failures: list[str], label: str, wrapper: Path, root: Path, env: dict[str, str]) -> None:
    code, output = run_wrapper(wrapper, {"cwd": str(root), "read_only": True}, env)
    record_check(failures, code == 0, f"{label} Stop wrapper exited {code}: {output.strip()}")
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        data = {}
        failures.append(f"{label} Stop wrapper did not emit valid JSON: {output.strip()}")
    record_check(failures, data.get("continue") is True, f"{label} Stop wrapper did not allow stop")


def assert_missing_cache_soft_skip(failures: list[str], root: Path, home: Path) -> None:
    env = fake_home_env(home)
    code, output = run_wrapper(root / ".codex" / "hooks" / "arbor-session-start", {"cwd": str(root), "source": "startup"}, env)
    record_check(failures, code == 0 and output.strip() == "", "Codex SessionStart wrapper must stay quiet when cache is missing")
    assert_stop_allows(
        failures,
        "Claude missing-cache",
        root / ".claude" / "hooks" / "arbor-stop-memory-hygiene",
        root,
        env,
    )


def assert_startup_quiet(failures: list[str], label: str, wrapper: Path, root: Path, env: dict[str, str]) -> None:
    code, output = run_wrapper(wrapper, {"cwd": str(root), "source": "startup"}, env)
    record_check(failures, code == 0, f"{label} SessionStart wrapper exited {code}: {output.strip()}")
    record_check(failures, output.strip() == "", f"{label} SessionStart wrapper must stay quiet")


def assert_non_release_cache_ignored(failures: list[str], plugin_root: Path, root: Path, home: Path) -> None:
    copy_plugin_cache(plugin_root, home / ".codex" / CODEX_CACHE_SUFFIX / "dev")
    copy_plugin_cache(plugin_root, home / ".claude" / CLAUDE_CACHE_SUFFIX / "dev")
    env = fake_home_env(home)
    assert_startup_quiet(
        failures,
        "Codex non-release cache",
        root / ".codex" / "hooks" / "arbor-session-start",
        root,
        env,
    )
    assert_startup_quiet(
        failures,
        "Claude non-release cache",
        root / ".claude" / "hooks" / "arbor-session-start",
        root,
        env,
    )


def assert_incomplete_higher_cache_fallback(
    failures: list[str],
    plugin_root: Path,
    root: Path,
    home: Path,
    version: str,
) -> None:
    higher_version = next_patch_version(version)
    copy_plugin_cache(plugin_root, home / ".codex" / CODEX_CACHE_SUFFIX / version)
    copy_plugin_cache(plugin_root, home / ".claude" / CLAUDE_CACHE_SUFFIX / version)
    write_broken_cache_adapter(home / ".codex" / CODEX_CACHE_SUFFIX / higher_version, "session-start")
    write_broken_cache_adapter(home / ".claude" / CLAUDE_CACHE_SUFFIX / higher_version, "session-start")
    env = fake_home_env(home)
    assert_startup_context(
        failures,
        "Codex incomplete higher cache",
        root / ".codex" / "hooks" / "arbor-session-start",
        root,
        env,
    )
    assert_startup_context(
        failures,
        "Claude incomplete higher cache",
        root / ".claude" / "hooks" / "arbor-session-start",
        root,
        env,
    )


def assert_bad_env_root_fallback(
    failures: list[str],
    plugin_root: Path,
    root: Path,
    home: Path,
    version: str,
) -> None:
    copy_plugin_cache(plugin_root, home / ".codex" / CODEX_CACHE_SUFFIX / version)
    copy_plugin_cache(plugin_root, home / ".claude" / CLAUDE_CACHE_SUFFIX / version)
    bad_root = home / "bad-env-plugin-root"
    write_broken_cache_adapter(bad_root, "session-start")
    env = fake_home_env(home)
    for name in ("ARBOR_PLUGIN_ROOT", "PLUGIN_ROOT", "CODEX_PLUGIN_ROOT", "CLAUDE_PLUGIN_ROOT"):
        env[name] = str(bad_root)
    assert_startup_context(
        failures,
        "Codex bad env-root fallback",
        root / ".codex" / "hooks" / "arbor-session-start",
        root,
        env,
    )
    assert_startup_context(
        failures,
        "Claude bad env-root fallback",
        root / ".claude" / "hooks" / "arbor-session-start",
        root,
        env,
    )


def smoke_project_wrappers(plugin_root: Path) -> list[str]:
    failures: list[str] = []
    try:
        version = source_manifest_version(plugin_root)
    except RuntimeError as exc:
        return [str(exc)]
    with tempfile.TemporaryDirectory(prefix="arbor-project-wrapper-smoke-") as tmp:
        root = Path(tmp) / "project"
        root.mkdir()
        prepare_project(root, plugin_root, failures)

        explicit_env = plugin_root_env(plugin_root)
        assert_startup_context(
            failures,
            "Codex explicit plugin-root",
            root / ".codex" / "hooks" / "arbor-session-start",
            root,
            explicit_env,
        )
        assert_startup_context(
            failures,
            "Claude explicit plugin-root",
            root / ".claude" / "hooks" / "arbor-session-start",
            root,
            explicit_env,
        )
        assert_stop_allows(
            failures,
            "Codex explicit plugin-root",
            root / ".codex" / "hooks" / "arbor-stop-memory-hygiene",
            root,
            explicit_env,
        )
        assert_stop_allows(
            failures,
            "Claude explicit plugin-root",
            root / ".claude" / "hooks" / "arbor-stop-memory-hygiene",
            root,
            explicit_env,
        )

        fake_home = Path(tmp) / "fake-home"
        copy_plugin_cache(plugin_root, fake_home / ".codex" / CODEX_CACHE_SUFFIX / version)
        copy_plugin_cache(plugin_root, fake_home / ".claude" / CLAUDE_CACHE_SUFFIX / version)
        cache_env = fake_home_env(fake_home)
        assert_startup_context(
            failures,
            "Codex installed-cache",
            root / ".codex" / "hooks" / "arbor-session-start",
            root,
            cache_env,
        )
        assert_startup_context(
            failures,
            "Claude installed-cache",
            root / ".claude" / "hooks" / "arbor-session-start",
            root,
            cache_env,
        )
        assert_stop_allows(
            failures,
            "Codex installed-cache",
            root / ".codex" / "hooks" / "arbor-stop-memory-hygiene",
            root,
            cache_env,
        )
        assert_stop_allows(
            failures,
            "Claude installed-cache",
            root / ".claude" / "hooks" / "arbor-stop-memory-hygiene",
            root,
            cache_env,
        )

        assert_missing_cache_soft_skip(failures, root, Path(tmp) / "missing-cache-home")
        assert_non_release_cache_ignored(failures, plugin_root, root, Path(tmp) / "non-release-cache-home")
        assert_incomplete_higher_cache_fallback(
            failures,
            plugin_root,
            root,
            Path(tmp) / "incomplete-higher-cache-home",
            version,
        )
        assert_bad_env_root_fallback(
            failures,
            plugin_root,
            root,
            Path(tmp) / "bad-env-root-home",
            version,
        )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugin-root", type=Path, default=PLUGIN_ROOT, help="Arbor plugin root to smoke.")
    args = parser.parse_args()

    failures = smoke_project_wrappers(args.plugin_root.resolve())
    if failures:
        print("project wrapper smoke failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("project wrapper smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
