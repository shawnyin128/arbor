# Arbor Hook Trigger Scenario Corpus

## Labels

- `H1`: `arbor.session_startup_context`
- `H2`: `arbor.in_session_memory_hygiene`
- `H3`: `arbor.goal_constraint_drift`
- `NONE`: no Arbor hook should trigger
- `MULTI`: more than one hook may be appropriate; see note

This corpus is for semantic review and later plugin dispatch evaluation. It is not a rule-based classifier.

## H1 Positive: Startup, Resume, Orientation

| ID | User expression | Expected | Note |
| --- | --- | --- | --- |
| H1-P001 | "Start this project session." | H1 | Explicit session start. |
| H1-P002 | "Resume this repo." | H1 | Resume orientation. |
| H1-P003 | "Continue where we left off." | H1 | Startup context needed. |
| H1-P004 | "Load the project context first." | H1 | Direct context load. |
| H1-P005 | "Initialize Arbor in this project." | H1 | Init plus startup flow. |
| H1-P006 | "Run the Arbor startup flow." | H1 | Direct hook intent. |
| H1-P007 | "Before coding, orient yourself in the repo." | H1 | Project orientation. |
| H1-P008 | "What is the current project state?" | H1 | Context recovery. |
| H1-P009 | "Pick up this project from the previous session." | H1 | Resume. |
| H1-P010 | "Open with AGENTS, log, memory, and status." | H1 | Exact order requested. |
| H1-P011 | "先恢复项目上下文。" | H1 | Chinese resume context. |
| H1-P012 | "接着这个 repo 做，先看下上下文。" | H1 | Chinese resume. |
| H1-P013 | "初始化一下这个项目的 memory 流程。" | H1 | Initialization. |
| H1-P014 | "新窗口开始，先读项目地图。" | H1 | New session. |
| H1-P015 | "看看这个项目现在做到哪了。" | H1 | Orientation. |
| H1-P016 | "Before answering, inspect the project guide and memory." | H1 | Startup sources requested. |
| H1-P017 | "Rehydrate project context." | H1 | Indirect startup wording. |
| H1-P018 | "Run the project onboarding sequence." | H1 | Onboarding. |
| H1-P019 | "I just opened this repo. Get oriented." | H1 | Runtime-like start. |
| H1-P020 | "Use Arbor to resume work here." | H1 | Skill plus resume. |

## H2 Positive: Short-Term Memory Hygiene

| ID | User expression | Expected | Note |
| --- | --- | --- | --- |
| H2-P001 | "Update `.codex/memory.md` for what we just did." | H2 | Direct memory update. |
| H2-P002 | "The memory is stale now." | H2 | Stale memory. |
| H2-P003 | "Clean up resolved memory items." | H2 | Remove stale items. |
| H2-P004 | "We changed direction; refresh short-term memory." | H2 | Direction change. |
| H2-P005 | "Before commit, summarize the uncommitted state in memory." | H2 | Pre-commit memory. |
| H2-P006 | "Record current in-flight work, but don't commit." | H2 | Uncommitted work. |
| H2-P007 | "This memory item is done now." | H2 | Stale item resolution. |
| H2-P008 | "Use git status and diff to refresh session memory." | H2 | Direct packet sources. |
| H2-P009 | "We fixed that concern; remove it from memory." | H2 | Memory cleanup. |
| H2-P010 | "Checkpoint this session without committing." | H2 | Checkpoint. |
| H2-P011 | "把这轮未提交的内容整理进 memory。" | H2 | Chinese memory update. |
| H2-P012 | "memory 里这条已经过期了。" | H2 | Chinese stale memory. |
| H2-P013 | "先别 commit，记录一下现在做到哪。" | H2 | Chinese uncommitted checkpoint. |
| H2-P014 | "刚刚改方向了，更新短期记忆。" | H2 | Chinese direction change. |
| H2-P015 | "检查 memory 有没有和当前 diff 不一致。" | H2 | Memory diff consistency. |
| H2-P016 | "At this checkpoint, capture risks from current changes." | H2 | Short-term risks. |
| H2-P017 | "The TODO in memory moved to a review doc." | H2 | Remove duplicated memory. |
| H2-P018 | "Make session memory reflect the current uncommitted patch." | H2 | Patch-to-memory. |
| H2-P019 | "Refresh memory after this implementation pass." | H2 | Implementation checkpoint. |
| H2-P020 | "Prune memory against git status." | H2 | Mechanical context. |

