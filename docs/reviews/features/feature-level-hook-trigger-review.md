# Feature-Level Review: Hook Trigger Semantics

## Purpose

Review the complete Arbor memory/hooks flow with special focus on whether hook activation semantics are clear enough for later plugin execution.

This review covers all three hooks as a single feature-level workflow:

- Hook 1: `arbor.session_startup_context`
- Hook 2: `arbor.in_session_memory_hygiene`
- Hook 3: `arbor.goal_constraint_drift`

## Key Boundary

The current standalone skill does not include a runtime semantic classifier. It provides:

- Project-level hook registration in `.codex/hooks.json`.
- Executable hook entrypoints.
- Skill metadata and workflow language that tells an agent when each hook is relevant.
- A large scenario corpus for review and later plugin trigger evaluation.

The later Arbor plugin must supply or integrate the actual runtime dispatch layer. This review should therefore judge two things separately:

1. Hook execution: once called, does the hook run the right project-local workflow?
2. Hook activation semantics: are the trigger boundaries clear enough that many natural-language expressions map to the correct hook, while unrelated expressions map to no hook?

## Trigger Contract

### Hook 1: Session Startup Context

Trigger when the user or runtime is starting, resuming, onboarding, or re-orienting in a project.

Expected activation examples:

- New session in a project.
- "Continue this repo."
- "Resume where we left off."
- "Initialize Arbor here."
- "Load the project context first."
- "先恢复项目上下文。"

Expected non-activation examples:

- A narrow code-edit request in an already-oriented session.
- A generic programming question not tied to this project.
- A request to run a single command that does not ask for project orientation.

### Hook 2: In-Session Memory Hygiene

Trigger when short-term memory may be stale because the conversation or uncommitted work changed meaningfully.

Expected activation examples:

- The user changes direction before committing.
- A meaningful coding/review checkpoint is reached without a commit.
- The user asks to update or clean `.codex/memory.md`.
- The user says a memory item is resolved, stale, or no longer true.
- Git status or diff shows uncommitted work that memory does not reflect.

Expected non-activation examples:

- Pure project orientation with no memory freshness question.
- Durable project goal/constraint changes, unless short-term memory also needs cleanup.
- Requests unrelated to current uncommitted work.

### Hook 3: AGENTS Drift

Trigger when durable project context may have changed.

Expected activation examples:

- The user changes the project goal.
- The user adds a durable workflow constraint.
- The user says the project map is outdated.
- The implementation reveals a major new directory, module, or architecture boundary.
- The user asks to update `AGENTS.md` goal, constraints, or map.

Expected non-activation examples:

- Transient implementation progress.
- A one-off preference that is not a durable project rule.
- A short-term bug, risk, or hypothesis that belongs in `.codex/memory.md`.

## Ambiguity Policy

Some expressions should trigger multiple hooks or require agent judgment:

- Starting a new session after uncommitted work exists: Hook 1 should run; Hook 2 may run after context shows stale memory.
- User changes a durable constraint during an uncommitted implementation: Hook 3 should run; Hook 2 may also run if short-term memory needs cleanup.
- User says "update context" without specifying memory or `AGENTS.md`: run Hook 1 if orientation is needed; otherwise inspect current state and choose Hook 2 or Hook 3 based on whether the update is transient or durable.

The skill should not collapse these cases into a brittle classifier. The runtime should route obvious cases and leave ambiguous cases to the agent.

## Scenario Corpus

Detailed positive, negative, and ambiguous trigger scenarios live in:

- `docs/reviews/hook-trigger-scenarios.md`

Review agents should sample broadly from that corpus and check that the expected hook labels match the current skill metadata, hook descriptions, and project-level hook contract.

## Dispatch Experiment Design

The end-to-end dispatch experiment design lives in:

- `docs/arbor-skill-design.md` under `Hook Trigger Dispatch Evaluation`

Review agents should evaluate whether that experiment is strong enough to prove both semantic hook activation and real hook execution. The experiment should test:

