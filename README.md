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

Run `/reload-plugins` afterward to activate the skill and the bundled `SessionStart` and `Stop` hooks in the current session. The `SessionStart` hook auto-injects the Arbor startup packet (AGENTS.md, formatted git log, `.arbor/memory.md`, git status) on `startup` and `resume` sources, trimmed to fit Claude Code's context-injection cap. The `Stop` hook emits the memory hygiene packet when an Arbor-managed worktree is dirty.

## Skills

Arbor ships the core project-context skill plus public workflow entrypoints and
internal workflow stages, available on both runtimes:

```text
Public entrypoints:

Codex:        $arbor
Claude Code:  /arbor:arbor

Codex:        $brainstorm
Claude Code:  /arbor:brainstorm

Codex:        $feedback
Claude Code:  /arbor:feedback

Codex:        $converge
Claude Code:  /arbor:converge

Internal workflow stages and gates:

develop, evaluate, release checkpoints/finalization
```

The public entrypoints are parallel, not a hidden intake chain:

```text
arbor      -> startup, resume, and project context
brainstorm -> plan, review context, and test plan -> converge
feedback   -> brainstorm | converge | needs evidence | direct response
converge   -> internal develop -> release(checkpoint_develop: local commit)
           -> internal evaluate -> release(checkpoint_evaluate)
           -> convergence decision -> release(finalize_feature)
```

`brainstorm` is the public planning entrypoint for managed work: it turns
requests into features, acceptance criteria, done-when criteria, and test scope.
Feedback decides whether user feedback should go to `brainstorm`, `converge`,
needs more evidence, or can be answered directly. It accepts bug reports,
regressions, failed checks, reviewer comments, and corrections to prior Arbor
work, then stops with a visible routing checkpoint instead of implementing or
evaluating directly. The word "feedback" alone is not a trigger when another
public entrypoint already fits.
`converge` is the public quality-loop entrypoint: it owns bug, defect, review
finding, and current-loop continuation requests after planning context exists,
then internally drives `develop` and `evaluate` as needed. `develop`,
`evaluate`, and `converge` append evidence to the same review document, while
`release` records checkpoints/finalization and keeps workflow state discoverable
through git and the feature registry. In this model, develop and evaluate are internal stages.
Develop, evaluate, and release are internal stages, not
user-facing commands. After a successful internal `develop`,
`release(checkpoint_develop)` creates an automatic local checkpoint commit before
internal `evaluate`; after an appendable internal `evaluate`,
`release(checkpoint_evaluate)` creates the evaluator checkpoint commit before
the convergence decision. After `converge` accepts the feature, internal release
finalization checks versioning and git readiness before any finalization commit
or public push. Automatic quality-loop runs must pass through both release gates
and stop if either checkpoint commit cannot be created. Push, PR, tag, publish,
or cache sync happens only after convergence and only when that external action
was explicitly authorized; do not push at intermediate develop/evaluate stages.

Two workflow artifacts carry state between skills:

- `.arbor/workflow/features.json` is the feature queue and status index.
- `docs/review/<feature>-review.md` is the shared evidence document for one feature, starting with the brainstorm Context/Test Plan and then accumulating Developer, Evaluator, Convergence, and Release rounds.

Managed features also carry a done-when verification thread. `brainstorm` states what completion means, `develop` maps self-tests to those criteria, `evaluate` challenges them and labels weak pass substitutes, `converge` checks agreement against the original goal, and `release` checks that verification evidence exists before finalization or publish. This thread uses artifact-appropriate verification and does not force one test type or pull small direct tasks into Arbor.

Managed features also carry a decision trace handoff. `brainstorm` records key decisions, rejected options, allowed implementation discretion, and decision invariants. `develop` records implementation-time decisions and deviations against that trace. `evaluate` checks for decision drift and hidden-decision conflicts, and `converge` checks decision trace consistency before marking work done. This does not require subagents or worktrees and is not a default multi-agent orchestration layer; it preserves agent judgment while keeping workflow decisions visible.

For separable evidence gathering, Arbor documents an optional delegation packet and effort budget. A packet names the objective, output format, tools/sources, boundaries, effort budget, context pointers, and stop conditions for a bounded investigation. This does not require subagents or worktrees: direct answers, simple edits, tightly coupled coding, and tightly coupled workflow changes remain single-threaded by default.

