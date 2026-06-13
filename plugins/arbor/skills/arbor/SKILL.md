---
name: arbor
description: "Use when initializing or checking Arbor-created project framework files and runtime hook surfaces: AGENTS.md, .arbor/memory.md, CLAUDE.md, Codex project hooks, Claude project hooks, or shared hook adapters; not for project summaries, resume status, migration advice, or general maintenance."
---

# Arbor

## Core Rule

Arbor is a context reliability layer. It initializes and checks only
Arbor-created or Arbor-managed project files and hook registration surfaces.

Use Arbor for:

- project initialization;
- framework checks;
- safe explicit framework repair;
- project hook diagnosis;
- startup context loading;
- short-term memory hygiene;
- conservative `AGENTS.md` Project Map support.

Do not use Arbor as a project-summary command, project-status command,
subjective health report, migration advisor, broad maintenance report, planning
method, implementation method, review method, or branch-finishing policy.
Ordinary questions such as "what does this repo do?", "where were we?", or
"what should I do next?" should use injected SessionStart context when present,
then answer directly from project sources unless the user also asks to
initialize Arbor or run an Arbor framework check.

## Startup Workflow

When initializing, resuming, or checking Arbor state in a project:

1. Ensure `AGENTS.md`, `.arbor/memory.md`, and the current runtime's bootstrap
   files exist. Use `scripts/init_project_memory.py --root <project-root>` when
   useful. Existing `AGENTS.md` and `.arbor/memory.md` must be preserved.
2. Initialize project hooks through the current runtime's project surface. Use
   `scripts/diagnose_project_hooks.py --root <project-root> --plugin-root
   <arbor-plugin-root>` when hook state is unclear. On Codex, use
   `scripts/register_project_hooks.py --root <project-root> --runtime codex`.
   On Claude Code, use the same script with `--runtime claude`. Use
   `--runtime both` only when both project hook surfaces are intentionally
   requested.
3. Confirm the project SessionStart hook is the normal startup path. Its
   deterministic context packet loads:
   - `AGENTS.md`
   - formatted `git log`
   - `.arbor/memory.md`
   - `git status`
4. Use `scripts/collect_project_context.py --root <project-root>` when hooks
   are unavailable or a deterministic ordered context packet is useful.
5. Read additional project files only when the user request requires them.

On Codex, project hooks may be skipped until the user trusts them through
`/hooks`. `AGENTS.md` remains the durable project guide and fallback map, not
proof that startup context was injected.

On Claude Code, `CLAUDE.md` is a short bridge to the canonical Arbor files. A
project initialized from Codex still needs Claude initialization to create
`.claude/settings.json`, `.claude/hooks/`, and `CLAUDE.md`.

## Visible Output Boundary

Visible `$arbor` output is a minimal deterministic framework check report.
Default `$arbor` runs in detect-only mode and does not mutate files unless the
user explicitly asks for framework repair.
For automation, add `--strict`; strict mode keeps the same visible report but
exits nonzero unless the final `Result` is `pass`.

Normal `$arbor` output must come from:

```bash
scripts/run_framework_check.py --root <project-root> --plugin-root <arbor-plugin-root>
```

Use this exact shape if a fallback report is required:

```markdown
**Arbor Framework Check**
Project root: ...
Mode: detect-only
Runtime: codex|claude|both

| Surface | Required | Status | Evidence | Repair |
| --- | --- | --- | --- | --- |
| AGENTS.md | yes | pass | ... | none |
| .arbor/memory.md | yes | pass | ... | none |
| CLAUDE.md | no | not_applicable | ... | none |
| .codex/hooks.json + .codex/hooks/ | yes | missing | ... | run register_project_hooks.py --runtime codex |
| .claude/settings.json + .claude/hooks/ | no | not_applicable | ... | none |
| shared hook adapters | yes | pass | ... | none |

Result: pass|needs_repair|blocked
```

Allowed `Status` values are lowercase only: `pass`, `fail`, `missing`, `drift`,
`blocked`, and `not_applicable`.
Allowed `Required` values are lowercase only: `yes` and `no`.
Allowed `Result` values are lowercase only: `pass`, `needs_repair`, and
`blocked`.

