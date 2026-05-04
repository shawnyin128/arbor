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

### Feature 13: Plugin Trigger Adapter Design

Deliverables:

- Design notes for replacing the sidecar-backed baseline with a real plugin/runtime trigger adapter.
- Updated review routing that marks this as a new phase after current-scope Arbor completion.
- A per-feature review file for the plugin trigger adapter plan.

Behavior:

- Keep the existing trigger decision contract unchanged:

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

- Treat the sidecar-backed path as `sidecar-baseline`, not as the runtime target.
- Add the real plugin trigger path behind a swappable adapter boundary so the fixture, sidecar, hook execution, and report harness stay reusable.
- Feed the plugin trigger path only the minimum evaluation inputs: user expression or runtime event, fixture summary, hook contract, and skill metadata/trigger guidance.
- Do not let the plugin trigger path read expected labels, expected hooks, forbidden hooks, or sidecar scoring fields.
- Preserve JSON-only structured output for automated scoring.
- Preserve project-local side-effect boundaries: the trigger adapter selects hooks only; hook scripts perform packet generation; the running agent edits memory or `AGENTS.md` only when appropriate.

Validation:

- Golden contract tests: plugin runtime trigger output has the same keys, decision vocabulary, confidence vocabulary, hook ids, and optional-arg shape as the sidecar baseline output.
- Non-circularity tests: plugin runtime trigger code path cannot load `expected_hooks`, `optional_expected_hooks`, `forbidden_hooks`, or `allowed_decisions` from the sidecar.
- Harness compatibility tests: the existing full-corpus harness can run with either sidecar baseline or plugin runtime trigger adapter through one adapter selection flag.
- Semantic metrics only after plugin runtime trigger output is used: H1/H2/H3 precision and recall, `NONE` false-positive rate, near-miss false-positive rate, ambiguous-case handling, multi-hook partial match, and stability.
- Regression gates from prior stages still apply: 100% hook execution pass rate, 0 outside-root leaks, and 0 unintended writes.

Failure behavior:

- Invalid JSON from the plugin trigger adapter is `trigger_gap`.
- Unknown hook ids are `trigger_gap`.
- Correct hook id with failing packet/side-effect assertion is `execution_gap`.
- Fixture setup failure is `fixture_gap`.
- Ambiguous scenario disagreement should be reviewed before being counted as a hard failure.

### Feature 14: Plugin Trigger Selection and Non-Circular Input Builder

Deliverables:

- A plugin trigger adapter module that keeps the sidecar baseline and future real plugin runtime behind one selection boundary.
- A harness `--trigger-adapter` option with `sidecar-baseline` as the default and `plugin-runtime-stub` as the first non-circular adapter path.
- A plugin runtime input builder that receives runtime-like context but excludes sidecar scoring data.
- Unit and CLI tests proving the harness can swap plugin trigger adapters without exposing expected labels, expected hooks, optional expected hooks, forbidden hooks, allowed decisions, or scenario notes to the plugin runtime path.

Behavior:

- Preserve the existing scenario corpus and sidecar as evaluator-only artifacts.
- Use sidecar expectations only for the `sidecar-baseline` adapter and for evaluator comparison in later features.
- Build plugin runtime trigger input from:
  - user expression or runtime event text;
  - project root;
  - fixture/live project summary;
  - project-local hook contract from `.codex/hooks.json`;
  - concise `SKILL.md` metadata.
- The `plugin-runtime-stub` adapter returns a valid trigger decision contract without selecting hooks. It exists to validate the adapter boundary, not to report semantic quality.
- Corpus reports should identify which plugin trigger adapter produced the observed labels.
- Semantic trigger metrics remain unreported for both `sidecar-baseline` and `plugin-runtime-stub`.

Validation:

- Unit tests assert plugin runtime input omits all sidecar scoring fields.
- Unit tests assert trigger decision contract validation rejects unknown hooks, invalid decisions, invalid confidence, and optional args for unselected hooks.
- Harness scenario tests pass with the default sidecar baseline adapter.
- CLI smoke tests pass for `--trigger-adapter sidecar-baseline` and `--trigger-adapter plugin-runtime-stub`.
- Full-corpus sidecar baseline execution remains passing.

