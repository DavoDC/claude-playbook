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
- `PostCompact` - after context compaction completes (good for logging what was compacted)
- `PostToolUseFailure` - when a tool call fails (good for error logging and recovery)
- `FileChanged` - when a watched file changes on disk (`matcher` specifies filenames to watch)
- `CwdChanged` - when working directory changes (useful for reactive environment management)

More events exist (`TeammateIdle`, `InstructionsLoaded`, `WorktreeCreate`, `PermissionRequest`, etc.) - check the official Claude Code hooks reference for the full list.

## Hook Configuration Patterns

### Exit Codes

Two exits matter, and they are not the "0 vs anything else" binary they look like at first glance:

- **Exit 0**: allow the tool call to proceed
- **Exit code 2**: block the tool call (Claude sees stderr message)
- **Any other non-zero exit code** (including the conventional Unix failure code 1): non-blocking error - the transcript shows a `<hook name> hook error` notice with the first line of stderr, but the tool call proceeds anyway

Exit code 1 does not block. If a hook is meant to enforce a policy, it must exit 2 - anything else, including a crash that happens to exit 1, is silently non-blocking. A hook that crashes with an unhandled exception before reaching its intended `exit 2` therefore fails open, not closed, and the workflow proceeds as if the check never ran. The fail-open pattern below makes that failure mode explicit and deliberate instead of accidental:

```bash
#!/bin/bash
# Wrap the main logic - exit 0 on any internal error
python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    # ... main logic ...
    # sys.exit(2) to block with message on stderr
    # sys.exit(0) to allow
except Exception as e:
    print(f'[HOOK] internal error: {e}', file=sys.stderr)
    sys.exit(0)  # fail open - hook crashes must never block the workflow
" || exit 0  # outer bash also catches Python startup failures
```

**Rule:** exit 2 only when you have a specific, intentional reason to block. Every other exit path is exit 0.

### Blast Radius Triage: Blocking vs Passive Hooks

Before writing a hook, ask one question: can this hook exit non-zero and block a tool call? The answer decides how paranoid to be about its failure modes, because the blast radius of a bug is completely different between the two kinds.

Passive hooks (logging, warnings, context injection) always exit 0. Blocking hooks (guards, validators) exit 2 on a violation, since that is the only code that blocks. A bug in a passive hook makes it go silently inert - it stops doing its job, but every tool call still succeeds. Annoying, but easy to notice and fix. A bug in a blocking hook can lock the whole session - every tool call blocked, including the tools you'd need to fix the hook itself. That second failure mode is the one worth designing against from the start.

### The Silent Fail-Open Trap (SyntaxError)

There is a failure mode worse than a hook crashing loudly: a hook that appears to run but does nothing. This is the passive-hook failure mode.

A Python SyntaxError inside a `-c "..."` block causes Python to exit 1. The `|| exit 0` wrapper converts that to exit 0 (allow). The hook is registered, it fires, it appears healthy - but it has never run a single check. This is the silent fail-open trap.

The most common cause is indentation - an `if` statement that looks like it's inside a `try` block but isn't:

```python
# WRONG - SyntaxError: 'if' is outside try (inconsistent indentation)
try:
    config = {...}          # 12-space indent
if key not in config:       # 8-space indent - NOT inside try
    sys.exit(2)
except SystemExit: raise

# CORRECT - everything inside try
try:
    config = {...}
    if key not in config:   # same indent level - inside try
        sys.exit(2)
except SystemExit:
    raise   # MANDATORY: sys.exit(2) raises SystemExit - must re-raise to propagate
except Exception:
    pass    # swallow crashes -> fail open
```

**Prevention:** syntax-check every hook's Python block before committing:

```bash
python3 -c "
import ast
code = open('my-hook.sh').read()
# Extract the Python block and parse it
import re
m = re.search(r\"-c '(.*?)'\", code, re.DOTALL)
if m: ast.parse(m.group(1)); print('SYNTAX OK')
"
```

One `ast.parse()` call catches the entire class of SyntaxError failures.

**BLOCKED messages must go to stderr.** In PostToolUse hooks, stdout output is not surfaced to Claude - only stderr is shown. A `print('BLOCKED: ...')` going to stdout silently disappears:

```python
# Wrong - goes to stdout, Claude never sees it
print(f'BLOCKED: {reason}')

# Correct - stderr is surfaced
print(f'BLOCKED: {reason}', file=sys.stderr)
sys.exit(2)
```

### Catastrophic Self-Lock: the Quoting Trap in Blocking Hooks

