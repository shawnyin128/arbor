# Feature 8 Review: Trigger Scenario Sidecar

## Purpose

Convert the human-readable Arbor hook trigger scenario corpus into a machine-checkable sidecar that the future plugin-based dispatch evaluation harness can consume.

## Scope

In scope:

- Add `docs/reviews/hook-trigger-scenarios.json`.
- Preserve `docs/reviews/hook-trigger-scenarios.md` as the human-readable source.
- Define structured defaults and per-scenario overrides for dispatch expectations.
- Cover all 150 Markdown scenarios through expansion.
- Add tests that validate sidecar schema, coverage, hook ids, `NONE` behavior, single-hook behavior, multi/ambiguous overrides, and optional args.

Out of scope:

- Dispatcher implementation.
- Eval harness implementation.
- Fixture builders.
- Actual semantic precision/recall/false-positive metrics.
- Hook behavior changes.

## Design Notes

The sidecar is compact by design:

- Markdown stores scenario ids, expressions, expected labels, and notes.
- JSON stores machine-checkable expectation defaults and overrides.
- Tests merge the two sources and verify every Markdown row expands to a complete dispatch expectation.

This keeps the scenario corpus readable while avoiding a brittle duplicated 150-row JSON copy. Future harness code should consume the expanded Markdown-plus-sidecar view.

## Implementation Notes

- Added `docs/reviews/hook-trigger-scenarios.json`.
- Added `HookTriggerSidecarTests` to `tests/test_arbor_skill.py`.
- Updated `docs/arbor-skill-design.md` with Feature 8 scope and Stage B progress.

## Validation

- `python3 -m unittest tests.test_arbor_skill.HookTriggerSidecarTests`: 5 tests passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 64 tests passed.
- `python3 -m json.tool docs/reviews/hook-trigger-scenarios.json`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f8-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py tests/test_arbor_skill.py`: passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f8-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 64 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f8-coverage conda run -n arbor python -m coverage report`: total coverage 88%.

## Scenario Coverage

- 150 Markdown scenarios are parsed and covered.
- Default expectation labels cover `H1`, `H2`, `H3`, `NONE`, and `MULTI`.
- Overrides only reference scenario ids that exist in Markdown.
- Hook ids are constrained to the three Arbor hook ids.
- `NONE` scenarios expand to no expected or optional hooks and forbid all Arbor hooks.
- `H1`, `H2`, and `H3` scenarios expand to their corresponding single hook.
- `MULTI` scenarios require explicit structured overrides.
- Optional args are keyed by valid Arbor hook ids and contain string argument lists.

## Developer Response

Feature 8 is implemented and targeted-tested. The sidecar creates the contract needed before building fixture generation, dispatcher adapters, or metric-producing evaluation.

### Response To Round 1

Review item addressed:

- `F8-R1-P1`: Relabeled `M-P014` and `M-P015` from single-hook labels to `MULTI`, because both scenarios explicitly allow conditional extra hook behavior.

Additional hardening:

- Added `field_semantics` to `docs/reviews/hook-trigger-scenarios.json` to distinguish `expected_hooks`, `optional_expected_hooks`, and `forbidden_hooks`.
- Strengthened `HookTriggerSidecarTests.test_sidecar_preserves_single_hook_and_none_semantics` so non-`MULTI` `H1`/`H2`/`H3` rows must have no optional hooks and must forbid every non-target Arbor hook.

Expected effect:

- Future precision/recall metrics cannot count multi-hook dispatch as passing a single-label scenario.

Validation after fix:

- `python3 -m unittest tests.test_arbor_skill.HookTriggerSidecarTests`: 5 tests passed.
- `python3 -m unittest tests/test_arbor_skill.py`: 64 tests passed.
- `python3 -m json.tool docs/reviews/hook-trigger-scenarios.json`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor`: passed.
- `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor`: passed.
- `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f8-r1fix-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py tests/test_arbor_skill.py`: passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f8-r1fix-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py`: 64 tests passed.
- `env COVERAGE_FILE=/private/tmp/arbor-f8-r1fix-coverage conda run -n arbor python -m coverage report`: total coverage 88%.

