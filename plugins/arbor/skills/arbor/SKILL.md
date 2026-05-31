---
name: arbor
description: "Initialize Arbor project state and run minimal deterministic Arbor framework checks on Codex or Claude Code: create or check `AGENTS.md`, `.arbor/memory.md`, the Claude `CLAUDE.md` bridge, Codex project hooks, Claude project hooks, and packaged hook definitions; report one strict file/hook table and no project summaries, health reports, process-state reports, migration advice, or maintenance suggestions."
---

# Arbor

## Core Rule

Fix the workflow order, not the agent's reading depth. Keep Arbor outcome-first:
initialize and check only Arbor-created or Arbor-managed framework files and
hook registration surfaces. `arbor` is not a generic project-summary skill and
must not turn memory prose into product status, feature recommendations, or
release advice. It is not a project-summary, project-status, resume-summary, or subjective health advice command. Ordinary
questions like "what does this repo do?", "where were we?", or "what is the
project status?" should load startup context when required by `AGENTS.md`, then
answer direct and source-grounded from sources without selecting `arbor`, unless
the user also asks to initialize Arbor or run an Arbor framework check. Long-term context is
distributed across `AGENTS.md`, git history, and project docs;
`AGENTS.md` is the project guide and map, not the whole memory store. Do not
impose commit counts, byte limits, file limits, documentation depth, or
summary-size limits as part of this skill. Use scripts as helpers; continue
reading whatever files, diffs, logs, or docs the task requires.

## Startup Workflow

When initializing, resuming, or checking Arbor state in a project:

1. Ensure `AGENTS.md`, `.arbor/memory.md`, and the current runtime's bootstrap files exist. Use `scripts/init_project_memory.py --root <project-root>` when useful, even when `AGENTS.md` and `.arbor/memory.md` already exist. This explicit initialization flow migrates legacy `.codex/memory.md` by copying it to `.arbor/memory.md` when the canonical file is missing. Runtime-specific adapter initialization is separate from canonical project state: a project first initialized from Codex still needs a later Claude Code initialization to create the short `CLAUDE.md` bridge pointing at `AGENTS.md` and `.arbor/memory.md`. When the script lives inside a Claude Code plugin cache, it creates that bridge automatically; the `--claude-bridge on|off` flag overrides this default.
2. Initialize hooks through the current runtime's own project surface. Use `scripts/diagnose_project_hooks.py --root <project-root> --plugin-root <arbor-plugin-root>` when the hook state is unclear; it separates intent-only files, executable wrappers, Claude plugin manifests, and runtime trust gaps. On Codex, register project-local Arbor hooks with `scripts/register_project_hooks.py --root <project-root>` when useful; this writes executable `.codex/hooks.json` entries plus project-local wrappers under `.codex/hooks/` and preserves unrelated hook entries. Codex may still require the user to trust those hooks through `/hooks`, so file presence is not proof that a hook fired. On Claude Code, the installed plugin ships `hooks/hooks.json` for plugin-level `SessionStart` and `Stop`; project-local `.claude/settings.json` plus `.claude/hooks/` wrappers remain an explicit per-project initialization path.
3. Load startup context in this order:
   - `AGENTS.md`
   - formatted `git log`
   - `.arbor/memory.md`
   - `git status`
4. Use `scripts/collect_project_context.py --root <project-root>` when a deterministic ordered context packet is useful. The script does not decide how much context is enough.
5. Read additional docs, diffs, source files, or logs when the project map, task risk, or user request calls for them.

On Codex, `AGENTS.md` is the reliable native startup bootstrap. Do not assume `.codex/hooks.json` has already injected `arbor.session_startup_context`. For
fresh sessions, resumed sessions, and project-overview prompts, actively run or
manually reproduce the startup context load before answering. That bootstrap
requirement is not a skill-selection rule: if the user asked for a normal
project overview, answer directly from loaded sources in a direct and source-grounded response rather than rendering an `arbor` status checkpoint. Use
`arbor` itself only for initialization, hook/context diagnosis, memory state,
project-guide state, and deterministic Arbor framework checks.

