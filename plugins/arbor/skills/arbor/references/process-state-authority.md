# Process State Authority

Arbor controls workflow facts, not the agent's implementation judgment. These
artifacts own the durable facts for a managed workflow:

| Fact | Authoritative source | Validation role |
| --- | --- | --- |
| Stable project goal, constraints, and map | `AGENTS.md` | Startup orientation and project-map drift checks. |
| Short-term unresolved work before commit | `.arbor/memory.md` | Resume pointer for uncommitted managed work. |
| Feature queue and status | `.arbor/workflow/features.json` | Which feature exists, where its review evidence lives, and whether it is planned, in development, in evaluation, changed, done, or blocked. |
| Brainstorm, developer, evaluator, convergence, and release evidence | `docs/review/*.md` | Append-only evidence by workflow phase. |
| Completed work | git history plus release/checkpoint evidence | Finished state after local checkpoints, publish, push, or other release actions. |

`scripts/check_process_state.py` validates these facts without mutating them.
It checks registry shape, review-document existence, phase round presence,
open-work memory hygiene, stale in-flight memory after terminal features, and
optional release-round evidence for done features.

The script deliberately does not choose a feature, select tests, decide whether
an implementation is good, update statuses, or impose a coding process. Use it
as an advisory check during development and as a stricter release-gate input
when warnings should block a checkpoint.

Useful commands:

```bash
python3 plugins/arbor/skills/arbor/scripts/check_process_state.py --root <project-root>
python3 plugins/arbor/skills/arbor/scripts/check_process_state.py --root <project-root> --json
python3 plugins/arbor/skills/arbor/scripts/check_process_state.py --root <project-root> --strict
python3 plugins/arbor/skills/arbor/scripts/check_process_state.py --root <project-root> --require-release-round-for-done
python3 plugins/arbor/skills/arbor/scripts/check_process_state.py --self-test
```
