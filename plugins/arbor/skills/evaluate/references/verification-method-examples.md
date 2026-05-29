# Verification Method Examples

Use this reference when an evaluation needs help choosing concrete checks for a
changed artifact. It calibrates test-method selection; it does not replace the
brainstorm test plan, developer self-test evidence, or evaluator judgment.

The core rule is outcome-first: choose the strongest practical check for the
behavior a user, runtime, or downstream system can observe. Do not force one
test type across every feature.

## When To Read

Read this file when:

- the changed artifact type is unfamiliar;
- the brainstorm plan names broad verification such as "test the UI" or
  "verify the workflow";
- developer evidence covers only a happy path;
- the accepted outcome depends on rendered output, external runtime behavior,
  browser behavior, packaging, hooks, or generated artifacts;
- you need an adversarial check that would fail under a plausible broken
  version of the contract.

Do not read it for tiny direct fixes where the review plan already names an
obvious concrete check.

## Method Selection Matrix

| Development Scenario | Strong Evaluator Checks | Useful Adversarial Probes | Avoid |
| --- | --- | --- | --- |
| Pure functions, parsers, formatters, reducers, or algorithms | Unit tests, fixture input/output checks, boundary values, idempotence checks, property-style probes when cheap | Invalid input, empty input, repeated input, ordering changes, mutation or contract probes | Browser automation or full workflow replay when no rendered/runtime behavior is involved |
| CLI commands or local scripts | Real command replay, stdout/stderr and exit-code checks, fixture files, path and environment variation | Missing arguments, bad paths, permission errors, missing environment variables, malformed config | Claiming success from code inspection alone |
| Backend APIs or service boundaries | Endpoint or integration tests, request/response schema checks, status-code checks, contract tests with realistic payloads | Unauthorized requests, invalid payloads, duplicate requests, backward-compatibility payloads, failure responses | Only testing direct helper functions when the public endpoint contract changed |
| Database schema, migrations, or persistence | Migration up/down when supported, schema diff, seed fixtures, constraint checks, representative read/write flows | Re-running migration, old data shape, rollback, uniqueness/foreign-key violations, index-sensitive queries | Treating a successful code formatter or type check as migration proof |
| Frontend or UI behavior | Browser automation, DOM assertions, rendered-output inspection, screenshots when visual state matters, responsive viewport checks, console error inspection | Click/input flows, route changes, loading/empty/error states, keyboard flow, focus state, mobile viewport, asset loading failures | Browser automation for pure data utilities or style-token-only changes |
| Frontend state logic without browser-specific behavior | Unit or component-level state transition tests, event reducer checks, serialization checks | Conflicting events, stale state, reset behavior, invalid props, edge transitions | Full browser replay as the only proof when state logic can be tested directly |
| Visual design or layout | Rendered screenshot inspection, viewport matrix, text-overflow checks, focus/hover state checks, asset presence checks | Long labels, narrow mobile width, dark/light theme if supported, missing image assets, overlapping elements | Saying "looks good" without a rendered artifact or concrete visual risk check |
| Workflow, hook, router, plugin, or prompt-routing behavior | Real runtime replay when feasible, deterministic harness substitute when live runtime is unavailable, final rendered response capture, process-state checks | Wrong route, missing hook registration, silent failure, stale cache, bad structured-output fallback, broken rendered checkpoint | Presenting deterministic substitutes as live proof without a weak-pass label |
| Prompt, skill, or documentation contracts | Content and structure checks, scenario simulations, static wording guards, rendered-output checks for user-facing packets | Internal field leakage, public/internal entrypoint confusion, vague test labels, missing canonical example, contradictory wording | Fake unit tests that do not exercise the text contract |
| External API, connector, or hosted service behavior | Local contract tests around request construction and error handling, mocked schema tests, authorized live smoke only when safe | Auth failure, rate limit, schema drift, unavailable service, permission denial | Unapproved live calls, or accepting local mocks as full external proof without residual-risk labels |
| Generated files, reports, documents, or package artifacts | Structure checks, schema validation, golden/snapshot output, render/open checks, package manifest validation | Corrupt output, missing assets, path with spaces, non-ASCII data when relevant, stale version/cache metadata | Only checking that a file exists |
| ML, research, or evaluation pipelines | Small smoke run, deterministic fixture, metric sanity check, baseline comparison, seed/repro notes | Data leakage, unfair baseline, broken metric definition, random-seed sensitivity, tiny-sample overclaim | Treating one successful run as a general result without workload and seed context |
| Performance-sensitive changes | Representative workload benchmark, before/after comparison, profiling evidence, threshold justification | Pathological input, cold vs warm run, memory pressure, concurrency if relevant | Microbenchmark-only proof for a user-facing performance claim |
| Security, auth, or permissions | Negative authorization tests, role matrix, forbidden request/path checks, least-privilege checks | Cross-role access, default-open behavior, path traversal, secret or error-message leakage | Only testing the allowed happy path |

## Frontend And Browser Automation

Use browser automation when the accepted outcome depends on browser-observable
behavior:

- rendered DOM state;
- click, input, drag, keyboard, focus, or navigation behavior;
- browser routing or history state;
- responsive layout across meaningful viewports;
- console/runtime errors;
- asset loading, canvas rendering, or media behavior;
- accessibility or keyboard flow when it is part of the requirement.

Browser automation is not mandatory just because a repository contains frontend
code. Prefer unit or component checks when the change is pure state logic, data
mapping, style tokens without rendered behavior, or compile-time type contracts.

When browser automation is unavailable, use the strongest practical substitute,
such as component rendering, DOM snapshots, screenshot inspection, or static
contract checks, and label the remaining browser gap as a weak pass.

## Evidence Quality

An accepted evaluation should normally combine:

- developer evidence replay or a recorded reason replay was not useful;
- at least two independent evaluator check categories that fit the artifact;
- one adversarial probe such as a negative case, broken-input case, mutation
  probe, static contract probe, or realistic wrong-route scenario;
- a visible mapping back to acceptance criteria and done-when criteria;
- weak-pass labels for any live runtime, browser, connector, rendered-output, or
  publish behavior that was substituted rather than directly proven.

Avoid vague evidence labels such as "tests pass", "manually reviewed UI",
"checked output", or "looks good" unless they are paired with the command,
artifact, scenario, expected result, observed result, and residual risk.
