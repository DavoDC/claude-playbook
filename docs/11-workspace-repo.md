# Part 11: The Workspace Repo

> **Core.** Part of the maintained quick-start path. The tools and settings snippets it references are asserted by `tools/selftest.sh` on every push.

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

## Secrets That Get Into Git Anyway

Keeping secrets out of git (above) is the design-time rule. Two things go wrong even when you follow it.

**An exact-path gitignore rule protects the file, not the secret.** `config/config.json` in `.gitignore` stops that one file from being staged, but it does not follow the file when a copy is made - and a copy is exactly what a credential rotation or migration produces, as a `.bak`, a suffixed backup, or an editor copy. The copy is usually the one holding the fresher secret, and it sails past a rule that looks like it covers this case. Write ignore rules for anything holding a live credential as a glob (`config.json*`, not `config.json`), and verify coverage with `git check-ignore -v <path>` rather than assuming - a rule that looks right and a rule that matches are different things, and the two diverge most often during exactly the operations, rotations and migrations, where the file being copied is most valuable.

**A history rewrite that verifies clean is not necessarily finished.** `git filter-repo` (or `filter-branch`) plus a force push removes the offending commits from the remote, but it does not remove the local objects - anything still named by a reflog entry stays reachable, and the default reflog expiry holds those entries for months. Worse, a GUI git client that syncs in the background can run a fetch in the gap between the rewrite and the push, pull the un-rewritten history back from a remote that has not been updated yet, and silently restore the removed objects to the local store - `git fsck --unreachable` will not catch this, because it respects reflogs. Treat the rewrite as finished only after: push, then `git reflog expire --expire=now --expire-unreachable=now --all`, then `git gc --prune=now`. Check with `du -sh .git` or `git count-objects -vH` before and after, rather than trusting a tool that respects reflogs. The dangerous window is the gap between the rewrite and the push - avoid touching a background-syncing GUI client during it, or push promptly enough to close the window.

---

## External Reference Repos (like the docs)

You'll sometimes want a local, read-only clone of something outside your own work - the official docs, a library you're reading source for, anything you pull but never push to. Keep these clones as siblings of the workspace repo, not nested inside it: a parent folder holding `workspace/` and `docs-repo/` next to each other, not `workspace/docs-repo/`.

This matters because "clone the docs locally" on its own is ambiguous - inside-the-workspace and beside-the-workspace are both reasonable readings of the same instruction, and any automation you build on top (a session-start hook that auto-pulls the clone, a skill that greps it) has to guess which one you meant. Guess wrong and the automation doesn't error, it just silently no-ops: the directory check fails, the pull never runs, and nothing tells you. State the convention explicitly - external reference repos live beside the workspace repo, one level up from it - and write any automation that depends on the path to fail loudly (print a warning, don't just skip) when it isn't found there, rather than degrading silently.

### Read Locally, Cite Officially

A local clone and the official docs site do different jobs, and neither replaces the other. The clone is what you read from, because one grep searches the whole corpus at once and answers the question you actually have: does this feature exist anywhere, and under what name. Fetching a page cannot answer that, since it requires you to already know which page holds the answer - which is the thing you were trying to find out. Offline access and the absence of a network round trip per lookup are real but secondary; the searchability is the point. The official site is what you cite: a pointer written for a reader who has no clone has to be the public URL, never a path into your copy.

Choosing a mirror is worth ten minutes once. The criteria that matter, in order: it stores plain markdown you can grep, rather than an index that fetches pages on demand, since an on-demand index reintroduces exactly the per-page fetch the clone exists to avoid; it is refreshed by a scheduled job rather than by hand, and you can read the schedule in the workflow file before trusting it; it is scoped to the documentation you actually want, because a mirror that also sweeps in blog posts and cookbooks gives every grep more to wade through; and it records provenance per file, ideally the source URL, a content hash and a fetch timestamp, so staleness becomes something you can detect instead of something you hope about.

Judge freshness by the date of the last commit, never by the repository's displayed update time. That field moves on any repository event and one popular-looking mirror shows a recent update while its content has not changed since spring. This is a small instance of a general habit: check the field that means what you need, not the one that is easiest to see.

Pull the clone before every read, and treat pull-then-grep as one operation. A mirror that is behind does not error, it answers from whatever was on disk the last time you pulled, and nothing in the output distinguishes that from a current answer. A fetched page cannot fail this way, because if it is wrong it is wrong now rather than wrong as of some date you never recorded. Community mirrors are unofficial and can lag the source, and that is the reason the pull is part of the rule rather than a performance tip.

---

## Cross-Machine Sync

The workspace repo syncs across machines the same way any git repo does: commit and push. On a new machine, clone the workspace repo and run Claude from it. Your entire context - preferences, corrections, session history, skills - is immediately available.

This is the unsexy reason the workspace-repo pattern is non-negotiable: without it, each machine is a cold start. With it, every machine starts where you left off.

---

## GitHub Setup: Keep It Private

Push the workspace repo to GitHub, but **set it to private**. The content that accumulates here is not suited for a public repo - session history mentions what you worked on, feedback files document your specific failure modes, memory files contain personal context and preferences. Even things that seem innocuous (project names, internal tooling, working patterns) add up over time into a detailed picture you probably don't want public.

Private GitHub gives you all the sync benefits without the exposure risk. If you want to share your skills or config templates with others, the pattern for that is a separate public repo - exactly what this playbook is.

---

## Publishing Is Not Distribution

Making a repo public, adding a donation badge, writing a licence, or cutting a release changes who is *allowed* to find your work. None of those acts changes whether anyone *does*. It is worth naming this explicitly because publishing work is uniquely seductive to track as progress: it is legible, fully within your own control, and you can tick it off in one sitting. A distribution act - a post, an announcement, actually asking someone to look - is uncomfortable in exactly the ways publishing is not: it involves a stranger, it can be ignored, and it produces a number you might not like. So a plan quietly refills with the comfortable half indefinitely.

The mechanism is worth stating plainly, because it survives any amount of diligence on the publishing side. A checklist can be fully complete - licence added, README written, hardcoded paths removed, repo flipped public - and still not have told a single human being that the thing exists. Every task on that list changes the artifact. None of them reaches a person. So a completed publishing checklist reads like progress toward an audience while being, by construction, entirely orthogonal to one.

Before adding a publishing task to a plan, ask what distribution act it is a precondition for, and schedule that act in the same breath. A licence with no announcement behind it is not a step toward reach. And if a reach goal has been open for a long stretch with nothing to show, do not conclude that more supply is needed - check first whether any distribution act has ever actually been performed. Publishing tasks are portfolio hygiene: worth doing, never worth counting as progress toward an audience.
