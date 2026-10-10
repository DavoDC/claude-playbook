# Part 7: Skills Reference

> **Field note.** Written from practice rather than machine-checked, and not covered by `tools/selftest.sh`. Last reviewed 2026-08-02 against Claude Code v2.1.220. Opinionated, and it may lag the harness.

All skills live in `.claude/skills/<name>/SKILL.md`. Each is a markdown file defining what Claude should do when you type `/<name>`. See the maintenance section at the end of this part for how to keep the installed set small.

Skills are sorted within each section by impact: how much a skill improves the work for most users, not by how interesting it sounds.

The shipped set is a menu, not a recommended set: install what fits your workflow. A skill that is dead weight in one workflow can be the most useful in another.

---

## The Thinking Skills (Pin These to the Top)

These are listed first because every invocation is high-value: they are the first thing to reach for on hard problems.

### [/aristotle](https://github.com/DavoDC/claude-playbook/blob/main/skills/aristotle/SKILL.md)

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

Wire to a recurring task with your enforced-rules.md + CLAUDE.md as arguments. Pairs well with `/reflection` (which finds new rules to add) - `/socrates` is the trimmer.

A calendar cadence ("quarterly") generalises poorly if your usage is irregular, since a quarter can pass in a handful of sessions or hundreds. If usage is bursty, prefer a cadence measured in sessions (for example every 15-20) over calendar time.

