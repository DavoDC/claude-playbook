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

## Multi-Agent Orchestration

### Three-Model Decision

Claude Code supports three model tiers. Picking the right one per task matters - Opus is roughly 25x the cost of Haiku for the same token count.

| Signal | Model |
|--------|-------|
| Design / architecture / first-principles / open question | Opus |
| Execute a scoped spec / follow a process doc / commit / pattern-copy | Sonnet |
| Same mechanical operation repeated across many files, no judgment | Haiku |
| Mixed: design then execute | Opus for the design turn, fresh Sonnet session to execute |

The mixed case is important. Running Opus for the entire session when only the first 20% requires judgment wastes budget. Run Opus to design the approach, review the output, then start a fresh Sonnet session to execute.

### Four Orchestration Patterns

**Solo Sonnet (default):** One session plans, executes, and commits. Right for most work where items are scoped and judgment calls are few.

**Solo Haiku (mechanical sweeps):** Em-dash removal, frontmatter normalization, format passes across many files. Haiku has 200K context but less judgment - use only for well-defined mechanical work.

**Sonnet orchestrator + Haiku workers:** Sonnet runs the top-level loop, spawns Haiku subagents via `Agent(model="haiku", ...)` for mechanical subtasks. Sonnet sees plan and result summaries; Haiku pays the file-scanning tokens. On a 10-item loop where 8 items are mechanical, this can cut cost 60-70%.

**Opus planner + Sonnet executor (cross-session):** Opus designs the approach. User reviews the plan. Fresh Sonnet session executes it. Keeps judgment costs in one session, execution costs in another.

### Parallel Foreground Tool Calls vs Background Agent

These are not the same thing. A common mistake is reaching for a Background Agent when parallel foreground calls are what you need.

**Parallel foreground tool calls** (one message, multiple tool calls): the harness runs all N calls concurrently, all results land in the same next turn. Full context sharing, immediate aggregation, zero orient overhead.

```python
# Right: parallel reads in one turn
[Read("file_a.md"), Read("file_b.md"), Bash("git log --oneline")]

# Wrong for this case: Background Agent for parallel reads
Agent(run_in_background=True, ...)  # isolated context, 5-15K orient overhead each
```

**Background Agent** is only right when: the task is genuinely independent AND takes more than ~5 minutes wall-clock AND you have other useful work to do while it runs.

Decision rule:
- 2+ independent reads, greps, or research queries -> parallel foreground calls
- Long-running task you can work in parallel with -> Background Agent

### When to Delegate vs Do It Directly

Delegate to subagents when:
- 50+ files to process with the same operation
- Multiple independent tasks that can run in parallel
- Clean-slate isolation is needed (subagent starts with no accumulated context)

Do it directly when:
- Fewer than ~20 files
- Steps are sequential and depend on each other's outputs
- Task requires shared context from earlier in the session

**Orient overhead:** every `Agent()` call costs ~5-15K tokens to initialize the subagent regardless of task size. A 10-file check is cheaper done directly than via subagent.

### Model Parameter Resolution

When spawning subagents, the model resolves in this priority order:

1. `CLAUDE_CODE_SUBAGENT_MODEL` environment variable
2. `model=` parameter in the `Agent()` call
3. Subagent definition's frontmatter
4. Parent conversation's active model (lowest priority - often wrong)

**Always pass `model=` explicitly.** Silently inheriting the parent model means a Haiku-appropriate sweep task runs on Opus and burns 25x the expected tokens.

```python
# Good - explicit model selection
Agent(model="haiku", prompt="normalize frontmatter in these 40 files: ...")

# Bad - inherits parent model (probably Sonnet or Opus)
Agent(prompt="normalize frontmatter in these 40 files: ...")
```

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
