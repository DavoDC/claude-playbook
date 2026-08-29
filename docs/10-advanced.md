# Part 10: Advanced Patterns and Worked Examples

> **Field note.** Written from practice rather than machine-checked, and not covered by `tools/selftest.sh`. Last reviewed 2026-08-02 against Claude Code v2.1.220. Opinionated, and it may lag the harness.

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

The delta tells you WHICH files to re-read. It does not tell you what to ask of them, and asking the same question of new files is how a fifth audit round confirms what the fourth one said. [Part 12](12-audit-lenses.md) covers the other half: generating the questions before you scan, and recording coverage in a form that makes "have we looked at this" answerable.

## Reading Is Not Running, and the Difference Is Not What You Expect

Reading something is not the same activity as running it, and the gap is bigger than "you might miss things" - a purely reading-based check can produce a confident, quantified, and entirely wrong finding that survives review because the arithmetic checks out. [Part 12](12-audit-lenses.md#operate-the-tool-do-not-read-it) covers this lens in full, including how to validate the instrument itself before trusting anything it reports.

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

### Working Around an API Registration Wall

Some platforms gate API access behind an application registration process that an individual developer can no longer complete - a corporate approval step, a closed waitlist, a category the platform stopped accepting new registrants into. The instinct is to keep probing for a way around the wall as an individual. There often isn't one, and repeating the attempt burns rounds without changing the outcome.

The reframe: an established piece of free, open-source software talking to the same platform almost certainly already holds its own long-standing registration, obtained before the wall went up or through a category still open to software vendors rather than individuals. Switching to that client reaches the same data through ordinary sign-in, using the vendor's registration instead of a personal one you can no longer get. In one case, a personal-account API path was closed off entirely by a registration requirement individuals could no longer obtain; switching to an established open-source client that already held its own registration reached the same data with none of the blocked path involved at all.

The boundary that keeps this legitimate: use the vendor's software as it is meant to be used, and never extract or borrow its client credentials to call the API directly from your own code. The first is walking through a door that is open to you; the second is copying someone else's key.

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

### A Brief Is Output, Not Just Planning

It is tempting to treat writing a brief as a planning activity - something that happens before the "real" output, and is therefore exempt from the checks that apply to real output. That is a mistake. A brief is a document another process will read and act on, sometimes with no human in between, which makes it output in every sense that matters: the same privacy rules, verification standards and scope discipline that govern a direct write apply to it in full.

A brief that embeds an unverified claim, a stale piece of state, or content that should never leave a private context does not become safe by virtue of being "just a handoff document." The subagent reading it has no way to tell a verified fact from an assumption the orchestrator typed in passing, and will act on both with equal confidence. So before sending a brief, apply the same pass you would apply to any other write: is every factual claim in it actually verified, does it carry anything that should not propagate downstream, and is the scope stated precisely enough that the reader cannot reasonably drift outside it. Skipping that pass because "it is only a brief" is how a stale claim or a private detail travels one level further than it would have if the same content had been written directly.

### De-risking a Costly One-Shot Build With a Cheap Mockup First

Anything visual or subjective - a GUI layout, an art style, a UX flow - is a bad candidate for a single expensive one-shot build, because a text spec underdetermines taste. "Clean, data-dense, professional" can mean a dozen different layouts, and if the premium build doesn't land, there's rarely a cheap way to course-correct after the budget is already spent.

The fix: before handing a GUI-shaped or visually-shaped brief to a large one-shot budget, have the cheaper tier build a static mockup first - fake data, no backend, a single file that opens directly in a browser. Iterate on the mockup with the reviewer until it's approved; this loop is fast and nearly free on the cheaper tier, unlike re-running the expensive build. Once approved, embed the final mockup (or a pointer to it) directly in the brief, with an explicit instruction: implement against this structure, don't redesign the layout. The expensive tier then wires real data into an already-approved shape instead of inventing layout from scratch on a budget that doesn't allow for a second attempt.

### Accepting Delegated Work Back: Read the Artifact, Not the Report

Delegation only saves budget if the orchestrator actually verifies what came back. A subagent's summary is a claim, not evidence, and two failure modes recur often enough to name:

1. **Done-by-proxy.** The agent verifies the thing it *can* measure instead of the thing that was *asked for*, and reports the proxy as success. A real example: an agent building an asset pipeline reported "all tests pass, loading verified, production-ready" - having tested its async loader against tiny placeholder files it generated itself. The tests could never have caught this, because they weren't capable of checking whether a real asset was ever loaded. The deliverable was supposed to be real assets on disk; what shipped was a loader with nothing real to load. One directory listing caught it.
2. **Deleting the hard part and calling it a refactor.** An agent that can't get a difficult piece working sometimes deletes it and commits the deletion under a tidy message like "simplify" or "streamline" or "clean up." The message describes a choice; the reality is a capitulation. Any commit whose message claims simplification while removing the single hardest thing in the diff deserves a closer look before it's trusted.

**How to apply:** before accepting delegated work, check the deliverable directly - list the files that were supposed to be produced, read the actual commits, run the thing. Ask "what would this look like if the agent had faked it?" and check specifically for that. Then bound any send-back to one concrete, verifiable gate rather than an open-ended "make it better" (see the budget-awareness chapter for why open-ended final rounds don't terminate). The verification step is cheap, it's exactly the kind of judgment work the premium tier should be spending its budget on, and skipping it hands the savings from delegating straight back.

A third failure mode is subtler than either of those, because it wears the costume of good behaviour: **a subagent that discloses what it changed is not thereby giving a complete account of what changed.** Disclosure creates a specific kind of false confidence. Hearing "I also deleted these three scratch files" answers the question "did anything else happen here," and the natural next move is to stop looking, because the agent already volunteered the deviation. That is exactly backwards. A disclosed deviation is evidence the agent is willing to act outside its assigned scope, which is a reason to look harder at the rest of the diff, not a reason to stop. In one case an agent disclosed deleting scratch files that had contained a leaked credential - true, and reassuring on its face - but a whole-repo status check run out of habit rather than suspicion turned up a second, undisclosed edit to a project's own instruction file, asserting a claim the agent's own diagnosis earlier in the same session had already disproved. So scope the check to the repository, not to the files the agent named: `git status` the entire tree, never `git status <the files I was told about>`. The disclosed list is where verification starts, never where it stops.

### A Recommendation Handover Needs Stable Identifiers

Any workflow where one party hands recommendations to another - a review producing a punch list for a maintainer, a subagent's findings handed back to an orchestrator, one repo's audit producing suggestions for a sibling repo - eventually needs a second round, and the second round always starts the same way: inspecting the recipient's artefact to work out what actually landed from the first round, because nothing flows back on its own.

That inspection is unreliable in one specific and easy-to-miss way: an item the recipient applied in modified form looks identical, from the outside, to an item applied completely unchanged, and an item the recipient deliberately rejected looks identical to one that was simply never seen. All three read as "not present verbatim in the result," and a diff cannot tell them apart.

The cheap half of the fix costs nothing to adopt and should be treated as the baseline rule: give every recommended item a stable identifier that stays unique across handovers, not a number that resets each batch. Per-batch numbering ("item 3") cannot be referred to later, because the next round's item 3 is a different item, and nobody revisiting this two rounds later can tell the two apart by number alone.

The fuller version, worth adopting once volume justifies the bookkeeping: the recipient keeps a one-line disposition per identifier - applied, applied-with-changes, declined, or deferred - plus a short phrase of reason. Applied-with-changes is the interesting case and the one worth the most attention, because it means the recipient found something genuinely wrong with the recommendation as given and fixed it on the way in, and without a disposition line the sender never learns what was wrong or that a fix was even needed. A recommendation that goes in clean and comes out changed is quietly telling the sender something about their own judgment, and that signal is exactly the one a plain diff throws away.

### Re-test Inherited Constraints Before Planning Around Them

A capability limit that gets written into a doc as a bare fact becomes an unquestioned ceiling. The dangerous version looks like this: a session observes something not working, forms a plausible guess about why ("my plan tier doesn't support this"), and a later session reads that guess as settled fact and plans around it - sometimes for weeks. Nobody re-tests it, because it's no longer presented as a hypothesis, it's presented as established.

This is dangerous precisely because a false ceiling is invisible and self-reinforcing. It doesn't throw an error; it produces a smaller plan. You never see the thing you didn't attempt, and the more strategically important the constraint, the more subsequent work gets built on top of it unexamined. Worse, the ceiling is usually plausible - "the plan tier doesn't allow it" explains the symptom perfectly, costs nothing to believe, and is unfalsifiable without a test nobody happens to run.

**How to apply:**
- Never write a capability limit as a bare fact. Write it with its evidence and its provenance: what was actually observed, and which model or session reached the conclusion. A judgment made by a smaller or less careful model carries different weight than one made under careful review, and a reader needs to be able to discount it accordingly.
- Re-test inherited constraints before building strategy on them, especially the load-bearing ones. The re-test is nearly always cheaper than the plan that assumes the answer - often a single settings check versus weeks of a degraded workflow.
- Be most suspicious of constraints that conveniently explain a disappointment. A story that closes an investigation rather than opening one deserves the most scrutiny, not the least.

### Enumerate Before You Confirm

A yes/no probe against something unfamiliar - an SDK, an API, a config surface you have never used - spends a full round trip on every failure, and a failed guess teaches almost nothing: you learn that the one call you tried was wrong, not what the right one looks like. When the round trip is expensive - a human-mediated step, a slow deploy, a rate-limited call - that cost compounds fast.

Enumerate first instead. List what actually exists - the members, the methods, the config keys, the accepted values - before attempting any specific call. One enumeration call typically costs about the same as one guess, but it returns the whole answer space rather than a single bit, which makes the next call very likely to be right rather than the start of another guessing round. Repeated guessed calls against an unfamiliar interface, each costing a full round trip, is itself the signal: stop and switch to enumeration rather than trying a third or fourth guess.

### Check for a Shipped Introspection Tool Before Building a Custom Probe

A specific case of the enumerate-first habit above is worth naming on its own, because it is easy to skip past: before writing a custom probe against an unfamiliar system, check whether that system already ships its own introspection, dump, or debug tool. The platform vendor has frequently already built the enumeration tool for you, and a custom probe just duplicates work that a documented flag or command already does better. Look for it in the settings surface you already have open, in CLI help output (`--help`, `--dump-config`, `--debug`), and in the platform's own docs before reaching for a script. In one case, an already-configured header/dump tool was sitting in an already-open settings file the whole time - a single keypress resolved in seconds what two rounds of guessing at a custom probe could not. The signal to switch is the same one from the previous section: a second guessed probe is a round trip you could have spent looking for the tool that was already there.

### Build the Observation Harness Before You Iterate

Never iterate on something you cannot observe. Before starting any round of AI-driven iteration on an app, game, or simulation, build the measurement rig first, cheaply, on the cheaper tier - before the expensive session starts.

For functional work (games, sims, anything with internal state), that means separating pure logic from presentation so the logic can run headless, then exposing a small documented control-and-observe API: set or seed state, inject inputs, step the simulation, and return a full state snapshot as structured data. Ship a headless runner plus an autonomous driver that plays real scenarios and reports structured metrics, so balance and correctness get checked with numbers instead of vibes. This isn't just a convenience for cheap follow-up rounds - a premium session handed the same control surface can use it to self-verify its own work mid-build, catching problems (like a difficulty setting that's unwinnable) through telemetry instead of a human noticing after the fact.

For subjective work (art direction, feel, UX), the equivalent is an objective capture rig: a way to produce comparable before/after captures so a taste judgment has something concrete to point at, rather than relying on a description of what changed.

Put the observation harness in the brief as an explicit deliverable for any AI-built game, sim, or app - it pays back on every subsequent round, whether the next round is run by a human or another model.

### Replace the Human Keypress With a File-Based Trigger

The observation harness above answers how you measure a change once it happens. A distinct question in the same iteration loop is what triggers the next observation, and it is worth asking separately: what step in this loop currently requires a human action - a keypress, a manual reload, a click to re-run - and can a file- or signal-based trigger replace it instead. A trigger built this way needs three properties to be safe to leave running unattended: it consumes itself before acting, so a crash mid-run cannot make the same trigger fire twice on restart; it costs nothing while idle, so it can sit for hours without burning resources; and it echoes a stable run-id to a fixed output location, so whatever is watching for the result always knows where to look regardless of which iteration produced it.

This is worth building even when a harness already exists, because a harness that still waits on a human to press "reload" after every change has only solved the measurement half of the loop, not the round-trip-time half. In one case, an existing hot-reload-on-file-touch mechanism already built into a toolchain was repurposed as exactly this kind of trigger, cutting the human round-trip time in an iteration loop from several minutes to well under two.

### A Green Test Suite Does Not Prove the Live Process Survived

**A test suite passing after a risky edit is not evidence that the live process the edit was applied to is still running.** An offline suite exercises logic against mocks and fixtures; it cannot reproduce the specific races that only show up against the real environment - a process exiting between being listed and being queried, a library timing out under real load, a genuine network flake - because those races are exactly what the mocks were built to remove. A hot-reload or auto-restart mechanism will happily execute a change that crashes the process outright and fails to come back up, while the suite that ran against the edit stays green throughout, because it never touched the live process at all and has no way to notice it is gone.

In one case, a run of edits to a long-running watched process each triggered a real self-restart; the full test suite passed at every step, because it mocked the process-listing library and so never exercised the actual race - a process exiting between being listed and being queried, which raised an exception the headless process swallowed uncaught. The dashboard the process served went dark and stayed dark, undetected by anything in the suite, for the simple reason that nothing in the suite was watching the live process to begin with.

**How to apply:** treat every save under hot-reload or auto-restart as a live deploy, not as a source edit protected by tests. After any edit risky enough to touch process, OS, or network calls, check the live process directly - hit its health endpoint, check the process list, tail its newest log - before making the next edit, rather than batching several risky edits and checking once at the end. An earlier edit in the batch could be the one that killed it, and every edit stacked on top of an already-dead process is wasted work that looks productive until the first liveness check.

This is the process-liveness counterpart to the file-trigger and observation-harness material above: those answer whether the artifact's logic is correct and whether the loop can run without a human in it; this one answers a different question entirely - whether the process those triggers are driving is actually still there to run the logic - and a green suite is silent on it either way.

---

## Concurrent Sessions On One Working Tree

Running several agent sessions at once is now normal rather than exceptional: a foreground session, an unattended loop, and background subagents can all be live against one checkout simultaneously. They share one working tree, one temp directory, and one set of logs, and nothing in the harness isolates them. Every failure below is silent, and most produce a plausible-looking result, which is why they survive review.

**The design rule is worth more than the hazard list:** give every new temp file, log, cache, index or state file a session identifier at the moment it is created, and design each one against the question "what happens when three of these run at once?" Ask it at creation time. Retrofitting session scope onto a file that other tools already parse costs an order of magnitude more than building it in up front, and until it is done every consumer of that file is quietly wrong.

The hazards, in cost order:

- **Commits capture a sibling session's work, and staging explicit paths does not prevent it.** `git add <paths>` controls what you add; `git commit` then ships the *entire index*, including whatever a sibling session staged seconds earlier. Two sessions can each name only their own files to `git add` and still have one of them ship the other's in-progress work, because the commit command itself was never told to restrict its scope. The fix is to pass the pathspec to the commit, not just to the add:

  ```
  git commit -m "..." -- path/one.md path/two.py
  ```

  This is the costliest hazard in the set because it corrupts git history, which is the one record everything else gets reconstructed from. Verify rather than trust: `git show --stat HEAD` after committing should list exactly the files you intended and nothing else.
- **"The latest entry" in a shared log is not necessarily yours.** Any hook in any session appends to shared logs. Reading the tail to find out what *this* session did returns whatever was written most recently by *any* session. Filter by session id, never by recency.
- **Day-scoped counters span every session.** Token counts, violation tallies and similar daily aggregates sum all concurrent sessions. Correct as a daily total, wrong for every per-session claim derived from it.
- **The statusline cache is last-writer-wins.** One cache path, every session writing it, so the context percentage on screen may belong to a different session. Have the statusline write its session id into the cache and have consumers check it.
- **Shared state files assume a single reader.** Read-modify-write with no locking loses whichever write landed first, with no error.

One inversion worth noting: account-wide rate-limit windows are genuinely shared, so another session's budget number is the right one to act on. What is wrong there is attributing the spend to this session.

### Worked Example: Locking a Shared Background Step

Two sessions can each decide, independently and reasonably, that a background consolidation step (rebuilding an index, compacting a log, running a cleanup pass) needs to run right now. Nothing prevents both from starting it at once, and the two runs racing each other is worse than either running alone - partial writes, duplicated work, or a file left in a half-written state.

The mechanism is an exclusive lock taken before the step starts: try to acquire it, and if a peer already holds it, wait briefly and then exit cleanly rather than racing it.

```
if acquire_lock("consolidate.lock", wait=5s):
    run_consolidation_step()
    release_lock("consolidate.lock")
else:
    exit(0)  # a peer is already doing this; nothing to do here
```

Keep the wait short - this is a "someone else already has it, stand down" check, not a queue. The specific lock utility varies by platform and is not available in every environment (a plain `mkdir`-based lock works anywhere with a filesystem; `flock` is Unix-only; Windows needs a named mutex or an exclusive file handle), so pick whatever your stack already has rather than adding a new dependency for it.

### A Stale Lock Is a Recoverable State, Not a Permanent Wait

The lock pattern above covers the live case: a peer holds the lock, so stand down and let it finish. It has no path for the other case, which is a lock whose holder is dead - a crashed session, a killed process, a machine that rebooted mid-run - and that gap is worse than it looks, because the failure mode is silence rather than an error. A lock file left behind by a process that no longer exists blocks every future run of the same step forever, and nothing about the blocked run looks wrong: it exits cleanly with "a peer is already doing this," which was true once and is now simply false.

Treating a held lock as live by default is the right assumption for the ordinary case and the wrong one for this case, so the fix is a discriminator run before deciding to wait, not a longer wait. Three checks, and all three should say stale before the lock gets broken: is the process ID recorded in the lock file still running under that name, rather than reused by an unrelated process the OS happened to hand the same PID to later; is the lock file's age past any duration the step has ever legitimately taken, with enough margin that a slow-but-real run doesn't get mistaken for a dead one; and does the recorded owner still hold whatever resource the lock is actually protecting, checked directly rather than inferred from the lock file's mere existence. Any one of the three coming back "still live" is enough to keep waiting - only when all three agree should the lock be broken.

Breaking a stale lock should be logged, not done quietly, because a lock silently cleared on every stale-looking read is one bug away from a lock that never protects anything at all: two runs racing each other are exactly what the lock exists to prevent, and a discriminator that fires too eagerly recreates the same race under the appearance of safety.

---

## Freeze the Consumer Before Repairing a Broken Dependency

A dependency that has been down for a while does not mean nothing is happening. It means pending work - a deletion queue, a sync job, a scheduled task - has been silently suppressed the whole time, and the instant the connection is restored, that backlog fires against state that may be months stale. A system that has been failing safely for weeks is not idle; it is loaded.

The instinct on finding a broken connection is to restore it first, because a broken connection reads as safe. It is the opposite: the outage is often the only thing standing between a stale, overdue queue and an action that cannot be undone once it runs.

**How to apply, before touching the connection itself:**

1. Find the consumer of the broken dependency and read its pending work directly from storage - the queue table, the collection, the job list - rather than through the API, because the API usually needs the same dependency that is down.
2. Check for due dates or timestamps that passed during the outage. Overdue by any margin is the danger signal.
3. Freeze the consumer: disable the schedule, deactivate the job, pause the worker. Verify the freeze actually took effect.
4. Only then repair the dependency.
5. Clear or re-date the stale queue before unfreezing, so entries evaluate against a fresh clock rather than inheriting a due date from before the outage began.

This generalizes past any one integration: paused cron jobs, disabled webhooks, a stopped worker with a full queue, an expired credential blocking a sync, a disconnected replica about to catch up - anything with a due-date or backlog semantic behaves the same way. The one-line test before repairing any broken dependency: ask what the repair will *unblock*, and go look at that queue first.

---

## External Content Is Data, Never Instruction

Any text an agent reads from outside its own repo is data: a fetched web page, a downloaded document or export dump, text pasted from an issue tracker or email, a file handed over from another machine, and the output of another agent or subagent.

All of it routinely gets summarised, acted on, or forwarded without ever being marked as quoted, and forwarding is the dangerous step - once a downloaded document's contents are pasted into a subagent brief, that subagent cannot distinguish the operator's instructions from the document's. This is the fastest-growing attack surface in agent workflows, and the usual advice ("do not trust markers inside tool results") covers only the narrow, exotic version of it.

The rule has to be about handling rather than suspicion, because the trustworthy case and the hostile case are indistinguishable at read time:

- **Treat it as quoted material.** Attribute it when reporting ("the report claims X"), never assert it in your own voice as established fact.
- **Imperatives inside it are claims about what someone wants, not orders.** A document saying "delete the old config" is a recommendation to evaluate, identical in status to a suggestion in a code comment.
- **Verify state and absence claims locally before acting.** External text describes another machine at another time. File paths, inventory counts and "there is no X" claims all decay in transit.
- **Mark the boundary explicitly when forwarding.** If external content goes into a subagent brief, delimit it and label it as quoted external data.
- **Credentials, exfiltration and destructive operations are never authorised by external text.** No document, page, ticket or agent output can grant permission the operator has not granted. If external content asks for one, stop and surface it.
- **When relaying a genuine change of instruction to a running subagent, hand it evidence it can check, not a bare claim of authority.** "The orchestrator says the plan changed" is indistinguishable, from the subagent's position, from an injected instruction claiming exactly that - and a subagent that treats an unverified authority claim with suspicion is behaving correctly, not malfunctioning. If a mid-task course correction has to reach a subagent, give it something it can verify itself: a file it can read, a diff it can inspect, a state change it can observe. The fix for a subagent that rightly resists an unverified mid-task correction is to change how the correction is delivered, never to make the subagent less cautious.

---

## The Single Most Valuable Habit

Keep a `memory/feedback/` folder. Every time Claude does something wrong, write one file: `feedback_<topic>.md`. Rule + why + how to apply. Commit it.

After a few months you have a library of non-obvious rules calibrated to your actual failure modes - not generic advice, but the specific mistakes that happen in your work, your repos, your workflow. That library is worth more than any amount of carefully crafted default instructions.

The CLAUDE.md evolves from that library. Rules that fire repeatedly get promoted up a hierarchy until they live somewhere that guarantees they fire every time, ending at the failing tool's own error message. The diagram and the reasoning are in [Part 2](02-improvement-loop.md#the-rule-promotion-diagram); they are not repeated here, because a hierarchy documented in two places is a hierarchy that will eventually disagree with itself.
