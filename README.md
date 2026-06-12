# Arbor

Arbor is a lightweight project-context plugin for Codex and Claude Code.

It helps agents enter a repository with the same dependable context each time:

- `AGENTS.md`: durable project guide and map.
- `.arbor/memory.md`: short-term unresolved session memory.
- `CLAUDE.md`: Claude Code bridge to `AGENTS.md` and `.arbor/memory.md`.
- `.codex/hooks.json` and `.codex/hooks/`: Codex project hooks when initialized.
- `.claude/settings.json` and `.claude/hooks/`: Claude Code project hooks when initialized.

Arbor does not provide a development methodology. Planning, debugging, review,
branch finishing, and implementation workflows should be handled by the user's
preferred tools, such as Superpowers.

## Install

### Codex

```bash
codex plugin marketplace add shawnyin128/arbor
```

If `codex` is not on your macOS `PATH`:

```bash
/Applications/Codex.app/Contents/Resources/codex plugin marketplace add shawnyin128/arbor
```

SSH:

```bash
codex plugin marketplace add git@github.com:shawnyin128/arbor.git
```

Upgrade or remove:

```bash
codex plugin marketplace upgrade arbor
codex plugin marketplace remove arbor
```

### Claude Code

Inside Claude Code:

```text
/plugin marketplace add shawnyin128/arbor
/plugin install arbor@arbor
/reload-plugins
```

After installing the Claude plugin, run Arbor initialization in the project so
Claude project hooks are written under `.claude/`. The initialized hooks include
`SessionStart` startup context and quiet `Stop` context maintenance.

## Skill

Arbor publishes one skill:

```text
Codex   Claude Code      Purpose
$arbor  /arbor:arbor     initialize, framework checks, hook diagnosis, safe repair
```

Use it for:

- initializing `AGENTS.md`, `.arbor/memory.md`, and runtime-specific adapters;
- registering Codex project hooks in `.codex/hooks.json` with wrappers under
  `.codex/hooks/`;
- registering Claude Code project hooks in `.claude/settings.json` with wrappers
  under `.claude/hooks/`;
- creating the `CLAUDE.md` bridge for Claude Code;
- checking shared hook adapters used by project-level wrappers;
- running explicit safe repairs for missing Arbor framework files.

`$arbor` is not a project summary, project status report, resume summary, health
assessment, migration report, or maintenance advisor. For ordinary questions
such as "what does this project do?" or "where were we?", use injected startup
context when present and answer directly from project sources.

The normal `$arbor` output is detect-only and comes from
`plugins/arbor/skills/arbor/scripts/run_framework_check.py` when available. It
uses one strict table with `Surface`, `Required`, `Status`, `Evidence`, and
`Repair`, followed by one `Result:` line.

The framework check only covers Arbor-created or Arbor-managed surfaces:

- `AGENTS.md`
- `.arbor/memory.md`
- `CLAUDE.md`
- Codex project hooks
- Claude Code project hooks
- shared hook adapters

Safe repair mode is explicit and limited to creating missing Arbor state files,
creating the Claude bridge when requested, and registering or refreshing Codex
or Claude project hook wrappers. Arbor does not silently delete files, change
repository policy, repair invalid JSON, assert runtime trust, or rewrite
user-authored project guidance.

## Startup Context

Fresh and resumed sessions normally receive Arbor context from the project
`SessionStart` hook. The deterministic startup packet loads:

1. `AGENTS.md`
2. recent formatted git history
3. `.arbor/memory.md`
4. `git status --short`

`AGENTS.md` is the durable project guide and Project Map, not the primary
startup protocol. Do not treat `.codex/hooks.json` as proof that startup
context has already been injected, because Codex hooks still require runtime
trust. If hooks are unavailable, use `AGENTS.md` as the map and inspect
`.arbor/memory.md` plus git status before answering resume questions.

`CLAUDE.md` is the native Claude Code bridge. It should stay short and point to
the canonical Arbor files instead of duplicating the full project guide.

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

## Hooks

Arbor registers runtime-specific project-local hooks only. It does not ship
plugin-level hook registrations.

Codex initialization writes executable project hooks into target-project
`.codex/hooks.json` plus wrappers under `.codex/hooks/`:

- `SessionStart`: injects startup context for `startup` and `resume`.
- `Stop`: quietly maintains `.arbor/memory.md` recovery notes when Arbor
  context would otherwise be hard to resume, and applies conservative
  `AGENTS.md` Project Map drift when current git status shows new durable
  top-level entrypoints. Output/artifact directories such as `outputs/`, `tmp/`,
  caches, and build outputs are ignored. A tracked deletion under `.arbor/`
  still counts as Arbor-managed state so Stop can recreate the recovery file
  before the session ends. Arbor reads unquoted porcelain status, so spaces or
  special characters in `.arbor/` paths do not hide Arbor-managed changes from
  Stop.

