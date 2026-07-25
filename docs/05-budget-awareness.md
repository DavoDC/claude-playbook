# Part 5: Budget Awareness

## The Problem

Claude has no fuel gauge. It will confidently start a 3-hour refactor with 25 minutes of budget remaining, get cut off mid-implementation, and leave your codebase in a state that's worse than when it started - broken tests, half-written functions, uncommitted changes that need untangling. Context compaction is just as bad: at 80% context, Claude summarises its own working memory mid-task, losing the detailed understanding it built up. The files it touches after compaction are edited with a different mental model than the ones before.

The damage from hitting limits mid-task isn't just lost time. It's a working tree you have to diagnose and fix.

**This is not built in.** Claude Code does not expose its rate-limit state to Claude. The `tools/` scripts in this repo are custom-built to surface that data and make it actionable. With a fuel gauge, Claude makes active decisions before the limit hits: picks a smaller task, commits what it has, runs `/end-session` to preserve context, schedules a wakeup after the reset. Without one, it drives until it runs out - in the middle of your code.

---

Claude Code has two kinds of resource limits: context window size and API rate limits (5-hour and 7-day usage caps). Both can silently degrade a session if you're not watching them.

## The Three Budget Axes

**1. Context window (ctx%)**

Percentage of the context used this session. At ~80% Claude starts compacting (summarising older context to free space). Compaction mid-session means Claude loses memory of earlier work. Compaction mid-`/end-session` can lose the session record entirely.

**2. 5-hour rate limit**

Percentage of the short-window API quota used. If this hits 83%+ the system will throttle requests within the hour. The reset time is a Unix timestamp in the status data - countdown timers tell you exactly when it resets.

**3. 7-day rate limit**

Percentage of the weekly API quota. If this is high you may hit rate limits even if the session itself is small. Less urgent than the 5-hour limit but worth watching in heavy-use weeks.

---

## What session-status.sh Outputs

A 2-line summary readable by humans and parseable by scripts:

```
MyWorkspace | <model name> (<context window>) | 5h: 43% (r 1h14m) | 7d: 23% (r 6d8h) | ctx: 43%
Claude v<version> | 10:35AM | Sun 24/05/2026
```

The `/dev-session` skill calls this at session start and before continuation decisions to make budget-aware choices automatically.

---

## Budget Decision Table

| Condition | Action |
|---|---|
| 5h >= 83% | Abort. Schedule wakeup after reset. Do not start new work. |
| 7d >= 85% OR ctx >= 80% | Quick-win only. Warn user. |
| 7d >= 70% OR ctx >= 60% | Proceed with caution. Smallest clear item. No batching. |
| Otherwise | Normal session. Batching allowed. |

This prevents the worst outcome: starting a large piece of work at 75% context, running out mid-implementation, and ending with half-finished code.

**One timing trap to know:** the ctx% counter updates between response turns, not between individual tool calls within the same turn. If a session reads several files and then checks budget status in that same turn, the check sees a stale, artificially-low number - none of those reads have been counted yet. Run the budget check after a natural turn boundary (a confirmation gate, the start of the next response) to get an accurate figure. Calling the check twice in the same turn does not help; both calls see the same stale counter.

**When budget runs low, bound the next task, not just the model.** An open-ended "make it better" has no stop condition - as budget approaches exhaustion the prompt needs to get *more* bounded, not less. Give one concrete, verifiable task with explicit in-scope and out-of-scope boundaries, and say explicitly "stop the moment this is verified, do not pick up anything else" - otherwise the model will keep going and burn the reserve you were trying to protect. Prefer an objectively-checkable fix over a subjectively-better one for the last task in a session; if the only remaining work is subjective and ungated (a "does this feel right" call), the correct move is often to spend nothing and hand it to a human review instead of gambling the last of the budget on it.

---

## Model Choice

Claude Code lets you choose which model powers your sessions. The practical rule:

**Use Sonnet for most work. Opus burns budget too fast for daily use.**

Sonnet handles 95%+ of real engineering work well: writing code, debugging, reading files, making commits, running the improvement loop. The quality difference for typical tasks is small. The budget difference is large - Opus uses significantly more of your quota per session.

Keep Opus for the genuinely hard problems: architecture decisions, complex debugging you've already tried to solve, anything where you need the extra reasoning depth. Don't burn it on routine feature work.

