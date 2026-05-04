# Feature 13 Review: Plugin Trigger Adapter Design

## Purpose

Define the next-phase adapter boundary for replacing Arbor's sidecar-backed trigger baseline with a real plugin/runtime trigger path.

## Scope

In scope:

- Preserve the existing trigger decision contract.
- Define a swappable adapter boundary for sidecar baseline and plugin runtime trigger implementations.
- Define non-circular evaluation rules so the plugin runtime trigger path cannot read expected labels or sidecar scoring fields.
- Define validation gates before reporting semantic precision, recall, false-positive, ambiguity, multi-hook, and stability metrics.
- Update high-level review routing for the new post-completion phase.

Out of scope:

- Implementing a real runtime/plugin trigger adapter.
- Calling a model or external runtime.
- Reporting real semantic metrics.
- Changing hook scripts, hook registration, fixture builders, or sidecar expectations.

## Trigger Decision Contract

The plugin runtime trigger adapter must return the same JSON shape as the sidecar baseline:

```json
{
  "hooks": ["arbor.in_session_memory_hygiene"],
  "decision": "trigger",
  "confidence": "high",
  "requires_agent_judgment": false,
  "optional_args": {
    "arbor.in_session_memory_hygiene": []
  },
  "reason": "The user asked to refresh short-term memory for uncommitted work."
}
```

Allowed decisions:

- `trigger`
- `none`
- `ambiguous`

Allowed hooks:

- `arbor.session_startup_context`
- `arbor.in_session_memory_hygiene`
- `arbor.goal_constraint_drift`

Allowed confidence values:

- `high`
- `medium`
- `low`

## Adapter Input

The plugin runtime trigger adapter can receive:

- user expression or runtime event text;
- project root;
- fixture summary or live project summary;
- project-local hook contract from `.codex/hooks.json`;
- concise skill trigger metadata from `SKILL.md`;
- optional project-state signals already available to the runtime, such as missing `AGENTS.md`, missing `.codex/memory.md`, git status class, available selected docs, and runtime event type.

The plugin runtime trigger adapter must not receive:

- expected label;
- expected hooks;
- optional expected hooks;
- forbidden hooks;
- allowed decisions;
- scenario note as scoring guidance;
- any other sidecar scoring field.

## Design Notes

Feature 13 is intentionally a design feature. The current Arbor scope is already complete; this begins a new phase whose first task is preventing the semantic evaluation from becoming circular.

The existing `scripts/simulated_dispatcher.py` remains useful as a sidecar-baseline adapter because it exercises the trigger decision contract and hook execution harness. The plugin runtime trigger adapter should be plugged into the same harness through an adapter-selection surface, for example:

```bash
python3 scripts/evaluate_hook_triggers.py --all --trigger-adapter sidecar-baseline --work-root /private/tmp/arbor-sidecar
python3 scripts/evaluate_hook_triggers.py --all --trigger-adapter plugin-runtime --work-root /private/tmp/arbor-plugin
```

The exact adapter name and implementation can change in Feature 14, but the scoring boundary should not: expected sidecar fields are for the evaluator, not for the plugin trigger adapter.

## Test Plan

Unit tests:

- Adapter output schema accepts only the known keys and vocabularies.
- Unknown hook ids fail as `trigger_gap`.
- Invalid JSON or missing fields fail as `trigger_gap`.
- Optional args can only be keyed by selected hooks.
- Plugin-runtime input builder excludes sidecar scoring fields.

Scenario tests:

- Run a representative subset with both sidecar baseline and plugin runtime trigger adapter through the same harness path.
- Run the full corpus with the plugin runtime trigger adapter and compare observed labels against the sidecar.
- Verify no expected-label data is present in the plugin runtime trigger input.
- Verify hook execution assertions still pass after plugin trigger adapter selection.

Metric tests:

- Report semantic metrics only for plugin runtime trigger output.
- Do not report H1/H2/H3 precision/recall for sidecar-backed baseline output.
- Compute `NONE` and near-miss false-positive rates only from observed real decisions.
- Report ambiguous-case handling and multi-hook partial-match with scenario ids for failures.
- Repeat real adapter runs at least 3 times before reporting stability.

## Acceptance Gates

- Existing sidecar-backed harness remains passing.
- Plugin runtime trigger output validates against the trigger decision contract.
- Plugin runtime trigger input has no access to expected hooks or forbidden hooks.
- Full-corpus plugin-runtime report contains both semantic metrics and hook execution metrics.
- Hook execution metrics remain at prior gates: 100% selected-hook execution pass rate, 0 outside-root leaks, and 0 unintended writes.

## Validation

- `python3 -m unittest tests/test_arbor_skill.py`: 102 tests passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- Runtime code was not changed in Feature 13.

## Developer Response

Feature 13 defines the plugin trigger adapter boundary and metric gates. It does not implement the plugin runtime trigger adapter yet. The next feature should add the adapter-selection surface and a plugin-runtime stub that proves the harness can swap trigger paths without exposing sidecar scoring fields.
