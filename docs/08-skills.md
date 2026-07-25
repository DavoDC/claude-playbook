# Part 8: Skills Reference

All skills live in `.claude/skills/<name>/SKILL.md`. Each is a markdown file defining what Claude should do when you type `/<name>`. Usage below is tracked via a session logger hook and shown qualitatively (heavily used / regularly used / occasional / rarely used) rather than as exact counts - a number written today is stale by next week, and the category is what actually matters for deciding what to keep installed. See the maintenance section at the end of this part for how that tracking feeds a retirement loop.

Skills are sorted below by how often they're actually used - not by how interesting they sound.

---

## The Thinking Skills (Pin These to the Top)

These are listed first regardless of usage count - every invocation is high-value and they should be the first thing you reach for on hard problems.

### [/aristotle](https://github.com/DavoDC/claude-playbook/blob/main/skills/aristotle/SKILL.md) (occasional, but every use is high-value)

First principles deconstruction. Strips all assumptions from a problem, finds the irreducible truths, rebuilds from zero.

**The 5 phases:**
1. **Identify the claim** - state exactly what is being assumed
2. **Assumption autopsy** - list every assumption baked in. Not just the obvious ones.
3. **Find irreducible truths** - what do we actually know for certain? These are the axioms.
4. **Reconstruct from zero** - given only the axioms, what are three different designs? No inherited structure.
5. **The Aristotelian Move** - the single highest-leverage action. Not a plan, not a roadmap - one thing that changes the most.

**When to use:** when designing a system, when facing a "should this even exist?" question, when an existing approach is failing and you can't see why. Anywhere you need to cut through accumulated assumptions.

**Why it's valuable:** it consistently surfaces the real problem behind the stated problem. You think you're designing a config system; Aristotle reveals you're actually trying to reduce manual context-switching. The solution space changes completely.

