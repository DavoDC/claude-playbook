# Part 10: Hook Failure Modes and Guard Maintenance

> **Field note.** Written from practice rather than machine-checked, and not covered by `tools/selftest.sh`. Last reviewed 2026-08-02 against Claude Code v2.1.220. Opinionated, and it may lag the harness.

How hooks fail without anybody noticing, and how to keep a set of guards honest over time. Events, exit codes and configuration are in [Part 8](08-hooks.md); the hooks worth building are in [Part 9](09-hooks-recipes.md).

## Blast Radius Triage: Blocking vs Passive Hooks

Before writing a hook ask: can this exit 2 and block a tool call? Passive hooks (logging, warnings, context injection) always exit 0; blocking hooks (guards, validators) exit 2 on a violation, the only blocking code. A bug in a passive hook makes it silently inert while every tool call still succeeds: annoying, easy to notice. A bug in a blocking hook can lock the whole session, including the tools needed to fix the hook. Design against that second mode from the start.

## The Silent Fail-Open Trap (SyntaxError)

Worse than a hook crashing loudly is one that appears to run but does nothing. A Python SyntaxError inside a `-c "..."` block makes Python exit 1; the `|| exit 0` wrapper converts that to exit 0 (allow). The hook is registered, fires and looks healthy, but has never run a check.

The most common cause is indentation, an `if` that looks inside a `try` block but isn't:

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

**Prevention:** syntax-check every hook's Python block before committing. One `ast.parse()` call catches the whole class:

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

**BLOCKED messages must go to stderr.** In PostToolUse hooks only stderr is surfaced to Claude; a `print('BLOCKED: ...')` to stdout silently disappears:

```python
# Wrong - goes to stdout, Claude never sees it
print(f'BLOCKED: {reason}')

# Correct - stderr is surfaced
print(f'BLOCKED: {reason}', file=sys.stderr)
sys.exit(2)
```

## Error Handling Protects the Managed Runtime, Not a Crash in Foreign Native Code

A try/except (or equivalent in any managed language) only catches errors raised inside that runtime. A hook that shells out to or embeds foreign native code (a compiled binary, native extension, system library) can crash the whole process however carefully it is wrapped: the crash never became an exception, it took the interpreter down. The fail-open assumption above stops holding when the failure is below the runtime.

The near-free fix: write a flushed log line immediately before any risky native call, naming what is about to run. If the process survives it is redundant; if not, it is the only artifact to diagnose from, since there is no stack trace, exception or non-zero exit code. Evidence: a scripting-language mod wrapped every call in the language's own error handler, but its first real native call crashed the whole process with the handler never engaging.

## Catastrophic Self-Lock: the Quoting Trap in Blocking Hooks

Embedding Python in `bash -c "..."` works until a blocked message needs a double-quote character: the `"` closes the outer shell argument early, producing a SyntaxError. For a passive hook that is the silent fail-open trap. For a blocking hook with fallback `|| exit 2` (fail closed, the correct default for a security guard), the SyntaxError blocks every tool call - Read, Edit, Write, Bash - with no self-repair path, since the tools needed to fix the hook are the ones it blocks (observed on Claude Code v2.1.220, Windows 11 with Git Bash; no official page covers this session-lock failure mode, so recheck if behaviour changes).

Not hypothetical: a stale-content check was added to a write guard, its blocked-message text contained a quote character, and the guard began exiting 2 on every tool use. Nothing worked until the file was edited on disk from outside the session, and the first attempted fix made it worse, swapping double quotes for single quotes and landing on a different SyntaxError.

**The fix: extract the Python to a `.py` file,** which has no shell-quoting constraints. The `.sh` file becomes a thin caller that syntax-checks the script before running it and fails **open**, not closed, specifically when that syntax check itself fails. That is the one place a blocking hook should not block: the alternative is a session that can never repair itself.

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

Apply this to any hook that can exit 2; it is the general answer to the blast-radius question. Passive hooks can stay as `-c "..."` if convenient: their worst case is inert, never locked.

## Two Ways a Guard Gets Walked Around Without Anybody Noticing

Both were live in a guard running for months, found while fixing something unrelated, and leave no trace when exercised because the guard's normal behaviour is to say nothing.

### A sanitiser applied to one check is a bypass for the others

A command guard usually runs many independent checks over one input string. When one check false-positives on data the command carries rather than the command itself, the natural fix is a narrowed copy of the input with the data stripped out. The trap is applying the narrowed value only to the check that motivated it while the others read the raw string: a bypass in one direction, a false positive in the other, and only the false-positive half is ever reported because the bypass is silent by construction. In the real instance the narrowing was written for the dangerous-verb check and every other check kept scanning the raw string.

The narrowing was also wrong: **never narrow by splitting on a delimiter and keeping one side.** Taking the part before the opening marker discards everything after the embedded data, including anything chained on after it. Excise the region between the opening marker and its terminator instead, preserving the invoking line, the terminator and everything after. When the terminator cannot be found, **fail closed**: return the input unchanged so every check sees everything, rather than a truncated string that quietly stops matching. The rule: apply a narrowed input to every check or to none.

