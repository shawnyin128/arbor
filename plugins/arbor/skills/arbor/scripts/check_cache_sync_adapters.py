#!/usr/bin/env python3
"""Validate Arbor local plugin cache sync behavior."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

SCRIPT_ROOT = Path(__file__).resolve().parent


def add_error(errors: list[str], message: str) -> None:
    errors.append(message)


def check(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        add_error(errors, message)


def run_command(args: list[str], errors: list[str]) -> str:
    proc = subprocess.run(
        args,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        joined = " ".join(args)
        detail = proc.stderr.strip() or proc.stdout.strip() or "no output"
        add_error(errors, f"command failed ({proc.returncode}): {joined}: {detail}")
    return proc.stdout


def run_git(root: Path, errors: list[str], *args: str) -> str:
    return run_command(["git", "-C", str(root), *args], errors)


def load_cache_sync_module(name: str):
    module_path = SCRIPT_ROOT / "sync_local_plugin_cache.py"
    spec = importlib.util.spec_from_file_location(name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load sync_local_plugin_cache.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_cache_sync_copy_and_registry_behavior(errors: list[str]) -> None:
    try:
        module = load_cache_sync_module("arbor_sync_local_plugin_cache_copy_check")
    except RuntimeError as exc:
        add_error(errors, str(exc))
        return
    check(errors, hasattr(module, "verify_synced_cache"), "cache sync must expose post-sync cache verification")
    if not hasattr(module, "verify_synced_cache"):
        return

    with tempfile.TemporaryDirectory(prefix="arbor-cache-sync-check-") as tmp:
        root = Path(tmp)
        source = root / "source"
        target = root / "target"
        source.mkdir()
        (source / "kept.txt").write_text("keep\n", encoding="utf-8")
        (source / "module.pyc").write_bytes(b"stale")
        (source / "__pycache__").mkdir()
        (source / "__pycache__" / "old.cpython-313.pyc").write_bytes(b"stale")
        (source / ".pytest_cache").mkdir()
        (source / ".pytest_cache" / "README.md").write_text("stale\n", encoding="utf-8")
        (source / ".codex-plugin").mkdir()
        (source / ".codex-plugin" / "plugin.json").write_text(
            '{"name": "arbor", "version": "2.0.0"}\n',
            encoding="utf-8-sig",
        )
        check(errors, module.version_from_manifest(source) == "2.0.0", "cache sync must accept UTF-8 BOM plugin manifests")
        (source / ".claude-plugin").mkdir()
        (source / ".claude-plugin" / "plugin.json").write_text(
            '{"name": "arbor", "version": "9.9.9"}\n',
            encoding="utf-8",
        )
        try:
            module.version_from_manifest(source)
        except RuntimeError as exc:
            check(errors, "versions differ" in str(exc), "cache sync manifest mismatch error must explain differing versions")
        else:
            add_error(errors, "cache sync must reject mismatched Codex and Claude manifest versions")

        original_source_within_repo = module.source_within_repo
        original_git_source_dirty = module.git_source_dirty
        original_codex_cache_base = module.CODEX_CACHE_BASE
        module.source_within_repo = lambda _repo, _source: True
        module.git_source_dirty = lambda _repo, _source: False
        module.CODEX_CACHE_BASE = root / "codex-cache"
        stderr = io.StringIO()
        try:
            with contextlib.redirect_stderr(stderr):
                mismatch_code = module.main(["--source", str(source), "--runtime", "codex"])
            check(errors, mismatch_code == 1, "cache sync CLI must fail cleanly for manifest version mismatches")
            check(errors, "versions differ" in stderr.getvalue(), "cache sync CLI must explain manifest version mismatches")
        except RuntimeError as exc:
            add_error(errors, f"cache sync CLI must not traceback for manifest version mismatches: {exc}")
        finally:
            module.source_within_repo = original_source_within_repo
            module.git_source_dirty = original_git_source_dirty
            module.CODEX_CACHE_BASE = original_codex_cache_base

        (source / ".codex-plugin" / "plugin.json").write_text(
            '{"name": "arbor", "version": "dev"}\n',
            encoding="utf-8",
        )
        (source / ".claude-plugin" / "plugin.json").write_text(
            '{"name": "arbor", "version": "dev"}\n',
            encoding="utf-8",
        )
        try:
            module.version_from_manifest(source)
        except RuntimeError as exc:
            check(errors, "release version" in str(exc), "cache sync non-release version error must explain release-version requirement")
        else:
            add_error(errors, "cache sync must reject non-release manifest versions")

        module.source_within_repo = lambda _repo, _source: True
        module.git_source_dirty = lambda _repo, _source: False
        module.CODEX_CACHE_BASE = root / "codex-cache"
        stderr = io.StringIO()
        try:
            with contextlib.redirect_stderr(stderr):
                dev_version_code = module.main(["--source", str(source), "--runtime", "codex"])
            check(errors, dev_version_code == 1, "cache sync CLI must fail cleanly for non-release manifest versions")
            check(errors, "release version" in stderr.getvalue(), "cache sync CLI must explain non-release manifest versions")
        except RuntimeError as exc:
            add_error(errors, f"cache sync CLI must not traceback for non-release manifest versions: {exc}")
        finally:
            module.source_within_repo = original_source_within_repo
            module.git_source_dirty = original_git_source_dirty
            module.CODEX_CACHE_BASE = original_codex_cache_base

        (source / ".claude-plugin" / "plugin.json").write_text(
            '{"name": "arbor", "version": "2.0.0"}\n',
            encoding="utf-8",
        )
        (source / ".codex-plugin" / "plugin.json").write_text(
            '{"name": "arbor", "version": "2.0.0"}\n',
            encoding="utf-8",
        )

        invalid_registry = root / "installed_plugins.json"
        invalid_registry.write_text("{not-json", encoding="utf-8")
        original_git_commit = module.git_commit
        original_claude_cache_base = module.CLAUDE_CACHE_BASE
        original_registry = module.CLAUDE_INSTALLED_PLUGINS
        module.source_within_repo = lambda _repo, _source: True
        module.git_source_dirty = lambda _repo, _source: False
        module.git_commit = lambda _repo: "abc1234"
        module.CLAUDE_CACHE_BASE = root / "claude-cache"
        module.CLAUDE_INSTALLED_PLUGINS = invalid_registry
        stderr = io.StringIO()
        try:
            with contextlib.redirect_stderr(stderr):
                registry_code = module.main(["--source", str(source), "--runtime", "claude", "--update-claude-registry"])
            check(errors, registry_code == 1, "cache sync CLI must fail cleanly for invalid Claude registry JSON")
            check(errors, "could not update Claude registry" in stderr.getvalue(), "cache sync CLI must explain invalid Claude registry JSON")
        except Exception as exc:  # noqa: BLE001 - adapter check reports the unexpected traceback.
            add_error(errors, f"cache sync CLI must not traceback for invalid Claude registry JSON: {exc}")
        finally:
            module.source_within_repo = original_source_within_repo
            module.git_source_dirty = original_git_source_dirty
            module.git_commit = original_git_commit
            module.CLAUDE_CACHE_BASE = original_claude_cache_base
            module.CLAUDE_INSTALLED_PLUGINS = original_registry

        valid_registry = root / "valid_installed_plugins.json"
        valid_registry.write_text(
            json.dumps({"plugins": {"arbor@arbor": [{"version": "old", "installPath": "old-path"}]}}) + "\n",
            encoding="utf-8",
        )
        original_verify_synced_cache = module.verify_synced_cache
        module.source_within_repo = lambda _repo, _source: True
        module.git_source_dirty = lambda _repo, _source: False
        module.git_commit = lambda _repo: "abc1234"
        module.CLAUDE_CACHE_BASE = root / "claude-cache-fail"
        module.CLAUDE_INSTALLED_PLUGINS = valid_registry
        module.verify_synced_cache = lambda _source, _target: ["forced post-sync failure"]
        stderr = io.StringIO()
        try:
            with contextlib.redirect_stderr(stderr):
                failed_sync_code = module.main(["--source", str(source), "--runtime", "claude", "--update-claude-registry"])
            registry_after_failed_sync = json.loads(valid_registry.read_text(encoding="utf-8"))
            arbor_record = registry_after_failed_sync["plugins"]["arbor@arbor"][0]
            check(errors, failed_sync_code == 1, "cache sync CLI must fail when post-sync verification fails")
            check(errors, arbor_record["version"] == "old", "cache sync must not update Claude registry after failed post-sync verification")
        finally:
            module.source_within_repo = original_source_within_repo
            module.git_source_dirty = original_git_source_dirty
            module.git_commit = original_git_commit
            module.CLAUDE_CACHE_BASE = original_claude_cache_base
            module.CLAUDE_INSTALLED_PLUGINS = original_registry
            module.verify_synced_cache = original_verify_synced_cache

        success_registry = root / "success_installed_plugins.json"
        success_registry.write_text(
            json.dumps({"plugins": {"arbor@arbor": [{"scope": "user", "installedAt": "earlier"}]}}) + "\n",
            encoding="utf-8",
        )
        module.source_within_repo = lambda _repo, _source: True
        module.git_source_dirty = lambda _repo, _source: False
        module.git_commit = lambda _repo: "abc1234"
        module.CLAUDE_CACHE_BASE = root / "claude-cache-success"
        module.CLAUDE_INSTALLED_PLUGINS = success_registry
        stdout = io.StringIO()
        try:
            with contextlib.redirect_stdout(stdout):
                registry_success_code = module.main(["--source", str(source), "--runtime", "claude", "--update-claude-registry"])
            success_data = json.loads(success_registry.read_text(encoding="utf-8"))
            success_record = success_data["plugins"]["arbor@arbor"][0]
            check(errors, registry_success_code == 0, "cache sync CLI must succeed when verified Claude registry update succeeds")
            check(errors, success_record["version"] == "2.0.0", "cache sync must write synced version to Claude registry after verification")
            check(errors, success_record["gitCommitSha"] == "abc1234", "cache sync must write source commit to Claude registry after verification")
            check(errors, "claude registry updated:" in stdout.getvalue().lower(), "cache sync CLI must report successful Claude registry updates")
        finally:
            module.source_within_repo = original_source_within_repo
            module.git_source_dirty = original_git_source_dirty
            module.git_commit = original_git_commit
            module.CLAUDE_CACHE_BASE = original_claude_cache_base
            module.CLAUDE_INSTALLED_PLUGINS = original_registry

        unsafe_source = root / "unsafe-source"
        unsafe_source.mkdir()
        (unsafe_source / "kept.txt").write_text("keep\n", encoding="utf-8")
        try:
            module.sync_tree(unsafe_source, unsafe_source)
        except RuntimeError as exc:
            check(errors, "source tree" in str(exc), "cache sync self-target refusal must explain the source-tree boundary")
        except Exception as exc:  # noqa: BLE001 - adapter check reports unexpected unsafe failures.
            add_error(errors, f"cache sync self-target refusal must not use destructive copy errors: {exc}")
        else:
            add_error(errors, "cache sync must refuse syncing into the source directory itself")
        check(errors, (unsafe_source / "kept.txt").is_file(), "cache sync self-target refusal must preserve source files")

        nested_source = root / "nested-source"
        nested_source.mkdir()
        (nested_source / "kept.txt").write_text("keep\n", encoding="utf-8")
        nested_target = nested_source / "nested-cache"
        try:
            module.sync_tree(nested_source, nested_target)
        except RuntimeError as exc:
            check(errors, "source tree" in str(exc), "cache sync nested-target refusal must explain the source-tree boundary")
        except Exception as exc:  # noqa: BLE001 - adapter check reports unexpected unsafe failures.
            add_error(errors, f"cache sync nested-target refusal must not use recursive copy errors: {exc}")
        else:
            add_error(errors, "cache sync must refuse syncing into a nested source directory")
        check(errors, not nested_target.exists(), "cache sync nested-target refusal must not create nested cache directories")

        unsafe_cli_source = root / "2.0.0"
        shutil.copytree(source, unsafe_cli_source)
        original_codex_cache_base_for_unsafe = module.CODEX_CACHE_BASE
        original_git_commit_for_unsafe = module.git_commit
        module.source_within_repo = lambda _repo, _source: True
        module.git_source_dirty = lambda _repo, _source: False
        module.git_commit = lambda _repo: "abc1234"
        module.CODEX_CACHE_BASE = root
        stderr = io.StringIO()
        try:
            with contextlib.redirect_stderr(stderr):
                try:
                    unsafe_cli_code = module.main(["--source", str(unsafe_cli_source), "--runtime", "codex"])
                except RuntimeError as exc:
                    add_error(errors, f"cache sync CLI must not traceback for unsafe sync targets: {exc}")
                    unsafe_cli_code = 99
            check(errors, unsafe_cli_code == 1, "cache sync CLI must fail cleanly for unsafe sync targets")
            check(errors, "source tree" in stderr.getvalue(), "cache sync CLI must explain unsafe sync targets")
        finally:
            module.source_within_repo = original_source_within_repo
            module.git_source_dirty = original_git_source_dirty
            module.git_commit = original_git_commit_for_unsafe
            module.CODEX_CACHE_BASE = original_codex_cache_base_for_unsafe

        module.sync_tree(source, target)

        check(errors, (target / "kept.txt").is_file(), "cache sync must copy normal plugin files")
        check(errors, not (target / "module.pyc").exists(), "cache sync must ignore top-level pyc files")
        check(errors, not (target / "__pycache__").exists(), "cache sync must ignore __pycache__ directories")
        check(errors, not (target / ".pytest_cache").exists(), "cache sync must ignore pytest cache directories")
        check(errors, module.verify_synced_cache(source, target) == [], "cache sync post-verify must pass for a freshly synced target")

        existing_target = root / "existing-target"
        existing_target.mkdir()
        (existing_target / "old-cache.txt").write_text("keep old cache\n", encoding="utf-8")
        original_copytree = module.shutil.copytree

        def fail_copytree(*_args: Any, **_kwargs: Any) -> Any:
            raise OSError("simulated copy failure")

        module.shutil.copytree = fail_copytree
        try:
            try:
                module.sync_tree(source, existing_target)
            except OSError:
                pass
            except Exception as exc:  # noqa: BLE001 - adapter check reports unexpected failure types.
                add_error(errors, f"cache sync copy failure should surface as copy error, got {exc}")
            else:
                add_error(errors, "cache sync must fail when staging copy fails")
        finally:
            module.shutil.copytree = original_copytree
        old_cache_file = existing_target / "old-cache.txt"
        check(
            errors,
            old_cache_file.is_file() and old_cache_file.read_text(encoding="utf-8") == "keep old cache\n",
            "cache sync must preserve existing cache when staging copy fails",
        )

        move_failure_target = root / "move-failure-target"
        move_failure_target.mkdir()
        (move_failure_target / "old-cache.txt").write_text("keep old cache\n", encoding="utf-8")
        original_move = module.shutil.move

        def fail_staging_move(src: object, dst: object, *_args: Any, **_kwargs: Any) -> Any:
            if ".staging-" in str(src):
                raise OSError("simulated final replacement failure")
            return original_move(src, dst, *_args, **_kwargs)

        module.shutil.move = fail_staging_move
        try:
            try:
                module.sync_tree(source, move_failure_target)
            except OSError:
                pass
            except Exception as exc:  # noqa: BLE001 - adapter check reports unexpected failure types.
                add_error(errors, f"cache sync move failure should surface as move error, got {exc}")
            else:
                add_error(errors, "cache sync must fail when final cache replacement fails")
        finally:
            module.shutil.move = original_move
        move_old_cache_file = move_failure_target / "old-cache.txt"
        check(
            errors,
            move_old_cache_file.is_file() and move_old_cache_file.read_text(encoding="utf-8") == "keep old cache\n",
            "cache sync must preserve existing cache when final replacement fails",
        )

        (target / "kept.txt").unlink()
        missing_failures = module.verify_synced_cache(source, target)
        check(errors, any("digest differs" in failure for failure in missing_failures), "cache sync post-verify must catch missing copied files")
        module.sync_tree(source, target)

        (target / "__pycache__").mkdir()
        (target / "__pycache__" / "stale.pyc").write_bytes(b"stale")
        transient_failures = module.verify_synced_cache(source, target)
        check(errors, any("transient artifact" in failure for failure in transient_failures), "cache sync post-verify must catch transient artifacts in target")
        shutil.rmtree(target / "__pycache__")

        source_hooks = source / "hooks"
        source_hooks.mkdir()
        (source_hooks / "session-start").write_text("new session adapter\n", encoding="utf-8")
        (source_hooks / "stop-memory-hygiene").write_text("new stop adapter\n", encoding="utf-8")
        cache_base = root / "cache-base"
        for version in ("1.1.1", "2.0.0", "dev"):
            cached_hooks = cache_base / version / "hooks"
            cached_hooks.mkdir(parents=True)
            (cached_hooks / "session-start").write_text("old session adapter\n", encoding="utf-8")
            (cached_hooks / "stop-memory-hygiene").write_text("old stop adapter\n", encoding="utf-8")
            (cached_hooks / "hooks.json").write_text('{"legacy": true}\n', encoding="utf-8")

        refreshed = module.refresh_cached_hook_adapters(source, cache_base)
        removed = module.remove_legacy_plugin_hook_manifests(cache_base)
        check(errors, refreshed == 4, "cache sync must refresh hook adapters only in existing release version caches")
        check(errors, removed == 2, "cache sync must remove legacy plugin-level hook manifests only from release version caches")
        for version in ("1.1.1", "2.0.0"):
            cached_hooks = cache_base / version / "hooks"
            check(errors, (cached_hooks / "session-start").read_text(encoding="utf-8") == "new session adapter\n", "cache sync must refresh session-start adapter")
            check(errors, (cached_hooks / "stop-memory-hygiene").read_text(encoding="utf-8") == "new stop adapter\n", "cache sync must refresh stop adapter")
            check(errors, not (cached_hooks / "hooks.json").exists(), "cache sync must remove legacy plugin-level hooks.json")
        dev_hooks = cache_base / "dev" / "hooks"
        check(errors, (dev_hooks / "session-start").read_text(encoding="utf-8") == "old session adapter\n", "cache sync must leave non-release cache adapters untouched")
        check(errors, (dev_hooks / "stop-memory-hygiene").read_text(encoding="utf-8") == "old stop adapter\n", "cache sync must leave non-release stop adapters untouched")
        check(errors, (dev_hooks / "hooks.json").exists(), "cache sync must leave non-release legacy plugin hook manifests untouched")


def validate_cache_sync_clean_source_behavior(errors: list[str]) -> None:
    try:
        module = load_cache_sync_module("arbor_sync_local_plugin_cache_dirty_check")
    except RuntimeError as exc:
        add_error(errors, str(exc))
        return

    check(errors, hasattr(module, "git_source_dirty"), "cache sync must expose git_source_dirty")
    check(errors, hasattr(module, "source_within_repo"), "cache sync must expose source_within_repo")
    if not hasattr(module, "git_source_dirty") or not hasattr(module, "source_within_repo"):
        return

    with tempfile.TemporaryDirectory(prefix="arbor-cache-sync-dirty-check-") as tmp:
        repo = Path(tmp)
        source = repo / "plugins" / "arbor"
        external = repo.parent / f"{repo.name}-external-source"
        source.mkdir(parents=True)
        external.mkdir()
        (source / ".codex-plugin").mkdir()
        (source / ".codex-plugin" / "plugin.json").write_text('{"name":"arbor","version":"2.0.0"}\n', encoding="utf-8")
        run_git(repo, errors, "init")
        run_git(repo, errors, "config", "user.email", "arbor@example.invalid")
        run_git(repo, errors, "config", "user.name", "Arbor Check")
        run_git(repo, errors, "add", ".")
        run_git(repo, errors, "commit", "-m", "initial")

        check(errors, not module.git_source_dirty(repo, source), "clean committed plugin source must be syncable")

        manifest_path = source / ".codex-plugin" / "plugin.json"
        clean_manifest = manifest_path.read_text(encoding="utf-8")
        manifest_path.write_text('{"name":"arbor","version":"2.0.1"}\n', encoding="utf-8")
        check(errors, module.git_source_dirty(repo, source), "cache sync must detect modified plugin source")
        manifest_path.write_text(clean_manifest, encoding="utf-8")

        (source / "untracked.txt").write_text("new\n", encoding="utf-8")
        check(errors, module.git_source_dirty(repo, source), "cache sync must detect untracked plugin source files")
        (source / "untracked.txt").unlink()

        (repo / "outside.txt").write_text("outside\n", encoding="utf-8")
        check(errors, not module.git_source_dirty(repo, source), "dirty files outside the plugin source must not block plugin cache sync")
        check(errors, module.source_within_repo(repo, source), "cache sync must accept plugin source inside the repository")
        check(errors, not module.source_within_repo(repo, external), "cache sync must reject plugin source outside the repository")

        original_subprocess_run = module.subprocess.run

        def raise_cache_sync_status_timeout(command: list[str], *_args: Any, **_kwargs: Any) -> Any:
            if command and command[0] == "git" and "status" in command:
                raise subprocess.TimeoutExpired(command, timeout=0.1)
            return original_subprocess_run(command, *_args, **_kwargs)

        module.subprocess.run = raise_cache_sync_status_timeout
        try:
            try:
                module.git_source_dirty(repo, source)
            except subprocess.TimeoutExpired as exc:
                add_error(errors, f"cache sync git status timeouts must not propagate: {exc}")
            except RuntimeError as exc:
                check(errors, "timed out" in str(exc), "cache sync git status timeout errors must explain the timeout")
            else:
                add_error(errors, "cache sync git status timeouts must fail dirty-source inspection")
        finally:
            module.subprocess.run = original_subprocess_run

        def raise_cache_sync_status_launch(command: list[str], *_args: Any, **_kwargs: Any) -> Any:
            if command and command[0] == "git" and "status" in command:
                raise OSError("simulated cache sync git status launch failure")
            return original_subprocess_run(command, *_args, **_kwargs)

        module.subprocess.run = raise_cache_sync_status_launch
        try:
            try:
                module.git_source_dirty(repo, source)
            except OSError as exc:
                add_error(errors, f"cache sync git status launch failures must not propagate: {exc}")
            except RuntimeError as exc:
                check(errors, "failed to start" in str(exc), "cache sync git status launch failures must explain the launch error")
            else:
                add_error(errors, "cache sync git status launch failures must fail dirty-source inspection")
        finally:
            module.subprocess.run = original_subprocess_run

        def raise_cache_sync_commit_timeout(command: list[str], *_args: Any, **_kwargs: Any) -> Any:
            if command and command[0] == "git" and "rev-parse" in command:
                raise subprocess.TimeoutExpired(command, timeout=0.1)
            return original_subprocess_run(command, *_args, **_kwargs)

        module.subprocess.run = raise_cache_sync_commit_timeout
        try:
            try:
                module.git_commit(repo)
            except subprocess.TimeoutExpired as exc:
                add_error(errors, f"cache sync git commit timeouts must not propagate: {exc}")
            except RuntimeError as exc:
                check(errors, "timed out" in str(exc), "cache sync git commit timeout errors must explain the timeout")
            else:
                add_error(errors, "cache sync git commit timeouts must fail commit inspection")
        finally:
            module.subprocess.run = original_subprocess_run

        def raise_cache_sync_commit_launch(command: list[str], *_args: Any, **_kwargs: Any) -> Any:
            if command and command[0] == "git" and "rev-parse" in command:
                raise OSError("simulated cache sync git commit launch failure")
            return original_subprocess_run(command, *_args, **_kwargs)

        module.subprocess.run = raise_cache_sync_commit_launch
        try:
            try:
                module.git_commit(repo)
            except OSError as exc:
                add_error(errors, f"cache sync git commit launch failures must not propagate: {exc}")
            except RuntimeError as exc:
                check(errors, "failed to start" in str(exc), "cache sync git commit launch failures must explain the launch error")
            else:
                add_error(errors, "cache sync git commit launch failures must fail commit inspection")
        finally:
            module.subprocess.run = original_subprocess_run

        original_source_within_repo = module.source_within_repo
        original_git_source_dirty = module.git_source_dirty
        original_git_commit = module.git_commit
        module.source_within_repo = lambda _repo, _source: True
        module.git_source_dirty = lambda _repo, _source: False

        def raise_commit_runtime_error(_repo: Path) -> str:
            raise RuntimeError("could not resolve HEAD: timed out after 10s")

        module.git_commit = raise_commit_runtime_error
        stderr = io.StringIO()
        try:
            with contextlib.redirect_stderr(stderr):
                try:
                    commit_timeout_code = module.main(["--source", str(source), "--runtime", "codex"])
                except RuntimeError as exc:
                    add_error(errors, f"cache sync CLI must not traceback for git commit timeouts: {exc}")
                    commit_timeout_code = 99
            check(errors, commit_timeout_code == 1, "cache sync CLI must fail cleanly when git commit inspection times out")
            check(errors, "timed out" in stderr.getvalue(), "cache sync CLI must explain git commit inspection timeouts")
        finally:
            module.source_within_repo = original_source_within_repo
            module.git_source_dirty = original_git_source_dirty
            module.git_commit = original_git_commit


def main() -> int:
    errors: list[str] = []
    validate_cache_sync_copy_and_registry_behavior(errors)
    validate_cache_sync_clean_source_behavior(errors)

    if errors:
        print("cache sync adapter checks failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("cache sync adapter checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
