# Arbor

Arbor is a project-context plugin for Codex and Claude Code. It makes both runtimes better at long-running repository work.

Either runtime is strongest when it has the right project context. In real projects, that context is split across docs, git history, current diffs, earlier session notes, and durable project rules. Arbor turns that into a repeatable workflow: every repo gets a project guide, short-term session memory, and hooks that restore the right context at the right time.

It creates and maintains:

- `AGENTS.md` as the canonical durable project guide and map to deeper context (read by both runtimes).
- `.arbor/memory.md` for short-term, uncommitted session memory (shared by both runtimes).
- `.codex/hooks.json` in target projects for project-level Arbor hook registration (Codex installs only).
- `CLAUDE.md` as a short Claude-native bridge pointing at `AGENTS.md` and `.arbor/memory.md` (Claude Code installs only).

The main benefit is continuity. Arbor helps each runtime resume a repo without re-discovering the same facts, keeps uncommitted work separate from durable project knowledge, and updates project guidance when goals or constraints change. Same project state, two runtimes, no duplication.

Arbor fixes the workflow order. It does not limit how much code, documentation, git history, or diff context the agent can read.

## Why Use Arbor

- **Faster repo resumption**: Arbor always starts from the project guide, git history, short-term memory, and current git status.
- **Cleaner memory boundaries**: unresolved uncommitted state goes in `.arbor/memory.md`; long-term context is reconstructed from `AGENTS.md`, git history, and project docs.
- **Less repeated context work**: decisions and project structure stop living only in chat history.
- **Project-local by default**: Arbor writes to the current repo, not a global memory store.
- **Hook-ready workflow**: startup context, memory hygiene, and AGENTS drift each have clear project-level hook intents.
- **Agent-friendly design**: Arbor controls the workflow shape without restricting the agent's reading depth or reasoning.

## Install

### Codex

Add the marketplace and install Arbor:

```bash
codex plugin marketplace add shawnyin128/arbor
```

If `codex` is not on your `PATH` on macOS:

```bash
/Applications/Codex.app/Contents/Resources/codex plugin marketplace add shawnyin128/arbor
```

SSH:

```bash
codex plugin marketplace add git@github.com:shawnyin128/arbor.git
```

Upgrade and remove:

```bash
codex plugin marketplace upgrade arbor
codex plugin marketplace remove arbor
```

### Claude Code

From within a Claude Code session:

```text
/plugin marketplace add shawnyin128/arbor
/plugin install arbor@arbor
```

Run `/reload-plugins` afterward to activate the skill and the bundled `SessionStart` hook in the current session. The hook auto-injects the Arbor startup packet (AGENTS.md, formatted git log, `.arbor/memory.md`, git status) on `startup` and `resume` sources, trimmed to fit Claude Code's context-injection cap.

## Skills

Arbor ships the core project-context skill plus six internally stable workflow skills, available on both runtimes:

```text
Codex:        $arbor
Claude Code:  /arbor:arbor

Codex:        $intake
Claude Code:  /arbor:intake

Codex:        $brainstorm
Claude Code:  /arbor:brainstorm

Codex:        $develop
Claude Code:  /arbor:develop

Codex:        $evaluate
Claude Code:  /arbor:evaluate

Codex:        $converge
Claude Code:  /arbor:converge

Codex:        $release
Claude Code:  /arbor:release
```

The managed development loop is:

```text
intake -> brainstorm -> develop -> release(checkpoint_develop)
-> evaluate -> release(checkpoint_evaluate)
-> converge -> release(finalize_feature)
```

`intake` decides whether Arbor should manage the request. `brainstorm` turns managed work into features, acceptance criteria, and test scope. `develop`, `evaluate`, and `converge` append evidence to the same review document, while `release` records checkpoints/finalization and keeps workflow state discoverable through git and the feature registry.

Two workflow artifacts carry state between skills:

- `.arbor/workflow/features.json` is the feature queue and status index.
- `docs/review/<feature>-review.md` is the shared evidence document for one feature, starting with the brainstorm Context/Test Plan and then accumulating Developer, Evaluator, Convergence, and Release rounds.

### `arbor`

