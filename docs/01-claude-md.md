# Part 1: The CLAUDE.md Configuration Layer

Claude Code reads `CLAUDE.md` from your repo root at the start of every session. This is your persistent instruction layer - things you never want to re-explain.

There are two kinds:

---

## Which Files Are "Claude Files" vs Your Own Files

New users often get confused about which files are special Claude configuration and which are just personal files that happen to be in the same repo. Here's the map:

### Claude's Configuration Files (auto-loaded, special behavior)

| File | What it is | Loaded when |
|------|-----------|-------------|
| `CLAUDE.md` (workspace root) | Your global working style, rules, preferences | Every session, automatically |
| `CLAUDE.md` (inside a repo) | Project-specific context and constraints | When Claude's CWD is that repo |
| `.claude/settings.json` | Hooks (shell scripts triggered by events) | Always active |
| `.claude/settings.local.json` | Permissions and MCP server config | Always active |
| `.claude/rules/enforced-rules.md` | Hard rules that override casual defaults | Read at session start (add to CLAUDE.md's session checklist) |

### Your Personal Files (not auto-loaded, just tracked data)

| File | What it is | Notes |
|------|-----------|-------|
| `memory/MEMORY.md` | Navigation index to all your memory files | Read it manually or add to session start checklist |
| `memory/pending-actions.md` | Your task list | Not special - just a markdown file you and Claude use |
| `memory/session-history.md` | Log of past sessions | Not special - written by `/end-session`, read for context |
| `memory/feedback/feedback_*.md` | Your rules library | Demand-loaded when relevant - not auto-loaded |

**The key distinction:** CLAUDE.md files load *automatically* and shape every response. Your memory files are just markdown - Claude reads them when you tell it to, or when skills like `/dev-session` read them as part of their workflow.

MEMORY.md and enforced-rules.md are closer to "extended CLAUDE.md" - they're not technically auto-loaded by Claude Code, but you add them to CLAUDE.md's session start checklist so they effectively are. That lets you offload detailed rules from CLAUDE.md (keeping it under 150 lines) into enforced-rules.md without losing coverage.

---

- **Workspace CLAUDE.md** - loaded globally for all sessions. Covers your working style, universal rules, how you want Claude to behave across everything.
- **Project CLAUDE.md** - inside each individual repo. Covers what that specific project does, its architecture, constraints, and how to build/run it.

One critical point: **do not use `/init` to generate these.** The `/init` command produces a generic starter file that doesn't reflect how you actually work. Build CLAUDE.md yourself by telling Claude what to add to it. Start with three or four rules, then grow it over time. Every time you correct Claude on something, add the correction to CLAUDE.md so it never happens again. That compounding is the entire game.

The `.claude/` folder also contains:
- `settings.json` - hooks (shell scripts that run on events)
- `settings.local.json` - permissions and MCP server config
- `skills/` - custom slash commands you define

Keep hooks in `settings.json` and permissions in `settings.local.json`. Never mix them - splitting hooks across both files causes double-fire.

---

## Size Discipline

CLAUDE.md is loaded on every single session. Every line costs tokens every time. Bloated CLAUDE.md = a constant tax on your budget.

Target:
- Workspace CLAUDE.md (your rules, preferences, workflow): **100-150 lines max**
- Per-repo CLAUDE.md (project-specific notes): **50-80 lines** is plenty

If it's growing past 150 lines, move content out. Detailed explanations go in `feedback_*.md` files that only load on demand, not every session.

**The key discipline:** CLAUDE.md holds principles and rules, not explanations. If you're writing paragraphs explaining WHY a rule exists, that belongs in a feedback file. CLAUDE.md says "do X" - the feedback file says "because Y happened." Keep them split.

The `enforced-rules.md` pattern helps with this. Split the load:
- `CLAUDE.md` - your core working style and principles (loaded every session)
- `.claude/rules/enforced-rules.md` - hard rules distilled from past failures (also loaded every session, but separate file so you can audit each independently)
- `feedback_*.md` - the WHY behind each rule (loaded only when relevant, on demand)

Three files, three jobs. None of them should do another's job.

---

## Workspace CLAUDE.md - Sections Worth Having

### 1. Senior Engineer Mindset

By default Claude is very agreeable - it will execute whatever you ask without questioning it. You want it to act as the senior engineer instead: pushing back on bad plans, spotting bugs unprompted, suggesting better approaches before implementing. Put this explicitly:

```
Act as the senior engineer, not just an executor. Evaluate requests before implementing.
Push back on bad plans, spot bugs unprompted, suggest improvements proactively.
If you see a problem in code you're working near, say so.
If a better approach exists, say so first.
```

This single instruction changes the quality of every response. Without it, Claude rubber-stamps everything.

### 2. Fix AND Prevent

When Claude fixes a bug, the default is to fix it and move on. You want it to also prevent recurrence:

```
When fixing a bug or correcting a mistake, always do BOTH:
(1) fix the immediate issue
(2) add a guard so it can't recur - a test, a CLAUDE.md rule, or a validation check
```

### 3. Research Approach

Tell Claude the order to look for information:

```
- Code first, docs second - read source before docs/websites. Source reveals truth.
- Test files are the best reference - tests show exactly how code is meant to be used.
- Pattern-copy - find the closest existing example and adapt, never build from scratch.
```

This stops Claude from hallucinating API docs or stating things that are only true in old versions.

### 4. Before Acting on Files

Claude will cheerfully overwrite things without asking. Stop that:

```
- Survey first, act second - analyse current state before any file operation.
- Confirm before major operations - moves, deletions, bulk changes require explicit confirmation.
- Data safety above all - when in doubt, read-only. Never overwrite without certainty.
```

### 5. Output and Communication

Define exactly how you want Claude to write:

```
- No em or en dashes - use regular hyphens (-) only.
- Write reports as markdown. No slide-deck formatting.
- Document as you go - write findings immediately, don't accumulate in context.
- No unexplained acronyms - define on first use.
```

The em/en dash rule sounds trivial but matters if you have a write-guard hook - em dashes in files will block edits.

### 6. Autonomous Work Rules

When you want Claude to work through a task without interrupting you:

```
- Keep working on directives - work through goals autonomously. Don't stop unless truly blocked.
- Don't re-ask for things already granted.
- Use subagents for parallel research - launch multiple Explore agents for independent tasks.
- Use TaskCreate for multi-step plans - any task with 3+ distinct steps benefits from task tracking. Create tasks upfront, mark in_progress when starting, completed when done.
```

**On permissions:** Do NOT put tool permissions in CLAUDE.md. They belong in `.claude/settings.local.json`. CLAUDE.md instructions like "always allowed to read files" are hints Claude can choose to follow - they don't grant permissions at the harness level. Use the settings files for real permission grants.

### 7. Development Approach

Your core engineering standards belong here so they apply across all repos:

```
- TDD always - every feature starts with tests. Write tests first, then implement.
- Scripts must be user-friendly - show output in terminal, log to a file, never close on completion.
- Always add timing to scripts - log start/end time and per-step timing.
```

### 8. README-First

```
README is product marketing. Every feature needs README + code + tests in the same commit.
Lead with benefit not mechanism. Highlight engineering.
```

Don't ship a feature without explaining why anyone would want it.

### 9. Session Start Checklist

Tell Claude what to read before doing anything each session:

```
Before starting work, read:
1. roadmap/pending-actions.md - what needs doing
2. memory/session-history.md - recent context
3. memory/MEMORY.md - full memory index
4. .claude/rules/enforced-rules.md - hard rules that override casual defaults
```

This makes a huge difference. Claude starts with context instead of cold-starting every session.

### 10. Your Vocabulary

Define your own terminology. Claude will use it consistently:

```
- Directive - strategic goal (weeks-months), lives in roadmap/directives/
- Task - concrete next action (session-day), lives in roadmap/pending-actions.md
```

---

## Project-Level CLAUDE.md

Each repo gets its own CLAUDE.md. The workspace one covers HOW you work; the project one covers WHAT this repo is. A great project CLAUDE.md answers the key questions before Claude reads a single line of code.

See `templates/CLAUDE_project.md` for a ready-to-fill template.

### Section 1: One-Line Summary

First line. What does this project do, in one sentence?

```
Python CLI daemon that auto-manages OBS streaming when launching a known game.
```

### Section 2: The Problem It Solves (the WHY)

The most underused section. Explain WHY the project exists - the real motivation, not just the mechanism. This shapes every design decision Claude makes.

Example:

> "The time saving (2 min manual setup) is secondary. The real value is psychological reassurance: the user should be able to glance at a second monitor and confirm everything is handled without alt-tabbing. The goal is 'I can see from one place it's all good.' This is the core UX, not just automation."

When Claude knows the real goal, it makes better decisions. It won't clutter the display with verbose debug output if it knows the design goal is at-a-glance confidence.

### Section 3: Repo Structure

A tree of key files with annotations:

```
src/
  main.py          - entry point
  pipeline.py      - orchestrator: sort -> scan -> batch -> encode
  encoder.py       - FFmpeg encode (GPU / CPU fallback)
tests/
config/
  config.example.json  - template (tracked)
  config.json          - your local config (gitignored)
```

### Section 4: How to Run (Two Versions)

One for users, one for Claude. These are different:

```
Users always run via scripts/run.bat - double-click launcher. Never suggest
python src/main.py or any CLI flags to the user.

Claude runs via CLI: python src/main.py from the repo root. Use this during
development to close the loop - don't wait for the user to test.
```

This distinction is critical. Users want the friendly launcher; Claude needs the raw command to iterate quickly. Conflating them means either users get overwhelmed with flags or Claude waits passively for every test.

### Section 5: Config Format

Document the schema, which file is the template, and which is gitignored:

```json
{
  "obs": { "host": "localhost", "port": 4455, "password": "..." },
  "games": {
    "GameProcess.exe": { "name": "Game Name", "id": "12345" }
  }
}
```

### Section 6: Key Business Logic (Non-Obvious Invariants)

The rules that aren't derivable from reading the code. This is where most of the value is.

Example:

> "The 5 most recently created clips in the Highlights/ root match what the game shows as 'SAVED' in its UI. If you process those clips, the game UI loses track of them. Protection applies ONLY to the root folder, NOT to character subfolders - clips there have already been sorted and are safe to process."

Without this, Claude writes reasonable-looking code that silently breaks the game's UI.

### Section 7: Data Safety Rules

For any project touching real files or irreversible operations:

```
Data Safety - HIGHEST PRIORITY

The library is the primary copy and is NOT frequently backed up.
Before ANY file operation: verify it is safe and reversible.
Prefer dry-run mode first. Never delete source files without confirming the
destination write succeeded. When in doubt, do nothing and ask.
```

### Section 8: Explicit Prohibitions

Named constraints are more reliable than implicit ones:

```
Only the user executes integration. Claude implements features and prepares
workflows, but stops before running any integration. No exceptions, even dry-run.
```

```
TagFixer MUST ONLY operate on the NewMusic folder. Never on the library root.
Never refactor this to accept a folderPath parameter.
```

### Section 9: Critical Platform Gotchas

Anything that looks like it should work but doesn't:

```
CRITICAL: Legacy csproj format - manual file registration required.
New .cs files are NOT auto-included in the build.
Every new file must be manually added to the .csproj.
If you forget: Build fails with CS0103.
```

```
.bat files MUST be run with PowerShell, never Bash.
Windows batch scripts don't work in Unix shells.
```

### Section 10: The IDEAS.md Contract

```
See docs/IDEAS.md for all pending work, ordered by priority.
When a feature is implemented: remove from IDEAS.md, add to HISTORY.md.
Never mark done with checkmarks - remove the entry completely.
```
