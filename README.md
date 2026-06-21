# Arbor

Arbor is a lightweight project-context plugin for Codex and Claude Code.

It helps agents enter a repository with the same dependable context each time:

- `AGENTS.md`: durable project guide and map.
- `.arbor/memory.md`: short-term unresolved session memory.
- `CLAUDE.md`: Claude Code bridge to `AGENTS.md` and `.arbor/memory.md`.
- hookless runtime contract: startup and finalization instructions appended to
  `AGENTS.md`.
- optional project hooks: explicit legacy repair and diagnosis surface only.

Arbor does not provide a development methodology. Planning, debugging, review,
branch finishing, and implementation workflows should be handled by the user's
preferred tools, such as Superpowers.

## Install

### Codex

```bash
codex plugin marketplace add shawnyin128/arbor
codex plugin add arbor@arbor
```

If `codex` is not on your macOS `PATH`:

```bash
/Applications/Codex.app/Contents/Resources/codex plugin marketplace add shawnyin128/arbor
/Applications/Codex.app/Contents/Resources/codex plugin add arbor@arbor
```

SSH:

```bash
codex plugin marketplace add git@github.com:shawnyin128/arbor.git
codex plugin add arbor@arbor
```

Upgrade or remove:

```bash
codex plugin marketplace upgrade arbor
codex plugin add arbor@arbor
codex plugin remove arbor@arbor
codex plugin marketplace remove arbor
```

`codex plugin marketplace add` and `codex plugin marketplace upgrade` manage
the marketplace snapshot only. `codex plugin add arbor@arbor` installs or
refreshes the Arbor plugin from that snapshot into Codex's plugin cache. Restart
or reload Codex surfaces such as VS Code after installing or upgrading so new
sessions load the refreshed skill package.

### Claude Code

Inside Claude Code:

```text
/plugin marketplace add shawnyin128/arbor
/plugin install arbor@arbor
/reload-plugins
```

After installing the Claude plugin, run Arbor initialization in the project so
`AGENTS.md`, `.arbor/memory.md`, and the optional `CLAUDE.md` bridge exist.

## Skill

Arbor publishes one skill:

```text
Codex   Claude Code      Purpose
$arbor  /arbor:arbor     initialize, hookless startup/finalization, checks
```

Use it for:

- initializing `AGENTS.md` and `.arbor/memory.md`;
- appending the Arbor hookless runtime contract to an existing `AGENTS.md`;
- creating the `CLAUDE.md` bridge for Claude Code;
- running hookless framework checks for project-local Arbor files;
- running explicit safe repairs for missing Arbor framework files.

`$arbor` is not a project summary, project status report, resume summary, health
assessment, migration report, or maintenance advisor. For ordinary questions
such as "what does this project do?" or "where were we?", use the hookless
startup packet when the project contract requires it; otherwise read
`AGENTS.md`, `.arbor/memory.md`, and git status directly from project sources.

The normal `$arbor` output is detect-only and comes from
`plugins/arbor/skills/arbor/scripts/run_framework_check.py` when available. It
uses one strict table with `Surface`, `Required`, `Status`, `Evidence`, and
`Repair`, followed by one `Result:` line.

The framework check only covers Arbor-created or Arbor-managed surfaces:

- `AGENTS.md`
- `.arbor/memory.md`
- `CLAUDE.md`

Safe repair mode is explicit and limited to creating missing Arbor state files,
appending the missing hookless runtime contract, and creating the Claude bridge
when requested. Legacy hook diagnosis or repair requires an explicit hook path
and is not part of the default check. Arbor does not silently delete files,
change repository policy, repair invalid JSON, assert runtime trust, or rewrite
user-authored project guidance.

## Startup Context

Fresh and resumed sessions should recover Arbor context from project-local
files by running:

```bash
python3 <arbor-skill-root>/scripts/run_session_startup_hook.py --root /path/to/project
```

Use a direct Python executable for Arbor context helpers. On Windows, do not
wrap these commands in `conda run`; it can recode captured stdout and corrupt
large UTF-8 context packets. If `python` is not on PATH, call the absolute
interpreter directly, such as `<conda-base>/python.exe`.

The deterministic recovery order is:

1. `AGENTS.md`
2. recent formatted git history
3. `.arbor/memory.md`
4. `git status --short`

`AGENTS.md` is the durable project guide and Project Map. Arbor initialization
preserves existing user content and appends a protected hookless runtime
contract so future agents know to run the startup packet. Do not treat
`.codex/hooks.json` as proof that startup context has already been loaded,
because legacy Codex hooks still require runtime trust.

`<arbor-skill-root>` is the installed Arbor skill package directory, such as
`~/.codex/plugins/cache/arbor/arbor/<version>/skills/arbor` on Codex. The
runtime helpers are package resources; they are not expected under the target
project's `scripts/` directory.

`CLAUDE.md` is the native Claude Code bridge. It should stay short and point to
the canonical Arbor files instead of duplicating the full project guide.

## Finalization