Collector sections include `Status`, `Source`, optional `Detail`, and raw body. Treat `missing`, `path-conflict`, `read-error`, `git-error`, and `empty` as fallback diagnostics, not blockers for reading later sections.

## User-Facing Output Boundary

Visible `arbor` output is a minimal deterministic framework check report, not a
project summary, not a subjective health assessment, and not a maintenance
report. Default `$arbor` runs in detect-only mode: it reports findings and does
not mutate files unless the user explicitly asks for framework repair. Prefer
`scripts/run_framework_check.py --root <project-root> --plugin-root <arbor-plugin-root>`
for deterministic checks, because it is the source of truth for the included
surfaces and output layout.

Use this fixed shape for normal visible output. The title must be exactly
`**Arbor Framework Check**`, and the `Mode: detect-only` line is mandatory for
default `$arbor` checks. No other normal sections are allowed:

```markdown
**Arbor Framework Check**
Project root: ...
Mode: detect-only
Runtime: codex|claude|both

| Surface | Required | Status | Evidence | Repair |
| --- | --- | --- | --- | --- |
| AGENTS.md | yes | pass | ... | none |
| .arbor/memory.md | yes | pass | ... | none |
| CLAUDE.md | no | not_applicable | ... | none |
| .codex/hooks.json + .codex/hooks/ | yes | missing | ... | run register_project_hooks.py --runtime codex |
| .claude/settings.json + .claude/hooks/ | no | not_applicable | ... | none |
| packaged Claude hook definitions | yes | pass | ... | none |

Result: pass|needs_repair|blocked
```

Allowed `Status` values are lowercase only: `pass`, `fail`, `missing`, `drift`,
`blocked`, and `not_applicable`.
Allowed `Required` values are lowercase only: `yes` and `no`.
Allowed `Result` values are lowercase only: `pass`, `needs_repair`, and
`blocked`.
Do not substitute softer labels such as `ok`, `healthy`, `repairable`,
`optional`, `present`, `clean`, `available`, `not configured`, or `external
verification`; map them to the fixed vocabulary instead. Do not use title-cased
variants such as `Pass`, `Fail`, `Warn`, `None`, `Automated`, or `Manual` in the
table.

The normal `$arbor` framework check includes only these surfaces:

- `AGENTS.md`
- `.arbor/memory.md`
- `CLAUDE.md`
- `.codex/hooks.json + .codex/hooks/`
- `.claude/settings.json + .claude/hooks/`
- `packaged Claude hook definitions`

Project-level hooks are required for the selected runtime. If `Runtime: codex`,
`.codex/hooks.json + .codex/hooks/` must be `Required: yes`. If
`Runtime: claude`, `.claude/settings.json + .claude/hooks/` must be
`Required: yes`. If `Runtime: both`, both project-level hook surfaces must be
required. Packaged Claude hook definitions are checked as shipped definitions,
but they do not satisfy missing Claude project hooks.

Do not include normal `$arbor` rows or sections for `docs/review/`,
`.arbor/workflow/features.json`, process-state validation, project guide/map
drift, git history, release/finalization, migration plans, feature registry
reconciliation, product status, memory resume summaries, or maintenance advice.
Do not use subjective report sections or wording such as `Framework Health`,
`Canonical state`, `Healthy`, `Maintenance blocker`, `Suggested Arbor maintenance actions`, `Suggested next actions`, `highest priority`, `worth
fixing`, or `No action required`.

## Framework Repair Mode

Run repair mode only when the user explicitly asks Arbor to repair or fix the
Arbor framework setup, or when the user selects a repair path from a detect-only
report. Use `scripts/run_framework_check.py --mode repair --root <project-root>`
and pass `--runtime codex`, `--runtime claude`, or `--runtime both` when the
target runtime is explicit. For Claude Code bridge repair, pass
`--claude-bridge on` when the user asked to initialize Claude Code support.

Repair mode may apply only safe, idempotent framework repairs:

- create missing `.arbor/memory.md`;
- create missing `AGENTS.md` from the Arbor template;
- create missing `CLAUDE.md` bridge when Claude support is requested;
- register or refresh Codex `.codex/hooks.json` and `.codex/hooks/` wrappers;
- register or refresh Claude `.claude/settings.json` and `.claude/hooks/` wrappers.

