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

## Visible Response Language

Render user-facing checkpoint prose in the user's active chat language unless
the user explicitly requests a different output language. The skill package,
internal schema fields, enum values, code identifiers, command names, file
paths, and stable technical names may remain English or literal.

The English section headings documented in each skill are canonical for English
prompts. For non-English prompts, use localized heading equivalents in the same
order, with the same required section meaning and table requirements. Do not
fall back to English headings only because the skill source file is written in
English.

For mixed-language prompts, use the user's dominant request language for visible
checkpoint prose unless the user names an explicit output language. Keep quoted
error text, commands, paths, APIs, package names, and code symbols in their
original language.

## Final Response Preflight

The final assistant message is part of the workflow artifact. Before returning
from a user-visible workflow skill, the agent must run a final-response
preflight over the exact text it is about to send to the user, not only over an
internal `user_response` draft or fixture row.

The preflight must verify:

- the final message renders the skill-specific checkpoint rather than a compact
  prose-only summary;
- for English prompts, required skill-specific headings appear exactly and in
  order;
- for non-English prompts, localized heading equivalents appear in the same
  order;
- required table sections contain Markdown tables;
- raw workflow schema, route labels, terminal-state labels, fixture ids, and
  unexplained internal ids are not the primary visible output;
- user-facing prose follows the user's active chat language or explicit output
  language;
- the next step is described in user-facing language and does not imply that a
  later checkpoint already happened.

If the captured final message fails this preflight, rewrite the visible response
before finishing. Static fixture checks are not a substitute for this
last-mile check because they do not inspect the actual live final response.

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
