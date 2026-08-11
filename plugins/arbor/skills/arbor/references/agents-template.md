# Agent Guide

<!--
This is the durable project guide. Claude Code loads it through the @AGENTS.md
import in CLAUDE.md, so it is in context every session and survives compaction.

Keep it short, well under 200 lines. Durable facts only, and only ones the
codebase cannot show by itself: how to build and test it, what it is for, the
constraints a newcomer would get wrong, and where a given kind of change belongs.

Running Arbor's initialization means you will not run Claude Code's own /init, so
this file has to carry what /init would have produced. Five things it refuses to
write, and neither should you:

  - Do not repeat yourself.
  - No obvious instructions, of the "write unit tests for all new utilities" or
    "never commit API keys" kind.
  - Do not list components or file structure that can be easily discovered.
  - No generic development practices.
  - Do not invent sections such as "Common Development Tasks", "Tips for
    Development", or "Support and Documentation". A section earns its place only
    if a file you actually read supports it.

Anything the agent can find with glob, grep, or git is in that third category:
directory listings, dependency lists, and repository tours measurably do not help
it reach the files it needs to change, and they are the first thing to go stale.
Anything that changes week to week belongs in .arbor/memory.md or in git.
-->

## Project Goal

Arbor has not recorded a stable project goal for this repository yet. Inspect the
repository itself before answering project-purpose questions, and replace this
section once the durable goal is known.

## Commands

Arbor has not recorded the commands for this repository yet. Work them out from
the build and test configuration before answering, and replace this section.

- Build, test, and lint, as the exact command line to type.
- How to run a **single** test, not just the whole suite. This is the one an agent
  needs most and the one least often written down.
- Only commands that are not obvious from the manifest. If `npm test` is the whole
  story, one line is the whole section.

## Project Constraints

- Record constraints a newcomer would get wrong, not universal good practice.
- Link to volatile external context instead of copying it here.
- Keep task-specific procedures in skills or referenced docs, not in this file.

## Project Map

Arbor has not recorded a durable project map for this repository yet. Inspect the
repository directly before answering project-structure questions, and replace this
section once there is something to say that the tree cannot show.

- Every bullet must state a rule, not a location: where new code of a given kind
  belongs, a boundary not to cross, or a trap that has caught someone.
- Name the exact file that matters, nested or not. A precise pointer earns its
  characters; a directory census does not.
- If a path here is renamed, fix it the same day. `arbor doctor` reports paths in
  this file that git has a record of but disk no longer has, because a guide that
  confidently names the wrong file is worse than one that names none.