### Resolve paths through their targets, not merely to absolute form

A guard deciding by where a path is must resolve links; making the path absolute only normalises the text without following a link to where the path lands. The failure: a scheme marks certain directories to control what may be written where, and a link inside a marked directory pointing at an unmarked one presented an absolute path under the marked directory, inherited its permissions, and allowed exactly the write the guard exists to stop. On common systems creating such a directory link needs no elevated privilege, so it is reachable by accident as well as intent. Use full link resolution in any check that depends on a path's real location: a one-word change, and the difference between a guard and a suggestion.

### Prove both directions, against current code, before you change anything

Verification is a pair of small sets: cases that **must block** (including the specific bypassing case) and cases that **must allow**. Run both against the code as it stands *before* the change, to tell a fix from a coincidence. The must-allow half matters equally, because tightening a guard until it blocks everything is the easy failure that gets reverted wholesale. Use a probe written independently of the change; a test written by the fix's author tends to encode the understanding that produced the defect.

## Retiring a Guard, and Reading a Fire Rate

Rules get promoted upward until they reach a hook and nothing comes back down: enforcement mechanisms only accumulate, each costing something on every matching call whether or not it fires, and the promotion diagram has an on-ramp but no retirement path.

Prerequisite: log every guard fire, with its verdict, as one appended line written by the guard itself, in the same code path as the block and before it exits. A block's reason is visible in that session's transcript but leaves no trail afterwards, and without the log "repeatedly" is unmeasurable. Once fires are logged, each guard sorts into a case with its own action, not a shared default of "leave it running."

- **Dominant** - a large share of all fires over meaningful volume. Do not touch the guard itself; ask what sits upstream. Either the correct form is harder to produce than the wrong one (make it the default or easier path); the guard sits after the decision rather than at it (move the check earlier); or the rule is genuinely wrong for a class of case that has become most of the traffic. People never consider the last first, so look at what is being blocked, not only how often.
- **Thin tail** - fires occasionally, blocking a real mistake each time. Healthy, no action; most guards should live here, and nobody notices them, which is correct.
- **Silent** - registered, never fired across the whole window. Two explanations give an identical zero: the class of mistake is genuinely solved, or the guard has quietly stopped working. Before retiring anything silent, deliberately trigger it once and watch it block. A guard silent because it is broken is the worst object in the system: it costs something on every matching call, protects nothing, and its presence is read as proof protection exists.
- **Correct but firing on an exempt case** - the guard does what it was built to do, but the rule carries a semantic exemption a lexical guard cannot see (a ban on exact counts in documentation, firing where the count is itself the cited evidence). The cost is the writer rephrasing real evidence into vaguer prose to get past it. Neither weaken nor retire the guard; give it an explicit escape marker the writer applies on purpose, leaving a trace for reviewers.
- **Reporting unhealthy against a system that is fine** - mirrors Silent, and is commoner for status and health checks than for write-blocking guards. A check that flags healthy things as stale (testing an image's build date when the question is whether the update job ran) is internally consistent and wrong, and each false alarm trains its reader to expect noise. Before shipping a health check, write down what it should report against a known-healthy system, run it against one, and confirm.

The Dominant case is easy to misread. Suppose a single top-of-ladder guard accounts for most of all blocks. It refuses outright with a good message naming the correct alternative, and still fires again and again against the same person, who complies every time. That is not under-promotion: the enforcement point sits downstream of the decision, so the refusal arrives after the command is composed, too late to touch the habit that composed it, and many blocks do not make the next one less likely. The diagnosis is not "the rule isn't clear enough", and the fire count is the only route to it, since the transcript of any single blocked attempt looks like success.

As a protocol: review the fire distribution on a cadence (a dominant guard reads as the system working, so nobody looks); triage each guard into the cases above; trigger every silent guard once before deciding anything (one that cannot be triggered is already retired in practice); for a dominant guard change what is upstream, never the guard, because weakening a guard for firing too often is backwards; and record the retirement decision somewhere revisitable, since a close call left as a completed action is never reconsidered. A guard firing on most attempts is a measurement of your setup, not of your users.

## When Two Correct Rules Cannot Both Be Satisfied

A layered rule system can reach a state where two independently sensible rules describe a jointly impossible action and nothing says so. The only symptom is a guard firing repeatedly on what looks like the same user error, since from the guard's view it correctly enforces a correct rule every time. Concretely: one rule requires every entry of a certain kind to be indexed in a specific tracking file, and an unrelated second rule forbids that kind of entry's identifying name from appearing inside that same file. Each is correct alone; together no compliant edit exists.

When a guard blocks the same category of edit three or more times, ask not only "is this rule correct" but "do the rules in force admit any satisfying action" - and if not, exempt one rule from the other, with a comment naming the conflicting rule, rather than tightening either. A jointly unsatisfiable pair reads like a Dominant guard in the log, and Dominant's upstream fix is wrong here.
