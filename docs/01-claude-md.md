# Part 1: The CLAUDE.md Configuration Layer

> **Core.** Part of the maintained quick-start path. The tools and settings snippets it references are asserted by `tools/selftest.sh` on every push.

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

One more thing worth building in from the start: when any of these files points to "where to find an example of X," prefer a grep search term over a hardcoded file path. A path like "look in project/data/logs/" is correct today and wrong once that repo gets renamed, restructured, or archived; a search term like `TimedRotating|getLogger` finds whatever the current best example is - including files that didn't exist when you wrote the doc - and just comes up empty if nothing matches yet, rather than pointing somewhere stale or wrong. The exception is a template file you maintain on purpose - those are stable by design and a path is fine there. Before adding a "look here" table to any process doc, ask: will this path still exist in a year? If you're not sure, use a grep term instead.

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

One way a guard fails quietly: when its selection criterion and its pass criterion are the same property. A checker that only examines inputs which already look valid can never find the ones that don't - the worst violations get skipped as "not my business" before they're ever checked, and the guard reports success while doing nothing. Keep the two separate: decide what to check based on something independent of correctness (file path, a marker, surrounding structure), never based on the property being validated. And treat an empty result as a failure to investigate, not a clean pass - a check that found nothing and a check that never ran look identical from the outside.

Fix and guard closes a single door. There's a third rung beyond it, and it's where the actual compounding happens: name the structural reason the setup allowed the bug in the first place, ask what else shares that same gap, and ask which existing review should have caught it and didn't - then fix that review too. Skipping this rung means the next bug with the same root cause gets fixed and guarded individually, again, forever.

The same discipline runs in the other direction. When something you tried turns out to be genuinely good - a prompt phrasing, a workflow shortcut, a way of splitting a task - decide immediately whether it should recur, not later. A high-value one-off left as a one-off wastes most of its value: the value was in doing it again, and by the time you remember it happened, the details of what made it work are gone.

### 3. Research Approach

Tell Claude the order to look for information:

```
- Code first, docs second - read source before docs/websites. Source reveals truth.
- Test files are the best reference - tests show exactly how code is meant to be used.
- Pattern-copy - find the closest existing example and adapt, never build from scratch.
```

This stops Claude from hallucinating API docs or stating things that are only true in old versions.

One failure mode is worse than getting something wrong: reporting that something doesn't exist when the search just didn't look hard enough. A grep for one spelling, one case, one file extension that finds nothing proves the search was bounded - not that the thing is absent. Before closing an investigation on a negative result, vary case, separators (hyphen, underscore, space, no separator), singular and plural, and check whether the file types and directories you actually searched were the right ones. Then do one of two things: widen the search and report a true negative, or say exactly what you searched. "No hits under this path in markdown files" is honest. "There is no such thing" is usually a claim you never tested.

