---
name: arbor
description: Initialize, resume, and answer project-orientation questions with project-local Arbor memory under the Arbor workflow on Codex or Claude Code. Use when starting or resuming work in a repo, answering what a project does, summarizing repo purpose before work, creating `.arbor/memory.md`, migrating legacy `.codex/memory.md`, creating or updating `AGENTS.md`, generating a `CLAUDE.md` bridge on Claude Code installs, loading startup context from project docs, formatted git log, session memory, and git status, refreshing stale pre-triage observations, or detecting stable project guide, constraint, or project-map changes.
---

# Arbor

## Core Rule

Fix the workflow order, not the agent's reading depth. Keep Arbor outcome-first: recover the right project context, maintain short-term memory, and update the project guide or map when needed. Long-term context is distributed across `AGENTS.md`, git history, and project docs; `AGENTS.md` is the project guide and map, not the whole memory store. Do not impose commit counts, byte limits, file limits, documentation depth, or summary-size limits as part of this skill. Use scripts as helpers; continue reading whatever files, diffs, logs, or docs the task requires.

## Startup Workflow

When initializing, resuming, or orienting in a project:

1. Ensure `AGENTS.md` and `.arbor/memory.md` exist. Use `scripts/init_project_memory.py --root <project-root>` when useful. This explicit initialization flow migrates legacy `.codex/memory.md` by copying it to `.arbor/memory.md` when the canonical file is missing. When the script lives inside a Claude Code plugin cache, it also creates a short `CLAUDE.md` bridge pointing at `AGENTS.md` and `.arbor/memory.md`; the `--claude-bridge on|off` flag overrides this default.
2. Register project-local Arbor hook intents when the project should keep the workflow active. Use `scripts/register_project_hooks.py --root <project-root>` when useful. This writes `.codex/hooks.json` in the project and preserves unrelated hook entries.
3. Load startup context in this order:
   - `AGENTS.md`
   - formatted `git log`
   - `.arbor/memory.md`
   - `git status`
4. Use `scripts/collect_project_context.py --root <project-root>` when a deterministic ordered context packet is useful. The script does not decide how much context is enough.
5. Read additional docs, diffs, source files, or logs when the project map, task risk, or user request calls for them.

On Codex, `AGENTS.md` is the reliable native startup bootstrap. Do not assume `.codex/hooks.json` has already injected `arbor.session_startup_context`. For fresh sessions, resumed sessions, and project-overview prompts such as "what does this project do?", actively run or manually reproduce the startup context load before answering.

Collector sections include `Status`, `Source`, optional `Detail`, and raw body. Treat `missing`, `path-conflict`, `read-error`, `git-error`, and `empty` as fallback diagnostics, not blockers for reading later sections.

## Session Memory

Use `.arbor/memory.md` for short-term, pre-triage observations only:

- Undecided bugs, hypotheses, concerns, risks, and notes.
- Items not already resolved by git history.
- Items not already captured in `AGENTS.md`, project docs, review docs, task trackers, or committed history.

Before adding an item, triage whether it is already resolved or captured elsewhere. Remove items once they are resolved, committed, or moved to their durable home. Keep the file under 30 lines when practical.

### In-Flight Memory Guard

Every Arbor-managed workflow that leaves uncommitted project changes must ensure `.arbor/memory.md` exists and records the current in-flight state before the assistant stops or hands off to another skill. This is mandatory even when review documents or feature registry rows were updated: those artifacts hold evidence, while `.arbor/memory.md` keeps the short-term resume pointer for uncommitted work.

Use this guard whenever `git status --short` is non-empty because of Arbor workflow work:

- create `.arbor/memory.md` from `references/memory-template.md` if it is missing;
- record the active feature, changed artifact paths, current checkpoint, unresolved risks, and next expected skill or user action;
- keep the entry short and pre-triage; do not duplicate full review evidence;
- after a successful commit or after the state is moved to durable docs, remove or shrink resolved entries so memory reflects only unresolved uncommitted work.

Do not rely only on runtime hooks. Hooks may emit a hygiene packet, but the active Arbor skill is still responsible for making sure memory is current before ending with uncommitted work.

## Long-Term Context

Treat long-term context as a layered project record:

- `AGENTS.md` is the durable project guide and entrypoint: stable project goal, durable constraints, and a project map pointing to the right code and docs.
- `git log` is the completed-work history: committed features, fixes, and validation evidence.
- project docs are the deeper knowledge base: design notes, review docs, domain context, and detailed decisions.

Update `AGENTS.md` only when the stable guide or map should change. Do not compress all long-term memory into `AGENTS.md`. Put completed implementation history in commits, keep deeper durable knowledge in project docs, and keep only undecided transient observations in `.arbor/memory.md`.

### Guidance Placement Guard

Use `references/guidance-placement-guard.md` when deciding where agent-facing guidance belongs. The guard improves context quality without controlling how the agent reads, reasons, implements, or tests.