Claude Code initialization writes executable project hooks into
`.claude/settings.json` plus wrappers under `.claude/hooks/` with the same
shared adapter behavior.

Project hook wrappers use the absolute Python interpreter that ran Arbor
registration instead of assuming bare `python` or `python3` is available in the
runtime hook environment. Hook adapters soft-skip empty probe payloads so hook
UIs can validate commands without false failures.
Codex on Windows launches project hooks through `.cmd` files. Launcher paths
without shell-sensitive characters are emitted unquoted because Codex's Windows
hook runner executes that form reliably; paths with spaces or shell-sensitive
characters are routed through `cmd.exe /d /c call "..."`. The launcher itself
quotes the absolute Python interpreter and same-directory wrapper path.
POSIX Claude Code hook commands prefer `CLAUDE_PROJECT_DIR` and fall back to
`pwd` so missing runtime project-directory variables do not resolve wrappers
under the filesystem root.

When hook state is unclear, run:

```bash
python3 plugins/arbor/skills/arbor/scripts/diagnose_project_hooks.py \
  --root /path/to/project \
  --plugin-root plugins/arbor
```

The diagnostic distinguishes stale intent-only Codex files, executable wrapper
state, shared adapter state, project-level Claude hooks, legacy plugin-level
hook drift, and Codex trust gaps. File presence is not the same thing as proof
that a runtime fired a hook. Project wrapper files are compared with Arbor's
current generated wrapper template, so stale or hand-edited wrapper content is
reported as hook drift and repaired by re-registration.
Wrapper files that cannot be decoded as UTF-8 are treated as stale wrapper
content for the same repair path, not as diagnostic crashes. Re-registration
must overwrite those corrupt wrapper files with the current generated template.
Hook configuration files that cannot be read as UTF-8 are reported as invalid
hook surfaces by diagnosis instead of leaking Python tracebacks. Registration
and repair also fail cleanly on unreadable hook configuration encodings instead
of rewriting or crashing through those files.

Project wrappers and shared adapters ignore incomplete `ARBOR_PLUGIN_ROOT`,
`PLUGIN_ROOT`, `CODEX_PLUGIN_ROOT`, or `CLAUDE_PLUGIN_ROOT` environment values
unless the path has the full Arbor plugin shape. This keeps stale runtime
environment state from turning hook validation into `hook exited with code 1`.
Plugin-root environment paths that cannot be inspected are ignored the same way
so filesystem errors fall back to the packaged adapter root.
Wrapper content diagnosis ignores CRLF-versus-LF line-ending differences, but
still treats real template drift as a repairable hook issue.
Re-registration is idempotent: existing wrappers with current content are not
reported as repairs just because Windows lacks POSIX executable bits, while
POSIX wrappers still get executable permission repair when needed.
If a registered project wrapper cannot find an installed Arbor plugin cache,
it soft-skips instead of surfacing `hook exited with code 1`: SessionStart emits
no context, and Stop emits an allow-stop response. Use diagnosis or framework
repair to restore the cache-backed adapter path.
Automatic cache discovery considers only complete Arbor plugin roots in `X.Y.Z`
version directories. Explicit plugin-root environment overrides can still point
at a local development source for smoke tests, but stale ad hoc cache directories
such as `dev` or incomplete cache copies are ignored.
If the selected cache adapter itself exits nonzero, wrappers use the same
soft-fail policy and suppress failed-adapter diagnostics from hook output; the
adapter probe in Arbor diagnosis is the place to surface that repair signal.
Wrappers also bound adapter execution with an internal timeout, configurable for
tests through `ARBOR_HOOK_ADAPTER_TIMEOUT_SECONDS`, and apply the same soft-fail
policy on timeout, adapter discovery failure, or adapter launch failure.
The SessionStart adapter also bounds its startup helper through
`ARBOR_SESSION_START_INTERNAL_TIMEOUT_SECONDS`; startup helper timeouts or launch
failures soft-skip without injecting partial context.
The Stop adapter also bounds its own internal git probes and guide-quality
checks through `ARBOR_STOP_INTERNAL_TIMEOUT_SECONDS`; git probes and guide
checks that time out or fail to start soft-skip rather than hanging or blocking
Stop. In block mode, block-mode memory helper timeouts or launch failures emit
the normal allow-stop response.
Stop wrappers validate successful adapter stdout before passing it to the
runtime. Empty or non-JSON Stop output falls back to the normal allow-stop JSON
response, which keeps stale cache output from breaking the hook protocol.
Project wrappers do not pass successful adapter stderr through to the runtime;
diagnostics belong in Arbor diagnosis, while hook stdout stays the only success
output channel.
Arbor diagnosis also bounds shared-adapter probe execution, configurable for
tests through `ARBOR_HOOK_ADAPTER_PROBE_TIMEOUT_SECONDS`, and reports probe
timeouts or launch failures as `shared-adapters-probe-failed` instead of
hanging or crashing framework checks.
Diagnosis rejects incomplete `--plugin-root` directories before probing shared
adapters; the root must include the Codex manifest, Claude manifest, and Arbor
skill so diagnosis matches wrapper cache-selection rules.
SessionStart startup-context git probes are bounded by
`ARBOR_STARTUP_GIT_TIMEOUT_SECONDS`; a timed-out or failed-to-start git command
marks only that context section as failed so readable file context can still be
injected.
The quality hard gate bounds each subprocess check as well, configurable for
tests through `ARBOR_QUALITY_GATE_TIMEOUT_SECONDS`, so a stuck child check
fails one row instead of hanging the release workflow. Subprocess launch
failures also fail the affected row with a readable diagnostic instead of
crashing the gate.
The skill package checker also bounds each `quick_validate.py` invocation,
configurable for tests through `ARBOR_SKILL_PACKAGE_TIMEOUT_SECONDS`, so direct
skill validation cannot hang outside the hard gate. Validator launch failures
are reported as normal skill package failures instead of Python tracebacks.
The release readiness gate applies the same bounded-subprocess rule, configurable
for tests through `ARBOR_RELEASE_READINESS_TIMEOUT_SECONDS`, so install-state or
runtime-evidence checks cannot hang publishability decisions. Its published
source `git status` check is bounded by the same timeout. Release readiness
subprocess launch failures must fail the affected row with a readable
diagnostic instead of crashing the gate.
Direct install-state checks also bound their own git probes, configurable for
tests through `ARBOR_INSTALL_STATE_GIT_TIMEOUT_SECONDS`, so dirty-source
inspection cannot hang or crash when git fails to start outside release
readiness.
Local plugin cache sync bounds its git dirty-source and commit probes,
configurable for tests through `ARBOR_CACHE_SYNC_GIT_TIMEOUT_SECONDS`, so
cache publishing cannot hang or crash while inspecting source state.
The context boundary check reads published text files as UTF-8 only. Invalid
UTF-8 is a package-boundary failure, not a cue to fall back to a platform
default encoding.