Before the final response for a non-trivial task, handoff, or dirty-worktree
turn, run:

```bash
python3 <arbor-skill-root>/scripts/run_hookless_finalization.py --root /path/to/project
```

This is the hookless replacement for Arbor's old Stop hook. It first executes
the same quiet maintenance adapter used by the legacy Stop wrapper, so dirty
Arbor-managed state can still refresh `.arbor/memory.md` and newly added durable
top-level entrypoints can still repair the `AGENTS.md` Project Map. It then
renders memory hygiene and AGENTS drift context so the agent can explain or
complete any remaining update. Clean direct turns should not create memory
churn.

## Memory

`.arbor/memory.md` is short-term recovery memory, not a project database.

Use it for unresolved context that a new agent could not recover from
`AGENTS.md`, git history, durable docs, and current git status alone:

- unfinished local work;
- important files or artifacts to inspect next;
- unresolved decisions;
- the first action a resumed session should take.

Do not use it for committed history, stable project rules, long review evidence,
release logs, or one-off answers. Once a commit or durable document captures the
state, prune or shrink memory so startup stays fast and useful.
Startup context treats unreadable memory as recovery damage, not resume content:
unreadable memory is reported as unreadable and must not be treated as explicit
resume context.

## Legacy Hook Support

Arbor's default path is hookless. It does not require Codex `/hooks` trust and
does not create `.codex/` or `.claude/` hook surfaces during normal framework
checks or repair.

Legacy hook diagnosis and repair are still available for projects that already
depend on Arbor's old `SessionStart` and `Stop` wrappers. To include those
surfaces in the framework report, pass `--include-hooks`:

```bash
python3 plugins/arbor/skills/arbor/scripts/run_framework_check.py \
  --root /path/to/project \
  --plugin-root plugins/arbor \
  --runtime both \
  --include-hooks
```

To repair legacy project hooks explicitly, add repair mode:

```bash
python3 plugins/arbor/skills/arbor/scripts/run_framework_check.py \
  --root /path/to/project \
  --plugin-root plugins/arbor \
  --runtime both \
  --mode repair \
  --include-hooks
```

When hook state is unclear, use the diagnostic directly:

```bash
python3 plugins/arbor/skills/arbor/scripts/diagnose_project_hooks.py \
  --root /path/to/project \
  --plugin-root plugins/arbor
```

Legacy diagnosis distinguishes stale intent-only Codex files, executable
wrapper state, shared adapter state, project-level Claude hooks, legacy
plugin-level hook drift, and Codex trust gaps. File presence is not proof that
a runtime fired a hook. Hook configuration files that cannot be read as UTF-8
are reported as invalid hook surfaces. Registration and repair also fail
cleanly on unreadable hook configuration encodings.

Legacy wrappers keep the old safety properties: plugin-root environment paths
that cannot be inspected are ignored; wrapper execution applies a soft-fail
policy on timeout, adapter discovery failure, or adapter launch failure; startup
helper timeouts or launch failures do not inject partial context; git probes
and guide checks that time out or fail to start do not block Stop; and
block-mode memory helper timeouts or launch failures emit the normal allow-stop
response. Diagnosis rejects incomplete `--plugin-root` directories before
probing shared adapters and reports probe timeouts or launch failures as
`shared-adapters-probe-failed`.

## Validation

### Scenario Gate

Offline hookless scenario checks are the default validation path for Arbor
context-core changes:

```bash
python3 plugins/arbor/skills/arbor/scripts/check_hookless_trigger_contract.py
```

Real Codex scenarios are explicit slow tests and do not run by default:

```bash
python3 plugins/arbor/skills/arbor/scripts/check_codex_hookless_trigger_scenarios.py \
  --run-codex \
  --repeat 2 \
  --evidence-dir docs/scenario-evidence/YYYY-MM-DD
```

Run the real Codex scenarios when a change deletes, replaces, or rewrites the
hookless context path; changes the `AGENTS.md`, `.arbor/memory.md`, or
`CLAUDE.md` protocol; changes `$arbor` visible output or trigger wording;
changes init, recover, status, or doctor behavior; or changes the scenario
harness. Use the final rationale JSON, project side effects, and JSONL evidence
to debug why the agent chose a context chain.

### Source Gate

Run the full deterministic hard gate before publishing:

```bash
python3 plugins/arbor/skills/arbor/scripts/check_quality_gate.py
```

The hard gate is the source-ready quality contract. It checks package
boundaries, Python syntax without bytecode artifacts, source hygiene for
tracked and untracked published text files, diff hygiene, skill resource links,
marketplace paths, hookless framework behavior, explicit legacy hook behavior,
install/cache tooling, and the Arbor framework report. It also asserts that
only the lightweight `arbor` skill is published and that plugin-level hook
registrations are absent.

For focused checks after package, manifest, README, context-boundary, or legacy
hook changes:

```bash
python3 plugins/arbor/skills/arbor/scripts/check_context_boundary.py
python3 plugins/arbor/skills/arbor/scripts/check_project_wrapper_smoke.py
python3 plugins/arbor/skills/arbor/scripts/check_project_wrapper_smoke_adapters.py
python3 plugins/arbor/skills/arbor/scripts/check_runtime_smoke_evidence_adapters.py
python3 plugins/arbor/skills/arbor/scripts/check_plugin_adapters.py
python3 plugins/arbor/skills/arbor/scripts/check_skill_packages.py
```

Python syntax validation treats invalid UTF-8 hook adapter sources as failures,
including extensionless adapter files, rather than skipping them. The context
boundary check reads published text files as UTF-8 only. Published JSON surfaces
must be JSON objects, so manifests and marketplace files cannot pass the
boundary check as arrays, strings, or other JSON shapes. Source manifests must
be JSON objects.

The quality hard gate bounds each subprocess check through
`ARBOR_QUALITY_GATE_TIMEOUT_SECONDS`. Subprocess launch failures also fail the
affected row with a readable diagnostic. The skill package checker also bounds
each `quick_validate.py` invocation through
`ARBOR_SKILL_PACKAGE_TIMEOUT_SECONDS`. Validator launch failures are
reported as normal skill package failures.

### Release And Install Checks

Run the release readiness gate before publishing or claiming installed runtime
readiness:

```bash
python3 plugins/arbor/skills/arbor/scripts/check_release_readiness.py --runtime-smoke-evidence path/to/evidence.md
```

The release readiness gate adds installed-runtime proof. It requires matching
Codex and Claude Code source manifest versions in `X.Y.Z` release form, a clean
published source surface, Codex and Claude marketplace source paths that point
at the plugin root under release, the source hard gate, strict install-state
checks for Codex and Claude Code caches, and a validated runtime smoke evidence
file. A passing hard gate alone is not proof of installed runtime behavior.

Runtime smoke evidence records its own validator command passing. It must keep
the full Codex and Claude Code event matrix for Windows and macOS/Linux: exactly
one row for each template matrix entry and no extra runtime rows. Fired rows
must include runtime trust proof, absolute Python wrapper-or-launcher proof,
and the absolute local cache path that supplied the hook adapter. Its `Commit:`
must match the release source `HEAD` and be a 7-or-more-character hexadecimal
git commit prefix or full hash; its `Date:` must use `YYYY-MM-DD`; and
`Operator:` must stay filled for auditability by identifying the operator.

Validate filled runtime smoke evidence with:

```bash
python3 plugins/arbor/skills/arbor/scripts/check_runtime_smoke_evidence.py path/to/evidence.md
```

Before runtime smoke, compare installed caches with source without mutating
them:

```bash
python3 plugins/arbor/skills/arbor/scripts/check_install_state.py
python3 plugins/arbor/skills/arbor/scripts/check_install_state.py --strict
```

For single-runtime smoke, narrow the check:

```bash
python3 plugins/arbor/skills/arbor/scripts/check_install_state.py --runtime codex --strict
python3 plugins/arbor/skills/arbor/scripts/check_install_state.py --runtime claude --strict
```

Strict mode also refuses non-`X.Y.Z` source manifest versions and dirty plugin
source even when caches match the source tree. Install-state selected-cache
reporting mirrors project wrappers: only complete Arbor plugin roots in
`X.Y.Z` release cache directories are candidates. Automatic cache discovery
considers only complete Arbor plugin roots in `X.Y.Z` release directories, so
stale `dev` directories and incomplete cache copies are ignored. Source or
cache digest failures are reported as install-state drift, not as tracebacks.

Drift, missing caches, dirty source, or `not run` install-state checks mean the
runtime evidence is not yet publishable. Local plugin cache sync also requires
matching `X.Y.Z` Codex and Claude source manifest versions. Local plugin cache
sync bounds its git dirty-source and commit probes, refreshes cached hook
adapters and removes legacy plugin-level hook manifests only inside existing
`X.Y.Z` release cache directories, stages cache copies before replacing
installed cache directories, and preserves the existing installed cache if
staging copy or final replacement fails.

Release readiness subprocess launch failures must fail the affected row with a
readable diagnostic. Initialization templates must be readable UTF-8 package
files; missing or unreadable templates fail initialization with a concise Arbor
error instead of a Python traceback.

## Legacy Memory Path

Arbor v0.1 used `.codex/memory.md`. Current Arbor uses `.arbor/memory.md` so
Codex and Claude Code share the same project-local memory. During explicit
initialization, Arbor copies legacy `.codex/memory.md` only when
`.arbor/memory.md` is missing. It does not merge or delete legacy files
automatically. Legacy memory migration requires readable UTF-8 text; unreadable
legacy files fail initialization with a concise error instead of a Python
traceback. Initialization dry-run validates legacy memory readability before
reporting that migration would succeed.

## Version

Current version:

```text
2.0.4
```

Version files:

```text
plugins/arbor/.codex-plugin/plugin.json
plugins/arbor/.claude-plugin/plugin.json
```

Marketplace files:

```text
.agents/plugins/marketplace.json
.claude-plugin/marketplace.json
```