For workflow-facing validation, Arbor keeps evaluation outcome-first and observable. `evaluate` checks final state, checkpoint outcomes, rendered output, review evidence, process state, git/file side effects, realistic replay, and trace evidence before demanding exact path matching. `converge` decides whether weak-pass gaps block the brainstorm goal, and `release` checks that required evidence exists before finalization or publish. This does not require LLM judges, fixed path matching, exact turn-by-turn replay, or one universal test type by default.

For versioned projects, `release` also checks the actual version management method before finalization or publish. Plugin manifests, `package.json`, `pyproject.toml`, git tags, or a documented custom policy determine the target version; Arbor does not reuse a stale version or invent a bump without source evidence. When a versioned artifact changed but the selected bump is missing, release blocks commit, push, tag, publish, or cache sync until the version source files match the target version.

When correction loops become unreliable, Arbor uses a loop-health advisory instead of an automatic reset. `evaluate` can mark evidence conflicts, weak replay evidence, or context contamination; `converge` can surface repeated same-class failures before another broad correction. The advisory may recommend narrowing scope, re-brainstorming, exact runtime replay, or a fresh-session handoff, but it does not automatically clear context, spawn subagents, or create worktrees. Subagents and worktrees remain optional strategies, and a normal correction loop with a clear owner and replay target should continue below the round limit.

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
- preparing `AGENTS.md` updates when the project guide or map needs to point the agent at changed durable context. The drift packet includes top-level project structure, mapped path validation, and `Project Map Drift Candidates`; when it reports `update-needed`, update the `Project Map` before handoff or release unless the missing or stale path is intentionally excluded (auto via `arbor.goal_constraint_drift` hook intent on Codex; user-invoked on Claude Code).
- validating process-state facts before handoff, checkpoint, release, or publish. `scripts/check_process_state.py` is read-only and checks the feature registry, review document links, phase evidence, short-term memory, and optional Release Round evidence without choosing implementation or test strategy.
- guarding rendered workflow checkpoints so normal users see readable status, findings, decisions, and next steps instead of raw `*.v1` packets, route labels, terminal-state labels, or unexplained internal ids. `references/rendered-checkpoint-protocol.md` defines this output boundary for workflow checkpoints only; it is not a template for direct answers or a constraint on implementation strategy.
- carrying done-when verification from planning through release so managed features show what completion means, how developer evidence covers it, how evaluation challenged it, and whether release has enough proof to finalize. `references/done-when-verification-thread.md` defines this evidence thread without prescribing implementation strategy or a single test type.
- carrying decision trace handoff from planning through convergence so key decisions, implementation-time decisions, and decision drift remain visible without requiring subagents or worktrees. `references/decision-trace-handoff.md` defines this handoff contract without turning Arbor into a default multi-agent orchestration system.
- documenting optional delegation packets with objective, output format, tools/sources, boundaries, effort budget, context pointers, and stop conditions for bounded evidence gathering. `references/delegation-packet-effort-budget.md` keeps direct answers and tightly coupled coding single-threaded by default.
- keeping workflow validation outcome-first and observable: final state, checkpoint outcomes, rendered output, review evidence, process state, git/file side effects, realistic replay, trace evidence, and explicit weak-pass gaps matter more than exact path matching unless the path is the claimed behavior. `references/outcome-eval-observability.md` keeps this deterministic by default and does not require LLM judges.
- surfacing loop-health advisories when repeated same-class failures, evidence conflicts, weak replay evidence, or context contamination make another automatic correction unreliable. `references/loop-health-advisory.md` keeps the response advisory-only: recommend narrowing scope, re-brainstorming, exact runtime replay, or a fresh-session handoff without requiring subagents, worktrees, fan-out execution, or automatic context clearing.

On Codex, `AGENTS.md` is the reliable native startup bootstrap. `.codex/hooks.json` records project hook intents, but a fresh Codex prompt should not assume those intents already injected Arbor context. The generated `AGENTS.md` includes a Startup Protocol that tells the agent to load `AGENTS.md`, recent formatted git history, `.arbor/memory.md`, and `git status --short` before answering fresh-session, resumed-session, or project-overview prompts.

The memory hygiene hook is intentionally high-recall around dirty Arbor workflow state. It should fire before stops, skill handoffs, release gates, commits, cache syncs, failed checks, or user review checkpoints when Arbor-managed changes are uncommitted, and it should stay quiet for clean direct answers, read-only inspections, explicit no-write turns, or unrelated dirty files outside Arbor scope.

