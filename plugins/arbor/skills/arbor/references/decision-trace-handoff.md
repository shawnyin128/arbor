# Decision Trace Handoff

Arbor preserves decision continuity across workflow roles. This is a handoff
contract, not a default multi-agent orchestration layer.

## Purpose

Long-running workflow work fails when later stages inherit artifacts but not the
decisions behind them. A decision trace keeps each action informed by the
important upstream choices without forcing the agent into a fixed
implementation strategy.

The trace is intentionally compact. It records the decisions needed by the next
role, not every line of reasoning.

## Brainstorm Responsibilities

For ready Arbor-managed work, `brainstorm` records a concise decision trace:

- key decisions that define the feature scope or product behavior;
- rejected options and why they should not be silently reopened;
- allowed implementation discretion, including where the developer may choose
  repo-native details freely;
- decision invariants that must remain true unless the workflow returns to
  planning;
- evidence pointers for source material, user approvals, and review context.

Small direct tasks stay outside this contract. Brainstorm should not turn
ordinary direct answers into managed work just to create a trace.

## Develop Responsibilities

`develop` consumes the decision trace before editing. It may implement freely
inside the accepted scope, but the Developer Round should record:

- implementation-time decisions made while applying the plan;
- decision deviations from the trace, including why they were necessary;
- whether each decision invariant still holds;
- any material drift that should return to `brainstorm` instead of being hidden
  inside implementation.

If a required change would violate decision invariants or reopen rejected
options, `develop` should return `needs_brainstorm` or record a blocker rather
than silently changing the plan.

## Evaluate Responsibilities

`evaluate` checks whether the implementation stayed aligned with the decision
trace. It should look for:

- decision drift between the plan, implementation, and developer evidence;
- hidden decision conflict, where implementation-time choices contradict
  upstream key decisions or rejected options;
- weak proof that appears to satisfy a check while rewriting the original goal;
- missing developer evidence for implementation-time decisions or decision
  deviations.

Evaluate does not fix implementation directly. It records findings and routes
the next owner through the normal workflow.

## Converge Responsibilities

`converge` checks decision trace consistency before marking a feature done. A
feature should not converge when unresolved decision drift, hidden decision
conflict, or violated decision invariants remain.

When the evidence is missing or inconsistent, converge should return the
appropriate evidence or planning route: missing brainstorm trace routes to
`brainstorm`, missing developer decision evidence routes to `develop`, and
missing evaluator drift checks route to `evaluate`.

## Non-Goals

This contract:

- is not a default multi-agent orchestration system;
- must not require subagents or worktrees;
- must not require fan-out execution or parallel coding;
- must not prescribe implementation strategy, file order, or test type;
- must not route small direct tasks into Arbor.