## Validation

Use these checks after package, manifest, hook, README, or context-boundary
changes:

```bash
python3 plugins/arbor/skills/arbor/scripts/check_context_boundary.py
python3 plugins/arbor/skills/arbor/scripts/check_project_wrapper_smoke.py
python3 plugins/arbor/skills/arbor/scripts/check_project_wrapper_smoke_adapters.py
python3 plugins/arbor/skills/arbor/scripts/check_runtime_smoke_evidence_adapters.py
python3 plugins/arbor/skills/arbor/scripts/check_plugin_adapters.py
python3 plugins/arbor/skills/arbor/scripts/check_skill_packages.py
```

Run the full deterministic hard gate with:

```bash
python3 plugins/arbor/skills/arbor/scripts/check_quality_gate.py
```

Run the release readiness gate before publishing or claiming installed runtime
readiness:

```bash
python3 plugins/arbor/skills/arbor/scripts/check_release_readiness.py --runtime-smoke-evidence path/to/evidence.md
```

The hard gate is the source-ready quality contract. It checks package
boundaries, Python syntax without bytecode artifacts, source hygiene for tracked
and untracked published text files, diff hygiene, skill resource links,
marketplace paths, project hook behavior, install/cache tooling, and the Arbor
framework report. It also runs a repeatable project wrapper smoke that creates
a temporary initialized project and executes generated Codex and Claude
wrappers through explicit plugin-root and fake installed-cache discovery paths.
The fake installed-cache paths are created from the source manifest `X.Y.Z`
version so wrapper smoke cannot silently keep testing an older cache directory
after a release-version bump.
Wrapper smoke also covers cache fallback hazards: non-release cache directories
are ignored, incomplete higher-version release caches fall back to a complete
cache, and bad plugin-root environment paths fall back to installed-cache
discovery.
The wrapper-smoke adapter assertions live in their own module, so wrapper-smoke
contract changes can be validated directly before running the broader adapter
suite.
Smoke subprocess launch failures or timeouts are reported as failed smoke
evidence with readable diagnostics instead of Python tracebacks.
The smoke subprocess timeout defaults to 30 seconds and can be shortened for
tests or CI with `ARBOR_PROJECT_WRAPPER_SMOKE_TIMEOUT_SECONDS`.
It also asserts that only the lightweight `arbor` skill is published and that
plugin-level hook registrations are absent.
Python syntax validation treats invalid UTF-8 hook adapter sources as failures,
including extensionless adapter files, rather than skipping them.
Published JSON surfaces must be JSON objects, so manifests and marketplace
files cannot pass the boundary check as arrays, strings, or other JSON shapes.