Repair mode must not silently apply policy-changing or destructive changes such
as `.gitignore` policy edits, deleting files, or rewriting durable project-guide
content. Invalid JSON, path conflicts, runtime trust, registry/review evidence
inconsistencies, and any issue that needs user judgment or another Arbor
workflow owner remain outside `$arbor` repair.

After any repair, rerun the framework check and report the before/after counts
plus the same fixed row table. Do not present repair mode as project progress,
release status, or a recommendation about the user's product work.

## Session Memory

Use `.arbor/memory.md` as the recovery file for current Arbor context that a
fresh agent needs to resume but cannot recover from committed history, durable
docs, stable project guidance, and git status alone.

Before adding an item, ask whether closing the session now would make the next
agent lose Arbor-relevant discussion, checkpoint files, unresolved decisions, or
the first resume action. Remove or shrink items once they are committed or moved
to a durable home. Keep the file short enough to read during startup.

### In-Flight Memory Guard

Every Arbor-managed workflow that leaves uncommitted or otherwise non-durable
resume context must ensure `.arbor/memory.md` exists and records the current
in-flight state before the assistant stops. This is mandatory even when review
documents or feature registry rows were updated: those artifacts hold evidence,
while `.arbor/memory.md` keeps the recovery pointer until startup context can
recover the state without conversation memory.

Use this guard whenever `git status --short` is non-empty because of Arbor workflow work:

- create `.arbor/memory.md` from `references/memory-template.md` if it is missing;
- record the active feature, changed artifact paths, current checkpoint, unresolved risks, and next expected skill or user action;
- keep the entry short and pre-triage; do not duplicate full review evidence;
- after a successful commit or after the state is moved to durable docs, remove or shrink resolved entries so memory reflects only unresolved uncommitted work.

The Stop hook is the automatic safety net and should run memory maintenance at
session boundaries, but active Arbor workflows should still avoid stopping with
known stale recovery context.

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

Use `scripts/check_process_state.py --root <project-root>` when a managed Arbor workflow is about to stop, hand off, checkpoint, release, or publish and the current state needs an auditable consistency check. The checker is read-only: it validates feature-registry shape, review-document links, phase evidence, checkpoint Release Round commit evidence, short-term memory for open work, stale in-flight memory after resolved work, and optional Release Round evidence for done features.

Treat normal warnings as migration or advisory evidence unless the current gate explicitly requires strictness. Use `--strict`, `--require-release-round-for-done`, or `--require-checkpoint-commit-evidence` for release gates that should fail on those gaps. Do not use this guard to choose implementation steps, tests, routes, or feature priorities.

### Rendered Checkpoint Guard

Use `references/rendered-checkpoint-protocol.md` as the shared boundary for Arbor's user-visible workflow checkpoints. The raw `*.v1` packet is a runtime handoff; normal users should see the rendered checkpoint from `user_response` and `ui`.

The protocol applies only to Arbor workflow checkpoints and decision points. It must not force ordinary direct answers, read-only explanations, implementation strategy, testing strategy, or private reasoning into a template. For workflow checkpoints, the visible text must explain the current situation, what the checkpoint controls, evidence or findings, material defaults or judgment calls, and the next step in readable language.

Before claiming a workflow-facing change is validated, inspect the final rendered response when feasible. The tracked real-chain runner captures `final-response.md`; use it to reject raw schema leaks, route labels, terminal-state labels, unexplained internal ids, and missing required visible sections. Static fixture checks are preflight, not a substitute for real final-response inspection.

### Done-When Verification Thread

Use `references/done-when-verification-thread.md` as the shared cross-skill contract for proving Arbor-managed work. The thread starts in `brainstorm` with task-appropriate done-when criteria, continues in `develop` by mapping self-tests to those criteria, is challenged independently by `evaluate`, is checked for agreement by `converge`, and is confirmed by `release` as evidence existence rather than correctness re-evaluation.

The thread is evidence discipline, not a fixed testing strategy. It must not force one test type, full test suite, live runtime replay, subagent use, or plan-first behavior for direct tasks. Small direct answers and simple edits stay outside the managed verification thread.

### Decision Trace Handoff

