# Hooks Worth Having

> Field notes, last reviewed 2026-08-01. Not mechanically asserted - see the README on what this repo guarantees.

Recipes moved out of `docs/09-hooks.md` to keep that file focused on the mechanics (events, exit codes, the fail-open trap, the quoting trap, the `if:` field). Start there first if you haven't read it yet - this file assumes that context.

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
    exit 2
fi

# Check for em/en dashes (U+2014, U+2013)
if echo "$CONTENT" | grep -qP '[\x{2013}\x{2014}]'; then
    echo "BLOCKED: em/en dash found - use regular hyphens only" >&2
    exit 2
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

### File Size Guard (PreToolUse on Edit/Write)

Enforces line-count limits on configuration files before every edit. This is what makes the "keep CLAUDE.md under 150 lines" advice in Part 1 actually stick - without a hook, Claude will gradually bloat the file and forget it ever happened.

Warn-only and block-only are both wrong on their own. A warn-only guard is easy to ignore repeatedly - the file quietly drifts past its target for weeks because nothing ever actually stops a write. A block-at-any-size guard is too rigid - it can reject the very edit that would legitimately grow the file, at the exact moment there's no room left to finish the thought before trimming. The fix is two thresholds per file: a soft cap that warns and a hard cap that blocks outright. Blocking only works if the hook runs on an event that fires before the write lands - a hard cap wired to an after-the-fact event silently degrades into a second warning while still reading like a block.

That's why this runs as `PreToolUse`, not `PostToolUse`. `PostToolUse` fires after the tool has already executed, so by the time it runs the write has already happened - exit code 2 there only surfaces stderr to Claude, it can't undo the write. `PreToolUse` fires before the write lands, which means the file on disk still holds the OLD content - re-reading it from disk would measure the wrong size. The hook has to compute the PROSPECTIVE size from the tool input instead: for `Write` that's the incoming `content`; for `Edit` it's the current on-disk content with `old_string` replaced by `new_string` (respecting `replace_all`). When the prospective size can't be determined - the file doesn't exist yet, `old_string` doesn't match, the payload is missing a field - the hook warns and allows rather than blocking, because a guard that blocks on its own confusion can lock a session out of the very edit that would fix the file.

```python
#!/usr/bin/env python3
# size-guard.py - called from a PreToolUse hook on Edit/Write
import sys, json, os

# Two thresholds per file: (soft cap, hard cap). Adjust to your CLAUDE.md targets.
limits = {
    'CLAUDE.md': (120, 150),
    'MEMORY.md': (160, 200),
    'enforced-rules.md': (200, 250),
}


def count_lines(text):
    if not text:
        return 0
    return text.count('\n') + (0 if text.endswith('\n') else 1)


def prospective_lines(tool_name, tool_input, fp):
    """Return the line count the file will have AFTER the pending write,
    or None if it can't be determined (unknown size)."""
    if tool_name == 'Write':
        content = tool_input.get('content')
        if content is None:
            return None
        return count_lines(content)

    if tool_name == 'Edit':
        old_string = tool_input.get('old_string')
        new_string = tool_input.get('new_string')
        replace_all = tool_input.get('replace_all', False)
        if old_string is None or new_string is None:
            return None
        if not os.path.isfile(fp):
            return None
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                current = f.read()
        except (OSError, UnicodeDecodeError):
            return None
        if old_string not in current:
            return None
        if replace_all:
            updated = current.replace(old_string, new_string)
        else:
            updated = current.replace(old_string, new_string, 1)
        return count_lines(updated)

    return None


def main():
    try:
        d = json.loads(sys.stdin.buffer.read())
    except Exception as e:
        # Say so rather than exiting quietly: a guard that goes inert must not
        # look identical to a guard that ran and found nothing wrong.
        print(f'WARNING: size guard could not parse its input ({e}) - write allowed unchecked.',
              file=sys.stderr)
        sys.exit(0)

    tool_name = d.get('tool_name')
    if tool_name not in ('Write', 'Edit'):
        sys.exit(0)

    tool_input = d.get('tool_input', {}) or {}
    fp = tool_input.get('file_path', '')
    bn = os.path.basename(fp)

    if bn not in limits:
        sys.exit(0)

    soft, hard = limits[bn]

    try:
        lines = prospective_lines(tool_name, tool_input, fp)
    except Exception:
        lines = None

    if lines is None:
        # Can't determine the prospective size - warn and allow rather than
        # blocking. A guard that blocks on its own confusion can lock a
        # session out of the very edit that would fix the file.
        print(f'WARNING: could not determine prospective size of {bn} - allowing write unchecked.',
              file=sys.stderr)
        sys.exit(0)

    if lines > hard:
        print(f'BLOCKED: this write would make {bn} {lines} lines (hard cap {hard}). '
              f'Move explanations to feedback files before writing more - CLAUDE.md holds rules, not rationale.',
              file=sys.stderr)
        sys.exit(2)

    if lines > soft:
        print(f'WARNING: this write would make {bn} {lines} lines (soft cap {soft}, hard cap {hard}). '
              f'Trim proactively before the hard cap blocks the next write.',
              file=sys.stderr)

    sys.exit(0)


if __name__ == '__main__':
    main()
```

