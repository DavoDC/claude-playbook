# Claude Playbook

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/G2G31WKOCN) [![selftest](https://github.com/DavoDC/claude-playbook/actions/workflows/selftest.yml/badge.svg)](https://github.com/DavoDC/claude-playbook/actions/workflows/selftest.yml)

For people who use Claude Code daily and are tired of re-correcting the same mistakes and hitting rate limits mid-task: a budget-aware, self-improving setup, distilled from sustained real use across multiple projects. Not theory - what actually worked and what didn't.

---

## The Three Gaps This Fills

Out of the box, Claude Code lacks three things, and each one costs you time until you add it:

**1. No improvement memory**

Every correction you make in a session evaporates at the end. You end up correcting the same behaviours repeatedly across months. The feedback_*.md system creates a library of rules calibrated to your actual failure modes - not generic advice, but the specific mistakes that happen in your work.

**2. No budget awareness**

Claude has no idea whether it's at 5% or 95% of its rate limits. It will happily start a 3-hour overnight loop at 82% of its 5-hour quota and wonder why it gets throttled. The `tools/` in this repo surface that data and make decisions based on it - before any work starts.

**3. No structured work selection**

Without a priority queue, Claude works on whatever is in front of it - often the wrong thing. An IDEAS.md priority queue gives it a scope contract and a priority-ordered list before any code is written. It picks the top actionable item; you don't have to direct it.

---

## Quick Start (15 minutes to first value)

**Step 1 - Workspace CLAUDE.md (5 min)**

Copy `templates/CLAUDE_workspace.md` to your workspace root as `CLAUDE.md`. Read through it and edit the sections to fit how you actually work. Delete anything that doesn't apply.

**Step 2 - Enforced rules (2 min)**

Copy `templates/enforced-rules.md` to `.claude/rules/enforced-rules.md`. It applies everywhere (load behaviour: [Part 1](docs/01-claude-md.md)).

**Step 3 - Install the statusline (5 min)**

Copy `tools/` to somewhere in your workspace. In `.claude/settings.json`, add:

```json
{
  "statusLine": {
    "type": "command",
    "command": "python /path/to/tools/statusline.py"
  }
}
```

Both details matter: the key is camelCase, and `"type": "command"` is required. Get either wrong and Claude Code ignores the block without complaining, the cache file below is never written, and every budget check in this playbook silently reports no data instead of failing (full reference: https://code.claude.com/docs/en/statusline).

Claude Code passes its current status JSON to this script on every update. The script (1) displays it in your terminal statusline, (2) writes it to a temp file so other scripts can read budget state without API calls.

**Step 4 - Write your first feedback file (3 min)**

The next time Claude does something you correct: write `memory/feedback/feedback_<topic>.md`. Rule + why + how to apply. Commit it. That's the improvement loop started.

**Step 5 - Install the privacy hooks (1 min)**

Run `sh hooks/install.sh` once after cloning. `.git/hooks/` is never tracked, so a fresh clone has no protection until you do. Add your own private terms, one per line, to `.git/private-terms.txt`; that file stays on your machine.

---

## The Workspace Repo

Everything in this playbook assumes you run Claude from one dedicated git repo - a "workspace repo." Not a project repo. A meta-repo that holds your config, memory, and skills.

```
workspace/          <- you always run Claude from here
  CLAUDE.md         <- your rules, loaded every session automatically
  .claude/
    rules/
      enforced-rules.md
    skills/         <- your custom slash commands
  memory/
    feedback/       <- accumulated corrections, one rule per file
    session-history.md
    MEMORY.md
```

**Why not just use a project repo?** If your preferences live in a project repo, they disappear when you start a new project. With a workspace repo, every session starts with your rules loaded, your skills available, and context from past sessions. Every correction you make to Claude compounds across all future sessions and all projects.

The whole system depends on this one structural choice. See `docs/12-workspace-repo.md` for the full setup guide.

---

## What's Guaranteed vs What's Field Notes

`tools/`, `templates/`, and every settings.json snippet documented in these docs are the asserted core - `tools/selftest.sh` checks all three on every push, so a typo in any copied-out snippet fails CI. Run it yourself in seconds: `bash tools/selftest.sh`.

Within `docs/`, each file is marked Core or Field note right under its heading (see the Tier column below). Core files reference only the tools and settings snippets covered by that same `selftest.sh` run. Field note files are dated observations from real use, useful but not mechanically verified - Claude Code's harness ships continuously, so any such claim about how it behaves is a snapshot, not a permanent fact, which is why each one carries the date it was last reviewed.

---

## What's Here

| Path | What it is |
|------|------------|
| `docs/` | Full guide split by topic - start with `01-claude-md.md` |
| `templates/` | Ready-to-use CLAUDE.md, enforced-rules and backlog (IDEAS/HISTORY) starters |
| `tools/` | statusline, budget and session-status scripts, loop-health measurement, the `backlog.py` backlog editor (spec: `templates/BACKLOG-SPEC.md`, config: `config/backlog.example.json`), the `doc_lint/` config-driven doc linter (ruleset: `tools/doc_lint/doc_lint.config.json`), the `check-capacity.py` file and group size checker (config: `config/capacity.example.json`), the `scratch-overdue.py` delete-after marker checker, the `prose-lint.py` wrap, dash and commit-subject linter, plus a launcher |
| `skills/` | skill files - thinking, git, review, and workflow tools |
| `hooks/` | git hooks that keep private details out of commits, a `privacy-scan.sh history` pre-publish scan, plus an installer |

---

## Guide Index

| File | Tier | Contents |
|------|------|----------|
| [01 - The CLAUDE.md Layer](docs/01-claude-md.md) | Core | Workspace and project CLAUDE.md - what goes where and why |
| [02 - The Improvement Loop](docs/02-improvement-loop.md) | Core | Enforced rules, feedback files, the rule promotion hierarchy |
| [03 - IDEAS.md and Roadmap](docs/03-ideas-and-roadmap.md) | Core | Priority queue, HISTORY.md archive, the roadmap layer |
| [04 - Budget Awareness](docs/04-budget-awareness.md) | Core | The three budget axes, what session-status.sh does, how to build it |
| [05 - Sessions and Memory](docs/05-sessions-and-memory.md) | Field note | /end-session, session fragments, the file-based memory system |
| [06 - The Overnight Loop](docs/06-overnight-loop.md) | Field note | /loop over IDEAS.md, restore points |
| [07 - Skills Reference](docs/07-skills.md) | Field note | Every shipped skill, ordered by impact |
| [08 - Hooks](docs/08-hooks.md) | Field note | Events, exit codes, blast radius triage, the fail-open trap, the `if:` field |
| [09 - Hook Recipes](docs/09-hooks-recipes.md) | Field note | Write guard, budget monitor, session logger, and the rest of the ready-to-use hooks |
| [10 - The Shorthand System](docs/10-shorthand-system.md) | Field note | A typed short term that triggers a defined behaviour: the glossary file, the prompt hook, the rules for what earns a row, and QUAD as the worked example |
| [11 - Privacy Hooks for a Public Repo](docs/11-privacy-hooks-public-repo.md) | Field note | Commit-time guards that keep private names and paths out, report where never what, and secrets that reach git anyway |
| [12 - The Workspace Repo](docs/12-workspace-repo.md) | Core | Why one dedicated git repo for all Claude config - the organizing principle behind the whole system |
| [13 - Audit Lenses](docs/13-audit-lenses.md) | Field note | How to scope an audit so it finds what the last one missed - the lens generator, coverage as cells, the re-ranking lenses, and how to run a pass |
| [14 - Reading a Measurement](docs/14-reading-a-measurement.md) | Field note | Deciding whether a number or green result can be believed: operate the tool, validate the probe, input states that fake a result, success signals, exit states |
| [15 - Auditing Your Own Changes](docs/15-auditing-your-own-changes.md) | Field note | Recent changes as an audit scope, consequence over file, composition defects, correlated readers |
| [16 - Multi-Agent Orchestration](docs/16-multi-agent-orchestration.md) | Field note | Model choice, delegation, budget before fan-out, briefs, accepting work back, external content as data |
| [17 - Concurrent Sessions](docs/17-concurrent-sessions.md) | Field note | Several sessions on one working tree: commits, shared logs, locks, git rules |
| [18 - Verification Habits](docs/18-verification-habits.md) | Field note | Re-test inherited limits, bounded-search absences, observation harness, test quality, live-process checks |
| [19 - Commit-Anchored Delta](docs/19-commit-anchored-delta.md) | Field note | Re-audit only what changed since the last anchor |
| [20 - Freeze the Consumer](docs/20-freeze-the-consumer.md) | Field note | Pause pending work before repairing the dependency it was waiting on |
| [21 - CLAUDE.md Worked Examples](docs/21-claude-md-examples.md) | Field note | What a project note changes in practice |
| [22 - Reframing Blocked Problems](docs/22-reframing-blocked-problems.md) | Field note | Restating a problem instead of pushing harder |
| [23 - When To Stop Refining](docs/23-when-to-stop-refining.md) | Field note | Stopping rules for any task: define done first, then core and optional stop tests |
| [24 - Config-Driven Doc Linting](docs/24-config-driven-doc-linting.md) | Core | Turning prose rules about docs into JSON-configured checks: dashes, wrapping, indexes, links, numbering, private terms |
| [25 - Bug Reports and PR Descriptions](docs/25-bug-reports-and-pr-descriptions.md) | Field note | Writing an upstream ticket and a pull request description a stranger can act on: evidence, minimal repro, expected and actual, what you tried |
| [Checklist](docs/checklist.md) | Core | Building the full system - what to build in what order |

Core files' referenced tools and snippets are asserted by `tools/selftest.sh` on every push; Field note files are dated patterns from practice that the harness does not check - see "What's Guaranteed vs What's Field Notes" above for the full distinction.

---

## The Honest Caveat

This took months to build incrementally. The templates and tools shortcut that time considerably - you get a working budget-aware statusline on day one instead of month three. But the real return comes from the discipline: running /end-session every session, writing a feedback file every time you correct Claude, keeping IDEAS.md ordered.

The templates don't compound. The habit does.

---

## Status and Licence

Maintained and updated from daily use; the self-test runs on every push and weekly. Released under the [MIT License](LICENSE).

## Skill Files

The `skills/` folder contains skills covering first-principles thinking (`/aristotle`, `/think`), git workflow (`/commit-chunks`, `/step-commits`, `/undo-commits`), code review (`/deep-dive`, `/cross-synth`), writing (`/human-voice`), and more.

To install: copy a skill folder to `.claude/skills/<name>/` in your workspace. Claude Code makes it available as `/<name>`.

See `skills/README.md` for the full list and descriptions.

---
