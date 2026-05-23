# Feedback Boundary

`feedback` exists so users can explicitly hand Arbor feedback without relying on
an implicit universal router. It is intentionally narrow: it accepts feedback,
decides the next owner, and stops.

## Invocation And Acceptance Boundary

Load feedback from an explicit `$feedback` or `/arbor:feedback` invocation, or
from a feedback-shaped prompt where the owner is unclear. Feedback-shaped means
the user is reacting to prior output, a bug, regression, failed check, reviewer
comment, missing behavior, or an unexpected result.

Accept and route as feedback only when that feedback shape is present. An
explicit `$feedback` invocation is allowed to produce `route_correction` or a
direct response when the actual request is project status, release, new feature
planning, or an ordinary explanation. Do not invent feedback context just
because the user named the skill.

Do not insert feedback between the user and another explicitly named public
skill when that skill fits. `brainstorm` owns new feature planning and unscoped
bug planning. `converge` owns known current-loop continuation, finish, repair,
verification, and post-convergence publish/push intent when review context is
clear. `arbor` owns startup, resume, and project-status context. `release` is an
internal gate, not a public feedback destination.

Do not trigger from a keyword alone. A status question mentioning feedback, a
new feature named "feedback", or a release request that includes reviewer
feedback is not automatically a feedback checkpoint.

## Route Owner Questions

Ask these questions in order:

1. Was `feedback` explicitly invoked, or is the input actually feedback about a
   result, bug, regression, failed check,
   reviewer comment, missing behavior, or prior assistant output?
2. If feedback was explicitly invoked, is the request actually feedback-shaped
   or should it be route-corrected/directly answered?
3. Did the user explicitly invoke another public skill that already fits the
   request?
4. Does the feedback change requirements, acceptance criteria, product scope, or
   test scope?
5. Is there existing Arbor review context for the affected feature?
6. Is the feedback an actionable implementation or test defect inside that
   existing review context?
7. Is the feature still an active or explicitly reopenable quality loop?
8. Can the feedback be answered directly without Arbor workflow state?

## Route Table

| Situation | Next Owner | Rationale |
| --- | --- | --- |
| New bug, no review context, missing reproduction plan, or broad debugging request. | `brainstorm` | Planning owns scope, acceptance criteria, reproduction evidence, and test plan creation. |
| Reviewer or user says the accepted criteria, non-goals, or test plan are wrong. | `brainstorm` | The feedback changes planning evidence, not implementation evidence. |
| Existing Arbor feature has a defect, failed check, regression, or evaluator finding within accepted scope. | `converge` | Converge owns the quality loop and internally drives repair and validation. |
| User asks to run develop or evaluate from a feedback-shaped prompt. | `converge` when review context exists; otherwise `brainstorm` or direct correction. | Develop and evaluate are internal stages, not public feedback destinations. |
| User explicitly names `brainstorm`, `converge`, or `arbor`, and that public skill fits. | that named skill or route correction | Feedback should not become a hidden pre-router in front of explicit public entrypoints. |
| User asks for finalization, push, publish, or cache sync from a feedback-shaped prompt. | `converge` when review context exists; otherwise route correction or needs evidence. | Release is internal; public release intent should be held until convergence/finalization evidence exists. |
| A finalized or released feature regresses after the loop closed. | `brainstorm` | The work normally needs a new scoped repair plan and proof target instead of silently reopening old evidence. |
| The feedback could refer to multiple features, a stale feature row, or a missing review document. | no workflow owner yet | Ask for feature identity or the missing review evidence before routing. |
| User corrects wording, asks for a direct answer, or points out a simple chat misunderstanding. | direct response | No workflow state, review document, or future development plan is needed. |
| Required log, traceback, review text, or active review document is missing. | no workflow owner yet | Ask for the missing evidence or name what must be loaded before routing. |

## Existing Review Context

Treat review context as existing only when the active feature can be tied to:

- `.arbor/workflow/features.json`;
- a selected feature row;
- a review document path;
- current Context/Test Plan evidence or prior developer/evaluator/convergence
  evidence.

If those links are missing, feedback about a bug should normally route to
`brainstorm`, not to `converge`.

Treat review context as ambiguous when more than one feature could be affected,
the active feature and referenced review document disagree, the review document
is missing, or the feature row is stale. Return an evidence request instead of
choosing a feature by recency.

Treat `done`, finalized, published, or released feature feedback as new planning
work unless the user explicitly asks to reopen the same review loop and the
review document still contains current, actionable scope.

## Planning Changes

Route to `brainstorm` when the feedback says any of these changed:

- what the feature should do;
- accepted behavior or non-goals;
- acceptance criteria;
- done-when criteria;
- test plan or proof strength;
- user approval scope;
- whether the work should exist as an Arbor-managed feature at all.

## Quality-Loop Feedback

Route to `converge` when all of these are true:

- the feedback is about an existing Arbor-managed feature;
- review context is present and identity is clear;
- the complaint is an implementation defect, failed check, regression, or
  evaluator finding inside accepted scope;
- the requested next action is repair, verification, or continuation of the same
  loop.

`converge` may then drive internal `develop`, release checkpoint, internal
`evaluate`, release checkpoint, and convergence decision. Feedback must not name
those internal stages as public next steps.

Do not route to `converge` when:

- the feature identity is ambiguous;
- the review document is missing or stale;
- the feature was already finalized and the feedback describes new work;
- the feedback changes criteria, proof strength, non-goals, or user approval
  scope;
- the user supplied only "it failed" without the relevant error, command, or
  reviewer text.

## Direct Feedback

Keep the response direct when the user is correcting the current conversation
rather than changing repo state. Examples include:

- "That did not answer my question; answer it directly."
- "Explain the tradeoff more clearly."
- "Use Chinese in the final answer."
- "You misunderstood which file I meant," when no managed workflow artifact was
  created and no downstream plan is needed.

When the direct answer is already known, include it in the same feedback
checkpoint. The checkpoint can say why no Arbor workflow is needed and then give
the corrected answer. When the direct answer requires missing facts, ask for
only those facts.

## Rendered Output Contract

Feedback output is an internal workflow checkpoint. Render the decision in
readable prose and a short table, and make the normal visible answer render the
checkpoint rather than an internal packet. Do not print the raw `feedback.v1` packet,
route fields, terminal-state labels, unexplained feature ids, or review document
paths as the normal visible answer.

The visible checkpoint should use the user's active chat language. English
prompts use `Feedback Decision`, `Why This Route`, `What I Need Or Will Use`,
and `Next Step`; non-English prompts use localized heading equivalents in the
same order. Final response preflight must inspect the exact final text and
reject a prose-only summary.
