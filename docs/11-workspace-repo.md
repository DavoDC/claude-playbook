# Part 11: The Workspace Repo

> Field notes, last reviewed 2026-05-24. Not mechanically asserted - see the README on what this repo guarantees.

The most important structural decision in this whole system is one that looks trivial: **always run Claude from the same git repo.**

Not a project repo. A dedicated workspace repo - a meta-repo whose only job is to hold your Claude config, memory, and skills.

---

## Why This Matters

Claude has no persistent memory. Every session starts completely cold. If you run Claude from a project repo, you get that project's CLAUDE.md and nothing else. When you start a new project, Claude has no idea how you like to work.

The workspace repo solves this with the simplest possible mechanism: **persistent memory = files in git + CLAUDE.md auto-load.**

Your preferences, corrections, and accumulated context live in one git-tracked place. Every session starts from there. Every correction you make compounds into the next session. When you switch to a new project, Claude still knows your rules, your style, your terminology.

---

## What Goes In It

The workspace repo is the home for everything that cuts across all your projects:

| What | Where | Why it's here |
|------|-------|---------------|
| Workspace CLAUDE.md | root | Auto-loaded every session - your universal rules |
| Enforced rules | `.claude/rules/enforced-rules.md` | Hard rules distilled from past failures |
| Skills | `.claude/skills/<name>/SKILL.md` | Reusable task instructions, available from any project |
| Feedback files | `memory/feedback/` | One rule per file, the improvement loop |
| Session history | `memory/session-history.md` | What you've worked on - context for next session |
| Memory index | `memory/MEMORY.md` | Navigation index to all memory files |

Project-specific content (what a particular repo does, how to build it, project constraints) lives in that project's own CLAUDE.md - not here.

---

## Setting One Up

Five minutes:

```bash
mkdir workspace
cd workspace
git init && git checkout -b main
mkdir -p .claude/rules .claude/skills memory/feedback
```

Copy `templates/CLAUDE_workspace.md` from this playbook to the root as `CLAUDE.md`. Copy `templates/enforced-rules.md` to `.claude/rules/enforced-rules.md`. Edit both to match how you actually work.

That's the workspace. Now always run Claude from this directory.

---

## Working on Projects From the Workspace

You have two options for working on a specific project:

**Option A - Run Claude from workspace, reference the project**

Claude starts with your workspace CLAUDE.md loaded. When it reads/edits files in a project repo, it uses absolute paths. Your workspace rules apply.

```
cd /your/workspace
claude
# Then: "look at /projects/myapp and fix the bug in auth.py"
```

**Option B - Run Claude from the project, extend the workspace CLAUDE.md**

Add a project CLAUDE.md that adds project-specific context. Your workspace CLAUDE.md doesn't load automatically here - but you can add a line to the project CLAUDE.md that points Claude at your workspace rules and asks it to read them.

Option A is simpler for small projects. Option B is better when the project has a lot of context that you always need loaded.

---

## The Compound Effect

The workspace repo is where the improvement loop actually runs. Each session:

1. Claude reads CLAUDE.md - knows your rules
2. Claude reads enforced-rules.md - knows the hard constraints
3. Claude reads session-history.md - knows what you worked on recently
4. Work happens
5. `/end-session` writes a session record, surfaces new feedback files, commits everything

Over time, the workspace becomes a detailed model of how you work. Not because of any AI feature - because of file persistence and the discipline of committing after every session.

---

## What NOT to Put Here

- **Project-specific code or context** - that goes in the project repo
- **Secrets, API keys, passwords** - use a secrets manager; keep them out of git
- **Private names, personal data** - if you ever make the workspace public, this is a liability
- **Temporary scratch files** - use a `TEMP/` folder with delete-after markers, not the main memory structure

---

## External Reference Repos (like the docs)

You'll sometimes want a local, read-only clone of something outside your own work - the official docs, a library you're reading source for, anything you pull but never push to. Keep these clones as siblings of the workspace repo, not nested inside it: a parent folder holding `workspace/` and `docs-repo/` next to each other, not `workspace/docs-repo/`.

This matters because "clone the docs locally" on its own is ambiguous - inside-the-workspace and beside-the-workspace are both reasonable readings of the same instruction, and any automation you build on top (a session-start hook that auto-pulls the clone, a skill that greps it) has to guess which one you meant. Guess wrong and the automation doesn't error, it just silently no-ops: the directory check fails, the pull never runs, and nothing tells you. State the convention explicitly - external reference repos live beside the workspace repo, one level up from it - and write any automation that depends on the path to fail loudly (print a warning, don't just skip) when it isn't found there, rather than degrading silently.

---

## Cross-Machine Sync

The workspace repo syncs across machines the same way any git repo does: commit and push. On a new machine, clone the workspace repo and run Claude from it. Your entire context - preferences, corrections, session history, skills - is immediately available.

This is the unsexy reason the workspace-repo pattern is non-negotiable: without it, each machine is a cold start. With it, every machine starts where you left off.

---

## GitHub Setup: Keep It Private

Push the workspace repo to GitHub, but **set it to private**. The content that accumulates here is not suited for a public repo - session history mentions what you worked on, feedback files document your specific failure modes, memory files contain personal context and preferences. Even things that seem innocuous (project names, internal tooling, working patterns) add up over time into a detailed picture you probably don't want public.

Private GitHub gives you all the sync benefits without the exposure risk. If you want to share your skills or config templates with others, the pattern for that is a separate public repo - exactly what this playbook is.