## Adversarial Review Rounds

### Round 1: Trigger Sidecar Replay

#### Round Result Tab

| Round | Scope | Verdict | Problems | Probe pass rate | Convergence |
| --- | --- | --- | ---: | ---: | --- |
| F8-R1 | Developer validation playback plus Markdown/JSON corpus coverage, sidecar schema, expansion integrity, label semantics, optional args, and future-harness metric readiness probes | Needs changes | 1 | 29/31, 93.5% | Not converged |

#### Problems Found

| ID | Severity | Area | Finding | Evidence | Impact | Next-round acceptance gate |
| --- | --- | --- | --- | --- | --- | --- |
| F8-R1-P1 | P2 | Sidecar label semantics | Non-`MULTI` scenario labels allow optional extra hooks. | `M-P014` is labeled `H3` but allows optional `arbor.in_session_memory_hygiene`; `M-P015` is labeled `H2` but allows optional `arbor.goal_constraint_drift`. | A future harness can count a multi-hook dispatch as passing a single-label scenario, inflating precision/recall and contradicting the sidecar contract that single-hook labels expand to their corresponding single hook. | Relabel these rows as `MULTI` with explicit structured overrides, or remove the optional hooks and forbid all non-target hooks for single-label scenarios. |

#### Test Coverage Table

| Test category | Cases/checks run | Category coverage | Passed | Failed | Pass rate | Result summary |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Developer baseline playback | 7 checks | 7/7 planned checks, 100% | 7 | 0 | 100% | Replayed targeted sidecar tests, full unit suite, sidecar JSON parsing, standalone and packaged skill validation, py_compile, coverage run, and coverage report. |
| Corpus coverage | 6 probes | 6/6 planned probes, 100% | 6 | 0 | 100% | Markdown row count is 150, scenario ids are unique, all labels appear, the sidecar source path resolves, overrides have no dangling ids, and every `MULTI` row has an override. |
| Schema/defaults | 8 probes | 8/8 planned probes, 100% | 8 | 0 | 100% | Schema version, hook ids, default labels, required default keys, fixture vocabulary, decision vocabulary, hook vocabulary, and override field names are valid. |
| Expansion integrity | 7 probes | 7/7 planned probes, 100% | 7 | 0 | 100% | Every expanded scenario has required keys, valid fixtures and decisions, known hook ids, and no expected/optional hooks conflict with forbidden hooks. |
| Label semantics | 5 probes | 5/5 planned probes, 100% | 3 | 2 | 60% | `NONE`, exact expected hook, and `MULTI` specificity passed; single-label optional-hook and forbidden-complement checks failed for `M-P014` and `M-P015`. |
| Optional args | 5 probes | 5/5 planned probes, 100% | 5 | 0 | 100% | Optional args reference known hook ids, use string lists, use Hook 3 `--doc` pairs, keep project-local docs relative, and reserve absolute docs for outside-root fixtures. |
| Total adversarial probes | 31 probes | 31/31 planned probes, 100% | 29 | 2 | 93.5% | Excludes baseline playback checks. |

#### Baseline Playback Table

| Command/check | Status | Notes |
| --- | --- | --- |
| `python3 -m unittest tests.test_arbor_skill.HookTriggerSidecarTests` | Pass | 5 tests passed. |
| `python3 -m unittest tests/test_arbor_skill.py` | Pass | 64 tests passed. |
| `python3 -m json.tool docs/reviews/hook-trigger-scenarios.json` | Pass | Sidecar JSON parsed successfully. |
| `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor` | Pass | Standalone skill validation passed. |
| `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor` | Pass | Packaged skill validation passed. |
| `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f8-r1-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py tests/test_arbor_skill.py` | Pass | No compile errors. |
| `env COVERAGE_FILE=/private/tmp/arbor-f8-r1-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py` | Pass | 64 tests passed under coverage. |
| `env COVERAGE_FILE=/private/tmp/arbor-f8-r1-coverage conda run -n arbor python -m coverage report` | Pass | Total coverage 88%. |

