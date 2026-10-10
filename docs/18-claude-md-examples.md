# Part 18: CLAUDE.md Worked Examples

> **Field note.** Written from practice rather than machine-checked, and not covered by `tools/selftest.sh`. Last reviewed 2026-08-02 against Claude Code v2.1.220. Opinionated, and it may lag the harness.

Three examples of what a project CLAUDE.md note changes in practice. The sections they illustrate are in [Part 1](01-claude-md.md).

## Preventing Silent Architecture Violations

Without a platform gotcha in CLAUDE.md, this happens:
1. Claude creates a new C# class file
2. Build fails with a cryptic CS0103 error
3. Claude spends 20 minutes debugging what looks like a code problem
4. Eventually discovers it was a project file registration issue

With the note:
```
CRITICAL: Legacy csproj format - manual file registration required.
New .cs files are NOT auto-included in the build.
Every new file must be manually added to the .csproj.
If you forget: Build fails with CS0103.
```

Claude registers the file immediately after creating it, and the problem doesn't occur.

The lesson: platform gotchas that are non-obvious, codebase-specific and have cryptic failure modes belong in the project CLAUDE.md. If a problem took 20 minutes to diagnose once, it should never take 20 minutes again.

## Communicating the Real Purpose

A streaming automation tool: the project CLAUDE.md says the user wants "psychological reassurance while gaming" - a glance at a second monitor shows everything is handled. That one sentence stops Claude suggesting UI-complexity features, because the design goal is at-a-glance simplicity, not information density. Without it, Claude suggests a detailed activity log on the status display.

## Data Safety Constraint That Actually Holds

For a tool touching real files, the CLAUDE.md states: "Only the user executes integration. Claude implements features and prepares workflows, but stops before running any integration. No exceptions, even dry-run."

It is named as an immovable constraint, not a preference. Without that phrasing Claude would offer to "just quickly run a dry-run", which is wrong because even a dry run is the user's decision when irreversible operations are at stake.