If you're on a plan with rate limits, the session statusline (from `tools/`) shows which model is active and exactly how much of your 5-hour and 7-day budget you've used. Before starting a heavy Opus session, check the 7-day figure.

---

## Effort Level

Effort controls adaptive reasoning - how much the model thinks before responding. It is a second budget lever independent of model choice.

**The key insight:** Claude Code's own UI describes `high` as "burns fastest - medium handles most tasks." Sessions contain a mix of complex reasoning and routine work (file reads, git ops, edits). Paying high-effort cost across every routine step wastes budget.

**Default: `medium`.** Set this via your launcher script:

```bat
cmd /k claude --effort medium
```

Using the `--effort` flag on launch sets the level for that session without writing to settings - so it resets cleanly each time. This matters because `/effort low` within a session writes to `settings.json` and persists to the next session; the launcher flag overrides it.

**For complex reasoning on demand:**
- Say `ultrathink` in your prompt - applies deep reasoning for that turn only, session level unchanged
- Use skills that have `effort: high` or `effort: xhigh` set in their frontmatter (e.g. /think, /aristotle, /deep-dive, /reflection) - the skill overrides the session level automatically and reverts when done

**Setting effort in skill frontmatter:**

```yaml
---
description: My heavy reasoning skill
effort: high
---
```

This means you don't manually switch effort before/after complex skills - it happens automatically. Route routine work through `medium`, and let the skills that need depth declare it.