[Starter SKILL.md](https://github.com/DavoDC/claude-playbook/blob/main/skills/socrates/SKILL.md)

---

### [/prioritise](https://github.com/DavoDC/claude-playbook/blob/main/skills/prioritise/SKILL.md) (ranking interface)

Rank any list or backlog by leverage, using Aristotle's "who benefits, are they a bottleneck?" lens. Aristotle is the engine; this is the focused interface for pure ranking - no full 5-phase narration, just a ranked list with one-line justification per item.

**When to use:** ranking a backlog, prioritising IDEAS.md, deciding what order to work through a list of tasks. When `/aristotle` is already running, redirect pure ranking requests here instead.

[Full SKILL.md](https://github.com/DavoDC/claude-playbook/blob/main/skills/prioritise/SKILL.md)

---

### [/brainstorm](https://github.com/DavoDC/claude-playbook/blob/main/skills/brainstorm/SKILL.md) (generation interface)

Generate options for a genuinely open-ended problem using a named method rather than free association: Six Thinking Hats to evaluate one candidate from six angles, SCAMPER to generate siblings of a candidate that already exists, total negation to break out of a framing, reverse brainstorming for safety and correctness work.

**When to use:** "think broadly", "what else could we do", "give me options", "I'm stuck on how to approach this". Also when exactly one candidate exists and you want adjacent or better ones.

**The thing it deliberately does not do is rank.** Generation and evaluation are different activities and blending them is why brainstorms produce three ideas: the first objection kills the second idea before the fourth one exists. This skill generates and hands off to `/prioritise`.

[Full SKILL.md](https://github.com/DavoDC/claude-playbook/blob/main/skills/brainstorm/SKILL.md)

---

## Daily Workflow Skills

### /end-session
Close out a session: write session record, reconcile tasks, drain memory, commit everything. The crux of the improvement loop. Run at the end of every session. See [Part 5](05-sessions-and-memory.md) for full detail.

A template [SKILL.md](../skills/end-session/SKILL.md) is included, with placeholders for your memory folder, fragment folder and task list. It names the scripts that own the mechanical edits (prep, finalize, commit) but does not ship them, since they depend on your layout. Build incrementally: start with "write session summary + commit", then add consolidation scripts as your workspace matures. Design: Part 5.

### /loop
Claude Code built-in. Runs a prompt on a repeating interval. Usage: `/loop 30m work the top item in IDEAS.md`. The overnight work loop - set before bed, wake up to finished features. See [Part 6](06-overnight-loop.md) for the full workflow. No SKILL.md needed.

### [/commit-chunks](https://github.com/DavoDC/claude-playbook/blob/main/skills/commit-chunks/SKILL.md)
Commit changed files in logical chunks - one commit per feature/fix/topic. Analyses what's staged/unstaged and proposes a commit split with draft messages. Prevents the "committed everything in one giant blob" problem that makes git history unreadable.

### [/deep-dive](https://github.com/DavoDC/claude-playbook/blob/main/skills/deep-dive/SKILL.md)

Deep investigation of a topic, file, directory or repo. Two mechanisms make it different from asking Claude to look at something carefully.

It uses a commit-anchored delta (see [Part 16](16-commit-anchored-delta.md)) so it only reads files that changed since the last dive of the same scope, which is what makes repeating it cheap.

And it generates its lenses before it scans, using the framework in [Part 12](12-audit-lenses.md), then states which cells it walked and which it deliberately skipped. That stops the fifth pass over a repo confirming what the fourth said: the delta says which files to re-read, only the lens framework says what to ask of them.

### [/cross-synth](https://github.com/DavoDC/claude-playbook/blob/main/skills/cross-synth/SKILL.md)
Cross-synthesise any N subjects (repos, files, docs, configs, tests, features) side-by-side: find what's shared, what's missing, what's inconsistent, and what one subject can teach the others. Horizontal analysis - where `/deep-dive` goes deep on one thing, `/cross-synth` goes wide across many.

### [/reflection](https://github.com/DavoDC/claude-playbook/blob/main/skills/reflection/SKILL.md)
Read recent session history and update CLAUDE.md, memory files, and workspace based on patterns found. Uses commit-anchored delta - only reads sessions added since the last reflection, stays fast. Run every few sessions or after a major block of work.

### [/process-feedback](https://github.com/DavoDC/claude-playbook/blob/main/skills/process-feedback/SKILL.md)
Takes a `feedback_*.txt` file written by the user (raw notes, corrections, wishes) and produces two outputs: new IDEAS.md entries for product work, and Claude rule files for feedback. The bridge between user notes and the improvement system.

### [/refine-ideas](https://github.com/DavoDC/claude-playbook/blob/main/skills/refine-ideas/SKILL.md)
Interactively clarify IDEAS.md priorities. Asks one question per item, derives semantic tiers from your answers. Use when IDEAS.md has gotten messy or when you've added a bunch of items and need to re-sort.

### [/step-commits](https://github.com/DavoDC/claude-playbook/blob/main/skills/step-commits/SKILL.md)
Plan changes as atomic commits upfront before implementing. Define the commit sequence first, then execute one commit at a time. Good for complex multi-step changes where getting the commit order right matters.

### [/commit-all](https://github.com/DavoDC/claude-playbook/blob/main/skills/commit-all/SKILL.md)
Commit all changed files in one go. Less surgical than `/commit-chunks` - use when you want everything staged and committed without thinking about logical grouping.

### [/human-voice](https://github.com/DavoDC/claude-playbook/blob/main/skills/human-voice/SKILL.md)
Audit and rewrite text to remove AI writing patterns. For anything written to a person.

**Tier 1 - always replace:** delve, leverage (as verb), utilize, robust, comprehensive, cutting-edge, seamless, meticulous, actionable, paradigm, testament to, underscores, holistic, synergy, "in order to", "serves as", "best practices"

**Always remove:** "I hope this helps!", "Certainly!", "Absolutely!", "Happy to help", "Feel free to reach out" - chat interface tics that sound fake in written documents

**Structural tells:** uniform paragraph length (vary deliberately), excessive bullet lists in personal messages (prose is almost always better), formulaic openings that start with broad context instead of the actual point

Two modes: `rewrite` (default) or `detect` (flags only, no rewriting).

---

## Supporting Skills

### [/today](../skills/today/SKILL.md)
Quick view of today's strategic and tactical focus. Reads a priority overview (strategic) and pending-actions.md (tactical), shows the top 3 with their next step plus the whole queue. Also includes a budget gate - if context is at 80%+ it stops and tells you to run `/end-session` before planning anything. Shipped as a template: point its three source paths at your own roadmap files.

### [/whats-next](../skills/whats-next/SKILL.md)
A numbered list of next actions and nothing else, each tagged as something Claude can do alone or something that needs you. Small on purpose.

### [/handoff](../skills/handoff/SKILL.md)
Writes the prompt that starts a fresh session on unfinished work. A script reads mechanical state off disk (branch, dirty files, scratch files), and the model adds only the judgment: the outcome, what is out of scope, and a live-verified date on every outward-facing instruction. Decides first whether a handoff is warranted at all.

### /plan-day
More detailed than `/today`. Categorises all pending items into: can do now, needs you, needs team, quick wins. Recommends parallel sessions when there are 2+ independent tasks that would each take 30+ minutes.

### /self-audit
Workspace compliance check. Read-only - reports findings, never auto-fixes. Checks MEMORY.md health, pending actions for stale items, .gitignore gaps, skill integrity, hooks configuration.

### [/undo-commits](https://github.com/DavoDC/claude-playbook/blob/main/skills/undo-commits/SKILL.md)
Undo the last N commits via `git reset --soft`, show what's staged, help recommit cleanly. Safe - never rebases, never force-pushes.

### [/repo-status](https://github.com/DavoDC/claude-playbook/blob/main/skills/repo-status/SKILL.md)
Multi-repo status overview. For each repo in a configured directory: current branch, uncommitted changes count, and unpushed commits count. Output as a compact table. Flags repos with dirty files, unpushed commits, or unexpected branches. Never fetches (no network requirement). Read-only.

Run before container rebuilds, session ends, or switching between repos. Build your own: `git -C <repo> status --short`, `git -C <repo> rev-list --count @{upstream}..HEAD`, output as a table.

[Starter SKILL.md](https://github.com/DavoDC/claude-playbook/blob/main/skills/repo-status/SKILL.md)

---

## Skill Library Maintenance

Every skill under `.claude/skills/` loads its name and one-line description into every session's context, whether or not that session calls it, so a skill nobody invokes is a permanent tax on all sessions. You can't know in advance which skills will earn their keep, so the fix isn't fewer skills up front but a retirement loop.

**Log invocations, then retire on evidence, not vibes.** The session logger hook records which skill fired on each `/command`, giving actual usage data. On a regular cadence - for example each `/reflection` - move skills that haven't fired in a long stretch out of `.claude/skills/` into an archive folder, for example `archive/skills/`. Archive, never delete: keep the file git-tracked and runnable, just outside the directory loaded every session. Bringing one back is a file move, not a rebuild.

**Keep a retired-skills index.** One entry per retired skill - what it did, when it was retired, and the path to bring it back - in an index file next to the archive. Without a record you forget it exists. The index makes retirement safe: you move its cost from "every session" to "the one session you need it."

**Prefer reading a retired skill in place over promoting it back.** For a genuinely occasional process, open the archived SKILL.md and follow it manually. Do not promote something back "just for this one use": nobody re-retires it afterwards, and a few months later it is dead weight in every session again.

**Track the retirement decision itself.** Archiving is easy to execute and forget; the judgment call ("was this the right thing to retire?") disappears with it. Put it on a visible backlog: a line in your ideas or backlog doc naming the skill and the open question. Most important for close calls - low but nonzero usage, or overlap with something that stayed installed. A decision on a backlog gets reconsidered when circumstances change; one that exists only as a completed action in an archive folder does not.

**The promotion criterion - and what invocation counts miss.** A skill earns its place installed if EITHER it is invoked directly and regularly, OR another installed skill routes into it as part of its workflow. The second is non-obvious: a ranking skill can have a low direct count while several thinking skills call it as a step; retire it and the routing calls silently fail until something downstream breaks. Before retiring anything, grep the other installed skills for its name, not just its invocation log.

**The case frequency cannot decide.** Both criteria come down to observable use, and neither separates *dead* from *rare by nature and high consequence when needed*: a pre-rebuild checklist, a recovery procedure, an annual audit. A low count looks identical either way, so a human judgement is required before retiring anything in that class; no counter supplies it.

For that class the answer is usually **neither install nor delete**. Keep it archived, tracked and runnable, and open the file when the moment comes. A process needed once every month or two is better as a plain document than a skill, because the document costs nothing on sessions that don't need it while a skill pays its description line on all of them. Reach for a skill when a process needs Claude to make judgment calls across several steps on a regular basis; reach for a doc for reference material consulted rarely.

**Match new corrections against the archive by lesson, not by name.** When a fresh correction comes in, check whether an archived feedback file already covers that lesson; if so the archival was premature and the rule should come back rather than be rewritten under a new name. Matching file names misses this every time, since the second occurrence of a lesson almost never arrives with the same wording. An archive nobody checks against is just a slower delete.

**Retiring from your own machine is not a reason to unpublish.** The counter informs only one of two different questions. Retirement asks "is this worth its description-line tax in every one of MY sessions", a fact about one person's habits. Publishing asks "would somebody with different repos and a different job find this valuable", which invocation counts say nothing about. A skill can be dead weight on the machine that wrote it and the most useful file in the library for the person who clones it. The only grounds for pulling something from a shared library are that it leaks something private, that the idea is actually wrong, or that the library's owner says so. "We stopped running it" is none of those, and the third is a decision rather than an inference.

**When a decision has a written rule, read the rule, not the record of past actions.** An archive index tells you what was done, never what should be done.

**And no sweep retires anything without the owner saying so.** Usage data is an input to that conversation, never the decision, because the counter cannot see the two cases that matter most: a skill other skills route into, and a skill rare by nature and high consequence when it fires. Both look like dead weight in the log. Propose the list, name the evidence for each, and let a human answer; retirement is cheap to defer and expensive to reverse, since what is really lost is not the file but the reason nobody wrote down.
