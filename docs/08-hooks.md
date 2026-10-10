# Part 8: Hooks

> **Field note.** Written from practice rather than machine-checked, and not covered by `tools/selftest.sh`. Last reviewed 2026-08-02 against Claude Code v2.1.220. Opinionated, and it may lag the harness.

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

Not the "0 vs anything else" binary it looks like:

- **Exit 0**: allow the tool call to proceed
- **Exit code 2**: block the tool call (Claude sees stderr message)
- **Any other non-zero exit code** (including the conventional Unix failure code 1): non-blocking error - the transcript shows a `<hook name> hook error` notice with the first line of stderr, but the tool call proceeds anyway

(full reference: https://code.claude.com/docs/en/hooks#exit-code-output)

Exit code 1 does not block. A hook enforcing a policy must exit 2; anything else, including a crash that happens to exit 1, is silently non-blocking. A hook that crashes with an unhandled exception before its intended `exit 2` fails open, and the workflow proceeds as if the check never ran. The fail-open pattern below makes that deliberate instead of accidental:

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

This produced a family of defects found in one audit: a budget monitor, a compaction counter, and every warning path in two guard scripts, all correct, registered and firing on schedule, all writing to stderr and exiting 0. Several had been considered finished for months, and each logged evidence it was working, so none was suspected. Another used `exit 1` for a policy it was meant to enforce, so it detected every violation correctly and permitted all of them.

The question for any new hook: **who needs to act on this, and does the channel I chose actually reach them?** Not "how important does this feel" - importance pushes authors toward stderr and shouting, the wrong axis. Routine housekeeping the model should act on is `additionalContext` even if minor. A privacy check silently degraded to fail-open is `systemMessage` even though nothing is broken yet, because a person has to know. A suggestion is never exit 2, because a suggestion that blocks is not a suggestion.

One mechanical constraint: **emit one JSON object per run, not one per finding.** Two concatenated JSON objects are invalid output, so the second silently destroys the first. Queue messages and emit once at the end, and make a blocking exit suppress queued advisory output so a blocking run never also carries advice on stdout. Likewise at session start: once any structured output is emitted for an event, plain stdout lines cannot coexist with it, so anything previously printed must move inside the object.

### A Mechanism That Runs and Logs Is Not a Rail

Every defect above passed the checks people actually run: registered in settings, executed, logged proof it had executed. None reached anybody.

Calling an enforcement mechanism finished has two halves, and the usual review does only the first:

1. Something proves it **fires** on the condition it targets.
2. Something proves it **reaches its audience**, and **fails when broken**.

The second half turns a mechanism into a rail, cheaply via mutation testing: a small script that reintroduces each historical defect one at a time and asserts a specific named test goes red. A fix without an entry there is a claim; with one, a rail. It costs a few lines per defect and stops a rail rotting back into a mechanism on refactor.

**Assert the channel and the exit code. Never assert the message wording.** This is the specific reason the defects survived: a test grepping stderr for BLOCKED passes against a hook that detects the violation, prints BLOCKED, and exits 1 without blocking. The wording was always right and never the thing that was broken.

This generalises past hooks: the same shape appears wherever one layer reports a condition and a layer above decides what to do with it, and an audit scoped to hooks will not enumerate it.

### Blast Radius Triage: Blocking vs Passive Hooks

Before writing a hook ask: can this exit 2 and block a tool call? That decides how paranoid to be, because the blast radius differs completely.

Passive hooks (logging, warnings, context injection) always exit 0. Blocking hooks (guards, validators) exit 2 on a violation, the only blocking code. A bug in a passive hook makes it silently inert while every tool call still succeeds: annoying, easy to notice. A bug in a blocking hook can lock the whole session, including the tools needed to fix the hook. Design against that second mode from the start.

### Retiring a Guard, and Reading a Fire Rate

Rules get promoted upward until they reach a hook and nothing comes back down. Enforcement mechanisms only accumulate, each costing something on every matching call whether or not it fires, and the promotion diagram has an on-ramp but no retirement path.

Prerequisite: log every guard fire, with its verdict, as one appended line written by the guard itself, in the same code path as the block and before it exits. A block's reason is visible in that session's transcript but leaves no trail afterwards unless something writes it down, and without the log "repeatedly" is unmeasurable. That log is the only source for the questions below.

Once fires are logged, each guard sorts into a case with its own action, not a shared default of "leave it running."

- **Dominant** - a large share of all fires over meaningful volume. Do not touch the guard itself; ask what sits upstream. Either the correct form is harder to produce than the wrong one (make it the default or easier path); the guard sits after the decision rather than at it (move the check earlier); or the rule is genuinely wrong for a class of case that has become most of the traffic. People never consider the last first, which is why it is worth naming: look at what is being blocked, not only how often.
- **Thin tail** - fires occasionally, blocking a real mistake each time. Healthy, no action. Most guards should live here, and nobody notices them, which is what makes it correct.
- **Silent** - registered, never fired across the whole window. Two explanations give an identical zero: the class of mistake is genuinely solved, or the guard has quietly stopped working, and the count cannot tell them apart. Before retiring anything silent, deliberately trigger it once and watch it block. A guard silent because it's broken is the worst object in the system: it costs something on every matching call, protects nothing, and its presence is read as proof protection exists.
- **Correct but firing on an exempt case** - the guard does what it was built to do, but the rule carries a semantic exemption a lexical guard cannot see (a ban on exact counts in documentation, firing where the count is itself the cited evidence). The cost is not the block but the writer rephrasing real evidence into vaguer prose to get past it. Neither weaken nor retire the guard; give it an explicit escape marker the writer applies on purpose, leaving a trace for reviewers.
- **Reporting unhealthy against a system that is fine** - mirrors Silent, and is commoner for status and health checks than for write-blocking guards. A check that flags healthy things as stale (testing an image's build date when the question is whether the update job ran) is internally consistent and wrong, and each false alarm trains its reader to expect noise, the same trust-destroying end as a guard that never fires. Before shipping a health check, write down what it should report against a known-healthy system, run it against one, and confirm.

The Dominant case is easy to misread, so here is a worked example. Suppose a single top-of-ladder guard accounts for most of all blocks. It refuses outright with a good message naming the correct alternative, and still fires again and again against the same person, who complies every time. That is not under-promotion: the guard's enforcement point sits downstream of the decision, so the refusal arrives after the command is composed, too late to touch the habit that composed it, and many blocks do not make the next one less likely. The diagnosis is not "the rule isn't clear enough", and the fire count is the only route to it, since the transcript of any single blocked attempt looks like success.

As a protocol: log every fire with its verdict. Review the fire distribution on a cadence, since a dominant guard reads as the system working and nobody thinks to look. Triage each guard into the cases above. Trigger every silent guard once before deciding anything; one that cannot be triggered is already retired in practice. For a dominant guard change what's upstream, never the guard, because weakening a guard for firing too often is backwards. And record the retirement decision somewhere revisitable, since a close call left as a completed action is never reconsidered.

A guard firing on most attempts is a measurement of your setup, not of your users.

### When Two Correct Rules Cannot Both Be Satisfied

A layered rule system can reach a state where two independently sensible rules describe a jointly impossible action and nothing says so. The only symptom is a guard firing repeatedly on what looks like the same user error, since from the guard's view it correctly enforces a correct rule every time. Nobody notices until someone traces both rules to their source and sees no action satisfies both.

Concretely: one rule requires every entry of a certain kind to be indexed in a specific tracking file, and an unrelated second rule forbids that kind of entry's identifying name from appearing inside that same file. Each is correct alone; together no compliant edit exists.

When a guard blocks the same category of edit three or more times, ask not only "is this rule correct" but "do the rules in force admit any satisfying action" - and if not, exempt one rule from the other, with a comment naming the conflicting rule, rather than tightening either. This sits beside fire-rate triage: a jointly unsatisfiable pair reads like a Dominant guard in the log, and Dominant's upstream fix is wrong here.

### The Silent Fail-Open Trap (SyntaxError)

Worse than a hook crashing loudly is a hook that appears to run but does nothing.

A Python SyntaxError inside a `-c "..."` block makes Python exit 1; the `|| exit 0` wrapper converts that to exit 0 (allow). The hook is registered, fires and appears healthy, but has never run a single check.

The most common cause is indentation - an `if` that looks inside a `try` block but isn't:

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
PY=$(command -v python || command -v python3)
$PY -c "
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

### Error Handling Protects the Managed Runtime, Not a Crash in Foreign Native Code

A try/except (or equivalent in any managed language) only catches errors raised inside that runtime. A hook that shells out to or embeds a call into foreign native code (a compiled binary, native extension, system library) can crash the whole process however carefully the surrounding logic is wrapped: the crash never became an exception the runtime could see, it took the interpreter down. A hook that assumes try/except guarantees graceful failure has covered only the managed half; the fail-open assumption above stops holding when the failure is below the runtime.

The near-free fix: write a flushed log line immediately before any risky native call, naming what's about to run. If the process survives, it is redundant; if not, it is the only artifact to diagnose from, since there was no stack trace, exception or non-zero exit code.

Evidence: a scripting-language mod wrapped every call in the language's own error handler, but its first real native call crashed the whole process with the handler never engaging.

### Catastrophic Self-Lock: the Quoting Trap in Blocking Hooks

Embedding Python in `bash -c "..."` works until a blocked message needs a double-quote character: a `"` in the Python string closes the outer shell argument early, producing a SyntaxError. For a passive hook that is the silent fail-open trap. For a blocking hook with fallback `|| exit 2` (fail closed, the correct default for a security guard), the SyntaxError blocks every tool call - Read, Edit, Write, Bash - with no self-repair path, since the tools needed to fix the hook are the ones it blocks (observed on Claude Code v2.1.220, Windows 11 with Git Bash; no official page covers this session-lock failure mode, so recheck if behaviour changes).

Not hypothetical: a stale-content check was added to a write guard, its blocked-message text contained a quote character, and the guard began exiting 2 on every tool use. Nothing worked until the file was edited on disk from outside the session, and the first attempted fix made it worse, swapping double quotes for single quotes and landing on a different SyntaxError.

**The fix: extract the Python to a `.py` file.** A `.py` file has no shell-quoting constraints. The `.sh` file becomes a thin caller that syntax-checks the script before running it and - the important asymmetry - fails **open**, not closed, specifically when the syntax check itself fails. That is the one place a blocking hook should not block: the alternative is a session that can never repair itself.

```bash
#!/bin/bash
# guard.sh - thin caller, no Python embedded here at all
PY=$(command -v python || command -v python3) || exit 0
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

### Allowlist Entries Are Literal String Matches

A permission allowlist entry - the `if:` pattern above, or an entry in `settings.local.json`'s `allow` list - matches the exact invocation written, not the intent. A command's documentation and its allowlist entry, even written in the same commit, were typed by hand twice and nothing checks they agree. Diff the documented invocation against the allowlist entry.

Sharper: never pre-authorize the destructive mode of a dual-mode tool as a side effect of an unrelated task. A permission loosened to unblock one docs-writing session can end up broader than needed and carries silently into every later session.

Evidence: a docs update and an allowlist entry written in the same commit described slightly different invocations of the same tool; the entry didn't cover what the docs said was now possible.

---

## The Append-Only Log Pattern

Several hooks in `docs/09-hooks-recipes.md` write to log files; the pattern applies to anything you want to audit over time.

**The pattern:** append-only text files, committed to git, one file per concern.

- `skill-usage.log` - one line per skill invocation
- `bash-audit.log` - every bash command Claude runs (with credential redaction)
- `session-timestamps.log` - session start/end + periodic checkpoints

One line appended per event; no truncation, no rotation (or slow rotation after 30 days to an archive file). Each git commit's diff then shows exactly what happened in that session - green lines only, easy to audit.

**Why commit them to git instead of ignoring them:** `git diff HEAD~1..HEAD -- skill-usage.log` shows every skill Claude used this session, and over time the log separates skills that earn their place from ones that merely sounded useful. The data is free if you don't gitignore it.

**Auto-committing leftover dirty logs:** a `SessionStart` hook running `git add logs/ && git commit -m "log: session update"` catches logs left dirty when the previous session crashed before `/end-session`. Otherwise they accumulate uncommitted indefinitely.

**Analysis tools:** simple Python scripts can generate monthly summaries, burn-rate graphs and skill usage rankings for the Question/Delete pass. Optional, but the data is worthless if you never look.

Blocking guards belong in this pattern too; the prerequisite is stated under [Retiring a Guard, and Reading a Fire Rate](#retiring-a-guard-and-reading-a-fire-rate).

---


## Two Ways a Guard Gets Walked Around Without Anybody Noticing

Both were live in a guard running for months, found while fixing something unrelated, and leave no trace when exercised because the guard's normal behaviour is to say nothing.

### A sanitiser applied to one check is a bypass for the others

A command guard usually runs many independent checks over one input string. When one check false-positives on data the command carries rather than the command itself, the natural fix is a narrowed version of the input with the data stripped out.

The trap is applying the narrowed value only to the check that motivated it while other checks read the raw string. That is a bypass in one direction and a false positive in the other, and only the false-positive half is ever reported because the bypass is silent by construction. In the real instance the narrowing was written for the dangerous-verb check and every other check kept scanning the raw string.

The narrowing was also wrong: **never narrow by splitting on a delimiter and keeping one side.** Taking the part before the opening marker discards everything after the embedded data, including anything chained on after it. The correct shape excises the region between the opening marker and its terminator, preserving the invoking line, the terminator and everything after. When the terminator cannot be found, **fail closed**: return the input unchanged so every check sees everything, rather than a truncated string that quietly stops matching.

The rule: apply a narrowed input to every check or to none.

### Resolve paths through their targets, not merely to absolute form

A guard deciding by where a path is must resolve links, not just make the path absolute, which normalises the text without following a link to where the path lands.

The failure: a scheme marks certain directories to control what may be written where. A link inside a marked directory pointing at an unmarked one presented an absolute path under the marked directory, inherited its permissions, and allowed exactly the write the guard exists to stop. On common systems creating such a directory link needs no elevated privilege, so it is reachable by accident as well as intent.

Use full link resolution in any check that depends on a path's real location. A one-word change, and the difference between a guard and a suggestion.

### Prove both directions, against current code, before you change anything

Verification is a pair of small sets: cases that **must block** and cases that **must allow**. Run both against the code as it stands *before* the change, to tell a fix from a coincidence, and include the specific bypassing case as a must-block entry. The must-allow half matters equally, because tightening a guard until it blocks everything is the easy failure that gets reverted wholesale.

Use a probe written independently of the change; a test written by the fix's author tends to encode the understanding that produced the defect.

---

## Hooks Never Load From a Sibling Directory

A hook only fires when registered in the `.claude/settings.json` of the directory Claude Code was launched from. There is no parent-directory fallback, and adding a directory to the session's awareness does not extend hook execution to it; only a narrow slice of settings (enabled plugins, known marketplaces) is read from an added directory. An auto-loaded instructions file follows the same rule: Claude walks up from the working directory and lazily loads instruction files in subdirectories as it reads into them, but never reaches into a sibling directory.

This bites hardest in a multi-repo setup where one directory is the launch point and the others are siblings. A hook or instructions file written into a sibling repo to protect it never fires unless a session is launched from inside it. The failure is quiet: the file looks correct, runs if invoked manually, and never executes in a normal session. Safety rules written this way read as protection while providing none, worse than no guard because the repo's own files say the guard exists.

Don't duplicate the hook into every sibling (see the next section) and don't hardcode each sibling's name into the launch directory's hook, which just makes a pile of special cases. Split the concern: the sibling declares the protection it needs in a small tracked marker file, and generic marker-driven logic in the launch directory's hook discovers and enforces it for any repo that opts in. Protecting one more sibling costs a marker file, not a code change.

## One Registration Point, Not One Copy Per Repo

Hooks register in a project's own `.claude/settings.json` (that project only) or the user-level settings file (every project on the machine). To run a hook across many repos, register it once at user level, pointing at one canonical copy of the script.

Copying the script into each repo as "safer" is a mistake. If user-level registration already covers every target, the copies do no protective work; they multiply risk. Any personal detail in the script (a home directory path, a machine name) leaks into every repo carrying a copy, including public ones; the copies drift once one is edited; and a bug fix must be applied once per repo, each a chance to miss one.

If such a leak is found, don't just sanitize the copies. Stripping a hardcoded path from duplicated files fixes the string and leaves the problem - a private script living in several public places - intact for the next detail. Ask why the file exists in each repo at all. Private or cross-cutting infrastructure belongs in one place: registered once at the single point of control, pointing at one canonical copy that never ships inside a repo that could go public.

This is one instance of a general rule: a generated or deployed file stamped "do not edit" should be edited at its source and redeployed, never hand-edited where it landed. A directly edited deployed copy drifts from its source, and the next regeneration either overwrites the fix or leaves it coexisting with content the source no longer matches. Conversely, a generator's "managed set" covers only the artifacts it explicitly tracks, so an output hand-duplicated outside it looks generated at creation, then drifts stale when the source changes because nothing watches it.

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

Note: `hooks/pre-commit` and `hooks/commit-msg` in this repo (see [Part 11](11-privacy-hooks-public-repo.md)) are POSIX `sh`, the exception warned about above: they only run for commits through Git Bash, never a GUI client's own commit flow. If you commit through a Windows GUI client, port them to `.ps1`/`.bat` first.

## Privacy Guard Git Hooks

This repo ships tracked `pre-commit` and `commit-msg` git hooks, plus a generic scanner, that block a commit carrying private names, paths or personal identifiers; they report where, never what. They are git hooks, not Claude Code hooks, and are covered in [Part 11](11-privacy-hooks-public-repo.md).