Use Arbor when you want either runtime to stay oriented across a real development workflow, especially when work spans multiple sessions or depends on git history.

What it does well:

- creating `AGENTS.md` when missing;
- creating `.arbor/memory.md` when missing;
- migrating legacy `.codex/memory.md` by copying it to `.arbor/memory.md` during explicit initialization when the canonical file is missing;
- creating `CLAUDE.md` as a short bridge to `AGENTS.md` and `.arbor/memory.md` when initialized from a Claude Code install;
- registering Arbor hooks into target-project `.codex/hooks.json` (Codex);
- loading startup context in the fixed order: `AGENTS.md`, formatted `git log`, `.arbor/memory.md`, `git status` — automatically on Claude Code via `SessionStart`, on demand on Codex via the project hook intent;
- refreshing short-term memory when current-session or uncommitted work makes `.arbor/memory.md` stale (auto via `arbor.in_session_memory_hygiene` hook intent on Codex; user-invoked on Claude Code);
- preparing `AGENTS.md` updates when the project guide or map needs to point the agent at changed durable context (auto via `arbor.goal_constraint_drift` hook intent on Codex; user-invoked on Claude Code).

On Codex, `AGENTS.md` is the reliable native startup bootstrap. `.codex/hooks.json` records project hook intents, but a fresh Codex prompt should not assume those intents already injected Arbor context. The generated `AGENTS.md` includes a Startup Protocol that tells the agent to load `AGENTS.md`, recent formatted git history, `.arbor/memory.md`, and `git status --short` before answering fresh-session, resumed-session, or project-overview prompts.

The memory hygiene hook is intentionally high-recall around dirty Arbor workflow state. It should fire before stops, skill handoffs, release gates, commits, cache syncs, failed checks, or user review checkpoints when Arbor-managed changes are uncommitted, and it should stay quiet for clean direct answers, read-only inspections, explicit no-write turns, or unrelated dirty files outside Arbor scope.

How long-term memory works:

Important: `AGENTS.md` is not Arbor's long-term memory database.

- `AGENTS.md` is the entrypoint. It holds stable goals, constraints, and a map of where important project knowledge lives.
- `git log` is the completed-work history. Good commits make finished features, fixes, and verification discoverable.
- project docs hold deeper design, review, and domain context that should not be compressed into `AGENTS.md`.
- `.arbor/memory.md` is only for short-term unresolved state before it is committed, resolved, or moved to durable docs.

Any Arbor-managed workflow that leaves uncommitted project changes must keep `.arbor/memory.md` current before the assistant stops or hands off. Review documents and `.arbor/workflow/features.json` hold workflow evidence, but they do not replace the short-term resume pointer. After a successful commit or publish resolves the work, prune resolved memory entries so git history becomes the source of truth.

Use it when:

- starting work in a new repo;
- resuming a repo after time away;
- preparing to commit and wanting memory to reflect only unresolved uncommitted work;
- changing project goals, constraints, naming, architecture, or the project map;
- building workflows where git log and project docs are part of the agent's long-term context.

### `intake`

Use `intake` when user input needs to be classified against Arbor's development workflow before any work begins.

What it does well:

- deciding whether a request belongs in Arbor-managed workflow or should stay as direct work;
- splitting compound requests into multiple intents when some parts need Arbor and others do not;
- distinguishing future backlog work from immediate active work;
- attaching short fragments or constraints to the current context instead of creating new items;
- selecting only one of the declared workflow routes: `brainstorm`, `develop`, `evaluate`, `converge`, `release`, or `none`;
- emitting UI-ready structured output so a future interface can render boundary decisions, warnings, route choices, and review focus without parsing prose.

Use it when:

- a user proposes a feature, bug, optimization, or later idea;
- a request may need planning, implementation, evaluation, convergence, or release;
- a prompt is ambiguous and may be a context patch rather than a new work item;
- you need to decide whether a document, codebase analysis, test request, or release instruction should enter Arbor.

### `brainstorm`

Use `brainstorm` after `intake` routes an Arbor-managed request to planning, clarification, impact analysis, research/experiment design, or feature breakdown.

What it does well:

