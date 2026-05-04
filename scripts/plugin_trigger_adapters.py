#!/usr/bin/env python3
"""Plugin trigger adapter boundary for Arbor hook trigger evaluation."""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import probe_plugin_runtime  # noqa: E402
import simulated_dispatcher  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SKILL_PATH = ROOT / "skills" / "arbor" / "SKILL.md"
HOOK_CONFIG_PATH = Path(".codex") / "hooks.json"
CODEX_BIN = Path("/Applications/Codex.app/Contents/Resources/codex")
TRIGGER_ADAPTER_STATE_PATHS = (
    Path("AGENTS.md"),
    Path(".codex") / "memory.md",
    Path(".codex") / "hooks.json",
)

TRIGGER_ADAPTERS = ("sidecar-baseline", "plugin-runtime-stub", "plugin-runtime-codex-exec")
TRIGGER_DECISION_KEYS = {
    "hooks",
    "decision",
    "confidence",
    "requires_agent_judgment",
    "optional_args",
    "reason",
}
DECISIONS = {"trigger", "none", "ambiguous"}
CONFIDENCE = {"high", "medium", "low"}
RUNTIME_DETAIL_MAX_CHARS = 500
SENSITIVE_OUTPUT_MARKERS = (
    "api key",
    "api_key",
    "authorization",
    "bearer ",
    "token",
)
ARBOR_HOOK_IDS = {
    "arbor.session_startup_context",
    "arbor.in_session_memory_hygiene",
    "arbor.goal_constraint_drift",
}
SIDECAR_SCORING_FIELDS = {
    "expected_label",
    "expected_hooks",
    "optional_expected_hooks",
    "forbidden_hooks",
    "allowed_decisions",
    "expectation",
    "overrides",
    "default_expectations",
    "note",
}
TRIGGER_DECISION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": sorted(TRIGGER_DECISION_KEYS),
    "properties": {
        "hooks": {
            "type": "array",
            "items": {"type": "string", "enum": sorted(ARBOR_HOOK_IDS)},
        },
        "decision": {"type": "string", "enum": sorted(DECISIONS)},
        "confidence": {"type": "string", "enum": sorted(CONFIDENCE)},
        "requires_agent_judgment": {"type": "boolean"},
        "optional_args": {
            "type": "object",
            "additionalProperties": False,
            "required": sorted(ARBOR_HOOK_IDS),
            "properties": {
                hook_id: {
                    "type": "array",
                    "items": {"type": "string"},
                }
                for hook_id in sorted(ARBOR_HOOK_IDS)
            },
        },
        "reason": {"type": "string"},
    },
}


class AdapterError(ValueError):
    """Raised when a plugin trigger adapter cannot produce a valid contract."""


@dataclass(frozen=True)
class RuntimeAdapterOptions:
    codex_bin: Path = CODEX_BIN
    timeout_seconds: int = 60
    auth_source_home: Path | None = None