Default placement:

- Put durable repo goals, constraints, startup protocol, and map pointers in `AGENTS.md`.
- Keep Claude Code's `CLAUDE.md` as a short bridge to `AGENTS.md` and `.arbor/memory.md`; do not duplicate the project guide there.
- Put unresolved current-session state in `.arbor/memory.md`.
- Put repeatable task methods, workflow contracts, and domain-specific behavior in skills and skill references.
- Put append-only brainstorm, developer, evaluator, convergence, and release evidence in `docs/review/`.
- Put completed outcomes in git history and release/checkpoint evidence.
- Fetch or link volatile external context through tools, MCP servers, URLs, or task-specific docs instead of copying it into startup guidance.

Only add guidance to startup files when removing it would likely cause repeated mistakes across sessions. If guidance grows into examples, tutorials, file-by-file descriptions, or task-specific procedures, move those details to a referenced doc or skill. Do not impose fixed reading limits, mandatory plan-first behavior, mandatory subagents, fixed implementation strategies, or fixed test suites as part of placement guidance.

### Project Map Drift Guard

Before handoff, release, publish, or a session boundary after adding, removing, or renaming durable project entrypoints, run `scripts/run_agents_guide_drift_hook.py --root <project-root>` or reproduce its checks manually. The drift packet includes top-level project structure, mapped path validation, git status, and `Project Map Drift Candidates`. When that section reports `update-needed`, update only the `AGENTS.md` `Project Map` section before continuing unless each missing or stale path is intentionally excluded and the reason is recorded in review evidence or `.arbor/memory.md`.

Durable project-map entrypoints include stable top-level directories, new skills, hook adapters, runtime integration paths, shared helper modules, command/script roots, and project docs that future agents need for startup orientation. Do not add transient caches, pycache, scratch output, current-session implementation notes, or unresolved progress to `AGENTS.md`; those belong in ignored artifacts or `.arbor/memory.md`.

### Process State Authority Guard

Use `scripts/check_process_state.py --root <project-root>` when a managed Arbor workflow is about to stop, hand off, checkpoint, release, or publish and the current state needs an auditable consistency check. The checker is read-only: it validates feature-registry shape, review-document links, phase evidence, short-term memory for open work, stale in-flight memory after resolved work, and optional Release Round evidence for done features.

Treat normal warnings as migration or advisory evidence unless the current gate explicitly requires strictness. Use `--strict` or `--require-release-round-for-done` for release gates that should fail on those gaps. Do not use this guard to choose implementation steps, tests, routes, or feature priorities.

### Rendered Checkpoint Guard

Use `references/rendered-checkpoint-protocol.md` as the shared boundary for Arbor's user-visible workflow checkpoints. The raw `*.v1` packet is a runtime handoff; normal users should see the rendered checkpoint from `user_response` and `ui`.

The protocol applies only to Arbor workflow checkpoints and decision points. It must not force ordinary direct answers, read-only explanations, implementation strategy, testing strategy, or private reasoning into a template. For workflow checkpoints, the visible text must explain the current situation, what the checkpoint controls, evidence or findings, material defaults or judgment calls, and the next step in readable language.

Before claiming a workflow-facing change is validated, inspect the final rendered response when feasible. The tracked real-chain runner captures `final-response.md`; use it to reject raw schema leaks, route labels, terminal-state labels, unexplained internal ids, and missing required visible sections. Static fixture checks are preflight, not a substitute for real final-response inspection.

### Done-When Verification Thread

Use `references/done-when-verification-thread.md` as the shared cross-skill contract for proving Arbor-managed work. The thread starts in `brainstorm` with task-appropriate done-when criteria, continues in `develop` by mapping self-tests to those criteria, is challenged independently by `evaluate`, is checked for agreement by `converge`, and is confirmed by `release` as evidence existence rather than correctness re-evaluation.

The thread is evidence discipline, not a fixed testing strategy. It must not force one test type, full test suite, live runtime replay, subagent use, or plan-first behavior for direct tasks. Small direct answers and simple edits stay outside the managed verification thread.

### Loop Health Advisory

Use `references/loop-health-advisory.md` when a develop/evaluate correction loop shows repeated same-class failures, evidence conflicts, weak replay evidence, or context contamination. The advisory helps `evaluate` and `converge` recommend a narrower correction, re-brainstorming, stronger runtime replay, or a fresh-session handoff when the loop is becoming unreliable.

The advisory is not an automatic reset mechanism. It must not automatically clear context, spawn subagents, create worktrees, or require fan-out execution. Subagents and worktrees remain optional strategies, and normal correction loops should continue when the owner is clear, evidence is coherent, and the loop remains below the round limit.

## Runtime Entrypoints

Arbor runs the same workflow on Codex and Claude Code, but each runtime carries it through a different entrypoint surface. The shared project state is always `AGENTS.md` plus `.arbor/memory.md`; everything else is adapter-side.

