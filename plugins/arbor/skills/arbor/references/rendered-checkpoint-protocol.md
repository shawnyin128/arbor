# Rendered Checkpoint Protocol

Arbor workflow packets are runtime handoffs. Normal users should see the
rendered checkpoint, not raw workflow JSON.

This protocol applies only to Arbor workflow checkpoints and decision points:
`brainstorm`, `develop`, `evaluate`, `converge`, and `release`. It does not
apply to direct answers, read-only explanations, ordinary code discussion, or
the agent's private reasoning.

## Visible Checkpoint Contract

Every visible workflow checkpoint must answer these questions in plain language:

| Question | Required visible content |
| --- | --- |
| What is happening now? | State the current situation and the work unit being handled in user-level words. |
| What does this checkpoint control? | Explain whether the checkpoint is a plan review, developer handoff, independent evaluation, convergence decision, or release status. |
| What changed or was checked? | Summarize concrete artifacts, evidence, checks, findings, or release status. |
| What did the agent decide by default? | Expose material defaults, tradeoffs, blocked checks, or judgment calls when they matter; otherwise say there were no material hidden decisions. |
| What happens next? | Name the next human-visible step or internal workflow step in readable terms. |

Skill-specific section headings remain owned by each skill. This protocol does
not replace those sections; it defines the minimum readable content they must
carry.

## Internal Packet Boundary

The structured packet may keep machine fields such as `schema_version`,
`source`, `route`, `ui`, `terminal_state`, `next_skill`, `feature_id`, and
`review_doc_path`. The rendered checkpoint must not make those fields the
primary user interface.

Do not print raw `*.v1` JSON, fenced JSON blocks, route assignments, terminal
state labels, or unexplained feature ids as the normal answer. Translate them
into user-facing language. For example, say "independent evaluation is next"
instead of `next_skill=evaluate`, and say "the reviewer found a blocking
regression" instead of a finding id alone.

## Release Visibility

`release` is status-only by default. In checkpoint mode, it may report that a
local checkpoint was saved and which readable step follows. It must not expose
handoff internals. In finalization or public-action mode, it must clearly
separate safe local preparation from commit, push, PR, tag, publish, or cache
sync actions that require explicit user authorization.

## Validation Scope

Rendered-output validation is a workflow-fact guard, not a style checker. It
should reject:

- raw workflow schema in the final visible response;
- route labels or terminal-state labels as primary text;
- unexplained internal ids, fixture ids, or assignment-style fields;
- missing required skill-specific visible sections;
- status text that implies evaluation, convergence, release, or publish already
  happened when only an earlier checkpoint ran.

Validation should not reject a direct answer because it lacks Arbor sections, and
it should not prescribe implementation approach, testing strategy, tone, or prose
style beyond the checkpoint readability contract.

## Real Runtime Evidence

For workflow-facing changes, at least one real runtime replay should capture the
final rendered response text when feasible. The tracked real-chain runner stores
`final-response.md` and asserts the strongest observable rendered-output
contract available for the selected cases. Static fixture checks and JSON schema
checks are preflight only; they do not replace a real final-response inspection.