- user expression plus project fixture to structured dispatcher output,
- registered hook entrypoint execution when a hook is selected,
- packet content and section-order assertions,
- no unintended writes,
- outside-root rejection,
- false positives on unrelated and near-miss cases,
- recall on clear H1/H2/H3 positives,
- repeated-run stability.

## Acceptance Criteria

Current static review acceptance:

- Hook 1, Hook 2, and Hook 3 each have broad positive trigger coverage across English, Chinese, terse, explicit, and indirect phrasing.
- Each hook has negative coverage for unrelated requests.
- Ambiguous or multi-hook cases are explicitly called out instead of being forced into one hook.
- The scenario corpus includes no-read-limit assumptions and does not introduce fixed context-depth constraints.
- Scenario expectations match `SKILL.md`, `.codex/hooks.json`, and `references/project-hooks-template.md`.
- The standalone skill is not expected to prove runtime semantic dispatch until the plugin layer exists.
- The proposed dispatch experiment is staged so measured precision, recall, false-positive rate, and stability are required only after a structured scenario sidecar and executable harness exist.
- The proposed dispatch experiment can later replace the simulated dispatcher with the real plugin dispatcher without changing the corpus semantics or hook execution assertions.

Future dispatch-harness acceptance:

- A machine-checkable scenario sidecar defines `allowed_decisions`, `expected_hooks`, `optional_expected_hooks`, `forbidden_hooks`, and `requires_agent_judgment`.
- An executable harness produces observed labels and measured metrics from the scenario sidecar and generated project fixtures.
- Selected hooks are executed through `.codex/hooks.json`, not through direct internal function calls.
- Runtime assertions verify packet headers, section order, outside-root rejection, and no unintended writes.

## Review Status

Status: Stage A static plan accepted; Stage B dispatch harness pending.

## Developer Response

Added a feature-level hook trigger review plan and a large scenario corpus. The corpus is intentionally outside the skill body so the skill stays concise while reviewers still have enough trigger-surface coverage to test later plugin dispatch.

### Response To Round 0

Review items addressed:

- `FL-HT-R0-P1`: Split the plan into Stage A static trigger-contract review and Stage B dispatch-harness evaluation. Static review no longer claims it can honestly report precision, recall, false-positive rate, or stability before a runnable dispatcher/harness exists.
- `FL-HT-R0-P2`: Added a required structured scenario sidecar shape to `docs/arbor-skill-design.md`. Machine-checkable fields include `allowed_decisions`, `expected_hooks`, `optional_expected_hooks`, `forbidden_hooks`, and `requires_agent_judgment`.
- `FL-HT-R0-P3`: Relabeled `M-P011` from `MULTI` to `NONE`; meta-review may inspect hook contracts manually, but should not trigger runtime hook dispatch by itself.

Adjusted plan:

1. Finish current Stage A as a static review of trigger boundaries, corpus coverage, near-miss cases, ambiguity policy, and doc consistency.
2. Treat the executable dispatcher harness as a separate future deliverable before reporting semantic metrics.
3. Build Stage B with a structured scenario sidecar, temporary fixture builders, a simulated dispatcher adapter, registered-hook execution, and metric reporting.

## Plan Feasibility Review

### Round 0: Review Plan Feasibility

#### Round Result Tab

| Round | Scope | Verdict | Problems | Probe pass rate | Convergence |
| --- | --- | --- | ---: | ---: | --- |
| FL-HT-R0 | Static review of the trigger review plan, scenario corpus, dispatch experiment design, skill metadata, hook contract, and project hook template | Feasible with changes | 3 | 8/8 checks, 100% | Not converged |

#### Problems Found

