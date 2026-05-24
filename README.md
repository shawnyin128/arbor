# Arbor

Arbor is a project-context and workflow plugin for Codex and Claude Code. It
helps agents resume repository work with the right local context, keep short-term
state separate from durable project knowledge, and run managed development work
through explicit checkpoints.

Arbor creates and maintains:

- `AGENTS.md`: durable project guide and map.
- `.arbor/memory.md`: short-term unresolved session memory.
- `.codex/hooks.json`: Codex project hook intent file when initialized.
- `CLAUDE.md`: Claude Code bridge to `AGENTS.md` and `.arbor/memory.md`.

Arbor is intentionally lightweight. It controls workflow shape and context
placement, not the agent's reading depth, implementation strategy, or test
design.

## Install

### Codex

```bash
codex plugin marketplace add shawnyin128/arbor
```

If `codex` is not on your macOS `PATH`:

```bash
/Applications/Codex.app/Contents/Resources/codex plugin marketplace add shawnyin128/arbor
```

SSH:

```bash
codex plugin marketplace add git@github.com:shawnyin128/arbor.git
```

Upgrade or remove:

```bash
codex plugin marketplace upgrade arbor
codex plugin marketplace remove arbor
```

### Claude Code

Inside Claude Code:

```text
/plugin marketplace add shawnyin128/arbor
/plugin install arbor@arbor
/reload-plugins
```

The Claude plugin includes `SessionStart` and `Stop` hooks. `SessionStart`
injects startup context on startup/resume. `Stop` quietly guards
`.arbor/memory.md` when an Arbor-managed dirty worktree is about to stop.

## Workflow Model

Prefer explicit skill invocation for managed workflow entrypoints. The public
entrypoints are:

```text
Codex        Claude Code          Purpose
$arbor       /arbor:arbor         initialize, resume, project context
$brainstorm  /arbor:brainstorm    plan scope, acceptance criteria, test plan
$feedback    /arbor:feedback      triage bug reports, failed checks, corrections
$converge    /arbor:converge      run/continue the managed quality loop
```

Internal stages:

```text
develop, evaluate, release checkpoints/finalization
```

The core flow is:

```text
brainstorm -> converge
converge   -> internal develop -> release(checkpoint_develop: local commit)
           -> internal evaluate -> release(checkpoint_evaluate)
           -> convergence decision -> internal release(finalize_feature)
feedback   -> brainstorm | converge | needs evidence | direct response
```

`develop and evaluate are internal stages`. Release is internal too. Users
should not be asked to invoke release directly. Push, PR, tag, publish, or cache
sync happens only after convergence and only when that exact external action was
explicitly authorized. Intermediate develop/evaluate checkpoints may create local
checkpoint commits, but they do not push.

Managed workflow state lives in:

- `.arbor/workflow/features.json`
- `docs/review/<feature>-review.md`

## Skill Guide

### `arbor`

Use `arbor` for startup and project context:

- initialize `AGENTS.md`, `.arbor/memory.md`, hooks, and Claude bridge files;
- load startup context in order: `AGENTS.md`, recent formatted git history,
  `.arbor/memory.md`, and `git status --short`;
- refresh short-term memory before handoff or commit;
- update the project map when durable project structure changes.

### `brainstorm`

Use `brainstorm` when work needs planning before implementation:

- broad feature or workflow ideas;
- ordinary bug reports without review context;
- requirements that need acceptance criteria, done-when criteria, or a test
  plan;
- codebase, paper, proposal, or reviewer evidence that must be read before a
  settled plan.

Canonical examples:

- `$brainstorm think through the boundary and test plan before editing`
- `$brainstorm read this reviewer feedback and plan the change`
- Do not use `brainstorm` for typo-level direct edits, completed evaluation,
  convergence decisions, or release gates.

### `feedback`

Feedback decides whether user feedback should go to `brainstorm`, `converge`,
needs more evidence, or can be answered directly.

Trigger it from an explicit `$feedback` / `/arbor:feedback` invocation, or from
a feedback-shaped prompt where the next public owner is unclear. The word
"feedback" alone is not a trigger; Arbor should keep avoiding keyword-only
routing.

Canonical examples:

- `$feedback this bug still happens in the current Arbor feature; decide the right next step`
- `$feedback the reviewer says the acceptance criteria are wrong`
- `$brainstorm plan the feedback skill trigger rules`
- Do not use `feedback` as a general project-status command, release command, or
  universal technical-request router.

### `converge`

Use `converge` when review context already exists and the current managed
quality loop should continue, repair, verify, or close.

Canonical examples:

- `$converge continue the current Arbor quality loop`
- `$converge fix this bug in the current Arbor feature and verify it`
- `$converge decide whether the accepted evaluation proves the feature is done`
- Do not use `converge` for generic project status or one-off explanations.

### Internal Stages

`develop`, `evaluate`, and `release` are internal stages selected by the
workflow:

- `develop` implements accepted scope and records developer self-test evidence.
- `evaluate` independently validates the developer handoff and labels weak pass
  substitutes.
- `release` records checkpoint/finalization evidence, including the automatic
  local checkpoint commit before internal `evaluate`, and handles gating
  finalization commit, push, PR, tag, and publish behind explicit user
  authorization.

## Context And Evidence Rules

`AGENTS.md` is not a memory database. It is the entrypoint for stable project
goals, constraints, and a map to deeper context. Completed work belongs in git
history. Deeper design and review evidence belongs in project docs. Unresolved
short-term state belongs in `.arbor/memory.md`.

The placement rule is deliberately narrow: it improves where context lives, not
how the agent must reason or implement. Put task-specific workflows in skills or
referenced docs, and fetch frequently changing external context through tools or
links instead of copying it into startup guidance. See
`plugins/arbor/skills/arbor/references/guidance-placement-guard.md`.

Managed features carry a done-when verification thread: `brainstorm` records
done-when criteria, `develop` maps evidence to them, `evaluate` labels weak pass
substitutes, `converge` checks agreement, and `release` checks that evidence is
present. In short, evaluate labels weak pass substitutes, release checks that verification evidence exists before finalization or publish, and the thread does not force one test type or pull small direct tasks into Arbor.

Managed features also carry a decision trace handoff: key decisions, rejected
options, implementation-time decisions, decision invariants, and decision drift
checks stay visible across the loop. It does not require subagents or worktrees.

Optional delegation packet and effort budget guidance exists for separable
evidence gathering. A packet names the objective, output format, tools/sources,
boundaries, effort budget, context pointers, and stop conditions. Delegation
does not require subagents or worktrees; direct answers, simple edits, tightly
coupled coding, and tightly coupled workflow changes remain single-threaded by default.

Workflow validation is outcome-first. Check final state, checkpoint outcomes,
rendered output, review evidence, process state, git/file side effects,
realistic replay, trace evidence, and weak-pass gaps before demanding exact
path matching. This does not require LLM judges, fixed path matching, exact
turn-by-turn replay, or one universal test type by default. See
`plugins/arbor/skills/arbor/references/outcome-eval-observability.md`.

When correction loops become unreliable, Arbor uses a loop-health advisory. It
surfaces repeated same-class failures, evidence conflicts, weak replay evidence,
context contamination, or round-limit pressure. It may recommend narrowing
scope, exact replay, or a fresh-session handoff, but it does not automatically clear context.
Subagents and worktrees remain optional strategies, and a normal correction loop
should continue when the owner and replay target are clear.

For versioned releases, `release` checks the actual version management method.
Plugin manifests, `package.json`, `pyproject.toml`, tags, or documented policy
determine the target version. If a versioned artifact changed and the required
bump is missing, release blocks commit, publish, push, tag, or cache sync until
the version source files match the target version.

## Hooks

Codex initialization writes three hook intents into target-project
`.codex/hooks.json`:

- `arbor.session_startup_context`
- `arbor.in_session_memory_hygiene`
- `arbor.goal_constraint_drift`

Treat `.codex/hooks.json` as a contract/replay target, not proof that startup
context has already been injected. `AGENTS.md` remains the reliable native
bootstrap.

Claude Code ships:

- `SessionStart`: injects startup context for `startup` and `resume`;
- `Stop`: defaults to a silent memory guard and can use
  `ARBOR_STOP_MEMORY_HYGIENE_MODE=block` for the older blocking behavior.

## Validation

Use these checks after package, manifest, hook, workflow, or README changes:

```bash
python3 plugins/arbor/skills/arbor/scripts/check_plugin_adapters.py
python3 plugins/arbor/skills/arbor/scripts/check_skill_packages.py
python3 scripts/check_workflow_simulations.py
```

For runtime-facing changes, static fixture checks and JSON schema checks are
preflight only. Use real runtime replay when feasible, and inspect rendered
workflow checkpoints in the user's active chat language. English prompts use the
skill's canonical headings; non-English prompts should use localized heading
equivalents. See
`plugins/arbor/skills/arbor/references/rendered-checkpoint-protocol.md`.

Run tracked local real-chain guards with:

```bash
python3 plugins/arbor/skills/arbor/scripts/check_real_workflow_chains.py --runtime local
```

Run selected Codex runtime cases when needed:

```bash
python3 plugins/arbor/skills/arbor/scripts/check_real_workflow_chains.py --runtime codex --cases R02,R07
```

For Claude Code smoke tests:

```bash
claude --plugin-dir ./plugins/arbor
```

Then run `/reload-plugins` and check that `/arbor:arbor` and the other public
Arbor skills are available.

## Legacy Memory Path

Arbor v0.1 used `.codex/memory.md`. Current Arbor uses `.arbor/memory.md` so
Codex and Claude Code share the same project-local memory. During explicit
initialization, Arbor copies legacy `.codex/memory.md` only when
`.arbor/memory.md` is missing. It does not merge or delete legacy files
automatically.

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
