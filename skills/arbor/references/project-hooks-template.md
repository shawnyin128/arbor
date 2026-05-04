# Arbor Project Hook Contract

Arbor registers project-local hook intents in `.codex/hooks.json`.

The hook file is a visible project artifact, not user-global state. A later Arbor plugin can adapt this contract to a runtime-specific hook API while keeping project memory in the current repository.

## Registered Hook Intents

1. `arbor.session_startup_context`
   - Event: `session.start`
   - Entrypoint: `scripts/run_session_startup_hook.py --root ${PROJECT_ROOT}`
   - Optional argument channel: `--git-log-args "${GIT_LOG_ARGS}"`
   - Required order: `AGENTS.md`, formatted `git log`, `.codex/memory.md`, `git status`

2. `arbor.in_session_memory_hygiene`
   - Event: `conversation.checkpoint`
   - Entrypoint: `scripts/run_memory_hygiene_hook.py --root ${PROJECT_ROOT}`
   - Optional argument channel: `--diff-args "${DIFF_ARGS}"`
   - Emits a memory hygiene packet with current memory, git status, unstaged diff stat, staged diff stat, and optional selected diff.
   - Rejects side-effecting selected diff options such as `--output`.
   - The running agent decides whether to edit project-local `.codex/memory.md` using the packet plus conversation context.

3. `arbor.goal_constraint_drift`
   - Event: `project.guide_drift`
   - Entrypoint: `scripts/run_agents_guide_drift_hook.py --root ${PROJECT_ROOT}`
   - Optional argument channel: repeat `--doc "${DOC_PATH}"` for each agent-selected project-local doc.
   - Emits an AGENTS drift packet with `AGENTS.md`, git status, and optional project-local docs.
   - The running agent decides whether to edit only `Project Goal`, `Project Constraints`, or `Project Map` in `AGENTS.md`.
   - `AGENTS.md` should remain the stable guide and map, not a complete long-term memory dump.

## Policy

- Project root must be resolved before registering or executing hooks.
- Hook state belongs in the project.
- Existing non-Arbor hooks must be preserved.
- Only canonical hooks with `owner=arbor` are replaced during registration; non-Arbor hooks are preserved even if ids collide.
- Re-registering Arbor hooks must be idempotent.
- Hook execution fixes workflow order, not read depth.
