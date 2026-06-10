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
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


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


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[5]


def version_from_manifest(plugin_root: Path) -> str:
    data = json.loads((plugin_root / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    version = data.get("version")
    if not isinstance(version, str) or not version.strip():
        raise RuntimeError(f"missing plugin version in {plugin_root / '.codex-plugin/plugin.json'}")
    return version


def git_commit(repo_root: Path) -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"could not resolve HEAD: {proc.stderr.strip()}")
    return proc.stdout.strip()


def sync_tree(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)


def refresh_cached_hook_adapters(source: Path, cache_base: Path) -> int:
    if not cache_base.is_dir():
        return 0
    refreshed = 0
    for cached_version in cache_base.iterdir():
        if not cached_version.is_dir():
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
        legacy_manifest = cached_version / LEGACY_PLUGIN_HOOK_MANIFEST
        if legacy_manifest.is_file():
            legacy_manifest.unlink()
            removed += 1
    return removed


def update_claude_registry(cache_path: Path, version: str, commit: str) -> None:
    if not CLAUDE_INSTALLED_PLUGINS.exists():
        return
    data = json.loads(CLAUDE_INSTALLED_PLUGINS.read_text(encoding="utf-8"))
    plugins = data.setdefault("plugins", {})
    records = plugins.setdefault("arbor@arbor", [{}])
    if not records:
        records.append({})
    record = records[0]
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
    args = parser.parse_args(argv)

    repo_root = repo_root_from_script()
    source = args.source or repo_root / PLUGIN_REL
    source = source.resolve()
    version = version_from_manifest(source)
    commit = git_commit(repo_root)
    targets: list[tuple[str, Path]] = []
    if args.runtime in ("both", "codex"):
        targets.append(("codex", CODEX_CACHE_BASE / version))
    if args.runtime in ("both", "claude"):
        targets.append(("claude", CLAUDE_CACHE_BASE / version))

    for _runtime, target in targets:
        sync_tree(source, target)

    refreshed_hooks = 0
    removed_legacy_hooks = 0
    if args.runtime in ("both", "codex"):
        if CODEX_MARKETPLACE_PLUGIN.exists():
            sync_tree(source, CODEX_MARKETPLACE_PLUGIN)
        refreshed_hooks += refresh_cached_hook_adapters(source, CODEX_CACHE_BASE)
        removed_legacy_hooks += remove_legacy_plugin_hook_manifests(CODEX_CACHE_BASE)
    if args.runtime in ("both", "claude"):
        refreshed_hooks += refresh_cached_hook_adapters(source, CLAUDE_CACHE_BASE)
        removed_legacy_hooks += remove_legacy_plugin_hook_manifests(CLAUDE_CACHE_BASE)

    if args.update_claude_registry and args.runtime in ("both", "claude"):
        update_claude_registry(CLAUDE_CACHE_BASE / version, version, commit)

    for runtime, target in targets:
        print(f"{runtime}: synced {target}")
    print("older cache versions preserved")
    print(f"cached hook adapters refreshed: {refreshed_hooks}")
    print(f"legacy plugin hook manifests removed: {removed_legacy_hooks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