The AGENTS guide-drift hook is intentionally high-recall around durable project-map changes. It should fire after adding, removing, or renaming top-level project entrypoints, new skills, hook adapters, runtime integration paths, or shared helper modules, and before release/publish/handoff when project structure changed. It should not add transient caches, scratch output, pycache, or current-session progress to `AGENTS.md`.

How long-term memory works:

Important: `AGENTS.md` is not Arbor's long-term memory database.

- `AGENTS.md` is the entrypoint. It holds stable goals, constraints, and a map of where important project knowledge lives.
- `git log` is the completed-work history. Good commits make finished features, fixes, and verification discoverable.
- project docs hold deeper design, review, and domain context that should not be compressed into `AGENTS.md`.
- `.arbor/memory.md` is only for short-term unresolved state before it is committed, resolved, or moved to durable docs.
- task-specific workflows, long examples, and domain methods belong in skills or referenced project docs, not in startup guidance.
- frequently changing external context should be fetched through tools, MCP servers, URLs, or task-specific docs instead of copied into `AGENTS.md`.

Any Arbor-managed workflow that leaves uncommitted project changes must keep `.arbor/memory.md` current before the assistant stops or hands off. Review documents and `.arbor/workflow/features.json` hold workflow evidence, but they do not replace the short-term resume pointer. After a successful commit or publish resolves the work, prune resolved memory entries so git history becomes the source of truth.

The placement rule is deliberately narrow: it improves context quality without imposing fixed reading limits, mandatory plan-first behavior, mandatory subagents or worktrees, fixed implementation strategy, or fixed test suites.

Use it when:

- starting work in a new repo;
- resuming a repo after time away;
- preparing to commit and wanting memory to reflect only unresolved uncommitted work;
- changing project goals, constraints, naming, architecture, or the project map;
- building workflows where git log and project docs are part of the agent's long-term context.

### `brainstorm`

Use `brainstorm` when a request needs Arbor-managed planning, clarification, impact analysis, research/experiment design, or feature breakdown before the quality loop.

What it does well:

- selecting and enforcing the required evidence mode: current conversation, user artifact, project context, codebase, paper, paper plus code, or mixed evidence;
- refusing to make settled claims before required evidence is loaded;
- asking one material clarification question at a time, then continuing until the requirement is clear instead of stopping after the first question;
- exposing hidden design decisions that would otherwise become silent defaults;
- comparing approaches when there are real alternatives;
- splitting broad work into independently testable features;
- producing acceptance criteria and a shared review test plan before the quality loop;
- defining done-when criteria so downstream evidence can prove the requested outcome;
- creating `docs/review/<feature>-review.md` with the Context/Test Plan section for ready implementation work;
- returning `route_correction` when a request is too direct or belongs to another skill.

Use it when:

- a request is too broad to implement safely in one pass;
- a codebase, paper, proposal, reviewer comment, or project artifact must be read before planning;
- the user wants to discuss an implementation, research, or experiment direction before coding;
- the next managed work unit needs explicit scope, acceptance criteria, and tests.

Canonical examples:

- `$brainstorm think through the boundary and test plan before editing` for broad redesign, research, experiment, or workflow work.
- `$brainstorm read this reviewer feedback and plan the change` when external/user artifacts determine the plan.
- Do not use `brainstorm` for typo-level direct edits, completed evaluation, convergence decisions, or release gates.

### `feedback`

Use `feedback` when the user gives bug information, reviewer comments, failed
checks, regression reports, or corrections to prior Arbor work and the next
public owner is not already obvious.

Trigger it from an explicit `$feedback` / `/arbor:feedback` invocation, or from
a feedback-shaped prompt where the owner is unclear. Do not insert it in front
of a clearly named public skill: new feature planning still belongs to
`brainstorm`, known current-loop continuation still belongs to `converge`,
project status still belongs to `arbor` or a direct answer, and finalization
still belongs to `release`.

What it does well:

- deciding whether feedback changes requirements, acceptance criteria, or test
  scope and should go to `brainstorm`;
- deciding whether feedback is an actionable defect in an existing
  Arbor-managed feature and should go to `converge`;
- keeping prose-only or simple chat-output corrections direct;
- asking for missing logs, tracebacks, reproduction details, reviewer comments,
  or review context before routing when that evidence changes the owner;
