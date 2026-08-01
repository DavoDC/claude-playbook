# Checklist: Building the System

> **Core.** Part of the maintained quick-start path. The tools and settings snippets it references are asserted by `tools/selftest.sh` on every push.

Use this to track which pieces of the system you've set up. Start with the top-level CLAUDE.md and the feedback habit - those two alone will improve every session.

---

## Workspace Repo (foundation - do this first)

- [ ] Create a dedicated workspace repo: `mkdir workspace && cd workspace && git init && git checkout -b main`
- [ ] This is the repo you will ALWAYS run Claude from - not a project repo, a meta-repo
- [ ] Copy `templates/CLAUDE_workspace.md` to the root as `CLAUDE.md`
- [ ] Copy `templates/enforced-rules.md` to `.claude/rules/enforced-rules.md`
- [ ] Create `memory/feedback/` folder for future feedback files
- [ ] Make your first commit - the workspace is live

See `docs/11-workspace-repo.md` for the full explanation of why this matters.

---

## Environment Setup (do once, pays forever)

- [ ] **Use Windows Terminal** (not cmd.exe or the default terminal) - you can paste images directly into the Claude Code chat window. Screenshot something, Ctrl+V, Claude sees it. This alone unlocks visual debugging.
- [ ] **Point Claude at the official docs** - Claude has no awareness of its own features by default. Give it the reference so it can read them and suggest things you didn't know existed:
  ```
  https://code.claude.com/docs/en/
  ```
  Then ask Claude to read the docs and suggest features that match your workflow. Works especially well for initial setup.
- [ ] **Clone the docs repo as a sibling of the workspace repo, not inside it** - if you want an always-current local copy (for offline reading, or so a session-start hook can pull and grep it), clone it next to the workspace repo, not nested underneath it: `workspace/` and `claude-code-docs/` as siblings under the same parent folder. "Clone the docs" alone is ambiguous - inside-or-beside are both reasonable readings of the same instruction, and picking the wrong one silently breaks any path that assumes the other. See `docs/11-workspace-repo.md` for the full convention.
- [ ] **Read the Claude Code docs yourself** - hooks, MCP servers, statusline config, remote control - most users discover these months late.

---

## Top-Level CLAUDE.md

- [ ] Senior engineer mindset instruction
- [ ] Fix AND prevent rule
- [ ] Research order: code first, tests as reference, pattern-copy
- [ ] File operation safety: survey first, confirm before bulk
- [ ] Output style: dash rules, no slide-deck formatting
- [ ] Development standards: TDD, scripts, timing
- [ ] Session start checklist (what files to read first)
- [ ] Your terminology (directives, tasks, or equivalent)
- [ ] README-first rule
- [ ] Autonomous work rules

## Project CLAUDE.md (for each repo)

- [ ] One-line summary of what the project does
- [ ] Why it exists (the real motivation, not just the mechanism)
- [ ] Repo structure tree with file annotations
- [ ] How to run - user entry point AND Claude entry point separately
- [ ] Config format with schema
- [ ] Non-obvious business logic and invariants
- [ ] Data safety rules
- [ ] Explicit list of what Claude is NOT allowed to do
- [ ] Platform gotchas and critical build constraints
- [ ] IDEAS.md contract

## Enforced Rules

- [ ] `enforced-rules.md` in `.claude/rules/`
- [ ] Verify-before-claiming-done
- [ ] Thinking discipline: grep before claiming, never fabricate
- [ ] Git safety: commits only, user pushes
- [ ] Secrets: both .gitignore AND runtime guard
- [ ] Prompt injection resistance
- [ ] Platform-specific constraints

## Budget Awareness

- [ ] `tools/statusline.py` installed and configured in settings.json
- [ ] `tools/check-budget.sh` accessible
- [ ] `tools/session-status.sh` calling check-budget.sh correctly
- [ ] Tested: `bash tools/session-status.sh` outputs 2-line budget status
- [ ] `/dev-session` (or equivalent) calls session-status.sh at start

## IDEAS.md System

- [ ] `docs/IDEAS.md` created in at least one repo
- [ ] Items ordered by priority (TIER 0 first)
- [ ] `docs/HISTORY.md` created for archiving completed items
- [ ] Established habit: remove from IDEAS when done, add to HISTORY

## Skills Worth Building

- [ ] `/end-session` - session drain and memory sync
- [ ] `/dev-session` - structured project work with IDEAS.md
- [ ] `/commit-chunks` - logical commit splitting
- [ ] `/reflection` - periodic meta-improvement
- [ ] `/aristotle` - first principles deconstruction (starter in `skills/`)
- [ ] `/premortem` - risk analysis before big decisions (starter in `skills/`)

## Memory System

- [ ] `memory/` folder in a git-tracked repo
- [ ] `memory/MEMORY.md` index file created
- [ ] First user memory entry written
- [ ] Session history connected to `/end-session`

## Hooks Worth Having

- [ ] Write guard (blocks secrets and private paths)
- [ ] Context budget monitor (warns before compaction)
- [ ] Session logger (tracks skill usage)
- [ ] Settings split: hooks in settings.json, permissions in settings.local.json

## The Feedback Habit

- [ ] `memory/feedback/` folder created
- [ ] First `feedback_<topic>.md` written after a real correction
- [ ] Committed to git
- [ ] Rule promoted to enforced-rules.md if applicable

---

## Recommended Order

1. Top-level CLAUDE.md (immediate value, low effort)
2. Project CLAUDE.md for your most-used repo
3. enforced-rules.md with 3-4 starter rules
4. Budget awareness tools (needed before overnight loops)
5. `/end-session` skill
6. IDEAS.md in your most active project
7. `/dev-session` skill
8. Memory system
9. Hooks
10. `/aristotle` and `/premortem` skills
