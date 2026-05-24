---
description: Commit changed files in logical chunks - one commit per feature/fix/topic
---

# Commit in Logical Chunks

Review all staged and unstaged changes in the current repo, then group them into logical commits and execute them one at a time.

## Steps

1. Run `git status` and `git diff` to see all changes
2. Group changed files by topic/feature/fix into logical chunks (e.g. "feat: X", "fix: Y", "data: Z")
3. For each chunk in order:
   - Stage only the files for that chunk
   - Write a concise commit message (imperative, present tense, no em dashes)
   - Commit with Co-Authored-By trailer
4. After all commits, confirm what was committed

## Rules

- Never batch unrelated changes in one commit
- One feature = one commit, one fix = one commit, one data update = one commit
- Generated/output files (reports, logs, cache) are separate from the script that generated them
- Co-Authored-By line: use the active Claude model, e.g. `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>` on every commit.

## File moves - split into two commits

When files are moved to a new location:
1. **Move commit first** - only the move + minimum path fixes to make the file work from its new location. Nothing else. This keeps the diff small enough for git to detect the rename.
2. **Content edits second** - comments, rewrites, or any other changes as a separate follow-up commit.

If move and content edits are batched together, git reports the file as deleted+created instead of renamed, which loses history. Treat any rename/move as its own chunk before any content changes.