## H3 Positive: Durable AGENTS Drift

| ID | User expression | Expected | Note |
| --- | --- | --- | --- |
| H3-P001 | "The project goal has changed." | H3 | Direct goal drift. |
| H3-P002 | "Update `AGENTS.md` with this new constraint." | H3 | Direct constraint update. |
| H3-P003 | "This is now a plugin-first project." | H3 | Durable goal shift. |
| H3-P004 | "From now on, docs must stay English." | H3 | Durable constraint. |
| H3-P005 | "The project map is outdated." | H3 | Map drift. |
| H3-P006 | "Add the new scripts folder to the project map." | H3 | Durable map update. |
| H3-P007 | "This workflow rule should be remembered across sessions." | H3 | Durable rule. |
| H3-P008 | "Make this a permanent project constraint." | H3 | Durable constraint. |
| H3-P009 | "AGENTS should say hooks are project-level." | H3 | Direct AGENTS update. |
| H3-P010 | "The architecture boundary changed." | H3 | Map or constraint drift. |
| H3-P011 | "项目目标变了。" | H3 | Chinese goal drift. |
| H3-P012 | "这个约束以后都要遵守。" | H3 | Chinese durable constraint. |
| H3-P013 | "项目地图需要更新一下。" | H3 | Chinese map drift. |
| H3-P014 | "把这个长期规则写进 AGENTS。" | H3 | Chinese AGENTS update. |
| H3-P015 | "以后不要一次设计所有 hook，要一个一个做。" | H3 | Durable workflow rule. |
| H3-P016 | "We added a new review-doc layout; update the guide." | H3 | Durable map/workflow. |
| H3-P017 | "The skill name is now Arbor permanently." | H3 | Durable naming. |
| H3-P018 | "Project constraints should include no fixed read limits." | H3 | Durable constraint. |
| H3-P019 | "Make the project map include the hook registration script." | H3 | Map update. |
| H3-P020 | "This belongs in long-term memory, not session memory." | H3 | AGENTS likely target. |

## NONE: Unrelated Or Non-Hook Requests

| ID | User expression | Expected | Note |
| --- | --- | --- | --- |
| N-P001 | "What is the capital of France?" | NONE | No project workflow. |
| N-P002 | "Translate this sentence into English." | NONE | No project memory. |
| N-P003 | "Run `date`." | NONE | Simple command. |
| N-P004 | "Explain Python decorators." | NONE | Generic question. |
| N-P005 | "Format this JSON." | NONE | No project context. |
| N-P006 | "What does this error mean?" | NONE | Generic unless project-bound. |
| N-P007 | "Write a regex for email validation." | NONE | Generic task. |
| N-P008 | "Make a logo image." | NONE | Visual request, no Arbor semantics. |
| N-P009 | "Open localhost in browser." | NONE | Browser action. |
| N-P010 | "Install dependencies." | NONE | Not memory or AGENTS by itself. |
| N-P011 | "Run the unit tests." | NONE | No hook unless checkpoint follows. |
| N-P012 | "Fix the lint error in this file." | NONE | Narrow coding task in active context. |
| N-P013 | "Commit the current changes." | NONE | Git action, not memory by itself. |
| N-P014 | "Push this branch." | NONE | Git action. |
| N-P015 | "Show me git status." | NONE | Command only. |
| N-P016 | "Review this function for bugs." | NONE | Code review only unless memory/guide drift emerges. |
| N-P017 | "Summarize this paper." | NONE | External summarization. |
| N-P018 | "帮我写一个 SQL 查询。" | NONE | Generic coding. |
| N-P019 | "这个词怎么翻译？" | NONE | Translation. |
| N-P020 | "给我一个 shell 命令。" | NONE | Command request. |

