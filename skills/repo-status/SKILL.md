---
description: Multi-repo status overview - branch, dirty file count, unpushed commits per repo. Read-only, never fetches.
effort: low
when_to_use: "Use before a container rebuild, session end, or when switching between repos to check for dirty files or unpushed commits across your workspace. Report, never fix - this skill surfaces state only."
---

# /repo-status - Multi-Repo Status Overview

Check the state of all repos in your workspace before a container rebuild, session end, or switching between repos.

## What it checks

For each repo in the configured directory:
1. Current branch
2. Uncommitted changes (dirty file count)
3. Unpushed commits (commits ahead of upstream)

Output as a compact markdown table:

| Repo | Branch | Dirty | Ahead |
|------|--------|-------|-------|

Flags:
- Any repo with dirty files
- Any repo with unpushed commits
- Any repo on an unexpected branch (e.g. not `main`)

Never fetches - no network requirement. Read-only.

## Implementation

```bash
# For each repo dir in your workspace root:
REPOS=$(ls -d /path/to/workspace/*/  2>/dev/null)

echo "| Repo | Branch | Dirty | Ahead |"
echo "|------|--------|-------|-------|"

for REPO in $REPOS; do
    [ -d "$REPO/.git" ] || continue
    NAME=$(basename "$REPO")
    BRANCH=$(git -C "$REPO" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")
    DIRTY=$(git -C "$REPO" status --short 2>/dev/null | wc -l | tr -d ' ')
    AHEAD=$(git -C "$REPO" rev-list --count "@{upstream}..HEAD" 2>/dev/null || echo "?")
    echo "| $NAME | $BRANCH | $DIRTY | $AHEAD |"
done
```

## Rules

- Report, never fix. This skill surfaces state only.
- If any repo has dirty=N or ahead>0, say so explicitly after the table.
- If a repo shows `?` for ahead (no upstream configured), note that as a gap.

## When to run

- Before destroying the development environment (pre-rebuild checklist)
- At session end, before closing the terminal
- When you think you might be on the wrong branch in any repo
