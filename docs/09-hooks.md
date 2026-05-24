# Part 9: Hooks

Hooks are shell scripts that run automatically on Claude Code events. They enforce rules at the system level rather than relying on Claude remembering them from CLAUDE.md.

## Events Available

- `PreToolUse` - before a tool call (Read, Edit, Write, Bash, etc.)
- `PostToolUse` - after a tool call
- `Stop` - when Claude stops a response
- `UserPromptSubmit` - when the user sends a message (fires before Claude responds - good for per-message guards and workspace health checks)
- `SessionStart` - once when the session begins (good for loading context, running status checks)
- `SessionEnd` - when the session closes (good for cleanup, final logging)
- `PreCompact` - just before context compaction (good for saving state before Claude loses prior context)

## Hooks Worth Having

### Write Guard (PreToolUse on Edit/Write)

Runs before Claude edits or writes a file. Checks for:
- Secrets in content (.env values, API keys, tokens)
- Blocked characters (em/en dashes if you've decided to block them)
- Private paths that should never appear in public repos
- Files that should never be edited (compiled binaries, lock files)

This prevents a whole class of mistakes that CLAUDE.md instructions alone can't prevent. Claude might follow the instruction 99 times and slip on the 100th. A hook is unconditional.

```bash
#!/bin/bash
# guard.sh - PreToolUse hook for Edit/Write
# Read file content from stdin (Claude Code passes it as JSON)
CONTENT=$(cat)

# Check for secrets
if echo "$CONTENT" | grep -qE 'password\s*=\s*["\x27][^"\x27]+["\x27]|api_key\s*=|PRIVATE KEY'; then
    echo "BLOCKED: potential secret in content" >&2
    exit 1
fi

# Check for em/en dashes (U+2014, U+2013)
if echo "$CONTENT" | grep -qP '[\x{2013}\x{2014}]'; then
    echo "BLOCKED: em/en dash found - use regular hyphens only" >&2
    exit 1
fi

exit 0
```

### Context Budget Monitor (PostToolUse)

Checks token usage after tool calls. Warns when approaching 75% context. This prevents the worst case: Claude compacts mid-`/end-session` and loses the session record.

```bash
#!/bin/bash
# budget-check.sh - PostToolUse hook
CTX_PCT=$(python3 -c "
import json, os, tempfile
try:
    f = os.path.join(tempfile.gettempdir(), 'claude-statusline-data.json')
    d = json.load(open(f))
    pct = (d.get('context_window') or {}).get('used_percentage', 0)
    print(int(pct))
except:
    print(0)
")

if [ "$CTX_PCT" -ge 80 ]; then
    echo "WARNING: Context at ${CTX_PCT}% - run /end-session before continuing" >&2
elif [ "$CTX_PCT" -ge 75 ]; then
    echo "NOTICE: Context at ${CTX_PCT}% - approaching compaction threshold" >&2
fi
exit 0
```

### File Size Guard (PostToolUse on Edit/Write)

Enforces line-count limits on configuration files after every edit. This is what makes the "keep CLAUDE.md under 150 lines" advice in Part 1 actually stick - without a hook, Claude will gradually bloat the file and forget it ever happened.

```python
#!/usr/bin/env python3
# size-guard.py - called from a PostToolUse hook on Edit/Write
import sys, json, os

d = json.loads(sys.stdin.buffer.read())
if d.get('tool_name') not in ('Write', 'Edit'):
    sys.exit(0)

fp = d.get('tool_input', {}).get('file_path', '')
bn = os.path.basename(fp)

# Adjust limits to match your targets from CLAUDE.md
limits = {
    'CLAUDE.md': 150,
    'MEMORY.md': 200,
    'enforced-rules.md': 250,
}

if bn in limits and os.path.isfile(fp):
    lines = sum(1 for _ in open(fp))
    if lines > limits[bn]:
        # Warn to stderr (shown in terminal) but don't block
        # Change sys.exit(1) to block Claude instead of just warning
        print(f'WARNING: {bn} is {lines} lines (limit {limits[bn]}). '
              f'Move explanations to feedback files - CLAUDE.md holds rules, not rationale.',
              file=sys.stderr)

sys.exit(0)
```

Wire it up in `.claude/settings.json`:

```json
"PostToolUse": [
  {
    "matcher": "Write|Edit",
    "hooks": [{ "type": "command", "command": "python3 /path/to/size-guard.py" }]
  }
]
```

The key design choice: warn (stderr, exit 0) rather than block (exit 1). Blocking file edits when a limit is exceeded prevents the very trimming that would fix the violation. Warn instead - Claude sees it and trims proactively.

### Lesson Detector (UserPromptSubmit)

Scans each user message for correction, lesson, and confirmation patterns. When a match fires, injects a reminder into Claude's context: "This looks like a correction - should it be saved to memory?"

This is the mechanical implementation of the "#1 Rule" in every CLAUDE.md: every user prompt is a potential lesson. Without this hook, the lesson is only captured if Claude happens to notice the pattern. With the hook, it's never missed.

```bash
#!/bin/bash
# lesson-detector.sh - UserPromptSubmit hook

python3 -c "
import sys, json

d = json.loads(sys.stdin.buffer.read())
msg = d.get('prompt', '').lower()

corrections = ['don\'t do', 'stop doing', 'never do', 'should not', 'wrong approach', 'avoid that']
lessons = ['remember', 'rmb', 'save this', 'always do', 'from now on', 'next time you']
confirmations = ['yes exactly', 'keep doing that', 'good call', 'right call']

kind = None
for p in corrections:
    if p in msg:
        kind = 'correction'; break
if not kind:
    for p in lessons:
        if p in msg:
            kind = 'lesson/save-request'; break
if not kind:
    for p in confirmations:
        if p in msg:
            kind = 'positive-confirmation'; break

if kind:
    print(f'[MEMORY REMINDER] Message contains a {kind} pattern.')
    print('Should this be saved to memory/ as a feedback file?')
" 2>/dev/null
exit 0
```

The confirmation branch matters as much as the correction branch. "Yes exactly, keep doing that" on a non-obvious approach is just as worth saving as a correction.

### Compact Counter (PostToolUse)

Counts tool calls this session and suggests `/compact` at a threshold. Solves the slow-boil problem: Claude doesn't know a session has run 80 tool calls; it just notices responses getting slower.

```bash
#!/bin/bash
# compact-counter.sh - PostToolUse hook

COUNTER_FILE="/tmp/claude-tool-count-$$"
THRESHOLD=75

COUNT=1
[ -f "$COUNTER_FILE" ] && COUNT=$(( $(cat "$COUNTER_FILE") + 1 ))
echo "$COUNT" > "$COUNTER_FILE"

if [ "$COUNT" -eq "$THRESHOLD" ]; then
    echo "[COMPACT SUGGESTION] $COUNT tool calls this session. Consider /compact to free context." >&2
elif [ "$COUNT" -gt "$THRESHOLD" ] && [ $(( (COUNT - THRESHOLD) % 50 )) -eq 0 ]; then
    echo "[COMPACT SUGGESTION] $COUNT tool calls. Session is getting long." >&2
fi
exit 0
```

Counter resets each session (uses `$$` - current process PID - in the temp file path).

### Feedback Folder Enforcer

Blocks `feedback_*.md` files from being written outside the correct folder. Feedback files accumulate fast and if they spread across the repo they become unfindable.

---

## The Append-Only Log Pattern

Several hooks above write to log files. The design pattern is worth naming because it applies to anything you want to audit over time.

**The pattern:** append-only text files, committed to git, one file per concern.

- `skill-usage.log` - one line per skill invocation
- `bash-audit.log` - every bash command Claude runs (with credential redaction)
- `session-timestamps.log` - session start/end + periodic checkpoints

Each log file gets a single line appended per event. No truncation, no rotation (or slow rotation after 30 days to an archive file). The result: each git commit's diff shows exactly what happened in that session - green lines only, easy to audit.

**Why commit them to git instead of ignoring them:**

`git diff HEAD~1..HEAD -- skill-usage.log` shows every skill Claude used this session. After a few months you know which skills you actually use vs which sounded useful when you wrote them. The data is free - you just have to not gitignore it.

**Auto-committing leftover dirty logs:** A `SessionStart` hook that runs `git add logs/ && git commit -m "log: session update"` at startup catches log files left dirty if the previous session crashed before running `/end-session`. Without this, logs accumulate as uncommitted changes indefinitely.

**Analysis tools:** once you have log data, simple Python scripts can generate monthly summaries, burn-rate graphs, skill usage rankings for the Question/Delete pass. These are optional - but the data is worthless if you never look at it.

---

## Settings Split - Critical

All hooks go in `.claude/settings.json`. All permissions and MCP server config go in `.claude/settings.local.json`. Never mix them - splitting hooks across both files causes double-fire where the same hook runs twice per event.

```json
// .claude/settings.json - hooks ONLY
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{ "type": "command", "command": "bash /path/to/guard.sh" }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": ".*",
        "hooks": [{ "type": "command", "command": "bash /path/to/budget-check.sh" }]
      }
    ]
  }
}
```

```json
// .claude/settings.local.json - permissions and MCP ONLY
{
  "permissions": {
    "allow": ["Read(*)", "Bash(git log*)", "Bash(python3 *)"]
  }
}
```

## Critical for Windows

Hooks must be `.bat` or `.ps1` files, not bash scripts. Git Bash hooks work in WSL but Windows git hooks (used by GitHub Desktop) will fail silently or block commits entirely if you use bash syntax. This is a painful lesson that only needs to be learned once.

If you're on Windows: write all hooks as `.ps1` or `.bat` scripts. Keep bash hooks only in `.claude/settings.json` (not in `.git/hooks/`).
