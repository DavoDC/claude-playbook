---
description: Process a user feedback file with mandatory dual output - product tasks AND Claude learnings
---

# /process-feedback

Process a feedback file the user has written. Two passes are mandatory - both must complete.

**Usage:** `/process-feedback <filepath>`

---

## Step 0 - Rename the feedback file

Before reading the file, rename it to include the short commit SHA of the repo's latest commit. This ties the feedback to the exact codebase state it reflects.

```bash
cd <repo-dir>
git log --oneline -1 HEAD  # gives e.g. "bd4c939 fix: ..."
# Rename file from feedback.txt -> feedback_bd4c939.txt (use full 7-char short SHA)
```

Skip this step if the file is already named with a SHA (e.g. `feedback_bd4c939.txt`).

After renaming, **commit the renamed file immediately** before reading or processing it:

```bash
git add docs/Development/Feedback_*.txt  # or whatever path
git commit -m "chore: rename feedback file with commit SHA"
```

This preserves the raw feedback in git history before it is deleted.

---

## Pass 1 - Product tasks

Read the file. Extract all product bugs, feature requests, and UX issues.

Route each item:
- Bugs / features for an active project -> that repo's `docs/IDEAS.md` (quick wins first)
- Cross-repo tasks -> the cross-repo pending-actions file
- Completed fixes already in the codebase -> skip or note in HISTORY.md

**Optimization note:** Use ONE bash command to locate IDEAS.md: `cd <repo-dir> && find . -name "IDEAS.md" -type f`. Read the result directly.

## Pass 2 - Claude learnings (MANDATORY - skill fails if skipped)

Re-read the same file with a different question: **"What does each item reveal about where Claude fell short?"**

For each item ask:
1. Was this predictable from the spec/context available at the time?
2. Did Claude miss a pattern, skip a check, or make a wrong assumption?
3. What memory or rule would have prevented this?

Then:
- Write at least one `memory/feedback/feedback_<topic>.md` file capturing the Claude-behaviour learning
- Add a one-line pointer to MEMORY.md
- If nothing reveals a Claude failure (e.g. pure user preference change), state that explicitly - don't fabricate a learning

## Output

After both passes:

```
## /process-feedback complete

**File processed:** <path>

**Pass 1 - Product tasks:**
- <item> -> <destination>

**Pass 2 - Claude learnings:**
- <feedback file written> - <one-line summary>
- OR: No Claude failures identified - all items were [reason]

**Flag for deletion:** <filepath> (superseded by extracted items)
```

Flag the source file for deletion: if it lives inside a single repo, delete it directly (or note deletion in that repo's HISTORY.md). Never add single-repo file deletions to a cross-repo task list.

After deleting, **commit the deletion**:

```bash
git rm docs/Development/Feedback_*.txt
git commit -m "chore: delete processed feedback file"
```

The rename commit preserves the original content in history. The deletion commit closes the loop.
