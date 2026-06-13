#!/usr/bin/env python3
"""Report whether local Arbor plugin caches match the source plugin."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


sys.dont_write_bytecode = True

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_GIT_TIMEOUT_SECONDS = 10.0
CODEX_CACHE_BASE = Path.home() / ".codex" / "plugins" / "cache" / "arbor" / "arbor"
CLAUDE_CACHE_BASE = Path.home() / ".claude" / "plugins" / "cache" / "arbor" / "arbor"
TRANSIENT_DIR_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache"}
IGNORED_RUNTIME_DIR_NAMES = {".in_use"}
TRANSIENT_SUFFIXES = {".pyc", ".pyo"}
LEGACY_PLUGIN_HOOK_MANIFEST = Path("hooks") / "hooks.json"
RELEASE_VERSION_PATTERN = re.compile(r"\d+\.\d+\.\d+")
RUNTIME_CODEX = "codex"
RUNTIME_CLAUDE = "claude"
RUNTIME_BOTH = "both"
RUNTIME_CHOICES = (RUNTIME_CODEX, RUNTIME_CLAUDE, RUNTIME_BOTH)


@dataclass(frozen=True)
class RuntimeCacheState:
    runtime: str
    status: str
    source_version: str
    cache_base: str
    expected_cache_path: str
    selected_cache_version: str | None
    source_digest: str | None
    cache_digest: str | None
    issues: list[str]


@dataclass(frozen=True)
class InstallState:
    source: str
    version: str
    runtimes: dict[str, RuntimeCacheState]


def version_key(path: Path) -> tuple[int, ...]:
    parts: list[int] = []
    for part in path.name.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(-1)
    return tuple(parts)


def load_json(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def source_version(source: Path) -> str:
    codex = load_json(source / ".codex-plugin" / "plugin.json")
    claude_path = source / ".claude-plugin" / "plugin.json"
    codex_version = codex.get("version")
    if not isinstance(codex_version, str) or not codex_version:
        raise ValueError(f"missing version in {source / '.codex-plugin/plugin.json'}")
    if claude_path.is_file():
        claude = load_json(claude_path)
        claude_version = claude.get("version")
        if claude_version != codex_version:
            raise ValueError("Codex and Claude plugin manifest versions differ")
    return codex_version


def is_transient(path: Path) -> bool:
    return any(part in TRANSIENT_DIR_NAMES for part in path.parts) or path.suffix in TRANSIENT_SUFFIXES


def is_ignored_for_digest(path: Path) -> bool:
    ignored_dirs = TRANSIENT_DIR_NAMES | IGNORED_RUNTIME_DIR_NAMES
    return any(part in ignored_dirs for part in path.parts) or path.suffix in TRANSIENT_SUFFIXES


def digest_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    return text.replace("\r\n", "\n").encode("utf-8")


def transient_artifacts(root: Path) -> list[str]:
    artifacts: list[str] = []
    if not root.exists():
        return artifacts
    for path in sorted(root.rglob("*")):
        if is_transient(path):
            try:
                artifacts.append(path.relative_to(root).as_posix())
            except ValueError:
                artifacts.append(str(path))
    return artifacts


def digest_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_dir() or is_ignored_for_digest(path):
            continue
        rel = path.relative_to(root).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(digest_bytes(path))
        digest.update(b"\0")
    return digest.hexdigest()


def selected_cache_version(cache_base: Path) -> str | None:
    if not cache_base.is_dir():
        return None
    versions = sorted(
        (
            path
            for path in cache_base.iterdir()
            if path.is_dir() and is_release_version(path.name) and looks_like_arbor_plugin_root(path)
        ),
        key=version_key,
        reverse=True,
    )
    return versions[0].name if versions else None


def looks_like_arbor_plugin_root(root: Path) -> bool:
    return (
        (root / ".codex-plugin" / "plugin.json").is_file()
        and (root / ".claude-plugin" / "plugin.json").is_file()
        and (root / "skills" / "arbor" / "SKILL.md").is_file()
    )


def runtime_cache_state(source: Path, cache_base: Path, runtime: str) -> RuntimeCacheState:
    resolved_source = source.resolve()
    resolved_cache_base = cache_base.expanduser().resolve()
    version = source_version(resolved_source)
    expected_cache = resolved_cache_base / version
    selected_version = selected_cache_version(resolved_cache_base)
    issues: list[str] = []
    try:
        source_digest_value = digest_tree(resolved_source)
    except OSError as exc:
        source_digest_value = None
        issues.append(f"could not digest source tree: {exc}")
    cache_digest_value: str | None = None

    if not expected_cache.is_dir():
        issues.append(f"expected cache version is missing: {expected_cache}")
        return RuntimeCacheState(
            runtime=runtime,
            status="missing",
            source_version=version,
            cache_base=str(resolved_cache_base),
            expected_cache_path=str(expected_cache),
            selected_cache_version=selected_version,
            source_digest=source_digest_value,
            cache_digest=None,
            issues=issues,
        )

    if selected_version != version:
        issues.append(f"newest release cache version is {selected_version}, expected {version}; project wrappers select the newest release cache")

    legacy_manifest = expected_cache / LEGACY_PLUGIN_HOOK_MANIFEST
    if legacy_manifest.is_file():
        issues.append(f"legacy plugin-level hooks/hooks.json is present: {legacy_manifest}")

    for artifact in transient_artifacts(expected_cache):
        issues.append(f"transient cache artifact is present: {artifact}")

    try:
        cache_digest_value = digest_tree(expected_cache)
    except OSError as exc:
        cache_digest_value = None
        issues.append(f"could not digest expected cache: {exc}")
    if cache_digest_value is not None and source_digest_value is not None and cache_digest_value != source_digest_value:
        issues.append("content digest differs between source and expected cache")

    return RuntimeCacheState(
        runtime=runtime,
        status="ready" if not issues else "drift",
        source_version=version,
        cache_base=str(resolved_cache_base),
        expected_cache_path=str(expected_cache),
        selected_cache_version=selected_version,
        source_digest=source_digest_value,
        cache_digest=cache_digest_value,
        issues=issues,
    )


def check_install_state(source: Path, codex_cache_base: Path, claude_cache_base: Path, runtime: str = RUNTIME_BOTH) -> InstallState:
    resolved_source = source.resolve()
    version = source_version(resolved_source)
    runtimes: dict[str, RuntimeCacheState] = {}
    if runtime in (RUNTIME_CODEX, RUNTIME_BOTH):
        runtimes[RUNTIME_CODEX] = runtime_cache_state(resolved_source, codex_cache_base, RUNTIME_CODEX)
    if runtime in (RUNTIME_CLAUDE, RUNTIME_BOTH):
        runtimes[RUNTIME_CLAUDE] = runtime_cache_state(resolved_source, claude_cache_base, RUNTIME_CLAUDE)
    return InstallState(
        source=str(resolved_source),
        version=version,
        runtimes=runtimes,
    )


def render_text(state: InstallState) -> str:
    lines = ["# Arbor Install State", "", f"Source: {state.source}", f"Version: {state.version}", ""]
    for runtime, runtime_state in state.runtimes.items():
        lines.extend(
            [
                f"## {runtime}",
                f"- status: {runtime_state.status}",
                f"- cache_base: {runtime_state.cache_base}",
                f"- expected_cache_path: {runtime_state.expected_cache_path}",
                f"- selected_cache_version: {runtime_state.selected_cache_version or 'none'}",
                "- issues:",
            ]
        )
        if runtime_state.issues:
            lines.extend(f"  - {issue}" for issue in runtime_state.issues)
        else:
            lines.append("  - none")
        lines.append("")
    return "\n".join(lines)


def has_install_drift(state: InstallState) -> bool:
    return any(runtime_state.status != "ready" for runtime_state in state.runtimes.values())


def is_release_version(version: str) -> bool:
    return RELEASE_VERSION_PATTERN.fullmatch(version) is not None


def git_timeout_seconds() -> float:
    raw = os.environ.get("ARBOR_INSTALL_STATE_GIT_TIMEOUT_SECONDS")
    if not raw:
        return DEFAULT_GIT_TIMEOUT_SECONDS
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_GIT_TIMEOUT_SECONDS
    if value <= 0:
        return DEFAULT_GIT_TIMEOUT_SECONDS
    return value


def git_root_for(path: Path) -> Path | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=git_timeout_seconds(),
        )
    except subprocess.TimeoutExpired:
        return None
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    root = proc.stdout.strip()
    return Path(root).resolve() if root else None


def git_source_dirty(source: Path) -> bool:
    resolved_source = source.resolve()
    root = git_root_for(resolved_source)
    if root is None:
        return False
    try:
        relative_source = resolved_source.relative_to(root)
    except ValueError:
        return False
    timeout = git_timeout_seconds()
    try:
        proc = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "status",
                "--porcelain",
                "--untracked-files=all",
                "--",
                str(relative_source),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout if isinstance(exc.stdout, str) else ""
        detail = output.strip()
        suffix = f": {detail}" if detail else ""
        raise RuntimeError(f"could not inspect plugin source git status: timed out after {timeout:g}s{suffix}") from exc
    except OSError as exc:
        raise RuntimeError(f"could not inspect plugin source git status: failed to start: {exc}") from exc
    if proc.returncode != 0:
        raise RuntimeError(f"could not inspect plugin source git status: {proc.stderr.strip()}")
    return bool(proc.stdout.strip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=PLUGIN_ROOT, help="Arbor plugin source root.")
    parser.add_argument("--codex-cache-base", type=Path, default=CODEX_CACHE_BASE)
    parser.add_argument("--claude-cache-base", type=Path, default=CLAUDE_CACHE_BASE)
    parser.add_argument("--runtime", choices=RUNTIME_CHOICES, default=RUNTIME_BOTH, help="Runtime cache surface to inspect.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument("--strict", action="store_true", help="Exit nonzero when any runtime cache is missing or drifted.")
    parser.add_argument(
        "--allow-dirty-source",
        action="store_true",
        help="Allow strict local development checks even when the plugin source has uncommitted changes.",
    )
    args = parser.parse_args(argv)

    try:
        state = check_install_state(args.source, args.codex_cache_base, args.claude_cache_base, args.runtime)
        dirty_source = git_source_dirty(args.source)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"install-state check failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(asdict(state), indent=2))
    else:
        print(render_text(state))
    strict_failed = False
    if args.strict and dirty_source and not args.allow_dirty_source:
        print(
            "install-state strict check failed: dirty plugin source has uncommitted changes; "
            "commit Arbor plugin changes first or pass --allow-dirty-source for an explicit local development check",
            file=sys.stderr,
        )
        strict_failed = True
    if args.strict and not is_release_version(state.version):
        print(
            f"install-state strict check failed: source manifest version must be a release version like X.Y.Z: {state.version}",
            file=sys.stderr,
        )
        strict_failed = True
    if args.strict and has_install_drift(state):
        print("install-state strict check failed: one or more runtime caches are missing or drifted", file=sys.stderr)
        strict_failed = True
    if strict_failed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
