# Part 9: Hooks Worth Having

> **Field note.** Written from practice rather than machine-checked, and not covered by `tools/selftest.sh`. Last reviewed 2026-08-02 against Claude Code v2.1.220. Opinionated, and it may lag the harness.

Ready-to-adapt hook recipes. They assume the mechanics in [Part 8](08-hooks.md) (events, exit codes, the `if:` field) and the failure modes in [Part 15](15-hook-failure-modes.md) (the fail-open trap, the quoting trap), so read those first.

### Write Guard (PreToolUse on Edit/Write)

Runs before Claude edits or writes a file. Checks for:
- Secrets in content (.env values, API keys, tokens)
- Blocked characters (em/en dashes if you've decided to block them)
- Private paths that should never appear in public repos
- Files that should never be edited (compiled binaries, lock files)

This prevents mistakes CLAUDE.md instructions alone can't: Claude might follow an instruction 99 times and slip on the 100th. A hook is unconditional.

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

Checks token usage after tool calls and warns approaching 75% context, preventing the worst case: compaction mid-`/end-session` losing the session record.

```bash
#!/bin/bash
# budget-check.sh - PostToolUse hook
PY=$(command -v python || command -v python3)
CTX_PCT=$($PY -c "
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

Enforces line-count limits on configuration files before every edit, which makes the "keep CLAUDE.md under 150 lines" advice in Part 1 stick; without a hook Claude gradually bloats the file.

Warn-only and block-only are both wrong alone. A warn-only guard is easy to ignore and the file drifts past target for weeks. A block-at-any-size guard is too rigid: it can reject the very edit that legitimately grows the file when there's no room to finish the thought before trimming. Use two thresholds per file: a soft cap that warns and a hard cap that blocks. Blocking only works on an event that fires before the write lands; a hard cap on an after-the-fact event degrades into a second warning that reads like a block.

So this runs as `PreToolUse`, not `PostToolUse`, which fires after the write has happened (exit code 2 there only surfaces stderr to Claude, it can't undo the write). At `PreToolUse` the file on disk still holds the OLD content, so re-reading it measures the wrong size. The hook must compute the PROSPECTIVE size from the tool input: for `Write` the incoming `content`; for `Edit` the current on-disk content with `old_string` replaced by `new_string` (respecting `replace_all`). When the prospective size can't be determined (file doesn't exist yet, `old_string` doesn't match, a payload field is missing), warn and allow, because a guard that blocks on its own confusion can lock a session out of the very edit that would fix the file.

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
    "hooks": [{ "type": "command", "command": "python /path/to/size-guard.py" }]
  }
]
```

The soft cap lets Claude trim proactively while there's room to do it in the same edit. The hard cap is the backstop a warning can't provide: on `PreToolUse`, `exit 2` stops the write before it lands. A warning that fires every time and stops nothing gets ignored like any repeated notice without teeth.

#### The Missing Escape Hatch: a Reasoned Override

The hard cap has one gap: no way through. With no override, every legitimate exception - a rule needing one more sentence to stop being cryptic, a one-time restructuring commit touching two files - becomes a fight with the tooling. The usual outcome is content degraded until it slips under the cap: a rule trimmed to ambiguity, a safety note shortened until it stops preventing its mistake. The guard "wins" and the content it protects loses.

The fix is an override token the author can put in the file itself, naming a REASON:

```
# SIZE-CAP-OVERRIDE: adding the credential-rotation rule mid-incident,
# will trim on the next pass.
# REASON: cutting it now removes the only guidance stopping the exact
# mistake causing tonight's incident.
```

Have the size guard check for that token before blocking: present and non-empty, allow the write but still print a warning so the override stays in the audit trail; absent, block as before. The point of the REASON is not the string match but that an override justified in writing, on the record inside the file, is self-limiting where a silent bypass is not. "I am overriding this because" is too small a tax for a lazy edit to pay and small enough for a genuine exception.

### Lesson Detector (UserPromptSubmit)

Scans each user message for correction, lesson and confirmation patterns and, on a match, injects a reminder into Claude's context: "This looks like a correction - should it be saved to memory?"

This is the mechanical form of the "#1 Rule" in every CLAUDE.md: every user prompt is a potential lesson. Without the hook a lesson is captured only if Claude notices the pattern.

```bash
#!/bin/bash
# lesson-detector.sh - UserPromptSubmit hook

PY=$(command -v python || command -v python3)
$PY -c "
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

Counts tool calls this session and suggests `/compact` at a threshold. Solves the slow-boil problem: Claude doesn't know a session has run 80 tool calls, only that responses get slower.

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

Names each session from the first prompt. Otherwise every session is titled "New Session" and history is unnavigable.

```python
#!/usr/bin/env python3
"""UserPromptSubmit hook: auto-name session from first prompt."""
import json, sys

SKILL_NAMES = {
    'end-session': 'EOD', 'reflection': 'Reflection',
    'deep-dive': 'Deep Dive',
    'loop': 'Loop',
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

Fires just before context compaction. Without it, accumulated state (learnings, notes, memory files) not yet committed to disk is at risk. Two things worth doing:

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

Fires once at session start; output goes directly into Claude's context before the first prompt. Use it to inject live workspace state so Claude never starts cold.

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

The minimal useful set: today's date (stops date-guessing), current git branch (stops wrong-branch commits), dirty file count (surfaces uncommitted state). Add or remove to suit your workflow.

### Feedback Folder Enforcer

Blocks `feedback_*.md` files written outside the correct folder; they accumulate fast and become unfindable if spread across the repo. Register it as a `PreToolUse` hook on `Write|Edit`. It denies only, and fails open on any parse error.

```bash
#!/bin/bash
# feedback-folder-enforcer.sh - PreToolUse hook on Write|Edit
PY=$(command -v python || command -v python3) || exit 0
$PY -c "
import sys, json
try:
    p = json.load(sys.stdin).get('tool_input', {}).get('file_path', '')
except Exception:
    sys.exit(0)
p = p.replace(chr(92), '/')
name = p.rsplit('/', 1)[-1]
if name.startswith('feedback_') and name.endswith('.md') and '/memory/feedback/' not in p:
    sys.stderr.write('Feedback files belong in memory/feedback/, not here: ' + p + '\n')
    sys.exit(2)
"
```

### Hook Registration Parity Check (SessionStart)

A hook file on disk proves nothing about whether it runs. A guard can be written, tested, reviewed in most commits touching it, and never wired into `settings.json`, looking correct and doing nothing until someone notices the pattern it should catch has been happening the whole time.

The fix is a parity check, not vigilance: at session start, scan every hook file that declares a Claude Code event type in its header comment and warn if its filename appears nowhere in `settings.json`. A directory listing and a grep catch drift when a session begins.

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

This depends on one convention: every hook file self-declares its event type in a header comment near the top (`# PreToolUse hook`); without it the check has nothing to scan. Run the same check in your hook test suite too, so drift shows up in non-interactive runs.

### Destructive Script Takes a Target Parameter

The same discipline applies to any script a hook might call, or that you write to fix something a hook flagged: a script that renames, deletes or otherwise mutates real state should accept a target-path parameter, defaulting to the real target, so the dangerous path can be validated against a decoy before touching production data. Careful writing is not testing; the check that catches a bug before the mutation is a dry run against a copy, not a read-through.

```bash
#!/bin/bash
# repair.sh [target-path]   (defaults to the real target if omitted)
TARGET="${1:-$REAL_TARGET_PATH}"

# Validate first: run this same script with a decoy TARGET (a copy of the
# real file/directory) before trusting it against the real one.
# ...destructive logic operates on "$TARGET" only, never a hardcoded path...
```

Evidence: applied to a repair script touching a live browser cookie database - the parameterized version let the destructive path be validated against a copy before it ever touched the real file.

### Example Hooks You Can Run

Working, neutral versions of the recipes below live in `hooks/examples/`, with `hooks/examples/test_examples.py` running each against sample payloads (a deny case, a pass case, a malformed payload, and a control proving an oversized read is really refused). Copy one, edit its constants, register it in `settings.json` with a timeout.

### Read-Size Guard (PreToolUse on Read)

A whole-file read of a large file costs context for the rest of the session. The guard denies a `Read` with no offset or limit when the file exceeds a byte ceiling, and the stderr message tells Claude to re-read a section or search instead. A read that names an offset or limit always passes, so the escape hatch is built in. See `hooks/examples/read_size_guard.py`.

### Bash Output Cap (PreToolUse on Bash)

Some commands reliably print thousands of lines. Keep a short list of patterns for the ones you actually hit, and deny them unless the command already limits its output with `head`, `tail`, `grep`, `wc` or a redirect to a file. Denying before the run is better than trimming after, because the flood never enters context. See `hooks/examples/bash_output_cap.py`.

### Edit-Without-Agent Tripwire (PostToolUse on Edit|Write)

If the main session keeps editing files itself after a long stretch of mechanical work, it is probably doing work a subagent should do. The tripwire counts edits per session in a small state file and, at a threshold, injects one reminder as `additionalContext`. It never blocks: it observes and nudges once. See `hooks/examples/edit_without_agent_tripwire.py`.

### Stop-Hook Unscheduled-Resume Guard (Stop)

If a budget script prints a `RESUME:` line when usage is high, acting on it is a judgement call a long loop can forget, and the work then idles past the reset. A Stop hook scans the current turn of the transcript for that line and, if no one-shot schedule follows it, blocks the stop with an instruction to schedule one. The payload's `stop_hook_active` flag is honoured first so the hook can never loop. See `hooks/examples/stop_resume_guard.py`.

### Convention-Reminder Injection (PreToolUse on Read|Write|Edit)

Rules that apply to one kind of file are easy to forget until the file is open. A hook matches by file name and returns `permissionDecision: "allow"` plus a one-line `additionalContext` the first time that file is touched in a session, then stays quiet. It is advice at the moment of need, not a gate. See `hooks/examples/convention_reminder.py`.

### Block Raw Edits to the Backlog File (PreToolUse on Edit|Write|Bash)

A backlog edited by hand drifts from its generated sections, and a prose rule against it relies on memory. A PreToolUse hook denies `Edit` and `Write` whose path names `IDEAS.md` or `HISTORY.md`, and `Bash` commands that redirect into them or run `sed -i` on them. The deny message names the replacement command from `templates/BACKLOG-SPEC.md` (`python3 tools/backlog.py add`, `shape`, `close`). Allow one logged escape hatch, such as an environment variable set for a single reorganisation, so a broken parser can never strand the file. It denies only and never approves.

A hook (or any plugin intercepting tool calls) answering "allow" can override a stricter check elsewhere, and a handler that answers without passing control on can stop later hooks running. Keep your interceptors to two jobs: deny, or observe and add context. The convention-reminder above returns "allow" only because it is advisory and sits beside the real guards. If you write interceptors as code, lint them for this rule as part of your test run.

### Absent Is Not Malformed

When a safety check resolves a setting with a default, treat a missing key and a present-but-unexpected value as different cases. Test membership to apply the default; coerce anything present by truthiness, or send it to an explicit "violation" result. The tempting `value if isinstance(value, bool) else DEFAULT` maps a present `1` or `"1"` to the safe default and reports safe while the dangerous flag is set. When you find one such resolver, grep the module for the shape; it repeats.

For hook plumbing the opposite holds: an unparseable hook payload should fail open (exit 0), since a broken guard that blocks everything is worse than none. Fail open on your own errors, fail closed on a present, parsed violation.

### Timeouts and a Health Check

Every hook needs an explicit numeric timeout, because a stuck hook freezes the session. Call an interpreter you know works rather than bare `python3`, which can be a hanging stub (the platform caveat is in [Part 4](04-budget-awareness.md)). Run `hooks/examples/check_hook_health.py` after any settings edit: it fails if a hook lacks a timeout, uses bare `python3`, names a script that does not exist, or if `disableAllHooks` was left on. It also covers the `statusLine` command, reads each shell script a command names and flags a bare `python3` inside it (a hook that is clean on its own line can still hang through the helper it calls), and reports an unparseable settings file as a problem rather than crashing. `python3 hooks/examples/check_hook_health.py --selftest` runs a positive control for every defect, and `tools/selftest.sh` asserts it.