[Full SKILL.md](https://github.com/DavoDC/claude-playbook/blob/main/skills/aristotle/SKILL.md)

---

### [/premortem](https://github.com/DavoDC/claude-playbook/blob/main/skills/premortem/SKILL.md) (every use is high-value)

Pre-mortem risk analysis. Imagine the plan has already failed. Work backward to find every reason why.

**The insight behind it:** prospective hindsight works better than forward-planning. "What could go wrong?" produces weak answers. "It failed - what happened?" produces specific, realistic ones. Gary Klein (HBR 2007); Kahneman called it his single most valuable decision-making technique.

**The classification framework:**

- **Tiger** - real, evidence-backed risk. A specific plausible scenario. Ignoring it is negligent.
- **Paper Tiger** - sounds alarming but, on close inspection, unlikely or low-impact. Often raised from anxiety rather than knowledge.
- **Elephant** - the thing everyone knows about but nobody says. Political, organisational, interpersonal. Often the actual cause of failure when projects fail. Signal: the room goes quiet when this comes up.

For each Tiger, assign urgency: Launch-Blocking / Fast-Follow (within 1-2 weeks) / Track (monitor).

**The synthesis output** (this is where the real value is):
- **Most Likely Failure** - highest probability Tiger with one-sentence reasoning
- **Most Dangerous Failure** - highest damage Tiger, even if less likely
- **Hidden Assumption** - the single biggest thing the plan takes for granted that hasn't been questioned. Frequently the Elephant in disguise.
- **Revised Plan** - one concrete action per Launch-Blocking Tiger. Not "consider X" - what to do, by when, who owns it.
- **Revised Confidence** - score out of 10 with rationale, and what single change raises it most.

**When to use:** before any significant implementation, before a release, before any irreversible decision. Especially when you're feeling confident - confidence is when blind spots are biggest.

Pairs well with `/aristotle`: run Aristotle to stress-test the design, then premortem to stress-test the execution plan.

[Full SKILL.md](https://github.com/DavoDC/claude-playbook/blob/main/skills/premortem/SKILL.md)

---

### [/think](https://github.com/DavoDC/claude-playbook/blob/main/skills/think/SKILL.md) (use for major design decisions)

Full first-principles build workflow. Chains three things in order:

1. **Aristotle deconstruction** - strip assumptions, find axioms, rebuild from zero
2. **5-step engineering algorithm** - applied to the Aristotelian Move:
   - **Question** - is this actually needed? Whose need does it serve?
   - **Delete** - actively try to remove 10% of it. If nothing was deleted, you haven't deleted enough.
   - **Simplify** - fewer steps, fewer dependencies, shorter.
   - **Accelerate** - make the remaining essential parts faster.
   - **Automate** - last. Never automate what should be deleted first.
3. **Instantiation check** - does the solution embody the problem it prevents? A complexity-reducing refactor that adds a new abstraction layer instantiates the problem. If yes: redesign.

The order matters. Delete before simplify. Simplify before accelerate. Automate last.

**When to use:** when designing or building anything non-trivial where getting the approach wrong has real cost. `/aristotle` alone for pure deconstruction; `/think` when you're actually building.

---

### [/socrates](https://github.com/DavoDC/claude-playbook/blob/main/skills/socrates/SKILL.md) (rule evaluator)

Examines EXISTING rules backward - "should this still exist?" Complements `/aristotle` (which deconstructs forward when designing). Use when auditing enforced-rules.md, before adding yet another rule, or when a rule feels stale and you can't articulate why.

**Five questions per principle:**
1. Still true? (conditions, tools, paths current?)
2. Justified from first principles? (real incident / system constraint, not convention)
3. Best practice or just "what we've always done"?
4. Still violated? (never-fires = zombie or success - check logs)
5. Zombie? (already covered by a hook or higher-tier enforcement?)

**Verdict scheme:** JUSTIFIED (keep) / VERBOSE (simplify) / WEAK (strengthen or move to hook) / ZOMBIE (delete) / DEAD-REF (fix the refs).

Output: table of verdicts per principle (not prose), then a one-paragraph summary. Anti-pattern: zero zombies = you summarised, not questioned.

Wire to a quarterly recurring task with your enforced-rules.md + CLAUDE.md as arguments. Pairs well with `/reflection` (which finds new rules to add) - `/socrates` is the trimmer.

[Starter SKILL.md](https://github.com/DavoDC/claude-playbook/blob/main/skills/socrates/SKILL.md)

---

## Daily Workflow Skills

### /end-session (heavily used)
Close out a session: write session record, reconcile tasks, drain memory, commit everything. The crux of the improvement loop. Run at the end of every session. See [Part 6](06-sessions-and-memory.md) for full detail.

No starter SKILL.md included - this skill calls workspace-specific scripts (session consolidation, finalize stages). Build it incrementally: start with a simple "write session summary + commit" skill, then add the consolidation scripts as your workspace matures. The design is fully documented in Part 6.

### /loop (heavily used)
Claude Code built-in. Runs a prompt on a repeating interval. Usage: `/loop 30m /dev-session myproject`. The overnight work loop - set before bed, wake up to finished features. See [Part 7](07-overnight-loop.md) for the full workflow. No SKILL.md needed.

### /dev-session (heavily used)
Smart session composition with IDEAS.md orchestration, TDD gate, budget awareness, scope definition, and rule capture. The primary skill for actual project work. See [Part 4](04-dev-session.md) for full detail.

No starter SKILL.md included - this skill integrates with IDEAS.md, budget awareness tools, and the git workflow. Build it after the workspace CLAUDE.md, IDEAS.md, and budget tools are set up. The design is fully documented in Part 4.

### [/commit-chunks](https://github.com/DavoDC/claude-playbook/blob/main/skills/commit-chunks/SKILL.md) (regularly used)
Commit changed files in logical chunks - one commit per feature/fix/topic. Analyses what's staged/unstaged and proposes a commit split with draft messages. Prevents the "committed everything in one giant blob" problem that makes git history unreadable.

### [/deep-dive](https://github.com/DavoDC/claude-playbook/blob/main/skills/deep-dive/SKILL.md) (occasional)
Deep investigation of a topic, file, directory, or repo. Think hard, investigate thoroughly, miss nothing. Uses a commit-anchored delta approach (see [Part 10](10-advanced.md)): only reads files that changed since the last deep-dive of the same scope.

### [/process-feedback](https://github.com/DavoDC/claude-playbook/blob/main/skills/process-feedback/SKILL.md) (occasional)
Takes a `feedback_*.txt` file written by the user (raw notes, corrections, wishes) and produces two outputs: new IDEAS.md entries for product work, and Claude rule files for feedback. The bridge between user notes and the improvement system.

### [/refine-ideas](https://github.com/DavoDC/claude-playbook/blob/main/skills/refine-ideas/SKILL.md) (occasional)
Interactively clarify IDEAS.md priorities. Asks one question per item, derives semantic tiers from your answers. Use when IDEAS.md has gotten messy or when you've added a bunch of items and need to re-sort.

### [/commit-all](https://github.com/DavoDC/claude-playbook/blob/main/skills/commit-all/SKILL.md) (rarely used)
Commit all changed files in one go. Less surgical than `/commit-chunks` - use when you want everything staged and committed without thinking about logical grouping.

### [/reflection](https://github.com/DavoDC/claude-playbook/blob/main/skills/reflection/SKILL.md) (rarely used)
Read recent session history and update CLAUDE.md, memory files, and workspace based on patterns found. Uses commit-anchored delta - only reads sessions added since the last reflection, stays fast. Run every few sessions or after a major block of work.

[Starter SKILL.md](https://github.com/DavoDC/claude-playbook/blob/main/skills/reflection/SKILL.md)

### [/step-commits](https://github.com/DavoDC/claude-playbook/blob/main/skills/step-commits/SKILL.md) (rarely used)
Plan changes as atomic commits upfront before implementing. Define the commit sequence first, then execute one commit at a time. Good for complex multi-step changes where getting the commit order right matters.

### [/human-voice](https://github.com/DavoDC/claude-playbook/blob/main/skills/human-voice/SKILL.md) (rarely used)
Audit and rewrite text to remove AI writing patterns. For anything written to a person.

**Tier 1 - always replace:** delve, leverage (as verb), utilize, robust, comprehensive, cutting-edge, seamless, meticulous, actionable, paradigm, testament to, underscores, holistic, synergy, "in order to", "serves as", "best practices"

**Always remove:** "I hope this helps!", "Certainly!", "Absolutely!", "Happy to help", "Feel free to reach out" - chat interface tics that sound fake in written documents

**Structural tells:** uniform paragraph length (vary deliberately), excessive bullet lists in personal messages (prose is almost always better), formulaic openings that start with broad context instead of the actual point

Two modes: `rewrite` (default) or `detect` (flags only, no rewriting).

### [/checkpoint](https://github.com/DavoDC/claude-playbook/blob/main/skills/checkpoint/SKILL.md) (use in overnight loops)
Create named restore points during long sessions or loops. `create <name>` commits current state and logs the checkpoint with SHA and context percentage. `list` shows today's checkpoints. `verify <name>` shows diff since that checkpoint.

---

## Supporting Skills

### /today
Quick view of today's strategic and tactical focus. Reads the directives overview (strategic) and pending-actions.md (tactical), shows top 3-5 items. Also includes a budget gate - if context is at 80%+ it stops and tells you to run `/end-session` before planning anything.

### /plan-day
More detailed than `/today`. Categorises all pending items into: can do now, needs you, needs team, quick wins. Recommends parallel sessions when there are 2+ independent tasks that would each take 30+ minutes.

### /self-audit
Workspace compliance check. Read-only - reports findings, never auto-fixes. Checks MEMORY.md health, pending actions for stale items, .gitignore gaps, skill integrity, hooks configuration.

### [/validate-rules](https://github.com/DavoDC/claude-playbook/blob/main/skills/validate-rules/SKILL.md)
Check that enforced-rules.md and feedback files are internally consistent and not contradicting each other. Also runs validation to ensure hook-enforced rules are actually implemented in the hooks.

### /pre-rebuild
Pre-rebuild checklist before a major refactor or rebuild. Ensures you've captured the current state, understand what exists, and have a recovery plan before destroying anything.

### /code-review *(build your own)*
Review the current diff for correctness bugs at configurable effort levels. No starter provided - straightforward to build: "read `git diff HEAD`, check for correctness issues, output findings."

### /security-review *(build your own)*
Security-focused code review. Looks for OWASP top 10, credential leaks, injection vulnerabilities. No starter provided - can be as simple as: "read the diff, check for the OWASP top 10, report findings grouped by severity."

### [/release](https://github.com/DavoDC/claude-playbook/blob/main/skills/release/SKILL.md)
Structured release process: version bump, changelog, tag, push.

### [/make-public](https://github.com/DavoDC/claude-playbook/blob/main/skills/make-public/SKILL.md)
Pre-flight checklist before making a repo public. Checks for private paths, personal names, credentials, workspace-internal references.

### /save-memory *(build your own)*
Manually save a piece of information to the memory system. No starter provided - straightforward: "write the fact to `memory/<category>/<name>.md`, add a pointer to `memory/MEMORY.md`, commit."

### [/check-compact](https://github.com/DavoDC/claude-playbook/blob/main/skills/check-compact/SKILL.md)
Context size check: counts exchanges in the current session; replies with one line - "Context heavy - please run /compact now." if heavy, or "Context light - no compact needed (~N exchanges)." if light. Run when unsure if compaction is needed before a large task.

[Starter SKILL.md](https://github.com/DavoDC/claude-playbook/blob/main/skills/check-compact/SKILL.md)

### [/survey-repo](https://github.com/DavoDC/claude-playbook/blob/main/skills/survey-repo/SKILL.md)
Quick codebase summary: language, purpose, key files, tests, entry points, open TODOs. Use when starting work on an unfamiliar repo.

### [/undo-commits](https://github.com/DavoDC/claude-playbook/blob/main/skills/undo-commits/SKILL.md)
Undo the last N commits via `git reset --soft`, show what's staged, help recommit cleanly. Safe - never rebases, never force-pushes.

### /health
Workspace health check. Detects skill gaps, hook count anomalies, file bloat, stale peer-sync reviews, unindexed memory files.

### [/repo-status](https://github.com/DavoDC/claude-playbook/blob/main/skills/repo-status/SKILL.md)
Multi-repo status overview. For each repo in a configured directory: current branch, uncommitted changes count, and unpushed commits count. Output as a compact table. Flags repos with dirty files, unpushed commits, or unexpected branches. Never fetches (no network requirement). Read-only.

Run before container rebuilds, session ends, or switching between repos. Build your own: `git -C <repo> status --short`, `git -C <repo> rev-list --count @{upstream}..HEAD`, output as a table.

[Starter SKILL.md](https://github.com/DavoDC/claude-playbook/blob/main/skills/repo-status/SKILL.md)

---

## Skill Library Maintenance

Every skill installed under `.claude/skills/` loads its name and one-line description into every session's context, whether or not that session ever calls it. A skill nobody invokes this month is a permanent tax on all the sessions that never call it either - the usage tiers above (heavily used, occasional, rarely used) exist specifically to surface which ones are paying for themselves and which aren't. The fix isn't fewer skills up front, since you can't know in advance which will earn their keep. It's a retirement loop.

**Log invocations, then retire on evidence, not vibes.** The session logger hook records which skill fired on each `/command`, which over time gives actual usage data instead of a guess about what "feels" used. On a regular cadence - each `/reflection`, or a periodic `/health` pass - look at what hasn't fired in a long stretch and move it out of `.claude/skills/` into an archive folder, for example `archive/skills/`. Archive, never delete: keep the file git-tracked and runnable exactly as it was, just outside the directory that gets loaded into context every session. Bringing one back is a file move, not a rebuild.

**Keep a retired-skills index.** Retiring a skill without a record of it means forgetting it exists the next time the process comes up. One entry per retired skill - what it did, when it was retired, and the path to bring it back - in an index file next to the archive folder. The index is what makes retirement safe: you're not deleting capability, you're moving its cost from "every session" to "the one session you actually need it."

**Prefer reading a retired skill in place over promoting it back.** For a process that comes up genuinely occasionally - once a quarter, once every few months - the cheapest move is to open the archived SKILL.md and follow it manually, not to reinstall it. Promoting it back "just for this one use" is exactly how the context tax creeps back in: nobody re-retires it afterward, and a few months later it's dead weight in every session again.

**The promotion criterion - and the part invocation counts alone will miss.** A skill earns its place installed if EITHER of two things is true: it's invoked directly and regularly, OR another installed skill routes into it as part of its own workflow. The second criterion is the non-obvious one. A real failure mode: a ranking/prioritisation skill was retired because its own direct invocation count was low, while several of the thinking skills that stayed installed all called into it as a step in their own process. The result was a dead command sitting in the middle of what had been a working chain - the routing calls into it silently failed, and nobody noticed until something downstream broke. Before retiring anything, grep the other installed skills for its name, not just its own invocation log.

**Match new corrections against the archive by lesson, not by name.** The same discipline applies to archived rules. When a fresh correction comes in, check whether an archived feedback file already covers that lesson - and if one does, the archival was premature and the rule should come back rather than be rewritten under a new name. Matching on file names alone misses this every time, because the second occurrence of a lesson almost never arrives with the same wording as the first. An archive nobody checks against is just a slower delete.

**The corollary.** A process you run only every month or two is often better off as a plain doc than as a skill at all. The doc is the runnable artifact - you or Claude reads it and follows the steps - and it costs nothing on every session that doesn't need it, versus a skill's permanent description-line tax paid regardless of use. Reach for a skill when a process needs Claude to make judgment calls across several steps on a regular basis; reach for a doc when it's reference material consulted rarely.
