# Loop Health Advisory

## Purpose

The loop-health advisory helps `evaluate` and `converge` notice when an Arbor
develop/evaluate loop is becoming unreliable. It is a warning and routing aid,
not an automatic context-reset system.

Use the advisory when the current feature shows one or more of these risks:

- repeated same-class failures across correction rounds;
- evidence conflicts between developer claims, evaluator replay, review docs,
  feature registry state, or runtime output;
- weak replay evidence being reused as if it were full runtime proof;
- context contamination, such as stale assumptions from an older feature,
  copied findings that no longer match the changed files, or mixed feature
  identities in the same handoff.

## Evaluate Responsibility

`evaluate` should mark a loop-health risk when independent validation finds an
evidence conflict, weak replay evidence, or context contamination. It should not
fix implementation directly. It should describe the risk, record whether it
blocks acceptance, and recommend the next owner.

Good evaluator recommendations include:

- narrow the next developer correction to one failure class;
- return to `brainstorm` when the acceptance criteria or test plan are no
  longer clear;
- prepare a fresh-session handoff when stale context is likely affecting the
  review;
- request exact runtime replay when weak evidence is blocking proof.

## Converge Responsibility

`converge` should surface repeated same-class failures as a loop-health risk
before automatically continuing the correction loop. It should compare the
latest evidence against the original brainstorm goal, acceptance criteria,
done-when criteria, and evaluator findings.

If the next route is still clear, below the round limit, and scoped to a single
implementation or test-evidence correction, convergence may continue the normal
correction loop. A normal correction loop should not be escalated just because a
single evaluator finding exists.

If repeated same-class failures, unresolved evidence conflicts, stale-context
signs, or round-limit pressure make the next route unreliable, `converge` should
recommend one of these options instead of silently continuing:

- narrow scope and send a precise correction to `develop`;
- return to `brainstorm` to restate criteria or test scope;
- prepare a fresh-session handoff for the current feature;
- ask the user for a decision when product intent or loop health cannot be
  resolved from evidence.

## Non-Goals

The advisory must not automatically clear context, reset the conversation, spawn
subagents, create worktrees, or require fan-out execution. Subagents and worktrees remain optional strategies an agent may choose when they fit the task; they are not required Arbor behavior.

The advisory also must not turn every failing review into a blocker. Normal correction loops should continue when the failure is new, the owner is clear,
the evidence is coherent, and the loop remains below the round limit.

In short: normal correction loops should continue when evidence is coherent and
ownership is clear.