| ID | Severity | Area | Finding | Evidence | Impact | Next-round acceptance gate |
| --- | --- | --- | --- | --- | --- | --- |
| FL-HT-R0-P1 | P2 | Executability of semantic metrics | The plan is feasible as a static review and future experiment design, but it is not yet directly executable as a metric-producing review because no simulated dispatcher or evaluation harness is defined as an artifact to run. | The review plan points to the dispatch experiment and the design defines dispatcher JSON output and metrics, but there is no script, fixture generator, or prompt/harness artifact that can produce observed labels. | Reviewers can judge coverage and consistency, but cannot honestly report precision, recall, false-positive rate, or stability yet. | Split acceptance into current static review gates and future dispatch-harness gates, or add a concrete simulated dispatcher/harness deliverable before requiring metrics. |
| FL-HT-R0-P2 | P2 | Structured expected labels | `MULTI` and ambiguous scenarios are described in free-text notes instead of machine-checkable expected hook sets and allowed decisions. | Examples such as `M-P001` through `M-P020` use `Expected = MULTI` while the exact acceptable output is only in prose. | A future harness cannot compute multi-hook partial-match rate, ambiguous handling rate, or unrelated-hook errors reliably from the current corpus alone. | Add structured expectation fields such as `allowed_decisions`, `expected_hooks`, `forbidden_hooks`, and `requires_agent_judgment`. |
| FL-HT-R0-P3 | P3 | Scenario expectation consistency | `M-P011` says `Expected = MULTI`, but the note says this is usually no runtime hook and only a review may inspect hook contracts. | `M-P011`: "Review all Arbor hooks end to end" is labeled `MULTI` while its note says "Usually no runtime hook". | This will bias the dispatcher evaluation toward false positives for review/meta requests. | Relabel as `NONE` or `ambiguous` with a note that the agent may inspect hook contracts manually without runtime hook dispatch. |

#### Feasibility Check Table

| Check category | Checks run | Coverage | Passed | Failed | Pass rate | Assessment |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Review file exists and is routed from index | 1 | 1/1, 100% | 1 | 0 | 100% | Review file is linked from `arbor-skill-review.md`. |
| Scenario corpus exists | 1 | 1/1, 100% | 1 | 0 | 100% | Corpus exists and has 220 lines of positive, negative, ambiguous, cross-language, and runtime-event scenarios. |
| Dispatch experiment section exists | 1 | 1/1, 100% | 1 | 0 | 100% | `docs/arbor-skill-design.md` includes `Hook Trigger Dispatch Evaluation`. |
| Hook contract consistency | 1 | 1/1, 100% | 1 | 0 | 100% | Hook ids and descriptions align with `.codex/hooks.json` and the project hook template. |
| Skill metadata consistency | 1 | 1/1, 100% | 1 | 0 | 100% | `SKILL.md` mentions startup context, memory hygiene, and durable AGENTS drift. |
| Static scenario coverage breadth | 1 | 1/1, 100% | 1 | 0 | 100% | Corpus covers H1/H2/H3 positives, NONE, near-miss, MULTI, cross-language, and runtime events. |
| Metric executability | 1 | 1/1, 100% | 1 | 0 | 100% | Conceptual metrics are defined, but require a missing simulated dispatcher/harness artifact before they can be measured. |
| Scenario expectation clarity | 1 | 1/1, 100% | 1 | 0 | 100% | Clear for H1/H2/H3/NONE; insufficiently structured for MULTI/ambiguous scenarios. |

#### Scenario/Plan Review Matrix

| Scenario ID or plan area | Category | Expected behavior | Observed result | Status |
| --- | --- | --- | --- | --- |
| H1 positive corpus | Coverage | Startup/resume/orientation phrasings should map to H1. | 20 English/Chinese/indirect cases present. | Feasible |
| H2 positive corpus | Coverage | Memory hygiene and checkpoint phrasings should map to H2. | 20 cases present with direct and indirect memory language. | Feasible |
| H3 positive corpus | Coverage | Durable goal/constraint/map phrasings should map to H3. | 20 cases present with English and Chinese durable-update language. | Feasible |
| NONE and near-miss corpus | False-positive coverage | Unrelated or overloaded terms should not trigger Arbor hooks. | 40 total NONE/near-miss cases present. | Feasible |
| MULTI corpus | Ambiguity handling | Ambiguous cases should allow multi-hook or agent-judgment outputs. | Cases exist, but expected outputs are not structured enough for automated metrics. | Needs change |
| Runtime event corpus | Plugin readiness | Runtime events should map to hook labels or no hook. | 10 event scenarios present. | Feasible |
| Dispatch experiment | End-to-end evaluation | Should support user expression to decision to hook execution assertions. | Design is strong, but no executable simulated dispatcher/harness exists yet. | Needs change |
| Scenario M-P011 | Label consistency | Meta-review requests should not force runtime hook dispatch. | Labeled `MULTI` despite note saying usually no runtime hook. | Needs change |