#### Scenario Test Matrix

| Scenario ID | Scenario | Category | Expected behavior | Observed result | Status |
| --- | --- | --- | --- | --- | --- |
| F8-R1-S1 | Markdown corpus count | Corpus coverage | Parse all 150 scenario rows. | Parsed 150 rows. | Pass |
| F8-R1-S2 | Override id integrity | Corpus coverage | Every override references an existing Markdown scenario id. | No dangling overrides found. | Pass |
| F8-R1-S3 | `MULTI` structure | Corpus coverage | Every Markdown `MULTI` row has an explicit structured override. | All 16 `MULTI` rows have overrides. | Pass |
| F8-R1-S4 | Hook id alignment | Schema/defaults | Sidecar hook ids should match packaged Arbor plugin hook ids. | Hook id sets matched. | Pass |
| F8-R1-S5 | Expanded hook conflicts | Expansion integrity | Expected/optional hooks must not also be forbidden. | No expected-forbidden or optional-forbidden overlap found. | Pass |
| F8-R1-S6 | `NONE` semantics | Label semantics | `NONE` rows should allow only `none`, expect no hooks, and forbid all Arbor hooks. | All 48 `NONE` rows matched. | Pass |
| F8-R1-S7 | Single-label expected hook | Label semantics | `H1`, `H2`, and `H3` rows should keep the exact primary hook in `expected_hooks`. | All single-label rows kept the correct primary hook. | Pass |
| F8-R1-S8 | Single-label optional hooks | Label semantics | Non-`MULTI` labels should not permit extra optional hooks. | `M-P014` and `M-P015` allow extra optional hooks. | Fail |
| F8-R1-S9 | Single-label forbidden complement | Label semantics | Non-target hooks should be forbidden for single-label rows. | `M-P014` does not forbid H2; `M-P015` does not forbid H3. | Fail |
| F8-R1-S10 | Optional Hook 3 args | Optional args | Hook 3 optional args should be `--doc` pairs with project-local relative docs unless the fixture is outside-root. | All optional docs matched the expected shape. | Pass |

#### Impact Assessment

| Functional area | Risk checked | Result | Assessment |
| --- | --- | --- | --- |
| Corpus completeness | The Markdown corpus should remain the human-readable source while sidecar expansion covers every row. | 150 rows parsed and covered. | No negative impact found. |
| Sidecar schema | Defaults and overrides should give a future harness stable fields. | Required keys and vocabularies are present. | No negative impact found. |
| Hook contract alignment | Sidecar hook ids should match packaged plugin hook ids. | Hook ids matched. | No negative impact found. |
| Label-to-metric integrity | Single-label rows should not pass multi-hook dispatch unless labeled/structured as ambiguous or multi. | `M-P014` and `M-P015` fail this invariant. | Needs change before metric-producing Stage B harness work. |
| Optional args safety | Selected Hook 3 docs should remain machine-checkable and project-local unless explicitly testing outside-root rejection. | Optional args probes passed. | No negative impact found. |

#### Optimization Suggestions

| Priority | Suggestion | Rationale | Follow-up owner |
| --- | --- | --- | --- |
| P1 | Add a permanent test that non-`MULTI` labels have no `optional_expected_hooks` and forbid every non-target Arbor hook. | This protects future precision/recall metrics from accepting multi-hook dispatch on single-label scenarios. | Feature 8 maintenance. |
| P2 | Relabel `M-P014` and `M-P015` as `MULTI` if the optional hook should be accepted. | Their notes already describe conditional extra hook behavior, which is exactly what `MULTI` is for. | Scenario corpus owner. |
| P3 | Keep the sidecar compact, but add a short schema note distinguishing `expected_hooks` from `optional_expected_hooks`. | The distinction affects scoring and should be unambiguous before harness implementation. | Stage B harness owner. |

