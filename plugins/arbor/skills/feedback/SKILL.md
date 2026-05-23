---
name: feedback
description: Use when the user explicitly invokes feedback or gives Arbor feedback such as bug reports, regressions, failed checks, reviewer comments, corrections to prior output, or defects in a current managed feature and the next public owner is unclear; do not use for new feature planning, project status, release/finalization requests, or ordinary explanations; route only to brainstorm, converge, needs-evidence, or a direct response, never public develop/evaluate/release.
---

# Feedback

## Purpose

Use `feedback` as the public entrypoint when the user gives feedback about an
Arbor result, prior assistant output, bug, regression, failed check, reviewer
comment, or missing behavior and the next public owner is not already obvious.

`feedback` is a triage checkpoint, not a repair loop. It does not implement,
plan a feature, evaluate a handoff, decide convergence, release, commit, push,
or publish. Its only normal decision is whether the feedback should go to
`brainstorm`, `converge`, or a direct response with no Arbor workflow state.
`develop` and `evaluate` remain internal stages owned by `converge`, not public
next steps from feedback.

The normal terminal output is a structured `feedback.v1` decision plus a
rendered user-facing feedback checkpoint. The rendered response must explain the
target of the feedback, why the selected owner is appropriate, what evidence is
needed or already available, and the next step in readable language.

`feedback` is a user-visible routing checkpoint. Do not silently continue into
`brainstorm` or `converge` in the same final response. Use
`"continue_policy": "must_stop"` in the checkpoint UI so the user can inspect
or correct the routing decision before downstream workflow work starts.

## Invocation And Acceptance Contract

Load `feedback` when any of these are true:

- the user explicitly invokes `$feedback` or `/arbor:feedback`;
- the user gives feedback about a prior Arbor result, current assistant answer,
  bug, regression, failed check, reviewer comment, missing behavior, or
  unexpected output, and asks what should happen next;
- the user reports that a bug, failed check, or evaluator finding still applies
  but it is unclear whether the owner should be planning or the quality loop;
- the user asks for public `develop` or `evaluate` from a feedback-shaped
  prompt and the request needs correction to the public entrypoint model.

Accept and route as feedback only when the input is actually feedback-shaped:
the user is reacting to prior output, a bug, regression, failed check, reviewer
comment, missing behavior, or unexpected output. An explicit `$feedback`
invocation loads this skill, but it does not force a non-feedback request to be
treated as feedback. If an explicit feedback invocation asks for project status,
release, new feature planning, or an ordinary explanation, return
`route_correction` or `direct_response` rather than inventing feedback context.

Do not trigger `feedback` when the user clearly invokes another public Arbor
skill and the request matches that skill. In particular, keep new feature ideas,
scope design, and unscoped bug planning in `brainstorm`; keep current-loop
continuation, finish, publish, push, and cache-sync intent with known review
context in `converge`; keep project overview or resume questions in `arbor`;
answer ordinary explanations directly. `release` is internal, not a public
feedback route.

Do not trigger from keywords alone. Words like "bug", "feedback", "reviewer",
or "failed" are signals, not proof that this skill owns the turn. The skill
owns the turn only when the input is feedback-shaped or explicitly invokes
`feedback`.

## Canonical Examples

Use these examples as the feedback-boundary calibration before applying the
checklist. They are canonical examples, not extra routing rules. If a request is
close but not identical, follow the same evidence-owner reasoning.

| User request shape | Use `feedback`? | Expected handling |
| --- | --- | --- |
| "Bug: the new command still crashes, but we have not created review context for it yet." | Yes. | Route to `brainstorm` so the bug gets scope, acceptance criteria, reproduction notes, and a test plan before repair. |
| "This bug still happens in the current Arbor feature; fix it and verify it." | Yes, when review context exists. | Route to `converge`, which owns the internal repair and validation loop for the existing feature. |
| "The evaluator found this failing scenario; keep going." | Yes. | Route to `converge` when the finding is within the accepted plan; route to `brainstorm` if the finding changes requirements or acceptance criteria. |
| "The reviewer says the acceptance criteria are wrong." | Yes. | Route to `brainstorm` because the feedback changes planning evidence, not implementation evidence. |
| "Your last answer did not answer my question; answer it directly." | Yes. | Respond directly if no workflow artifact, feature state, test plan, or future development decision is affected. |
| "Run develop" or "Run evaluate" from a user prompt. | Use `feedback` only if the prompt is feedback-shaped. | Route to `converge` when an existing quality loop is present; otherwise route to `brainstorm` or direct correction. Never route to public `develop` or `evaluate`. |
| "Use brainstorm to plan this new feedback workflow." | No. | Respect the named public planning entrypoint; do not insert feedback just because the word "feedback" appears. |
| "Use converge to keep fixing the current feature." | No. | Respect the named quality-loop entrypoint when current review context is already clear. |
| "The released feature regressed after finalization." | Yes. | Route to `brainstorm` unless the user explicitly wants to reopen the same active review loop and the review context is still current. A finalized feature usually needs a new scoped fix plan. |
| "This feedback could refer to two current features." | Yes. | Return `needs_evidence` and ask for the feature or review document identity; do not guess a quality loop. |
| "What is the project status?" | No. | Answer directly or use `arbor` startup context; do not emit a feedback checkpoint. |

