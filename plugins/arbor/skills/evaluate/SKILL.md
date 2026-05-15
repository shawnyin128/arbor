---
name: evaluate
description: Independently validate an Arbor develop handoff or active Arbor code-review continuation by replaying developer evidence, adding adversarial unit/scenario checks, appending evaluator review evidence, and emitting structured output for release checkpointing before converge.
---

# Evaluate

Validate completed Arbor work by trying to break it.

## Purpose

Use `evaluate` when `develop` has completed one Arbor-managed feature or managed artifact and produced a `ready_for_evaluate` handoff.

`evaluate` is the independent testing role. Its job is to attack the implementation against the brainstorm Context/Test Plan, developer self-test evidence, code/artifact diff, and likely adjacent behavior. It appends an Evaluator Round to the same review document and routes the result to `release` for an evaluator checkpoint before `converge`.

It does not implement fixes, approve plans, decide convergence, commit, push, tag, or release. It also does not decide whether a checkpoint can skip convergence; `release` records the evaluation checkpoint and routes onward.

The terminal state is a structured `evaluate.v1` output plus, when evaluation reaches an appendable state, an Evaluator Round in the existing review document. The next workflow skill is normally `release` with `release_context.release_mode=checkpoint_evaluate`, except for missing handoff evidence, blocked execution, or route correction.

`evaluate` is a mandatory user-visible checkpoint by default. The user must be able to see the independent validation result, findings, adversarial checks, unit tests, scenario tests, evaluator judgments, and residual risks before the workflow continues into convergence.

An `accepted` evaluation is not workflow completion. Do not present evaluation-only work as done, converged, released, or finished. The visible output must make convergence explicit as pending, either by stopping at the checkpoint or by continuing only under an eligible `develop_evaluate_converge` automation policy.

The only exception is an explicit `develop_evaluate_converge` automation policy requested by the user for the current workflow. Under that policy, `evaluate` may continue automatically only when evaluation evidence is appendable, no blocker requires a user decision, and the next route remains inside the develop/evaluate/converge loop.

## Checklist

You MUST complete these steps in order:

1. **Confirm source**: accept only a valid `develop.ready_for_evaluate` handoff or equivalent evaluator-ready packet. If missing, return `needs_develop_handoff`.
2. **Load workflow state**: read the shared review document and, when present, `.arbor/workflow/features.json` for the selected feature status.
3. **Load review context**: the review document named by the develop handoff must contain brainstorm Context/Test Plan and a Developer Round.
4. **Inspect implementation evidence**: review changed files/artifacts, developer self-tests, planned test coverage, uncovered planned tests, known risks, and replay targets.
5. **Plan adversarial evaluation**: map brainstorm acceptance criteria, required unit tests, required scenario tests, edge cases, negative cases, and evaluator focus to concrete checks.
6. **Run evaluation**: replay developer tests when useful, add independent unit/scenario/edge/negative checks, run coverage or static checks when the blast radius justifies it, include a negative control or mutation/static/contract probe for acceptance decisions, and record blocked checks.
7. **Find bugs, not confirmation**: prioritize behavioral regressions, missing tests, contract drift, scope creep, and untested edge cases.
8. **Append evaluator evidence**: append an Evaluator Round to the same review document. Do not overwrite brainstorm or developer rounds.
9. **Update in-flight memory**: before stopping or handing off with uncommitted Arbor workflow changes, ensure `.arbor/memory.md` exists and records the evaluated feature/artifact, changed evidence paths, evaluator result, unresolved findings or risks, and next expected step. Remove or shrink resolved entries only after the state is committed or moved to durable docs.
10. **Guard continuation semantics**: if evaluation reaches a completed evaluator state, make convergence explicit and do not use final-completion language.
11. **Return rendered checkpoint and runtime packet**: produce `evaluate.v1` for runtime handoff, and make the normal user-visible response the rendered `user_response` checkpoint, not raw JSON.

## Process Flow

```text
Confirm evaluator-ready handoff
-> Load feature registry status when available
-> Load shared review document
-> Read Developer Round and changed files
-> Map planned test scope
-> Replay or challenge developer tests
-> Add independent adversarial checks
-> Classify findings and residual risk
-> Append Evaluator Round
-> Route to release checkpoint or the correct blocker state
```

## Terminal States