TriggerAdapterSnapshot = dict[str, dict[str, Any]]


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise AdapterError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise AdapterError(f"cannot parse {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise AdapterError(f"expected JSON object in {path}")
    return data


def load_skill_metadata(path: Path = DEFAULT_SKILL_PATH) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise AdapterError(f"cannot read {path}: {exc}") from exc
    if not lines or lines[0] != "---":
        raise AdapterError(f"missing skill frontmatter in {path}")

    metadata: dict[str, str] = {}
    for line in lines[1:]:
        if line == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key in {"name", "description"}:
            metadata[key] = value.strip()
    if "name" not in metadata or "description" not in metadata:
        raise AdapterError(f"skill metadata must include name and description: {path}")
    return metadata


def sanitize_hook_contract(config: dict[str, Any]) -> dict[str, Any]:
    hooks = config.get("hooks")
    if not isinstance(hooks, list):
        raise AdapterError("hook contract must include a hooks list")
    sanitized_hooks: list[dict[str, Any]] = []
    for hook in hooks:
        if not isinstance(hook, dict):
            continue
        hook_id = hook.get("id")
        if not isinstance(hook_id, str):
            continue
        entrypoint = hook.get("entrypoint") if isinstance(hook.get("entrypoint"), dict) else {}
        sanitized_hooks.append(
            {
                "id": hook_id,
                "owner": hook.get("owner"),
                "event": hook.get("event"),
                "description": hook.get("description"),
                "entrypoint_type": entrypoint.get("type"),
                "optional_args": entrypoint.get("optional_args", []),
                "order": hook.get("order", []),
                "reads": hook.get("reads", []),
                "writes": hook.get("writes", []),
                "allowed_sections": hook.get("allowed_sections", []),
                "depth_policy": hook.get("depth_policy"),
            }
        )
    return {"version": config.get("version"), "hooks": sanitized_hooks}


def load_hook_contract(project_root: Path) -> dict[str, Any]:
    return sanitize_hook_contract(read_json_object(project_root / HOOK_CONFIG_PATH))


def summarize_project_state(fixture_summary: dict[str, Any]) -> dict[str, Any]:
    allowed_keys = {
        "project_root",
        "is_git_repo",
        "git_status_short",
        "has_agents",
        "has_memory",
        "has_hooks",
        "available_docs",
        "memory_state",
        "agents_state",
        "outside_path",
    }
    return {
        key: fixture_summary[key]
        for key in sorted(allowed_keys)
        if key in fixture_summary
    }


def build_plugin_runtime_input(
    expression: str,
    project_root: Path,
    fixture_summary: dict[str, Any],
    runtime_event: str = "user_expression",
) -> dict[str, Any]:
    payload = {
        "runtime_event": runtime_event,
        "expression": expression,
        "project_root": str(project_root),
        "project_state": summarize_project_state(fixture_summary),
        "hook_contract": load_hook_contract(project_root),
        "skill_metadata": load_skill_metadata(),
    }
    assert_no_sidecar_scoring_fields(payload)
    return payload


def assert_no_sidecar_scoring_fields(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in SIDECAR_SCORING_FIELDS:
                raise AdapterError(f"plugin runtime trigger input includes sidecar scoring field: {key}")
            assert_no_sidecar_scoring_fields(child)
    elif isinstance(value, list):
        for item in value:
            assert_no_sidecar_scoring_fields(item)


def validate_trigger_decision_contract(decision_payload: dict[str, Any]) -> dict[str, Any]:
    if set(decision_payload) != TRIGGER_DECISION_KEYS:
        raise AdapterError("plugin trigger output does not match the Arbor trigger decision contract keys")
    hooks = decision_payload["hooks"]
    if not isinstance(hooks, list) or not all(isinstance(item, str) for item in hooks):
        raise AdapterError("trigger decision hooks must be a list of strings")
    unknown_hooks = sorted(set(hooks) - ARBOR_HOOK_IDS)
    if unknown_hooks:
        raise AdapterError(f"trigger adapter selected unknown hook ids: {unknown_hooks}")

    decision = decision_payload["decision"]
    if decision not in DECISIONS:
        raise AdapterError(f"invalid trigger decision: {decision}")
    if decision != "trigger" and hooks:
        raise AdapterError("trigger adapter may only select hooks when decision is trigger")

    confidence = decision_payload["confidence"]
    if confidence not in CONFIDENCE:
        raise AdapterError(f"invalid trigger confidence: {confidence}")
    if not isinstance(decision_payload["requires_agent_judgment"], bool):
        raise AdapterError("requires_agent_judgment must be boolean")
    if not isinstance(decision_payload["reason"], str) or not decision_payload["reason"].strip():
        raise AdapterError("trigger reason must be a non-empty string")

    optional_args = decision_payload["optional_args"]
    if not isinstance(optional_args, dict):
        raise AdapterError("optional_args must be an object")
    for hook_id, args in optional_args.items():
        if hook_id not in ARBOR_HOOK_IDS:
            raise AdapterError(f"optional_args contains unknown hook id: {hook_id}")
        if not isinstance(args, list) or not all(isinstance(arg, str) for arg in args):
            raise AdapterError("optional_args values must be lists of strings")
    normalized_optional_args: dict[str, list[str]] = {}
    for hook_id, args in optional_args.items():
        normalized_args = normalize_hook_optional_args(hook_id, args)
        if normalized_args:
            normalized_optional_args[hook_id] = normalized_args
    if not set(normalized_optional_args) <= set(hooks):
        raise AdapterError("optional_args keys must be selected hooks")
    return {**decision_payload, "optional_args": normalized_optional_args}


def normalize_hook_optional_args(hook_id: str, args: list[str]) -> list[str]:
    if hook_id == "arbor.goal_constraint_drift":
        return normalize_doc_optional_args(args)
    if hook_id == "arbor.in_session_memory_hygiene":
        return normalize_single_value_option(args, "--diff-args")
    if hook_id == "arbor.session_startup_context":
        return normalize_single_value_option(args, "--git-log-args")
    return args


def normalize_doc_optional_args(args: list[str]) -> list[str]:
    tokens: list[str] = []
    for arg in args:
        if arg.startswith("--doc "):
            try:
                tokens.extend(shlex.split(arg))
            except ValueError:
                tokens.append(arg)
        else:
            tokens.append(arg)

    normalized: list[str] = []
    expecting_doc_value = False
    for token in tokens:
        if expecting_doc_value:
            if not token.strip() or token.startswith("-"):
                raise AdapterError("optional_args --doc requires a project-local doc path value")
            normalized.append(token)
            expecting_doc_value = False
            continue
        if token == "--doc":
            normalized.append("--doc")
            expecting_doc_value = True
            continue
        if token.startswith("--doc="):
            value = token.split("=", 1)[1].strip()
            if not value:
                raise AdapterError("optional_args --doc requires a project-local doc path value")
            normalized.extend(["--doc", value])
            continue
        if token.startswith("-"):
            raise AdapterError(f"unknown optional arg for arbor.goal_constraint_drift: {token}")
        normalized.extend(["--doc", token])
    if expecting_doc_value:
        raise AdapterError("optional_args --doc requires a project-local doc path value")
    return normalized


def normalize_single_value_option(args: list[str], option_name: str) -> list[str]:
    normalized: list[str] = []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == option_name:
            if index + 1 < len(args):
                value = args[index + 1].strip()
                if should_keep_single_value_option(value):
                    normalized.append(f"{option_name}={value}")
                index += 2
            else:
                index += 1
            continue
        if arg.startswith(f"{option_name} "):
            value = arg.removeprefix(f"{option_name} ").strip()
            if should_keep_single_value_option(value):
                normalized.append(f"{option_name}={value}")
        elif arg.startswith(f"{option_name}="):
            value = arg.split("=", 1)[1].strip()
            if should_keep_single_value_option(value):
                normalized.append(f"{option_name}={value}")
        else:
            value = arg.strip()
            if should_keep_single_value_option(value):
                normalized.append(f"{option_name}={value}")
        index += 1
    return normalized


def should_keep_single_value_option(value: str) -> bool:
    return bool(value) and value != "--"


def plugin_runtime_stub_trigger(plugin_runtime_input: dict[str, Any]) -> dict[str, Any]:
    assert_no_sidecar_scoring_fields(plugin_runtime_input)
    return {
        "hooks": [],
        "decision": "ambiguous",
        "confidence": "low",
        "requires_agent_judgment": True,
        "optional_args": {},
        "reason": "Plugin-runtime stub built non-circular input and abstained from semantic hook selection.",
    }


def sanitized_runtime_output(stdout: str, stderr: str) -> str:
    safe_lines: list[str] = []
    for line in f"{stdout}\n{stderr}".splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        lowered = stripped.lower()
        if any(marker in lowered for marker in SENSITIVE_OUTPUT_MARKERS):
            safe_lines.append("[redacted]")
        else:
            safe_lines.append(stripped)
    return " ".join(safe_lines)[:RUNTIME_DETAIL_MAX_CHARS]


def runtime_failure_detail(proc: subprocess.CompletedProcess[str]) -> str:
    output = sanitized_runtime_output(proc.stdout, proc.stderr)
    if not output:
        return f"returncode={proc.returncode}"
    return f"returncode={proc.returncode}; output={output}"


def runtime_blocker_decision(reason: str, detail: str | None = None) -> dict[str, Any]:
    detail_suffix = f"; detail: {detail}" if detail else ""
    return {
        "hooks": [],
        "decision": "ambiguous",
        "confidence": "low",
        "requires_agent_judgment": True,
        "optional_args": {},
        "reason": f"Plugin runtime unavailable: {reason}{detail_suffix}. Semantic hook selection was not measured.",
    }


def snapshot_trigger_adapter_state(project_root: Path) -> TriggerAdapterSnapshot:
    snapshot: TriggerAdapterSnapshot = {}
    for relative_path in TRIGGER_ADAPTER_STATE_PATHS:
        path = project_root / relative_path
        if path.is_file():
            snapshot[str(relative_path)] = {
                "kind": "file",
                "content": path.read_text(encoding="utf-8"),
            }
        elif path.exists():
            snapshot[str(relative_path)] = {"kind": "non_file", "content": None}
        else:
            snapshot[str(relative_path)] = {"kind": "missing", "content": None}
    return snapshot


def changed_trigger_adapter_paths(project_root: Path, before: TriggerAdapterSnapshot) -> list[str]:
    after = snapshot_trigger_adapter_state(project_root)
    return [
        relative_path
        for relative_path, before_state in before.items()
        if after.get(relative_path) != before_state
    ]


def remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def restore_trigger_adapter_state(project_root: Path, snapshot: TriggerAdapterSnapshot) -> None:
    for relative_path, state in snapshot.items():
        path = project_root / relative_path
        if path.exists() or path.is_symlink():
            remove_path(path)
        if state["kind"] == "file":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(state["content"] or "", encoding="utf-8")


def project_mutation_blocker(mutated_paths: list[str]) -> dict[str, Any]:
    return runtime_blocker_decision(f"project_file_mutation:{','.join(sorted(mutated_paths))}")


def build_codex_exec_trigger_prompt(plugin_runtime_input: dict[str, Any]) -> str:
    return (
        "You are evaluating Arbor plugin hook trigger behavior.\n"
        "Return only a JSON object matching the provided output schema.\n"
        "Do not execute hooks, edit files, initialize Arbor, or use expected labels.\n"
        "Select project-level Arbor hook ids only when the runtime input clearly calls for them.\n\n"
        "Hook selection boundaries:\n"
        "- Select arbor.session_startup_context for session start, resume, onboarding, orientation, "
        "or initializing the Arbor/project memory flow. Do not select memory hygiene only because "
        "the words memory flow appear during initialization.\n"
        "- Select arbor.in_session_memory_hygiene for current-session, temporary, in-flight, "
        "uncommitted, checkpoint, stale-memory, or not-long-term notes.\n"
        "- Select arbor.goal_constraint_drift for durable project goal, constraint, map, naming, "
        "architecture, or permanent workflow changes.\n"
        "- For runtime events about selected docs outside the project root, select the relevant "
        "hook if the event is otherwise an Arbor hook event; the hook execution layer enforces "
        "project-local safety. If project_state.outside_path is present for an AGENTS/doc drift "
        "event, pass it to arbor.goal_constraint_drift as a --doc optional arg.\n"
        "- For session-start events outside a project root, select no hooks.\n"
        "- If a request clearly says not to update a layer, do not select that layer's hook.\n\n"
        "Near-miss boundaries:\n"
        "- Do not select Arbor hooks for paragraph-local reminders, local variable names, or "
        "temporary editing notes that are not project session memory.\n"
        "- Do not select Arbor hooks for runtime memory, process memory, memory allocation, "
        "memory leaks, model memory, or domain/algorithm constraints unless the input clearly "
        "refers to .codex/memory.md, AGENTS.md, project constraints, or Arbor workflow state.\n\n"
        "Runtime input:\n"
        f"{json.dumps(plugin_runtime_input, indent=2, sort_keys=True)}"
    )


def run_codex_exec_trigger(
    plugin_runtime_input: dict[str, Any],
    project_root: Path,
    repo_root: Path = ROOT,
    codex_bin: Path = CODEX_BIN,
    timeout_seconds: int = 60,
    auth_source_home: Path | None = None,
) -> dict[str, Any]:
    assert_no_sidecar_scoring_fields(plugin_runtime_input)
    probe_plugin_runtime.ensure_codex_binary(codex_bin)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        home = tmp_root / "home"
        home.mkdir()
        marketplace = probe_plugin_runtime.add_marketplace(repo_root, home, codex_bin, timeout_seconds)
        if marketplace["status"] != "ok":
            return runtime_blocker_decision("marketplace_add_failed")
        if auth_source_home is not None:
            auth = probe_plugin_runtime.copy_runtime_auth(auth_source_home.expanduser().resolve(), home)
            if auth["status"] != "ok":
                return runtime_blocker_decision("auth_required")
        plugin_cache = probe_plugin_runtime.materialize_local_plugin_cache(repo_root, home)
        if plugin_cache["status"] != "ok":
            return runtime_blocker_decision(plugin_cache.get("reason", "plugin_cache_failed"))
        plugin_enable = probe_plugin_runtime.enable_arbor_plugin(home)
        if plugin_enable["status"] != "ok":
            return runtime_blocker_decision(plugin_enable.get("reason", "plugin_enable_failed"))

        schema_path = tmp_root / "trigger-decision.schema.json"
        output_path = tmp_root / "trigger-decision.json"
        schema_path.write_text(json.dumps(TRIGGER_DECISION_SCHEMA, indent=2, sort_keys=True), encoding="utf-8")
        state_before = snapshot_trigger_adapter_state(project_root)
        try:
            proc = probe_plugin_runtime.run_command(
                [
                    str(codex_bin),
                    "exec",
                    "--ephemeral",
                    "--json",
                    "-s",
                    "read-only",
                    "--skip-git-repo-check",
                    "--cd",
                    str(project_root),
                    "--output-schema",
                    str(schema_path),
                    "--output-last-message",
                    str(output_path),
                    build_codex_exec_trigger_prompt(plugin_runtime_input),
                ],
                cwd=project_root,
                env=probe_plugin_runtime.isolated_codex_env(home),
                timeout_seconds=timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            mutated_paths = changed_trigger_adapter_paths(project_root, state_before)
            if mutated_paths:
                restore_trigger_adapter_state(project_root, state_before)
                return project_mutation_blocker(mutated_paths)
            return runtime_blocker_decision("timeout")
        mutated_paths = changed_trigger_adapter_paths(project_root, state_before)
        if mutated_paths:
            restore_trigger_adapter_state(project_root, state_before)
            return project_mutation_blocker(mutated_paths)
        if proc.returncode != 0:
            return runtime_blocker_decision(
                probe_plugin_runtime.classify_exec_failure(proc),
                runtime_failure_detail(proc),
            )
        try:
            decision_payload = json.loads(output_path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise AdapterError(f"plugin runtime output file missing: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise AdapterError(f"plugin runtime output is not valid JSON: {exc}") from exc
        if not isinstance(decision_payload, dict):
            raise AdapterError("plugin runtime output must be a JSON object")
        return validate_trigger_decision_contract(decision_payload)


def plugin_runtime_codex_exec_trigger(
    plugin_runtime_input: dict[str, Any],
    project_root: Path,
    runtime_options: RuntimeAdapterOptions | None = None,
) -> dict[str, Any]:
    options = runtime_options or RuntimeAdapterOptions()
    return run_codex_exec_trigger(
        plugin_runtime_input,
        project_root,
        codex_bin=options.codex_bin,
        timeout_seconds=options.timeout_seconds,
        auth_source_home=options.auth_source_home,
    )


def trigger_with_adapter(
    trigger_adapter: str,
    scenario: simulated_dispatcher.TriggerScenario,
    project_root: Path,
    fixture_summary: dict[str, Any],
    runtime_options: RuntimeAdapterOptions | None = None,
) -> dict[str, Any]:
    if trigger_adapter == "sidecar-baseline":
        decision_payload = simulated_dispatcher.simulate_dispatch(scenario, fixture_summary)
    elif trigger_adapter == "plugin-runtime-stub":
        plugin_runtime_input = build_plugin_runtime_input(
            expression=scenario.expression,
            project_root=project_root,
            fixture_summary=fixture_summary,
        )
        decision_payload = plugin_runtime_stub_trigger(plugin_runtime_input)
    elif trigger_adapter == "plugin-runtime-codex-exec":
        plugin_runtime_input = build_plugin_runtime_input(
            expression=scenario.expression,
            project_root=project_root,
            fixture_summary=fixture_summary,
        )
        decision_payload = plugin_runtime_codex_exec_trigger(
            plugin_runtime_input,
            project_root,
            runtime_options=runtime_options,
        )
    else:
        raise AdapterError(f"unknown plugin trigger adapter: {trigger_adapter}")
    return validate_trigger_decision_contract(decision_payload)