(full reference: [Adjust effort level - Claude Code docs](https://github.com/ericbuess/claude-code-docs/blob/main/docs/model-config.md#adjust-effort-level))

---

## When a Setting Isn't Honoured: Check Env Vars First

Environment variables are the highest-precedence configuration layer and the least visible one. For subagent model selection, resolution order is: environment variable, then the `model=` parameter passed to the call, then the subagent's own frontmatter, then the parent conversation's active model. An environment variable set once - often months earlier, for a reason nobody remembers - silently overrides every explicit `model=` argument from then on. Nothing errors. The work just comes back worse, using a cheaper model than intended, and it is easy to mistake that for a capability limit ("my plan tier doesn't support this") rather than a stale config value.

The same silent-override behavior applies to effort level: a Windows/shell environment variable can lock effort at a fixed level and make `/effort` appear broken, with no indication in the UI that anything is overriding it.

**The rule:** when any model, effort, or capability setting appears not to be honoured, check the environment block of your settings file and your shell's environment variables *first* - before any theory about plans, tiers, quotas, or entitlements. Config beats cosmology. It costs one command to check and can save weeks of planning around a constraint that does not actually exist. Once you find and clear the stray value, confirm the fix by observation (the tokens land where expected) rather than by the absence of an error, since the failure mode here is silence in both directions.

This generalizes beyond env vars: any capability limit that gets written into a doc as a bare fact ("X is broken, use the workaround") should carry its evidence and who established it, not just the conclusion. A limit recorded as settled forecloses the five-minute re-test that would have found the one-line fix; a limit recorded as a hypothesis, with what was actually observed, invites someone to check it again next time it matters. Be especially suspicious of a constraint that conveniently explains a disappointment - "the plan won't allow it" is exactly the kind of story that closes an investigation instead of opening one.

---

## Session Strategy - Shorter is Better

Every prompt sends the entire conversation history. As a session grows, each exchange costs more tokens than the one before - early messages are re-sent every time.

The most token-efficient approach:

1. **One session per main feature or topic.** A focused 30-minute session costs far less than a 3-hour session that keeps compacting. When you hit compaction (~80% context), Claude loses memory of early work and re-explaining costs tokens.

2. **Write ideas down before starting, not during.** Keep a doc with everything you want done. Work through a few items per session, run `/end-session`, close, open fresh. This keeps sessions short and context cheap.

3. **Front-load your prompt.** Tell Claude everything you want in one message - it will figure out the best order and approach. One detailed 8-line prompt beats eight back-and-forth exchanges covering the same ground. Longer prompts, fewer rounds.

4. **Short + focused wins.** Rarely hitting max context is a sign of good session hygiene - it means you're closing before compaction, not fighting through it.

### Two Levers: Fixed Cost vs Message Growth

`/context` splits usage into a fixed session-start cost (paid once, every session, before you type anything) and message growth (paid per turn, which determines how long the session lasts before compaction). They need different tuning.

**Fixed cost** is dominated by whatever project-level instructions load automatically every session - a CLAUDE.md, an enforced-rules file, anything auto-attached. Keep that content well under whatever hard limit you've set for it, and start trimming before you're close to the ceiling, not at it. Route workflow-specific detail out of the always-loaded file and into a demand-loaded doc (a process doc, a skill file) that only gets pulled in when the relevant task comes up. The floor here is harm-prevention content - never cut a safety rule to save tokens, that trades safety for runway, which is the wrong trade. The actual lever is redundancy and verbosity, not rule count: shorter bullets and pointers instead of inline detail, never fewer invariants.

**Message growth** is the larger share of a typical session and the part under direct per-turn control:
- Don't re-read a file already read this session - reference the earlier output instead.
- Use offset/limit on large file reads when only a section is needed.
- Delegate wide, exploratory searches to a subagent so the raw search output stays in the subagent's context and only the synthesized result returns to the main thread.
- Prefer structured search tools over raw dumps of file contents.
- Batch independent tool calls in parallel - this doesn't cut total tokens, but it cuts round-trips, which matters when compaction risk is time-based as well as token-based.
- Compact at a natural breakpoint (right after finishing a subtask) rather than waiting for the forced threshold - a compaction forced mid-task loses more useful detail per token freed than one you choose.

---

## Building the System

The whole thing (statusline.py + check-budget.sh + session-status.sh) is under 200 lines total. Here is how it is wired:

### Step 1 - Configure Claude Code's statusline

In `.claude/settings.json`:
```json
{
  "statusline": {
    "command": "python3 /path/to/tools/statusline.py"
  }
}
```

Claude Code invokes this command via stdin for every status update, passing a JSON object containing `model`, `context_window`, `rate_limits`, `version`, `cwd`, etc.

### Step 2 - statusline.py does two things

(1) Print the formatted status line to stdout for display in your terminal. (2) Write the raw JSON to a temp file so other scripts can read budget state without making API calls.

```python
#!/usr/bin/env python3
import sys, json, os, tempfile

d = json.load(sys.stdin)

# Write raw data to temp file for other tools to read
cache_path = os.path.join(tempfile.gettempdir(), 'claude-statusline-data.json')
with open(cache_path, 'w') as f:
    json.dump(d, f)

# Extract and format what you want to display
model = (d.get('model') or {}).get('display_name', '?')
ctx   = (d.get('context_window') or {}).get('used_percentage', 0)
five  = ((d.get('rate_limits') or {}).get('five_hour') or {}).get('used_percentage')
week  = ((d.get('rate_limits') or {}).get('seven_day') or {}).get('used_percentage')

print(f"{model} | ctx:{int(ctx)}% | 5h:{int(five or 0)}% | 7d:{int(week or 0)}%")
```

The key: the temp file is written by `statusline.py` whenever Claude Code polls the statusline. Any other script can read it at any time to get current budget state.

### Step 3 - check-budget.sh reads the temp file

Reads from `$(python3 -c "import tempfile; print(tempfile.gettempdir())")/claude-statusline-data.json` and extracts:
- `rate_limits.five_hour.used_percentage` and `resets_at` (Unix timestamp)
- `rate_limits.seven_day.used_percentage` and `resets_at`
- `context_window.used_percentage`

Converts `resets_at` timestamps to human countdowns (e.g. "1h32m") by subtracting `datetime.now().timestamp()`.

Emits a warning line if `five_hour >= 83` including the seconds until reset - so the calling script can pass it to `ScheduleWakeup()`:

```
5h NEARLY EXHAUSTED: 86%, resets in 1h12m - use ScheduleWakeup(4320) to skip past reset
```

### Step 4 - session-status.sh wraps it all

```bash
MODEL=$(python3 -c "
import json, os, tempfile
d = json.load(open(os.path.join(tempfile.gettempdir(), 'claude-statusline-data.json')))
print((d.get('model') or {}).get('display_name', 'Unknown'))
")
BUDGET=$(/path/to/check-budget.sh 2>/dev/null)
echo "$MODEL | $BUDGET"
```

### Step 5 - Skills call it via Bash

In your SKILL.md files, run session-status.sh at session start:
```
Bash("bash /path/to/tools/session-status.sh")
```

Parse the output for the three percentages. Build decision logic:
- `five_pct >= 83` -> abort + `ScheduleWakeup(seconds_until_reset + 300)`
- `ctx_pct >= 80` -> quick-win only
- `ctx_pct >= 60` -> caution mode

The full scripts are in `tools/` - copy them to your workspace and adjust the path in settings.json.
