# Arbor Skill Design

## Purpose

Build a Codex skill that keeps project context stable across daily development sessions by combining:

- Short-term memory: undecided pre-triage observations about current uncommitted work, stored in project-local `.codex/memory.md`.
- Long-term memory: durable project context recovered from `AGENTS.md`, formatted `git log`, and progressively read project docs.
- Workflow guardrails: startup context loading, in-session memory refresh, and project goal/constraint updates.

The first deliverable is a standalone project-level skill. A later Arbor plugin should distribute the same skill plus project-scoped lifecycle hooks.

The second deliverable is a repo-local Arbor plugin package that ships the accepted standalone skill and hook contract without adding semantic dispatch yet. Plugin-based trigger evaluation remains a later Stage B concern.

## Non-Goals

- Do not restrict the agent's normal coding, review, or reasoning ability.
- Do not replace git history, project docs, or issue trackers.
- Do not require a heavyweight database or external service.
- Do not make automatic commits or pushes.
- Do not silently rewrite project goals or constraints without making the change visible.

## Core Boundary

The skill controls context gathering and memory hygiene. It should not dictate how the agent implements unrelated user tasks.

The skill fixes process order, not context depth. Do not hard-code read limits, commit counts, file counts, summary sizes, or documentation depth as workflow constraints. If scripts expose knobs such as `--log-format`, `--since`, or `--max-bytes`, treat them as optional agent-controlled parameters, not defaults that narrow the agent's authority. The agent should decide how much to read based on the task, repository size, risk, and available context.

The skill can provide:

- Triggering language in `SKILL.md`.
- A concise operating workflow.
- Reusable scripts for deterministic initialization, context collection, and validation.
- Templates for `.codex/memory.md` and `AGENTS.md`.

The skill cannot, by itself, guarantee true automatic session-start hooks in every runtime. For phase 1, hooks are represented as explicit skill workflows and script entrypoints. When the Arbor plugin exists, invoking `$arbor` in a project should register those entrypoints into that project's hook configuration.

Feature 3 introduces the first visible project hook artifact: `.codex/hooks.json`. It is an Arbor project-level hook contract that a later plugin can adapt to runtime-specific hook APIs.

## Prompt Design Guidance

Arbor skill development should follow GPT-5.5-style prompt guidance:

- Prefer outcome-first instructions over process-heavy prompt stacks.
- Keep `SKILL.md` concise; move large examples, scenario corpora, and evaluation details into references or review docs.
- Define success criteria, side-effect boundaries, validation expectations, and stopping conditions.
- Give the agent room to choose the efficient solution path once the Arbor memory flow order and project-local boundaries are fixed.
- Use strict words such as `must`, `only`, and `never` for true invariants: project-local state, no fixed read limits, no unintended writes, and no commit or push unless requested.
- Treat retrieval budgets as agent-selected stopping rules, not hard Arbor read-depth limits.
- For tool-heavy workflows, use brief user-visible preambles and preserve phase semantics in future plugin/runtime integrations.

This means Arbor should not grow by adding more prompt process for every edge case. New complexity should usually become one of:

- a script with clear inputs, outputs, and side-effect behavior;
- a reference file loaded only when needed;
- a review/evaluation artifact outside the skill body;
- or a future plugin/runtime dispatcher concern.

## Hook Distribution Model

Hooks should ship with the future Arbor plugin, not as standalone global behavior. The plugin may be installed in a user-level Codex location, but invoking `$arbor` should register hooks into the current project's hook configuration. Every hook must execute against the resolved current project root.

Registration flow:

1. User invokes `$arbor` in a project.
2. Arbor resolves the project root.
3. Arbor initializes `AGENTS.md` and `.codex/memory.md` if needed.
4. Arbor registers the session startup, in-session memory, and goal/constraint drift hooks in the project's hook configuration.
5. Registered hooks call Arbor plugin entrypoints, but all state reads/writes remain project-local.

Project-level guarantees:

- Resolve the project root before any hook action.
- Store hook registration in the project, not in user-global state.
- Read and write only project-local memory files: `AGENTS.md` and `.codex/memory.md`.
- Treat the plugin installation as code distribution only, not as shared memory storage.
- Do not read or write a user-level/global Arbor memory file unless a future design explicitly adds one.
- If no project root can be resolved, no-op or ask to initialize a project instead of writing outside the project.
- Keep hook decisions visible through project files or chat output.

Hook entrypoints:

- Session startup hook: run the startup context flow for the current project root.
- In-session memory hook: refresh `.codex/memory.md` only for the current project when pre-triage observations become stale.
- Goal/constraint drift hook: emit an AGENTS drift packet for the current project so the running agent can update only durable goal, constraint, or project-map sections when needed.

Hook implementation order:

1. Implement and review the session startup hook.
2. Implement and review the in-session memory hook.
3. Implement and review the goal/constraint drift hook.

Do not design detailed constraints for a later hook before the earlier hook has an executable, reviewed path. Feature 3 only registers hook intents; later features should turn one hook intent at a time into a concrete workflow.

## Target Skill Shape

Skill name: `arbor`

Proposed folder:

```text
arbor/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── scripts/
│   ├── init_project_memory.py
│   ├── collect_project_context.py
│   ├── run_session_startup_hook.py
│   ├── run_memory_hygiene_hook.py
│   ├── run_agents_guide_drift_hook.py
│   └── register_project_hooks.py
└── references/
    ├── memory-template.md
    ├── agents-template.md
    └── project-hooks-template.md
```

The skill body should stay short. Detailed templates and script behavior should live in `references/` and `scripts/`.

## Target Plugin Shape

Plugin name: `arbor`

Proposed folder:

```text
plugins/arbor/
├── .codex-plugin/
│   └── plugin.json
├── hooks.json
└── skills/
    └── arbor/
        ├── SKILL.md
        ├── agents/
        │   └── openai.yaml
        ├── scripts/
        └── references/
```

The plugin package should distribute code and hook contracts only. It should not introduce a runtime semantic dispatcher in Feature 7. Calling `$arbor` should still initialize project-local files and register hooks into the current project's `.codex/hooks.json`.

Plugin packaging rules:

- Keep `plugins/arbor/skills/arbor` synchronized with `skills/arbor` until a later refactor chooses a single source of truth.
- Keep `plugins/arbor/hooks.json` synchronized with `register_project_hooks.py` canonical Arbor hook definitions.
- Keep manifest metadata concrete and free of scaffold TODO placeholders.
- Do not add marketplace registration unless explicitly requested.
- Do not add MCP servers, apps, or auth flows for Feature 7.

## Project Files Managed By The Skill

### `.codex/memory.md`

Purpose: short-term session memory for undecided observations about current uncommitted work.

Minimum sections:

```text
# Session Memory

## Observations

## In-flight
```

Rules:

- Treat git status as supporting evidence, not the source of truth.
- Keep only undecided observations: bugs, hypotheses, concerns, risks, and notes.
- Remove items when they are resolved, committed, or captured in docs/review artifacts.
- Do not duplicate `AGENTS.md`, project docs, task trackers, review docs, or committed history.
- Keep the file under 30 lines when practical.

### `AGENTS.md`

Purpose: durable project map and project-level operating rules.

Required sections:

```text
# Agent Guide

## Project Goal

## Project Constraints

## Project Map
```

Rules:

- Update `Project Goal` when the product or development objective changes.
- Update `Project Constraints` when durable engineering constraints, workflows, or non-negotiables change.
- Update `Project Map` when major directories, modules, commands, or architecture boundaries change.
- Keep details that are only about current uncommitted work in `.codex/memory.md`, not `AGENTS.md`.

## Workflow Hooks

### Hook 1: Session Startup Context Load

Trigger intent:

- A session starts in a project repo.
- The user asks to initialize, resume, onboard, or continue project work.
- A later plugin calls the startup entrypoint automatically.

Read order:

1. `AGENTS.md`
2. formatted `git log`
3. `.codex/memory.md`
4. `git status`

Depth policy:

- Preserve this read order.
- Do not impose a fixed number of commits, docs, files, or bytes.
- Let the agent choose whether to read full files, summaries, selected ranges, diffs, docs, or additional project artifacts.
- Scripts may expose parameters to make that choice convenient, but the skill should not turn those parameters into mandatory limits.

Output expectation:

- Brief working context summary.
- Current short-term memory risks.
- Whether memory appears stale.
- Any missing setup files.

Initial command shape:

```bash
python scripts/collect_project_context.py --root <project-root>
```

### Hook 2: In-Session Memory Refresh

Trigger intent:

- The agent notices that `.codex/memory.md` is stale.
- The user changes direction.
- A task reaches a meaningful checkpoint without a commit.
- `git status` shows uncommitted changes that are not reflected in memory.

Refresh source:

- Conversation summary since the last refresh.
- `git diff --stat` and selected diffs when needed.
- `git status --short`.
- Existing `.codex/memory.md`.
- Additional files, diffs, logs, or docs selected by the agent when needed.

Output expectation:

- Updated `.codex/memory.md`.
- Explicit note about completed, pending, and risky uncommitted work.
- No durable project rules added unless they belong in `AGENTS.md`.

### Hook 3: Goal Or Constraint Drift Detection

Trigger intent:

- The user changes the project objective.
- The user introduces a durable workflow constraint.
- The implementation reveals that the project map is obsolete.

Behavior:

- Emit an AGENTS drift packet with `AGENTS.md`, `git status --short`, and optional agent-selected project-local docs.
- Let the running agent decide whether to make a targeted `AGENTS.md` update.
- Keep any update narrow to `Project Goal`, `Project Constraints`, or `Project Map`.
- Do not move short-term progress notes into `AGENTS.md`.
- Do not update `.codex/memory.md` from this hook.

## Incremental Development Plan

### Feature 0: Design And Review Setup

Deliverables:

- Design document.
- Review document with target and scope prefilled.

Validation:

- Confirm docs define scope, non-goals, hook semantics, and test strategy.

### Feature 1: Arbor Initializer

Deliverables:

- Skill scaffold.
- `init_project_memory.py`.
- Startup memory flow entrypoint.
- `collect_project_context.py`.
- Templates for `.codex/memory.md` and `AGENTS.md`.

Behavior:

- Create `.codex/memory.md` if missing.
- Create `AGENTS.md` if missing.
- Preserve existing files by default.
- Support a dry-run mode.
- Run or describe the full startup memory flow in order: `AGENTS.md`, formatted `git log`, `.codex/memory.md`, and `git status`.
- Expose parameters for git log formatting or depth only as agent-selected options.
- Avoid fixed read limits in the skill workflow.

Unit tests:

- Creates both files in an empty temp project.
- Preserves existing content.
- Creates `.codex/` when missing.
- Reports non-git projects without failing initialization.
- Maintains the required startup read order.

Scenario tests:

- New project with no git repo.
- Existing git repo with missing memory files.
- Existing project with user-authored `AGENTS.md`.
- Existing git repo where the agent requests a broader git log or deeper docs read.

### Feature 2: Startup Context Collector

Deliverables:

- Hardening for `collect_project_context.py`.
- Additional scenario coverage for larger repos, docs pointers, and agent-selected git log formats.
- Startup workflow refinements in `SKILL.md`.

Behavior:

- Preserve the existing required order: `AGENTS.md`, formatted git log, `.codex/memory.md`, `git status`.
- Render each source as a diagnostic section with `Status`, `Source`, optional `Detail`, and original body.
- Distinguish `ok`, `empty`, `missing`, `path-conflict`, `read-error`, and `git-error`.
- Keep collecting later sections after earlier sections fail.
- Preserve raw content and large outputs; do not summarize or truncate.
- Leave follow-up read depth to the agent.

Unit tests:

- Handles missing `AGENTS.md`.
- Handles missing `.codex/memory.md`.
- Handles non-git directories.
- Handles file path conflicts.
- Handles file read errors.
- Keeps read order stable.
- Does not enforce a hard-coded git log count or documentation depth.

Scenario tests:

- Git repo with clean status.
- Git repo with uncommitted changes.
- Repo with stale memory marker.
- Large file content is preserved.
- Agent-selected git log depth is respected without becoming the default.

### Feature 3: Project Hook Registration Skeleton

Deliverables:

- `register_project_hooks.py`.
- Project-local hook configuration template.
- `SKILL.md` workflow update that explains when to register or inspect hooks.
- Feature review file for hook registration behavior.

Behavior:

- Create or update only project-local hook configuration.
- Use `.codex/hooks.json` as the first visible project-level hook contract.
- Register the three Arbor hook intents: session startup context load, in-session memory hygiene, and goal/constraint drift update.
- Keep hook registration visible in project files.
- Point hook entries at Arbor entrypoints while keeping all state reads and writes in the current project.
- Treat memory freshness as part of the in-session hook workflow, not as a standalone semantic checker.
- Use mechanical context for fallback: existing `.codex/memory.md`, `git status --short`, selected diffs when the agent decides they are needed, and recent conversation context available to the running agent.
- Ask the agent to update memory when uncommitted work or conversation state makes the existing memory stale; do not try to fully infer task completion through a separate language-understanding pass.