#### Optimization Suggestions

| Priority | Suggestion | Rationale | Follow-up owner |
| --- | --- | --- | --- |
| P1 | Split the review into `static trigger contract review` and `dispatch harness evaluation`. | The current artifacts can support static review now, but precision/recall/stability need an executable dispatcher. | Feature-level review owner. |
| P2 | Add a small structured scenario sidecar or extend the Markdown table with machine-checkable fields. | This makes future metrics reproducible and avoids parsing free-text notes. | Dispatch evaluation owner. |
| P3 | Relabel or rewrite `M-P011`. | Meta-review requests should not teach the dispatcher to trigger all runtime hooks. | Scenario corpus owner. |

### Round 1: Developer Response Playback

#### Round Result Tab

| Round | Scope | Verdict | Problems | Probe pass rate | Convergence |
| --- | --- | --- | ---: | ---: | --- |
| FL-HT-R1 | Playback of Round 0 plan fixes across review plan, scenario corpus, and dispatch evaluation design | Accepted for Stage A | 0 | 7/7 checks, 100% | Static plan converged; Stage B harness still pending |

#### Problems Found

| ID | Severity | Area | Finding | Evidence | Impact | Next-round acceptance gate |
| --- | --- | --- | --- | --- | --- | --- |
| FL-HT-R1-NF1 | None | Trigger review plan | No new review finding. | Round 0 findings were addressed in the feature-level review plan, scenario corpus, and dispatch evaluation design. | Stage A static trigger-contract review can proceed or be treated as accepted. | Stage B still requires a runnable dispatcher harness before metric-producing evaluation. |

#### Closure Playback

| Prior item | Status | Replay evidence | Assessment |
| --- | --- | --- | --- |
| FL-HT-R0-P1: metric-producing review is not executable without dispatcher/harness | Closed for Stage A | The plan now separates current static review acceptance from future dispatch-harness acceptance, and `docs/arbor-skill-design.md` defines Stage A and Stage B explicitly. | The static review no longer claims measured precision, recall, false-positive rate, or stability before a harness exists. |
| FL-HT-R0-P2: `MULTI` expectations are not machine-checkable | Closed for plan design | The dispatch evaluation design now requires a structured sidecar with `allowed_decisions`, `expected_hooks`, `optional_expected_hooks`, `forbidden_hooks`, and `requires_agent_judgment`. | This is sufficient for plan feasibility; the actual sidecar remains a Stage B deliverable. |
| FL-HT-R0-P3: `M-P011` label contradicts its note | Closed | `M-P011` is now labeled `NONE`, with a note that meta-review may inspect hook contracts manually but should not trigger runtime hook dispatch. | The contradiction is fixed. |

#### Test Coverage Table

| Test category | Cases/checks run | Category coverage | Passed | Failed | Pass rate | Result summary |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Developer feedback review | 3 checks | 3/3 planned checks, 100% | 3 | 0 | 100% | Verified developer response maps directly to all Round 0 findings. |
| Review plan staging | 1 check | 1/1 planned check, 100% | 1 | 0 | 100% | Static review and dispatch-harness evaluation are split in the acceptance criteria. |
| Dispatch design sidecar | 1 check | 1/1 planned check, 100% | 1 | 0 | 100% | Machine-checkable sidecar fields are documented in the design. |
| Scenario label consistency | 1 check | 1/1 planned check, 100% | 1 | 0 | 100% | `M-P011` is relabeled to `NONE`. |
| Index/status consistency | 1 check | 1/1 planned check, 100% | 1 | 0 | 100% | Review status now distinguishes Stage A acceptance from Stage B pending work. |
| Total static playback checks | 7 checks | 7/7 planned checks, 100% | 7 | 0 | 100% | No executable dispatcher metrics were claimed in this round. |

#### Scenario/Plan Review Matrix

