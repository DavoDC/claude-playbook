# Part 9: Hooks

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

Two exits matter, and they are not the "0 vs anything else" binary they look like at first glance:

- **Exit 0**: allow the tool call to proceed
- **Exit code 2**: block the tool call (Claude sees stderr message)
- **Any other non-zero exit code** (including the conventional Unix failure code 1): non-blocking error - the transcript shows a `<hook name> hook error` notice with the first line of stderr, but the tool call proceeds anyway

(full reference: https://code.claude.com/docs/en/hooks#exit-code-output)

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

### Choose the Delivery Channel by Audience, Never by Loudness

The exit code decides whether the tool call proceeds. It does not decide who reads what the hook has to say, and those are separate questions that are easy to conflate. A hook has three delivery channels and they have three different audiences:

- **`hookSpecificOutput.additionalContext`** goes to the agent. Use it when the right response is for the model to change what it does next.
- **A top-level `systemMessage`** goes to the human. Use it when the right response is a person deciding something, or when the tooling itself is unhealthy in a way the model cannot fix.
- **Exit 2** stops the work. Use it when nothing should proceed until the condition is resolved.

**Plain stderr is not a fourth channel.** On a hook that exits 0, on most events, stderr goes nowhere a human or the model will ever see. Writing an advisory to stderr and exiting 0 is the most natural-looking way to write a hook and it is a silent no-op.

This produced a whole family of defects in one workspace, found in a single audit: a budget monitor, a compaction counter, and every warning path in two guard scripts, all of them correct, all of them registered, all of them firing on schedule, and all of them writing to stderr and exiting 0. Several had been considered finished for months. Each one logged evidence that it was working, which is why none of them was suspected. A separate one used `exit 1` for a policy it was meant to enforce, which does not block, so it spent its entire life detecting violations correctly and permitting every one of them.

The rule that resolves all of them, stated as a question to ask of any new hook: **who needs to act on this, and does the channel I chose actually reach them?** Not "how important does this feel". Importance is what pushes an author toward stderr and shouting; it is exactly the wrong axis. Routine housekeeping the model should act on is `additionalContext` even though it feels minor. A privacy check that has silently degraded to fail-open is `systemMessage` even though nothing is broken yet, because a person has to know. A suggestion is never exit 2, because a suggestion that blocks is not a suggestion.

One mechanical constraint that bites the moment a hook has more than one thing to say: **emit one JSON object per run, not one per finding.** Several advisory sites can fire in a single invocation, and two concatenated JSON objects are not valid output, so the second silently destroys the first. Queue the messages and emit once at the end, and make a blocking exit suppress the queued advisory output entirely, so a run that blocks never also carries advice on stdout. The same constraint applies at session start: once any structured output is emitted for an event, plain stdout lines cannot coexist with it in the same run, so anything that used to be printed has to move inside the object.

### A Mechanism That Runs and Logs Is Not a Rail

Every one of the defects above passed the checks people actually run. Each was registered in settings. Each executed. Each produced log output proving it had executed. None of them reached anybody.

So the standard for calling an enforcement mechanism finished has two halves, and the usual review only does the first:

1. Something proves it **fires** on the condition it targets.
2. Something proves it **reaches its audience**, and **fails when broken**.

The second half is what turns a mechanism into a rail, and the cheap way to get it is mutation testing: keep a small script that reintroduces each historical defect one at a time and asserts that a specific named test goes red. A fix without an entry there is a claim; a fix with one is a rail. It costs a few lines per defect and it is the only thing that stops a rail quietly rotting back into a mechanism when someone refactors it later.

**Assert the channel and the exit code. Never assert the message wording.** This is not a style preference, it is the specific reason that family of defects survived so long. A test that greps stderr for the word BLOCKED passes against a hook that detects the violation, prints BLOCKED, and exits 1 without blocking anything. The wording was always right. The wording was never the thing that was broken.

Worth stating plainly because it generalises past hooks: the same shape appears anywhere a layer reports a condition and a layer above it decides what to do with the report. It is not a hook-specific bug, and an audit scoped to hooks will not enumerate it.

### Blast Radius Triage: Blocking vs Passive Hooks

Before writing a hook, ask one question: can this hook exit 2 and block a tool call? The answer decides how paranoid to be about its failure modes, because the blast radius of a bug is completely different between the two kinds.

Passive hooks (logging, warnings, context injection) always exit 0. Blocking hooks (guards, validators) exit 2 on a violation, since that is the only code that blocks. A bug in a passive hook makes it go silently inert - it stops doing its job, but every tool call still succeeds. Annoying, but easy to notice and fix. A bug in a blocking hook can lock the whole session - every tool call blocked, including the tools you'd need to fix the hook itself. That second failure mode is the one worth designing against from the start.

### Retiring a Guard, and Reading a Fire Rate

Rules get promoted upward until they reach a hook, and nothing ever comes back down. The count of enforcement mechanisms only rises, each one costs something on every matching call whether or not it ever fires, and there is no retirement path built into the promotion diagram at all - only an on-ramp.

The prerequisite has to come first, because nothing below works without it: log every guard fire, with its verdict, as one appended line written by the guard itself at the moment it fires. That log is the only source for the questions that follow, and none of them are answerable any other way.

Once fires are logged, every guard sorts into one of a small number of cases, and each case has a different action rather than a shared default of "leave it running."

- **Dominant** - a large share of all fires over a meaningful volume. Do not touch the guard itself. Ask what sits upstream of it instead, and pick from: the correct form is harder to produce than the wrong one, so make the correct form the default or the easier path; the guard sits after the decision rather than at it, so move the check earlier; or the rule is genuinely wrong for a class of case that has quietly become most of the traffic. That last option is the one people never consider first, which is exactly why it's worth naming - it means looking at what is being blocked, not only counting how often.
- **Thin tail** - fires occasionally, and blocks a real mistake each time it does. This is healthy and needs no action. Most guards should live here, and it's the shape nobody ever notices, which is precisely what makes it correct.
- **Silent** - registered, never fired across the whole window measured. Two explanations produce an identical zero: the class of mistake it catches is genuinely solved, or the guard has quietly stopped working. Nothing in the count distinguishes them. Before retiring anything silent, deliberately trigger it once and watch it actually block. A guard that is silent because it's broken is the worst object in the system - it still costs something on every matching call, it protects nothing, and everyone reading the codebase treats its presence as proof that protection exists.

A worked example carries the argument. In one measured month of a live guard log, a single guard accounted for over two thirds of every block recorded. The instinct is to read that as the guard doing heavy lifting; it's closer to the opposite. That guard sat at the top of the enforcement ladder - it refused the action outright, and its message was good, naming the correct alternative and citing where the rule was written, delivered at the exact moment the mistake was made. It still fired over a hundred times against the same person, who read the message every time and complied every time.

The conclusion is that a top-of-ladder guard firing constantly is not under-promoted - its enforcement point sits downstream of the decision it's trying to change. The refusal arrives after the command has already been composed, which is too late to touch the habit that composed it. Each firing converts exactly one attempt, and being blocked a hundred times does nothing to make the hundred-and-first attempt less likely, because the block never participates in the moment the shape gets chosen in the first place. That's a different diagnosis than "the rule isn't written clearly enough" - clarity was never the problem - and the fire count is the only route to reaching it, since the transcript of any single blocked attempt looks exactly like success.

There's a fourth case worth adding to the three above, found while writing this section rather than derived from it: **correct but firing on an exempt case**. A guard can be doing exactly what it was built to do and still be wrong in the specific instance, when the rule it enforces carries a semantic exemption the guard has no way to see because the guard itself is lexical. The measured instance: a guard forbidding exact counts in documentation, whose own rule already exempts a count when the count is itself the evidence for a claim, fired on a mutation-testing result where the number of failing cases was the proof being cited. The cost isn't the block - it's that the writer rephrases real evidence into vaguer prose just to get past it, so the guard degrades the very artefact it exists to protect. The fix is neither to weaken the guard nor retire it, but to give it an explicit escape marker the writer can apply on purpose, one that leaves a trace in the text for anyone reviewing later. The general shape: a lexical guard enforcing a semantic rule will always have some exempt-case rate, and if there's no sanctioned way to declare the exemption, the pressure has nowhere to go but into degrading the content.

A fifth case is the mirror of Silent rather than a variant of any of the others, and it is the more common failure for status and health checks specifically, as opposed to write-blocking guards: **reporting unhealthy against a system that is actually fine.** Before shipping any health or status check, write down what it should report against a known-healthy system, then run it against one and confirm the prediction holds. A container-update health check flagged every one of several healthy containers as stale because it checked the container image's `Created` date - a signal that answers "when was this image built," not "did the last update job actually run." The check was internally consistent and completely wrong, and every false alarm it produced trained its reader to expect noise, which is the same trust-destroying end state as a guard that never fires at all, reached from the opposite direction.

Put together as a protocol: log every fire with its verdict, since nothing below this line is answerable without it. Review the fire distribution on a cadence rather than waiting for suspicion, because a dominant guard reads as the system working exactly as intended and nobody thinks to go look. Triage each guard into one of the cases above rather than assuming a shared default. For every silent guard, trigger it once before deciding anything, since a guard that cannot be triggered is already retired in practice and has just not been told. For a dominant guard, change what's upstream and never the guard itself, because weakening a guard for firing too often is exactly backwards. And record the retirement decision somewhere revisitable rather than only in a closed-out log, because a close call left as a completed action never gets reconsidered when circumstances change.

A guard firing on most attempts is a measurement of your setup, not of your users.

### When Two Correct Rules Cannot Both Be Satisfied

A layered rule or guard system can reach a state where two rules, each independently sensible, describe a jointly impossible action - and nothing in the system says so. The only visible symptom is a guard firing repeatedly on what looks like the same user error, because from the guard's own point of view it is correctly enforcing a correct rule every single time. Nobody notices the contradiction until someone traces both rules back to their source and realises there is no action that satisfies both at once.

A concrete shape this takes: one rule requires every entry of a certain kind to be indexed in a specific tracking file, and a second, unrelated rule forbids exactly that kind of entry's identifying name from appearing inside that same file. Each rule is correct on its own; together they describe something no compliant edit can produce.

So when a guard blocks the same category of edit three or more times, check not only "is this rule correct" but "do the rules currently in force admit any satisfying action at all" - and if they do not, fix it by exempting one rule from the other, with a comment naming the conflicting rule, rather than tightening either rule further. This sits next to the fire-rate triage above rather than inside it: a jointly unsatisfiable pair reads exactly like a Dominant guard in the log, and the upstream fix that Dominant calls for is the wrong one here.

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

### Error Handling Protects the Managed Runtime, Not a Crash in Foreign Native Code

A try/except (or the equivalent guard in any managed language) only catches errors raised inside that runtime. A hook, or any script, that shells out to or embeds a call into foreign native code - a compiled binary, a native extension, a system library - can crash the whole process regardless of how carefully the surrounding logic is wrapped. The handler never engages, because the crash never became an exception the runtime could see; it just took the interpreter down with it. This matters for hooks specifically because a hook that wraps its logic in try/except and assumes that alone guarantees graceful failure has only covered the managed half of what it calls - the same fail-open assumption the sections above rely on stops holding the moment the failure happens below the runtime rather than inside it.

The practical fix costs almost nothing: write a flushed log line immediately before any risky call into native code, naming what's about to run. If the process survives, the line is redundant. If it doesn't, that log is the only artifact left to diagnose from - there was never a stack trace, a caught exception, or even a non-zero exit code to read afterward, because the process simply stopped.

Evidence: a scripting-language mod wrapped every call in the language's own error handler, but its first real call into native code crashed the whole process anyway, with the handler never engaging at all.

### Catastrophic Self-Lock: the Quoting Trap in Blocking Hooks

Embedding Python inside `bash -c "..."` works fine until a blocked message needs a double-quote character. A `"` inside the Python string literal closes the outer shell's double-quoted argument early, producing a SyntaxError. For a passive hook that's the silent fail-open trap above - annoying but harmless. For a blocking hook whose fallback is `|| exit 2` (fail closed, which is the correct default for a security guard), that same SyntaxError now blocks every tool call - Read, Edit, Write, Bash, all of them. There is no self-repair path, because the tools needed to fix the hook are exactly the tools the hook is blocking (observed on Claude Code v2.1.220, Windows 11 with Git Bash; no official page covers this session-lock failure mode, so recheck if behaviour changes).

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

### Allowlist Entries Are Literal String Matches

A permission allowlist entry - the `if:` pattern above, or an entry in `settings.local.json`'s `allow` list - matches the exact invocation written, not the intent behind it. Writing the documentation for a command and the allowlist entry for it in the same commit does not guarantee the two describe the same invocation; they were typed by hand, twice, and nothing checks that they agree. Diff the documented invocation directly against the allowlist entry rather than trusting they were written consistently just because they were written together.

The sharper version of this: never pre-authorize the destructive mode of a dual-mode tool as a side effect of an unrelated task. A permission entry loosened to unblock one docs-writing session can end up broader than that session needed, and it carries forward silently into every session after it.

Evidence: a docs update and a permission allowlist entry were written in the same commit but described slightly different invocations of the same tool - the allowlist entry didn't actually cover what the docs said was now possible.

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

## Hooks Never Load From a Sibling Directory

A hook only fires when it's registered in the `.claude/settings.json` of the directory Claude Code was launched from. There is no parent-directory fallback, and adding another directory to the session's awareness does not extend hook execution to it either - only a narrow slice of settings (things like enabled plugins and known marketplaces) is read from an added directory, and hooks aren't in that list. An auto-loaded instructions file follows the same rule from the other direction: Claude walks up from the working directory and lazily loads instruction files it finds in subdirectories as it reads into them, but it never reaches into a sibling directory to load one.

This bites hardest in a multi-repo setup where one directory is always the launch point and everything else sits next to it as a sibling. A hook, or an instructions file, written into a sibling repo to protect that repo never fires unless a session happens to be launched from inside it directly. It's not a loud failure - the file sits there looking correct, runs fine if invoked manually, and simply never executes as part of a normal session. Safety rules written this way read as protection while providing none, which is worse than having no guard at all, because the repo's own files say the guard exists.

The fix is not to duplicate the hook into every sibling repo (see the next section for why that trades a dead guard for something worse) and not to hardcode each sibling's name into the launch directory's hook either, since that just turns a missing guard into a pile of special cases. Split the concern instead: the sibling repo declares what protection it needs in a small tracked marker file, and generic, marker-driven logic in the launch directory's hook discovers and enforces it for any repo that opts in. Protecting one more sibling then costs a marker file, not a code change.

## One Registration Point, Not One Copy Per Repo

Hooks can be registered in two places: a project's own `.claude/settings.json`, which applies to that project only, or the user-level settings file, which applies to every project on the machine. When a hook needs to run across many repos, the user-level file is the single point of control - register it once there, pointing at one canonical copy of the script, and every project picks it up automatically.

The mistake worth naming is copying the hook's script files into each repo instead, reasoning that a self-contained copy is safer or more defensive. It isn't. If the user-level registration already covers every target, the copies do no protective work at all - they are inert duplicates riding along for zero benefit. What they do instead is multiply risk: any personal detail baked into the script (a home directory path, a machine name) now leaks into every repo carrying a copy, including public ones; the copies drift the moment one is edited and the others aren't; and a bug fix has to be applied once per repo instead of once total, with every application a fresh chance to miss one or reintroduce the bug.

If a leak like this is ever found, resist the instinct to just sanitize the copies' contents. Stripping a hardcoded path out of several duplicated files fixes the string while leaving the actual problem - a private script living in several public places - fully intact for the next detail that gets added to it. The right question is why the file exists in each repo at all, not what's wrong with what's inside it. Private or cross-cutting infrastructure belongs in exactly one place: registered once, at the single point of control that already covers everything, pointing at one canonical copy that never ships inside a repo that could go public.

The registration-point argument above is one instance of a more general rule: a generated or deployed file stamped "do not edit" should be edited at its source and redeployed, never hand-edited where it landed. The moment someone edits the deployed copy directly, it silently drifts out of sync with the source that's supposed to produce it, and the next regeneration either overwrites the fix or leaves it coexisting invisibly with content the source no longer matches. The failure runs the other way too: a generator's "managed set" only covers the exact artifacts it explicitly tracks, so an output hand-duplicated outside that set to save a step looks identical to a generated one at the moment it's created, then drifts stale the first time the source changes, because nothing is watching it.

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

This section is about git hooks (`.git/hooks/`, run by git itself on `commit`, `push`, and so on), not Claude Code's own hooks - the two are separate mechanisms that happen to share a name. Claude Code hooks in `.claude/settings.json` can stay as bash: the shell-form command runs through Git Bash on Windows by default, or PowerShell if Git Bash isn't installed (full reference: https://code.claude.com/docs/en/hooks#exec-form-and-shell-form).

Git hooks are a different story. Git Bash hooks work under WSL, but a Windows git client that shells out through `cmd.exe` rather than Git Bash - GitHub Desktop is the common case - will fail silently or block commits entirely if a git hook is written in bash syntax (observed on Windows 11 with GitHub Desktop; this is git-client behaviour, not a Claude Code feature, so no official Claude Code page covers it - recheck if the client's shelling-out behaviour changes). This is a painful lesson that only needs to be learned once.

If you're on Windows: write git hooks (`.git/hooks/`) as `.ps1` or `.bat` scripts. Claude Code hooks (`.claude/settings.json`) can stay bash.

Note: `hooks/pre-commit` and `hooks/commit-msg` in this repo (below) are POSIX `sh`, which is the exception the paragraph above warns about - they are only exercised by commits run through Git Bash, never through a GUI client's own commit flow. If you commit through a Windows GUI client, port them to `.ps1`/`.bat` first.

## Privacy Guard Git Hooks (`hooks/`)

This repo ships two tracked git hooks - `hooks/pre-commit` and `hooks/commit-msg` - that block a commit whose staged content or message references a private sibling repo. `.git/hooks/` is never itself tracked by git, so a fresh clone has neither installed until you run:

```
sh hooks/install.sh
```

Neither hook hardcodes any repo name or path, which is what makes it safe to keep in a public repo. Each derives its blocklist at runtime by globbing the parent of this repo for `.private-root` marker files: any sibling repo opts in by dropping a `.private-root` file at its own root, optionally with a repo-relative subfolder name (e.g. a feedback or notes folder) as its first non-comment line. The hook's token list is the private repo's directory name plus that subfolder's first path component - generated fresh on every commit, from whatever markers exist on the machine it runs on. See `guard.py`'s `.private-root` handling for the same convention used at Claude Code write-time, not just commit-time.

**A privacy guard must report WHERE, never WHAT.** This is the rule that is easiest to get wrong and hardest to notice afterwards, because the wrong version looks more helpful. A hook that finds a private token and then echoes the matching line has printed that token into the terminal, into any CI log that captured the run, and into the transcript of any assistant that was committing on your behalf - which is a wider audience than the commit it just blocked. So the pre-commit hook prints file names and the commit-msg hook prints line numbers, and neither prints the match. A location is enough to act on and costs nothing if it leaks.

The general form is worth stating on its own, because it applies to any check over sensitive data rather than to git hooks specifically: **a rule that names the thing it protects instantiates the leak it exists to prevent.** The public copy of a privacy rule says "no private repo names"; the private copy is where the actual names live. The same split applies to the guard's own output.

That failure is not hypothetical, and it survived a review. These two hooks were written in the same sitting, from the same template, with the pre-commit one carrying a comment explaining exactly why it withholds the match - and the commit-msg one printing `grep -n` output directly underneath. Sharing a rationale in a comment does not propagate it to the sibling file, and a reviewer who has just read the good version is the least likely person to notice the bad one. **When one of a pair implements a safety rule, check the other for the same rule specifically, by name, rather than reading it for general correctness.**

### This section is also a live installation

Both hooks are installed and active in this repo, not merely documented in it. That is deliberate and it is worth copying: a repo that publishes advice is the cheapest possible test bed for it, and it is the only one where drift between the advice and the practice is visible for free. The commit-msg leak above was found precisely because the hook was a live thing to inspect rather than a snippet in a code fence - a snippet nobody runs is never wrong, which is exactly the problem with it.

The discipline this asks for is small. When you document a practice here, ask whether this repo could adopt it, and if it can, adopt it in the same change. When it genuinely cannot - because the practice needs a private workspace, a paid service, or a codebase this one does not have - say so in the text, so a reader can tell the difference between advice under test and advice merely written down. An unmarked claim reads as tested, and most of the value of a playbook that eats its own cooking is lost the moment a reader cannot tell which parts are being eaten.

---

## Before Renaming Any Tracked File

A rename that updates every path reference correctly can still silently delete an enforcement mechanism.

A file's name may be referenced by more than paths. A privacy blocklist, a lint rule, a commit-message scanner or a hook matcher can key on the **bare name as a string**. Rename the file, update every path, and nothing breaks visibly, because nothing was pointing at the path. The guard is simply gone, and it will stay gone because its absence produces no error.

**Before renaming anything tracked, grep for the bare name as a string, not only as a path.** If it appears inside a matcher rather than a path, do not rename it. Split the file by concern instead, leaving the original name attached to whatever the matcher is protecting.

The tempting move in that situation is the worst one: renaming to a clearer, more generic name usually makes the guard unrecoverable, because a generic name cannot be blocklisted without false positives.