### Round 2: Round 1 Fix Playback

#### Round Result Tab

| Round | Scope | Verdict | Problems | Probe pass rate | Convergence |
| --- | --- | --- | ---: | ---: | --- |
| F8-R2 | Playback of `F8-R1-P1` fix plus baseline validation, label-semantics regression probes, schema hardening, corpus expansion, optional args, and future-harness metric readiness checks | Accepted | 0 | 33/33, 100% | Converged for Feature 8 sidecar scope |

#### Problems Found

| ID | Severity | Area | Finding | Evidence | Impact | Next-round acceptance gate |
| --- | --- | --- | --- | --- | --- | --- |
| F8-R2-NF1 | None | Trigger sidecar | No new review finding. | Developer baseline checks passed; independent adversarial probes passed 33/33. | Feature 8 can be treated as accepted for structured sidecar readiness. | No additional Feature 8 gate. Continue to deterministic fixture builders and dispatch harness work. |

#### Prior Findings Replay

| Prior finding | Status | Playback evidence | Result |
| --- | --- | --- | --- |
| `F8-R1-P1`: non-`MULTI` labels allow optional extra hooks | Closed | `M-P014` and `M-P015` are now labeled `MULTI`; single-label rows have no optional hooks and forbid every non-target Arbor hook; `field_semantics` documents scoring semantics. | Multi-hook dispatch can no longer pass a single-label scenario through these two rows. |

#### Test Coverage Table

| Test category | Cases/checks run | Category coverage | Passed | Failed | Pass rate | Result summary |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Developer baseline playback | 8 checks | 8/8 planned checks, 100% | 8 | 0 | 100% | Replayed targeted sidecar tests, full unit suite, sidecar JSON parsing, standalone and packaged skill validation, py_compile, coverage run, and coverage report. |
| Corpus coverage | 6 probes | 6/6 planned probes, 100% | 6 | 0 | 100% | Markdown row count is 150, scenario ids are unique, all labels appear, sidecar source resolves, overrides have no dangling ids, and every `MULTI` row has an override. |
| Schema/defaults | 9 probes | 9/9 planned probes, 100% | 9 | 0 | 100% | Schema version, `field_semantics`, hook ids, default labels, required keys, fixture vocabulary, decision vocabulary, hook vocabulary, and override field names are valid. |
| Expansion integrity | 7 probes | 7/7 planned probes, 100% | 7 | 0 | 100% | Every expanded scenario has required keys, valid fixtures and decisions, known hook ids, and no expected/optional hooks conflict with forbidden hooks. |
| Label semantics | 6 probes | 6/6 planned probes, 100% | 6 | 0 | 100% | `NONE`, single-label exact hook, single-label no-optional-hooks, forbidden-complement, `MULTI` specificity, and the `M-P014`/`M-P015` relabel all passed. |
| Optional args | 5 probes | 5/5 planned probes, 100% | 5 | 0 | 100% | Optional args reference known hook ids, use string lists, use Hook 3 `--doc` pairs, keep project-local docs relative, and reserve absolute docs for outside-root fixtures. |
| Total adversarial probes | 33 probes | 33/33 planned probes, 100% | 33 | 0 | 100% | Excludes baseline playback checks. |

#### Baseline Playback Table

| Command/check | Status | Notes |
| --- | --- | --- |
| `python3 -m unittest tests.test_arbor_skill.HookTriggerSidecarTests` | Pass | 5 tests passed. |
| `python3 -m unittest tests/test_arbor_skill.py` | Pass | 64 tests passed. |
| `python3 -m json.tool docs/reviews/hook-trigger-scenarios.json` | Pass | Sidecar JSON parsed successfully. |
| `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor` | Pass | Standalone skill validation passed. |
| `python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor` | Pass | Packaged skill validation passed. |
| `env PYTHONPYCACHEPREFIX=/private/tmp/arbor-f8-r2-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py tests/test_arbor_skill.py` | Pass | No compile errors. |
| `env COVERAGE_FILE=/private/tmp/arbor-f8-r2-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py` | Pass | 64 tests passed under coverage. |
| `env COVERAGE_FILE=/private/tmp/arbor-f8-r2-coverage conda run -n arbor python -m coverage report` | Pass | Total coverage 88%. |