## Checklist

1. **Confirm invocation and acceptance**: load on explicit `feedback` invocation
   or feedback-shaped input, but accept only feedback-shaped work as feedback. If
   another public skill is explicitly invoked and fits, return a route correction
   instead of re-routing through feedback.
2. **Match canonical example**: identify the closest example above. If none
   fits, classify only enough context to decide whether this is feedback,
   direct work, or another explicit workflow skill.
3. **Confirm feedback shape**: accept bug reports, regressions, failed checks,
   reviewer comments, user corrections, missing behavior, or complaints about
   prior output. Return a direct route correction for ordinary status questions,
   new feature requests, release requests, or one-off explanations.
4. **Identify the target**: decide whether the feedback targets current chat
   prose, a new or unscoped bug, existing Arbor review context, acceptance
   criteria, test scope, release behavior, or something outside Arbor.
5. **Load minimal workflow state when needed**: when the feedback claims an
   existing Arbor feature or current quality loop, read `.arbor/workflow/features.json`
   and the selected review document before routing to `converge`. Do not scan
   the whole codebase just to decide the entrypoint.
6. **Check identity and state**: route to `converge` only when one affected
   feature is clear, the review document exists, the Context/Test Plan is
   current, and the feature is still an active or reopenable quality loop. If
   multiple features could match, the review document is missing, or the feature
   is already finalized and needs new work, do not guess the loop.
7. **Check evidence sufficiency**: if the feedback mentions a missing log,
   traceback, reproduction, reviewer comment, review document, or feature
   identity that changes the route, return `needs_evidence` and name the missing
   evidence.
8. **Choose the next owner**: route planning changes, new/unscoped bugs, changed
   acceptance criteria, and changed test plans to `brainstorm`; route bugs,
   defects, failed checks, evaluator findings, and repair requests tied to
   existing review context to `converge`; keep prose-only or simple response
   corrections direct.
9. **Answer direct feedback when possible**: for `direct_response`, include the
   direct answer in the visible response when the answer is already known and no
   workflow evidence is needed. If the direct answer needs missing facts, ask
   for those facts instead of creating Arbor workflow state.
10. **Reject public internal-stage routes**: never route user feedback to public
   `develop`, public `evaluate`, or public `release`. `converge` owns internal
   repair and validation after review context exists.
11. **Decide persistence**: feedback itself normally does not create or update
   `.arbor/workflow/features.json` or review documents. `brainstorm` creates or
   updates planning artifacts; `converge` appends quality-loop evidence.
12. **Update in-flight memory when needed**: if uncommitted Arbor workflow
   changes remain because this feedback decision created local evidence or
   state, ensure `.arbor/memory.md` records the active feature, changed paths,
   current checkpoint, risks, and next expected step before stopping.
13. **Return rendered checkpoint and runtime packet**: produce `feedback.v1` for
    runtime handoff, and make the normal visible response the rendered
    `user_response` checkpoint, not raw JSON.

## Process Flow

```text
Confirm invocation
-> Confirm feedback shape
-> Match canonical example
-> Identify feedback target
-> Load minimal workflow state only if an existing feature or loop is claimed
-> Check identity, feature state, and missing evidence
-> Choose brainstorm, converge, needs-evidence, direct response, or route correction
-> Render the feedback checkpoint
-> Stop before downstream work
```

## Terminal States

- `needs_brainstorm`: feedback changes planning, scope, acceptance criteria, or
  test scope, or a bug lacks review context.
- `needs_converge`: feedback is an actionable defect, failed check, evaluator
  finding, or repair request tied to existing Arbor review context.
