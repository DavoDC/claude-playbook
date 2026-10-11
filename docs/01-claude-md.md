# Part 1: The CLAUDE.md Configuration Layer

> **Core.** Part of the maintained quick-start path. The tools and settings snippets it references are asserted by `tools/selftest.sh` on every push.

Claude Code reads `CLAUDE.md` from your repo root at the start of every session. This is your persistent instruction layer - things you never want to re-explain.

There are two kinds:

---

## Which Files Are "Claude Files" vs Your Own Files

Which files are special Claude configuration and which are just personal files in the same repo:

### Claude's Configuration Files (auto-loaded, special behavior)

| File | What it is | Loaded when |
|------|-----------|-------------|
| `CLAUDE.md` (workspace root) | Your global working style, rules, preferences | Every session, automatically |
| `CLAUDE.md` (inside a repo) | Project-specific context and constraints | When Claude's CWD is that repo |
| `.claude/settings.json` | Hooks (shell scripts triggered by events) | Always active |
| `.claude/settings.local.json` | Permissions and MCP server config | Always active |
| `.claude/rules/enforced-rules.md` | Hard rules that override casual defaults | Every session, automatically (rules files without `paths` frontmatter load like CLAUDE.md) |

### Your Personal Files (not auto-loaded, just tracked data)

| File | What it is | Notes |
|------|-----------|-------|
| `memory/MEMORY.md` | Navigation index to all your memory files | Read it manually or add to session start checklist |
| `memory/pending-actions.md` | Your task list | Not special - just a markdown file you and Claude use |
| `memory/session-history.md` | Log of past sessions | Not special - written by `/end-session`, read for context |
| `memory/feedback/feedback_*.md` | Your rules library | Demand-loaded when relevant - not auto-loaded |

**The key distinction:** CLAUDE.md files load *automatically* and shape every response. Your memory files are just markdown - Claude reads them when you tell it to, or when a skill reads them as part of its workflow.

`.claude/rules/enforced-rules.md` is "extended CLAUDE.md": Claude Code loads every file in `.claude/rules/` that has no `paths` frontmatter at launch, with the same priority as CLAUDE.md. That lets you offload detailed rules (keeping CLAUDE.md under 150 lines) without losing coverage. `MEMORY.md` is not loaded this way, so list it in CLAUDE.md's session start checklist.

The workspace CLAUDE.md covers how you work across everything; each project CLAUDE.md covers what that project is and how to build and run it. `.claude/skills/` holds your custom slash commands.

**Do not use `/init` to generate these.** It produces a generic starter that does not reflect how you work. Start with three or four rules and grow it; every time you correct Claude, add the correction so it never recurs. That compounding is the entire game.

Keep hooks in `settings.json` and permissions in `settings.local.json`. Never mix them: splitting hooks across both files causes double-fire.

---

## Size Discipline

CLAUDE.md loads every session, so every line costs tokens every time; a bloated one is a constant tax.

Target:
- Workspace CLAUDE.md (your rules, preferences, workflow): **100-150 lines max**
- Per-repo CLAUDE.md (project-specific notes): **50-80 lines** is plenty

The line target is a proxy for a byte ceiling, which is what actually costs tokens: set a hard byte limit for each always-loaded file, with a down-only ratchet (each cleanup that brings the file under its ceiling lowers the ceiling to match, never raises it). `tools/check-capacity.py` holds those ceilings in a config file and reports the room left before you edit (see [Part 4](04-budget-awareness.md), "Size ceilings, and a budget for the group"). If it grows past the ceiling, move content out; detailed explanations go in on-demand `feedback_*.md` files.

**The key discipline:** CLAUDE.md holds principles and rules, not explanations. CLAUDE.md says "do X"; the feedback file says "because Y happened."

Split the load across three files, three jobs, none doing another's:
- `CLAUDE.md`: core working style and principles (loaded every session)
- `.claude/rules/enforced-rules.md`: hard rules distilled from past failures (also loaded every session, but separate so each can be audited independently)
- `feedback_*.md`: the WHY behind each rule (loaded on demand)

When any of these points to "where to find an example of X," prefer a grep search term over a hardcoded path. A path like "look in project/data/logs/" goes wrong once the repo is renamed or restructured; a term like `TimedRotating|getLogger` finds the current best example and comes up empty rather than stale. A template file you maintain on purpose is the exception.

---

## Workspace CLAUDE.md - Sections Worth Having

### 1. Senior Engineer Mindset