Before building any diff, match, or reconciliation, say out loud what the unit of comparison actually is - and check that it's the thing the question is really about. It's easy to build a technically correct comparison that answers nothing: a file-level diff can report most files unchanged while the record inside them moved, split, or merged across files entirely, and the comparison would be accurate and useless at the same time. Ask: if every instance of the container changed shape but the real unit was preserved, would this comparison still say so? If yes is possible, you're comparing the wrong thing - restate the unit before writing the comparison, not after the first result disappoints.

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
- Never write exact counts in any doc - test counts, skill counts, config entry counts, anything that changes as work continues. They go stale silently: the doc doesn't know a test got added, the reader assumes the number shown is current, and it's already wrong. Use a qualifier instead ("several", "over a dozen", "comprehensive as of DATE") or drop the number entirely. This applies to your own CLAUDE.md and feedback files just as much as a public README - see Part 8 for what happens when a skills list hardcodes usage counts.
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
- Test strength over test count - a test that cannot fail still passes.
- Scripts must be user-friendly - show output in terminal, log to a file, never close on completion.
- Always add timing to scripts - log start/end time and per-step timing.
```

**On that second line.** "TDD always" is the most common rule in a workspace CLAUDE.md and the least self-enforcing, because coverage percentages and test counts both rise when weak tests are added. A suite can grow steadily while its ability to detect a defect stays flat. The question is never how many tests exist, but whether each one would fail if the feature were broken.

Five smells, all of which pass a green run: a **structural string-scan** that asserts the source text contains a function name or config key (it verifies someone typed something, so renaming a variable breaks it but shipping a bug does not); an **assertion-free** test that calls the code and asserts nothing, passing as long as no exception escapes; a **dodger** that tests a helper, wrapper or re-implementation rather than the real entry point, so the tested path and the shipped path are different code; an **over-mocked** test that ends up exercising its own mocks, whose worst form is a mock whose signature has drifted from the real object so that every real call would raise and the test never notices; and **assertion roulette**, many unlabelled assertions in one test, so a failure says the test broke but not which behaviour regressed.

The strong version, in order: drive the **real entry point** that production uses; mock **only true boundaries** (network, database, clock, auth, filesystem) and run everything inside the boundary for real; assert **observable outcomes** - returned value, written file, emitted record, resulting state - rather than call sequences, because asserting that a function was called with certain arguments tests the implementation you already wrote while asserting the outcome tests the behaviour you wanted; and **mutation-verify anything that matters** by reintroducing the bug, watching the test fail, then restoring the source. A test you have never seen fail is a test you have not verified, and it takes seconds to check.

One more signal worth watching for while testing: a suspiciously perfect result. A 100% match, a zero-diff, or "everything accounted for" on real data is exactly what a self-comparison bug, an overly loose match key, or a filter quietly dropping the hard cases would also produce. Before reporting a clean result as good news, spend one question ruling out the boring explanation for why it's clean. And when a verification pass does turn up a real defect, don't fix it in the same pass that found it - hand the fix to a fresh check. A fix validated by the same reasoning that just missed the bug once is not independently verified, just re-asserted.

The pattern to watch for is a high test count concentrated on easy pure functions while the main orchestration path and the primary output writer sit at zero behavioural coverage. Look at what the suite covers, not how much of it there is.

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

A concrete example: a session-composition skill once grew a special case for one project because that project's idea backlog lived in a different location than every other project's. The right fix wasn't a branch inside the skill - it was a one-line pointer file in that project pointing at the real location, so the skill kept reading normally with no branch at all. The pattern worth stealing: put the special knowledge in the data a skill reads, not in the skill's logic.

---

## Project-Level CLAUDE.md

Each repo gets its own CLAUDE.md. The workspace one covers HOW you work; the project one covers WHAT this repo is. A great project CLAUDE.md answers the key questions before Claude reads a single line of code.

See `templates/CLAUDE_project.md` for a ready-to-fill template.

### When It Grows Too Big: Split Off a DevContext.md

CLAUDE.md is auto-loaded every session, whether or not the work at hand actually needs it. A project CLAUDE.md's scope is orientation and harm prevention only: what the repo does, build/test/run commands, key paths, and the safety rules that prevent data loss or broken invariants. How specific functions work internally, code patterns, and architecture notes are implementation detail - useful only when you're actively coding in that area, not worth paying for on every session including doc updates and config changes that never touch the code. Split those into a demand-loaded file, for example `docs/References/DevContext.md`, and read it only when a session is actually working on implementation. The trigger to split: CLAUDE.md exceeds roughly 150 lines, or more than half its content is implementation notes rather than orientation and safety rules. One project's CLAUDE.md grew past 300 lines because every dev session appended implementation learnings straight into it - the file paid its full token cost on every session, including ones that never touched that code. The fix was two files with two different load times, not one file trimmed by hand every few weeks.

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

Prohibitions are only half of it. A CLAUDE.md should name two lists explicitly: what the agent may do without asking, and what it must always hand back to you. An unstated boundary gets rediscovered by crossing it - the agent tries the risky operation, gets caught, gets corrected, and the correction only covers that one case. Naming both lists up front closes the whole class at once instead of one instance at a time.

The harder half to hold onto: when a task hits a step the agent genuinely cannot run - a push, a production deploy, an account credential, a physical action - the right response is to deliver the complete solution with that one step clearly handed over, never to quietly shrink the deliverable to only what could be executed. A narrowed deliverable reads as a finished one right up until the un-run step turns out to matter. State the handoff in the output every time it's hit, rather than letting the gap surface later as a surprise.

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

One more habit worth codifying alongside it: when you dump a burst of raw ideas on Claude - dense, half-formed, "I had so many I couldn't get them all out" - tell it to save the raw text verbatim first, in its own section, before writing any refined version. A refined-only summary is Claude's interpretation baked in as the record; if the interpretation missed the point, the original is gone and there's nothing left to correct against. Structure it as a "Raw (verbatim)" section with the exact text - obvious typos fixed, substance untouched - followed by a "Processed" section below it with the expanded, connected, prioritised version. This only applies to genuine idea dumps, not routine back-and-forth; normal conversation doesn't need a verbatim transcript.

One thing that habit does not protect on its own: capturing raw phrasing verbatim is safe going in, and not automatically safe coming back out. The underlying fact inside a raw sentence can be perfectly fine to publish or share while the sentence itself is not, because the way something was actually phrased carries identifying context the fact alone does not - who said it, what system or environment they were working in, what constraint or workaround they were describing around. Verbatim capture is a one-way valve: fine to write down exactly as heard, not fine to forward or publish exactly as heard. The generalising step - turning "here is the raw sentence" into "here is the reusable fact, stripped of who and where" - has to happen at the boundary where content leaves the private capture and enters anything shareable, not get deferred to whenever someone happens to revisit the note. A fact can be entirely public while the original sentence carrying it is not, and the two get confused precisely because the fidelity habit that makes verbatim capture valuable is the same habit that makes it risky to move verbatim.