- refusing to route ordinary user feedback to public `develop` or `evaluate`;
- avoiding keyword-only routing when another public entrypoint already fits.

Use it when:

- the user explicitly invokes `$feedback` or `/arbor:feedback`;
- the user reports a bug but it is unclear whether review context already
  exists;
- a reviewer or evaluator comment may be either a planning change or a repair
  finding;
- the user corrects the last Arbor result and asks what should happen next;
- a direct fix request might need the managed quality loop but should stay under
  `converge`.

Canonical examples:

- `$feedback this bug still happens in the current Arbor feature; decide the right next step` routes to `converge` when review context exists.
- `$feedback this crash has no review context yet; decide whether to plan or fix` routes to `brainstorm` until scope and tests exist.
- `$feedback the reviewer says the acceptance criteria are wrong` routes to `brainstorm`.
- `$brainstorm plan the feedback skill trigger rules` stays in `brainstorm`; the word "feedback" alone does not trigger this skill.
- Do not use `feedback` as a general project-status command, release command, or universal technical-request router.

### `develop`

`develop` is an internal implementation stage. Do not call it directly for
ordinary user requests; call `converge` to continue, fix, or repair an
Arbor-managed quality loop. `converge` invokes `develop` when a selected
feature, bug, defect, or evaluator finding has enough review context to execute.

What it does well:

- consuming upstream scope from known Arbor skills or another valid handoff source;
- recording why execution is authorized without owning the approval process;
- giving the agent implementation freedom inside the accepted scope;
- running developer self-tests against the brainstorm review test scope or recording why they could not run;
- mapping developer self-tests to accepted done-when criteria;
- appending developer review handoff evidence to the existing review document;
- routing only completed developer handoffs to `release` for an automatic local checkpoint commit before internal `evaluate`.
- treating automatic develop/evaluate/converge continuation as permission for internal release checkpoints, not permission to skip release or finalization gates.

Internal stage use:

- `converge` selected an approved feature or evaluator finding for implementation;
- `brainstorm` produced a selected feature and review context that `converge` is now driving;
- developer self-test and review handoff evidence must be prepared for `evaluate`.

### `evaluate`

`evaluate` is an internal validation stage. Do not call it directly for ordinary
user requests; call `converge` to continue, verify, or repair an Arbor-managed
quality loop. `converge` invokes `evaluate` after an internal developer handoff
is checkpointed and ready for independent validation.

What it does well:

- consuming `develop.ready_for_evaluate` handoff evidence;
- loading the shared review document with brainstorm Context/Test Plan and Developer Round;
- replaying developer self-tests when useful;
- adding independent adversarial unit, scenario, edge, negative, mutation, static, schema, or coverage checks;
- challenging done-when criteria and labeling weak pass evidence when exact runtime proof was unavailable;
- marking loop-health risk when evidence conflicts, weak replay evidence, or context contamination make the next correction unreliable, without fixing implementation directly;
- appending Evaluator Round evidence to the same review document;
- routing completed evaluation results to `converge`.

Internal stage use:

- developer self-tests passed but need independent replay and attack;
- a review document contains a brainstorm test plan and Developer Round ready for evaluation;
- you need blocking findings, test gaps, scope drift, or residual risks structured for convergence;
- managed documentation artifacts need scenario/content validation against the review plan.

Successful evaluate handoffs route through `release` for an evaluator checkpoint before `converge`.

### `converge`

Use `converge` as the public quality-loop entrypoint for an Arbor-managed
feature after planning exists. It accepts bug reports, defects, evaluator
findings, and current-loop continuation requests, then owns the internal
`develop`/`evaluate` cycle until the feature either converges, needs planning,
is blocked, or needs a user decision.

What it does well:

- deciding whether develop and evaluate agree;
- checking whether the accepted result still satisfies brainstorm goals, acceptance criteria, non-goals, and test scope;
- checking whether developer and evaluator evidence satisfies the done-when criteria;
- driving implementation/test findings through internal `develop` and `evaluate`;
- routing planning contradictions or missing brainstorm evidence back to `brainstorm`;
- routing missing developer/evaluator evidence to the correct internal stage;
- surfacing loop-health risk for repeated same-class failures, evidence conflicts, weak replay evidence, context contamination, or round-limit pressure before continuing a broad automatic loop;
- updating the selected feature to `done` only after convergence is justified;
- routing converged features to internal `release` finalization.

