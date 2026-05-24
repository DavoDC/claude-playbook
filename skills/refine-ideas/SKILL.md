---
description: Clarify IDEAS.md priorities by asking ONE question per item - Claude-driven, derives tiers from answers, works with any format
---

# /refine-ideas $ARGUMENTS

Optimize IDEAS.md by surfacing the ONE irreducible question: "Why is this necessary?" Groups items by answer, flags unclear ones, shows prioritization without enforcing format.

**Synergy:** `/prioritise` for pure ranking of an already-clear list (no grouping narration, just ranked output with justifications). Use `/refine-ideas` first when priorities are unclear; hand the output to `/prioritise` to rank within or across groups.

`$ARGUMENTS` = repo name or path. If none provided, uses current directory.

## Core Principle

**Good IDEAS.md = clarity on "why each item matters."** Tiers, formats, validation checklists are scaffolding. The real work is answering: "If we skip this item, what fails?"

**This skill does NOT impose a format.** It works on any existing structure (Pending/Future, Phase 1/2, TIER 0-4, unstructured narrative). It derives priorities FROM the why-necessary answer, not from tier labels.

---

## Phase 1: Locate repo & read IDEAS.md

1. Resolve repo path (check filesystem or use current directory)
2. Read `<repo>/docs/IDEAS.md`
3. Extract all items/ideas (any format)

---

## Phase 2: For each item, extract or ask ONE question

**Question:** "Why is this necessary? What fails if we skip it?"

For each item:
- If answer is already clear from the text -> extract it
- If answer is vague or missing -> ask Claude to infer it from context, flag as "NEEDS CLARIFICATION"

---

## Phase 3: Group items by answer type

Create 5 groups (not strict tiers, just groupings):

**Group 1: "Program fails without it"**
- Items with clear "program breaks" answers

**Group 2: "Needed for core workflow"**
- Items that enable other work

**Group 3: "Makes core workflow better"**
- Items that improve, don't enable

**Group 4: "Nice to have / Polish"**
- Items with "would be nice" answers

**Group 5: "Unclear or aspirational"**
- Items with vague/missing answers
- Items that contradict each other

---

## Phase 4: Present grouping to user

Show:
1. Current structure of IDEAS.md (what format is it using?)
2. Proposed grouping with why-necessary answers
3. Flagged items (unclear or contradictory answers)
4. Questions for the user:
   - "Does this grouping match your priorities?"
   - "Should any items move groups?"
   - "Any items to delete (unclear why they matter)?"

---

## Phase 5: User adjusts

User can:
- Accept grouping as-is
- Move items between groups
- Delete items ("that one doesn't matter anymore")
- Clarify answers

---

## Phase 6: Reformat and commit (optional)

If user wants standard TIER format:
- Group 1 -> TIER 0 (BLOCKING)
- Group 2 -> TIER 1 (MVP)
- Group 3 -> TIER 2 (QUALITY)
- Group 4 -> TIER 3 (POLISH)
- Group 5 -> TIER 4 (FUTURE) or DELETE

Reorganize file with tier headers, quick wins at top of each tier.

Commit: "refine: reorganize IDEAS.md by priority (group by why-necessary answers)"

---

## Key differences from format-first approaches

| Old approach | This skill |
|---|---|
| "Match best practices" | "Clarify why each item matters" |
| Validate against TIER structure | Derive tiers FROM answers |
| Claude assigns priorities | User answers; Claude surfaces contradictions |
| Format -> clarity | Clarity -> optional format |

---

## When to use

- IDEAS.md has 10+ items and priorities are unclear
- Ideas file uses old format and you want to modernize
- You have items marked "deprecated", "FIXME", "unclear" and need to decide what to do
- You want to focus on CORE workflow before touching EXTRA features

## When NOT to use

- Ideas file is already well-organized with clear answers to "why necessary?" - use `/prioritise` instead to rank it
- You're just adding one quick item
- You're doing exploratory work and don't need to prioritize yet
