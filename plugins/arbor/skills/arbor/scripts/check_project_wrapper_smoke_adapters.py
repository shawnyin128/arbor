#!/usr/bin/env python3
"""Validate Arbor's project-wrapper smoke checker."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True


PLUGIN_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = PLUGIN_ROOT.parents[1]
SCRIPTS_ROOT = PLUGIN_ROOT / "skills" / "arbor" / "scripts"


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


def run_command(command: list[str], errors: list[str]) -> str:
    try:
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=bytecode_suppressed_env(),
            timeout=60,
            check=False,
        )
    except OSError as exc:
        add_error(errors, f"command failed to start: {' '.join(command)}: {exc}")
        return ""
    except subprocess.TimeoutExpired as exc:
        add_error(errors, f"command timed out: {' '.join(command)}: {exc}")
        return ""
    output = result.stdout or ""
    if result.returncode != 0:
        add_error(errors, f"command failed ({result.returncode}): {' '.join(command)}\n{output}")
    return output


def load_smoke_module(module_script: Path, errors: list[str]) -> Any | None:
    spec = importlib.util.spec_from_file_location("arbor_project_wrapper_smoke_probe", module_script)
    if spec is None or spec.loader is None:
        add_error(errors, "could not load project wrapper smoke script for resilience validation")
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_smoke_script_surface(errors: list[str]) -> None:
    module_script = SCRIPTS_ROOT / "check_project_wrapper_smoke.py"
    quality_gate = load_text(SCRIPTS_ROOT / "check_quality_gate.py", errors)
    check(errors, module_script.is_file(), "project wrapper smoke must live in its own script")
    check(
        errors,
        "check_project_wrapper_smoke.py" in quality_gate and "project wrapper smoke" in quality_gate,
        "quality gate must run project wrapper smoke as its own row",
    )
    if not module_script.is_file():
        return

    module_text = module_script.read_text(encoding="utf-8")
    check(
        errors,
        "register_project_hooks.py" in module_text,
        "project wrapper smoke must exercise generated project hook wrappers",
    )
    check(
        errors,
        "ARBOR_PLUGIN_ROOT" in module_text and "plugins/cache/arbor/arbor" in module_text.replace("\\", "/"),
        "project wrapper smoke must cover explicit plugin-root and installed-cache discovery",
    )
    check(
        errors,
        "source_manifest_version" in module_text,
        "project wrapper smoke must derive fake cache version from source manifests",
    )
    check(
        errors,
        '/ "2.0.0"' not in module_text and "/ '2.0.0'" not in module_text,
        "project wrapper smoke must not hardcode the fake cache version",
    )
    check(
        errors,
        "ARBOR_PROJECT_WRAPPER_SMOKE_TIMEOUT_SECONDS" in module_text and "wrapper_timeout_seconds" in module_text,
        "project wrapper smoke timeout must be configurable for tests and CI",
    )
    for marker, message in (
        ("assert_non_release_cache_ignored", "project wrapper smoke must cover non-release cache ignore behavior"),
        (
            "assert_incomplete_higher_cache_fallback",
            "project wrapper smoke must cover incomplete higher-version cache fallback",
        ),
        ("assert_bad_env_root_fallback", "project wrapper smoke must cover bad plugin-root env fallback"),
    ):
        check(errors, marker in module_text, message)


def validate_smoke_subprocess_resilience(errors: list[str]) -> None:
    module_script = SCRIPTS_ROOT / "check_project_wrapper_smoke.py"
    if not module_script.is_file():
        return
    module = load_smoke_module(module_script, errors)
    if module is None:
        return

    original_run = module.subprocess.run

    def raise_project_smoke_launch_failure(*_args: Any, **_kwargs: Any) -> Any:
        raise OSError("simulated project wrapper smoke launch failure")

    module.subprocess.run = raise_project_smoke_launch_failure
    try:
        try:
            launch_code, launch_output = module.run_command(["fixture"])
        except OSError as exc:
            add_error(errors, f"project wrapper smoke subprocess launch failures must not propagate: {exc}")
            launch_code, launch_output = 99, ""
    finally:
        module.subprocess.run = original_run
    check(errors, launch_code != 0, "project wrapper smoke subprocess launch failures must fail the command")
    check(
        errors,
        "failed to start" in launch_output and "simulated project wrapper smoke launch failure" in launch_output,
        "project wrapper smoke subprocess launch failures must be readable",
    )

    def raise_project_smoke_timeout(command: list[str], *_args: Any, **_kwargs: Any) -> Any:
        raise subprocess.TimeoutExpired(command, timeout=0.1)

    module.subprocess.run = raise_project_smoke_timeout
    try:
        try:
            timeout_code, timeout_output = module.run_command(["fixture"])
        except subprocess.TimeoutExpired as exc:
            add_error(errors, f"project wrapper smoke subprocess timeouts must not propagate: {exc}")
            timeout_code, timeout_output = 99, ""
    finally:
        module.subprocess.run = original_run
    check(errors, timeout_code != 0, "project wrapper smoke subprocess timeouts must fail the command")
    check(errors, "timed out" in timeout_output, "project wrapper smoke subprocess timeouts must be readable")

    original_timeout_env = os.environ.get("ARBOR_PROJECT_WRAPPER_SMOKE_TIMEOUT_SECONDS")
    os.environ["ARBOR_PROJECT_WRAPPER_SMOKE_TIMEOUT_SECONDS"] = "0.25"

    def assert_project_smoke_timeout_arg(_args: list[str], *_run_args: Any, **kwargs: Any) -> Any:
        if kwargs.get("timeout") != 0.25:
            raise AssertionError(f"expected configurable timeout 0.25, got {kwargs.get('timeout')!r}")
        return subprocess.CompletedProcess(_args, 0, "ok\n")

    module.subprocess.run = assert_project_smoke_timeout_arg
    try:
        try:
            configured_timeout_code, configured_timeout_output = module.run_command(["fixture"])
        except AssertionError as exc:
            add_error(errors, f"project wrapper smoke must pass configured timeout to subprocess.run: {exc}")
            configured_timeout_code, configured_timeout_output = 99, ""
    finally:
        module.subprocess.run = original_run
        if original_timeout_env is None:
            os.environ.pop("ARBOR_PROJECT_WRAPPER_SMOKE_TIMEOUT_SECONDS", None)
        else:
            os.environ["ARBOR_PROJECT_WRAPPER_SMOKE_TIMEOUT_SECONDS"] = original_timeout_env
    check(errors, configured_timeout_code == 0, "project wrapper smoke configurable timeout probe must succeed")
    check(
        errors,
        configured_timeout_output == "ok\n",
        "project wrapper smoke must preserve command output with configured timeout",
    )


def validate_smoke_script_executes(errors: list[str]) -> None:
    output = run_command([sys.executable, str(SCRIPTS_ROOT / "check_project_wrapper_smoke.py")], errors)
    check(errors, "project wrapper smoke passed" in output, "project wrapper smoke script must report pass evidence")


def main() -> int:
    errors: list[str] = []
    validate_smoke_script_surface(errors)
    validate_smoke_subprocess_resilience(errors)
    validate_smoke_script_executes(errors)

    if errors:
        print("project wrapper smoke adapter checks failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("project wrapper smoke adapter checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
