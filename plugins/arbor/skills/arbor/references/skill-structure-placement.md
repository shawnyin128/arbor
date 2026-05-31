# Skill Structure Placement

Use this reference when creating or editing Arbor skill bodies.

The goal is to keep decisive behavior where the agent is likely to see it,
without turning word counts into a hard product limit.

## Front Body Shape

Prefer this order for a skill's main body:

1. Purpose
2. Critical Gates
3. Trigger/Non-trigger examples
4. Checklist
5. Red Flags
6. Output Contract
7. References

The exact headings can vary when an existing skill has stable local vocabulary,
but high-risk route, output, ownership, or authorization rules should appear in
the front 100 lines.

## Placement Rules

- Put mandatory visible-output contracts before long examples or schemas.
- Put authorization, release, or public-entrypoint red flags before long
  checklists.
- Keep bulky schema fields, scenario catalogs, and exhaustive examples in
  references when they are not needed for the first route decision.
- Track word-count trend before and after large skill-body edits, but treat
  budgets as guidance, not a hard product limit.

## Word-Count Guidance

| Skill Type | Main Body Target | Notes |
| --- | --- | --- |
| Public entrypoint | Under 3k words when practical. | Exceeding the target is acceptable when live routing/output evidence justifies it. |
| Internal schema-heavy stage | Under 3.5k words when practical. | Move exhaustive schema semantics into references when they obscure critical gates. |
| Framework utility skill | Keep normal visible output and repair boundaries near the top. | Scripts and references can hold deterministic details. |

Do not remove concrete examples or verification rules solely to hit a number.
Shorter skill files are useful only when the critical path becomes easier to
follow.