#### Scenario Test Matrix

| Scenario ID | Scenario | Category | Expected behavior | Observed result | Status |
| --- | --- | --- | --- | --- | --- |
| F8-R2-S1 | Round 1 relabel replay | Label semantics | `M-P014` and `M-P015` should no longer be single-label rows if extra hooks are allowed. | Both rows are labeled `MULTI`. | Pass |
| F8-R2-S2 | Single-label optional-hook guard | Label semantics | `H1`, `H2`, and `H3` rows should have no optional extra hooks. | No single-label optional hooks found. | Pass |
| F8-R2-S3 | Single-label forbidden complement | Label semantics | Single-label rows should forbid every non-target Arbor hook. | All single-label rows had exact forbidden complements. | Pass |
| F8-R2-S4 | Field semantics | Schema/defaults | Sidecar should document `expected_hooks`, `optional_expected_hooks`, and `forbidden_hooks`. | `field_semantics` contains all three fields. | Pass |
| F8-R2-S5 | Markdown corpus count | Corpus coverage | Parse all 150 scenario rows. | Parsed 150 rows. | Pass |
| F8-R2-S6 | `MULTI` structure | Corpus coverage | Every Markdown `MULTI` row should have an explicit sidecar override. | All `MULTI` rows have overrides. | Pass |
| F8-R2-S7 | Hook id alignment | Schema/defaults | Sidecar hook ids should match packaged Arbor plugin hook ids. | Hook id sets matched. | Pass |
| F8-R2-S8 | Expanded hook conflicts | Expansion integrity | Expected/optional hooks must not also be forbidden. | No hook-set conflicts found. | Pass |
| F8-R2-S9 | `NONE` semantics | Label semantics | `NONE` rows should allow only `none`, expect no hooks, and forbid all Arbor hooks. | All `NONE` rows matched. | Pass |
| F8-R2-S10 | Optional Hook 3 args | Optional args | Hook 3 optional args should be `--doc` pairs with project-local relative docs unless the fixture is outside-root. | Optional docs matched the expected shape. | Pass |

#### Impact Assessment

| Functional area | Risk checked | Result | Assessment |
| --- | --- | --- | --- |
| Round 1 label-semantics bug | Multi-hook dispatch should not pass single-label scenarios. | `M-P014` and `M-P015` are now `MULTI`; single-label invariants pass. | Fixed. |
| Sidecar schema clarity | A future harness should understand required, optional, and forbidden hook scoring fields. | `field_semantics` documents all three fields. | No negative impact found. |
| Corpus completeness | The Markdown corpus should still expand to structured expectations for every row. | 150 rows parsed and expanded. | No negative impact found. |
| Hook contract alignment | Sidecar hook ids should match packaged plugin hook ids. | Hook ids matched. | No negative impact found. |
| Optional args safety | Selected Hook 3 docs should remain machine-checkable and project-local unless explicitly testing outside-root rejection. | Optional args probes passed. | No negative impact found. |

#### Optimization Suggestions

| Priority | Suggestion | Rationale | Follow-up owner |
| --- | --- | --- | --- |
| P1 | Keep the strengthened single-label invariant test permanently. | It guards the most important scoring boundary before precision/recall metrics are introduced. | Feature 8 maintenance. |
| P2 | Proceed to deterministic fixture builders before dispatcher scoring. | The sidecar is now machine-checkable, but Stage B metrics still require reproducible project states. | Stage B harness owner. |
