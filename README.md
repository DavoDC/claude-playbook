# Claude Playbook

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/G2G31WKOCN)

Budget-aware, self-improving Claude Code. Built from hundreds of sessions of daily use across multiple projects. Not theory - distilled from what actually worked and what didn't.

---

## The Three Gaps This Fills

By default, Claude Code has three significant gaps that most users don't notice until they're badly bitten by them:

**1. No budget awareness**

Claude has no idea whether it's at 5% or 95% of its rate limits. It will happily start a 3-hour overnight loop at 82% of its 5-hour quota and wonder why it gets throttled. The `tools/` in this repo surface that data and make decisions based on it - before any work starts.

**2. No improvement memory**

Every correction you make in a session evaporates at the end. You end up correcting the same behaviours repeatedly across months. The feedback_*.md system creates a library of rules calibrated to your actual failure modes - not generic advice, but the specific mistakes that happen in your work.

**3. No structured work selection**

Without a priority queue, Claude works on whatever is in front of it - often the wrong thing. The /dev-session + IDEAS.md pattern gives it a scope contract and a priority-ordered list before any code is written. It picks the top actionable item; you don't have to direct it.

---

## Quick Start (15 minutes to first value)

**Step 1 - Workspace CLAUDE.md (5 min)**

Copy `templates/CLAUDE_workspace.md` to your workspace root as `CLAUDE.md`. Read through it and edit the sections to fit how you actually work. Delete anything that doesn't apply.

**Step 2 - Enforced rules (2 min)**

Copy `templates/enforced-rules.md` to `.claude/rules/enforced-rules.md`. This file is auto-loaded by Claude Code and applies everywhere.

**Step 3 - Install the statusline (5 min)**

Copy `tools/` to somewhere in your workspace. In `.claude/settings.json`, add:

```json
{
  "statusline": {
    "command": "python3 /path/to/tools/statusline.py"
  }
}
```

Claude Code passes its current status JSON to this script on every update. The script (1) displays it in your terminal statusline, (2) writes it to a temp file so other scripts can read budget state without API calls.

**Step 4 - Write your first feedback file (3 min)**

The next time Claude does something you correct: write `memory/feedback/feedback_<topic>.md`. Rule + why + how to apply. Commit it. That's the improvement loop started.

---

## What's Here

| Path | What it is |
|------|------------|
| `docs/` | Full guide split by topic - start with `01-claude-md.md` |
| `templates/` | Ready-to-use CLAUDE.md and enforced-rules starters |
| `tools/` | statusline.py, check-budget.sh, session-status.sh |
| `skills/` | skill files - thinking, git, review, and workflow tools |

---

## Guide Index

| File | Contents |
|------|----------|
| [01 - The CLAUDE.md Layer](docs/01-claude-md.md) | Workspace and project CLAUDE.md - what goes where and why |
| [02 - The Improvement Loop](docs/02-improvement-loop.md) | Enforced rules, feedback files, the rule promotion hierarchy |
| [03 - IDEAS.md and Roadmap](docs/03-ideas-and-roadmap.md) | Priority queue, HISTORY.md archive, the roadmap layer |
| [04 - The /dev-session Skill](docs/04-dev-session.md) | Phase walkthrough, TDD gate, scope definition, rule capture |
| [05 - Budget Awareness](docs/05-budget-awareness.md) | The three budget axes, what session-status.sh does, how to build it |
| [06 - Sessions and Memory](docs/06-sessions-and-memory.md) | /end-session, session fragments, the file-based memory system |
| [07 - The Overnight Loop](docs/07-overnight-loop.md) | /loop + /dev-session, /checkpoint restore points |
| [08 - Skills Reference](docs/08-skills.md) | All skills sorted by actual usage count |
| [09 - Hooks](docs/09-hooks.md) | Write guard, budget monitor, session logger, settings split |
| [10 - Advanced Patterns](docs/10-advanced.md) | Commit-anchored delta, worked examples |
| [Checklist](docs/checklist.md) | Building the full system - what to build in what order |

---

## The Honest Caveat

This took months to build incrementally. The templates and tools shortcut that time considerably - you get a working budget-aware statusline on day one instead of month three. But the real return comes from the discipline: running /end-session every session, writing a feedback file every time you correct Claude, keeping IDEAS.md ordered.

The templates don't compound. The habit does.

---

## Skill Files

The `skills/` folder contains skills covering first-principles thinking (`/aristotle`, `/think`), git workflow (`/commit-chunks`, `/step-commits`, `/undo-commits`), code review (`/deep-dive`, `/survey-repo`, `/cross-synth`), writing (`/human-voice`), and more.

To install: copy a skill folder to `.claude/skills/<name>/` in your workspace. Claude Code makes it available as `/<name>`.

See `skills/README.md` for the full list and descriptions.

---
