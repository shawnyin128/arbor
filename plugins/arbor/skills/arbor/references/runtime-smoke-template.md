# Arbor Runtime Smoke Evidence

Version: 2.0.0
Commit: pending
Date: YYYY-MM-DD
Operator: pending

The `Version:` value must be the concrete `X.Y.Z` plugin version under release.
`Commit:` must be a 7-or-more-character hexadecimal git commit prefix or full
hash that matches the release source `HEAD`. `Date:` must use `YYYY-MM-DD`.
Keep `Operator:` filled with the operator identity so the evidence remains
auditable.
Each audit metadata field and required section must appear exactly once.
Audit metadata and required sections must each appear exactly once.

## Hard Gate

Result must be pass or accepted. Do not use blocked runtime smoke evidence as
release proof. The hard gate must include passing quality-gate evidence and a
passing self-validation command for this runtime smoke evidence file.

- `python3 plugins/arbor/skills/arbor/scripts/check_quality_gate.py`: pending
- `python3 plugins/arbor/skills/arbor/scripts/check_runtime_smoke_evidence.py <this-file>`: pending
- Result: pending
- Accepted caveats: pending

## Cache And Install State

Strict install/cache checks must pass before this file can be treated as release
proof.
Dirty-source sync and strict guards must pass; development overrides are not
release proof.
Cache detail blockers must be absent: no legacy plugin-level hook manifests and
no transient cache artifacts.

- `python3 plugins/arbor/skills/arbor/scripts/check_install_state.py --strict`: pending
- Single-runtime install checks (`--runtime codex|claude|both`): pending
- Codex cache path: pending
- Claude cache path: pending
- Cache version selected by project wrapper: pending
- Dirty source sync guard: pending
- Dirty source strict guard: pending
- Legacy plugin-level `hooks/hooks.json` present: pending
- `__pycache__` / `*.pyc` present in synced cache: pending

## Hook Runtime Smoke

Record real runtime evidence when available. If a runtime cannot be exercised,
record `not run` plus a concrete reason; `n/a` and `not applicable` are not
concrete reasons.
Keep all template rows so Codex and Claude Code SessionStart/Stop evidence is
explicit for both Windows and macOS/Linux.
Keep exactly one row for each template matrix entry. No extra runtime rows are
allowed because release evidence must stay a fixed auditable matrix.
Known Risks cannot be `none` when any runtime smoke row is not fully passing.
Use either `- none` or explicit risk entries, never both.
Fired rows must include absolute local cache discovery paths.
Fired cache discovery paths must point at the same version directory named by
the `Version:` field above.
Fired rows must prove runtime trust and absolute Python wrapper-or-launcher use.
Fired row Evidence must describe concrete observed output or runtime state;
`none` and `n/a` are not evidence.
Fired rows must not also carry a concrete unavailable reason.
Any passing Fired marker, including `ok` or `ready`, counts as fired proof and
must include the same evidence.
Fired must be either a passing marker or `not run`; do not use ambiguous values
such as `no`.

| Runtime | OS | Event | Trusted | Fired | Wrapper or launcher uses absolute Python | Cache discovery path | Evidence | Unavailable reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Codex | Windows | SessionStart | pending | pending | pending | pending | pending | pending |
| Codex | Windows | Stop | pending | pending | pending | pending | pending | pending |
| Claude Code | Windows | SessionStart | pending | pending | pending | pending | pending | pending |
| Claude Code | Windows | Stop | pending | pending | pending | pending | pending | pending |
| Codex | macOS/Linux | SessionStart | pending | pending | pending | pending | pending | pending |
| Codex | macOS/Linux | Stop | pending | pending | pending | pending | pending | pending |
| Claude Code | macOS/Linux | SessionStart | pending | pending | pending | pending | pending | pending |
| Claude Code | macOS/Linux | Stop | pending | pending | pending | pending | pending | pending |

## Deterministic Substitute Evidence

Deterministic substitute checks must pass. These checks are the fallback proof
when a runtime smoke row is unavailable.

- Project wrapper execution with plugin-root env: pending
- Project wrapper execution through fake Codex cache: pending
- Project wrapper execution through fake Claude cache: pending
- Multi-version cache selection with broken older adapter: pending
- POSIX command rendering: pending

## Known Risks

- pending