Embedding Python inside `bash -c "..."` works fine until a blocked message needs a double-quote character. A `"` inside the Python string literal closes the outer shell's double-quoted argument early, producing a SyntaxError. For a passive hook that's the silent fail-open trap above - annoying but harmless. For a blocking hook whose fallback is `|| exit 2` (fail closed, which is the correct default for a security guard), that same SyntaxError now blocks every tool call - Read, Edit, Write, Bash, all of them. There is no self-repair path, because the tools needed to fix the hook are exactly the tools the hook is blocking.

This is not a hypothetical: a stale-content check was added to a write guard, its blocked-message text happened to contain a quote character, and the guard began exiting 2 on every single tool use. Nothing worked until the file was edited directly on disk from outside the session - and the first attempted fix made it worse, swapping the double quotes for single quotes and landing on a different SyntaxError inside a Python string.

**The fix: extract the Python to a `.py` file.** A `.py` file has zero shell-quoting constraints - any message content, any quote character, any punctuation, is safe. The `.sh` file becomes a thin caller that syntax-checks the script before running it, and - this is the important asymmetry - fails **open**, not closed, specifically when the syntax check itself fails. That's the one place a blocking hook should not block: the alternative is a session that can never repair itself.

```bash
#!/bin/bash
# guard.sh - thin caller, no Python embedded here at all
PY=$(command -v python3 || command -v python) || exit 0
SCRIPT="$(dirname "$0")/guard.py"

# If guard.py itself is broken: fail OPEN with a loud warning so tools keep
# working and the file can be edited to fix it. Every other exit path below
# this check is the hook's real, deliberate blocking logic.
if ! $PY -m py_compile "$SCRIPT" 2>/tmp/guard_pyc_err.txt; then
    echo "WARNING: guard.py syntax error - checks bypassed until fixed:" >&2
    cat /tmp/guard_pyc_err.txt >&2
    exit 0
fi

$PY "$SCRIPT" || exit 2   # only genuine, deliberate blocks reach here
```

Inside `guard.py`, any string content is safe - no shell quoting to reason about at all. Apply this pattern to any hook that can exit 2; it's the general answer to the blast-radius question above. Passive hooks can stay as `-c "..."` if that's more convenient - their worst case is inert, never locked.

### The `if:` Field - Efficient Tool Matching

The `matcher` field matches the tool name only - `"Bash"` matches every Bash call. To narrow further to specific subcommands or file patterns, use the `if:` field on individual hook handlers. `if:` uses permission rule syntax matching against tool name AND arguments together:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "bash /path/to/guard-commit.sh",
            "if": "Bash(git * commit*)"
          }
        ]
      }
    ]
  }
}
```

Examples:
- `"Bash(git * commit*)"` - only on git commit commands (any subcommand, leading `VAR=value` assignments stripped)
- `"Edit(*.ts)"` - only when editing TypeScript files
- `"Write(*/memory/*)"` - only writes inside a memory directory

The `if:` field means an expensive hook (subprocess call, file I/O) costs zero on the 99% of tool calls it doesn't need to see.

**One condition per handler.** There's no `&&` or `||` syntax. For multiple independent conditions, define separate hook handlers. For complex conditions that can't be expressed as a single permission rule, fall back to checking inside the hook script and exiting 0 early.

---

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
        # Change sys.exit(2) to block Claude instead of just warning
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

The key design choice: warn (stderr, exit 0) rather than block (exit 2). Blocking file edits when a limit is exceeded prevents the very trimming that would fix the violation. Warn instead - Claude sees it and trims proactively.

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

**A blind spot worth naming:** blocking hooks (exit 2 + stderr message) are the one hook type this pattern tends to miss entirely. A guard that blocks a write and prints its reason to stderr is visible in that single session's transcript, but if nothing writes the event to a log file, it leaves no trail once the session ends - there's nothing to grep. That matters because of a related rule worth having: a hook that fires repeatedly on the same pattern is a signal, not a mechanism - it means the underlying default behavior is wrong and should be fixed at the source (the instruction, the skill, the process doc that's steering Claude wrong), rather than silently tolerated because the hook keeps catching it every time. Without a log, "repeatedly" is unmeasurable - you're relying on memory of past incidents instead of a search. If a guard hook blocks something, consider having it append one line to a violations log before it exits, right there in the same code path as the block - that closes the loop between "the hook caught something" and "was this the third time this month."

---

## Settings Split - Critical

All hooks go in `.claude/settings.json`. All permissions and MCP server config go in `.claude/settings.local.json`. Hook entries merge across settings files rather than replacing each other, so having different hooks in both files is normal - the real risk is registering the identical hook entry in more than one settings file, which makes it run twice per event. Keep hooks in one canonical file so that duplication can't happen by accident.

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
