# Part 3: IDEAS.md, HISTORY.md, and the Roadmap System

> Field notes, last reviewed 2026-07-25. Not mechanically asserted - see the README on what this repo guarantees.

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

## How IDEAS.md and /dev-session Work Together

IDEAS.md is the orchestrator. `/dev-session` (see Part 4) reads the priority ordering from IDEAS.md and picks the top actionable item. The session derives its purpose from the file, not from conversation context.

This is why keeping IDEAS.md well-ordered matters: it directly determines what Claude works on in every session. An ordered IDEAS.md means zero cognitive overhead at session start. A disordered one means the session burns tokens figuring out what to do next.
