# Claude Playbook - Development Guide

This repo is **public**. Every file here is visible to anyone on GitHub.

---

## What belongs in this file vs elsewhere

**This file (public CLAUDE.md):** public-safe operational rules only - what never to include, when to update, commit message hygiene, no-internal-paths rule. A stranger reading this should find it useful without learning anything private.

**Workspace maintenance guide (private):** everything that cannot be public - SYNC safety specifics, skill classification, internal project names, incident notes. Located at `PRIVATE_NOTES/memory/playbook/maintenance.md` in the workspace repo. Read it before making any changes here.

**Workspace IDEAS file (private):** unshipped plans and TODOs. Located at `PRIVATE_NOTES/memory/playbook/IDEAS.md`. Never in this repo (only a pointer file lives here).

---

## Before making any changes

Read `PRIVATE_NOTES/memory/playbook/maintenance.md` in your workspace. It covers SYNC safety, skill sync approach, which skills to skip, and Ko-fi conventions.

---

## Core rule

**No personal data, no private paths, no workspace internals.** This means:
- No absolute user paths (`C:\Users\name\`, `/home/user/`)
- No internal project or tool names from private work
- No personal names
- No workspace-specific folder names (PRIVATE_NOTES/, PRIVATE_LOGS/, etc.)
- No private workflow names - use generic terms instead
- No attribution to private workflow sources in commit messages - describe content only

If you're unsure whether something is safe to include: don't include it.

---

## Playbook updates are manual-only

Never update this repo automatically. Only when explicitly asked.

---

## Commit message hygiene

Never include private source attribution in commit messages. Describe the content only. The commit-msg hook blocks: SYNC, PRIVATE_NOTES, PRIVATE_LOGS, From WORK, From HOME, WORK PC, HOME PC, PRIVATE_NOTES.

---

## Don't duplicate official Claude Code docs

The playbook's job is opinionated workflow guidance - when to use a feature, how it fits into your workflow, what actually works. Official Claude Code docs cover what features exist and how they work technically. Don't duplicate that.

**Rule:** When a playbook doc describes a Claude Code feature in detail, add a pointer:

```
(full reference: https://docs.anthropic.com/en/claude-code/[topic])
```

One sentence of workflow context + a pointer beats three paragraphs that go stale.

**Verify before documenting.** Never document a Claude Code feature from training knowledge alone. Check official docs first.

---

## No internal paths - use hyperlinks

**Never reference local workspace paths in this repo.** Readers do not have your file system.
- No local filesystem paths that only exist on your machine
- For Claude Code docs: link to `https://docs.anthropic.com/en/claude-code/[topic]`
- For skills in this repo: use relative links or full GitHub URLs
- Prefer hyperlinks over plain path text everywhere

---

## Structure

```
docs/         10-part guide
templates/    CLAUDE.md and enforced-rules starters
tools/        statusline.py, check-budget.sh, session-status.sh
skills/       skill SKILL.md files
IDEAS.md      pointer to private workspace IDEAS file
```
