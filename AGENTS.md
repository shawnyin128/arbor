# Agent Guide

## Project Goal

Build Arbor as a small Codex skill/plugin system for the user's daily development workflow. The first skill is also named `arbor` and provides project initialization plus memory management.

## Project Constraints

- Discuss design and progress with the user in Chinese; keep code and project docs in English.
- Develop incrementally: design first, then one small feature, then focused unit and scenario tests, then review notes.
- Keep skill boundaries clear. A skill should control workflow and reduce drift, not limit the agent's normal reasoning or implementation ability.
- For `arbor`, fix the memory flow order but do not impose read-depth, commit-count, file-count, byte, or summary-size limits.
- Arbor hooks are project-level. The future plugin can distribute hook entrypoints, but `$arbor` should register them into the current project's hook configuration; hook execution must resolve the project root and read/write only that project's `AGENTS.md` and `.codex/memory.md`.
- Develop hook runtime one hook at a time: session startup first, in-session memory second, goal/constraint drift third.
- Do not commit or push unless the user explicitly asks.
- Keep transient current-session progress in `.codex/memory.md`; keep durable goals, constraints, and project map updates here.

## Project Map

- `docs/arbor-skill-design.md`: feature design, workflow boundaries, incremental development plan, and test plan.
- `docs/reviews/arbor-skill-review.md`: high-level review index and feature routing.
- `docs/reviews/arbor-final-delivery.md`: final current-scope delivery summary, validation snapshot, and handoff commands.
- `docs/reviews/features/`: detailed per-feature review files for progressive review reads.
- `.codex/hooks.json`: project-local Arbor hook contract with startup, memory hygiene, and AGENTS drift hook intents.
- `skills/arbor/SKILL.md`: user-facing skill trigger metadata and core operating workflow.
- `skills/arbor/references/`: templates copied into target projects.
- `skills/arbor/scripts/`: executable helpers for initialization, startup context collection, session startup hook execution, memory hygiene hook execution, AGENTS drift hook execution, and project hook registration.
- `plugins/arbor/`: repo-local Codex plugin package that distributes the accepted Arbor skill payload and hook contract.
- `scripts/eval_fixtures.py`: deterministic temporary project fixture builders for Stage B hook trigger dispatch evaluation.
- `scripts/simulated_dispatcher.py`: sidecar-backed simulated dispatcher adapter for Stage B harness plumbing.
- `scripts/evaluate_hook_triggers.py`: Stage B harness that executes selected hooks through project-registered `.codex/hooks.json` entrypoints, checks packet/side-effect assertions, and reports full-corpus hook execution-chain quality.
- `tests/test_arbor_skill.py`: unit and scenario tests for the skill scripts.
