# Outcome Evaluation And Observability

Arbor evaluates workflow changes by the outcome they produce and the evidence
that makes that outcome observable. It should not require exact turn-by-turn path
matching unless the feature explicitly claims a path as the behavior under test.

## Purpose

Workflow systems can look correct in isolated traces while failing at the
visible checkpoint, registry state, review evidence, or release gate. This
reference keeps evaluation focused on final state and checkpoint outcomes:

- user-visible rendered output;
- review rounds and findings;
- feature registry and session memory state;
- git commits, file side effects, and selected-file scope;
- real runtime replay or the strongest deterministic substitute;
- trace evidence when exact skill-chain proof is available.

## Evaluation Contract

For workflow-facing changes, `evaluate` should inspect the final state before
arguing about the exact path. Useful evidence includes rendered output,
workflow artifacts, review document rounds, process-state checks, real workflow
chain replay, static contract probes, mutation probes, and trace evidence.

If exact runtime telemetry, live connector behavior, rendered final output, or
publish behavior is unavailable, mark the result as a weak pass and name the
remaining proof. Do not present a deterministic substitute as full live proof.

Outcome-first evaluation does not mean accepting any path. Route and sequence
evidence still matters when the feature specifically changes routing,
checkpoint order, release policy, or startup behavior. In those cases, require
the strongest observable route evidence available, and record any telemetry gap.

## What Not To Require

This guidance must not require LLM judges, fixed path matching, exact turn-by-turn path replay, subagents, worktrees, fan-out execution, or one universal test type by default. Prefer deterministic checks when they can prove the outcome. Use LLM or human-style judgment only as supporting evidence, not as the default acceptance gate.

## Stage Ownership

- `develop` records which observable outcomes its self-tests cover and which
  proof is deferred to evaluation or release.
- `evaluate` challenges final state, rendered output, workflow artifacts,
  trace evidence, and weak-pass labels before accepting.
- `converge` decides whether developer and evaluator evidence agree on the
  outcome and whether any weak-pass gap blocks completion.
- `release` checks that required outcome and observability evidence exists
  before finalization or publish, without re-evaluating correctness.

Evidence belongs in the same review document as the feature. Runtime artifacts
such as `final-response.md`, route traces, reports, and temporary replay
directories may support the review, but review evidence should summarize what
was observed in user-readable terms.