Unit tests:

- Creates project hook configuration when missing.
- Preserves unrelated existing hook entries.
- Updates existing Arbor hook entries idempotently.
- Refuses to write hook state outside the resolved project root.
- Keeps hook entry order and names stable.

Scenario tests:

- New project after `$arbor` invocation shows visible hook files under the project.
- Existing project with other hooks keeps those hooks intact.
- Session startup hook points to the startup context collector.
- In-session hook reminds the agent to refresh `.codex/memory.md` when uncommitted work or conversation state has drifted.
- Goal/constraint hook points to targeted `AGENTS.md` updates.

### Feature 4: Session Startup Hook Execution

Deliverables:

- Executable session startup hook wrapper or workflow entrypoint.
- Tests that replay the registered `arbor.session_startup_context` hook path.
- Feature review file for Hook 1 behavior.

Behavior:

- Resolve the current project root.
- Load startup context in Arbor order: `AGENTS.md`, formatted `git log`, `.codex/memory.md`, `git status`.
- Use the existing collector as the deterministic execution core.
- Preserve agent-selected read depth and git-log arguments.
- Report fallback diagnostics without blocking later sections.
- Do not update `.codex/memory.md` or `AGENTS.md`; those belong to later hooks.

Unit tests:

- Replays the registered startup hook entrypoint.
- Preserves collector section order.
- Passes agent-selected git log args through.
- Handles missing setup files and non-git projects without blocking later sections.

Scenario tests:

- New project with registered hooks runs the startup hook.
- Existing repo with uncommitted work reports memory and git status.
- Non-git project returns fallback diagnostics.
- Hook 1 does not write memory or `AGENTS.md`.

### Feature 5: In-Session Memory Hook Execution

Deliverables:

- Executable in-session memory hygiene hook wrapper.
- Registered Hook 2 script entrypoint and optional diff argument channel.
- Tests for memory packet generation, uncommitted work context, selected diff passthrough, fallback diagnostics, and no-write behavior.
- Feature review file for Hook 2 behavior.

Behavior:

- Emit a memory hygiene packet containing existing `.codex/memory.md`, `git status --short`, unstaged `git diff --stat`, staged `git diff --cached --stat`, and optional agent-selected diff.
- Let the running agent decide whether `.codex/memory.md` needs an edit using the packet plus conversation context.
- Use project-local context and agent-selected diff arguments.
- Reject side-effecting selected diff options that can write files.
- Do not update `AGENTS.md`.
- Do not make a standalone semantic freshness checker.

### Feature 6: Goal And Constraint Drift Hook Execution

Deliverables:

- Executable AGENTS drift hook wrapper.
- Registered Hook 3 script entrypoint with repeatable `--doc` argument channel.
- Tests for packet generation, selected project-local docs, path boundary checks, fallback diagnostics, and no-write behavior.
- Feature review file for Hook 3 behavior.

Behavior:

- Emit an AGENTS drift packet containing `AGENTS.md`, `git status --short`, and optional agent-selected project-local docs.
- Let the running agent decide whether durable project goal, constraint, or map changes require an `AGENTS.md` edit using the packet plus conversation context.
- If an update is needed, edit only `Project Goal`, `Project Constraints`, or `Project Map`.
- Keep short-term progress in `.codex/memory.md`.
- Do not update `.codex/memory.md` from this hook.
- Reject selected docs outside the resolved project root.

### Feature 7: Arbor Plugin Packaging

Deliverables:

- Repo-local `plugins/arbor` plugin package.
- `.codex-plugin/plugin.json` manifest with concrete Arbor metadata.
- Plugin `skills/arbor` payload copied from the accepted standalone skill.
- Plugin `hooks.json` containing the same three Arbor hook intents.
- Tests that ensure the packaged skill and hook contract stay synchronized with the source skill and registration script.
- Feature review file for plugin packaging behavior.

Behavior:

- Package the existing skill for plugin distribution.
- Preserve project-level memory and hook state: hook registration still writes to the target project's `.codex/hooks.json`.
- Do not implement natural-language/runtime semantic dispatch in Feature 7.
- Do not change Hook 1, Hook 2, or Hook 3 behavior.
- Do not create marketplace entries unless requested.

Validation:

- Manifest has no TODO placeholders and points to `./skills/` plus `./hooks.json`.
- Packaged `skills/arbor` files exactly match `skills/arbor`.
- Plugin `hooks.json` exactly matches canonical `ARBOR_HOOKS` from `register_project_hooks.py`.
- Every packaged hook entrypoint resolves to a script inside the packaged skill.
- Existing Arbor script tests continue to pass.

