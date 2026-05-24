# Claude Playbook - Development Guide

This repo is **public**. Every file here is visible to anyone on GitHub.

## Before making any changes

Read the full maintenance guide in your workspace before editing anything in this repo. It covers:
- What content is safe to add (and what isn't)
- How to sync skills from workspace to playbook
- Which skills to skip (too workspace/work-specific)
- Ko-fi and public repo conventions

The maintenance guide path is workspace-internal and not listed here intentionally.

## Core rule

**No personal data, no private paths, no workspace internals.** This means:
- No absolute user paths (`C:\Users\name\`, `/home/user/`)
- No internal project/tool names from private work
- No personal names
- No workspace-specific folder names (PRIVATE_NOTES/, PRIVATE_LOGS/, etc.)

If you're unsure whether something is safe to include: don't include it.

## Playbook updates are manual-only

Never update this repo automatically. Only when explicitly asked.

## Structure

```
docs/         10-part guide
templates/    CLAUDE.md and enforced-rules starters
tools/        statusline.py, check-budget.sh, session-status.sh
skills/       21 skill SKILL.md files
```