- selecting and enforcing the required evidence mode: current conversation, user artifact, project context, codebase, paper, paper plus code, or mixed evidence;
- refusing to make settled claims before required evidence is loaded;
- asking one blocking clarification question instead of a broad questionnaire;
- exposing hidden design decisions that would otherwise become silent defaults;
- comparing approaches when there are real alternatives;
- splitting broad work into independently testable features;
- producing acceptance criteria and a shared review test plan before development;
- creating `docs/review/<feature>-review.md` with the Context/Test Plan section for ready implementation work;
- returning `route_correction` when a request is too direct or belongs to another skill.

Use it when:

- a request is too broad to implement safely in one pass;
- a codebase, paper, proposal, reviewer comment, or project artifact must be read before planning;
- the user wants to discuss an implementation, research, or experiment direction before coding;
- the next development unit needs explicit scope, acceptance criteria, and tests.

### `develop`

Use `develop` when an Arbor-managed feature or artifact change is authorized to execute.

What it does well:

- consuming upstream scope from known Arbor skills or another valid handoff source;
- recording why execution is authorized without owning the approval process;
- giving the agent implementation freedom inside the accepted scope;
- running developer self-tests against the brainstorm review test scope or recording why they could not run;
- appending developer review handoff evidence to the existing review document;
- routing only completed developer handoffs to `release` for a checkpoint before `evaluate`.

Use it when:

- `brainstorm` produced a selected feature and initialized review document that is ready for development;
- `intake` routed a clear managed artifact or narrow active implementation with an existing review context directly to development;
- `converge` selected evaluator findings for a correction loop;
- developer self-test and review handoff evidence must be prepared for `evaluate`.

### `evaluate`

Use `evaluate` when a completed Arbor develop handoff needs independent validation before convergence.

What it does well:

- consuming `develop.ready_for_evaluate` handoff evidence;
- loading the shared review document with brainstorm Context/Test Plan and Developer Round;
- replaying developer self-tests when useful;
- adding independent adversarial unit, scenario, edge, negative, mutation, static, schema, or coverage checks;
- appending Evaluator Round evidence to the same review document;
- routing completed evaluation results to `converge`.

Use it when:

- developer self-tests passed but need independent replay and attack;
- a review document contains a brainstorm test plan and Developer Round ready for evaluation;
- you need blocking findings, test gaps, scope drift, or residual risks structured for convergence;
- managed documentation artifacts need scenario/content validation against the review plan.

Successful evaluate handoffs route through `release` for an evaluator checkpoint before `converge`.

### `converge`

Use `converge` after `evaluate` appends an Evaluator Round for an Arbor-managed feature.

What it does well:

- deciding whether develop and evaluate agree;
- checking whether the accepted result still satisfies brainstorm goals, acceptance criteria, non-goals, and test scope;
- routing implementation/test findings back to `develop`;
- routing planning contradictions or missing brainstorm evidence back to `brainstorm`;
- routing missing developer/evaluator evidence to the owner of that evidence;
- updating the selected feature to `done` only after convergence is justified;
- routing converged features to internal `release` finalization.

Use it when:

- `evaluate` emitted a completed evaluation result for an Arbor feature;
- the workflow needs to decide whether to loop back to develop/evaluate or close the feature;
- the feature registry needs a final status update after independent evaluation;
- the current feature should move into release finalization after convergence.

### `release`

`release` is primarily an internal skill invoked after `develop`, `evaluate`, and `converge`, not the normal user-facing entrypoint.

What it does well:

- checkpointing developer and evaluator evidence before the next workflow skill runs;
- verifying convergence evidence and release readiness for the current feature;
- enforcing the git convention `<type>[optional scope]: <description>` with optional body and footers;
- gating commit, push, PR, tag, and publish behind explicit user authorization;
- appending Release Round evidence to the review document;
- selecting the next unfinished feature through structured `workflow_continuation`.

Use it directly only when a manual release request has equivalent review or convergence evidence loaded.

## Usage

Invocation phrasing is the same idea on both runtimes; replace the prefix with `$arbor` on Codex or `/arbor:arbor` on Claude Code (or use natural language — both runtimes auto-trigger Arbor when the request matches its description).

Initialize Arbor in a project:

```text
$arbor initialize this project
```

