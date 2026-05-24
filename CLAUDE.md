# Claude Playbook - Development Guide

This repo is **public**. Every file here is visible to anyone on GitHub.

## Before making any changes

Read the full maintenance guide before editing anything in this repo. To find it:

1. Check your workspace's `.claude/rules/enforced-rules.md` for the rule named **"claude-playbook updates - manual only"**
2. That rule contains the exact path to `playbook-maintenance.md` in your workspace
3. The maintenance guide starts with a backlink confirming it's the right file

The guide covers what content is safe to add, skill sync approach, which skills to skip, and Ko-fi conventions.

## Core rule

**No personal data, no private paths, no workspace internals.** This means:
- No absolute user paths (`C:\Users\name\`, `/home/user/`)
- No internal project/tool names from private work
- No personal names
- No workspace-specific folder names (PRIVATE_NOTES/, PRIVATE_LOGS/, etc.)

If you're unsure whether something is safe to include: don't include it.

## Playbook updates are manual-only

Never update this repo automatically. Only when explicitly asked.

## Don't duplicate official Claude Code docs

The playbook's job is opinionated workflow guidance - when to use a feature, how it fits into your workflow, what actually works. Official Claude Code docs document what features exist and how they work technically. Don't duplicate that.

**Rule:** When a playbook doc describes a Claude Code feature in detail, add a pointer:

```
(full reference: https://docs.anthropic.com/en/claude-code/[topic])
```

One sentence of workflow context + a pointer beats three paragraphs that go stale.

**Verify before documenting.** Never document a Claude Code feature from training knowledge alone. Check official docs first - features change, and a stale description in the playbook misleads every reader who follows it. If you find the local `claude-code-docs` clone in your workspace, check that first.

## Structure

```
docs/         10-part guide
templates/    CLAUDE.md and enforced-rules starters
tools/        statusline.py, check-budget.sh, session-status.sh
skills/       21 skill SKILL.md files
```