By default Claude is very agreeable and executes whatever you ask. You want the senior engineer instead: pushing back on bad plans, spotting bugs unprompted, suggesting better approaches before implementing. Say so explicitly:

```
Act as the senior engineer, not just an executor. Evaluate requests before implementing.
Push back on bad plans, spot bugs unprompted, suggest improvements proactively.
If you see a problem in code you're working near, say so.
If a better approach exists, say so first.
```

This single instruction changes the quality of every response; without it Claude rubber-stamps everything.

One way pushing back goes wrong: when a user names a specific mechanism ("plugin", "macro", "extension"), that name is a constraint on the solution space, not a gesture at a category of fix. Proposing a cleaner architecture overrides information the user already gave you. Investigate the named mechanism on the real system first. One project spent months on a cloud-API integration route while the user kept saying "plugin"; the answer was an already-installed native plugin dialog needing zero registration, findable in minutes. If you substitute a different approach after investigating, say so explicitly.

### 2. Fix AND Prevent

By default Claude fixes a bug and moves on. You want it to also prevent recurrence:

```
When fixing a bug or correcting a mistake, always do BOTH:
(1) fix the immediate issue
(2) add a guard so it can't recur - a test, a CLAUDE.md rule, or a validation check
```

A guard fails quietly when its selection criterion and pass criterion are the same property: a checker that only examines inputs which already look valid never finds the ones that don't. Decide what to check from something independent of correctness (file path, a marker, surrounding structure). Treat an empty result as a failure to investigate; a check that found nothing and one that never ran look identical.

Fix and guard closes a single door. The third rung is where the compounding happens: name the structural reason the setup allowed the bug, ask what else shares that gap, and ask which existing review should have caught it, then fix that review too. Otherwise the next bug with the same root cause gets fixed and guarded individually, forever.

It runs the other way too: when something you tried is genuinely good (a prompt phrasing, a workflow shortcut), decide immediately whether it should recur. A high-value one-off left as a one-off wastes most of its value.

### 3. Research Approach

Tell Claude the order to look for information:

```
- Code first, docs second - read source before docs/websites. Source reveals truth.
- Test files are the best reference - tests show exactly how code is meant to be used.
- Pattern-copy - find the closest existing example and adapt, never build from scratch.
```

This stops Claude from hallucinating API docs or stating things that are only true in old versions.

A worse failure than being wrong: reporting that something doesn't exist when the search didn't look hard enough. A grep for one spelling, case or extension that finds nothing proves the search was bounded, not that the thing is absent. Before closing on a negative, vary case, separators, singular and plural, and check the file types and directories searched. Then widen the search, or say exactly what you searched: "No hits under this path in markdown files" is honest; "There is no such thing" is usually untested (the full rule is in [Part 19](19-verification-habits.md)).