Use it when:

- `evaluate` emitted a completed evaluation result for an Arbor feature;
- the workflow needs to decide whether to run or repeat the internal develop/evaluate cycle or close the feature;
- the user reports a bug, defect, regression, or failed check against an existing Arbor-managed feature;
- the feature registry needs a final status update after independent evaluation;
- the current feature should move into release finalization after convergence.

Canonical examples:

- `$converge continue the current Arbor quality loop` when a managed feature exists but the next owner is unclear.
- `$converge fix this bug in the current Arbor feature and verify it` when the feedback is an implementation/test defect with existing review context.
- `$converge decide whether the accepted evaluation proves the feature is done` after evaluator evidence exists.
- `$converge handle this evaluator finding and keep the repair/validation loop together` when a correction loop or planning gap needs ownership.
- Do not use `converge` for generic project status or one-off explanations.

### `release`

`release` is an internal skill invoked after `develop`, `evaluate`, and
`converge`; it is not a user-facing entrypoint and users should not call
`$release` or `/arbor:release` directly.

What it does well:

- checkpointing developer and evaluator evidence before the next workflow skill runs, including a local checkpoint commit after successful `develop`;
- verifying convergence evidence and release readiness for the current feature;
- checking that required done-when verification evidence exists before finalization or publish;
- enforcing the git convention `<type>[optional scope]: <description>` with optional body and footers;
- gating finalization commit, push, PR, tag, and publish behind explicit user authorization;
- appending Release Round evidence to the review document;
- selecting the next unfinished feature through structured `workflow_continuation`.

Use `converge` for the public quality-loop entrypoint. If the user asks to
finish, publish, push, or sync a converged feature, keep that as a user intent
for the internal release gate after convergence instead of exposing a public
release command.

## Usage

Invocation phrasing is the same idea on both runtimes; replace the prefix with `$arbor` on Codex or `/arbor:arbor` on Claude Code. Prefer explicit skill invocation for managed workflow entrypoints; if automatic skill selection misses, call the intended public skill manually.

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

Plan an Arbor-managed request before the quality loop:

```text
$brainstorm clarify and plan this feature before the implementation/review loop
$brainstorm turn this broad workflow redesign into small reviewable features with acceptance criteria
$brainstorm read this reviewer feedback and plan the experiment change before coding
```

Triage feedback before choosing a workflow owner:

```text
$feedback this bug still happens in the current Arbor feature; decide the right next step
$feedback the reviewer says the acceptance criteria are wrong
$feedback your last answer missed my question; answer it directly
```

Continue or repair a managed quality loop:

```text
$converge decide whether this feature is done and route release finalization
$converge continue the current Arbor quality loop from the available review evidence
$converge fix this bug in the current Arbor feature and verify it
$converge handle the evaluator's findings and keep the repair/validation loop together
```

Finish or publish a managed feature through the quality loop:

```text
$converge finish the current feature; after convergence, create the required release commit and push only if explicitly authorized
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

The installed plugin bundles two hooks in `hooks/hooks.json`:

- `SessionStart` (`hooks/session-start`) fires on the `startup` and `resume` sources. Its Python adapter calls the shared `run_session_startup_hook.py`, applies a budget-aware truncation policy so the rendered packet stays under Claude Code's `additionalContext` cap, and prints the packet to stdout for automatic injection into the conversation.
- `Stop` (`hooks/stop-memory-hygiene`) is the Claude Code mapping of the Codex `arbor.in_session_memory_hygiene` hook. Claude Code has no native checkpoint event, and `Stop` output can re-enter the agent loop as a visible continuation, so the adapter defaults to a silent memory guard when the Arbor worktree is dirty: if `.arbor/memory.md` is missing, empty, or lacks a meaningful `In-flight` entry, it writes a generic resume pointer and returns non-blocking JSON with suppressed hook output. It still honors `stop_hook_active` first so it can never loop. Set `ARBOR_STOP_MEMORY_HYGIENE_MODE=block` to opt into the older blocking behavior, where the adapter calls the shared `run_memory_hygiene_hook.py` and returns the hygiene packet as the block reason.

Goal-constraint drift is not auto-fired on Claude Code: there is no native event that maps to `project.guide_drift`. Invoke it through the user-driven workflows above; the underlying scripts are the same on both runtimes.

## Adapter Validation

Run the local adapter smoke check after changing plugin manifests, Claude hook
files, or runtime-facing Arbor initialization behavior:

```bash
python3 plugins/arbor/skills/arbor/scripts/check_plugin_adapters.py
python3 plugins/arbor/skills/arbor/scripts/check_skill_packages.py
```

The check validates Codex and Claude manifest identity fields, the Claude
marketplace entry, the Claude `SessionStart` and `Stop` hook shapes, the absence
of out-of-scope plugin-level `agents/` and `PreCompact` adapters, a synthetic
Claude startup event with budget-aware context truncation, the `Stop`
memory-hygiene adapter's self-gating (clean worktree, dirty Arbor worktree by
default, non-Arbor project, and `stop_hook_active` all stay silent; dirty Arbor
worktrees get a quiet fallback memory entry when one is missing; opt-in block
mode returns the hygiene packet), and every Arbor skill package without relying on
`quick_validate.py` being on the shell `PATH`.

For workflow behavior, these checks are only preflight. The real release gate is
the runtime case matrix in
`plugins/arbor/skills/arbor/references/real-workflow-chain-review.md`: it must
use real Codex or Claude Code processes, real Arbor skill invocation, rendered
final responses, and real git/file side-effect assertions. Ignored simulation
fixtures and baseline scripts are optional development aids and must not be
reported as full-chain validation.

Rendered checkpoint validation follows
`plugins/arbor/skills/arbor/references/rendered-checkpoint-protocol.md`. For
workflow-facing changes, inspect at least one captured `final-response.md` from a
real runtime replay when feasible; static fixture checks and JSON schema checks
are preflight only. User-facing checkpoint prose should follow the user's active
chat language; the English section headings in skill files are canonical for
English prompts, while non-English prompts should render localized heading
equivalents in the same order.

Guidance placement follows
`plugins/arbor/skills/arbor/references/guidance-placement-guard.md`. Keep
startup guidance concise, move task-specific methods into skills or referenced
docs, keep unresolved state in `.arbor/memory.md`, keep review evidence in
`docs/review/`, and fetch volatile external context through tools or links. This
guard is about where context lives, not how the agent must reason or implement.

Done-when verification follows
`plugins/arbor/skills/arbor/references/done-when-verification-thread.md`.
Managed work should state task-appropriate done-when criteria, map developer and
evaluator evidence back to those criteria, label weak pass substitutes, and let
release check evidence existence without re-evaluating correctness. This thread
does not force one test type or route small direct tasks into Arbor.

Decision trace handoff follows
`plugins/arbor/skills/arbor/references/decision-trace-handoff.md`.
Managed work should carry key decisions, rejected options, allowed implementation
discretion, decision invariants, implementation-time decisions, decision
deviations, decision drift checks, and hidden-decision conflict checks across the
workflow. This handoff does not require subagents or worktrees and is not a
default multi-agent orchestration layer.

Delegation packet and effort budget guidance follows
`plugins/arbor/skills/arbor/references/delegation-packet-effort-budget.md`.
Delegation remains optional and bounded. When used, the packet should name the
objective, output format, tools/sources, boundaries, effort budget, context
pointers, and stop conditions. The guidance does not require subagents or
worktrees, does not require fan-out execution, and keeps direct answers, simple
edits, tightly coupled coding, and tightly coupled workflow changes
single-threaded by default.

Outcome evaluation and observability follows
`plugins/arbor/skills/arbor/references/outcome-eval-observability.md`.
Workflow-facing validation should inspect final state, checkpoint outcomes,
rendered output, review evidence, process state, git/file side effects,
realistic replay, trace evidence, and explicit weak-pass gaps before demanding
exact path matching. This does not require LLM judges, fixed path matching,
exact turn-by-turn replay, or one universal test type by default.

Real routing replay reports include user-level scenario metadata and
classification counts for stable pass, weak pass, wrong route,
flaky/ambiguous, blocked runtime, and skipped cases. A weak pass is acceptable
evidence only when the report explains that exact route telemetry was unavailable
and the strongest observable substitute passed.

Run tracked local-only real-chain guards with:

```bash
python3 plugins/arbor/skills/arbor/scripts/check_real_workflow_chains.py --runtime local
```

Run runtime cases explicitly when real model execution is intended, for example:

```bash
python3 plugins/arbor/skills/arbor/scripts/check_real_workflow_chains.py --runtime codex --cases R02,R07
```

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
1.0.1
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