- `accepted`: evaluation found no blocking issue; route to `release` for checkpointing before converge.
- `changes_requested`: evaluation found actionable implementation/test defects; route to `release` for checkpointing before converge.
- `needs_brainstorm`: evaluation found unclear requirements, invalid test plan, or scope/design mismatch; route to `release` for checkpointing before converge.
- `needs_develop_handoff`: the developer handoff, review document, Developer Round, changed files, or replay evidence is missing or invalid; route to `develop`.
- `blocked`: evaluation cannot run because required files, dependencies, permissions, or environment are unavailable; route to `none`.
- `route_correction`: request belongs to another skill or direct work.

Only completed evaluation states (`accepted`, `changes_requested`, `needs_brainstorm`) route to `release`. The release checkpoint then routes the same evaluation evidence to `converge`.

## Core Rules

1. Evaluate independently; do not trust developer claims without checking files, tests, and review evidence.
2. Do not modify implementation files or silently fix defects.
3. Temporary probes are allowed when they do not become product changes; clean them up or record them as blocked/residual risk.
4. Append only to the existing review document named by `source.review_doc_path`.
5. Treat brainstorm's test plan as the minimum required scope, not the maximum.
6. Add adversarial unit, scenario, edge, negative, mutation, or static probes when they materially improve confidence.
7. Non-blocking recommendations do not become acceptance unless the evidence supports it.
8. Do not decide final convergence; `converge` owns that decision.
9. Do not mark a feature `done` or update final feature status. `evaluate` emits a feature-registry signal for `converge`.
10. Do not accept by replay alone. Accepted evaluations require independent evaluator evidence across multiple useful dimensions.

## Anti-Patterns

### "Developer Tests Passed, So Evaluation Is Done"

No. Developer self-tests are evidence to replay or challenge. Evaluation must add independent scrutiny.

### "Evaluate Can Fix The Bug"

No. Record findings and route to `release` for checkpointing. Implementation fixes belong to `develop` after convergence selects the next action.

### "Evaluate Means Generic Assessment"

No. This skill is only for independent validation of implemented Arbor work. Generic advice, paper judgment, or proposal review belongs elsewhere.

### "Append Anywhere Convenient"

No. `review_append.path` must match `source.review_doc_path`. The Evaluator Round belongs in the same review document as brainstorm Context/Test Plan and Developer Round.

### "Review Evidence Replaces Session Memory"

No. Evaluator rounds are durable evidence, but uncommitted Arbor workflow state still needs a compact `.arbor/memory.md` in-flight entry until it is committed or moved to durable docs.

### "Converge Is Obvious, So Skip It"

No. `evaluate` recommends a terminal state and provides evidence. `converge` decides whether the developer/evaluator loop is accepted, needs another develop round, needs brainstorm, or is blocked.

### "Evaluation Accepted, So Mark Feature Done"

No. `.arbor/workflow/features.json` is the queue/status index, but `evaluate` should only report the recommended next status. `converge` owns final updates such as `done`, `changes_requested`, `blocked`, or returning to planning.

### "Accepted Means Complete"

No. `accepted` only means independent evaluation did not find a blocking issue. Convergence still must compare evaluator evidence against the brainstorm goal and update final workflow state.

## The Process

### Understand The Handoff

- Start from the develop structured output and raw user request.
- Confirm `develop_terminal_state=ready_for_evaluate` or an equivalent evaluator-ready signal.
- Read `source.feature_registry_path` when provided and confirm the selected feature is currently evaluable.
- Read `source.review_doc_path`; do not rely on copied snippets when the file is available.
- Check that the review document has both brainstorm Context/Test Plan and the current Developer Round.
- If the handoff is incomplete, stop with `needs_develop_handoff`.

### Build The Attack Plan

- Treat the brainstorm test plan as the minimum scope.
- Inspect changed files/artifacts before deciding what to test.
- Compare developer self-tests against required unit tests, required scenario tests, edge cases, negative cases, and evaluator focus.
- Look for nearby behavior that could regress even if the direct happy path works.
- Decide which developer checks to replay and which independent checks to add.

### Run Evaluation

- Use existing repo commands and conventions.
- Prefer targeted checks over broad expensive checks unless the blast radius justifies breadth.
- Add adversarial probes for contract-critical behavior, negative cases, boundary cases, schema drift, or route mistakes.
- For documentation or managed artifacts, use content, structure, and workflow scenario checks instead of pretending code tests are required.
- If a check cannot run, record the command, blocker, and residual risk.

