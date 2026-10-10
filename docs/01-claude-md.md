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
| `.claude/rules/enforced-rules.md` | Hard rules that override casual defaults | Read at session start (add to CLAUDE.md's session checklist) |

### Your Personal Files (not auto-loaded, just tracked data)

| File | What it is | Notes |
|------|-----------|-------|
| `memory/MEMORY.md` | Navigation index to all your memory files | Read it manually or add to session start checklist |
| `memory/pending-actions.md` | Your task list | Not special - just a markdown file you and Claude use |
| `memory/session-history.md` | Log of past sessions | Not special - written by `/end-session`, read for context |
| `memory/feedback/feedback_*.md` | Your rules library | Demand-loaded when relevant - not auto-loaded |

**The key distinction:** CLAUDE.md files load *automatically* and shape every response. Your memory files are just markdown - Claude reads them when you tell it to, or when a skill reads them as part of its workflow.

MEMORY.md and enforced-rules.md are "extended CLAUDE.md": not auto-loaded by Claude Code, but listed in CLAUDE.md's session start checklist so they effectively are. That lets you offload detailed rules (keeping CLAUDE.md under 150 lines) without losing coverage.

---

- **Workspace CLAUDE.md** - loaded globally for all sessions. Covers your working style, universal rules, how you want Claude to behave across everything.
- **Project CLAUDE.md** - inside each individual repo. Covers what that specific project does, its architecture, constraints, and how to build/run it.

**Do not use `/init` to generate these.** It produces a generic starter file that doesn't reflect how you work. Build CLAUDE.md by telling Claude what to add. Start with three or four rules and grow it; every time you correct Claude, add the correction so it never recurs. That compounding is the entire game.

The `.claude/` folder also contains:
- `settings.json` - hooks (shell scripts that run on events)
- `settings.local.json` - permissions and MCP server config
- `skills/` - custom slash commands you define

Keep hooks in `settings.json` and permissions in `settings.local.json`. Never mix them - splitting hooks across both files causes double-fire.

---

## Size Discipline

CLAUDE.md loads every session, so every line costs tokens every time; a bloated one is a constant tax.

Target:
- Workspace CLAUDE.md (your rules, preferences, workflow): **100-150 lines max**
- Per-repo CLAUDE.md (project-specific notes): **50-80 lines** is plenty

The line target is a proxy for a byte ceiling, which is what actually costs tokens: set a hard byte limit for each always-loaded file, with a down-only ratchet (each cleanup that brings the file under its ceiling lowers the ceiling to match, never raises it). If it grows past the ceiling, move content out; detailed explanations go in on-demand `feedback_*.md` files.

**The key discipline:** CLAUDE.md holds principles and rules, not explanations. CLAUDE.md says "do X"; the feedback file says "because Y happened."

The `enforced-rules.md` pattern helps. Split the load:
- `CLAUDE.md` - your core working style and principles (loaded every session)
- `.claude/rules/enforced-rules.md` - hard rules distilled from past failures (also loaded every session, but separate file so you can audit each independently)
- `feedback_*.md` - the WHY behind each rule (loaded only when relevant, on demand)

Three files, three jobs. None of them should do another's job.

When any of these files points to "where to find an example of X," prefer a grep search term over a hardcoded path. A path like "look in project/data/logs/" goes wrong once the repo is renamed, restructured or archived; a term like `TimedRotating|getLogger` finds the current best example, including files that didn't exist when you wrote the doc, and comes up empty rather than stale. The exception is a template file you maintain on purpose; a path is fine there. Before adding a "look here" table to a process doc, ask whether the path will still exist in a year; if unsure, use a grep term.

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

One way pushing back goes wrong: when a user names a specific mechanism - "plugin", "macro", "extension", the literal name of a feature they know exists - that name is a constraint on the solution space, not a gesture at a category of fix. Proposing a cleaner, more general architecture overrides information the user already gave you. Investigate the named mechanism on the real system first. One project spent months on a cloud-API integration route while the user kept saying "plugin"; the answer was an already-installed native plugin dialog needing zero registration, findable in minutes had the word been read literally. If you substitute a different approach after investigating, say so explicitly.

### 2. Fix AND Prevent

By default Claude fixes a bug and moves on. You want it to also prevent recurrence:

```
When fixing a bug or correcting a mistake, always do BOTH:
(1) fix the immediate issue
(2) add a guard so it can't recur - a test, a CLAUDE.md rule, or a validation check
```

A guard fails quietly when its selection criterion and pass criterion are the same property. A checker that only examines inputs which already look valid never finds the ones that don't: the worst violations are skipped before being checked, and the guard reports success while doing nothing. Decide what to check from something independent of correctness (file path, a marker, surrounding structure), never the property being validated. Treat an empty result as a failure to investigate, not a clean pass; a check that found nothing and one that never ran look identical.

Fix and guard closes a single door. The third rung is where the compounding happens: name the structural reason the setup allowed the bug, ask what else shares that gap, and ask which existing review should have caught it - then fix that review too. Otherwise the next bug with the same root cause gets fixed and guarded individually, forever.

The discipline also runs the other way. When something you tried is genuinely good - a prompt phrasing, a workflow shortcut, a way of splitting a task - decide immediately whether it should recur. A high-value one-off left as a one-off wastes most of its value, and the details of what made it work fade.

### 3. Research Approach

Tell Claude the order to look for information:

```
- Code first, docs second - read source before docs/websites. Source reveals truth.
- Test files are the best reference - tests show exactly how code is meant to be used.
- Pattern-copy - find the closest existing example and adapt, never build from scratch.
```

This stops Claude from hallucinating API docs or stating things that are only true in old versions.

A worse failure than being wrong: reporting that something doesn't exist when the search didn't look hard enough. A grep for one spelling, case or file extension that finds nothing proves the search was bounded, not that the thing is absent. Before closing on a negative, vary case, separators (hyphen, underscore, space, none), singular and plural, and check the file types and directories searched were the right ones. Then either widen the search and report a true negative, or say exactly what you searched. "No hits under this path in markdown files" is honest; "There is no such thing" is usually untested.

Before building any diff, match or reconciliation, say what the unit of comparison is and check it is what the question is about. A file-level diff can report most files unchanged while the record inside them moved, split or merged across files: accurate and useless. Ask: if every container changed shape but the real unit was preserved, would this comparison still say so? If that is possible you're comparing the wrong thing; restate the unit before writing the comparison.

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
- Write markdown at full width, one paragraph per line - don't hard-wrap prose at 70-80 characters. Renderers reflow paragraphs anyway, so a hard wrap is invisible to a reader and just adds noisy diffs where one edit touches several wrap-points instead of one line. Lists, tables, code blocks, and ASCII diagrams keep their natural shape - this is about prose only.
- Never write exact counts in any doc - test counts, skill counts, config entry counts, anything that changes as work continues. They go stale silently: the doc doesn't know a test got added, the reader assumes the number shown is current, and it's already wrong. Use a qualifier instead ("several", "over a dozen", "comprehensive as of DATE") or drop the number entirely. This applies to your own CLAUDE.md and feedback files just as much as a public README - see Part 7 for what happens when a skills list hardcodes usage counts.
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

**On that second line.** "TDD always" is the most common workspace rule and the least self-enforcing, because coverage and test counts both rise when weak tests are added. A suite can grow while its ability to detect a defect stays flat. The question is whether each test would fail if the feature were broken.

Five smells, all passing a green run: a **structural string-scan** asserting the source text contains a function name or config key (renaming a variable breaks it, shipping a bug does not); an **assertion-free** test that calls the code and asserts nothing; a **dodger** that tests a helper, wrapper or re-implementation rather than the real entry point, so the tested and shipped paths differ; an **over-mocked** test that exercises its own mocks, worst when a mock's signature has drifted from the real object so every real call would raise unnoticed; and **assertion roulette**, many unlabelled assertions in one test, so a failure doesn't say which behaviour regressed.

A sixth smell lives in production code: an **error handler with scope wider than the risk it guards**. Wrapping a whole loop or function body in try/except, rather than the one call that can fail, makes any unrelated exception trigger the same fallback as the real failure, and a suite built around the intended failure stays green. A console encoding error inside an unrelated `print()`, caught by the broad try/except around a classification routine, caused unambiguous input to be misclassified as "needs review". Scope every handler to the smallest block that can raise the error you handle.

A seventh survives even a well-structured test: **a field that passes its schema and is still meaningless**. A raw heap address rendered as a string, a `tostring()` dump standing in for a real value, or an integer enum shown as a bare number all satisfy "exists and has the right type" while conveying nothing. The same raw-address-as-string bug shipped across three rounds of one project because each check confirmed only that the field existed and parsed. Read the actual value in the assertion, not its shape.

An eighth, in the code under test like the sixth: a resolve-with-default helper that cannot tell an absent value from a malformed one. Avoid `value if isinstance(value, T) else DEFAULT` inside any safety or privacy check where DEFAULT is the safe outcome; it maps two situations to one result. Test membership first (`if key not in settings: return DEFAULT`); when the key IS present, coerce explicitly (`bool(value)`, `str(value).strip()`) or route to an explicit violation sentinel, never the safe default a missing key gets. The danger is invisible when the code looks most defensive: a boolean privacy flag legitimately absent passes every test, while one PRESENT but set to a truthy non-bool (`1`, `"1"`) fails the same isinstance check and lands on the same safe default - a real violation reported as SAFE. Once one resolver in a module has this shape, grep the module for the pattern; it repeats across sibling fields written in one sitting.

One level above the over-mocked smell, a property of the suite: **a suite built only against invented fixtures proves nothing about the real corpus, disk or store it protects**, however well-scoped each test. A history rewrite was silently reversed by a background sync tool while every test stayed green, because none had read the actual object store. Every project needs at least one check, however coarse, that reads the real thing.

The strong version, in order: drive the **real entry point** production uses; mock **only true boundaries** (network, database, clock, auth, filesystem) and run everything inside for real; assert **observable outcomes** (returned value, written file, emitted record, resulting state) rather than call sequences, since asserting a call tests the implementation you wrote while asserting the outcome tests the behaviour you wanted; and **mutation-verify anything that matters** by reintroducing the bug, watching the test fail, then restoring the source. A test you have never seen fail is unverified, and checking takes seconds.

Watch for a suspiciously perfect result. A 100% match, zero-diff or "everything accounted for" on real data is what a self-comparison bug, a loose match key or a filter dropping the hard cases would also produce. Before reporting a clean result as good news, rule out the boring explanation. And when verification turns up a real defect, don't fix it in the same pass; hand the fix to a fresh check, since a fix validated by the reasoning that missed the bug is re-asserted, not verified.

Also watch for a high test count concentrated on easy pure functions while the main orchestration path and primary output writer sit at zero behavioural coverage. Look at what the suite covers, not how much.

**A test runner's own output needs the same design discipline as the code it tests.** Most frameworks print every test's chatter pass or fail, so the log a human or agent must read is mostly noise from tests needing no attention. Use a runner that captures each test's console output, discards it on a pass, and surfaces it with the failure message only on failure. One custom runner printed a multi-line trace for every passing check, the overwhelming majority of the log. Capturing output per test, emitting only `[PASS] name` on success and the captured trace plus `[FAIL] name: reason` on failure, cut the log to a fraction while giving failures more context, since the trace up to the failure is no longer interleaved with passing traces. Put the pass/fail counts and overall result on the LAST lines, never the first, so a human or script can `tail` the file for the answer.

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

CLAUDE.md is auto-loaded every session whether or not the work needs it. A project CLAUDE.md's scope is orientation and harm prevention only: what the repo does, build/test/run commands, key paths, and safety rules preventing data loss or broken invariants. Internals, code patterns and architecture notes are implementation detail, not worth paying for on sessions that never touch the code. Split them into a demand-loaded file, for example `docs/References/DevContext.md`, read only when working on implementation. Split when CLAUDE.md exceeds roughly 150 lines, or more than half is implementation notes. One project's CLAUDE.md grew past 300 lines because every dev session appended learnings to it; the fix was two files with different load times, not one file hand-trimmed every few weeks.

### Section 1: One-Line Summary

First line. What does this project do, in one sentence?

```
Python CLI daemon that auto-manages OBS streaming when launching a known game.
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

Prohibitions are half of it. Name two lists explicitly: what the agent may do without asking, and what it must always hand back to you. An unstated boundary gets rediscovered by crossing it, and the correction covers only that case. Naming both lists closes the whole class at once.

The harder half: when a task hits a step the agent cannot run - a push, a production deploy, an account credential, a physical action - deliver the complete solution with that one step clearly handed over, never quietly shrink the deliverable to what could be executed. A narrowed deliverable reads as finished until the un-run step matters. State the handoff in the output every time.

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

The backlog need not live in the project repo. Keeping it outside (for example in your workspace repo, a folder per project) keeps unshipped plans out of a public repo and holds every project's queue in one place; put the path in this line so Claude finds it. Inside the repo (`docs/IDEAS.md`) is fine for a private project.

A habit to codify alongside it: when you dump a burst of raw, half-formed ideas on Claude, tell it to save the raw text verbatim first, in its own section, before any refined version. A refined-only summary bakes Claude's interpretation in as the record; if it missed the point, the original is gone. Use a "Raw (verbatim)" section with the exact text - obvious typos fixed, substance untouched - followed by a "Processed" section with the expanded, connected, prioritised version. Only for genuine idea dumps, not routine back-and-forth.

That habit does not protect the way out: verbatim capture is safe going in, not automatically safe coming back out. The fact inside a raw sentence can be fine to publish while the sentence is not, because the phrasing carries identifying context the fact alone does not - who said it, what system they worked in, what workaround they described. Verbatim capture is a one-way valve: write down exactly as heard, never forward or publish exactly as heard. The generalising step - from "here is the raw sentence" to "here is the reusable fact, stripped of who and where" - must happen at the boundary where content leaves private capture for anything shareable, not whenever someone revisits the note. The two get confused because the fidelity that makes verbatim capture valuable also makes moving it verbatim risky.