### Feature 15: Plugin Installation Readiness

Deliverables:

- A repo-local marketplace at `.agents/plugins/marketplace.json` exposing `plugins/arbor`.
- A plugin installation-readiness validator at `scripts/validate_plugin_install.py`.
- Packaged skill smoke tests that run from the plugin payload rather than the standalone `skills/arbor` copy.
- An isolated Codex CLI marketplace add probe that uses a temporary `HOME` so the user's real `~/.codex/config.toml` is not modified.

Behavior:

- Marketplace name is `arbor-local`.
- Marketplace entry points to `./plugins/arbor` with local source, `AVAILABLE` installation, and `ON_INSTALL` authentication.
- The validator checks:
  - marketplace entry shape and path;
  - plugin manifest name, skills path, hooks path, and interface prompt bounds;
  - packaged skill `SKILL.md`;
  - packaged hook ids and entrypoint script resolution;
  - packaged initialization behavior;
  - packaged Hook 1, Hook 2, and Hook 3 entrypoint smoke behavior;
  - optional isolated `codex plugin marketplace add <repo-root>` behavior.

Validation:

- `python3 scripts/validate_plugin_install.py` passes.
- `python3 scripts/validate_plugin_install.py --codex-probe` passes.
- Unit tests cover the install validator's marketplace and packaged hook smoke behavior.
- Full project validation still runs after the plugin-readiness files are added.

### Feature 16: Real Plugin Runtime Probe

Deliverables:

- `scripts/probe_plugin_runtime.py`.
- An isolated Codex runtime probe that adds the repo-local marketplace, enables `arbor@arbor-local`, and optionally attempts a real `codex exec` run against the installed plugin.
- Tests for isolated config mutation, exec failure classification, expected plugin side-effect checks, and default no-model-call behavior.
- Feature review file for plugin runtime probing behavior.

Behavior:

- Use a temporary `HOME` so the user's real Codex config is not modified.
- Add the `arbor-local` marketplace through the real Codex CLI.
- Enable `arbor@arbor-local` in the isolated config using the same config table shape as installed plugins.
- Skip real `codex exec` by default; run it only when `--attempt-exec` is provided.
- When `--attempt-exec` is used, ask the installed `$arbor` skill to initialize a temporary project and register hooks, then assert that `AGENTS.md`, `.codex/memory.md`, and `.codex/hooks.json` exist.
- Classify `codex exec` failures as `network_unavailable`, `auth_required`, `plugin_runtime_error`, or generic `runtime_failed` so Arbor failures are not confused with environment blockers.
- Do not report semantic trigger metrics from this probe. It verifies runtime reachability and plugin side effects for one installed-skill path; full scenario semantics remain a later adapter feature.

Validation:

- Unit tests mock runtime execution and verify success/failure classification without requiring network or model calls.
- CLI probe without `--attempt-exec` passes in the local sandbox.
- CLI probe with `--attempt-exec` either passes in an online authenticated runtime or reports a classified blocker without mutating the user's real Codex config.
- Existing install-readiness and full Arbor tests continue to pass.

### Feature 17: Codex Exec Plugin Runtime Trigger Adapter

Deliverables:

- A `plugin-runtime-codex-exec` trigger adapter behind the existing Feature 14 adapter boundary.
- A Codex exec prompt/input path that uses the installed Arbor plugin runtime, receives non-circular runtime input, and asks for the standard trigger decision contract as JSON.
- Unit tests for valid runtime decision parsing, runtime blocker classification, harness compatibility, and continued sidecar-baseline behavior.
- Feature review file for the Codex exec trigger adapter.

Behavior:

