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

See `docs/13-workspace-repo.md` for the full explanation of why this matters.

---

## Environment Setup (do once, pays forever)

- [ ] **Use Windows Terminal** (not cmd.exe or the default terminal) - you can paste images directly into the Claude Code chat window. Screenshot something, Ctrl+V, Claude sees it. This alone unlocks visual debugging.
- [ ] **Clone the Claude Code docs locally** - Claude has no awareness of its own features by default, so give it something it can search rather than a link it has to guess its way around:
  ```
  git clone https://github.com/ericbuess/claude-code-docs
  ```
  That is a preference, not the only option: several community mirrors exist, none official, and any maintained one works. This playbook uses it because it refreshes on a schedule measured in hours, keeps one plain markdown file per documentation page so the set is greppable, is scoped to the Claude Code docs rather than blog posts and cookbooks, and ships a manifest recording each file's source URL, content hash and fetch time, which lets you tell a stale copy from a current one. `thevibeworks/claude-code-docs` is the reasonable alternative if you want the wider Anthropic material in the same clone. Check the criteria in `docs/13-workspace-repo.md` before adopting either, and judge whether a mirror is alive by its last commit date, not the displayed update time. Put the clone beside the workspace repo, not nested under it. When writing a pointer for someone else, cite `https://code.claude.com/docs/en/`, not your local path. Then ask Claude to read the docs and suggest features that match your workflow; this works especially well for initial setup.
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
- [ ] Your work loop or session routine calls session-status.sh at start

## IDEAS.md System

- [ ] `docs/IDEAS.md` created in at least one repo
- [ ] Items ordered by priority (TIER 0 first)
- [ ] `docs/HISTORY.md` created for archiving completed items
- [ ] Established habit: remove from IDEAS when done, add to HISTORY

## Skills Worth Building

- [ ] `/end-session` - session drain and memory sync
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
- [ ] **Git hooks** - `sh hooks/install.sh` in this repo points `core.hooksPath` at the tracked `hooks/` folder, so `pre-commit`, `commit-msg` and `pre-push` run from there, and they block staged content or commit messages that reference a private sibling repo (derived at runtime from any `.private-root` marker under the parent folder - see `docs/12-privacy-hooks-public-repo.md`). Git config is never tracked, so this install step is required again after every fresh clone.

## The Feedback Habit

- [ ] `memory/feedback/` folder created
- [ ] First `feedback_<topic>.md` written after a real correction
- [ ] Committed to git
- [ ] Rule promoted to enforced-rules.md if applicable

## Audit Habits

- [ ] **Generate lenses before scanning, and record which ones you did not apply.** A skipped lens with a reason is a decision. An unlisted lens is a blind spot. See `docs/14-audit-lenses.md`.
- [ ] **For every prose rule about your docs, ask whether a check can see a violation; if so, make it a config rule.** See `docs/25-config-driven-doc-linting.md`.
- [ ] **Before filing an upstream bug or opening a pull request, cold-read the text as a stranger and re-run the reproduction from scratch.** See `docs/26-bug-reports-and-pr-descriptions.md`.

## Small Habits Worth Having

- [ ] **A process under `--watch` or auto-reload has no "don't reload yet" channel.** It fires on its own timer whatever you tell it, so flag that the moment someone asks you to hold off, not after the instruction has been silently ignored.
- [ ] **Verify a backup target is a different physical disk, not just a different drive letter.** Two letters can be partitions of one disk; walk the disk, partition, volume chain before trusting it as redundancy.
- [ ] **When a live user's description of their screen conflicts with your reading of a screenshot, defer to the user.** A screenshot is one static frame without hover or focus state; the human has the running system.
- [ ] **Before hardcoding a host address, port or handle, check the property its stability depends on** (for example a lease about to expire), not just the value you observed.
- [ ] **Never ask a human to type a visually ambiguous character** (O vs 0, l vs 1 vs I) in a keybind, filename or code. The misread costs a round trip.
- [ ] **When a "keep or revert external changes" dialog appears, name the specific deliberate change it describes before answering.** Never answer from the dialog's wording alone.
- [ ] **Before calling a missing list or menu item broken, check whether inclusion in that list is opt-in.**

---

## Recommended Order

1. Top-level CLAUDE.md (immediate value, low effort)
2. Project CLAUDE.md for your most-used repo
3. enforced-rules.md with 3-4 starter rules
4. Budget awareness tools (needed before overnight loops)
5. `/end-session` skill
6. IDEAS.md in your most active project
7. Memory system
8. Hooks
9. `/aristotle` and `/premortem` skills
