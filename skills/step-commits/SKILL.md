---
description: Plan changes as atomic commits upfront, then implement and commit one at a time
effort: medium
when_to_use: "Use when starting a multi-change implementation session. Forces atomic commits by planning the full split BEFORE writing any code - each change gets its own commit. For already-dirty trees with multiple topics, use /commit-chunks instead. For a single-topic dirty tree, use /commit-all. To undo planned commits that went wrong, use /undo-commits."
---

# Step Commits - One Change, One Commit

Use this when implementing multiple changes in one session. Forces atomic commits
by planning the split BEFORE writing any code. Prevents the anti-pattern of one
large commit with 5+ unrelated bullet points.

| Skill | When to use |
|-------|-------------|
| `/commit-all` | tree already dirty, one topic, one commit |
| `/commit-chunks` | tree already dirty, multiple topics, split post-hoc |
| `/step-commits` | nothing implemented yet, plan atomic commits UPFRONT |

## Steps

1. **List all planned changes** as a numbered atomic commit plan. Each item = one commit.
   - One change = one observable effect on program behaviour
   - Split by: fix A / fix B / feat C / refactor D - never bundle these
   - Show the list to the user and confirm before writing any code

2. **For each item in order:**
   a. Implement ONLY that change - nothing else, even if you notice something nearby
   b. Immediately commit with a message that describes just that one effect
   c. Say "Committed [N/total]: <message>" so user tracks progress
   d. Move to next item

3. **If you notice an unplanned fix while implementing** - do NOT apply it.
   Add it to the end of the list and continue. Never mix an unplanned change
   into an in-progress commit.

## Commit message rules

- One line, under 72 chars
- Imperative, present tense ("fix X", "add Y", "move Z")
- Describes the USER-VISIBLE effect, not the code change
- No em dashes, no bullet points in the subject line
- Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

## What counts as "one change"

Aim for 1-3 related things per commit. Don't go so granular that "add blank line"
is its own commit - that's noise. The test: can you describe the commit's effect in
one plain sentence without using "and" to join unrelated ideas?

GOOD (tight, describable in one line):
- "move header to print before file loading" (one move, clear effect)
- "add 3-way per-clip review: y include / a archive / d delete" (one feature, coherent)
- "add blank lines and align Video/Leftover labels" (two cosmetic tweaks, same concern)

BAD (too much, needs "and" to describe unrelated things):
- "header first, per-clip y/a/d review, spacing, archive helper, feedback file deleted"

## When changes are already applied together (recovery)

If you already implemented multiple changes in one batch:
1. Note it happened - don't hide it
2. For the NEXT set of changes, use /step-commits from the start
3. Do NOT try to undo and re-apply just to get clean commits - the value is in future sessions, not fixups