Use `references/decision-trace-handoff.md` to preserve decision continuity across Arbor workflow roles. Brainstorm records key decisions, rejected options, allowed implementation discretion, and decision invariants. Develop records implementation-time decisions and decision deviations against that trace. Evaluate checks decision drift and hidden decision conflict. Converge checks decision trace consistency before marking a feature done.

This is not a default multi-agent orchestration layer. It must not require subagents or worktrees, fan-out execution, fixed implementation strategy, or heavy workflow for direct tasks. The trace narrows only workflow evidence: it helps later stages understand the decisions that matter while preserving normal agent judgment inside the accepted scope.

### Delegation Packet And Effort Budget

Use `references/delegation-packet-effort-budget.md` only when optional delegation is useful for separable evidence gathering. A delegation packet names the objective, output format, tools/sources, boundaries, effort budget, context pointers, and stop conditions for a bounded investigation.

This is advisory, not a default multi-agent orchestration layer. Direct answers, simple edits, tightly coupled coding, and tightly coupled workflow changes remain single-threaded by default. The guidance must not require subagents or worktrees, fan-out execution, parallel coding, fixed tool-call counts, or a fixed implementation strategy.

### Outcome Evaluation And Observability

Use `references/outcome-eval-observability.md` to keep workflow validation outcome-first. Evaluate final state, checkpoint outcomes, rendered output, review evidence, process state, git/file side effects, real workflow replay, and trace evidence before arguing about exact path matching.

This guidance must not require LLM judges, fixed path matching, exact turn-by-turn replay, subagents, worktrees, fan-out execution, or one universal test type by default. When exact runtime telemetry or live proof is unavailable, label the strongest deterministic substitute as a weak pass and name the remaining proof.

### Loop Health Advisory

Use `references/loop-health-advisory.md` when a develop/evaluate correction loop shows repeated same-class failures, evidence conflicts, weak replay evidence, or context contamination. The advisory helps `evaluate` and `converge` recommend a narrower correction, re-brainstorming, stronger runtime replay, or a fresh-session handoff when the loop is becoming unreliable.

The advisory is not an automatic reset mechanism. It must not automatically clear context, spawn subagents, create worktrees, or require fan-out execution. Subagents and worktrees remain optional strategies, and normal correction loops should continue when the owner is clear, evidence is coherent, and the loop remains below the round limit.

## Runtime Entrypoints

Arbor runs the same workflow on Codex and Claude Code, but each runtime carries it through a different project-local entrypoint surface. The shared project state is always `AGENTS.md` plus `.arbor/memory.md`; everything else is adapter-side and not universal across runtimes.

- **Codex** auto-loads `AGENTS.md` natively. Project-level executable hooks are registered in `.codex/hooks.json` with wrappers under `.codex/hooks/` via `scripts/register_project_hooks.py`, but Codex may skip untrusted hooks until the user reviews them in `/hooks`. Validate hook firing in a trusted interactive Codex or desktop session; non-interactive `codex exec` runs are not a reliable proof that project hooks fired. The `AGENTS.md` Startup Protocol is the reliable Codex bootstrap and must tell the agent to run or manually reproduce `arbor.session_startup_context` on fresh/resumed/project-overview turns.
- **Claude Code** reads `CLAUDE.md` natively. When `init_project_memory.py` runs from a Claude Code plugin install, it generates a short `CLAUDE.md` bridge that points at `AGENTS.md` and `.arbor/memory.md` (the canonical Arbor state). This must still happen when Codex already created the canonical files; existing `AGENTS.md` and `.arbor/memory.md` are not proof that the Claude adapter was initialized. The plugin package ships `hooks/hooks.json` so Claude Code can register plugin-level `SessionStart` and `Stop` hooks after install. Project-level `.claude/settings.json` plus `.claude/hooks/` wrappers remain an explicit per-project path when local wrapper control is desired. `.codex/hooks.json` is not a Claude hook registration. Goal/constraint drift is not auto-fired on Claude Code (no native event maps to it); invoke it through the user-driven workflows above.

The runtime is auto-detected from the script's installed cache path (`~/.codex/plugins/cache/...` vs `~/.claude/plugins/cache/...`). Override with `--claude-bridge on|off` on `init_project_memory.py` when needed.

