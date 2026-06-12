#!/usr/bin/env python3
"""Sync committed Arbor plugin files into local Codex and Claude plugin caches.

The sync is versioned and additive: it creates or refreshes the target version
directory without deleting older versions. Running Codex or Claude Code
sessions may keep trusted hook definitions that reference an older cache path
until the client reloads, so release-time sync must not prune prior versions.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


sys.dont_write_bytecode = True

PLUGIN_REL = Path("plugins") / "arbor"
CODEX_CACHE_BASE_LABEL = ".codex/plugins/cache/arbor/arbor"
CLAUDE_CACHE_BASE_LABEL = ".claude/plugins/cache/arbor/arbor"
CODEX_CACHE_BASE = Path.home() / ".codex" / "plugins" / "cache" / "arbor" / "arbor"
CLAUDE_CACHE_BASE = Path.home() / ".claude" / "plugins" / "cache" / "arbor" / "arbor"
CODEX_MARKETPLACE_PLUGIN = Path.home() / ".codex" / ".tmp" / "marketplaces" / "arbor" / "plugins" / "arbor"
CLAUDE_INSTALLED_PLUGINS = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
HOOK_ADAPTER_RELS = (
    Path("hooks") / "session-start",
    Path("hooks") / "stop-memory-hygiene",
)
LEGACY_PLUGIN_HOOK_MANIFEST = Path("hooks") / "hooks.json"
TRANSIENT_DIR_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache"}
TRANSIENT_SUFFIXES = {".pyc", ".pyo"}
RELEASE_VERSION_PATTERN = re.compile(r"\d+\.\d+\.\d+")
DEFAULT_GIT_TIMEOUT_SECONDS = 10.0


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[5]


def git_timeout_seconds() -> float:
    raw = os.environ.get("ARBOR_CACHE_SYNC_GIT_TIMEOUT_SECONDS")
    if not raw:
        return DEFAULT_GIT_TIMEOUT_SECONDS
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_GIT_TIMEOUT_SECONDS
    if value <= 0:
        return DEFAULT_GIT_TIMEOUT_SECONDS
    return value


def load_manifest(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise RuntimeError(f"plugin manifest must be a JSON object: {path}")
    return data


def version_from_manifest(plugin_root: Path) -> str:
    codex_manifest = plugin_root / ".codex-plugin" / "plugin.json"
    data = load_manifest(codex_manifest)
    version = data.get("version")
    if not isinstance(version, str) or not version.strip():
        raise RuntimeError(f"missing plugin version in {codex_manifest}")
    claude_manifest = plugin_root / ".claude-plugin" / "plugin.json"
    if claude_manifest.is_file():
        claude_version = load_manifest(claude_manifest).get("version")
        if claude_version != version:
            raise RuntimeError(
                "Codex and Claude plugin manifest versions differ: "
                f"{codex_manifest} has {version!r}, {claude_manifest} has {claude_version!r}"
            )
    if RELEASE_VERSION_PATTERN.fullmatch(version) is None:
        raise RuntimeError(f"plugin manifest version must be a release version like X.Y.Z: {version!r}")
    return version


def is_release_version(version: str) -> bool:
    return RELEASE_VERSION_PATTERN.fullmatch(version) is not None


def git_commit(repo_root: Path) -> str:
    timeout = git_timeout_seconds()
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_root,
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
        raise RuntimeError(f"could not resolve HEAD: timed out after {timeout:g}s{suffix}") from exc
    except OSError as exc:
        raise RuntimeError(f"could not resolve HEAD: failed to start: {exc}") from exc
    if proc.returncode != 0:
        raise RuntimeError(f"could not resolve HEAD: {proc.stderr.strip()}")
    return proc.stdout.strip()


def source_within_repo(repo_root: Path, source: Path) -> bool:
    try:
        source.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return False
    return True


def git_source_dirty(repo_root: Path, source: Path) -> bool:
    resolved_repo = repo_root.resolve()
    resolved_source = source.resolve()
    try:
        relative_source = resolved_source.relative_to(resolved_repo)
    except ValueError:
        return False
    timeout = git_timeout_seconds()
    try:
        proc = subprocess.run(
            [
                "git",
                "-C",
                str(resolved_repo),
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


def sync_tree(source: Path, target: Path) -> None:
    resolved_source = source.resolve()
    resolved_target = target.resolve()
    if resolved_target == resolved_source or resolved_source in resolved_target.parents:
        raise RuntimeError(f"refusing to sync plugin cache into the source tree: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.staging-", dir=target.parent))
    backup = target.parent / f".{target.name}.backup-{os.getpid()}"
    try:
        shutil.rmtree(staging)
        shutil.copytree(
            source,
            staging,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", ".mypy_cache"),
        )
    except Exception:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        raise
    if backup.exists():
        shutil.rmtree(backup)
    try:
        if target.exists():
            shutil.move(str(target), str(backup))
        shutil.move(str(staging), str(target))
    except Exception:
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        if backup.exists() and not target.exists():
            shutil.move(str(backup), str(target))
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        raise
    if backup.exists():
        shutil.rmtree(backup, ignore_errors=True)


def is_transient(path: Path) -> bool:
    return any(part in TRANSIENT_DIR_NAMES for part in path.parts) or path.suffix in TRANSIENT_SUFFIXES


def digest_tree(root: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_dir() or is_transient(path):
            continue
        rel = path.relative_to(root).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def transient_artifacts(root: Path) -> list[str]:
    artifacts: list[str] = []
    if not root.exists():
        return artifacts
    for path in sorted(root.rglob("*")):
        if is_transient(path):
            artifacts.append(path.relative_to(root).as_posix())
    return artifacts


def verify_synced_cache(source: Path, target: Path) -> list[str]:
    failures: list[str] = []
    if not target.is_dir():
        return [f"synced target is missing: {target}"]
    for artifact in transient_artifacts(target):
        failures.append(f"transient artifact in synced target: {artifact}")
    if digest_tree(source) != digest_tree(target):
        failures.append(f"content digest differs after sync: {target}")
    return failures


def refresh_cached_hook_adapters(source: Path, cache_base: Path) -> int:
    if not cache_base.is_dir():
        return 0
    refreshed = 0
    for cached_version in cache_base.iterdir():
        if not cached_version.is_dir():
            continue
        if not is_release_version(cached_version.name):
            continue
        for rel in HOOK_ADAPTER_RELS:
            source_file = source / rel
            target_file = cached_version / rel
            if source_file.is_file() and target_file.exists():
                shutil.copy2(source_file, target_file)
                refreshed += 1
    return refreshed


def remove_legacy_plugin_hook_manifests(cache_base: Path) -> int:
    if not cache_base.is_dir():
        return 0
    removed = 0
    for cached_version in cache_base.iterdir():
        if not cached_version.is_dir():
            continue
        if not is_release_version(cached_version.name):
            continue
        legacy_manifest = cached_version / LEGACY_PLUGIN_HOOK_MANIFEST
        if legacy_manifest.is_file():
            legacy_manifest.unlink()
            removed += 1
    return removed


def update_claude_registry(cache_path: Path, version: str, commit: str) -> None:
    if not CLAUDE_INSTALLED_PLUGINS.exists():
        return
    data = json.loads(CLAUDE_INSTALLED_PLUGINS.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"Claude installed plugins registry must be a JSON object: {CLAUDE_INSTALLED_PLUGINS}")
    plugins = data.setdefault("plugins", {})
    if not isinstance(plugins, dict):
        raise ValueError(f"Claude installed plugins registry has invalid plugins object: {CLAUDE_INSTALLED_PLUGINS}")
    records = plugins.setdefault("arbor@arbor", [{}])
    if not isinstance(records, list):
        raise ValueError(f"Claude installed plugins registry has invalid Arbor records: {CLAUDE_INSTALLED_PLUGINS}")
    if not records:
        records.append({})
    record = records[0]
    if not isinstance(record, dict):
        raise ValueError(f"Claude installed plugins registry has invalid Arbor record: {CLAUDE_INSTALLED_PLUGINS}")
    record.setdefault("scope", "user")
    record.setdefault("installedAt", "unknown")
    record["installPath"] = str(cache_path)
    record["version"] = version
    record["lastUpdated"] = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    record["gitCommitSha"] = commit
    CLAUDE_INSTALLED_PLUGINS.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=None, help="Committed plugin source to sync.")
    parser.add_argument("--runtime", choices=("both", "codex", "claude"), default="both")
    parser.add_argument("--update-claude-registry", action="store_true")
    parser.add_argument(
        "--allow-dirty-source",
        action="store_true",
        help="Allow local development cache sync even when the plugin source has uncommitted changes.",
    )
    args = parser.parse_args(argv)

    repo_root = repo_root_from_script()
    source = args.source or repo_root / PLUGIN_REL
    source = source.resolve()
    if not source_within_repo(repo_root, source):
        print(
            f"refusing to sync source outside this repository: {source}",
            file=sys.stderr,
        )
        return 1
    try:
        dirty_source = git_source_dirty(repo_root, source)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if dirty_source and not args.allow_dirty_source:
        print(
            "refusing to sync dirty plugin source; commit Arbor plugin changes first "
            "or pass --allow-dirty-source for an explicit local development sync",
            file=sys.stderr,
        )
        return 1
    try:
        version = version_from_manifest(source)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"could not read plugin manifests: {exc}", file=sys.stderr)
        return 1
    try:
        commit = git_commit(repo_root)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    targets: list[tuple[str, Path]] = []
    if args.runtime in ("both", "codex"):
        targets.append(("codex", CODEX_CACHE_BASE / version))
    if args.runtime in ("both", "claude"):
        targets.append(("claude", CLAUDE_CACHE_BASE / version))

    sync_failures: list[str] = []
    for _runtime, target in targets:
        try:
            sync_tree(source, target)
        except (OSError, RuntimeError) as exc:
            sync_failures.append(f"sync failed for {target}: {exc}")
            continue
        sync_failures.extend(verify_synced_cache(source, target))

    refreshed_hooks = 0
    removed_legacy_hooks = 0
    if args.runtime in ("both", "codex"):
        if CODEX_MARKETPLACE_PLUGIN.exists():
            try:
                sync_tree(source, CODEX_MARKETPLACE_PLUGIN)
            except (OSError, RuntimeError) as exc:
                sync_failures.append(f"sync failed for {CODEX_MARKETPLACE_PLUGIN}: {exc}")
            else:
                sync_failures.extend(verify_synced_cache(source, CODEX_MARKETPLACE_PLUGIN))
        refreshed_hooks += refresh_cached_hook_adapters(source, CODEX_CACHE_BASE)
        removed_legacy_hooks += remove_legacy_plugin_hook_manifests(CODEX_CACHE_BASE)
    if args.runtime in ("both", "claude"):
        refreshed_hooks += refresh_cached_hook_adapters(source, CLAUDE_CACHE_BASE)
        removed_legacy_hooks += remove_legacy_plugin_hook_manifests(CLAUDE_CACHE_BASE)

    if sync_failures:
        print("post-sync verification failed:", file=sys.stderr)
        for failure in sync_failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    if args.update_claude_registry and args.runtime in ("both", "claude"):
        try:
            update_claude_registry(CLAUDE_CACHE_BASE / version, version, commit)
        except (OSError, RuntimeError, ValueError) as exc:
            print(f"could not update Claude registry: {exc}", file=sys.stderr)
            return 1
        print(f"claude registry updated: {CLAUDE_INSTALLED_PLUGINS} -> {CLAUDE_CACHE_BASE / version}")

    for runtime, target in targets:
        print(f"{runtime}: synced {target}")
    print("older cache versions preserved")
    print(f"cached hook adapters refreshed: {refreshed_hooks}")
    print(f"legacy plugin hook manifests removed: {removed_legacy_hooks}")
    print("post-sync verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