The normal framework check includes only these surfaces:

- `AGENTS.md`
- `.arbor/memory.md`
- `CLAUDE.md`
- `.codex/hooks.json + .codex/hooks/`
- `.claude/settings.json + .claude/hooks/`
- `shared hook adapters`

Do not include normal `$arbor` rows or sections for git history, project
summary, broad project health, maintenance advice, migration plans, product
status, memory resume summaries, subjective recommendations, or unrelated local
state.

## Framework Repair Mode

Run repair mode only when the user explicitly asks Arbor to repair or fix the
framework setup, or when the user selects a repair path from a detect-only
report. Use:

```bash
scripts/run_framework_check.py --mode repair --root <project-root>
```

Pass `--runtime codex`, `--runtime claude`, or `--runtime both` when the target
runtime is explicit. For Claude Code bridge repair, pass `--claude-bridge on`
when the user asked to initialize Claude Code support.

Repair mode may apply only safe, idempotent framework repairs:

- create missing `.arbor/memory.md`;
- create missing `AGENTS.md` from the Arbor template;
- create missing `CLAUDE.md` bridge when Claude support is requested;
- register or refresh Codex `.codex/hooks.json` and `.codex/hooks/` wrappers;
- register or refresh Claude `.claude/settings.json` and `.claude/hooks/`
  wrappers.

Repair mode must not silently apply policy-changing or destructive edits such
as `.gitignore` changes, deleting files, changing runtime trust, recovering
invalid JSON, or rewriting durable user guidance.

After repair, rerun the framework check and report before/after counts plus the
same fixed row table.

## Session Memory

Use `.arbor/memory.md` as the recovery file for current context that a fresh
agent cannot recover from committed history, durable docs, stable project
guidance, and git status alone.
During explicit initialization, legacy `.codex/memory.md` is copied only when
canonical `.arbor/memory.md` is missing and the legacy file is readable UTF-8;
unreadable legacy memory must fail with a concise Arbor error, not a traceback.
Dry-run validates legacy memory readability before reporting that migration
would succeed.
Initialization templates must also be readable UTF-8 package files; missing or
unreadable templates must fail with a concise Arbor error, not a traceback.
During startup context collection, unreadable memory is reported as unreadable
and must not be treated as explicit resume context.

Before adding an item, ask whether closing the session now would make the next
agent lose Arbor-relevant discussion, changed artifact paths, unresolved
decisions, or the first resume action. Remove or shrink items once they are
committed or moved to a durable home. Keep the file short enough to read during
startup.

The Stop hook is a quiet safety net. It may preserve a concise resume pointer
when dirty Arbor-managed state or conversation-only context would otherwise be
lost. It should not create memory churn for clean direct answers, read-only
inspection, or already durable state. A tracked deletion under `.arbor/` still
counts as Arbor-managed state so Stop can recreate `.arbor/memory.md` instead of
silently losing the recovery file. Stop status parsing must use unquoted
porcelain status so spaces or special characters in `.arbor/` paths do not hide
Arbor-managed changes.

## AGENTS.md Management

`AGENTS.md` is the durable project guide and map, not the whole memory store.

It should contain:

- Project Goal;
- Project Constraints;
- Project Map;
- minimal stable runtime notes when project-specific.

It should not contain transient session progress, long design history, review
logs, generic development methodology, copied external docs, or cache notes.

Update `AGENTS.md` only when stable project goals, durable constraints, or
Project Map pointers should change. Project Map primary bullets must be
top-level durable entrypoints only; mention nested modules or files in the
entry descriptions instead of making them separate primary map entries. Put
unresolved current-session state in `.arbor/memory.md`, completed outcomes in
git history, and deeper durable knowledge in project docs.

Use `scripts/run_agents_guide_drift_hook.py --root <project-root>` when
Project Map drift needs an explicit packet. The Stop hook also applies safe
Project Map path maintenance when the current git status includes new durable
top-level entrypoints that are missing from the map or non-canonical nested
primary map entries that should be folded into the top-level map, while still
ignoring artifact directories such as `outputs/`, `tmp/`, caches, and build
outputs.
Clean direct turns should not mutate `AGENTS.md` just because old pre-existing
map drift exists.