- Preserve the trigger decision contract from Feature 13.
- Build runtime input from the user expression, project-local fixture summary, `.codex/hooks.json`, and `SKILL.md` metadata.
- Exclude sidecar scoring fields and expected labels from the Codex exec prompt.
- Install and enable `arbor@arbor-local` in an isolated `HOME` before the exec call.
- Use `codex exec --ephemeral --json --output-schema --output-last-message` so the runtime result is machine-parseable.
- The adapter selects hooks only. It must not execute hooks, initialize Arbor, update memory, or edit `AGENTS.md`.
- Runtime blockers such as network, auth, plugin enable failure, or timeout return a valid `ambiguous` trigger decision with `requires_agent_judgment=true` and no hooks.
- Invalid JSON, unknown hook ids, or invalid decision contract from a successful runtime call remain adapter errors.
- Do not run full 150-scenario semantic metrics in this feature. This feature proves the runtime adapter path and blocker behavior; metric reporting is a later feature after review.

Validation:

- Unit tests mock Codex exec and verify a valid runtime JSON decision is parsed and contract-validated.
- Unit tests verify the prompt excludes sidecar scoring fields.
- Unit tests verify network/runtime blockers return a valid ambiguous decision without selecting hooks.
- Harness scenario evaluation can use `plugin-runtime-codex-exec` without executing hooks when the runtime returns a blocker.
- Existing sidecar-baseline full-corpus report remains passing.

### Feature 18: Runtime Availability And Semantic Scoring Gates

Deliverables:

- Runtime availability and scoring gate fields in the full-corpus hook trigger report.
- Tests proving runtime blockers are excluded from semantic scoring readiness.
- A feature review file for the gate design and implementation.

Behavior:

- Keep `semantic_metrics.reported=false`; this feature does not implement precision, recall, false-positive, ambiguity, multi-hook, or stability formulas.
- Add `semantic_metrics.ready_for_semantic_metrics` as the explicit handoff signal for the later metric feature.
- Gate semantic metric readiness on:
  - adapter eligibility: only `plugin-runtime-codex-exec` can become metric-eligible;
  - runtime availability: runtime blocker decisions such as `network_unavailable`, `auth_required`, `project_file_mutation:<paths>`, timeout, or plugin enable failure block scoring and are not counted as semantic `NONE`;
  - hook execution cleanliness: selected hook execution pass rate is 1.0, outside-root leaks are 0, unintended writes are 0, and assertion failures are empty.
- Preserve sidecar and stub behavior as ineligible for semantic metrics.
- Preserve existing hook execution-chain summary fields.

Validation:

- Sidecar baseline corpus still reports `semantic_metrics.reported=false` and adapter-ineligible.
- Mocked plugin runtime blocker corpus reports runtime unavailable with blocker counts and blocked scenario ids.
- Synthetic clean runtime results can set `ready_for_semantic_metrics=true` while still leaving formulas unreported.
- Full sidecar baseline corpus remains passing.
- Existing tests, compile checks, ruff, skill validation, and plugin install validation continue to pass.

### Feature 19: Semantic Metric Formulas For Real Plugin Trigger Output

Deliverables:

- Semantic metric formulas behind the Feature 18 scoring gates.
- Per-hook precision and recall for required hook selection.
- `NONE` and near-miss false-positive rates.
- Ambiguous-case acceptance and multi-hook partial-match metrics.
- A stability placeholder that stays unreported until repeated real runtime runs exist.
- A feature review file for the metric formulas and release boundary.

Behavior:

- Report semantic metrics only when `semantic_metrics.ready_for_semantic_metrics=true`.
- Keep sidecar-baseline and plugin-runtime-stub reports ineligible.
- Keep runtime blocker reports unscored.
- Use evaluator-side scenario expectations only inside the harness scoring path; do not pass scoring fields into plugin runtime input.
- Treat optional expected hooks as precision-acceptable but not required for recall.
- Treat required hooks in non-agent-judgment scenarios as recall obligations.
- Count selected forbidden or unexpected hooks as semantic failures.
- Count `NONE` and `NM-*` scenarios as false positives when the runtime returns `trigger` or selects any hook.
- Report stability as `reported=false` until the same real runtime adapter has repeated corpus runs.

Release boundary:

