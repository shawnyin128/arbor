# Skill Authoring Quality Guard

Use this guard when creating or editing Arbor skills.

## Frontmatter

Skill descriptions are discovery triggers, not workflow summaries.

- Start descriptions with `Use when` for public skills or `Use only` for internal stages.
- Describe the situation that should load the skill: user intent, missing state, artifact type, or workflow position.
- Include key negative triggers when misrouting is common.
- Do not summarize the skill checklist, output packet, route sequence, or implementation process.
- Keep descriptions under 500 characters.

Bad:

```yaml
description: Clarify requirements, create artifacts, route to converge, and emit a structured packet.
```

Good:

```yaml
description: "Use when Arbor-managed work needs scope clarification, evidence-backed planning, feature splitting, acceptance criteria, or test planning before implementation."
```

## Body Structure

Keep high-stakes workflow boundaries explicit in the body:

- purpose and non-purpose;
- canonical examples for route calibration;
- ordered checklist;
- terminal states and next owner;
- anti-patterns that match observed failures;
- verification expectations for the specific artifact.

Do not move all workflow detail into frontmatter. If the description contains
enough process detail for an agent to act without reading the skill body, it is
too broad.

## Testing

Before publishing skill edits, record why the change is needed before changing
the skill body.

### Baseline Failure

Every Arbor skill-quality change needs one of these review evidence entries:

- an existing replay, fixture, or static check that already fails;
- a new failing replay, fixture, or static check added before the fix;
- an explicit static-only exception explaining why a dynamic failure is not
  practical for this change.

Use RED, GREEN, and REFACTOR headings in the review evidence for skill-quality
work:

- RED: the failing replay, fixture, static check, or static-only exception;
- GREEN: the smallest skill, reference, or checker change that satisfies the
  evidence;
- REFACTOR: cleanup after the proof stays green, or a statement that no cleanup
  was needed.

### Changed Skill Replay Map

Map changed public skills to the minimum replay set before claiming behavior
improved.

| Changed Skill | Minimum Replay Scope |
| --- | --- |
| `brainstorm` -> R01/R02/R27 plus direct-answer control R03 | Planning trigger, visible checkpoint, feature split, and direct-answer non-trigger. |
| `feedback` -> R32 plus direct-answer control | Feedback triage and a nearby direct response that must not enter Arbor workflow. |
| `converge` -> R04/R07/R21/R29/R30 plus a direct status control | Existing-loop continuation, repair, closure, informal evaluate wording, and non-workflow status answer. |

### Internal Stage Pressure Fixtures

Internal skills can use deterministic pressure fixtures when a real runtime
replay would be too expensive or would require calling an internal skill
directly from the user interface.

- `develop`: weak self-test, unapproved scope expansion, or missing acceptance
  mapping.
- `evaluate`: accepted-from-replay-only, missing negative probe, or vague
  evidence.
- `release`: checkpoint prose without a commit hash, implied public action, or
  dirty unrelated work.

Before publishing skill edits, run at least:

```bash
python3 plugins/arbor/skills/arbor/scripts/check_plugin_adapters.py
```

For routing, workflow, prompt, or visible-output changes, add or run a realistic
scenario replay or the strongest deterministic substitute, and label any live
runtime gap in review evidence.
