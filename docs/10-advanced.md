# Part 10: Advanced Patterns and Worked Examples

## The Commit-Anchored Delta Pattern

Used by both `/reflection` and `/deep-dive`, this pattern applies to any repeating audit workflow.

**The problem:** every time you run a reflection or audit, you could re-read everything. But most of it hasn't changed since last time. Re-reading unchanged files wastes tokens.

**The solution:** store an anchor after each run - a git SHA recording what state the files were in when you last audited them. Next time, `git diff <anchor>..HEAD` gives you exactly what changed. Read only those files.

In practice, an `audit.py` tool manages these anchors. Each scope/lens pair (e.g., `workspace:session-history content`) has its own anchor. Three outcomes when you query the delta:
- No prior anchor: full dive required
- Anchor exists, nothing changed: skip entirely
- Anchor exists, changes found: read only those files

This means `/reflection` stays fast even when session-history.md has grown to thousands of lines - it only reads the new sessions. And two consecutive `/deep-dive` calls on the same scope skip the second one unless something actually changed.

### Building Your Own Audit Tool

The core data structure: a JSON file mapping `scope:lens` -> `{sha, date, findings_path}`. On each audit run:

1. Run `git rev-parse HEAD` to get current SHA
2. If no prior anchor: audit everything, store current SHA
3. If prior anchor exists: `git diff <stored_sha>..HEAD -- <scope_path>` to get changed files
4. Audit only changed files
5. After audit: store new SHA as anchor

The lens (content/staleness/security/etc.) lets you track different types of audit separately for the same scope. A content audit and a staleness audit of the same folder can be at different anchors.

---

## Worked Examples

### Preventing Silent Architecture Violations

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

Claude registers the file immediately after creating it. Problem doesn't occur.

The lesson: platform gotchas that are non-obvious, specific to your codebase, and have cryptic failure modes are exactly the content that belongs in the project CLAUDE.md. If a problem took you 20 minutes to diagnose once, it should never take 20 minutes again.

### Communicating the Real Purpose

A streaming automation tool: the project CLAUDE.md explains the user wants "psychological reassurance while gaming" - the ability to glance at a second monitor and see that everything is handled. This one sentence prevents Claude from ever suggesting a feature that adds UI complexity, because it knows the design goal is at-a-glance simplicity, not information density.

Without this: Claude suggests adding a detailed activity log to the status display. With this: Claude understands that more information on the status display is the wrong direction.

### Data Safety Constraint That Actually Holds

For a tool touching real files, the CLAUDE.md explicitly states: "Only the user executes integration. Claude implements features and prepares workflows, but stops before running any integration. No exceptions, even dry-run."

This is not just a preference - it's named as an immovable constraint. Without this phrasing, Claude would offer to "just quickly run a dry-run to show you what it'll do" - and that offer is wrong because even dry-run execution is the user's decision when irreversible operations are at stake.

### Using /aristotle to Find the Real Problem

During development of a build script, `/aristotle` was run on: "why does the build script hardcode VS paths?"

The deconstruction revealed: the assumption was that Visual Studio installs to a predictable location. The irreducible truth was that MSBuild needs to be found at runtime, not compile time. The Aristotelian Move: replace the hardcoded path with `vswhere` (Microsoft's own tool for locating VS installations). The build script went from fragile to portable in one change - and the same pattern was applied across multiple repos.

This is a typical /aristotle outcome: the stated problem ("hardcoded path") dissolves into a better-framed problem ("runtime discovery"), and the solution that falls out of the reframing is simpler than any fix for the original problem.

---

## The Single Most Valuable Habit

Keep a `memory/feedback/` folder. Every time Claude does something wrong, write one file: `feedback_<topic>.md`. Rule + why + how to apply. Commit it.

After a few months you have a library of non-obvious rules calibrated to your actual failure modes - not generic advice, but the specific mistakes that happen in your work, your repos, your workflow. That library is worth more than any amount of carefully crafted default instructions.

The CLAUDE.md evolves from that library. Rules that fire repeatedly get promoted up the hierarchy until they live somewhere that guarantees they fire every time:

```
feedback_*.md (discovered)
    -> enforced-rules.md (promoted if cross-cutting)
        -> CLAUDE.md (promoted if top-level principle)
            -> skill file (if workflow-specific)
                -> hook (if system-level enforcement needed)
```

Each promotion makes the rule more reliable. A hook cannot be ignored. A CLAUDE.md rule is read every session. A feedback file is only useful if Claude happens to load it.

The game is getting important rules to the top of the hierarchy. Everything else follows from that.