### Strict Acceptance Gate

For `accepted`, developer replay is required but never sufficient. The evaluator must add at least two independent evaluator check categories that fit the artifact, such as unit/content checks, workflow scenario checks, edge/negative checks, mutation checks, static/schema/contract probes, compile/lint/type checks, or coverage checks.

When the planned scope includes unit-level behavior, an accepted evaluation needs an independent unit-level or content-level check. When the planned scope includes workflow behavior, it needs an independent scenario check. When edge or negative behavior is planned, it needs an edge/negative check or a mutation/static/contract probe that would fail under a broken version of the contract.

For workflow, skill, router, plugin, or prompt-routing changes, include at least one realistic workflow or user scenario replay. If a live `codex exec`, Claude Code, browser, connector, or external model replay is too costly or unavailable, use the strongest deterministic substitute and record the live gap in `Risks And Gaps`; do not claim live trigger behavior was verified unless it actually ran.

For workflow, process-control, routing, plugin, prompt-routing, or output-layer changes, accepted evaluation must be stronger than a normal documentation check: replay the developer evidence, inspect the relevant runtime output or strongest available substitute, add a checker or harness negative probe that would fail under a broken contract, and explicitly state whether any result is a weak pass because exact runtime telemetry was unavailable.

Every accepted evaluation should include a negative control, mutation probe, static contract probe, or equivalent adversarial check that is expected to catch a purposeful broken input. If no meaningful adversarial probe is possible, record why and treat that as residual risk before deciding whether acceptance is justified.

### Write Findings

- Findings come first in the evaluator round.
- Make each finding actionable: id, priority, location, evidence, recommendation, and whether it blocks acceptance.
- Distinguish implementation bugs from test gaps, scope drift, requirements gaps, blockers, and route issues.
- Do not bury failed commands or missing planned tests in prose-only notes.

### Prepare User-Readable Output

- Test-matrix rows must include a concrete representative example of the exact replay, not only a category label and counts.
- Write scenario summaries in workflow language a user can understand without reading code.
- Start each primary scenario row with a human workflow situation before internal evidence.
- Explain the real situation being tested, the risk it proves, and the result.
- Use internal field names, fixture ids, enum values, and mutation details only as supporting evidence.
- Do not make `Case 1`, `source.develop_terminal_state`, or other internal names the primary scenario explanation.
If a reader cannot understand what was tested from the table row and scenario row without opening the JSON fixture or harness code, the output is not acceptable.

Prefer test-matrix examples like "Copied a completed handoff and changed its source from develop to a manual packet." Avoid category-only labels such as "source-gate adversarial replay."

### User-Facing Evaluation Packet

`user_response` is the visible evaluation summary. It should reduce review cost by leading with the evaluation result and findings, then showing the evidence behind that result.

The structured `evaluate.v1` object is an internal workflow/runtime packet. In a normal user-facing final response, render the checkpoint from `user_response` and `ui`; do not print the raw `evaluate.v1` JSON unless the user explicitly asks for debug or machine output.

Use this shape by default:

```markdown
**Evaluation Verdict**
...

**Findings First**
...

**How I Challenged The Work**
...

**Plan Coverage**
...

**What I Checked**
...

**Unit Tests**
...

**Scenario Tests**
...

**Other Checks**
...

**Evaluator Judgments I Made**
...

**Risks And Gaps**
...

**Next Step**
...
```

Write each section in natural language. For `Findings First`, say clearly whether there are blocking findings. For `What I Checked`, include developer evidence replay and evaluator-added checks. For `How I Challenged The Work`, describe adversarial scenarios, edge cases, negative cases, mutation/static probes, or why they were blocked. For `Plan Coverage`, map the evaluation back to the planned acceptance and test scope in user-level language. For `Evaluator Judgments I Made`, expose judgment calls such as whether a missing check blocks acceptance, whether a failure belongs to implementation or planning, or why documentation was validated through content/scenario checks.

`Unit Tests` and `Scenario Tests` must be shown as Markdown tables, not bullets or loose prose. Use natural-language columns such as `Check`, `Behavior Covered`, `Expected`, `Actual`, and `Result`. Do not list only command names or test ids. Explain what each unit test or scenario test actually proved, what behavior it exercised, and whether it passed, failed, was blocked, or was not applicable. If no unit or scenario tests were appropriate, still include the table with a row explaining why the category was not applicable.