## Runtime Entrypoints

Arbor runs the same context layer on Codex and Claude Code, but each runtime has
its own project-local hook surface.

- **Codex** uses project-level executable hooks registered in
  `.codex/hooks.json` with wrappers under `.codex/hooks/` for Arbor startup
  context. Codex may skip untrusted hooks until the user reviews them in
  `/hooks`; `AGENTS.md` remains a project guide and fallback map.
- **Claude Code** reads `CLAUDE.md` natively. Project-level executable hooks
  are registered in `.claude/settings.json` with wrappers under `.claude/hooks/`.
  The bridge points Claude Code back to `AGENTS.md` and `.arbor/memory.md`.

Arbor does not ship plugin-level hook registrations. Uninitialized projects do
not have project-local `.arbor/` state to maintain, and project-level wrappers
are the surface that `$arbor` can diagnose and repair.

## Project Hooks

Project hooks delegate to shared adapter scripts:

- `hooks/session-start` calls `run_session_startup_hook.py` and applies a
  conservative runtime injection budget.
- `hooks/stop-memory-hygiene` calls the Stop context-maintenance path. It may
  refresh `.arbor/memory.md`, apply conservative `AGENTS.md` Project Map path
  maintenance for dirty or transcript-backed recovery context, then block stop
  only when guide quality still fails in that active-maintenance path.

Hook wrappers use the absolute Python interpreter that ran registration. Stale
bare `python` or `python3` wrapper commands are hook drift and should be
repaired by re-registration.
Codex on Windows launches project hooks through `.cmd` files. Launcher paths
without shell-sensitive characters must be emitted unquoted because Codex's
Windows hook runner executes that form reliably; paths with spaces or
shell-sensitive characters must be routed through `cmd.exe /d /c call "..."`.
The launcher itself must quote the absolute Python interpreter and
same-directory wrapper path.
POSIX Claude Code hook commands must prefer `CLAUDE_PROJECT_DIR` and fall back
to `pwd` so wrapper paths stay project-local when the runtime variable is not
available.

