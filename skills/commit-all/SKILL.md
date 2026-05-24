---
description: Commit all files in git status to this repo - stages everything, writes commit message, no push
effort: low
disable-model-invocation: true
when_to_use: "Use when all dirty files belong to a single topic and can be committed together. If there are multiple unrelated topics in the dirty tree, use /commit-chunks instead. If planning commits BEFORE writing code, use /step-commits."
---

# Commit All

One-shot commit of everything in `git status`. No planning, no splitting. Use
`/commit-chunks` when there are multiple topics in the dirty tree.

## Steps

1. `git status` - see dirty + untracked files
2. `git diff` for unstaged changes, `git log --oneline -5` if you need the
   recent commit-message style
3. Skip anything sensitive (`.env`, credentials, large binaries). Stage the
   rest by name: `git add <file1> <file2> ...`
4. Write a 1-2 sentence commit message focusing on WHY (not what)
5. Commit following commit-mechanics: staging verification, pathspec form,
   message format, and Co-Authored-By
6. `git status` after, to confirm the tree is clean

Do NOT ask for confirmation - just do it. Do NOT push.

## Rules

- Commit message should be one line, under 72 chars
- Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com> on every commit
- If nothing to commit, say so and stop
