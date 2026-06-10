# Closed-Loop Diagnostics

Use this reference when Arbor is handling failures in simulations, agent
behavior systems, ranking loops, planners, schedulers, markets, game economies,
control systems, or other closed-loop systems where outputs feed later state.

The goal is to diagnose system dynamics before repair. Arbor should not jump
from "the artifact looks wrong" to a schema-first parser, validator, or
normalizer fix unless evidence shows the interface contract is the actual root
cause.

Required anchor terms for checks: candidate pool, decision distribution.

## Trigger Signals

Treat feedback as closed-loop diagnostics work when the user or reviewer says
one of these patterns:

- a simulation collapse, runaway loop, starvation, saturation, oscillation, or
  domination by one candidate class;
- an agent timeline, market, scheduler, planner, or generated artifact behaves
  logically wrong even though code still runs;
- outputs are flooded by repeated choices, invalid demand, impossible state, or
  implausible transitions;
- tests pass, but the live artifact still looks wrong;
- a proposed fix focuses on schema, validation, parsing, or normalization before
  explaining the state trajectory.

## Evidence Packet

A ready diagnostic plan must require the smallest useful evidence packet before
implementation:

| Evidence | Purpose |
| --- | --- |
| State trajectory | Shows how key state variables evolve over time and where collapse begins. |
| Event/effect trace | Connects decisions, events, effects, and downstream state changes. |
| Candidate pool trace | Shows which candidate source creates available actions or events. |
| Decision distribution | Shows selected action or event frequencies across time, agents, or sources. |
| Dimension and unit check | Finds mixed units, incomparable scales, sign errors, or time-step mistakes. |
| Budget balance estimate | Compares inflows, outflows, conservation rules, capacity, and depletion rates. |
| Live artifact sample | Captures the actual output users judge, not only a unit-test fixture. |
| Weak-pass gap | Names any missing live trace, raw trace, runtime target, or telemetry proof. |

For closed-loop systems, "tests pass" is not enough when the live artifact still
fails the intended behavior. The diagnostic packet must include raw trace
evidence or explicitly label the weak-pass gap.

## Planning Rules

`brainstorm` should plan the diagnostic first:

- name the state variables that define health or collapse;
- name likely feedback loop paths from input decisions to later state;
- identify candidate source and decision selection channels separately;
- require an event/effect trace before accepting a root-cause claim;
- include at least one dimension or unit check when numeric dynamics exist;
- include a rough budget balance estimate when resources, demand, capacity,
  population, probability mass, money, energy, inventory, or time are consumed
  or produced;
- defer implementation until the diagnostic can distinguish system dynamics
  from interface contract defects.

## Convergence Rules

`converge` may not close a closed-loop diagnostics feature from static tests or
defensive code alone. It must inspect whether developer and evaluator evidence
include the agreed raw trace, state trajectory, live artifact, and artifact
quality criteria.

Block convergence when:

- the implementation only adds parser, validator, schema, or normalizer defenses
  without proving why the original loop collapsed;
- the raw trace or state trajectory is missing;
- the live artifact still has the same behavior failure;
- the result is only a weak pass and the weak-pass gap blocks the brainstorm
  done-when criteria.

## Release Rules

`release` should preserve the proof conditions that affect confidence:

- live artifact location or sample;
- raw trace source and command;
- state trajectory evidence;
- behavior quality metric or reviewer criterion;
- weak-pass gap when live proof, runtime telemetry, or raw trace is missing.

Release should refuse a completion claim for a closed-loop diagnostics feature
when the review evidence says tests pass but the live artifact still collapses.

## Anti-Patterns

### "Schema-First Fix"

Adding schema checks may be useful, but it is not a root-cause diagnosis for a
closed-loop failure unless the evidence packet shows malformed inputs caused
the collapse.

### "Unit Tests As Behavior Proof"

Unit tests can protect pieces of the repair, but the feature is not proven if
the state trajectory, event/effect trace, and live artifact are missing.

### "Domain Constants As Arbor Rules"

Do not encode project-specific constants such as hunger, energy, money, or
candidate names into Arbor. Encode the diagnostic method: state, effects,
candidate sources, decisions, dimensions, budgets, traces, and artifacts.