## Negative Near-Misses

| ID | User expression | Expected | Note |
| --- | --- | --- | --- |
| NM-P001 | "Remember this for the next paragraph." | NONE | Not project memory. |
| NM-P002 | "This is a constraint in the algorithm." | NONE | Local algorithm term, not project constraint. |
| NM-P003 | "The goal of this test is coverage." | NONE | Test-local goal. |
| NM-P004 | "Map over this array." | NONE | Not project map. |
| NM-P005 | "Start the dev server." | NONE | "Start" is not session startup. |
| NM-P006 | "Resume the download." | NONE | Not project resume. |
| NM-P007 | "Clean memory usage in this Python process." | NONE | Runtime memory, not `.codex/memory.md`. |
| NM-P008 | "The model has long-term memory." | NONE | Conceptual phrase, not AGENTS. |
| NM-P009 | "Update the README." | NONE | Docs edit, not AGENTS unless durable guide requested. |
| NM-P010 | "This feature has a goal and constraints section." | NONE | Artifact content, not project guide drift. |
| NM-P011 | "Checkpoint the training model." | NONE | ML checkpoint, not session memory. |
| NM-P012 | "Use git log to find the bug." | NONE | Git log as task evidence, not startup. |
| NM-P013 | "The hook failed in React." | NONE | Software hook concept, not Arbor hook. |
| NM-P014 | "Update memory allocation limits." | NONE | Runtime memory. |
| NM-P015 | "Add a map component to the UI." | NONE | UI map, not project map. |
| NM-P016 | "This rule is only for this function." | NONE | Not durable project rule. |
| NM-P017 | "Don't forget this variable name while editing." | NONE | Local working note. |
| NM-P018 | "Let's start with file A." | NONE | Task start, not session orientation. |
| NM-P019 | "The session token expired." | NONE | Auth session. |
| NM-P020 | "Update constraints in the optimization solver." | NONE | Domain constraints, not project constraints. |

## MULTI Or Ambiguous Cases

| ID | User expression | Expected | Note |
| --- | --- | --- | --- |
| M-P001 | "New session; we also have uncommitted changes from last time." | MULTI | H1 first; H2 if memory stale after context. |
| M-P002 | "Resume work and clean up stale memory." | MULTI | H1 plus H2. |
| M-P003 | "The project goal changed; also record our uncommitted pivot." | MULTI | H3 plus H2. |
| M-P004 | "Update context after this pivot." | MULTI | Need agent judgment: H2 or H3, maybe both. |
| M-P005 | "We are switching strategy permanently; capture the current patch too." | MULTI | Durable and transient updates. |
| M-P006 | "Initialize Arbor and make this new workflow rule permanent." | MULTI | H1 plus H3. |
| M-P007 | "Start fresh, then update AGENTS if the map is wrong." | MULTI | H1, conditional H3. |
| M-P008 | "看看项目上下文，同时 memory 也可能过期了。" | MULTI | H1 plus possible H2. |
| M-P009 | "这个目标变了，而且当前未提交内容也要整理。" | MULTI | H3 plus H2. |
| M-P010 | "恢复现场，然后把长期约束更新掉。" | MULTI | H1 plus H3. |
| M-P011 | "Review all Arbor hooks end to end." | NONE | Meta-review may inspect hook contracts manually, but should not trigger runtime hook dispatch by itself. |
| M-P012 | "Update project memory." | MULTI | Ambiguous: ask whether short-term `.codex/memory.md` or durable `AGENTS.md`, unless context makes it clear. |
| M-P013 | "Refresh context." | MULTI | Ambiguous: H1 if orientation, H2 if in-session memory. |
| M-P014 | "Make the current direction durable." | MULTI | H3 is primary; could also require H2 cleanup if memory has old direction. |
| M-P015 | "We are done with this feature but no commit yet." | MULTI | H2 is primary; could later lead to H3 if project map changed. |
| M-P016 | "This should be remembered." | MULTI | Ask or infer durable vs short-term from context. |
| M-P017 | "Document the new workflow." | MULTI | Could be project docs only or H3 if `AGENTS.md` must change. |
| M-P018 | "Before ending, save where we are." | H2 | Usually memory checkpoint, not H1. |
| M-P019 | "Before starting, save where we were." | MULTI | Wording conflict; inspect state. |
| M-P020 | "AGENTS and memory are both stale." | MULTI | H3 plus H2. |

