#!/usr/bin/env python3
"""Validate Arbor's published context-only product boundary."""

from __future__ import annotations

import json
import sys
from pathlib import Path


sys.dont_write_bytecode = True

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = PLUGIN_ROOT.parents[1]
SKILLS_ROOT = PLUGIN_ROOT / "skills"
EXPECTED_VERSION = "2.0.2"

FORBIDDEN_SKILLS = {
    "brainstorm",
    "feedback",
    "converge",
    "develop",
    "evaluate",
    "release",
}

PUBLISHED_TEXT_FILES = [
    REPO_ROOT / "README.md",
    PLUGIN_ROOT / ".codex-plugin" / "plugin.json",
    PLUGIN_ROOT / ".claude-plugin" / "plugin.json",
    REPO_ROOT / ".agents" / "plugins" / "marketplace.json",
    REPO_ROOT / ".claude-plugin" / "marketplace.json",
    SKILLS_ROOT / "arbor" / "SKILL.md",
    SKILLS_ROOT / "arbor" / "agents" / "openai.yaml",
]
PUBLISHED_REFERENCE_ROOT = SKILLS_ROOT / "arbor" / "references"
PUBLISHED_HOOK_ROOT = PLUGIN_ROOT / "hooks"
PLUGIN_LEVEL_HOOK_MANIFEST = PLUGIN_ROOT / "hooks" / "hooks.json"

FORBIDDEN_PHRASES = [
    "$brainstorm",
    "$feedback",
    "$converge",
    "/arbor:brainstorm",
    "/arbor:feedback",
    "/arbor:converge",
    "develop/evaluate",
    "feature registry",
    "features.json",
    "workflow entrypoints",
    "managed quality loop",
    "workflow JSON",
]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_text(path: Path, failures: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        failures.append(f"{rel(path)} must be UTF-8 text: {exc}")
    except OSError as exc:
        failures.append(f"could not read {rel(path)}: {exc}")
    return ""


def load_json_object(path: Path, failures: list[str]) -> dict[str, object]:
    text = load_text(path, failures)
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        failures.append(f"{rel(path)} is invalid JSON: {exc}")
        return {}
    if not isinstance(data, dict):
        failures.append(f"{rel(path)} must be a JSON object")
        return {}
    return data


def validate_json(path: Path, failures: list[str]) -> None:
    load_json_object(path, failures)


def validate_version(failures: list[str]) -> None:
    codex_manifest = load_json_object(PLUGIN_ROOT / ".codex-plugin" / "plugin.json", failures)
    claude_manifest = load_json_object(PLUGIN_ROOT / ".claude-plugin" / "plugin.json", failures)
    readme = load_text(REPO_ROOT / "README.md", failures)
    for label, manifest in (("Codex", codex_manifest), ("Claude", claude_manifest)):
        actual = manifest.get("version")
        if actual != EXPECTED_VERSION:
            failures.append(f"{label} manifest version must be {EXPECTED_VERSION}, got {actual!r}")
    if f"Current version:\n\n```text\n{EXPECTED_VERSION}\n```" not in readme:
        failures.append(f"README Current version block must be {EXPECTED_VERSION}")


def published_text_files() -> list[Path]:
    files = list(PUBLISHED_TEXT_FILES)
    if PUBLISHED_REFERENCE_ROOT.is_dir():
        files.extend(sorted(PUBLISHED_REFERENCE_ROOT.glob("*.md")))
        files.extend(sorted(PUBLISHED_REFERENCE_ROOT.glob("*.json")))
    if PUBLISHED_HOOK_ROOT.is_dir():
        files.extend(sorted(path for path in PUBLISHED_HOOK_ROOT.iterdir() if path.is_file()))
    return files


def validate_skill_inventory(skills_root: Path, failures: list[str]) -> None:
    try:
        skill_dirs = sorted(path.name for path in skills_root.iterdir() if (path / "SKILL.md").is_file())
    except OSError as exc:
        failures.append(f"could not inspect published skills: {exc}")
        return
    if skill_dirs != ["arbor"]:
        failures.append(f"published skills must be exactly ['arbor'], got {skill_dirs}")


def main() -> int:
    failures: list[str] = []
    validate_version(failures)
    validate_skill_inventory(SKILLS_ROOT, failures)

    if PLUGIN_LEVEL_HOOK_MANIFEST.exists():
        failures.append(f"plugin-level hook manifest must not be published: {PLUGIN_LEVEL_HOOK_MANIFEST.relative_to(REPO_ROOT)}")

    for skill_name in sorted(FORBIDDEN_SKILLS):
        skill_dir = SKILLS_ROOT / skill_name
        if skill_dir.exists():
            failures.append(f"forbidden workflow skill directory exists: {skill_dir.relative_to(REPO_ROOT)}")

    for path in published_text_files():
        if not path.is_file():
            failures.append(f"published boundary file missing: {path.relative_to(REPO_ROOT)}")
            continue
        if path.suffix == ".json":
            validate_json(path, failures)
        text = load_text(path, failures)
        if not text:
            continue
        lowered = text.lower()
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in lowered:
                failures.append(f"forbidden workflow phrase {phrase!r} in {path.relative_to(REPO_ROOT)}")

    if failures:
        print("context boundary check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("context boundary check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