### Feature 8: Plugin-Based Trigger Scenario Sidecar

Deliverables:

- Machine-checkable `docs/reviews/hook-trigger-scenarios.json` sidecar.
- Tests that expand every Markdown scenario into structured dispatch expectations.
- Tests that keep Markdown ids, expected labels, hook ids, optional args, and structured expectations consistent.
- Feature review file for sidecar behavior.

Behavior:

- Preserve `docs/reviews/hook-trigger-scenarios.md` as the human-readable scenario source.
- Use the JSON sidecar for structured fields needed by the future eval harness.
- Cover all 150 Markdown scenarios through defaults plus explicit overrides.
- Add precise expectations for multi-hook and ambiguous cases.
- Keep single-label `H1`, `H2`, and `H3` scenarios strict: exactly one expected hook, no optional hooks, and all non-target Arbor hooks forbidden.
- Do not implement a dispatcher.
- Do not implement fixtures or hook execution harnesses yet.

Validation:

- Sidecar schema has valid hook ids and default expectation labels.
- Every Markdown scenario expands to a machine-checkable expectation.
- Single-hook and `NONE` scenarios preserve their expected semantics.
- `MULTI` scenarios have explicit structured overrides.
- Optional args in the sidecar reference valid Arbor hook ids.

### Feature 9: Deterministic Dispatch Eval Fixtures

Deliverables:

- `scripts/eval_fixtures.py`.
- Builders for the Stage B project-state fixtures.
- JSON fixture summaries for future dispatcher and hook-execution harness inputs.
- Tests that keep fixture names aligned with the sidecar and verify each generated state.
- Feature review file for fixture builder behavior.

Behavior:

- Generate small deterministic project fixtures under caller-provided temporary directories.
- Initialize project-local Arbor files and project hook registration where applicable.
- Do not depend on this repository's current git status or untracked files.
- Preserve raw git status semantics in the fixture summary.
- Include an outside-root path only in the fixture designed to test rejection behavior.
- Do not implement dispatcher decisions, hook execution assertions, or semantic metrics yet.

Validation:

- Every fixture builder creates a project root and machine-readable summary.
- Fixture names cover all sidecar-referenced fixtures and the planned `non_git_project` case.
- Clean git, non-git, missing setup, uncommitted changes, stale memory, durable drift docs, and outside-root cases are asserted directly.
- CLI output is valid JSON and bad fixture names fail without traceback.

### Feature 10: Simulated Dispatcher Adapter

Deliverables:

- `scripts/simulated_dispatcher.py`.
- Sidecar-backed scenario loader and dispatcher contract output.
- Tests that validate trigger, none, multi-hook, ambiguous, optional-arg, outside-root, deterministic, and CLI behavior.
- Feature review file for simulated dispatcher behavior.

Behavior:

- Load the human-readable Markdown corpus plus the JSON sidecar.
- Expand a scenario id into the dispatcher output contract:

```json
{
  "hooks": ["arbor.in_session_memory_hygiene"],
  "decision": "trigger",
  "confidence": "high",
  "requires_agent_judgment": false,
  "optional_args": {},
  "reason": "Sidecar-backed simulated dispatch..."
}
```

- Preserve structured sidecar semantics for `trigger`, `none`, `ambiguous`, expected hooks, optional hooks, forbidden hooks, and optional hook arguments.
- Resolve outside-root placeholder docs from a fixture summary when that fixture is provided.
- Do not implement natural-language semantic classification.
- Do not execute hooks.
- Do not report precision, recall, false-positive, stability, or execution metrics.

Validation:

- All 150 scenarios produce valid dispatcher-contract JSON.
- Selected hooks never include forbidden hooks.
- `NONE` scenarios return no hooks.
- Ambiguous scenarios preserve `requires_agent_judgment`.
- Optional args are attached only to selected hooks.
- Repeated identical inputs produce identical outputs.
- CLI errors are controlled and do not show tracebacks.

### Feature 11: Registered Hook Execution Harness

Deliverables:

- `scripts/evaluate_hook_triggers.py`.
- Scenario execution flow from sidecar expectation to fixture, simulated dispatcher, registered hook command, and packet/side-effect assertions.
- Tests covering H1, H2, H3 with selected docs, `NONE`, multi-hook, outside-root rejection, unknown hook errors, and CLI behavior.
- Feature review file for hook execution harness behavior.

