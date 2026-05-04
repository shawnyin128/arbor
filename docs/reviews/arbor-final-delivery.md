# Arbor Final Delivery

## Status

Arbor is complete for the current skill/plugin scope.

Completed scope:

- standalone `arbor` skill;
- project-local initialization for `AGENTS.md` and `.codex/memory.md`;
- project-level hook registration through `.codex/hooks.json`;
- Hook 1 session startup context packet;
- Hook 2 in-session memory hygiene packet;
- Hook 3 AGENTS goal/constraint/map drift packet;
- repo-local `plugins/arbor` plugin package;
- sidecar-backed Stage B trigger evaluation harness;
- full-corpus hook execution-chain report;
- isolated installed-plugin runtime probe.
- gated semantic metric formulas for real plugin trigger output, including raw-versus-presentation missing-required fields.
- repeated full-corpus stability aggregation for gate-ready real plugin runtime reports.
- Stage B final review document for plugin runtime trigger evaluation closure.
- plugin payload inventory validation that rejects transient release artifacts, symlinks, unsupported entries, and unexpected payload drift before install validation passes.
- authenticated installed-plugin runtime probing through an isolated Codex home, including explicit auth copy, local plugin cache materialization, isolated project trust, and true `$arbor` injection evidence.
- authenticated selected real-runtime trigger batches with progress JSONL and adapter optional-args normalization.

Deferred future scope:

- online/authenticated measured stability from repeated real plugin runtime corpus runs.
- non-local marketplace publication metadata, if Arbor is later distributed outside this repo-local plugin package.

## Project Initialization

Initialize a project with:

```bash
python3 skills/arbor/scripts/init_project_memory.py --root <project-root>
python3 skills/arbor/scripts/register_project_hooks.py --root <project-root>
```

Expected project-local files:

- `<project-root>/AGENTS.md`
- `<project-root>/.codex/memory.md`
- `<project-root>/.codex/hooks.json`

## Hook Execution

The project hook contract registers:

- `arbor.session_startup_context`
- `arbor.in_session_memory_hygiene`
- `arbor.goal_constraint_drift`

Registered hooks resolve `${PROJECT_ROOT}` and execute Arbor skill scripts against that project root. The scripts emit context packets; the running agent decides whether to edit memory or `AGENTS.md`.

Representative direct commands:

```bash
python3 skills/arbor/scripts/run_session_startup_hook.py --root <project-root>
python3 skills/arbor/scripts/run_memory_hygiene_hook.py --root <project-root>
python3 skills/arbor/scripts/run_agents_guide_drift_hook.py --root <project-root>
```

## Validation Snapshot

Latest release gate:

- plugin install validation with `--codex-probe`: passed;
- Codex CLI marketplace add for `arbor-local`: passed;
- packaged payload inventory: 13/13 expected files, `matches_expected_payload=true`;
- packaged skill smoke: initialized `AGENTS.md` and `.codex/memory.md`;
- packaged hook smokes: all three Arbor hooks passed;
- standalone skill validation: passed;
- packaged plugin skill validation: passed;
- full unit suite: 186 tests passed;
- `py_compile`: passed;
- `ruff`: passed;
- plugin manifest, hook config, and marketplace JSON validation: passed;
- `git diff --check`: passed.

Latest authenticated full-corpus runtime validation:

- full 150-scenario `plugin-runtime-codex-exec` corpus: 150/150 scenarios passed;
- selected hook executions: 111/111 passed;
- runtime availability gate: passed, no blockers;
- hook execution gate: passed, no assertion failures;
- outside-root leaks: 0;
- unintended writes: 0;
- semantic metrics: reported and passed;
- none false-positive rate: 0.0;
- near-miss false-positive rate: 0.0;
- multi-hook required recall: 1.0.

Latest authenticated runtime-probe validation:

- isolated marketplace add: passed;
- explicit auth copy from `--auth-source-home`: passed;
- local `arbor@arbor-local` plugin cache materialization: passed;
- isolated plugin enable: passed;
- isolated project trust: passed;
- true `$arbor` injection in direct `codex exec`: observed;
- runtime side-effect gate: blocked because headless `codex exec` rejects project `.codex` writes in this environment;
- focused runtime-probe and trigger-adapter tests: 22 tests passed;
- focused `py_compile`: passed;
- focused `ruff`: passed.

Prior closure validation:

- full unit suite: 140 tests passed;
- standalone skill validation: passed;
- packaged plugin skill validation: passed;
- Python compile check: passed;
- full-corpus hook execution report: 150/150 scenarios passed;
- selected hook executions: 103/103 passed;
- outside-root leaks: 0;
- unintended writes: 0;
- prior sandbox runtime smoke through `plugin-runtime-codex-exec`: passed with a classified `network_unavailable` blocker;
- repeated `plugin-runtime-stub` corpus smoke: passed with stability withheld because labels are not real runtime labels; compact rows include `optional_args` for replay.
- plugin install validation reports 13 packaged files, confirms `matches_expected_payload=true`, and rejects transient artifacts, symlinks, unsupported entries, unexpected directories, or unexpected file drift.
- total coverage: 88%.

Commands run:

```bash
python3 -m unittest tests/test_arbor_skill.py
python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor
python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor
env PYTHONPYCACHEPREFIX=/private/tmp/arbor-stage-b-pycache python3 -m py_compile skills/arbor/scripts/init_project_memory.py skills/arbor/scripts/collect_project_context.py skills/arbor/scripts/register_project_hooks.py skills/arbor/scripts/run_session_startup_hook.py skills/arbor/scripts/run_memory_hygiene_hook.py skills/arbor/scripts/run_agents_guide_drift_hook.py scripts/eval_fixtures.py scripts/simulated_dispatcher.py scripts/plugin_trigger_adapters.py scripts/evaluate_hook_triggers.py scripts/validate_plugin_install.py scripts/probe_plugin_runtime.py tests/test_arbor_skill.py
conda run -n arbor python -m ruff check . --no-cache
python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-stage-b-corpus-sidecar --trigger-adapter sidecar-baseline
python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-stage-b-repeat-stub --trigger-adapter plugin-runtime-stub --repeat-runs 2
python3 scripts/evaluate_hook_triggers.py --scenario-id H1-P001 --work-root /private/tmp/arbor-stage-b-runtime-smoke --trigger-adapter plugin-runtime-codex-exec
env PYTHONPYCACHEPREFIX=/private/tmp/arbor-stage-b-install-pycache python3 scripts/validate_plugin_install.py
env COVERAGE_FILE=/private/tmp/arbor-stage-b-coverage conda run -n arbor python -m coverage run -m unittest tests/test_arbor_skill.py
env COVERAGE_FILE=/private/tmp/arbor-stage-b-coverage conda run -n arbor python -m coverage report
```

## Full-Corpus Report

Run the sidecar-backed full-corpus harness with:

```bash
python3 scripts/evaluate_hook_triggers.py --all --work-root /private/tmp/arbor-final-corpus
```

The report is intentionally sidecar-backed. It validates fixture generation, dispatcher-contract plumbing, project-local hook registration, hook execution, no-write assertions, and outside-root rejection. It does not validate natural-language semantic dispatch accuracy.

## Stage B Review

Review the completed plugin/runtime trigger evaluation layer with:

```bash
docs/reviews/stage-b-plugin-runtime-final-review.md
```

This review entry covers Feature 13-20 as one stage: plugin installability, non-circular runtime input, runtime blocker gating, semantic metric reporting, repeated-run stability, release boundary, and online/authenticated runtime validation commands.

## Plugin Runtime Probe

Check installed-plugin reachability without running a model:

```bash
python3 scripts/probe_plugin_runtime.py
```

Attempt a real installed `$arbor` run when the environment has Codex network/model access:

```bash
python3 scripts/probe_plugin_runtime.py --attempt-exec --auth-source-home ~ --timeout 90
```

In the current authenticated runtime, marketplace add, auth copy, plugin cache materialization, plugin enable, project trust, and true `$arbor` injection succeed. The remaining blocker is headless `codex exec` refusing project `.codex` writes, so `.codex/memory.md` and `.codex/hooks.json` side-effect gates remain blocked.

## Release Verification

Run the current release gate with:

```bash
python3 scripts/validate_plugin_install.py --codex-probe
python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/arbor
python3 /Users/shawn/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/arbor/skills/arbor
python3 -m unittest tests/test_arbor_skill.py
conda run -n arbor python -m ruff check . --no-cache
```

Reproduce the retained authenticated full-corpus runtime validation with:

```bash
python3 scripts/evaluate_hook_triggers.py \
  --all \
  --work-root /private/tmp/arbor-runtime-corpus \
  --trigger-adapter plugin-runtime-codex-exec \
  --auth-source-home ~ \
  --runtime-timeout 300 \
  --progress-jsonl /private/tmp/arbor-runtime-corpus-progress.jsonl \
  --report-json /private/tmp/arbor-runtime-corpus-report.json
```

## Latest Real Runtime Full Corpus

Feature 25 now has a retained full authenticated installed-plugin runtime corpus through `plugin-runtime-codex-exec`:

- report artifact: `docs/reviews/artifacts/feature-25-full-corpus-r4-report.json`;
- progress artifact: `docs/reviews/artifacts/feature-25-full-corpus-r4-progress.jsonl`;
- execution chain: 150/150 scenarios passed;
- hook execution: 111/111 selected hook executions passed;
- adapter contract gate: passed with 0 adapter errors;
- runtime availability gate: passed with 0 blockers;
- hook execution gate: passed with 0 assertion failures, 0 outside-root leaks, and 0 unintended writes;
- semantic trigger metrics: reported and passed;
- per-hook precision/recall: 1.0/1.0 for startup, memory hygiene, and AGENTS drift;
- `NONE` and near-miss false-positive rates: 0.0;
- multi-hook required recall: 1.0.

Round 1 focused replay fixed the four known semantic misses (`CL-P020`, `EV-P010`, `H1-P013`, and `H3-P017`). Round 2 full-corpus replay confirmed those fixes generalized across the complete 150-scenario corpus. Stability remains intentionally unreported because it requires repeated full real-runtime runs.
