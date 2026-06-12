#!/usr/bin/env python3
"""Check whether Arbor source, install state, and runtime smoke are release-ready."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


sys.dont_write_bytecode = True

SCRIPT_ROOT = Path(__file__).resolve().parent
PLUGIN_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = PLUGIN_ROOT.parents[1]
PUBLISHED_SOURCE_PATHS = (
    Path("README.md"),
    Path(".agents") / "plugins" / "marketplace.json",
    Path(".claude-plugin") / "marketplace.json",
)
SOURCE_MANIFEST_PATHS = {
    "Codex": Path(".codex-plugin") / "plugin.json",
    "Claude": Path(".claude-plugin") / "plugin.json",
}
RELEASE_VERSION_PATTERN = re.compile(r"\d+\.\d+\.\d+")
DEFAULT_CHECK_TIMEOUT_SECONDS = 120.0


@dataclass(frozen=True)
class ReadinessCheck:
    name: str
    command: list[str] | None
    required: bool = True


@dataclass(frozen=True)
class ReadinessOutcome:
    name: str
    status: str
    output: str = ""


def subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def check_timeout_seconds() -> float:
    raw = os.environ.get("ARBOR_RELEASE_READINESS_TIMEOUT_SECONDS")
    if not raw:
        return DEFAULT_CHECK_TIMEOUT_SECONDS
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_CHECK_TIMEOUT_SECONDS
    if value <= 0:
        return DEFAULT_CHECK_TIMEOUT_SECONDS
    return value


def run_command(command: list[str]) -> tuple[int, str]:
    timeout = check_timeout_seconds()
    try:
        proc = subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=subprocess_env(),
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout if isinstance(exc.stdout, str) else ""
        detail = output.strip()
        suffix = f"\n{detail}" if detail else ""
        return 1, f"command timed out after {timeout:g}s{suffix}"
    except OSError as exc:
        return 1, f"command failed to start: {exc}"
    return proc.returncode, proc.stdout.strip()


def run_check(check: ReadinessCheck) -> ReadinessOutcome:
    if check.command is None:
        return ReadinessOutcome(check.name, "missing")
    code, output = run_command(check.command)
    return ReadinessOutcome(check.name, "pass" if code == 0 else "fail", output)


def published_source_paths(root: Path, plugin_root: Path) -> list[str]:
    resolved_root = root.resolve()
    try:
        plugin_relative = plugin_root.resolve().relative_to(resolved_root)
    except ValueError as exc:
        raise RuntimeError(f"plugin root is outside release root: {plugin_root}") from exc
    return [path.as_posix() for path in PUBLISHED_SOURCE_PATHS] + [plugin_relative.as_posix()]


def run_published_source_check(root: Path, plugin_root: Path) -> ReadinessOutcome:
    try:
        paths = published_source_paths(root, plugin_root)
    except RuntimeError as exc:
        return ReadinessOutcome("published source", "fail", str(exc))
    missing = [path for path in paths if not (root.resolve() / path).exists()]
    if missing:
        return ReadinessOutcome("published source", "fail", "missing published source:\n" + "\n".join(missing))
    timeout = check_timeout_seconds()
    try:
        proc = subprocess.run(
            ["git", "-C", str(root.resolve()), "status", "--porcelain", "--untracked-files=all", "--", *paths],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=subprocess_env(),
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout if isinstance(exc.stdout, str) else ""
        detail = output.strip()
        suffix = f"\n{detail}" if detail else ""
        return ReadinessOutcome("published source", "fail", f"git status timed out after {timeout:g}s{suffix}")
    except OSError as exc:
        return ReadinessOutcome("published source", "fail", f"git status failed to start: {exc}")
    output = proc.stdout.strip()
    if proc.returncode != 0:
        return ReadinessOutcome("published source", "fail", output or "git status failed")
    if output:
        return ReadinessOutcome("published source", "fail", f"dirty published source:\n{output}")
    return ReadinessOutcome("published source", "pass")


def marketplace_source_paths(root: Path) -> dict[str, str]:
    codex_path = root / ".agents" / "plugins" / "marketplace.json"
    claude_path = root / ".claude-plugin" / "marketplace.json"
    codex = json.loads(codex_path.read_text(encoding="utf-8-sig"))
    claude = json.loads(claude_path.read_text(encoding="utf-8-sig"))
    if not isinstance(codex, dict) or not isinstance(claude, dict):
        raise RuntimeError("marketplace files must contain JSON objects")
    codex_plugins = codex.get("plugins")
    claude_plugins = claude.get("plugins")
    if not isinstance(codex_plugins, list) or len(codex_plugins) != 1:
        raise RuntimeError("Codex marketplace must contain exactly one plugin entry")
    if not isinstance(claude_plugins, list) or len(claude_plugins) != 1:
        raise RuntimeError("Claude marketplace must contain exactly one plugin entry")
    codex_entry = codex_plugins[0]
    claude_entry = claude_plugins[0]
    if not isinstance(codex_entry, dict) or not isinstance(claude_entry, dict):
        raise RuntimeError("marketplace plugin entries must be JSON objects")
    codex_source = codex_entry.get("source")
    codex_source_path = codex_source.get("path") if isinstance(codex_source, dict) else None
    claude_source_path = claude_entry.get("source")
    if not isinstance(codex_source_path, str) or not isinstance(claude_source_path, str):
        raise RuntimeError("marketplace source paths must be strings")
    return {"Codex": codex_source_path, "Claude": claude_source_path}


def run_marketplace_source_check(root: Path, plugin_root: Path) -> ReadinessOutcome:
    try:
        resolved_root = root.resolve()
        expected = "./" + plugin_root.resolve().relative_to(resolved_root).as_posix()
        paths = marketplace_source_paths(resolved_root)
    except (OSError, UnicodeError, json.JSONDecodeError, RuntimeError, ValueError) as exc:
        return ReadinessOutcome("marketplace source", "fail", str(exc))
    mismatches = [
        f"{runtime} marketplace source {path} does not match {expected}"
        for runtime, path in paths.items()
        if path != expected
    ]
    if mismatches:
        return ReadinessOutcome("marketplace source", "fail", "\n".join(mismatches))
    return ReadinessOutcome("marketplace source", "pass")


def manifest_version(manifest: Path) -> str:
    data = json.loads(manifest.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise RuntimeError(f"expected JSON object: {manifest}")
    version = data.get("version")
    if not isinstance(version, str) or not version.strip():
        raise RuntimeError(f"plugin source manifest has no version: {manifest}")
    return version.strip()


def plugin_source_version(plugin_root: Path) -> str:
    return manifest_version(plugin_root / SOURCE_MANIFEST_PATHS["Codex"])


def run_source_manifests_check(plugin_root: Path) -> ReadinessOutcome:
    try:
        versions = {
            runtime: manifest_version(plugin_root / relative_path)
            for runtime, relative_path in SOURCE_MANIFEST_PATHS.items()
        }
    except (OSError, UnicodeError, json.JSONDecodeError, RuntimeError) as exc:
        return ReadinessOutcome("source manifests", "fail", str(exc))
    if versions["Codex"] != versions["Claude"]:
        return ReadinessOutcome(
            "source manifests",
            "fail",
            f"Codex source version {versions['Codex']} does not match Claude source version {versions['Claude']}",
        )
    if RELEASE_VERSION_PATTERN.fullmatch(versions["Codex"]) is None:
        return ReadinessOutcome(
            "source manifests",
            "fail",
            f"plugin source version must be a release version like X.Y.Z: {versions['Codex']}",
        )
    return ReadinessOutcome("source manifests", "pass")


def runtime_smoke_evidence_version(evidence: Path) -> str:
    text = evidence.read_text(encoding="utf-8")
    match = re.search(r"(?im)^Version:\s*([^\s]+)\s*$", text)
    if match is None:
        raise RuntimeError(f"runtime smoke evidence has no Version: {evidence}")
    return match.group(1).strip()


def runtime_smoke_evidence_commit(evidence: Path) -> str:
    text = evidence.read_text(encoding="utf-8")
    match = re.search(r"(?im)^Commit:\s*([^\s]+)\s*$", text)
    if match is None:
        raise RuntimeError(f"runtime smoke evidence has no Commit: {evidence}")
    commit = match.group(1).strip()
    if len(commit) < 7 or not re.fullmatch(r"[0-9a-fA-F]+", commit):
        raise RuntimeError(f"runtime smoke evidence Commit is not a concrete git commit: {commit}")
    return commit.lower()


def release_source_head(root: Path) -> str:
    code, output = run_command(["git", "-C", str(root.resolve()), "rev-parse", "HEAD"])
    if code != 0:
        raise RuntimeError(output or "could not inspect release source HEAD")
    head = output.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{40}", head):
        raise RuntimeError(f"release source HEAD is not a full git commit: {head}")
    return head


def run_runtime_smoke_version_check(plugin_root: Path, evidence: Path) -> ReadinessOutcome:
    try:
        source_version = plugin_source_version(plugin_root)
        evidence_version = runtime_smoke_evidence_version(evidence)
    except (OSError, UnicodeError, json.JSONDecodeError, RuntimeError) as exc:
        return ReadinessOutcome("runtime smoke version", "fail", str(exc))
    if evidence_version != source_version:
        return ReadinessOutcome(
            "runtime smoke version",
            "fail",
            f"runtime smoke evidence Version {evidence_version} does not match plugin source version {source_version}",
        )
    return ReadinessOutcome("runtime smoke version", "pass")


def run_runtime_smoke_commit_check(root: Path, evidence: Path) -> ReadinessOutcome:
    try:
        source_head = release_source_head(root)
        evidence_commit = runtime_smoke_evidence_commit(evidence)
    except (OSError, UnicodeError, RuntimeError) as exc:
        return ReadinessOutcome("runtime smoke commit", "fail", str(exc))
    if not source_head.startswith(evidence_commit):
        return ReadinessOutcome(
            "runtime smoke commit",
            "fail",
            f"runtime smoke evidence Commit {evidence_commit} does not match release source HEAD {source_head}",
        )
    return ReadinessOutcome("runtime smoke commit", "pass")


def build_checks(args: argparse.Namespace) -> list[ReadinessCheck]:
    python = sys.executable
    checks: list[ReadinessCheck] = []
    if not args.skip_quality_gate:
        checks.append(
            ReadinessCheck(
                "source hard gate",
                [python, str(SCRIPT_ROOT / "check_quality_gate.py"), "--root", str(args.root), "--plugin-root", str(args.plugin_root)],
            )
        )
    codex_install_command = [
        python,
        str(SCRIPT_ROOT / "check_install_state.py"),
        "--source",
        str(args.plugin_root),
        "--runtime",
        "codex",
        "--strict",
    ]
    if args.codex_cache_base is not None:
        codex_install_command.extend(["--codex-cache-base", str(args.codex_cache_base)])
    claude_install_command = [
        python,
        str(SCRIPT_ROOT / "check_install_state.py"),
        "--source",
        str(args.plugin_root),
        "--runtime",
        "claude",
        "--strict",
    ]
    if args.claude_cache_base is not None:
        claude_install_command.extend(["--claude-cache-base", str(args.claude_cache_base)])
    checks.extend(
        [
            ReadinessCheck("install-state codex", codex_install_command),
            ReadinessCheck("install-state claude", claude_install_command),
        ]
    )
    if args.runtime_smoke_evidence is None:
        checks.append(ReadinessCheck("runtime smoke evidence", None))
    else:
        checks.append(
            ReadinessCheck(
                "runtime smoke evidence",
                [
                    python,
                    str(SCRIPT_ROOT / "check_runtime_smoke_evidence.py"),
                    str(args.runtime_smoke_evidence),
                ],
            )
        )
    return checks


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="Repository root to validate.")
    parser.add_argument("--plugin-root", type=Path, default=PLUGIN_ROOT, help="Arbor plugin source root.")
    parser.add_argument("--codex-cache-base", type=Path, default=None, help="Override Codex plugin cache base for checks.")
    parser.add_argument("--claude-cache-base", type=Path, default=None, help="Override Claude Code plugin cache base for checks.")
    parser.add_argument(
        "--runtime-smoke-evidence",
        type=Path,
        default=None,
        help="Completed runtime smoke evidence file to validate.",
    )
    parser.add_argument(
        "--skip-quality-gate",
        action="store_true",
        help="Skip the slow source hard gate when testing readiness failure classification.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    outcomes: list[ReadinessOutcome] = [
        run_source_manifests_check(args.plugin_root),
        run_marketplace_source_check(args.root, args.plugin_root),
    ]
    inserted_published_source = False
    for check in build_checks(args):
        if not inserted_published_source and check.name != "source hard gate":
            outcomes.append(run_published_source_check(args.root, args.plugin_root))
            inserted_published_source = True
        if check.name == "runtime smoke evidence" and check.command is not None:
            outcomes.append(run_runtime_smoke_version_check(args.plugin_root, args.runtime_smoke_evidence))
            outcomes.append(run_runtime_smoke_commit_check(args.root, args.runtime_smoke_evidence))
        outcomes.append(run_check(check))
        if check.name == "source hard gate":
            outcomes.append(run_published_source_check(args.root, args.plugin_root))
            inserted_published_source = True
    if not inserted_published_source:
        outcomes.append(run_published_source_check(args.root, args.plugin_root))

    print("Arbor release readiness")
    failures: list[ReadinessOutcome] = []
    for outcome in outcomes:
        print(f"- {outcome.name}: {outcome.status}")
        if outcome.status != "pass":
            failures.append(outcome)

    if failures:
        print("")
        print("release readiness failed:")
        for outcome in failures:
            print(f"- {outcome.name}: {outcome.status}")
            if outcome.output:
                print(outcome.output)
        return 1

    print("")
    print("release readiness passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