Behavior:

- Generate the scenario's deterministic fixture under a caller-provided work root.
- Run the simulated dispatcher adapter for the scenario.
- Resolve selected hook ids through the generated fixture's `.codex/hooks.json`.
- Execute registered hook entrypoints through subprocess commands, not direct internal function calls.
- Assert hook packet shape and project-local side-effect behavior.
- Treat outside-root rejection as a passing execution assertion when the scenario is designed to test rejection.
- Do not compute semantic precision, recall, false-positive, or stability metrics yet.

Validation:

- Hook 1 output includes startup context sections in Arbor order and leaves `AGENTS.md` and `.codex/memory.md` unchanged.
- Hook 2 output includes memory, git status, unstaged diff stat, staged diff stat, and leaves project memory files unchanged.
- Hook 3 output includes AGENTS, git status, selected docs when provided, and leaves project memory files unchanged.
- Outside-root selected docs are rejected without leaking outside file contents.
- `NONE` and ambiguous/no-hook decisions skip hook execution.
- CLI output is valid JSON and controlled errors do not show tracebacks.

### Feature 12: Full-Corpus Hook Execution Report

Deliverables:

- Full-corpus mode for `scripts/evaluate_hook_triggers.py`.
- Compact JSON report for all Markdown/sidecar scenarios.
- Tests that run the full 150-scenario corpus through fixture generation, simulated dispatch, registered hook execution, and packet/side-effect assertions.
- Feature review file for full-corpus report behavior.

Behavior:

- Add `--all` CLI mode to evaluate every scenario in the corpus.
- Keep single-scenario mode for detailed debugging.
- Produce a compact report by default so hook packet stdout/stderr does not dominate the artifact.
- Support `--include-details` when full hook stdout/stderr is needed.
- Report only harness and hook execution quality: pass counts, decision counts, hook counts, hook execution pass rate, outside-root leaks, unintended writes, and assertion failures.
- Explicitly mark semantic metrics as not reported while the dispatcher remains sidecar-backed.

Validation:

- All 150 sidecar scenarios run through the harness.
- Full-corpus report passes when every selected hook satisfies its assertions.
- `NONE` and no-hook ambiguous cases are counted without hook execution.
- Outside-root rejection scenarios report zero content leaks.
- Unintended writes to `AGENTS.md` and `.codex/memory.md` report as failures.
- CLI full-corpus mode emits valid JSON.

## Hook Trigger Dispatch Evaluation

The standalone skill defines hook contracts and executable hook entrypoints, but it does not yet include the future plugin's runtime semantic dispatcher. The feature-level review should therefore evaluate a dispatcher as an explicit component instead of relying only on document review.

### Evaluation Goal

Test the full dispatch path:

```text
user expression + project-state fixture
-> dispatcher decision
-> hook script execution when selected
-> output and side-effect assertions
```

The experiment must answer two questions:

1. Semantic activation: does the dispatcher select the correct Arbor hook labels for natural-language requests and runtime events?
2. Runtime execution: after a hook is selected, does the registered hook entrypoint run the expected project-local packet flow without unintended writes?

### Scenario Corpus

Use `docs/reviews/hook-trigger-scenarios.md` as the initial evaluation corpus.

The corpus should cover:

- H1 positive cases: startup, resume, onboarding, and project orientation.
- H2 positive cases: stale `.codex/memory.md`, uncommitted work checkpoints, direction changes, and memory cleanup.
- H3 positive cases: durable project goal, constraint, and project-map drift.
- Negative cases: ordinary programming, translation, shell, browser, git, and unrelated project tasks.
- Near-miss cases: runtime memory, React hooks, algorithm constraints, UI maps, generic "start", and generic "remember".
- Ambiguous or multi-hook cases where the expected output is multiple hooks or an explicit need for agent judgment.
- Cross-language phrasing in English, Chinese, and mixed technical language.
- Runtime event cases such as `session.start` and `conversation.checkpoint`.

Do not convert this corpus into hard-coded keyword rules. It is an evaluation surface for dispatch behavior.

Before metric-producing evaluation, add a machine-checkable scenario sidecar derived from the Markdown corpus. The Markdown corpus is for human review; the sidecar is for the harness.

Required sidecar fields:

```json
{
  "id": "M-P001",
  "expression": "New session; we also have uncommitted changes from last time.",
  "fixture": "uncommitted_changes",
  "allowed_decisions": ["trigger", "ambiguous"],
  "expected_hooks": ["arbor.session_startup_context"],
  "optional_expected_hooks": ["arbor.in_session_memory_hygiene"],
  "forbidden_hooks": ["arbor.goal_constraint_drift"],
  "requires_agent_judgment": true,
  "notes": "H1 should run first; H2 depends on memory staleness after startup context."
}
```

Structured expectations are required for `MULTI`, ambiguous, and near-miss cases before computing precision, recall, ambiguous-case handling, or multi-hook partial-match metrics.

### Project-State Fixtures

Run the corpus across a small set of temporary project fixtures:

- `clean_git_project`: git repo with initialized `AGENTS.md`, `.codex/memory.md`, and no uncommitted changes.
- `non_git_project`: initialized files but no git repository.
- `missing_agents`: `.codex/memory.md` exists but `AGENTS.md` is missing.
- `missing_memory`: `AGENTS.md` exists but `.codex/memory.md` is missing.
- `uncommitted_changes`: tracked and untracked changes exist.
- `stale_memory`: `.codex/memory.md` contains an in-flight item contradicted by current diff or conversation metadata.
- `durable_drift_docs`: project-local docs indicate a durable goal, constraint, or map change.
- `outside_root_path`: selected doc or diff path points outside the project root and should be rejected by hook execution.

Fixtures should be small, deterministic, and generated under temporary directories. They must not depend on this repository's current untracked state.

### Dispatcher Contract

Before the plugin exists, test a simulated dispatcher. After the plugin exists, replace the simulated dispatcher with the real plugin dispatch layer while keeping the same evaluation harness.

Dispatcher input:

- User expression or runtime event.
- Project root.
- Fixture summary such as git status class, missing setup files, and available selected docs.
- Hook contract from `.codex/hooks.json`.
- Skill metadata and the relevant trigger guidance from `SKILL.md`.

Dispatcher output must be structured JSON:

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

Allowed `decision` values:

- `trigger`: one or more hooks should run.
- `none`: no Arbor hook should run.
- `ambiguous`: the expression needs agent judgment before hook execution.

Allowed hook ids:

- `arbor.session_startup_context`
- `arbor.in_session_memory_hygiene`
- `arbor.goal_constraint_drift`

### Evaluation Stages

Stage A: static trigger contract review.

- Review `SKILL.md`, `.codex/hooks.json`, `references/project-hooks-template.md`, the Markdown scenario corpus, and this design.
- Validate trigger boundaries, negative cases, near-miss cases, ambiguity policy, and consistency across docs.
- Do not report precision, recall, false-positive rate, or stability as measured metrics in this stage.
- Output should be qualitative findings with scenario ids and whether each issue is a metadata, hook-contract, corpus, or design gap.

Stage B: dispatch harness evaluation.

- Add an executable evaluation harness and structured scenario sidecar.
- Generate deterministic project fixtures under temporary directories.
- Run a simulated dispatcher first; later swap in the real plugin dispatcher without changing corpus semantics.
- Execute selected hooks through registered `.codex/hooks.json` entrypoints.
- Report measured metrics and hook execution assertions.

Stage B deliverables:

- A structured scenario sidecar with machine-checkable expected decisions and hook sets. Feature 8 supplies the first version.
- Deterministic fixture builders for clean, non-git, missing setup, uncommitted, stale-memory, durable-drift, and outside-root cases. Feature 9 supplies the first version.
- A simulated dispatcher adapter that emits the dispatcher output contract from sidecar expectations. Feature 10 supplies the first version.
- `scripts/evaluate_hook_triggers.py` or equivalent harness. Feature 11 supplies the first version for registered-hook execution assertions.
- Full-corpus hook execution report. Feature 12 supplies the first sidecar-backed corpus report.
- A result report appended to `docs/reviews/features/feature-level-hook-trigger-review.md`.

### Hook Execution Assertions

When the dispatcher selects a hook, the harness should execute the hook through the registered `.codex/hooks.json` entrypoint rather than calling an internal function directly.

Hook 1 assertions:

- Output includes `# Project Startup Context`.
- Section order is `AGENTS.md`, formatted `git log`, `.codex/memory.md`, `git status`.
- Missing files and non-git projects emit diagnostics instead of aborting later sections.
- `.codex/memory.md` and `AGENTS.md` are unchanged.

Hook 2 assertions:

- Output includes `# Memory Hygiene Context`.
- Output includes `.codex/memory.md`, `git status`, unstaged diff stat, staged diff stat, and optional selected diff when provided.
- Side-effecting or outside-root diff args are rejected without leaking outside file contents.
- `AGENTS.md` is unchanged; `.codex/memory.md` is unchanged by the hook script itself.

Hook 3 assertions:

- Output includes `# AGENTS Guide Drift Context`.
- Output includes `AGENTS.md`, `git status`, and selected project-local docs when provided.
- Outside-root selected docs are rejected without leaking outside file contents.
- `.codex/memory.md` and `AGENTS.md` are unchanged by the hook script itself.

### Metrics

Report metrics by scenario family and overall:

- H1 precision and recall.
- H2 precision and recall.
- H3 precision and recall.
- `NONE` false-positive rate.
- Near-miss false-positive rate.
- Ambiguous-case handling rate: fraction of expected ambiguous cases marked `ambiguous` or returning a documented multi-hook decision.
- Multi-hook partial-match rate: selected hooks include at least one expected hook and do not include unrelated hooks.
- Execution pass rate: selected hooks execute and satisfy packet and side-effect assertions.
- Stability rate: identical inputs produce identical hook labels across repeated runs.

Repeat stochastic dispatcher runs at least 3 times for the same corpus. Any non-determinism must be reported with the affected scenario ids.

### Static Review Acceptance Gates

Stage A acceptance gates:

- Hook 1, Hook 2, and Hook 3 have clear positive and negative trigger boundaries.
- The Markdown scenario corpus covers clear positives, negatives, near-misses, ambiguous cases, cross-language cases, and runtime events.
- Scenario labels do not contradict their notes.
- Ambiguous and multi-hook cases identify why agent judgment or multiple hooks may be valid.
- The plan explicitly defers measured semantic metrics until the dispatch harness and structured sidecar exist.
- The skill body stays concise and does not embed the large scenario corpus.

### Dispatch Harness Acceptance Thresholds

Stage B acceptance thresholds:

- 100% hook execution pass rate for selected hooks.
- 0 outside-root content leaks.
- 0 unintended writes by hook scripts.
- `NONE` false-positive rate at or below 2%.
- Near-miss false-positive rate at 0%.
- H1/H2/H3 recall at or above 90% on clear positive cases.
- All ambiguous cases either return `ambiguous`, return the expected multi-hook set, or include a reason explaining why agent judgment is required.

Plugin-readiness thresholds can be tightened later after the real runtime dispatcher exists.

### Failure Classification

Each failed scenario should be classified as one of:

- `metadata_gap`: `SKILL.md` trigger language is too broad or too narrow.
- `hook_contract_gap`: `.codex/hooks.json` or `project-hooks-template.md` describes the hook unclearly.
- `dispatcher_gap`: the simulated or plugin dispatcher misread an otherwise clear contract.
- `execution_gap`: the selected hook script failed packet or side-effect assertions.
- `fixture_gap`: the project fixture does not represent the intended state clearly enough.
- `expected_ambiguity`: the scenario expectation should allow agent judgment or multi-hook behavior.

The review output should append findings to `docs/reviews/features/feature-level-hook-trigger-review.md`, with scenario ids, observed labels, expected labels, and failure class.

## Feature-Level Review Plan

After all small features in the queue are complete:

1. Run unit tests.
2. Run scenario tests against temporary projects.
3. Use the skill on a fresh sample repo.
4. Review whether the skill body is concise enough and delegates details to scripts/references.
5. Review whether hook semantics are clear enough for later plugin integration.

Stage A static trigger-contract review is complete and accepted. Do not keep expanding the standalone skill to chase semantic dispatch metrics. Those metrics belong to Stage B.

Next Stage B order:

1. Build the structured scenario sidecar from the Markdown corpus. Complete in Feature 8.
2. Validate that sidecar entries preserve the human-readable corpus labels and notes. Complete in Feature 8.
3. Add deterministic fixture builders. Complete in Feature 9.
4. Add the simulated dispatcher adapter. Complete in Feature 10.
5. Add registered-hook execution and packet/side-effect assertions. Complete in Feature 11.
6. Add a full-corpus hook execution report. Complete in Feature 12.
7. Report semantic metrics only after observed labels come from a real dispatcher rather than the sidecar-backed simulator.

## Current Environment Notes

The current working directory `/Users/shawn/Desktop/arbor` is a git repository on `master` with no commits yet. Current project files are untracked until the user requests staging or committing.
