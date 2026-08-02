# Part 3: IDEAS.md, HISTORY.md, and the Roadmap System

> **Core.** Part of the maintained quick-start path. The tools and settings snippets it references are asserted by `tools/selftest.sh` on every push.

## IDEAS.md - The Priority Queue

Every project repo gets a `docs/IDEAS.md`. It is the forward-looking priority list for that repo - the single source of truth for "what to work on next."

Rules that make it work:
- Ordered by priority (not by when you added them)
- Use semantic tiers: TIER 0 (blocking/critical), TIER 1 (core features), TIER 2 (quality), TIER 3 (nice-to-have)
- When something ships: remove from IDEAS.md, add a dated entry to `docs/HISTORY.md`
- Never mark done with checkmarks and leave the entry - remove completely

`HISTORY.md` is the archive of everything that shipped. When you ask "how did we implement X before?" Claude can read HISTORY.md without wading through the active list.

This split (active vs archived) keeps IDEAS.md clean and usable. A list that keeps growing without anything leaving it stops being useful quickly.

One placement note if you fork this playbook: keep your own ideas somewhere private (your workspace repo, a private gist, a local file outside the repo), not in the public fork. A backlog is the most context-leaking file you own - it names unreleased work, internal systems, and people. Public repos take bug reports and feature suggestions through Issues instead.

### Why the Removal Discipline Matters

Marking done with `[x]` leaves noise. The active list is polluted with completed items. When Claude reads IDEAS.md to pick the next thing to work on, it has to filter through things that are already done. Remove entries cleanly; the git history is the record.

### Semantic Tiers Over Phase Numbering

Numbering phases ("Phase 1", "Phase 2") creates pressure to complete them in order even when priorities change. Semantic tiers communicate what matters and why:

- **TIER 0** - blocking/critical: nothing else matters until this is fixed
- **TIER 1** - core feature work: what the project exists to do
- **TIER 2** - quality/polish: makes it better, not essential
- **TIER 3** - nice-to-have: backlog material

The tier communicates urgency at a glance. When budget is tight, the decision is easy: TIER 0 only.

### Routing: Which List Does This Belong On

Picking the wrong list is the most common backlog defect, and the usual test ("is it about this repo?") gets it wrong regularly. The better test is **what unblocks the item**, not what it is about.

| The item | Goes to | Why |
|---|---|---|
| Code, docs, tests or tooling scoped to ONE repo | that repo's `IDEAS.md` | `/dev-session` picks from here |
| Work on the workspace itself: a hook, a skill, a rule, a workspace tool | the workspace's own `IDEAS.md` | The workspace is a repo and deserves the same treatment as any other. Most people never create this one, and it is why workspace improvements live in scattered notes |
| The unattended run's work QUEUE, research, cross-repo sweeps | a separate queue file | A queue answers "what should tonight's run do", which spans every repo and includes work belonging to none. That is a different question from "what should be built in this repo next" |
| Blocked on a named person, with a deadline and a real consequence | `pending-actions.md` | High bar, dated, and capped. An unbounded blocked list is a wish list |

The distinction between the second and third rows is the one people collapse, and collapsing it is why a queue file grows to hundreds of items: repo-scoped engineering work has nowhere else to go, so it accumulates in the queue and the queue stops functioning as a queue.

**Keep the specification in ONE file and point every backlog at it.** Copy the convention into each repo's backlog and you have created N copies that will disagree within a month, and improving the process becomes N edits instead of one. See `templates/BACKLOG-SPEC.md`.

### The One Question That Derives the Tier

Assigning a tier is a judgement someone makes and then defends. Deriving it from an answer is cheaper and more honest, and it needs exactly one question per item:

**"Why is this necessary, and what fails if we skip it?"**

Ask it of every item once the list has grown past roughly ten and the ordering has stopped being self-evident. The tier falls out of the answer:

- "it is broken or loses data without this" -> TIER 0
- "it enables other work, or the repo's main job is worse without it" -> TIER 1
- "it improves something that already works" -> TIER 2
- "it would be nice" -> TIER 3
- **"I cannot answer" -> the most valuable group of the five**

That last group is the point. An item whose necessity cannot be stated is either not understood yet or no longer wanted, and both of those are decisions worth taking now rather than carrying for another six months. A list where every item has an answer is well-ordered whether or not it has tier labels; a list with tier labels and no answers is decorated, not prioritised.

Tiers, templates and validation checklists are scaffolding. The clarity is the work.

---

## The Roadmap System (for multi-repo work)

For work spanning multiple repos, there is a roadmap layer above IDEAS.md:

- **Directives** - strategic goals spanning weeks or months. One file per directive in `roadmap/directives/`. Each has a `Repo:` and `Ideas:` pointer to the specific repo and IDEAS.md section. Max 30 lines - just the pointer and the what/why.
- **Tasks** - concrete next actions at the session level, in `roadmap/pending-actions.md`. Cross-repo only; repo-specific tasks live in that repo's IDEAS.md.
- **DIRECTIVES_OVERVIEW.md** - a table of all active directives with status, priority, and repo pointers. The `/today` skill reads this as the source of strategic priority.

When a directive is complete, move the file to `roadmap/directives/archived/` and remove it from the overview table.

### The pending-actions.md Discipline

`pending-actions.md` holds cross-repo tasks only - things that span multiple repos or are workspace-level. Never put repo-specific tasks here. Those go in that repo's IDEAS.md.

When a task is done: remove it from pending-actions.md, add a dated entry to completed-actions.md. Same discipline as IDEAS.md/HISTORY.md.

---

### Close Every Backlog Pass by Re-Ranking It

Adding items to a backlog is easy and everybody does it. Re-ranking one is rare, and it is where the value is: **a ranking made under no constraint is mostly an artefact of the order things were found in.**

Before closing any pass over a backlog, apply **one** extreme lens from [Part 12](12-audit-lenses.md) to the LIST rather than to the code, and write down what moved.

This is the cheapest step in the whole process and the only one that improves items you are not touching. One measured instance: asking "what would you fix if you could never touch this repo again" of a 180-item backlog promoted a bottom-tier item to first place, because an override flag that silently destroyed hand-edited work had been correctly tiered as polish under "how valuable is this" and was the most important item in the repo under "what is unrecoverable". Nothing was learned about the code.

"Nothing moved" is a real result and gets recorded as one.

---

## How IDEAS.md and /dev-session Work Together

IDEAS.md is the orchestrator. `/dev-session` (see Part 4) reads the priority ordering from IDEAS.md and picks the top actionable item. The session derives its purpose from the file, not from conversation context.

This is why keeping IDEAS.md well-ordered matters: it directly determines what Claude works on in every session. An ordered IDEAS.md means zero cognitive overhead at session start. A disordered one means the session burns tokens figuring out what to do next.
