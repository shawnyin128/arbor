# Arbor Project Hook Contract

Arbor registers runtime-specific project-local hooks:

- Codex: `.codex/hooks.json`
- Codex wrapper scripts: `.codex/hooks/`
- Claude Code: `.claude/settings.json`
- Claude Code wrapper scripts: `.claude/hooks/`

Hook files are visible project artifacts, not user-global state. Each runtime
gets its own project hook surface while shared project memory remains in the
current repository.

## Registered Hook Intents

1. `arbor.session_startup_context`
   - Event: `session.start`
   - Entrypoint: `scripts/run_session_startup_hook.py --root ${PROJECT_ROOT}`
   - Optional argument channel: `--git-log-args "${GIT_LOG_ARGS}"`
   - Required order: `AGENTS.md`, formatted `git log`, `.arbor/memory.md`,
     `git status`
   - Git probes must be bounded by `ARBOR_STARTUP_GIT_TIMEOUT_SECONDS`; a
     timed-out git command marks only that context section as `git-timeout`
     while readable file context continues to render.

2. `arbor.in_session_memory_hygiene`
   - Event: `conversation.checkpoint`
   - Entrypoint: `scripts/run_memory_hygiene_hook.py --root ${PROJECT_ROOT}`
   - Optional argument channel: `--diff-args "${DIFF_ARGS}"`
   - Emits a memory hygiene packet with current memory, git status, unstaged
     diff stat, staged diff stat, and optional selected diff.
   - Rejects side-effecting selected diff options such as `--output`.
   - The running agent decides whether `.arbor/memory.md` would help the next
     agent resume current Arbor context that is not committed or durable
     elsewhere.
   - Trigger policy: high recall at stop, handoff, commit, or session boundary
     when Arbor-managed files are dirty or important discussion would otherwise
     be lost.
   - Positive cases include dirty Arbor context files, hook repairs, failed
     checks with unresolved local changes, user scope changes for current local
     context, local cache sync, ignored validation notes that explain dirty
     package changes, and any pause/stop with unresolved Arbor context.
   - Negative cases include clean git status, direct one-off explanations,
     read-only inspection, committed-and-pruned state, AGENTS-only stable guide
     updates, explicit no-write turns, and unrelated dirty files outside Arbor
     scope.
   - Arbor plugin source is treated as Arbor-managed only when `plugins/arbor`
     has the Arbor plugin shape: Codex manifest, Claude manifest, and the
     `skills/arbor/SKILL.md` file. A same-named application directory is not
     Arbor-managed state.
   - Git rename rows count as Arbor-managed when either the old path or the new
     path is Arbor-managed, so moving `.arbor/memory.md` or hook files still
     triggers recovery.
   - A tracked deletion under `.arbor/` counts as Arbor-managed even when the
     directory no longer exists on disk, so Stop can recreate `.arbor/memory.md`
     before the session ends.
   - Stop must inspect unquoted porcelain status so spaces, quotes, or special
     characters in `.arbor/` paths do not hide Arbor-managed changes from the
     trigger decision.
   - Codex mapping: `.codex/hooks.json` calls the
     `.codex/hooks/arbor-stop-memory-hygiene` wrapper, which delegates to
     `hooks/stop-memory-hygiene`. Codex requires configured command hooks to be
     trusted through `/hooks`; an initialized file alone is not proof the hook
     ran.
   - Claude mapping: `.claude/settings.json` calls the
     `.claude/hooks/arbor-stop-memory-hygiene` wrapper, which delegates to
     `hooks/stop-memory-hygiene`.

3. `arbor.goal_constraint_drift`
   - Event: `project.guide_drift`
   - Entrypoint: `scripts/run_agents_guide_drift_hook.py --root ${PROJECT_ROOT}`
   - Optional argument channel: repeat `--doc "${DOC_PATH}"` for each
     agent-selected project-local doc.
   - Emits an AGENTS drift packet with `AGENTS.md`, git status, top-level
     project structure, mapped path validation, `Project Map Drift Candidates`,
     and optional project-local docs.
   - The running agent decides whether to edit only `Project Goal`,
     `Project Constraints`, or `Project Map` in `AGENTS.md` when invoked
     manually.
   - Trigger with high recall after adding, removing, or renaming durable
     project entrypoints, after adding a new skill or runtime adapter, and
     before handoff when project structure changed.
   - Stop-time mapping: safe Project Map drift is checked by the shared Stop
     context-maintenance adapter when current git status includes new durable
     top-level entrypoints that are missing from the map. Output artifacts,
     caches, temporary directories, and build products are ignored. After safe
     map maintenance, Stop blocks unresolved guide-quality failures so the
     current agent repairs `AGENTS.md` before ending the active maintenance
     path. Clean direct turns do not mutate `AGENTS.md` or block stop for
     pre-existing map drift. Project Goal and Project Constraints remain
     explicit/manual unless a future design proves a safe automatic rule.

## Policy

