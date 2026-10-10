# Part 3: IDEAS.md, HISTORY.md, and the Roadmap System

> **Core.** Part of the maintained quick-start path. The tools and settings snippets it references are asserted by `tools/selftest.sh` on every push.

## IDEAS.md - The Priority Queue

Every project repo gets a `docs/IDEAS.md`. It is the forward-looking priority list for that repo - the single source of truth for "what to work on next."

Rules that make it work:
- Ordered by priority (not by when you added them)
- Use semantic tiers: TIER 0 (blocking/critical) through TIER 4 (parked). Full specification, and the `tools/backlog.py` editor that enforces it: `templates/BACKLOG-SPEC.md`
- When something ships: remove from IDEAS.md, add a dated entry to `docs/HISTORY.md`
- Never mark done with checkmarks and leave the entry - remove completely

`HISTORY.md` is the archive of everything that shipped. When you ask "how did we implement X before?" Claude can read HISTORY.md without wading through the active list.

This split (active vs archived) keeps IDEAS.md clean and usable. A list that keeps growing without anything leaving it stops being useful quickly.

One placement note if you fork this playbook: keep your own ideas somewhere private (your workspace repo, a private gist, a local file outside the repo), not in the public fork. A backlog is the most context-leaking file you own - it names unreleased work, internal systems, and people. Public repos take bug reports and feature suggestions through Issues instead.

### Why the Removal Discipline Matters

Marking done with `[x]` pollutes the active list: when Claude reads IDEAS.md to pick the next item, it has to filter out what is already done. Remove entries cleanly; the git history is the record.

### Semantic Tiers Over Phase Numbering

Numbering phases ("Phase 1", "Phase 2") creates pressure to complete them in order even when priorities change. Semantic tiers communicate what matters and why, and when budget is tight, the decision is easy: TIER 0 only.

**Keep the specification in ONE file and point every backlog at it.** Copy the convention into each repo's backlog and you have created N copies that will disagree within a month, and improving the process becomes N edits instead of one. The full tier definitions, the routing table for which list an item belongs on, the one question that derives a tier, and the re-ranking discipline all live in `templates/BACKLOG-SPEC.md` - not repeated here.

Tiers, templates and validation checklists are scaffolding. The clarity is the work.

### Check What the Platform Already Does For Free Before Adding an Item

**Before writing a new automation item onto IDEAS.md, state explicitly what the underlying platform already does without it, and what the increment is actually worth.** A backlog item is a proposal to spend build time, and time spent duplicating what the platform already does on its own timeline is a net loss even when the tool works perfectly. If the honest answer to "what does this buy that isn't already happening" is only "sooner" or "tidier," close the item with that finding written down, as a shipped item gets a HISTORY.md entry. The check is cheap and easy to skip because the platform's existing behavior is rarely documented where the backlog author looks; one cleanup automation got partway through implementation before discovering the platform already purged the exact folder it targeted, on a schedule of its own.

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

Adding items to a backlog is easy and everybody does it. Re-ranking is rare, and it is where the value is - a ranking made under no constraint is mostly an artefact of the order things were found in. The re-ranking discipline (apply one extreme lens to the LIST, write down what moved) is specified in `templates/BACKLOG-SPEC.md`; the lens comes from [Part 11](11-audit-lenses.md).

That periodic pass catches gradual drift. A sharper trigger needs its own check: **when a new capability lands - a tool, a permission, an integration, anything that removes a constraint that used to be true - re-check which plan steps were ordered that way only because of the constraint that just disappeared.** An ordering written under an old constraint keeps being followed after it stops being true, because nothing forces a re-read of the reasoning behind a step already scoped correctly at the time. One plan ordered "search after OCR" because the records weren't machine-readable yet; an unrelated tool made many of them machine-readable as a side effect, and the ordering was obeyed anyway until someone re-checked it. Treat a landed capability as a prompt to re-open every item whose ordering depended on its absence, not just a green light for whatever it directly unblocks.

---

## How IDEAS.md Drives a Session

IDEAS.md is the orchestrator. A session that starts by reading the priority ordering in IDEAS.md and taking the top actionable item derives its purpose from the file, not from conversation context.

Its ordering directly determines what Claude works on in every session. An ordered IDEAS.md means zero overhead at session start; a disordered one burns tokens figuring out what to do next.
