# Checklist: Building the System

Use this to track which pieces of the system you've set up. Start with the top-level CLAUDE.md and the feedback habit - those two alone will improve every session.

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