Wire it up in `.claude/settings.json`:

```json
"PreToolUse": [
  {
    "matcher": "Write|Edit",
    "hooks": [{ "type": "command", "command": "python3 /path/to/size-guard.py" }]
  }
]
```

The soft cap gives Claude a chance to trim proactively while there's still room to do it in the same edit. The hard cap is the backstop a warning alone can't provide - because it runs on `PreToolUse`, `exit 2` actually stops the write before it lands, instead of just leaving a note after the fact. A warning that fires every time and never actually stops anything eventually gets ignored like any other repeated notice that has no teeth.

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

### Session Auto-Title (UserPromptSubmit)

Names each session automatically from the first prompt. Without this, every session in the session list is titled "New Session" and you can't navigate your history.

```python
#!/usr/bin/env python3
"""UserPromptSubmit hook: auto-name session from first prompt."""
import json, sys

SKILL_NAMES = {
    'end-session': 'EOD', 'reflection': 'Reflection',
    'deep-dive': 'Deep Dive', 'dev-session': 'Dev Session',
    'loop': 'Loop', 'checkpoint': 'Checkpoint',
}

try:
    d = json.load(sys.stdin)
    prompt = d.get('prompt', '').strip()
    if not prompt:
        sys.exit(0)

    if prompt.startswith('/'):
        skill = prompt[1:].split()[0]
        title = SKILL_NAMES.get(skill, skill.replace('-', ' ').title()[:25])
    else:
        title = ' '.join(prompt.split()[:5])[:40]

    print(json.dumps({
        'hookSpecificOutput': {
            'hookEventName': 'UserPromptSubmit',
            'sessionTitle': title,
        }
    }))
except Exception:
    sys.exit(0)  # fail open
```

Register under `UserPromptSubmit`. Claude Code uses the `sessionTitle` value on the first prompt only - subsequent prompts don't rename the session. Add your own skill names to the mapping table.

### PreCompact Hook - Save State Before Context Loss

Fires just before context compaction begins. Without this, any state Claude has accumulated (learnings, notes, memory files) that hasn't been committed to disk yet is at risk.

Two things worth doing in the PreCompact hook:

1. **Commit dirty tracked files** - log files and daily notes that are append-only are often dirty when compaction hits
2. **Drain internal Claude memory** - Claude Code stores auto-saved memory in `~/.claude/projects/<hash>/memory/`. If your workspace runs in a container or ephemeral environment, these files need rescuing before the context resets.