Hook diagnosis must compare project wrapper file content with Arbor's current
generated wrapper template. A wrapper that merely exists but has stale or
hand-edited content is hook drift, and repair mode should refresh it by
re-registration. CRLF-versus-LF line-ending differences alone are not hook
drift. Invalid wrapper text encodings count as stale wrapper content rather
than diagnostic crashes, and re-registration must refresh those files from the
current generated template.
Hook configuration files that cannot be read as UTF-8 must be reported as
invalid hook surfaces by diagnosis, not as Python tracebacks. Registration and
repair must fail cleanly on unreadable hook configuration encodings instead of
rewriting or crashing through those files.
Re-registration must be idempotent. Windows wrappers with current content must
not be reported as `chmod` repairs solely because Windows lacks POSIX executable
bits; POSIX wrappers should still receive executable permission repair.
If a registered project wrapper cannot find an installed Arbor plugin cache, it
must soft-skip rather than return a hook failure: SessionStart emits no context,
and Stop emits an allow-stop JSON response. Diagnose or repair hook state after
the session is no longer at risk of being interrupted by a failing hook.
Project wrappers and shared adapters must also ignore plugin-root environment
paths that cannot be inspected, using the next candidate or the packaged adapter
root instead of surfacing a hook failure.
Automatic cache discovery must consider only complete Arbor plugin roots in
`X.Y.Z` version directories. Explicit plugin-root environment overrides may
still point at a local development source for smoke tests, but stale ad hoc
cache directories such as `dev` or incomplete cache copies must be ignored.
Wrappers must apply the same soft-fail behavior if the selected cache adapter
exits nonzero. Failed adapter diagnostics belong in Arbor diagnosis, not in a
runtime hook failure.
Wrappers must also bound adapter execution with an internal timeout, configurable
for tests through `ARBOR_HOOK_ADAPTER_TIMEOUT_SECONDS`, and soft-fail on timeout
or adapter discovery or launch failure.
The SessionStart adapter must bound startup helper execution, configurable for
tests through `ARBOR_SESSION_START_INTERNAL_TIMEOUT_SECONDS`; startup helper
timeouts or launch failures soft-skip without injecting partial context.
The Stop adapter must also bound internal git probes and guide-quality checks,
configurable for tests through `ARBOR_STOP_INTERNAL_TIMEOUT_SECONDS`; git probes
and guide checks that time out or fail to start soft-skip rather than hanging or
blocking Stop. In block mode, block-mode memory helper timeouts or launch
failures must emit the normal allow-stop response.
Stop wrappers must validate successful adapter stdout before passing it to the
runtime. Empty or non-JSON Stop output must fall back to allow-stop JSON.
Project wrappers must not pass successful adapter stderr through to the
runtime; diagnostics belong in Arbor diagnosis, and hook stdout is the only
success output channel.
Hook diagnosis must bound shared-adapter probe execution, configurable for tests
through `ARBOR_HOOK_ADAPTER_PROBE_TIMEOUT_SECONDS`, and report probe timeouts or
launch failures as `shared-adapters-probe-failed` rather than hanging or
crashing framework checks.
Hook diagnosis must reject incomplete `--plugin-root` directories before
probing shared adapters; the root must include the Codex manifest, Claude
manifest, and Arbor skill so diagnosis matches wrapper cache-selection rules.
SessionStart startup-context git probes must be bounded, configurable for tests
through `ARBOR_STARTUP_GIT_TIMEOUT_SECONDS`; a timed-out or failed-to-start git
command should mark only that context section as failed so readable file context
can still be injected.
The quality hard gate must bound each subprocess check, configurable for tests
through `ARBOR_QUALITY_GATE_TIMEOUT_SECONDS`, so a stuck child check fails a row
instead of hanging the workflow. Subprocess launch failures must also fail the
affected row with a readable diagnostic instead of crashing the gate.
The skill package checker must bound each `quick_validate.py` invocation,
configurable for tests through `ARBOR_SKILL_PACKAGE_TIMEOUT_SECONDS`, so direct
skill validation cannot hang outside the hard gate. Validator launch failures
must be reported as normal skill package failures instead of Python tracebacks.
The release readiness gate must also bound subprocess checks, configurable for
tests through `ARBOR_RELEASE_READINESS_TIMEOUT_SECONDS`, so install-state or
runtime-evidence checks cannot hang publishability decisions. Subprocess launch
failures must fail the affected row with a readable diagnostic instead of
crashing the gate. The published source `git status` check is part of that
bounded release-readiness surface. Source manifests must be JSON objects.
Direct install-state checks must bound their own git probes, configurable for
tests through `ARBOR_INSTALL_STATE_GIT_TIMEOUT_SECONDS`, so dirty-source
inspection cannot hang or crash when git fails to start outside release
readiness. Source or cache digest failures are reported as install-state drift,
not as tracebacks.
Local plugin cache sync must bound its git dirty-source and commit probes,
configurable for tests through `ARBOR_CACHE_SYNC_GIT_TIMEOUT_SECONDS`, so cache
publishing cannot hang or crash while inspecting source state.
The context boundary check must read published text files as UTF-8 only. Invalid
UTF-8 is a package-boundary failure, not a cue to fall back to a platform
default encoding. Published JSON surfaces must be JSON objects, so manifests and
marketplace files cannot pass as arrays, strings, or other JSON shapes.

Project wrappers and hook adapters ignore incomplete plugin-root environment
values unless they point to a full Arbor plugin root with Codex and Claude
manifests plus `skills/arbor/SKILL.md`. Hook adapters also soft-skip empty
probe payloads so hook UIs can validate commands without reporting false
failures.

## Resources

- `references/memory-template.md`: template for `.arbor/memory.md`
- `references/agents-template.md`: template for `AGENTS.md`
- `references/claude-template.md`: bridge template for `CLAUDE.md`
- `references/project-hooks-template.md`: project hook contract
- `references/runtime-smoke-template.md`: release-time runtime smoke evidence
  template
- `scripts/init_project_memory.py`: create missing project memory files without
  overwriting existing files
