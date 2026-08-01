# Part 9: Hooks

> Field notes, last reviewed 2026-08-01. Not mechanically asserted - see the README on what this repo guarantees.

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

The recipes - write guard, budget monitor, file size guard, lesson detector, compact counter, session auto-title, PreCompact and SessionStart hooks, feedback folder enforcer, hook registration parity check - moved to `docs/09-hooks-recipes.md` to keep this file about the mechanics rather than a library of scripts.

---

## The Append-Only Log Pattern

Several of the hooks in `docs/09-hooks-recipes.md` write to log files. The design pattern is worth naming because it applies to anything you want to audit over time.

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