```bash
#!/bin/bash
# PreCompact hook: commit dirty files before compaction

WORKSPACE_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
TS=$(date +%H:%M)

# Commit dirty log files (fail open - non-critical)
cd "$WORKSPACE_ROOT" || exit 0
git add -- memory/logs/ 2>/dev/null || true
if ! git diff --cached --quiet 2>/dev/null; then
    git commit -m "log: auto-commit before context compaction at $TS" \
        -- memory/logs/ >/dev/null 2>&1 || true
fi
exit 0
```

Pair with a `PostCompact` hook that logs the compaction event (timestamp + why it triggered) to your audit log.

### SessionStart Hook - Inject Live Context

Fires once when a session begins. Output goes directly to Claude's context window before the first prompt. Use it to inject live workspace state so Claude never starts cold.

```bash
#!/bin/bash
# SessionStart hook: inject live workspace state

WORKSPACE_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "")

echo "=== Session Context ==="
echo "Date: $(date '+%A %d %B %Y, %H:%M %Z')"

if [ -n "$WORKSPACE_ROOT" ]; then
    BRANCH=$(git -C "$WORKSPACE_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
    AHEAD=$(git -C "$WORKSPACE_ROOT" rev-list --count "@{upstream}..HEAD" 2>/dev/null || echo "?")
    DIRTY=$(git -C "$WORKSPACE_ROOT" status --short 2>/dev/null | wc -l | tr -d ' ')
    echo "Git: branch=$BRANCH | $AHEAD commits unpushed | $DIRTY dirty files"
fi

# Also auto-commit dirty log files left over from last session
if [ -n "$WORKSPACE_ROOT" ]; then
    git -C "$WORKSPACE_ROOT" add -- memory/logs/ 2>/dev/null || true
    if ! git -C "$WORKSPACE_ROOT" diff --cached --quiet 2>/dev/null; then
        git -C "$WORKSPACE_ROOT" commit -m "log: session update" \
            -- memory/logs/ >/dev/null 2>&1 || true
    fi
fi

echo "=== End Context ==="
```

The minimal useful set: today's date (stops date-guessing errors), current git branch (stops wrong-branch commits), dirty file count (surfaces uncommitted state). Add/remove based on what's genuinely useful for your workflow.

### Feedback Folder Enforcer

Blocks `feedback_*.md` files from being written outside the correct folder. Feedback files accumulate fast and if they spread across the repo they become unfindable.

### Hook Registration Parity Check (SessionStart)

A hook file existing on disk proves nothing about whether it runs. It's entirely possible for a guard hook to be written, tested, actively reviewed in most commits that touch it - and never wired into `settings.json`. It sits there looking correct, doing nothing, for a long time, until someone eventually notices that the exact pattern it was supposed to catch has been happening the whole time and the hook never fired once.

The fix is a parity check, not vigilance: at session start, scan every hook file that declares a Claude Code event type in its header comment, and warn if its filename never shows up anywhere in `settings.json`. It's cheap - a directory listing and a grep - and it catches drift the moment a new session begins, rather than the moment someone happens to go looking.

```bash
# in a SessionStart hook, after loading live context
SETTINGS_FILE="$WORKSPACE_ROOT/.claude/settings.json"
for hookfile in "$WORKSPACE_ROOT"/hooks/*.sh; do
    bn=$(basename "$hookfile")
    if head -3 "$hookfile" | grep -qiE 'PreToolUse|PostToolUse|SessionStart|SessionEnd|UserPromptSubmit|PreCompact'; then
        if ! grep -q "$bn" "$SETTINGS_FILE"; then
            echo "WARN: $bn declares a hook event but is NOT registered in settings.json" >&2
        fi
    fi
done
```

This depends on one small convention: every hook file self-declares its event type in a header comment (`# PreToolUse hook`, near the top of the file). Without that, the check has nothing to scan for - a small discipline that pays for the whole thing. Worth running the same check inside your hook test suite too, not only interactively at session start, so registration drift shows up in a non-interactive run as well.