The normal visible final response MUST include these exact Markdown headings, in this
order, even when a section has only one sentence or a not-applicable table:

- `**Evaluation Verdict**`
- `**Findings First**`
- `**How I Challenged The Work**`
- `**Plan Coverage**`
- `**What I Checked**`
- `**Unit Tests**`
- `**Scenario Tests**`
- `**Other Checks**`
- `**Evaluator Judgments I Made**`
- `**Risks And Gaps**`
- `**Next Step**`

Before returning, self-check the captured visible response for the exact headings above
and for Markdown tables under `Unit Tests` and `Scenario Tests`. If any heading or table
is missing, rewrite the visible response before finishing. A shorter prose-only
evaluation is not an acceptable `evaluate` checkpoint.

Do not expose machine-oriented labels in visible text. Avoid schema field names, route assignments, terminal-state strings, fixture ids, synthetic feature ids, and shorthand such as `dev/eval`. Internal evidence may stay in structured fields; the visible text should explain the situation a user cares about.

### After Evaluation

- If there are no blocking findings and independent checks ran, return `accepted -> release`.
- If implementation behavior, developer evidence, or test coverage failed, return `changes_requested -> release`.
- If the plan itself is contradictory or underspecified, return `needs_brainstorm -> release`.
- If developer handoff evidence is missing, return `needs_develop_handoff -> develop`.
- If the environment prevents evaluation, return `blocked -> none`.
Return a `feature_registry_signal` recommending the next feature status for `converge`; do not edit final registry status inside `evaluate`.

## Evaluation Scope

Minimum scope comes from the shared review document and develop handoff:

- brainstorm acceptance criteria;
- required unit tests;
- required scenario tests;
- edge cases;
- negative cases;
- evaluator focus;
- developer changed files/artifacts;
- developer self-test commands and results;
- developer planned-test coverage and uncovered planned tests;
- known risks and replay targets.

Use repo conventions for actual commands. Good evaluation checks can include:

- replaying developer commands;
- adding or running targeted unit tests;
- scenario tests for user/workflow behavior;
- edge and negative cases from the brainstorm review plan;
- mutation/adversarial probes for contract-critical behavior;
- negative controls that prove the test would fail against a broken contract;
- realistic workflow or user-scenario replays for skill, router, plugin, prompt-routing, or UI-facing changes;
- lint/type/compile/schema checks when relevant;
- coverage checks when requested or when blast radius is broad.

## Review Append

Append an Evaluator Round to the same review document. Include:

- feature id/title and developer round reference;
- files/artifacts inspected;
- developer tests replayed and result;
- additional evaluator checks and result;
- planned test scope coverage;
- blocked or skipped checks and residual risk;
- findings with id, priority, location, evidence, recommendation, and whether they block acceptance;
- acceptance verdict;
- recommended next route for `release` checkpoint and downstream `converge`.

Do not rewrite prior rounds. Do not store evaluator evidence inside skill `references/`.

## Key Principles

- Attack the work, not the developer.
- Trust evidence over claims.
- Cover planned tests before optional polish.
- Keep findings structured and replayable.
- Preserve prior review history.
- Keep implementation fixes out of evaluate.

## Status Matrix

| Terminal state | Evaluation | Review append | Findings | Next |
| --- | --- | --- | --- | --- |
| `accepted` | `passed` | `appended` | no blocking findings | `release` |
| `changes_requested` | `failed` or `partial` | `appended` | one or more blocking/actionable findings | `release` |
| `needs_brainstorm` | `blocked` or `partial` | `appended` | requirement/test-plan/scope finding | `release` |
| `needs_develop_handoff` | `not_started` or `blocked` | `not_required` or `blocker_packet` | handoff blocker | `develop` |
| `blocked` | `blocked` | `blocker_packet` or `not_required` | environment/dependency blocker | `none` |
| `route_correction` | `not_started` | `not_required` | route issue | declared route or `none` |

## Structured Output Contract

Produce this structure for internal workflow handoff:

```json
{
  "schema_version": "evaluate.v1",
  "raw_user_request": "",
  "source": {
    "from_skill": "develop",
    "develop_terminal_state": "ready_for_evaluate",
    "feature_id": "",
    "feature_registry_path": ".arbor/workflow/features.json",
    "review_doc_path": "docs/review/<feature>-review.md",
    "developer_round_ref": "",
    "changed_files": [],
    "artifact_changes": [],
    "developer_replay_targets": []
  },
  "review_context": {
    "brainstorm_context_loaded": true,
    "developer_round_loaded": true,
    "acceptance_criteria": [],
    "planned_unit_tests": [],
    "planned_scenario_tests": [],
    "edge_cases": [],
    "negative_cases": [],
    "evaluator_focus": []
  },
  "evaluation": {
    "status": "passed",
    "strategy": "adversarial",
    "developer_replay": [],
    "additional_unit_tests": [],
    "additional_scenario_tests": [],
    "edge_negative_tests": [],
    "mutation_or_static_probes": [],
    "coverage": null,
    "planned_scope_coverage": [],
    "blocked_checks": [],
    "findings": []
  },
  "review_append": {
    "status": "appended",
    "path": "docs/review/<feature>-review.md",
    "round_type": "evaluator",
    "finding_count": 0,
    "blocking_finding_count": 0,
    "replay_targets": []
  },
  "feature_registry_signal": {
    "status": "not_updated",
    "path": ".arbor/workflow/features.json",
    "feature_id": "",
    "current_status": "in_evaluate",
    "recommended_next_status": "done",
    "reason": "converge owns final feature status update"
  },
  "route": {
    "terminal_state": "accepted",
    "next_skill": "release",
    "next_skill_context": {
      "release_mode": "checkpoint_evaluate",
      "next_after_release": "converge"
    },
    "reason": "Evaluator evidence is appended; release should checkpoint before converge."
  },
  "ui": {
    "summary": "",
    "review_focus": [],
    "warnings": [],
    "scenario_tests": [
      {
        "scenario": "",
        "simulated_situation": "",
        "what_this_proves": "",
        "actual_result": "",
        "evidence": []
      }
    ],
    "checkpoint": {
      "visibility": "user_visible",
      "continue_policy": "must_stop",
      "reason": "The independent evaluation result, findings, tests, and residual risks must be visible before convergence.",
      "resume_after": "user_acknowledgement"
    },
    "workflow_automation": {
      "policy": "develop_evaluate_converge",
      "enabled": false,
      "eligible": false,
      "stop_conditions": [
        "blocking finding that needs user decision",
        "plan or scope contradiction",
        "missing developer handoff",
        "blocked evaluation",
        "route correction"
      ]
    }
  },
  "user_response": ""
}
```

Use these enums:

- `source.from_skill`: `develop` or a stable equivalent handoff source label
- `source.develop_terminal_state`: `ready_for_evaluate` or another explicit upstream state
- `source.feature_registry_path`: `.arbor/workflow/features.json` or `null`
- `evaluation.status`: `not_started`, `passed`, `failed`, `partial`, `blocked`
- `review_append.status`: `not_started`, `appended`, `blocker_packet`, `not_required`
- `feature_registry_signal.status`: `not_updated`, `not_required`, `blocked`
- `feature_registry_signal.recommended_next_status`: `done`, `changes_requested`, `planned`, `blocked`, or `null`
- `feature_registry_signal.feature_id`: must match `source.feature_id` whenever evaluation emits a registry-backed signal
- `route.terminal_state`: `accepted`, `changes_requested`, `needs_brainstorm`, `needs_develop_handoff`, `blocked`, `route_correction`
- `route.next_skill`: `brainstorm`, `develop`, `evaluate`, `converge`, `release`, `none`
- `route.next_skill_context.release_mode`: `checkpoint_evaluate` when a completed evaluation state routes to `release`
- `route.next_skill_context.next_after_release`: `converge` when a completed evaluation state routes to `release`
- `ui.checkpoint.visibility`: `user_visible`
- `ui.checkpoint.continue_policy`: `must_stop` or `auto_continue_allowed`
- `ui.checkpoint.resume_after`: `user_acknowledgement`, `auto_policy`, `develop_handoff_ready`, or `blocker_resolved`
- `ui.workflow_automation.policy`: `develop_evaluate_converge` or `none`

For every terminal state, default to `ui.checkpoint.visibility=user_visible` and `ui.checkpoint.continue_policy=must_stop`. `evaluate` may record `release -> converge` as the next workflow path, but that route is normally a resume target after the visible evaluation checkpoint, not permission to continue silently in the same turn. Use `auto_continue_allowed` only when the user explicitly enabled `develop_evaluate_converge` automation and no stop condition applies.

