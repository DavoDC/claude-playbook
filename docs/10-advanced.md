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

### The Advisor Pattern: The Premium Tier Decides, the Cheaper Tier Types

This generalizes the three-model table above into a habit worth naming on its own, because it applies to every premium or budget-limited tier you get access to, not just the everyday Opus/Sonnet/Haiku split. The rule: **the expensive model spends its tokens on the decision, not the typing.** Once a plan is locked, the premium-tier session should be writing briefs and reviewing results, not hand-writing implementation code that a cheaper tier could produce just as well from a clear spec.

The failure mode is easy to fall into, because it's seductive in exactly the moment it happens: the premium session already has the full context loaded, and it genuinely feels faster to just do the mechanical part itself rather than delegate it. That instinct is usually wrong on a shared or rate-limited budget - every token the premium tier spends on work a cheaper tier could do is a token unavailable for the judgment call only the premium tier can make, and on a shared weekly or session budget it can also be quietly stolen from a different task's allocation.

**How to apply:** once the plan is made and the hard calls are locked, the premium session writes briefs, not code. Delegate implementation to parallel subagents on the cheaper execution tier, and keep the premium session for the things only it should spend on: architecture calls, reviewing what comes back, and the next decision. Fan out whenever the work is mechanical and the spec is already written - which is exactly what a good plan produces.

### Brief-First Handoffs to a Premium or Rate-Limited Tier

Before handing a task to a model tier with a small or fast-draining budget, do the research and spec-writing on the cheaper, more available tier first. Produce one self-contained brief with everything the expensive tier needs: exact file paths, schemas and formats, repo conventions, explicit scope boundaries (what's in, what's explicitly out), and explicit "you decide this, document your reasoning" delegation for the genuine open judgment calls. The expensive tier should spend its budget building, not re-reading the repo or re-deriving context the cheaper tier already gathered.

A brief with vague or implicit boundaries invites scope creep from a model that's trying to be helpful. State hard boundaries as an explicit banned-ops list, not soft prose - "read-only" should mean "no Write/Edit, no redirects to files, no `mkdir`/`rm`/`git commit`," not just "please don't modify anything." And include a short "definition of done" checklist so both the model and the reviewer can verify completion without re-reading everything.

The inverse rule matters just as much: never write a brief for work that's completable directly in one response. Delegation overhead has to be smaller than the work delegated, or the brief itself becomes the wasted spend.

### De-risking a Costly One-Shot Build With a Cheap Mockup First

Anything visual or subjective - a GUI layout, an art style, a UX flow - is a bad candidate for a single expensive one-shot build, because a text spec underdetermines taste. "Clean, data-dense, professional" can mean a dozen different layouts, and if the premium build doesn't land, there's rarely a cheap way to course-correct after the budget is already spent.

The fix: before handing a GUI-shaped or visually-shaped brief to a large one-shot budget, have the cheaper tier build a static mockup first - fake data, no backend, a single file that opens directly in a browser. Iterate on the mockup with the reviewer until it's approved; this loop is fast and nearly free on the cheaper tier, unlike re-running the expensive build. Once approved, embed the final mockup (or a pointer to it) directly in the brief, with an explicit instruction: implement against this structure, don't redesign the layout. The expensive tier then wires real data into an already-approved shape instead of inventing layout from scratch on a budget that doesn't allow for a second attempt.

### Accepting Delegated Work Back: Read the Artifact, Not the Report

Delegation only saves budget if the orchestrator actually verifies what came back. A subagent's summary is a claim, not evidence, and two failure modes recur often enough to name:

1. **Done-by-proxy.** The agent verifies the thing it *can* measure instead of the thing that was *asked for*, and reports the proxy as success. A real example: an agent building an asset pipeline reported "all tests pass, loading verified, production-ready" - having tested its async loader against tiny placeholder files it generated itself. The tests could never have caught this, because they weren't capable of checking whether a real asset was ever loaded. The deliverable was supposed to be real assets on disk; what shipped was a loader with nothing real to load. One directory listing caught it.
2. **Deleting the hard part and calling it a refactor.** An agent that can't get a difficult piece working sometimes deletes it and commits the deletion under a tidy message like "simplify" or "streamline" or "clean up." The message describes a choice; the reality is a capitulation. Any commit whose message claims simplification while removing the single hardest thing in the diff deserves a closer look before it's trusted.

**How to apply:** before accepting delegated work, check the deliverable directly - list the files that were supposed to be produced, read the actual commits, run the thing. Ask "what would this look like if the agent had faked it?" and check specifically for that. Then bound any send-back to one concrete, verifiable gate rather than an open-ended "make it better" (see the budget-awareness chapter for why open-ended final rounds don't terminate). The verification step is cheap, it's exactly the kind of judgment work the premium tier should be spending its budget on, and skipping it hands the savings from delegating straight back.

### Re-test Inherited Constraints Before Planning Around Them

A capability limit that gets written into a doc as a bare fact becomes an unquestioned ceiling. The dangerous version looks like this: a session observes something not working, forms a plausible guess about why ("my plan tier doesn't support this"), and a later session reads that guess as settled fact and plans around it - sometimes for weeks. Nobody re-tests it, because it's no longer presented as a hypothesis, it's presented as established.

This is dangerous precisely because a false ceiling is invisible and self-reinforcing. It doesn't throw an error; it produces a smaller plan. You never see the thing you didn't attempt, and the more strategically important the constraint, the more subsequent work gets built on top of it unexamined. Worse, the ceiling is usually plausible - "the plan tier doesn't allow it" explains the symptom perfectly, costs nothing to believe, and is unfalsifiable without a test nobody happens to run.

**How to apply:**
- Never write a capability limit as a bare fact. Write it with its evidence and its provenance: what was actually observed, and which model or session reached the conclusion. A judgment made by a smaller or less careful model carries different weight than one made under careful review, and a reader needs to be able to discount it accordingly.
- Re-test inherited constraints before building strategy on them, especially the load-bearing ones. The re-test is nearly always cheaper than the plan that assumes the answer - often a single settings check versus weeks of a degraded workflow.
- Be most suspicious of constraints that conveniently explain a disappointment. A story that closes an investigation rather than opening one deserves the most scrutiny, not the least.

### Build the Observation Harness Before You Iterate

Never iterate on something you cannot observe. Before starting any round of AI-driven iteration on an app, game, or simulation, build the measurement rig first, cheaply, on the cheaper tier - before the expensive session starts.

For functional work (games, sims, anything with internal state), that means separating pure logic from presentation so the logic can run headless, then exposing a small documented control-and-observe API: set or seed state, inject inputs, step the simulation, and return a full state snapshot as structured data. Ship a headless runner plus an autonomous driver that plays real scenarios and reports structured metrics, so balance and correctness get checked with numbers instead of vibes. This isn't just a convenience for cheap follow-up rounds - a premium session handed the same control surface can use it to self-verify its own work mid-build, catching problems (like a difficulty setting that's unwinnable) through telemetry instead of a human noticing after the fact.

For subjective work (art direction, feel, UX), the equivalent is an objective capture rig: a way to produce comparable before/after captures so a taste judgment has something concrete to point at, rather than relying on a description of what changed.

Put the observation harness in the brief as an explicit deliverable for any AI-built game, sim, or app - it pays back on every subsequent round, whether the next round is run by a human or another model.

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