- `scripts/evaluate_hook_triggers.py`, `scripts/simulated_dispatcher.py`, `scripts/eval_fixtures.py`, `docs/reviews/hook-trigger-scenarios.*`, and review docs are repository evaluation tooling.
- They should not be included in the Arbor plugin payload.
- The plugin payload remains `plugins/arbor/.codex-plugin/plugin.json`, `plugins/arbor/hooks.json`, and `plugins/arbor/skills/arbor`.

Validation:

- Sidecar baseline corpus still passes and does not report semantic metrics.
- Synthetic gate-ready plugin runtime results report semantic metrics.
- Synthetic false-positive and missing-required-hook results are reflected in metric failures.
- Runtime blocker results still withhold semantic metrics.
- Existing full test, compile, ruff, skill validation, plugin install validation, and coverage checks continue to pass.

### Feature 20: Repeated Runtime Corpus Stability Evaluation

Deliverables:

- A repeated full-corpus evaluation mode for the existing hook trigger harness.
- Stability aggregation for comparable real plugin runtime reports.
- Tests proving stability is reported only when repeated real runtime runs are gate-ready.
- A feature review file for repeated runtime stability behavior and blocker handling.

Behavior:

- Add a repeat-run path that executes the same full corpus more than once under isolated per-run fixture roots.
- Preserve the existing single-run `--all` and `--scenario-id` behavior.
- Compare trigger decisions by scenario id using decision, selected hooks, and optional args.
- Preserve `optional_args` in compact corpus rows so default repeated reports can be replayed for stability signatures.
- Report stability only when:
  - the trigger adapter is `plugin-runtime-codex-exec`;
  - at least two corpus runs exist;
  - every run reports semantic metrics through the existing readiness gates.
- Keep stability unreported for sidecar, stub, single-run, empty-run, runtime blocker, and hook execution failure paths.
- Do not retry around runtime blockers or convert blockers into semantic `NONE` results.

Validation:

- Unit tests cover matching repeated runtime decisions reporting `stability_rate=1.0`.
- Unit tests cover changed repeated runtime decisions reporting unstable scenario ids.
- Unit tests cover sidecar and runtime-blocker repeated runs withholding stability.
- CLI tests cover `--all --repeat-runs 2` without changing default single-run output.
- Existing full test, compile, ruff, skill validation, plugin install validation, sidecar full-corpus, runtime smoke, and coverage checks continue to pass.

### Feature 21: Authenticated Installed Plugin Runtime Probe

Deliverables:

- Authenticated isolated runtime probing for the installed Arbor plugin.
- Local plugin cache materialization, explicit auth copy, isolated project trust, and installed skill injection evidence.
- A fresh-project side-effect gate that rejects pre-existing Arbor output files before `codex exec`.
- A feature review file for authenticated runtime probe behavior.

Behavior:

- Copy auth only from an explicit `--auth-source-home`; never mutate the user's real Codex config.
- Require true installed-cache evidence before reporting a runtime probe pass.
- Treat online/headless runtime blockers as environment blockers, not semantic trigger results.

Validation:

- Unit tests cover auth copy, missing auth, plugin cache materialization, project trust, fresh-project side-effect gates, and installed-cache injection evidence.
- Runtime probe commands either pass in an authenticated online runtime or report classified blockers.

### Feature 22: Authenticated Runtime Corpus Controls

Deliverables:

- Runtime adapter options for `plugin-runtime-codex-exec`.
- Harness CLI flags for authenticated real-runtime corpus runs:
  - `--auth-source-home`
  - `--runtime-timeout`
  - `--codex-bin`
- Tests proving authenticated runtime options are copied into isolated runtime homes and forwarded from scenario/corpus evaluation.
- A feature review file for the corpus control surface.

Behavior:

- Keep the adapter read-only for trigger selection; it must not execute hooks or mutate project memory files.
- Copy auth into each isolated runtime home only when explicitly requested.
- Missing requested auth returns an `auth_required` runtime blocker and remains unscored.
- Runtime options apply to `plugin-runtime-codex-exec`; sidecar and stub behavior remain unchanged.
- Full-corpus semantic metrics remain gated on runtime availability and clean hook execution.

Validation:

- Unit tests cover auth copy into the adapter runtime, missing auth blocker behavior, runtime option forwarding, and CLI parsing.
- Focused adapter/harness/probe tests, compile, and ruff continue to pass.

### Feature 23: Runtime Schema Compatibility And Smoke Gates

Deliverables:

- A strict structured-output-compatible trigger decision schema for `plugin-runtime-codex-exec`.
- Normalization for schema-required empty `optional_args` hook keys.
- Stable runtime blocker diagnostics that preserve blocker counts while exposing short redacted failure detail.
- Positive and negative authenticated runtime smoke evidence.
- A feature review file for the schema fix and smoke results.

Behavior:

- `optional_args` remains part of the trigger decision contract, but the output schema declares every hook id explicitly with `additionalProperties=false`.
- Empty schema-required optional-arg arrays are normalized away before local contract validation.
- Non-empty optional args for unselected hooks remain invalid.
- Runtime blocker reason strings may include a short `detail` suffix, but scoring gates still count the stable blocker class only.
- `--runtime-timeout` rejects non-positive values before runtime execution.
- Single-scenario smoke gates use explicit expectation flags; without those flags, default runtime blocker behavior remains unscored rather than failed:
  - `--require-runtime-available`
  - `--expect-decision`
  - `--expect-hooks`

Validation:

- Unit tests cover strict optional-args schema shape, empty optional-args normalization, runtime detail redaction, blocker-count normalization, and timeout parser rejection.
- Authenticated runtime smoke covers one clear positive and one negative scenario with explicit runtime availability, decision, and hook assertions before attempting a larger corpus run.

### Feature 24: Runtime Batch Execution Controls

Deliverables:

- Selected corpus execution for authenticated real-runtime batches via `--scenario-ids`.
- Per-scenario progress JSONL via `--progress-jsonl`.
- Adapter-level normalization for model-natural optional hook arguments before command execution.
- A feature review file for selected batch controls and authenticated replay evidence.

Behavior:

- `--scenario-ids` accepts a comma-separated list from the existing scenario corpus and reports `scenario_scope=selected`.
- `--progress-jsonl` writes one compact event after each scenario so slow real-runtime runs can be monitored and partial failures can be replayed.
- Smoke expectation flags remain single-scenario only; selected corpus reports keep corpus/scoring semantics.
- Optional args are normalized at the adapter contract boundary:
  - H3 bare doc paths and `--doc path` strings become repeated `--doc <path>` argv pairs.
  - H2 joined or split `--diff-args ...` values become a single safe equals-form option-value argument.
  - H1 joined or split `--git-log-args ...` values preserve spaces as a single option value.
- Non-empty optional args for unselected hooks remain invalid.
- Malformed optional args, including missing values and unknown hook-specific flags, fail at adapter validation before hook execution.

Validation:

- Unit tests cover selected scenario parsing, progress JSONL output, CLI selected-corpus reports, and optional-args normalization.
- Authenticated real-runtime replay covers prior batch failures before attempting a larger selected batch.

### Feature 25: Real Runtime Full Corpus

Deliverables:

- Full 150-scenario authenticated real-runtime corpus execution through `plugin-runtime-codex-exec`.
- Adapter contract continuation for corpus runs: per-scenario adapter errors are captured in the report and progress JSONL instead of aborting the run.
- H1/H2 single-value optional-arg normalization that accepts model-natural bare values without constraining read depth or diff/log shape.
- Honest corpus pass/fail status: once real semantic metrics are reported, any semantic failed scenario makes the report fail and the CLI return non-zero.
- Durable report retention via `--report-json` for expensive authenticated runtime runs.
- Feature review file for full-corpus real-runtime execution, semantic-miss closure, and retained full-corpus artifacts.

Behavior:

- H1/H2 optional args are one value slot. The adapter accepts canonical equals form, joined flag/value form, split flag/value form, or a bare value, then normalizes to the canonical equals form.
- H3 remains a structured repeated `--doc <path>` list and keeps rejecting unknown option-like values.
- Runtime trigger input may include an outside selected-doc path when the fixture/runtime event needs hook-level project-local safety validation; it must not include outside file content or sidecar scoring labels.
- Corpus reports distinguish:
  - hook execution pass rate;
  - adapter contract readiness;
  - runtime availability;
  - semantic trigger quality.
