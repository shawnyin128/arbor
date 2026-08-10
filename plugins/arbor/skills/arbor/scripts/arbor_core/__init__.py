"""Arbor: the volatile project-context layer for Claude Code.

Arbor keeps a Claude Code session oriented in a local repository. The durable
layer (project goal, constraints, map) is carried by ``AGENTS.md`` loaded
natively through a ``CLAUDE.md`` import. Arbor owns only what no static file
can carry: git position, the task list that was in flight, unresolved decisions,
and parked ideas.

Hooks observe what happened; the agent records why. Those two kinds of state are
kept in separate files so neither has to be classified.
"""

from __future__ import annotations

SCHEMA_VERSION = 1