- Project root must be resolved before registering or executing hooks.
- Hook state belongs in the project.
- Existing non-Arbor hooks must be preserved in both `.codex/hooks.json` and
  `.claude/settings.json`.
- Codex re-registration replaces only Arbor wrapper commands under
  `.codex/hooks/arbor-*`; unrelated Codex hook events, matcher groups,
  handlers, and settings are preserved.
- Claude project hook re-registration replaces only Arbor wrapper commands
  under `.claude/hooks/arbor-*`; unrelated Claude hooks and settings are
  preserved.
- Project hook wrappers use the absolute Python interpreter that ran Arbor
  registration; stale bare `python` or `python3` wrapper commands are hook drift
  and should be repaired by re-registration.
- Codex on Windows launches project hooks through `.cmd` files. Launcher paths
  without shell-sensitive characters are emitted unquoted because Codex's
  Windows hook runner executes that form reliably; paths with spaces or
  shell-sensitive characters are routed through `cmd.exe /d /c call "..."`. The
  launcher itself quotes the absolute Python interpreter and same-directory
  wrapper path.
- POSIX Claude Code hook commands must prefer `CLAUDE_PROJECT_DIR` and fall
  back to `pwd` so wrapper paths remain project-local when the runtime variable
  is unavailable.
- Project wrapper files must match Arbor's current generated wrapper template.
  Existing but stale or hand-edited wrapper content is hook drift, not ready
  state. CRLF-versus-LF line-ending differences alone do not count as drift.
- Project wrappers and shared adapters ignore incomplete `ARBOR_PLUGIN_ROOT`,
  `PLUGIN_ROOT`, `CODEX_PLUGIN_ROOT`, or `CLAUDE_PLUGIN_ROOT` values unless the
  path has the full Arbor plugin shape: Codex manifest, Claude manifest, and
  `skills/arbor/SKILL.md`.
- Arbor must not ship plugin-level hook registrations; Codex and Claude Code
  hook execution is project-level so `$arbor` can diagnose and repair it.
- Re-registering Arbor hooks must be idempotent: Windows must not report
  `chmod` repairs for current-content wrappers solely because POSIX executable
  bits do not apply there, while POSIX wrappers still get executable permission
  repair when needed.
- Registered project wrappers must soft-skip if no installed Arbor plugin cache
  can be found: SessionStart emits no context, and Stop emits an allow-stop JSON
  response instead of producing `hook exited with code 1`.
- Project wrappers and shared adapters must ignore plugin-root environment paths
  that cannot be inspected, using the next candidate or the packaged adapter
  root instead of surfacing a hook failure.
- Automatic cache discovery must ignore non-release cache directories such as
  `dev`; only complete Arbor plugin roots in `X.Y.Z` version directories are
  candidates. Explicit plugin-root environment overrides remain available for
  local development smoke tests.
- Local cache sync maintenance must refresh cached hook adapters and remove
  legacy plugin-level hook manifests only inside `X.Y.Z` release cache
  directories; non-release cache directories are not publishable runtime state
  and must be left untouched.
- Registered project wrappers must also soft-skip selected adapter failures:
  adapter diagnostics should be reported by Arbor diagnosis, not surfaced as
  runtime hook failures.
- Registered project wrappers must bound selected adapter execution with an
  internal timeout and soft-skip on timeout or adapter discovery/launch failure.
- SessionStart adapter startup helper execution must be bounded. Startup helper
  timeouts or launch failures must soft-skip rather than hang startup or inject
  partial context.
- Stop adapter internal subprocesses must also be bounded. Git probes and guide
  checks that time out or fail to start must soft-skip rather than hang or block
  Stop. In block mode, block-mode memory helper timeouts or launch failures must
  emit the normal allow-stop response.
- Stop wrappers must validate successful adapter stdout before passing it to
  the runtime. Empty or non-JSON Stop output must fall back to the normal
  allow-stop JSON response.
- Project wrappers must not pass successful adapter stderr through to the
  runtime; diagnostics belong in Arbor diagnosis, while hook stdout stays the
  only success output channel.
- Hook diagnosis must bound shared-adapter probe execution and report probe
  timeouts or launch failures as `shared-adapters-probe-failed` rather than
  hanging or crashing framework checks.
- Hook execution improves context recovery, not the agent's reading depth.
- Codex hook execution proof must come from a trusted interactive Codex or
  desktop session; non-interactive `codex exec` is not a reliable project-hook
  firing oracle.
- Use `scripts/diagnose_project_hooks.py` to distinguish hook intent files,
  executable wrappers, shared adapter state, legacy plugin-level hook drift,
  project-level Claude hook state, and Codex trust gaps before claiming a
  runtime hook is configured.
- Wrapper diagnosis must treat invalid wrapper text encodings as stale wrapper
  content, and re-registration must refresh corrupt wrapper files from the
  current template instead of surfacing a traceback.
- Hook configuration files with invalid text encodings must be reported as
  invalid hook surfaces by diagnosis instead of surfacing a traceback.
- Registration and repair must fail cleanly on unreadable hook configuration
  encodings instead of rewriting or crashing through those files.