For completed evaluation states, the visible `user_response` must say that convergence remains next. It must not imply the feature is done, released, or finally accepted.

When adding a terminal state, update the status matrix, output enums, simulation cases, baseline JSONL, and `scripts/check_evaluate_baselines.py` in the same change.

For completed evaluation states, accept either `source.from_skill=develop` with `source.develop_terminal_state=ready_for_evaluate`, or an explicitly modeled active review continuation from `intake` with `source.develop_terminal_state=active_review_continuation`, an appendable review document, changed files or artifact changes, and replayable review targets. Do not accept other evaluator-ready packet types unless they are explicitly modeled with positive and negative fixtures.

For completed evaluation states, `review_context.acceptance_criteria` must be loaded, and at least one planned test or evaluator-focus dimension must be present. `planned_scope_coverage` must map evaluation work back to that loaded scope.

For `accepted`, `developer_replay` must be non-empty, at least two independent evaluator check categories must be present, and at least one mutation/static/contract probe or negative-control equivalent must be recorded. The accepted state must not rely only on developer replay, broad lint, or prose inspection.

`planned_scope_coverage` entries must name the specific loaded planned item they cover using a stable mapping such as `acceptance:<criterion>`, `unit:<planned test>`, `scenario:<planned scenario>`, `edge:<edge case>`, `negative:<negative case>`, `focus:<evaluator focus>`, `replay:<target>`, or `developer_replay:<target>`. The text after the prefix must match the loaded review scope or replay target. Generic or unrelated entries such as `covered`, `acceptance:covered`, `unit:checked`, or `acceptance:unrelated payment behavior` are not auditable.

Evaluator evidence lists such as `developer_replay`, `additional_unit_tests`, `additional_scenario_tests`, `edge_negative_tests`, and `mutation_or_static_probes` must contain replayable commands, checks, scenarios, or inspection targets plus an observed result. Do not use vague entries such as `checked output`, `checked parser output`, `manually reviewed UI`, `looks good`, or `good enough`.

## Self-Check

Before returning:

1. Did I verify the input is an evaluator-ready develop handoff?
2. Did I load the same review document that contains brainstorm Context/Test Plan and Developer Round?
3. Did I read `.arbor/workflow/features.json` when the handoff included it?
4. Did I inspect changed files/artifacts instead of trusting developer prose?
5. Did I replay or explicitly decline developer tests with a reason?
6. Did I add independent adversarial unit/scenario/edge/negative checks where relevant?
7. Did I map evaluation checks to the planned test scope?
8. Did I append an Evaluator Round to `source.review_doc_path` without overwriting prior rounds?
9. If uncommitted Arbor workflow changes remain, did I create or refresh `.arbor/memory.md` with the in-flight state and next step?
10. Did I route only completed evaluation states to `release`, with `route.next_skill_context.release_mode=checkpoint_evaluate` and `next_after_release=converge`?
11. Did I include a user-visible checkpoint that prevents silent continuation into convergence?
12. Did I emit a feature-registry signal without marking the feature done?
13. Did I include user-readable scenario summaries that explain the real workflow situation, risk, result, and evidence without leading with internal field names or synthetic ids such as `F2`, `ABC-123`, or `feature-001`?
14. Did every test-matrix row include a concrete representative example a reader can understand without opening the harness?
15. For accepted evaluations, did I add at least two independent evaluator check categories plus a negative control, mutation probe, static contract probe, or equivalent adversarial check?
16. For workflow, skill, router, plugin, or prompt-routing changes, did I replay a realistic workflow/user scenario or record the live replay gap?
17. Did `planned_scope_coverage` and evaluator evidence name concrete planned scope and replayable checks instead of generic phrases?
18. Did `user_response` make clear that convergence remains pending instead of implying final completion?
19. Did `user_response` start with the evaluation result and findings, then explain checks, adversarial coverage, evaluator judgments, risks, and next step without leaking internal field names or codes?

If any check fails, revise the output or return the appropriate blocked/needs state.

## Reference Material

- `references/evaluate-boundary.md`: full boundary, handoff requirements, adversarial testing contract, review append, and terminal-state matrix.
- `references/evaluate-simulation-cases.md`: regression cases for evaluate routing and evidence.
- `scripts/check_evaluate_baselines.py`: deterministic replay/schema checks for evaluate simulation baselines.