## Cross-Language Paraphrase Sweep

| ID | User expression | Expected | Note |
| --- | --- | --- | --- |
| CL-P001 | "先进入项目状态。" | H1 | Startup orientation. |
| CL-P002 | "Bring me back into the repo." | H1 | Startup orientation. |
| CL-P003 | "恢复上下文，不要直接开写。" | H1 | Context first. |
| CL-P004 | "Boot the project memory flow." | H1 | Startup flow. |
| CL-P005 | "帮我同步一下短期记忆。" | H2 | Short-term memory. |
| CL-P006 | "Session notes are out of date." | H2 | Memory stale. |
| CL-P007 | "把未提交的风险留下来。" | H2 | Uncommitted risks. |
| CL-P008 | "Prune stale in-flight notes." | H2 | Memory cleanup. |
| CL-P009 | "长期目标换了。" | H3 | Durable goal. |
| CL-P010 | "This project rule is no longer true." | H3 | Durable constraint drift. |
| CL-P011 | "项目地图漏了新模块。" | H3 | Project map drift. |
| CL-P012 | "Write this into the agent guide." | H3 | Direct AGENTS. |
| CL-P013 | "开始跑测试。" | NONE | Start tests, not session. |
| CL-P014 | "Memory leak 怎么查？" | NONE | Runtime memory. |
| CL-P015 | "Map this JSON field." | NONE | Data mapping. |
| CL-P016 | "The hook in this React component needs useEffect." | NONE | React hook. |
| CL-P017 | "接着上次，不过先别动 memory。" | H1 | Explicitly avoid H2. |
| CL-P018 | "只更新 memory，不要碰 AGENTS。" | H2 | Explicit H2 only. |
| CL-P019 | "只更新 AGENTS，不要碰 memory。" | H3 | Explicit H3 only. |
| CL-P020 | "这个只是临时备注，不要写进长期文档。" | H2 | Short-term if relevant to current work. |

## Runtime Event Scenarios

| ID | Event or context | Expected | Note |
| --- | --- | --- | --- |
| EV-P001 | Runtime emits `session.start` in a project root. | H1 | Direct event dispatch. |
| EV-P002 | Runtime emits `session.start` outside a project root. | NONE | Should not write outside project. |
| EV-P003 | Runtime emits `conversation.checkpoint` after uncommitted diff appears. | H2 | Memory hygiene packet. |
| EV-P004 | Runtime emits `conversation.checkpoint` with clean git status and no memory issue. | NONE | No semantic need; runtime may skip. |
| EV-P005 | Runtime detects user updated durable project constraint. | H3 | AGENTS drift packet. |
| EV-P006 | Runtime detects a one-off user preference for this turn. | NONE | Not durable. |
| EV-P007 | Runtime detects `AGENTS.md` missing during startup. | H1 | Startup fallback diagnostics. |
| EV-P008 | Runtime detects `.codex/memory.md` missing during checkpoint. | H2 | Memory diagnostic. |
| EV-P009 | Runtime detects docs selected for AGENTS drift. | H3 | Include `--doc`. |
| EV-P010 | Runtime detects selected doc outside project root. | H3 | Hook should reject outside path once called. |

## Minimum Review Sampling Plan

A feature-level reviewer should sample at least:

- 10 H1 positive cases.
- 10 H2 positive cases.
- 10 H3 positive cases.
- 15 `NONE` or near-miss cases.
- 10 `MULTI` or ambiguous cases.
- 10 cross-language cases.
- All runtime event scenarios.

Any failed case should be recorded in the feature-level review file with whether the issue is:

- skill metadata wording,
- hook contract wording,
- missing runtime/plugin dispatch behavior,
- or expected ambiguity requiring agent judgment.