## Project Hooks

Arbor has runtime-specific hook surfaces. `.codex/hooks.json` plus `.codex/hooks/` is the Codex project surface for two executable hooks:

- `SessionStart`: delegates to `hooks/session-start`, which loads startup context in the required order.
- `Stop`: delegates to `hooks/stop-memory-hygiene`, which quietly runs Arbor
  context maintenance. The Stop path refreshes `.arbor/memory.md` recovery
  state when needed and applies conservative `AGENTS.md` Project Map drift
  updates for durable entrypoint changes.

The underlying Arbor hook intents remain `arbor.session_startup_context`, `arbor.in_session_memory_hygiene`, and `arbor.goal_constraint_drift`, but Codex has no native project-guide drift event. Guide drift stays skill-driven through `run_agents_guide_drift_hook.py`.

The Stop context-maintenance hook should be treated as high-recall around Arbor
resume state and durable guide drift. It should run before stops, handoffs,
release gates, commits, cache syncs, failed checks, or user review checkpoints
when Arbor-managed changes or guide/map drift may exist. Suppress mutation for
clean direct answers, read-only inspections with no unresolved Arbor state,
explicit no-write turns, and unrelated dirty files outside Arbor scope.

Do not store Arbor hook state in user-global memory. Re-register hooks when needed; registration is idempotent and should preserve unrelated project hooks.

Claude Code also has a packaged plugin hook manifest at `hooks/hooks.json` that calls the same shared adapters through `CLAUDE_PLUGIN_ROOT`. Codex project hooks are registered in `.codex/hooks.json` and call wrappers under `.codex/hooks/`. Claude Code project hooks are optionally registered in `.claude/settings.json` and call wrappers under `.claude/hooks/`. Those wrappers locate the installed Arbor plugin cache and delegate to the shared adapter scripts:

- `hooks/session-start` (`SessionStart`) calls `run_session_startup_hook.py` and applies a conservative runtime injection budget.
- `hooks/stop-memory-hygiene` (`Stop`) is the compatibility-named Stop
  context-maintenance adapter. It maps memory hygiene and conservative
  `AGENTS.md` Project Map drift maintenance onto each runtime's Stop event.
  `Stop` output can re-enter the agent loop as a visible continuation, so the
  adapter defaults to silent, non-blocking JSON with suppressed hook output. It
  honors `stop_hook_active` first so it can never loop. Set
  `ARBOR_STOP_MEMORY_HYGIENE_MODE=block` to opt into blocking with the
  `run_memory_hygiene_hook.py` packet as the block reason for memory debugging.

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
- `references/decision-trace-handoff.md`: decision trace handoff for key decisions, implementation-time decisions, decision drift checks, and optional delegation boundaries
- `references/delegation-packet-effort-budget.md`: optional delegation packet and effort budget guidance for bounded evidence gathering
- `references/outcome-eval-observability.md`: outcome-first evaluation and observable proof guidance for workflow changes
- `references/loop-health-advisory.md`: advisory for repeated failures, evidence conflicts, weak replay, context contamination, and fresh-session handoff recommendations
- `scripts/init_project_memory.py`: create missing project memory files without overwriting existing files
- `scripts/collect_project_context.py`: collect startup context in the required order
- `scripts/run_session_startup_hook.py`: execute Hook 1 and forward optional agent-selected git log arguments
- `scripts/run_memory_hygiene_hook.py`: execute Hook 2 and forward optional agent-selected diff arguments
- `scripts/run_agents_guide_drift_hook.py`: execute Hook 3 and forward optional agent-selected project doc paths
- `scripts/diagnose_project_hooks.py`: classify Codex and Claude hook surfaces as intent-only, executable wrapper state, Claude plugin manifest state, and trust gaps
- `scripts/check_process_state.py`: validate Arbor workflow state facts without mutating implementation or routing decisions
- `scripts/register_project_hooks.py`: create or update `.codex/hooks.json` plus `.codex/hooks/` wrappers on Codex, or `.claude/settings.json` plus `.claude/hooks/` wrappers on Claude Code
- `scripts/check_real_workflow_chains.py`: execute real Codex/Claude workflow chain review cases
