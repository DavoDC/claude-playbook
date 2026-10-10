---
description: End-of-session routine. Writes a session fragment, reconciles the task list, appends a log row, routes learnings, and commits. Concurrent-safe and fast.
disable-model-invocation: true
when_to_use: "ONLY the user invokes this by typing /end-session directly; Claude must never auto-invoke it. Run at the end of every work session. For long or risky sessions use /checkpoint for mid-session saves before risky refactors."
---

# End-of-Session Routine

The crux of the continuous-improvement loop. It runs often, so it must be fast AND never lose data. This is a template: replace each `<placeholder>` with your own path once (`<memory>` your memory folder, `<fragments>` a folder of per-session fragments, `<task-list>` your pending-actions file, `<daily-log>` an optional per-day log).

**Architecture:** scripts own every mechanical edit (draining, consolidating, appending to the completed list, committing). The model authors only what needs judgment: the session fragment (narrative and feedback detection) and a one-row log append. If you have no scripts yet, do the mechanical parts by hand in the same order; the fragment still makes concurrent sessions safe.

**Target:** under 15 seconds. No confirmations. Execute all steps.

---

## Step 1 - Prep (one shell call)

Run your prep script from the repo root. It should print `KEY=VALUE` lines the later steps use: a session id, the date and time, start and end time, duration, the daily log file and whether it exists, a count of dirty files outside memory, budget readings (`?` when unavailable), and how many lessons the lesson-detector hook flagged today.

**If dirty non-memory files exist:** say so once in a single line ("N non-memory files dirty: X, Y, Z. Commit them first with /commit-chunks if you want named commits, otherwise they stay dirty."), then continue. Do not run a commit skill automatically: end-session is for session-scoped state only, and coupling the two is a foot-gun.

## Step 1b - Gates (refuse on failure)

Any repo-specific gate worth enforcing at the close goes here, each as "run X, a non-zero exit means stop, fix, rerun until it exits 0". Examples worth having: a backlog format check (drift caught here costs one fix, drift found by the next reader costs a session), a scan for subprocess calls that open a visible window in GUI apps, a check for leftover background interpreter shells from finished subagents, a check that a doc did not gain an appended dated section with its old text untouched, a probe gate that refuses to call a launcher done on unit tests alone. Do not bypass a gate to finish faster.

## Step 2 - Two parallel writes

Issue these as parallel tool calls.

### 2a. Session fragment

**File:** `<fragments>/session_<SESSION_ID>.md`

Write `Session ??` literally. Do NOT substitute a number: the consolidate script owns numbering, and hardcoding one collides under concurrency.

```
## Session ?? - <date> (<type>)

**Time:** <start> - <end> (<duration>)
**Model:** <active model name from the system prompt>
**Budget:** <reading now> (session burned: <delta>% of the 7-day window; omit if unavailable)
**This session:** one-line summary

**What happened:**
1. ...

**Commits:** (hashes if any)

**User feedback this session:** (exact corrections, praise, preferences, or "No new feedback")

**What worked this session:** (what fired correctly without prompting: a skill that landed, a rule that prevented a mistake. Be specific, or "Nothing notable.")

**Transferable learnings (REQUIRED):**
- Tag each item with a routing destination:
  - `-> workspace`: Claude behaviour that applies across all projects
  - `-> repo:<name>`: specific to one project's architecture or conventions
  - `-> discard`: implementation detail fixed in code, no future value
- Re-read after writing. For each workspace item ask whether it deserves its own feedback file. For each repo item ask whether it is harm-prevention or orientation (CLAUDE.md) or an implementation detail (the project's deep-context doc).

**New feedback files created:** (filenames, or "none")

**Mark done (appended to the completed list by the finalize script):**
- [x] full text of an item completed this session
```

- Type is interactive, overnight or short. Be concise.
- The `**Mark done:**` section is script-parsed: lines starting with `- ` between that heading and the next `**` or end of file are appended under today's heading in the completed list. Skip the section if nothing was completed.
- Anything listed there must also be REMOVED from the task list in 2b.
- **Parity check:** if the lesson-detector count for today is higher than the number of feedback files you wrote, name the gap under "User feedback this session" so lessons are not silently dropped.

### 2b. Task-list reconcile and log row

1. Read `<task-list>` in full, and only the tail of `<daily-log>` (offset to the last few rows). Never read the completed list; the script appends to it.
2. Edit `<task-list>`: delete every item under Mark done. Add a new item ONLY if the user asked for it or you promised it this session. Never file work you merely noticed was possible: an unasked-for item is a chore the user must read and reject on every future scan. Remove stale items. Never leave `[x]` in the pending file.
3. Append one row to `<daily-log>`: `| start - end | duration | summary | ticket |`, matching the table format. Create the file with its header block if it does not exist. Name outcomes (shipped or blocked), not topics. If the session covered three or more distinct areas, write one row per area.

If an edit fails because a concurrent session touched the file, re-read the narrow slice and retry. The fragment is durable, so nothing is lost.

## Step 3 - Finalize (two stages)

**Stage 1, synchronous and fast:** drain any memory the tool wrote in its own folder into your tracked memory folder, append the Mark-done bullets to the completed list, clean temp files.

**Stage 2, in the background:** consolidate the fragment into the session history and commit with narrow pathspecs, one commit per concern (session record and log; task-list reconcile; new feedback and index; drained memory; logs). Use a lock so two concurrent runs wait instead of colliding. If the previous run's stage 2 has not finished, stage 1 is idempotent, and stage 2 will wait on the lock.

Files that were dirty before the session started stay untouched.

## Step 4 - Route learnings (always, even on a routine session)

For each item in Transferable learnings:
- **`-> workspace`**: if it is a durable rule not already captured, write a feedback file (frontmatter, Why, How) and add a one-line pointer to the memory index.
- **`-> repo:<name>`**: harm-prevention or orientation goes into that repo's CLAUDE.md (one tight bullet, under an existing section); implementation detail goes into the repo's on-demand deep-context doc. The file lives in a different repo, so commit it there separately.
- **`-> discard`**: no action.

Do not skip this step because the session felt routine. Repo-specific learnings are the ones most often dropped.

## Step 4b - Changelog (only if tooling changed)

For each hook, skill, rule, process or tool change shipped this session, append a row to your changelog: `| date | sha7 | category | one-line description | portability |`. Skip it for pure project work.

## Step 4c - Scratch triage

Every scratch file should carry a `DELETE-AFTER:` condition. List the scratch folder one line per entry (`<file> -> <condition>` or `MISSING MARKER`) and show it verbatim. Flag conditions that look already met so the user can remove them; never auto-delete. Skip if the folder is empty.

## Step 5 - Summary (one line)

Example: `Session 12 saved (2h15m). 1 feedback file, 1 repo learning -> myproject CLAUDE.md, 3 mark-done. Committed.`

If context is at 70 percent or more, add: `Context at X% - close the terminal and start fresh.` Do not recommend compaction here: after this routine everything is committed to files, and a fresh session is strictly better. If the budget delta is 5 points or more of the weekly window, add a note that the session burned a notable share.

---

## Why this shape

- **Scripts own every mechanical edit.** The model never reads the large completed list and never improvises git chunks inside this skill.
- **The model authors only judgment:** the narrative, feedback detection, the task-list decisions, the log summary.
- **The fragment is the single artifact.** It is concurrent-safe by design, and the Mark-done tail is the structured hand-off between model and script.
- **Committing non-memory work is out of scope.** Warn once; the user runs a commit skill separately.