- **Codex** auto-loads `AGENTS.md` natively. Project-level hook intents are registered in `.codex/hooks.json` via `scripts/register_project_hooks.py`, but they are hook contracts rather than proof that startup context has already entered the model input. The `AGENTS.md` Startup Protocol is the reliable Codex bootstrap and must tell the agent to run or manually reproduce `arbor.session_startup_context` on fresh/resumed/project-overview turns.
- **Claude Code** reads `CLAUDE.md` natively. When `init_project_memory.py` runs from a Claude Code plugin install, it generates a short `CLAUDE.md` bridge that points at `AGENTS.md` and `.arbor/memory.md` (the canonical Arbor state). The bundled `hooks/hooks.json` registers a `SessionStart` hook on `startup|resume` that injects the Arbor startup packet into the conversation, and a `Stop` hook that emits the memory hygiene packet when an Arbor-managed worktree is dirty. Goal/constraint drift is not auto-fired on Claude Code (no native event maps to it); invoke it through the user-driven workflows above.

The runtime is auto-detected from the script's installed cache path (`~/.codex/plugins/cache/...` vs `~/.claude/plugins/cache/...`). Override with `--claude-bridge on|off` on `init_project_memory.py` when needed.

## Project Hooks

Arbor hook registration is project-level. `.codex/hooks.json` is the Codex project contract for three hook intents:

- `arbor.session_startup_context`: load startup context in the required order.
- `arbor.in_session_memory_hygiene`: emit memory hygiene context so the agent can refresh `.arbor/memory.md` when uncommitted work or conversation state makes it stale.
- `arbor.goal_constraint_drift`: emit AGENTS drift context so the agent can update stable `AGENTS.md` goal, constraint, or map sections when needed.

The memory hygiene hook should be treated as high-recall around dirty Arbor workflow state. Prefer triggering it before stops, handoffs, release gates, commits, cache syncs, failed checks, or user review checkpoints when Arbor-managed changes are uncommitted. Suppress it for clean direct answers, read-only inspections with no unresolved Arbor state, explicit no-write turns, and unrelated dirty files outside Arbor scope.

Do not store Arbor hook state in user-global memory. Re-register hooks when needed; registration is idempotent and should preserve unrelated project hooks.

Claude Code does not have an equivalent project-level hook intent file. It ships two auto-fired Arbor adapters in `hooks/hooks.json`:

- `hooks/session-start` (`SessionStart`) calls `run_session_startup_hook.py` and applies a runtime-specific injection budget so the rendered packet stays under Claude Code's `additionalContext` cap.
- `hooks/stop-memory-hygiene` (`Stop`) is the Claude Code mapping of `arbor.in_session_memory_hygiene`. `Stop` is the only native Claude Code event whose output can re-enter the agent loop, so the adapter self-gates: it honors `stop_hook_active` first (so it can never loop), stays silent unless the project is Arbor-managed and the worktree is dirty, and otherwise blocks the stop with the `run_memory_hygiene_hook.py` packet as the block reason.

`arbor.goal_constraint_drift` has no native Claude Code event; it stays user/skill-driven there.

## Resources

- `references/memory-template.md`: template for `.arbor/memory.md`
- `references/agents-template.md`: template for `AGENTS.md`
- `references/claude-template.md`: bridge template for `CLAUDE.md` (Claude Code installs only)
- `references/project-hooks-template.md`: project hook contract
- `references/real-workflow-chain-review.md`: real-runtime chain review case matrix and release gate
- `references/process-state-authority.md`: source-of-truth map for Arbor workflow state
- `references/rendered-checkpoint-protocol.md`: shared user-visible checkpoint rendering contract
- `references/guidance-placement-guard.md`: placement rubric for startup guidance, memory, skills, review evidence, and external context
- `references/done-when-verification-thread.md`: cross-skill done-when criteria and verification evidence thread
- `references/loop-health-advisory.md`: advisory for repeated failures, evidence conflicts, weak replay, context contamination, and fresh-session handoff recommendations
- `scripts/init_project_memory.py`: create missing project memory files without overwriting existing files
- `scripts/collect_project_context.py`: collect startup context in the required order
- `scripts/run_session_startup_hook.py`: execute Hook 1 and forward optional agent-selected git log arguments
- `scripts/run_memory_hygiene_hook.py`: execute Hook 2 and forward optional agent-selected diff arguments
- `scripts/run_agents_guide_drift_hook.py`: execute Hook 3 and forward optional agent-selected project doc paths
- `scripts/check_process_state.py`: validate Arbor workflow state facts without mutating implementation or routing decisions
- `scripts/register_project_hooks.py`: create or update `.codex/hooks.json` with Arbor hook intents
- `scripts/check_real_workflow_chains.py`: execute real Codex/Claude workflow chain review cases
