# Done-When Verification Thread

Arbor-managed work should carry one verification thread from planning to
release. The thread says what must be true for the feature to be done and which
evidence proves that outcome.

This is workflow discipline, not an implementation constraint. The agent keeps
normal judgment over how to read, design, code, test, and review.

## Stage Ownership

| Stage | Responsibility |
| --- | --- |
| `brainstorm` | Define task-appropriate done-when criteria and artifact-appropriate verification before development begins. |
| `develop` | Map self-tests, structure checks, content checks, or replay evidence to the accepted done-when criteria. Record any verification gap instead of hiding it. |
| `evaluate` | Independently challenge the done-when criteria, add adversarial checks, and label weak pass evidence when exact runtime proof is unavailable. |
| `converge` | Decide whether developer and evaluator evidence agrees with the done-when criteria and the original brainstorm goal. |
| `release` | Check that required verification evidence exists before finalization or publish, without re-evaluating correctness. |

## Good Done-When Criteria

Good criteria are outcome statements, not command lists. They should answer:

- what user-visible or workflow-visible behavior must hold;
- what artifact or runtime surface proves the behavior;
- which stage owns the strongest practical evidence;
- what remains a weak pass if exact live proof is unavailable.

Examples:

- "A planning continuation creates a durable brainstorm checkpoint and does not edit implementation files."
- "A develop handoff cannot proceed unless every self-test row covers a named planned check or done-when criterion."
- "A release finalization reports missing verification evidence instead of publishing a feature whose review thread is incomplete."

## Verification Shape

Use the strongest artifact-appropriate verification available:

- unit tests for unit-level behavior;
- scenario replays for workflow behavior;
- content and structure checks for docs or skill contracts;
- rendered-output inspection for user-facing workflow packets;
- static, schema, or mutation probes for contract drift;
- live runtime checks when the claim is specifically about live runtime behavior.

Do not force one test type across all work. A docs-only feature may need content,
structure, and mutation evidence; a router feature may need scenario replay and
negative controls; a publish feature may need release evidence and cache/runtime
checks.

## Non-Goals

This thread must not:

- route small direct tasks into Arbor just to create criteria;
- require full test suites for every feature;
- require live runtime replay when a deterministic substitute is the strongest feasible evidence;
- require subagents, worktrees, or fan-out execution;
- prescribe implementation strategy, code style, or reasoning order.

Weak evidence is allowed only when it is named. If exact runtime telemetry,
rendered final output, external connector behavior, or publish behavior was not
available, call the result a weak pass and record the remaining proof.