Before building any diff, match or reconciliation, say what the unit of comparison is. A file-level diff can report most files unchanged while the record inside them moved, split or merged across files: accurate and useless. If every container changed shape but the real unit was preserved, would the comparison still say so? If not, restate the unit first.

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
- Write markdown at full width, one paragraph per line - don't hard-wrap prose at 70-80 characters. Renderers reflow anyway, so a hard wrap is invisible to a reader and only adds noisy diffs. Lists, tables and code keep their natural shape.
- Never write exact counts in any doc (tests, skills, config entries, anything that changes as work continues). They go stale silently and the reader assumes the number is current. Use a qualifier ("several", "comprehensive as of DATE") or drop the number. This applies to your own CLAUDE.md and feedback files as much as a public README.
```

The em/en dash rule sounds trivial but matters if you have a write-guard hook - em dashes in files will block edits.

### 6. Autonomous Work Rules

When you want Claude to work through a task without interrupting you:

```
- Keep working on directives - work through goals autonomously. Don't stop unless truly blocked.
- Don't re-ask for things already granted.
- Ration subagents - measure remaining budget first, dispatch one at a time with related work bundled into each brief, and fan out in parallel only for small, genuinely independent tasks.
- Use TaskCreate for multi-step plans - any task with 3+ distinct steps benefits from task tracking. Create tasks upfront, mark in_progress when starting, completed when done.
```

**On permissions:** Do NOT put tool permissions in CLAUDE.md. They belong in `.claude/settings.local.json`. CLAUDE.md instructions like "always allowed to read files" are hints Claude can choose to follow - they don't grant permissions at the harness level. Use the settings files for real permission grants.

### 7. Development Approach

Your core engineering standards belong here so they apply across all repos:

```
- TDD always - every feature starts with tests. Write tests first, then implement.
- Test strength over test count - a test that cannot fail still passes.
- Scripts must be user-friendly - show output in terminal, log to a file, never close on completion.
- Always add timing to scripts - log start/end time and per-step timing.
```

**On that second line.** A test that cannot fail still passes, and coverage and test counts both rise when weak tests are added.

The test smells to avoid, the strong form of a test, and how a runner should report are in [Part 19](19-verification-habits.md#test-quality-a-green-run-is-not-evidence).

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

### 11. Avoid Special-Case Exceptions

Tell Claude to resist the urge to hardcode "if this repo / if this context" branches into shared rules and skills:

```
Before adding an if-repo or if-context exception to a shared rule or skill, stop and question
the design. Exceptions signal the general structure doesn't fit the problem - they add cognitive
load and drift out of sync with everything else. Ask what general mechanism (a pointer file, a
consistent folder structure, a line of config) would make the exception unnecessary. Only hardcode
the exception if no general solution exists and the cost of the exception is clearly lower than
restructuring.
```

Example: a session-composition skill grew a special case for one project whose idea backlog lived elsewhere. The fix was a one-line pointer file in that project pointing at the real location, so the skill read normally with no branch. Put the special knowledge in the data a skill reads, not in its logic.

---

## Project-Level CLAUDE.md

Each repo gets its own CLAUDE.md. The workspace one covers HOW you work; the project one covers WHAT this repo is. A great project CLAUDE.md answers the key questions before Claude reads a single line of code.

See `templates/CLAUDE_project.md` for a ready-to-fill template.

### When It Grows Too Big: Split Off a DevContext.md

A project CLAUDE.md's scope is orientation and harm prevention only: what the repo does, build/test/run commands, key paths, and safety rules preventing data loss or broken invariants. Internals, code patterns and architecture notes are not worth paying for on sessions that never touch the code. Split them into a demand-loaded file, for example `docs/References/DevContext.md`, when CLAUDE.md exceeds roughly 150 lines or more than half is implementation notes. One project's CLAUDE.md grew past 300 lines because every dev session appended learnings to it; the fix was two files with different load times, not one file hand-trimmed every few weeks.

### Section 1: One-Line Summary

First line. What does this project do, in one sentence?

```
Python CLI that renames and sorts photos on import.
```

### Section 2: The Problem It Solves (the WHY)

The most underused section. Explain WHY the project exists - the real motivation, not just the mechanism. It shapes every design decision.

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

The distinction is critical: users want the friendly launcher, Claude needs the raw command to iterate. Conflating them overwhelms users with flags or leaves Claude waiting passively for every test.

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

### Section 8: Explicit Prohibitions and the Division of Labour

Named constraints are more reliable than implicit ones:

```
Only the user executes integration. Claude implements features and prepares
workflows, but stops before running any integration. No exceptions, even dry-run.
```

```
The importer MUST ONLY operate on the staging folder. Never on the library root.
Never refactor this to accept a folderPath parameter.
```

Name two lists explicitly: what the agent may do without asking, and what it must always hand back to you. An unstated boundary gets rediscovered by crossing it, and the correction covers only that case; naming both lists closes the whole class.

When a task hits a step the agent cannot run (a production deploy, an account credential, a physical action), deliver the complete solution with that one step clearly handed over, never quietly shrink the deliverable to what could be executed. A narrowed deliverable reads as finished until the un-run step matters.

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
See <backlog path> for all pending work, ordered by priority.
When a feature is implemented: remove from IDEAS.md, add to HISTORY.md.
Never mark done with checkmarks - remove the entry completely.
```

The backlog need not live in the project repo. Keeping it in your workspace repo keeps unshipped plans out of a public repo and holds every queue in one place; put the path in this line. `docs/IDEAS.md` inside the repo is fine for a private project.

A habit to codify alongside it: when you dump a burst of raw, half-formed ideas, tell Claude to save the raw text verbatim first, in its own "Raw (verbatim)" section (obvious typos fixed, substance untouched), followed by a "Processed" section with the expanded, prioritised version. A refined-only summary bakes Claude's interpretation in as the record; if it missed the point, the original is gone. Only for genuine idea dumps.

Verbatim capture is safe going in, not coming back out. The fact inside a raw sentence can be fine to publish while the sentence is not, because the phrasing carries identifying context (who said it, what system they worked in). It is a one-way valve: write down exactly as heard, never forward or publish exactly as heard. The generalising step, from the raw sentence to the reusable fact stripped of who and where, must happen at the boundary where content leaves private capture for anything shareable.
