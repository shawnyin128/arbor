#!/usr/bin/env python3
"""Validate Arbor's portable Agent Plugins core and client adapter parity."""

from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path


sys.dont_write_bytecode = True

SCRIPT_ROOT = Path(__file__).resolve().parent
PLUGIN_ROOT = SCRIPT_ROOT.parents[2]
AGENT_PLUGIN_MANIFEST = PLUGIN_ROOT / "plugin.json"
CODEX_MANIFEST = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
CLAUDE_MANIFEST = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
SKILLS_ROOT = PLUGIN_ROOT / "skills"
AGENT_PLUGINS_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
ALLOWED_AGENT_PLUGIN_KEYS = {
    "$schema",
    "name",
    "version",
    "description",
    "author",
    "homepage",
    "repository",
    "license",
    "keywords",
    "extensions",
}
SHARED_METADATA_KEYS = ("name", "version", "description", "author", "homepage", "repository", "license")


def load_json_object(path: Path, failures: list[str]) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        failures.append(f"missing JSON file: {path}")
        return {}
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        failures.append(f"could not read JSON object {path}: {exc}")
        return {}
    if not isinstance(value, dict):
        failures.append(f"JSON file must contain an object: {path}")
        return {}
    return value


def validate_portable_package(root: Path) -> list[str]:
    failures: list[str] = []
    manifest = load_json_object(root / "plugin.json", failures)
    if manifest:
        unknown = sorted(set(manifest) - ALLOWED_AGENT_PLUGIN_KEYS)
        if unknown:
            failures.append(f"portable manifest has non-standard top-level keys: {', '.join(unknown)}")
        if manifest.get("$schema") != AGENT_PLUGINS_SCHEMA:
            failures.append(f"portable manifest must target {AGENT_PLUGINS_SCHEMA}")
        name = manifest.get("name")
        name_is_valid = (
            isinstance(name, str)
            and re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", name) is not None
            and len(name) <= 64
            and "--" not in name
            and ".." not in name
        )
        if not name_is_valid:
            failures.append("portable manifest name must use Agent Plugins lowercase naming")

    skills_root = root / "skills"
    if not skills_root.is_dir():
        failures.append("portable package must contain a skills directory")
    else:
        skills = sorted(path.name for path in skills_root.iterdir() if (path / "SKILL.md").is_file())
        if skills != ["arbor"]:
            failures.append(f"portable package must expose exactly the arbor skill, got {skills!r}")

    legacy_hook_manifest = root / "hooks" / "hooks.json"
    if legacy_hook_manifest.exists():
        failures.append("portable package must not publish hooks/hooks.json")
    return failures


def validate_adapter_parity(root: Path) -> list[str]:
    failures: list[str] = []
    portable = load_json_object(root / "plugin.json", failures)
    codex = load_json_object(root / ".codex-plugin" / "plugin.json", failures)
    claude = load_json_object(root / ".claude-plugin" / "plugin.json", failures)
    for field in SHARED_METADATA_KEYS:
        expected = portable.get(field)
        for runtime, manifest in (("Codex", codex), ("Claude", claude)):
            if manifest.get(field) != expected:
                failures.append(
                    f"{runtime} adapter {field!r} must match portable manifest: "
                    f"expected {expected!r}, got {manifest.get(field)!r}"
                )
    return failures


def run_fixture_tests() -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="arbor-agent-plugin-contract-") as temp_dir:
        root = Path(temp_dir)
        (root / "skills" / "arbor").mkdir(parents=True)
        (root / "skills" / "arbor" / "SKILL.md").write_text("---\nname: arbor\ndescription: test\n---\n", encoding="utf-8")
        (root / "plugin.json").write_text(
            json.dumps({"$schema": AGENT_PLUGINS_SCHEMA, "name": "arbor"}),
            encoding="utf-8",
        )
        if validate_portable_package(root):
            failures.append("valid portable fixture was rejected")

        (root / "plugin.json").write_text(json.dumps({"name": "Arbor", "skills": "./skills"}), encoding="utf-8")
        fixture_failures = validate_portable_package(root)
        if not any("must target" in failure for failure in fixture_failures):
            failures.append("fixture without $schema was accepted")
        if not any("non-standard" in failure for failure in fixture_failures):
            failures.append("fixture with legacy skills field was accepted")
        if not any("lowercase naming" in failure for failure in fixture_failures):
            failures.append("fixture with invalid name was accepted")

        (root / "plugin.json").write_text(
            json.dumps({"$schema": AGENT_PLUGINS_SCHEMA, "name": "arbor"}),
            encoding="utf-8",
        )
        (root / "skills" / "arbor" / "SKILL.md").unlink()
        (root / "skills" / "arbor" / "nested").mkdir()
        (root / "skills" / "arbor" / "nested" / "SKILL.md").write_text("---\nname: nested\ndescription: test\n---\n", encoding="utf-8")
        if not any("exactly the arbor skill" in failure for failure in validate_portable_package(root)):
            failures.append("nested SKILL.md was incorrectly discovered")
    return failures


def main() -> int:
    failures = run_fixture_tests()
    failures.extend(validate_portable_package(PLUGIN_ROOT))
    failures.extend(validate_adapter_parity(PLUGIN_ROOT))
    if failures:
        print("Agent Plugins contract check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("Agent Plugins contract check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