- `needs_evidence`: required feedback evidence is missing or inaccessible.
- `direct_response`: feedback can be answered without Arbor workflow state.
- `route_correction`: the request is not feedback-shaped.
- `blocked`: required files, permissions, or environment prevent a routing
  decision.

## Core Rules

1. The next owner is limited to `brainstorm`, `converge`, or direct response.
2. Do not expose `develop` or `evaluate` as public next steps. Do not expose
   `develop`, `evaluate`, or `release` as public next steps.
3. Do not recreate a universal router. `feedback` handles feedback-shaped input
   only.
4. Do not intercept another explicitly named public skill when that skill fits
   the request.
5. Do not implement fixes, edit files, run tests, or append review rounds inside
   `feedback`.
6. Do not route a new or unscoped bug to `converge` just because it sounds
   urgent. Existing review context is required for direct quality-loop repair.
7. Do not route a planning change to `converge` just because it was discovered
   during evaluation. Planning changes go to `brainstorm`.
8. Do not create workflow artifacts in feedback. Route to the owner that creates
   or appends the correct artifacts.
9. Do not reopen a finalized feature by implication. Post-finalization
   regressions normally route to `brainstorm` for a new scoped repair plan unless
   the user and evidence clearly identify a current reopenable loop.
10. Do not guess when feedback identity is ambiguous. Ask for the feature,
   review document, traceback, command, or reviewer text needed to route safely.
11. Use the user's active chat language for the visible checkpoint. For English
   prompts, use the exact headings below; for non-English prompts, render
   localized heading equivalents in the same order.

## User-Facing Feedback Packet

`user_response` is the visible feedback decision. It should be short and
route-oriented. Do not print the raw internal workflow packet, internal route
assignments, terminal-state labels, unexplained feature ids, review document
paths, or field names unless the user explicitly asks for debug output.

Use this shape by default:

```markdown
**Feedback Decision**
...

**Why This Route**
| Signal | What It Means |
| --- | --- |
| ... | ... |

**What I Need Or Will Use**
...

**Next Step**
...
```

The normal visible final response MUST include these exact Markdown headings for
English prompts, in this order. When the user's active chat language is not
English, render localized heading equivalents in the same order with the same
section meaning. `Why This Route` must contain a Markdown table with natural
language cells.

- `**Feedback Decision**`
- `**Why This Route**`
- `**What I Need Or Will Use**`
- `**Next Step**`

For `direct_response`, the `Next Step` section may include the direct answer
itself when the answer is known. Do not force the user to ask again for a simple
conversation correction.

Final response preflight: before returning, inspect the captured final text that
will be sent to the user. It must contain the required headings in order, include
the required table, avoid raw `feedback.v1` or route fields, and avoid a
prose-only summary. If any required visible section is missing, rewrite the
visible response before finishing.

## Structured Output Contract

Produce this structure for internal workflow handoff:

```json
{
  "schema_version": "feedback.v1",
  "raw_user_feedback": "",
  "feedback_context": {
    "feedback_kind": "implementation_defect",
    "target_type": "existing_feature",
    "existing_review_context": true,
    "scope_or_plan_changes": false,
    "actionable_quality_loop": true,
    "missing_evidence": []
  },
  "review_context": {
    "feature_registry_loaded": true,
    "review_doc_loaded": true,
    "identity_confidence": "clear",
    "feature_status": "in_evaluate",
    "feature_id": "",
    "review_doc_path": ""
  },
  "direct_response": {
    "available": false,
    "answer_included": false
  },
  "route": {
    "terminal_state": "needs_converge",
    "next_skill": "converge",
    "reason": ""
  },
  "user_response": "",
  "ui": {
    "checkpoint": {
      "visibility": "user_visible",
      "continue_policy": "must_stop",
      "reason": "",
      "resume_after": ""
    }
  }
}
```

For detailed boundary rationale, read `references/feedback-boundary.md`.

## Anti-Patterns

### "Feedback Can Fix It Directly"

No. A clear defect with existing review context goes to `converge`; a new or
changed plan goes to `brainstorm`; prose-only corrections can be answered
directly.

### "Feedback Is The New Universal Router"

No. It handles feedback-shaped input only. New feature ideas, status questions,
release requests, and ordinary explanations have their own entrypoints or stay
direct.

### "A Bug Always Goes To Converge"

No. A bug without review context needs `brainstorm` first so repair has a plan,
acceptance criteria, and test scope.

### "Evaluator Findings Always Stay In Converge"

No. Implementation/test findings stay in `converge`; acceptance-criteria or
scope contradictions go to `brainstorm`.
