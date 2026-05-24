---
description: Rank any list or named backlog by leverage using Aristotle's "who benefits and are they a bottleneck?" lens. Returns a ranked list with one-line justification per item.
effort: low
argument-hint: "[backlog | pending | <inline list>]"
when_to_use: "Use when you want to rank a list, prioritise a backlog, or decide what order to do things. Aristotle is the engine; this is the focused interface for pure ranking tasks - no full 5-phase narration, just the ranked output. Synergy: /aristotle for deep design decisions, /reflection to surface ordering improvements."
---

# /prioritise $ARGUMENTS

Rank a list by leverage. Aristotle is the engine. This skill is the focused interface - it skips the full 5-phase narration and delivers a ranked list with one-line justification per item.

**Synergy:** `/aristotle` for deep design decisions (full 5-phase). `/reflection` to identify what ordering improvements to make. When /aristotle is already running, redirect pure ranking requests here instead.

## Parsing args

| Input | Action |
|-------|--------|
| `backlog` / `ideas` | Read the project's IDEAS.md or backlog |
| `pending` | Read all open items from the task list |
| Inline list (paste items) | Use those items directly |
| No args | Ask: "What are you prioritising? Paste your list or name the file." |

## Steps

1. **Load the items.** Read from the named backlog or use inline list. Strip completed and blocked items. Show count: "Ranking N items."

2. **Apply the Aristotle leverage lens** (condensed - no narration):

   For each item, silently ask:
   - **Who benefits?** Team-wide > user-only > future-you
   - **Are they a bottleneck?** Does this unblock other people or other work?
   - **Irreversibility:** Hard-deadline or drifts-worse-over-time items float up
   - **Effort vs unlock ratio:** Low-effort items that unblock high-value work > high-effort items with contained value

   Classify into tiers:
   - **T1** - multiplier: benefits others or unblocks shared work
   - **T2** - infrastructure risk: you-only but prevents future pain or has hard deadline
   - **T3** - personal tooling: no deadline, no bottleneck

3. **Output the ranked list.** Format:

   ```
   ## Ranked (N items)

   **T1 - Multipliers (unblocks others)**
   1. [Item name] - [one-line justification: who benefits + why now]
   2. ...

   **T2 - Infrastructure / risk**
   3. [Item name] - [one-line justification]
   ...

   **T3 - Personal tooling (yield to any T1/T2)**
   N. [Item name] - [one-line justification]
   ```

4. **Ask:** "Want me to reorder the file to match this ranking?" If yes, update and commit.

## Rules

- **Never reorder without asking first** - ranking is an opinion, the file is the truth.
- **Show your reasoning** in the one-line justification - don't just rank, say WHY.
- **Blocked items stay blocked** - don't surface them as high-priority just because they were before being blocked.
- **Short list (< 5 items):** skip tier headers, just rank 1-N with justifications.
- **If two items tie on leverage:** prefer the one with lower effort and fewer dependencies.
