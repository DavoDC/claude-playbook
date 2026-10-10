# Part 4: Budget Awareness

> **Core.** Part of the maintained quick-start path. The tools and settings snippets it references are asserted by `tools/selftest.sh` on every push.

## The Problem

Claude has no fuel gauge. It will confidently start a 3-hour refactor with 25 minutes of budget left, get cut off mid-implementation, and leave the codebase worse than it started - broken tests, half-written functions, uncommitted changes to untangle. Compaction is just as bad: at 80% context Claude summarises its own working memory mid-task, losing the detailed understanding it built, so files touched afterwards are edited with a different mental model. The damage isn't just lost time; it's a working tree you must diagnose and fix.

**This is not built in.** Claude Code does not expose its rate-limit state to Claude; the `tools/` scripts here surface it. With a fuel gauge Claude decides before the limit hits: picks a smaller task, commits what it has, runs `/end-session`, schedules a wakeup after the reset. Without one, it drives until it runs out - in the middle of your code.

---

Claude Code has two kinds of resource limits, context window size and API rate limits (5-hour and 7-day caps), and both can silently degrade a session.

## The Three Budget Axes

**1. Context window (ctx%)**

Percentage of context used this session. At ~80% Claude starts compacting (summarising older context), losing memory of earlier work; compaction mid-`/end-session` can lose the session record entirely.

**2. 5-hour rate limit**

Percentage of the short-window API quota used. At 83%+ the system will throttle requests within the hour. The reset time is a Unix timestamp in the status data, so countdown timers show exactly when it resets.

**3. 7-day rate limit**

Percentage of the weekly API quota. When high you may hit limits even in a small session. Less urgent than the 5-hour limit but worth watching in heavy weeks.

---

## What session-status.sh Outputs

A 2-line summary readable by humans and parseable by scripts:

```
MyWorkspace | <model name> (<context window>) | 5h: 43% (r 1h14m) | 7d: 23% (r 6d8h) | ctx: 43%
Claude v<version> | 10:35AM | Sun 24/05/2026
```

Any work skill or loop can call this at session start and before continuation decisions to make budget-aware choices automatically.

---

## Budget Decision Table

| Condition | Action |
|---|---|
| 5h >= 83% | Abort. Schedule wakeup after reset. Do not start new work. |
| 7d >= 85% OR ctx >= 80% | Quick-win only. Warn user. |
| 7d >= 70% OR ctx >= 60% | Proceed with caution. Smallest clear item. No batching. |
| Otherwise | Normal session. Batching allowed. |

This prevents the worst outcome: starting a large piece of work at 75% context and ending with half-finished code.

**A timing trap:** the ctx% counter updates between response turns, not between tool calls within a turn. A budget check after reading several files in the same turn sees a stale, artificially-low number. Check after a natural turn boundary (a confirmation gate, the start of the next response); calling twice in the same turn doesn't help, both see the same stale counter.

**When budget runs low, bound the next task, not just the model.** An open-ended "make it better" has no stop condition; as budget runs out the prompt must get *more* bounded. Give one concrete, verifiable task with explicit in-scope and out-of-scope boundaries and say "stop the moment this is verified, do not pick up anything else", or the model keeps going and burns the reserve. For the last task of a session prefer an objectively-checkable fix over a subjectively-better one; if the only remaining work is subjective and ungated ("does this feel right"), often spend nothing and hand it to human review.

---

## Model Choice

**Use Sonnet for most work. Opus burns budget too fast for daily use.**

Sonnet handles 95%+ of real engineering work well: writing code, debugging, reading files, commits, the improvement loop. The quality difference for typical tasks is small; the budget difference is large, since Opus uses significantly more quota per session.

Keep Opus for genuinely hard problems: architecture decisions, complex debugging you've already tried, anything needing the extra reasoning depth. Not routine feature work.

On a rate-limited plan the session statusline (from `tools/`) shows the active model and your 5-hour and 7-day usage. Before a heavy Opus session, check the 7-day figure.

---

## Effort Level

Effort controls adaptive reasoning - how much the model thinks before responding - a second budget lever independent of model choice.

**The key insight:** Claude Code's own UI describes `high` as "burns fastest - medium handles most tasks." Sessions mix complex reasoning with routine work (file reads, git ops, edits); paying high-effort cost on every routine step wastes budget.

**Default: `medium`.** Two mechanisms can set it, with different persistence semantics; the wrong one defeats the point.

An environment variable (for example a shell or launcher-set `CLAUDE_CODE_EFFORT_LEVEL`) looks like the obvious way to pin a default, but it leaks into the whole session and outranks everything, including mid-session `/effort` calls. Every later attempt to raise effort silently gets overridden: `/effort high` appears to work, then the model reasons at the env var's level, with no error. That defeats "reset the default at session start, then let the session control itself."