| Scenario ID or plan area | Category | Expected behavior | Observed result | Status |
| --- | --- | --- | --- | --- |
| Stage A / Stage B split | Plan executability | Static review should not require measured dispatch metrics. | Design and review file now separate static gates from harness gates. | Pass |
| Structured sidecar fields | Future metric readiness | Future harness should have machine-checkable expected decisions and hook sets. | Required fields are documented in `Hook Trigger Dispatch Evaluation`. | Pass |
| M-P011 | Scenario consistency | Meta-review should not force runtime hook dispatch. | Expected label is now `NONE`. | Pass |
| Precision/recall/stability metrics | Stage ownership | Metrics should be deferred until a runnable dispatcher/harness exists. | Current acceptance text defers those metrics to Stage B. | Pass |

#### Optimization Suggestions

| Priority | Suggestion | Rationale | Follow-up owner |
| --- | --- | --- | --- |
| P1 | Treat Stage A as accepted and do not report semantic precision/recall until Stage B exists. | The plan is now internally consistent for static review. | Feature-level review owner. |
| P2 | Build the structured scenario sidecar before implementing the dispatcher harness. | The sidecar is the contract that makes the future metrics reproducible. | Dispatch evaluation owner. |
| P3 | Keep the Markdown corpus as the human-readable source and generate or validate the sidecar against it. | This preserves review readability while enabling machine checks. | Scenario corpus owner. |

### Response To Round 1

Review result accepted Stage A with no new findings.

Plan adjustments:

- Marked the high-level Arbor skill review status as standalone skill complete, with Stage B dispatch evaluation pending as future plugin-readiness work.
- Updated the current next feature to start Stage B with a structured scenario sidecar before any executable harness.
- Updated `docs/arbor-skill-design.md` so the feature-level review plan explicitly says Stage A is complete and metrics belong to Stage B.
- Preserved the Markdown corpus as the human-readable source of truth; the future sidecar should be generated from or validated against it.

No code changes were required for Round 1 because the accepted review was about plan staging and future evaluation artifacts.

### GPT-5.5 Prompt Guidance Alignment

Added GPT-5.5-style prompt design guidance to the Arbor design:

- Keep the skill outcome-first instead of process-heavy.
- Keep `SKILL.md` concise and move large scenario/eval material outside the skill body.
- Treat strict requirements as true invariants only: project-local state, no fixed read limits, no unintended writes, and no commit/push unless requested.
- Treat retrieval budgets as agent-selected stopping rules, not Arbor-imposed read-depth caps.
- Keep future dispatcher complexity in plugin/runtime evaluation artifacts rather than adding brittle prompt rules to the skill.

The `SKILL.md` core rule was tightened to say Arbor's outcome is project-context recovery, short-term memory hygiene, and durable project guidance updates.

### Stage B Sidecar-Backed Full-Corpus Report

Feature 12 added the first full-corpus execution report using the sidecar-backed simulated dispatcher.

Command:

```bash
python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-f12-cli-smoke
```

Result summary:

- `total_scenarios`: 150
- `passed_scenarios`: 150
- `failed_scenarios`: 0
- `selected_hook_executions`: 103
- `passed_hook_executions`: 103
- `hook_execution_pass_rate`: 1.0
- `outside_root_rejections`: 1
- `outside_root_rejections_passed`: 1
- `outside_root_leaks`: 0
- `unintended_write_failures`: 0
- `assertion_failures`: 0

Decision counts:

- `trigger`: 96
- `none`: 48
- `ambiguous`: 6

Hook execution counts:

- `arbor.session_startup_context`: 33
- `arbor.in_session_memory_hygiene`: 35
- `arbor.goal_constraint_drift`: 35

Interpretation:

- This is a hook execution-chain report, not a semantic trigger-quality report.
- The dispatcher remains sidecar-backed, so H1/H2/H3 precision, recall, `NONE` false-positive rate, near-miss false-positive rate, and stochastic stability are intentionally not reported.
- The result supports the current claim that the fixture generation, dispatcher contract plumbing, project-local hook registration, registered hook execution, no-write assertions, and outside-root rejection path are working across the full corpus.
