# Claude Playbook - Development Guide

This repo is **public**. Every file here is visible to anyone on GitHub.

---

## What belongs in this file vs elsewhere

**This file (public CLAUDE.md):** public-safe operational rules only - what never to include, when to update, commit message hygiene, no-internal-paths rule. A stranger reading this should find it useful without learning anything private.

**Workspace maintenance guide (private):** everything that cannot be public - safety specifics for syncing between environments, skill classification, internal project names, incident notes. Kept privately in your own workspace repo, never here. Read it before making any changes here.

**Workspace IDEAS file (private):** unshipped plans and TODOs. Kept privately in your own workspace repo, never here (only a pointer file lives in this repo).

---

## Before making any changes

Read your private maintenance guide in your workspace. It covers safety for syncing between environments, skill sync approach, which skills to skip, and Ko-fi conventions.

---

## Core rule

**No personal data, no private paths, no workspace internals.** This means:
- No absolute user paths (`C:\Users\name\`, `/home/user/`)
- No internal project or tool names from private work
- No personal names
- No folder names specific to your private workspace repo
- No private workflow names - use generic terms instead
- No attribution to private workflow sources in commit messages - describe content only

If you're unsure whether something is safe to include: don't include it.

---

## Playbook updates are manual-only

Never update this repo automatically. Only when explicitly asked.

---

## Commit message hygiene

Never include private source attribution in commit messages. Describe the content only. The commit-msg hook blocks a set of private source-attribution terms; the term list lives in the hook itself, out of this repo.

---

## Don't duplicate official Claude Code docs

The playbook's job is opinionated workflow guidance - when to use a feature, how it fits into your workflow, what actually works. Official Claude Code docs cover what features exist and how they work technically. Don't duplicate that.

Duplication means restating what the docs say inside playbook prose, where the restatement goes stale the moment the feature changes underneath it. Keeping a pulled local clone of the docs to read from is the opposite of duplication - it's how you avoid restating from memory in the first place, by checking the current source instead of trusting what you wrote down last time.

**Rule:** When a playbook doc describes a Claude Code feature in detail, add a pointer:

```
(full reference: https://code.claude.com/docs/en/[topic])
```

One sentence of workflow context + a pointer beats three paragraphs that go stale.

**Verify before documenting.** Never document a Claude Code feature from training knowledge alone. Check official docs first.

**Stamp what the docs don't cover.** If a claim describes official Claude Code feature behavior, point at the docs page for it - don't restate it from memory. If a claim describes something observed in practice that no official page covers, say so explicitly: name the Claude Code version and platform it was observed on, so a reader can discount an old observation instead of trusting it at face value. Behaviour is tested, not remembered, and an unstamped claim reads with the same confidence as a documented one even when it is neither.

**Update the existing entry point rather than adding a second one.** When a new capability looks like a variant of something that already exists, whether that is a skill, a script, a launcher or a flag, change the existing one. A second entry point over the same capability splits its users across two levels of quality, and its only real power is letting someone pick wrong. If the environment already determines the right setting, bake it in rather than offering the choice.

**A number that is printed is not a number that is checked.** Every count, total, duration and success word a tool prints should be traced back to what it actually counts, at least once. Three separate cases sat in plain output for months and were missed because no one had ever asked whether the value was right, only whether the command ran.

---

## No internal paths - use hyperlinks

**Never reference local workspace paths in this repo.** Readers do not have your file system.
- No local filesystem paths that only exist on your machine
- For Claude Code docs: link to `https://code.claude.com/docs/en/[topic]`
- For skills in this repo: use relative links or full GitHub URLs
- Prefer hyperlinks over plain path text everywhere

---

## Structure

```
docs/         the guide, split by topic, numbered
templates/    CLAUDE.md and enforced-rules starters
tools/        statusline, budget and session-status scripts, plus a launcher
skills/       skill SKILL.md files
```