The release readiness gate adds installed-runtime proof. It requires matching
Codex and Claude Code source manifest versions in `X.Y.Z` release form, a clean
published source surface, Codex and Claude marketplace source paths that point
at the plugin root under release, the source hard gate, strict install-state
checks for Codex and Claude Code caches, and a validated runtime smoke evidence
file. Source manifests must be JSON objects. A passing hard gate alone is not
proof that installed hooks fired in the runtime.
The runtime smoke evidence `Version:` must be an `X.Y.Z` release version and
match the plugin source manifest version being released. Its `Commit:` must
match the release source `HEAD`, and must be a 7-or-more-character hexadecimal
git commit prefix or full hash. Its `Date:` must use `YYYY-MM-DD`, and
`Operator:` must stay filled for auditability by identifying the operator.

The framework-check step may report Codex hook trust as blocked when `/hooks`
trust cannot be proven from files. Treat that as a runtime caveat: record it in
smoke evidence and do not claim trusted hook firing until the runtime proves it.

Runtime smoke evidence can use:

```text
plugins/arbor/skills/arbor/references/runtime-smoke-template.md
```

Validate filled runtime smoke evidence with:

```bash
python3 plugins/arbor/skills/arbor/scripts/check_runtime_smoke_evidence.py path/to/evidence.md
```

Runtime-smoke evidence adapter assertions live in
`check_runtime_smoke_evidence_adapters.py`, so evidence-contract changes can be
validated directly before running the broader adapter suite.

Runtime smoke evidence records its own validator command passing. It must keep
the full Codex and Claude Code event matrix for Windows and macOS/Linux,
including unavailable rows with concrete reasons. The matrix must contain exactly
one row for each template matrix entry and no extra runtime rows. Fired rows
must include runtime trust proof, absolute Python wrapper-or-launcher proof, and the absolute
local cache path that supplied the hook adapter. Any passing `Fired` marker,
including `ok` or `ready`, is treated as a fired row and must carry the same
proof. If any row is `not run`, blocked, or failed, keep it listed under Known
Risks. Use either `- none` or explicit risk entries, never both.
Audit metadata and required sections must each appear exactly once.

Before runtime smoke, compare installed caches with source without mutating
them:

```bash
python3 plugins/arbor/skills/arbor/scripts/check_install_state.py
```

Use strict mode for release automation:

```bash
python3 plugins/arbor/skills/arbor/scripts/check_install_state.py --strict
```

Strict mode also refuses non-`X.Y.Z` source manifest versions and dirty plugin
source even when caches match the source tree. Use `--allow-dirty-source` only
for explicit local development checks, not release evidence.
Install-state selected-cache reporting mirrors project wrappers: only complete
Arbor plugin roots in `X.Y.Z` release cache directories are candidates, so stale
`dev` directories and incomplete cache copies are not reported as the cache a
wrapper would automatically select.
Source or cache digest failures are reported as install-state drift, not as
tracebacks, so strict checks fail with actionable evidence instead of crashing.

For single-runtime smoke, narrow the check:

```bash
python3 plugins/arbor/skills/arbor/scripts/check_install_state.py --runtime codex --strict
python3 plugins/arbor/skills/arbor/scripts/check_install_state.py --runtime claude --strict
```

Runtime smoke release proof must record passing install/cache strict checks.
Drift, missing caches, dirty source, or `not run` install-state checks mean the
runtime evidence is not yet publishable.
Local plugin cache sync also requires matching `X.Y.Z` Codex and Claude source
manifest versions. It refuses dirty source by default and should not create
cache directories for ad hoc development versions such as `dev`. Cache sync
refreshes cached hook adapters and removes legacy plugin-level hook manifests
only inside existing `X.Y.Z` release cache directories; non-release cache
directories are left untouched. Cache sync also refuses targets that are the
plugin source tree or nested inside it, and reports those write-boundary
failures without a traceback. It stages cache copies before replacing installed
cache directories and preserves the existing installed cache if staging copy or
final replacement fails.

For runtime-facing hook changes, static checks are preflight only. Validate
trusted hook firing in an interactive Codex or Claude Code session when feasible.

Initialization templates must be readable UTF-8 package files. Missing or
unreadable templates fail initialization with a concise Arbor error instead of
a Python traceback.

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
2.0.0
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
