# Arbor Project Hook Contract

Arbor registers runtime-specific project-local hooks:

- Codex: `.codex/hooks.json`
- Codex wrapper scripts: `.codex/hooks/`
- Claude Code: `.claude/settings.json` plus wrappers under `.claude/hooks/`

Hook files are visible project artifacts, not user-global state. Each runtime
gets its own project hook surface while shared project memory remains in the
current repository.

## Registered Hook Intents

1. `arbor.session_startup_context`
   - Event: `session.start`
   - Entrypoint: `scripts/run_session_startup_hook.py --root ${PROJECT_ROOT}`
   - Optional argument channel: `--git-log-args "${GIT_LOG_ARGS}"`
   - Required order: `AGENTS.md`, formatted `git log`, `.arbor/memory.md`, `git status`

2. `arbor.in_session_memory_hygiene`
   - Event: `conversation.checkpoint`
   - Entrypoint: `scripts/run_memory_hygiene_hook.py --root ${PROJECT_ROOT}`
   - Optional argument channel: `--diff-args "${DIFF_ARGS}"`
   - Emits a memory hygiene packet with current memory, git status, unstaged diff stat, staged diff stat, and optional selected diff.
   - Rejects side-effecting selected diff options such as `--output`.
   - The running agent decides whether to edit project-local `.arbor/memory.md` using the packet plus conversation context.
   - Trigger policy: high recall when Arbor-managed work is dirty or about to cross a checkpoint, handoff, release gate, commit, or session boundary.
   - Positive cases include brainstorm/develop/evaluate/converge/release artifact changes, failed checks, scope changes, local cache sync, ignored review or fixture edits, and any pause/stop with dirty Arbor work.
   - Negative cases include clean git status, direct one-off explanations, read-only inspection with no unresolved Arbor state, committed-and-pruned work, AGENTS-only stable guide updates, explicit no-write turns, and unrelated dirty files outside Arbor scope.
   - The registered policy includes a machine-checkable `case_corpus`; adapter validation checks trigger/suppress counts, unique ids, required fields, and required scenario classes.
   - Codex mapping: the project hook in `.codex/hooks.json` calls the `.codex/hooks/arbor-stop-memory-hygiene` wrapper, which delegates to `hooks/stop-memory-hygiene`. Codex requires configured command hooks to be trusted through `/hooks`; an initialized file alone is not proof the hook ran.
   - Claude Code mapping: the project hook in `.claude/settings.json` calls the `.claude/hooks/arbor-stop-memory-hygiene` wrapper, which delegates to `hooks/stop-memory-hygiene`. `Stop` output can re-enter the agent loop as a visible continuation, so the adapter defaults to a silent memory guard for dirty Arbor worktrees: if `.arbor/memory.md` is missing, empty, or lacks a meaningful `In-flight` entry, it writes a generic resume pointer and returns non-blocking JSON with suppressed hook output. It honors `stop_hook_active` first so it can never loop. Set `ARBOR_STOP_MEMORY_HYGIENE_MODE=block` to opt into blocking with the packet as the block reason.

3. `arbor.goal_constraint_drift`
   - Event: `project.guide_drift`
   - Entrypoint: `scripts/run_agents_guide_drift_hook.py --root ${PROJECT_ROOT}`
   - Optional argument channel: repeat `--doc "${DOC_PATH}"` for each agent-selected project-local doc.
   - Emits an AGENTS drift packet with `AGENTS.md`, git status, top-level project structure, mapped path validation, `Project Map Drift Candidates`, and optional project-local docs.
   - The running agent decides whether to edit only `Project Goal`, `Project Constraints`, or `Project Map` in `AGENTS.md`.
   - Trigger with high recall after adding, removing, or renaming durable project entrypoints, after adding a new skill or runtime adapter, and before release/publish/handoff when project structure changed.
   - When `Project Map Drift Candidates` reports `update-needed`, update `AGENTS.md` Project Map before handoff or release unless the listed missing or stale path is intentionally excluded.
   - `AGENTS.md` should remain the stable guide and map, not a complete long-term memory dump.
   - Claude Code mapping: none. Claude Code has no native event for project-guide drift, so this intent stays user/skill-driven there.

## Policy

- Project root must be resolved before registering or executing hooks.
- Hook state belongs in the project.
- Existing non-Arbor hooks must be preserved in both `.codex/hooks.json` and `.claude/settings.json`.
- Codex re-registration replaces only Arbor wrapper commands under `.codex/hooks/arbor-*`; unrelated Codex hook events, matcher groups, handlers, and settings are preserved.
- Legacy Arbor-only Codex hook intent lists are converted to Codex's executable hook schema during registration.
- Claude project hook re-registration replaces only Arbor wrapper commands under `.claude/hooks/arbor-*`; unrelated Claude hooks and settings are preserved.
- Re-registering Arbor hooks must be idempotent.
- Hook execution fixes workflow order, not read depth.
- Codex hook execution proof must come from a trusted interactive Codex or
  desktop session; non-interactive `codex exec` is useful for ordinary workflow
  replay but is not a reliable project-hook firing oracle.