Patch the default directly instead: the `effortLevel` key in `settings.json` at launch, or the `--effort` CLI flag below, which sets the level for that session without a persistent override, so it resets cleanly each launch and doesn't block later `/effort` changes.

```bat
cmd /k claude --effort medium
```

A settings-file or flag default resets each session and doesn't shadow later in-session changes, so `/effort high` still works. Skill-level `effort: high` frontmatter also overrides the session level - but not the environment variable, so a stray `CLAUDE_CODE_EFFORT_LEVEL` still wins over a skill's declared effort. Prefer the flag or settings patch; avoid an environment variable unless you want it to override every in-session change.

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

No manual switching around complex skills. Route routine work through `medium` and let skills that need depth declare it.

(full reference: https://code.claude.com/docs/en/model-config#adjust-effort-level)

---

## When a Setting Isn't Honoured: Check Env Vars First

Environment variables are the highest-precedence configuration layer and the least visible. For subagent model selection the resolution order is: environment variable, then the `model=` parameter on the call, then the subagent's frontmatter, then the parent conversation's model. An environment variable set once, often months earlier for a forgotten reason, silently overrides every explicit `model=` argument from then on. Nothing errors; the work comes back worse on a cheaper model than intended, easily mistaken for a capability limit ("my plan tier doesn't support this") rather than a stale config value.

Effort level behaves the same: a Windows/shell environment variable can lock effort and make `/effort` appear broken, with no UI indication.

**The rule:** when any model, effort or capability setting appears not honoured, check your settings file's environment block and your shell's environment variables *first*, before any theory about plans, tiers, quotas or entitlements. Config beats cosmology: one command to check, and it can save weeks of planning around a constraint that doesn't exist. After clearing the stray value, confirm by observation (the tokens land where expected), not by absence of an error, since the failure is silent in both directions.

This generalizes: any capability limit written into a doc as a bare fact ("X is broken, use the workaround") should carry its evidence and who established it. A limit recorded as settled forecloses the five-minute re-test that would find the one-line fix; one recorded as a hypothesis, with what was observed, invites a re-check when it matters. Be suspicious of a constraint that conveniently explains a disappointment - "the plan won't allow it" closes an investigation instead of opening one.

---

## Session Strategy - Shorter is Better

Every prompt sends the entire conversation history, so each exchange costs more than the last; early messages are re-sent every time.

The most token-efficient approach:

1. **One session per main feature or topic.** A focused 30-minute session costs far less than a 3-hour one that keeps compacting, after which Claude loses early work and re-explaining costs tokens.

2. **Write ideas down before starting, not during.** Keep a doc of everything you want done, work a few items per session, run `/end-session`, close, open fresh.

3. **Front-load your prompt.** Tell Claude everything in one message; it will find the order and approach. One detailed 8-line prompt beats eight back-and-forth exchanges.

4. **Short + focused wins.** Rarely hitting max context means you're closing before compaction, not fighting through it.

### Two Levers: Fixed Cost vs Message Growth

`/context` splits usage into a fixed session-start cost (paid every session before you type) and message growth (paid per turn, determining how long the session lasts before compaction). They need different tuning.

**Fixed cost** is dominated by project-level instructions loaded every session - a CLAUDE.md, an enforced-rules file, anything auto-attached. Keep it well under your hard limit and start trimming before the ceiling, not at it. Route workflow-specific detail into a demand-loaded doc (process doc, skill file). The floor is harm-prevention content: never cut a safety rule to save tokens, which trades safety for runway. The lever is redundancy and verbosity, not rule count: shorter bullets and pointers instead of inline detail, never fewer invariants.

**Message growth** is the larger share of a typical session and under direct per-turn control:
- Don't re-read a file already read this session - reference the earlier output instead.
- Use offset/limit on large file reads when only a section is needed.
- Delegate wide, exploratory searches to a subagent so the raw search output stays in the subagent's context and only the synthesized result returns to the main thread.
- Prefer structured search tools over raw dumps of file contents.
- Batch independent tool calls in parallel: no fewer total tokens, but fewer round-trips, which matters when compaction risk is time-based as well as token-based.
- Compact at a natural breakpoint (right after finishing a subtask) rather than at the forced threshold; a forced mid-task compaction loses more useful detail per token freed.

---

## Token-Saving Mechanisms That Compound

The levers above are habits. These are mechanisms: each one removes a recurring cost without relying on anyone remembering.

**A session-start brief.** A SessionStart hook prints a few lines (the first handful of open tasks, the latest few session headings, today's date, branch and dirty-file count) so a session orients without reading long files. Cap it in bytes, not lines, so a pathological file cannot blow the budget, and let a missing source file produce an empty section rather than an error. `tools/session-brief.py` is a working, tested version with configurable paths.

**A token baseline with a down-only ratchet.** Claude Code writes a transcript per session. `tools/token-baseline.py` reads them and reports the median first-turn context (what every session pays before you type), the average per turn, compactions, and oversized shell results. Store a ceiling for each number in a small JSON file (`tools/token-ceilings.example.json`), run `--check` in your test run so a regression fails loudly, and run `--ratchet` after a cleanup so the ceiling only ever moves down. Without a measurement, "we saved tokens" is a belief.

**Size ceilings, and a budget for the group.** A per-file limit misses the case where several always-loaded files each sit under their own cap while their sum keeps growing. Keep a short manifest of every file that loads into every session, check the combined size against a soft and a hard byte budget, and run that check whenever any member is edited.

**Read and shell caps.** Deny a whole-file read of a large file and ask for a section, and deny known-flooding shell commands unless their output is already limited. Both are hooks, and working examples are in `hooks/examples/`.

**Serial, bundled subagents.** Many small parallel subagents cost the orchestrator more context, because each report and diff must be read and checked, than a few larger sequential ones. Group queued fixes by shared code location, dispatch one bundle, verify the artifact, then dispatch the next. See [Part 12](12-multi-agent-orchestration.md#serial-bundled-dispatch).

## The Bottleneck Is Often a Human Action, Not Model Budget

Everything above measures whether the model has budget left. Also check the opposite: whether finished work sits idle waiting on a small human action - a click, a yes/no answer, plugging something in, approving a change - rather than on model capacity. Easy to miss, because when budget is healthy the instinct is to keep building, the wrong response to a queue never blocked on building.

Keep an explicit ranked list of "waiting on a human action" items and work it down before starting new work, as you would check the budget axes. The two constraints are measured by different instruments: a budget readout shows capacity left, and nothing shows how much finished work is parked behind a click. When usage is well under the ceiling and output still feels stalled, look there first.

This is not an argument against delegating when delegation is right - see [Part 12](12-multi-agent-orchestration.md#when-to-delegate-vs-do-it-directly). It is an argument for checking, before delegating or building more, whether the bottleneck is capacity to build or a short list only a human can finish. Building more just grows a backlog that was never short of finished work.

---

## Building the System

The whole thing (statusline.py + check-budget.sh + session-status.sh) is small enough to read end to end in one sitting. Here is how it is wired:

### Step 1 - Configure Claude Code's statusline

In `.claude/settings.json`:
```json
{
  "statusLine": {
    "type": "command",
    "command": "python3 /path/to/tools/statusline.py"
  }
}
```

Platform caveat: the bare name `python3` is not a real interpreter everywhere. On Windows it can be a Store stub that hangs and ignores timeouts, so use `python` or a full interpreter path there, and run it by hand once before trusting it in a hook or status line.

The key is camelCase and `"type": "command"` is mandatory. A wrong key is accepted silently, so the symptom is not an error but every budget check below reporting no data forever.

Claude Code invokes this command via stdin for every status update, passing a JSON object containing `model`, `context_window`, `rate_limits`, `version`, `cwd`, etc.

Updates are event-driven, so they can go quiet exactly when the number matters: an unattended loop whose main session idles waiting on background subagents produces no status events, so the cache below ages while the loop keeps spending. Set the optional `refreshInterval` field (seconds) to also re-run the command on a timer (full reference: https://code.claude.com/docs/en/statusline).

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

Emits a warning line if `five_hour >= 83` including the seconds until reset:

```
5h NEARLY EXHAUSTED: 86%, resets in 1h12m
```

`ScheduleWakeup` clamps its delay to 60-3600 seconds, so a reset more than an hour away can't be skipped in one call. Use bounded wakeups, not one long sleep: call `ScheduleWakeup(min(seconds_until_reset, 3600))`, re-run the budget check on each wake, and reschedule if the reset hasn't passed. The loop stops once the 5-hour window has reset.

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
- `five_pct >= 83` -> abort + `ScheduleWakeup(min(seconds_until_reset, 3600))`, re-checking and rescheduling on each wake until the reset has actually passed (see Step 3 - the clamp means one call can't skip past a reset more than an hour away)
- `ctx_pct >= 80` -> quick-win only
- `ctx_pct >= 60` -> caution mode

The full scripts are in `tools/` - copy them to your workspace and adjust the path in settings.json.
