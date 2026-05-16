# Delegation Packet And Effort Budget

Arbor can help an agent describe optional delegation when delegation is actually
useful. This is a packet format and effort heuristic, not a requirement to use
subagents, worktrees, fan-out execution, or parallel coding.

## Purpose

Some work benefits from bounded outside investigation: broad research, source
collection, independent evidence checks, or narrow artifact review. Other work
gets worse when split because decisions are tightly coupled. Arbor should help
the agent make that judgment visible without taking the judgment away.

Use this reference only when the agent independently chooses delegation as a
useful strategy for the current task or when the user explicitly asks for it.
Direct answers, simple edits, tightly coupled coding, and tightly coupled workflow changes remain single-threaded by default.

## Delegation Packet

When delegation is used, write a compact packet with these fields:

- objective: the specific question or evidence target;
- output format: the exact shape of the result expected back;
- tools/sources: allowed or preferred tools, files, docs, URLs, or data sources;
- boundaries: what is out of scope, what must not be edited, and which upstream
  decisions must not be reopened;
- effort budget: an approximate cap on time, search breadth, tool calls, or
  evidence depth;
- context pointers: the review doc, decision trace, feature id, source files, or
  exact artifact paths needed to avoid context loss;
- stop conditions: when to stop early because enough evidence was found, the
  source is unavailable, or the delegation no longer fits.

The packet should be specific enough to prevent duplicated work and missing
coverage, while small enough that it does not become a second planning system.

## Effort Budget

Scale effort to task shape:

- no delegation for direct answers, small edits, single obvious checks, or work
  where all decisions must stay in one context;
- one narrow investigation for a bounded question with one clear output;
- two to four bounded investigations only for separable evidence gathering,
  such as comparing independent sources or checking unrelated artifacts;
- broader fan-out only when the user explicitly asks for it or the task is
  high-value, research-heavy, and separable enough to justify the cost.

The effort budget is advisory. It helps the agent avoid over-investing in simple
tasks, but it must not require a particular number of subagents, tool calls,
worktrees, or files. This guidance must not require subagents or worktrees and
must not require fan-out execution.

## When Not To Delegate

Use this section as the when not to delegate checklist.

Do not delegate by default when:

- the task is a direct answer, a small mechanical edit, or a single-file fix;
- the code or workflow decisions are tightly coupled;
- the delegate would need the full trace to avoid changing product intent;
- the work requires exact runtime execution by the main agent;
- the user asked for no fan-out, no subagents, no worktrees, or no file writes;
- delegation would hide implementation-time decisions from the review evidence.

If delegation is skipped, no packet is required. A short note such as "kept
single-threaded because the change is tightly coupled" is enough when the
choice matters.

## Workflow Ownership

- `brainstorm` may include a delegation packet only for optional evidence work
  that is separable from the main feature.
- `develop` may use a packet for bounded investigation, but implementation
  remains owned by the main developer unless the user explicitly assigned work
  elsewhere.
- `evaluate` may use a packet for independent evidence gathering, but findings
  and verdict remain evaluator-owned.
- `converge` does not require delegation. It may note whether delegated evidence
  is sufficient, missing, duplicated, or out of scope.

Delegation evidence belongs in the same review document as the feature. It does
not replace the decision trace, developer self-tests, evaluator checks, or
convergence decision.