- Runtime blocker reports remain unscored. Semantic report failure applies only after all scoring gates pass and semantic metrics are actually reported.

Validation:

- Unit tests cover bare H1/H2 optional values, adapter-error continuation, semantic report failure, and CLI non-zero exit for failed corpus reports.
- Authenticated real-runtime validation covers the prior H2 optional-arg failures, then the full corpus.
- Round 1 focused authenticated replay covers the four prior semantic misses and persists report/progress artifacts.
- Round 2 authenticated full-corpus replay covers all 150 scenarios with retained report/progress artifacts and reports semantic metrics as passed. Stability remains unreported until repeated full real-runtime runs exist.

## Hook Trigger Dispatch Evaluation

The standalone skill defines hook contracts and executable hook entrypoints, but it does not yet include the future plugin's runtime semantic dispatcher. The feature-level review should therefore evaluate a dispatcher as an explicit component instead of relying only on document review.

### Evaluation Goal

Test the full dispatch path:

```text
user expression + project-state fixture
-> plugin trigger decision
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
- A sidecar-baseline trigger adapter that emits the trigger decision contract from sidecar expectations. Feature 10 supplies the first version under the historical `simulated_dispatcher.py` name.
- `scripts/evaluate_hook_triggers.py` or equivalent harness. Feature 11 supplies the first version for registered-hook execution assertions.
- Full-corpus hook execution report. Feature 12 supplies the first sidecar-backed corpus report.
- Plugin trigger adapter plan. Feature 13 defines the next-phase adapter boundary and non-circular semantic-evaluation gates.
- Plugin trigger selection and non-circular runtime input builder. Feature 14 supplies the first adapter selection surface and plugin-runtime-stub path.
- Plugin installation readiness. Feature 15 supplies the repo-local marketplace and isolated Codex CLI marketplace add probe.
- Real plugin runtime probe. Feature 16 supplies the isolated installed-plugin reachability check and classified `codex exec` blocker reporting.
- Codex exec plugin runtime trigger adapter. Feature 17 supplies the first real runtime adapter path with JSON contract output and blocker classification.
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
- Ambiguous-case acceptance: ambiguous or agent-judgment scenarios use an allowed decision and avoid forbidden or unexpected hooks.
- Multi-hook required recall: selected required hooks divided by total required hooks across multi-hook scenarios.
- Multi-hook metric inputs preserve `raw_missing_required_hooks` separately from `missing_required_hooks`; the raw field is the scoring input, while the presentation field may be cleared for an allowed ambiguous abstention.
- Multi-hook exact-required rate: raw required hooks must actually be selected; allowed ambiguous abstention is accepted separately but is not an exact required-hook match.
- Execution pass rate: selected hooks execute and satisfy packet and side-effect assertions.
- Stability stays `reported=false` until repeated real runtime corpus runs are available; identical-input stability should not be inferred from a single smoke run or sidecar replay.

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
7. Define the plugin trigger adapter boundary and non-circular metric gates. Complete in Feature 13.
8. Add plugin trigger adapter selection and a non-circular plugin runtime input builder. Complete in Feature 14.
9. Add repo-local plugin installation readiness and isolated Codex CLI marketplace add probe. Complete in Feature 15.
10. Add an isolated installed-plugin runtime probe and classify environment blockers. Complete in Feature 16.
11. Add the Codex exec plugin runtime trigger adapter and validate single-scenario/blocker behavior. Complete in Feature 17.
12. Report semantic metrics only after observed labels come from the reviewed runtime adapter rather than the sidecar-backed baseline. Complete in Feature 19.
13. Add repeated real runtime corpus stability aggregation without reporting stability for blocked, sidecar, stub, or single-run paths.

## Current Environment Notes

The current working directory `/Users/shawn/Desktop/arbor` is a git repository on `master` with no commits yet. Current project files are untracked until the user requests staging or committing.
