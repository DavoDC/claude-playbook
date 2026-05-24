# Part 5: Budget Awareness

> **This is not built in.**
>
> Claude Code does not expose its rate-limit state to Claude by default. Claude has no awareness of whether it's at 5% or 95% of its 5-hour or 7-day quota. It will happily start a 3-hour overnight loop at 82% of its 5-hour quota and wonder why it gets throttled. The `tools/statusline.py`, `tools/check-budget.sh`, and `tools/session-status.sh` scripts in this repo are custom-built tooling to surface that data and make it actionable. Without this setup, your skills have no budget awareness.

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
MyWorkspace | Sonnet 4.6 (200k) | 5h: 43% (r 1h14m) | 7d: 23% (r 6d8h) | ctx: 43%
Claude v2.1.143 | 10:35AM | Sun 24/05/2026
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
