# Part 8: Hooks

> **Field note.** Written from practice rather than machine-checked, and not covered by `tools/selftest.sh`. Last reviewed 2026-08-02 against Claude Code v2.1.220. Opinionated, and it may lag the harness.

Hooks are shell scripts that run automatically on Claude Code events. They enforce rules at the system level rather than relying on Claude remembering them from CLAUDE.md. This part covers events, exit codes, configuration and registration; how hooks fail silently and how to retire a guard is in [Part 10](10-hook-failure-modes.md), and ready-made hooks are in [Part 9](09-hooks-recipes.md).

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

Not the "0 vs anything else" binary it looks like:

- **Exit 0**: allow the tool call to proceed
- **Exit code 2**: block the tool call (Claude sees stderr message)
- **Any other non-zero exit code** (including the conventional Unix failure code 1): non-blocking error - the transcript shows a `<hook name> hook error` notice with the first line of stderr, but the tool call proceeds anyway

(full reference: https://code.claude.com/docs/en/hooks#exit-code-output)

A hook enforcing a policy must exit 2; anything else, including a crash that happens to exit 1, is silently non-blocking, so a hook that crashes before its intended `exit 2` fails open. The pattern below makes that deliberate instead of accidental:

```bash
#!/bin/bash
# Wrap the main logic - exit 0 on any internal error
PY=$(command -v python || command -v python3)
$PY -c "
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

### Choose the Delivery Channel by Audience, Never by Loudness

The exit code decides whether the tool call proceeds, not who reads what the hook says. A hook has three delivery channels with three audiences:

- **`hookSpecificOutput.additionalContext`** goes to the agent. Use it when the right response is for the model to change what it does next.
- **A top-level `systemMessage`** goes to the human. Use it when the right response is a person deciding something, or when the tooling itself is unhealthy in a way the model cannot fix.
- **Exit 2** stops the work. Use it when nothing should proceed until the condition is resolved.

**Plain stderr is not a fourth channel.** On a hook that exits 0, on most events, stderr reaches neither human nor model. Writing an advisory to stderr and exiting 0 is the most natural-looking hook and a silent no-op.

One audit found a family of such defects: a budget monitor, a compaction counter, and every warning path in two guard scripts, all correct, registered and firing on schedule, all writing to stderr and exiting 0. Several had been considered finished for months, and each logged evidence it was working, so none was suspected. Another used `exit 1` for a policy it was meant to enforce, so it detected every violation and permitted all of them.

The question for any new hook: **who needs to act on this, and does the channel I chose actually reach them?** Not "how important does this feel" - importance pushes authors toward stderr and shouting. Routine housekeeping the model should act on is `additionalContext` even if minor. A privacy check silently degraded to fail-open is `systemMessage` even though nothing is broken yet, because a person has to know. A suggestion is never exit 2.

One mechanical constraint: **emit one JSON object per run, not one per finding.** Two concatenated JSON objects are invalid output, so the second silently destroys the first. Queue messages and emit once at the end, and make a blocking exit suppress queued advisory output so a blocking run never also carries advice on stdout. Likewise at session start: once any structured output is emitted for an event, plain stdout lines cannot coexist with it, so anything previously printed must move inside the object.

### A Mechanism That Runs and Logs Is Not a Rail

Every defect above passed the checks people actually run: registered in settings, executed, logged proof it had executed. None reached anybody. Calling an enforcement mechanism finished has two halves, and the usual review does only the first:

1. Something proves it **fires** on the condition it targets.
2. Something proves it **reaches its audience**, and **fails when broken**.

The second half turns a mechanism into a rail, cheaply via mutation testing: a small script that reintroduces each historical defect one at a time and asserts a specific named test goes red. A fix without an entry there is a claim; with one, a rail, and it stops a rail rotting back into a mechanism on refactor.

**Assert the channel and the exit code. Never assert the message wording.** A test grepping stderr for BLOCKED passes against a hook that detects the violation, prints BLOCKED, and exits 1 without blocking: the wording was always right and never the thing that was broken. The same shape appears wherever one layer reports a condition and a layer above decides what to do with it, so an audit scoped to hooks will not enumerate it.

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

### Allowlist Entries Are Literal String Matches

A permission allowlist entry - the `if:` pattern above, or an entry in `settings.local.json`'s `allow` list - matches the exact invocation written, not the intent. A command's documentation and its allowlist entry were typed by hand twice and nothing checks they agree (in one commit they described slightly different invocations of the same tool, and the entry didn't cover what the docs said was now possible). Diff the documented invocation against the allowlist entry.

Sharper: never pre-authorize the destructive mode of a dual-mode tool as a side effect of an unrelated task. A permission loosened to unblock one docs-writing session can end up broader than needed and carries silently into every later session.

---

## The Append-Only Log Pattern

Several hooks in `docs/09-hooks-recipes.md` write to log files; the pattern applies to anything you want to audit over time.

**The pattern:** append-only text files, committed to git, one file per concern.

- `skill-usage.log` - one line per skill invocation
- `bash-audit.log` - every bash command Claude runs (with credential redaction)
- `session-timestamps.log` - session start/end + periodic checkpoints

One line appended per event; no truncation, no rotation (or slow rotation after 30 days to an archive file). **Commit them to git instead of ignoring them:** each commit's diff then shows exactly what happened in that session, green lines only (`git diff HEAD~1..HEAD -- skill-usage.log` lists every skill used), and over time the log separates skills that earn their place from ones that merely sounded useful.

**Auto-committing leftover dirty logs:** a `SessionStart` hook running `git add logs/ && git commit -m "log: session update"` catches logs left dirty when the previous session crashed before `/end-session`.

**Analysis tools:** simple scripts can generate monthly summaries, burn-rate graphs and skill usage rankings for the Question/Delete pass; the data is worthless if you never look.

Blocking guards belong in this pattern too; the prerequisite is stated under [Retiring a Guard, and Reading a Fire Rate](10-hook-failure-modes.md#retiring-a-guard-and-reading-a-fire-rate).

---

## Hooks Never Load From a Sibling Directory

A hook only fires when registered in the `.claude/settings.json` of the directory Claude Code was launched from. There is no parent-directory fallback, and adding a directory to the session's awareness does not extend hook execution to it; only a narrow slice of settings (enabled plugins, known marketplaces) is read from an added directory. An auto-loaded instructions file follows the same rule: Claude walks up from the working directory and lazily loads instruction files in subdirectories as it reads into them, but never reaches into a sibling directory.

This bites hardest in a multi-repo setup where one directory is the launch point and the others are siblings. A hook or instructions file written into a sibling repo to protect it never fires unless a session is launched from inside it. The failure is quiet: the file looks correct, runs if invoked manually, and never executes in a normal session, which is worse than no guard because the repo's own files say the guard exists.

Don't duplicate the hook into every sibling (next section) or hardcode each sibling's name into the launch directory's hook. Split the concern: the sibling declares the protection it needs in a small tracked marker file, and generic marker-driven logic in the launch directory's hook enforces it for any repo that opts in. Protecting one more sibling costs a marker file, not a code change.

## One Registration Point, Not One Copy Per Repo

Hooks register in a project's own `.claude/settings.json` (that project only) or the user-level settings file (every project on the machine). To run a hook across many repos, register it once at user level, pointing at one canonical copy of the script.

Copying the script into each repo as "safer" is a mistake: if user-level registration already covers every target, the copies do no protective work and multiply risk. Any personal detail in the script (a home directory path, a machine name) leaks into every repo carrying a copy, including public ones; the copies drift once one is edited; and a bug fix must be applied once per repo.

If such a leak is found, don't just sanitize the copies: stripping a hardcoded path fixes the string and leaves a private script living in several public places, intact for the next detail. Private or cross-cutting infrastructure belongs in one place, registered once at the single point of control, pointing at one canonical copy that never ships inside a repo that could go public.

A general rule follows: a generated or deployed file stamped "do not edit" is edited at its source and redeployed, never where it landed, or the next regeneration overwrites the fix or coexists with content the source no longer matches. Conversely, a generator's "managed set" covers only the artifacts it explicitly tracks, so an output hand-duplicated outside it looks generated at creation, then drifts stale because nothing watches it.

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

This section is about git hooks (`.git/hooks/`, run by git itself on `commit`, `push`, etc.), not Claude Code's own hooks; the two share only a name. Claude Code hooks in `.claude/settings.json` can stay bash: the shell-form command runs through Git Bash on Windows by default, or PowerShell if Git Bash isn't installed (full reference: https://code.claude.com/docs/en/hooks#exec-form-and-shell-form).

Git hooks differ. They work under WSL, but a Windows git client that shells out through `cmd.exe` rather than Git Bash - GitHub Desktop is the common case - will fail silently or block commits entirely on a bash-syntax git hook (observed on Windows 11 with GitHub Desktop; this is git-client behaviour, not a Claude Code feature, so no official Claude Code page covers it - recheck if the client's shelling-out behaviour changes). A painful lesson needed only once.

On Windows: write git hooks (`.git/hooks/`) as `.ps1` or `.bat` scripts. Claude Code hooks (`.claude/settings.json`) can stay bash.

This repo's tracked `pre-commit` and `commit-msg` privacy hooks (git hooks, not Claude Code hooks; see [Part 12](12-privacy-hooks-public-repo.md)) are POSIX `sh`, the exception warned about above: they only run for commits through Git Bash, never a GUI client's own commit flow. If you commit through a Windows GUI client, port them to `.ps1`/`.bat` first.