- `scripts/collect_project_context.py`: collect startup context in the required
  order
- `scripts/run_session_startup_hook.py`: execute startup context loading
- `scripts/run_memory_hygiene_hook.py`: emit memory hygiene context
- `scripts/run_agents_guide_drift_hook.py`: emit `AGENTS.md` drift context
- `scripts/run_framework_check.py`: render the deterministic Arbor framework
  check and apply explicit safe repair mode
- `scripts/sync_local_plugin_cache.py`: sync committed plugin source to local
  runtime caches; requires matching `X.Y.Z` Codex and Claude source manifest
  versions, refuses dirty plugin source unless explicitly overridden for local
  development, rejects sources outside the repository, refuses sync targets
  inside the source tree, stages cache copies before replacing installed cache
  directories, preserves the existing installed cache if staging copy or final
  replacement fails, refreshes cached adapters and removes legacy plugin-level
  hook manifests only in `X.Y.Z` release cache directories, and verifies synced
  targets after writing
- `scripts/check_cache_sync_adapters.py`: run cache-sync adapter validation as
  a separate module so installed-cache behavior can evolve independently
- `scripts/check_agents_guide_quality.py`: validate `AGENTS.md` guide shape and
  Project Map usefulness
- `scripts/diagnose_project_hooks.py`: classify Codex and Claude hook surfaces
- `scripts/register_project_hooks.py`: create or update Codex and Claude project
  hook wrappers
- `scripts/check_context_boundary.py`: ensure only the context layer is
  published
- `scripts/check_install_state.py`: report whether local Arbor plugin caches
  match the source plugin without mutating them; use `--strict` for release
  automation, `X.Y.Z` source-version enforcement, dirty-source protection, and
  `--runtime codex|claude|both` for targeted runtime smoke; selected-cache
  reporting mirrors project wrappers by considering only complete Arbor plugin
  roots in `X.Y.Z` release cache directories; digest read failures become drift
  evidence rather than tracebacks
- `scripts/check_plugin_adapters.py`: validate shared hook adapters and project
  hook registration behavior
- `scripts/check_project_wrapper_smoke.py`: run repeatable local smoke checks
  for generated Codex and Claude project wrappers through explicit plugin-root
  and fake installed-cache discovery paths; fake cache directories must use
  the source manifest `X.Y.Z` version rather than a hardcoded release, and
  smoke must cover non-release cache ignore behavior, incomplete
  higher-version cache fallback, and bad plugin-root environment fallback;
  smoke subprocess launch failures or timeouts must be readable failures;
  `ARBOR_PROJECT_WRAPPER_SMOKE_TIMEOUT_SECONDS` may shorten the smoke
  subprocess timeout for tests or CI
- `scripts/check_project_wrapper_smoke_adapters.py`: run wrapper-smoke adapter
  contract validation as a separate module before or during broader adapter
  checks
- `scripts/check_python_syntax.py`: validate Arbor Python sources without
  writing bytecode artifacts; extensionless hook adapters with invalid UTF-8
  must fail validation rather than be skipped
- `scripts/check_source_hygiene.py`: validate published text source hygiene,
  including untracked files, before relying on `git diff --check`
- `scripts/check_quality_gate.py`: run the deterministic Arbor v2 hard gate
- `scripts/check_runtime_smoke_evidence.py`: validate filled runtime smoke
  evidence before treating it as release proof; any passing Fired marker
  requires runtime trust, absolute Python wrapper-or-launcher proof, absolute local cache path,
  and evidence; the runtime matrix must include exactly one row for each
  template matrix entry with no extra runtime rows; audit metadata and required
  sections must each appear exactly once; release readiness also requires Codex
  and Claude source manifests to agree on an `X.Y.Z` release version, Codex and
  Claude marketplace source paths to point at the plugin root under release,
  then requires the evidence `Version:` and `Commit:` to match the source under
  release; unreadable evidence files fail with concise diagnostics
- `scripts/check_runtime_smoke_evidence_adapters.py`: run runtime-smoke
  evidence contract validation as a separate module before or during broader
  adapter checks
- `scripts/check_skill_packages.py`: validate published Arbor skill packages
