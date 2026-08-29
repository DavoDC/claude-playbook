# Part 6: Sessions and Memory

> **Field note.** Written from practice rather than machine-checked, and not covered by `tools/selftest.sh`. Last reviewed 2026-08-02 against Claude Code v2.1.220. Opinionated, and it may lag the harness.

## Session Launcher

Claude Code has no built-in launch UI - you type flags every time (`claude --model sonnet --continue`). A session launcher script replaces that with an arrow-key or number-key picker for session type and model.

`tools/launch-claude.sh` is a ready-to-use template. Copy it to your workspace, make it executable, and run it instead of `claude` directly:

```bash
cp tools/launch-claude.sh ~/workspace/launch.sh
chmod +x ~/workspace/launch.sh
./launch.sh
```

The picker shows:

```
  Session?
  (arrows + Enter  |  1-4 quick  |  q quit)

> bypass-permissions  (skip permission prompts - use with trusted projects)
  new                 (fresh start)
  continue            (auto-resumes most recent, no prompt)
  resume              (shows conversation picker)
```

Then a second screen picks the model (sonnet / haiku / opus). The selected command is logged to `logs/claude-launch.log` for audit.

**Adapting it:** Change `WORKSPACE_DIR` at the top to an absolute path if you don't always launch from the same directory. Add or remove session options by editing the `_pick "Session?"` block and the matching `case $session` block - they must stay in sync (index 0 is the first option).

---

## /end-session - The Session Drain

`/end-session` is the most-used skill in a serious setup. It is the crux of the continuous improvement loop - everything good that happened in a session gets preserved here.

### What It Does

1. **Captures session state** - timing, budget figures, any uncommitted changes
2. **Writes a session fragment** - structured record of what happened, commits made, corrections received, and transferable lessons from the session
3. **Reconciles the task list** - removes completed items, adds new ones surfaced during the session
4. **Appends to the daily log** - one row per session (detailed enough for context the next day)
5. **Runs finalize scripts** - drains internal Claude memory to the tracked memory folder, consolidates into session history, commits everything in logical chunks

### The Session Fragment

The fragment is the most important artifact. Key sections:

```
## Session [N] - [Date]

**Time:** HH:MM - HH:MM (duration)
**Model:** <model in use this session>
**Budget:** ctx% used

**What happened:**
1. ...

**Commits:** (hashes)

**User feedback this session:** exact corrections, preferences received

**Transferable lessons (REQUIRED):**
- Surprising gotcha, generalizable pattern, or technique discovered

**Mark done:**
- [x] Full text of completed task
```

The `**Mark done:**` section is script-parsed - a finalize script extracts these lines and appends them to `completed-actions.md` automatically.

### Two-Stage Finalize

For speed, end-session runs in two stages:

- **Stage 1 (synchronous, fast):** drains Claude's internal memory to the tracked folder, appends completed items, cleans temp files. User waits for this.
- **Stage 2 (background):** consolidates the session fragment into session-history.md, makes commits (session record, task reconcile, feedback files, memory drain, logs). User doesn't wait.

This keeps `/end-session` feeling instant while doing real work in the background.

### Why Committing Matters

Every end-session produces several commits. This isn't bureaucracy - it's what makes the memory system work across machines and across weeks. If sessions aren't committed, the next session cold-starts with no context. Committed sessions mean Claude can read back months of what happened.

---

## The Memory System

Claude's built-in session memory is erased at context compaction. For memory that persists across sessions and machines, you need a memory system built on files.

The approach: a `memory/` folder inside a git-tracked repo. Markdown files, committed, pushed. When Claude starts a session it reads `MEMORY.md` (an index), then demand-loads specific files when they become relevant.

### Types of Memory Worth Keeping

**User** - your background, preferences, what explanations to skip. E.g. "deep Python expertise, new to React - frame frontend explanations in backend analogues." Helps Claude calibrate how it explains things.

**Feedback** - corrections and confirmations of approach. These are the improvement loop in persistent form. Lead with the rule, then a Why line (the reason, often a past incident), then a How to apply line (when this fires). The Why line is what lets you judge edge cases - "don't mock the database in tests" + "we got burned when mocked tests passed but prod migration failed" gives you the context to decide whether mocking is OK in a new situation.