Resume work in a repository:

```text
$arbor resume this repo
```

Refresh memory before a commit:

```text
$arbor refresh project memory before commit
```

Update the project guide or map:

```text
$arbor update AGENTS.md for the new project constraints
```

Classify whether a request belongs in Arbor workflow:

```text
$intake classify this request before we decide what to do
```

Plan an Arbor-managed request before development:

```text
$brainstorm clarify and plan this feature before develop
```

Execute an authorized Arbor feature:

```text
$develop implement this selected feature and prepare review handoff
```

Evaluate a completed develop handoff:

```text
$evaluate independently validate this develop handoff
```

Decide whether a completed develop/evaluate loop has converged:

```text
$converge decide whether this feature is done and route release finalization
```

Finalize or checkpoint a feature when the required review evidence is already loaded:

```text
$release finalize this converged feature using the Arbor git convention
```

After initialization on Codex, the target project should contain:

```text
AGENTS.md
.arbor/memory.md
.codex/hooks.json
```

After initialization on Claude Code, the target project should contain:

```text
AGENTS.md
.arbor/memory.md
CLAUDE.md
```

A project that hosts both runtimes ends up with all four files, sharing the same `AGENTS.md` and `.arbor/memory.md`.

## Hooks

### Codex

`$arbor` registers three project-level hook intents into the target project's `.codex/hooks.json`:

- `arbor.session_startup_context`: emits startup context in the required order.
- `arbor.in_session_memory_hygiene`: emits memory, git status, and diff context for short-term memory refresh.
- `arbor.goal_constraint_drift`: emits project guide context when `AGENTS.md` may need to update its stable goals, constraints, or map pointers.

The hooks are registered by the skill during project initialization; Arbor does not ship a root-level Codex hook manifest. Treat the Codex hook file as a project contract and replay target, not as evidence that a new Codex model input already contains the packet. The generated `AGENTS.md` remains the native bootstrap that instructs the agent to load startup context before project-orientation answers.

### Claude Code

The installed plugin bundles a single `SessionStart` hook (`hooks/hooks.json` + `hooks/session-start`) that fires on the `startup` and `resume` sources. Its Python adapter calls the shared `run_session_startup_hook.py`, applies a budget-aware truncation policy so the rendered packet stays under Claude Code's `additionalContext` cap, and prints the packet to stdout for automatic injection into the conversation.

Memory hygiene and goal-constraint drift are not auto-fired on Claude Code (Claude Code has no native event that delivers a context packet at the right time). Invoke them through the user-driven workflows above; the underlying scripts are the same on both runtimes.

## Adapter Validation

Run the local adapter smoke check after changing plugin manifests, Claude hook
files, or runtime-facing Arbor initialization behavior:

```bash
python3 plugins/arbor/skills/arbor/scripts/check_plugin_adapters.py
python3 plugins/arbor/skills/arbor/scripts/check_skill_packages.py
```

The check validates Codex and Claude manifest identity fields, the Claude
marketplace entry, the Claude `SessionStart` hook shape, the absence of
out-of-scope plugin-level `agents/` and `PreCompact` adapters, a synthetic
Claude startup event with budget-aware context truncation, and every Arbor skill
package without relying on `quick_validate.py` being on the shell `PATH`.

For a real Claude Code session smoke test, load the local plugin with:

```bash
claude --plugin-dir ./plugins/arbor
```

Then run `/reload-plugins` and check that `/arbor:arbor` and the other
`/arbor:*` skills are available.

## Legacy Memory Path

Arbor v0.1 used `.codex/memory.md` for short-term memory. Current Arbor uses `.arbor/memory.md` so the same memory file can be shared by future runtime adapters.

During explicit initialization, if `.arbor/memory.md` is missing and legacy `.codex/memory.md` exists, Arbor copies the legacy content into `.arbor/memory.md` and preserves the old file. It does not merge or delete legacy files automatically.

## Version

Current version:

```text
0.4.1
```

Version files:

```text
plugins/arbor/.codex-plugin/plugin.json
plugins/arbor/.claude-plugin/plugin.json
```

Marketplace files:

```text
.agents/plugins/marketplace.json
.claude-plugin/marketplace.json
```