**Project** - who is doing what, why, by when. Convert relative dates to absolute dates when saving ("Thursday" -> "2026-05-29") so they remain interpretable later. Lead with the fact, then Why (motivation) and How to apply (how it shapes suggestions).

**Reference** - where to find things: ticket tracker project names, dashboards, credential locations.

### What NOT to Put in Memory

- Code patterns - read the source instead
- Git history - use `git log`
- Anything already in CLAUDE.md or enforced-rules.md
- Ephemeral task details that only matter for the current session

### MEMORY.md - The Index

MEMORY.md is a navigation guide, not content storage. Each entry is one line with a pointer to the actual file. Claude reads it first, then loads specific files on demand. Keep it under 150 lines or it becomes a liability (lines after 200 get truncated in context).

A memory that names a specific function, file, or flag is a claim that it existed when the memory was written. Before acting on it, verify it still exists. Memory goes stale. If a recalled memory conflicts with what you observe now, trust what you observe - and update the stale memory.

### Session History

Every session gets a fragment written by `/end-session`. These are consolidated into `session-history.md` by the finalize script. This gives Claude a running history of what was done, what was learned, and what's pending. Claude reads this at session start to get context without you having to re-explain.

### File Findings by Subject, Not by Run

A test run, an experiment, or a debugging session tempts you to write a new dated file named after itself - `round-3-crash.md`, `test-round-4.md`. This does not scale, and it buries the durable lesson inside a narrative about one afternoon: by the tenth round you have ten files, and the rule that governs every future decision is sitting in whichever one happened to contain it.

The fix is three distinct kinds of document, not one file per event. A subject document answers "what do we know about X" - durable, named for the subject, and edited in place as understanding improves, not appended to chronologically. A single evidence log answers "what actually happened on each run" - one file, newest first, one section per run, preserving the concrete details verbatim. And the narrative - what happened this session and why it mattered - is session history itself, already covered above.

The reason this split matters is that evidence and analysis want opposite treatment. Evidence is immutable and accumulates - never rewrite what a run actually returned. Analysis is mutable and consolidates - a rule refined on round four should overwrite round three's version of it, not sit beside it as a second opinion. Filing everything by run number forces both into the same append-only shape, which is right for the evidence and wrong for the rule. This mirrors the reasoning behind one-file-per-rule feedback files above: the unit of storage should be the thing that persists, not the event that produced it. Before creating a file named for a round, a date, or an attempt number, ask which existing subject document should absorb the finding instead - create a new file only when a genuinely new subject appears, not a new instance of an old one.

---

## Common Gotchas

### Manual Edits Getting Overwritten

When Claude reads a file, the content goes into its context window. If you manually edit that file later and then ask Claude to modify it, Claude writes edits on top of what it remembers - not what's currently on disk. Your manual changes get overwritten.

The fix: **Tell Claude when you've manually edited a file.** "I just edited `main.py` manually - please re-read it before making any changes." That forces a fresh Read tool call from disk instead of using the stale context copy.

If you notice Claude undoing your manual edits: it used its context memory. Tell it to re-read the file and it will see what you changed.

### Python Is a Good Language Choice for Claude

When you're building a new tool and have language flexibility, Python is the best choice for Claude-assisted development:

- No compilation step - Claude runs, tests, and iterates in seconds
- Readable output that Claude can parse and reason about
- Vast standard library coverage means fewer dependencies to manage
- Error messages are explicit and Claude handles them well

For scripts, utilities, and automation tools, default to Python. Compiled languages (C++, Java, C#) work but the build friction slows iteration significantly - Claude has to wait for compilation between every change, and build errors are harder to diagnose than runtime errors.

### Claude Isn't Aware of Its Own Features

Claude Code has many features - hooks, MCP servers, custom slash commands, statusline config, remote control, thinking modes - but Claude has no awareness of them by default. Claude doesn't know what it can configure unless you tell it.

A practical fix: clone the docs locally so the whole corpus is greppable in one command, rather than pointing Claude at individual pages:

```
git clone https://github.com/ericbuess/claude-code-docs
```

See `docs/11-workspace-repo.md` for where this clone should live and why. Then ask Claude to read the docs and suggest features that would help your workflow. It will find things you didn't know existed. This works especially well for initial setup - Claude can read its own docs and then self-configure for your use case.
