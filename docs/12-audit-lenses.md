# Part 12: Audit Lenses

> **Field note.** Written from practice rather than machine-checked. Last reviewed 2026-08-02.

An audit finds what its questions allow it to find. Most audits ask one question repeatedly, in more and more detail, and conclude the artefact is clean. This part is about generating the questions before you start scanning, and about recording coverage in a form that lets the next pass start wider instead of starting over.

## The problem, stated precisely

A lens that is not on the list does not get applied by being thorough.

In one recorded case, four parallel audits, a security readiness pass, a documentation parity pass, a failure-mode analysis and a month of log review all missed that five tests held seventy percent of one test suite's runtime. Every one of those passes was a correctness lens. None of them was wrong. The runtime was simply not a question any of them asked, and no amount of additional care within a correctness lens would ever have surfaced it.

**Breadth of lens beats depth within one.** That is the whole claim, and everything below is machinery for getting breadth without turning the audit into an unbounded list of things to check.

## How completeness works: the generator is bounded, the list is not

The obvious failure of a checklist like this is that it grows forever and nobody can say when it is finished. That question has no answer while the list is the unit, because any artefact admits endlessly many questions. So the completeness claim lives one level up.

**Two axes generate the lenses. The axes are a small fixed set. The lenses are not.**

- **SUBJECT**, what you point the lens at: product code, tests, the instrument, config, data and output, docs, the usage surface, dependencies and platform, history and process, your own recent changes, and the audit itself.
- **QUESTION**, what you ask of it: is it CORRECT, does it FAIL SAFELY, is it HONEST (does the claim match reality), is it CONSISTENT, is it USABLE, is it FAST ENOUGH, is it SECURE, and what is MISSING.

**A pass is complete when every cell has either a named lens being applied or a stated reason it is empty or not applicable.** Not when the list stops growing. Most cells will be empty for any given pass and that is fine. What is not fine is never having looked at the cell.

### The rule that makes re-auditing principled rather than wasteful

**A subject examined under one QUESTION has not been examined under another.**

"We already audited the code" is not a reason to skip the code. Coverage is a property of cells, never of subjects, so the honest unit of "we have looked at this" is `product code x fails safely`, not `product code`. Seven rounds in one project read the same source repeatedly and every round found new defects, because each was pointed at a slightly different question and mostly at the same one.

**The corollary is the most reliable prediction this framework makes: the cells nobody has walked are where the defects are.** Not the hard cells. The unwalked ones. When a round finds a cluster of defects in an area that has been audited four times already, look at which question is newly being asked. That is what found them, not extra diligence.

## The coverage grid, and why it needs three states

Record what you walked. A grid of subjects against questions, with four marks:

- `Y` walked, and holding.
- `W` **walked but proven weak: a defect escaped this cell.**
- `.` open, never walked.
- `-` not applicable.

**`W` is worse news than `.` and must never be quietly restored to `Y`.** An open cell is an honest gap that the next round will look at. A `Y` standing next to a defect that escaped it is a false signal that stops the next round looking at all. This compounds: the grid is what every subsequent round loads to decide where to look, so one flattering mark misdirects all of them, not only the round that wrote it. A `W` is cleared only by a pass that states what it changed about the lens, not by walking the cell again with the same question.

**Build the grid from verified results, at the END of a pass.** Never from intent at the start. See "The prerequisite trap" below for what happens when you try.

### Worked example of a cell being walked, producing a true finding, and still being too weak

This is the sharpest single data point the framework has, and it is what `W` exists for.

A data-correctness audit read a specific line of a synchronisation tool: the check that decides whether a remote item has changed and needs re-downloading. It found a genuine defect on that exact line, a configuration boolean read by bare truthiness so that the string "false" turned the feature on. It reported it correctly.

Three days later a real user hit a different defect **on the same line**: the skip decides on version equality alone, so it never re-downloads a file the user has deleted locally.

The lens was not absent. The line was not unread. The question asked of it was "is this value parsed correctly", and the defect answered to "can this decision lose data". Same subject, same line, different question, and the audit had no way to see it.

## Which questions pay best

Measured across eight rounds, in descending yield:

1. **HONEST** (the claim does not match the code) and **MISSING** (nothing is wrong, something is absent). The two richest, and the two least natural to ask.
2. **FAILS SAFELY.**
3. **USABLE.** Never asked at all until round eight, and it immediately produced defects in the artefacts with the largest audience.
4. **CORRECT.** The most-asked and by now the most exhausted.

Bias a new pass toward HONEST, MISSING and USABLE. Treat a round that is mostly CORRECT as a round that will confirm what the last one said.

## Three generators, in increasing cheapness

**The matrix**, above. Walk the cells.

**Walk the PEOPLE.** Who else touches this and what do they see? A first-time user. A security reviewer. Someone debugging at two in the morning with only the log. A packager. Someone on the other operating system. Someone with narrower permissions than you. The team inheriting it. Yourself in a year. Each is a lens, and the people axis catches things the subject axis words too neutrally.

**Cross-synthesise, cheapest of all.** Put two comparable things side by side and the differences generate the questions for free. Two repos, two modules, your tool and the real artefact it imitates, this pass and the last one. **Run it both ways or the better design loses to whichever side was audited most recently.** In one instance, comparing two sibling tools produced four defects in one and, more valuably, revealed that the other keyed all its state by an immutable record identifier rather than by filename, which is exactly why one of them had forked forty-three live records and the other structurally could not.

## Operate the tool, do not read it

**If the thing runs, run it before you read it.** This is the first lens to reach for on anything with an executable form, and it is not the same activity as imagining a user.

One short real invocation on real data, small enough that every printed number can be checked by hand, returned five findings that many prior reading-based rounds had gone past. It also **disproved the premise of a sixth**, and that is the lens's strongest credential. A discrepancy quantified across more than two thousand log cycles, arithmetically sound and confidently reported, turned out to be a category error: two counters with plausible names measured different populations and were never required to agree. One entry that downloaded zero items and processed one settled it in a single line of real output.

**So reading-based auditing does not merely miss things. It manufactures confident, quantified, false findings that survive review because the arithmetic checks out.** A finding derived purely from logs or source is a hypothesis until something runs.

**Step one is always validation of the instrument**, before any measurement is trusted. Two earlier attempts at this kind of measurement produced clean-looking and entirely invalid results: one called the wrong entry point, so the code path under test was never exercised, and one compared two data structures whose element shapes differed between versions, yielding a confident and meaningless delta. Confirm the measurement exercises the path it claims to, and that both sides of any before-and-after comparison are the same shape. Skip this and the lens manufactures false confidence rather than findings.

Four questions to ask of a real run:

- **Does each printed number equal what you can count yourself?** Real finds: a headline count that equalled the number of log lines rather than the sum of anything processed; a "Warnings: 0" printed six lines below a real warning; a "3 warnings, full detail in the log file" where the log file held no detail at all.
- **Does a printed count measure what its NAME says?** Trace every count and duration back to what it actually increments.
- **Does a BOUND remove real data on an ordinary run?** Find every threshold that drops, skips or truncates, then check the real corpus for what it actually catches. One three-hundred-character bound dropped three real records in a nine-second run, two of them at identical sizes, which reveals a shared template rather than a coincidence and makes the population measurable.
- **A warning that fires is not a warning that HELPS.** When a new guard fires on real input, ask whether it also fixes anything. A filename-collision warning fired correctly on two real records, and both still mapped to one filename, so the second silently claimed the first's state. The warning shipped. The data loss did not stop.

## Your own recent changes, as a subject

No round ever points anything at this, and it is high-yield ground.

Run a log of the last week's commits with file statistics and treat the changed-file list as the audit scope rather than the whole repo. For each changed file, list its callers and its state dependents, then ask which of those were re-tested. The answer is usually none.

**Hardening commits first.** Which recent commits were framed as fixes, guards, caps or safety, and what did each one break? A change framed as protective is the one whose author and reviewers are least likely to ask what it breaks, which makes hardening commits the highest-risk input to this subject rather than the safest. The worst defect in the case that produced this subject arrived inside a path-length hardening commit.

**Key-derivation changes are MIGRATIONS.** Did any recent change alter how a filename, slug, path or cache key is derived? If so, every record keyed by that value has forked, and the old records are still on disk under the old key. Grep the diff for changes to any sanitising, truncating or slugifying function, then ask what is keyed by its output. This one shape produced three separate defects in a single day across two tools.

**Sweep merged pull requests for what they introduced.** Not a re-review of the author's judgement, a search for what got through. Read each pull request's own diff, never its description. For each behaviour added, ask what input class it now handles differently and whether that class previously worked. Across six merged pull requests this found one live regression no backlog held, and two more already fixed **after each had caused a real incident**. A pull request that merges fast and reviews clean can still ship data loss that only a real user finds.

**Distinguish a new feature under-delivering from a regression before ranking either.** A new check that is imperfect leaves every non-matching case no worse off. A changed behaviour can make a working case fail. Ask whether the previous code handled the failing input correctly; if there was no check at all before, it is not a regression however ugly it looks.

## How to walk a cell

One read-only agent per cell, or per subject where its open questions are related. The prompt that works has five parts, and dropping any one measurably degrades the result.

1. **Name the cell explicitly and fence it.** "You are assigned SUBJECT x QUESTION. Do not report correctness bugs, that is another cell." Without the fence, every agent drifts to correctness, because correctness is what auditing feels like.
2. **State what a prior round already found in that area and declare it out of scope**, so the agent hunts new ground instead of rediscovering a fixed defect and reporting it as live.
3. **Demand a method, not a verdict.** Normalise and count rather than eyeball. Run the real thing rather than read it. Give real numbers with their source, never an impression.
4. **Require the clean answer.** "State explicitly which parts came back CLEAN. Do not manufacture findings." An agent with no permission to find nothing will invent something, and that noise costs more to triage than the real findings are worth.
5. **Require file and line for every claim**, both for the claim and for the evidence. A finding you cannot verify in one jump is a finding you will not verify.

Then **verify before acting**. Every report is a claim. Reproduce the consequential ones yourself. An agent has already recommended documenting an output artefact that the tool had stopped producing, which would have shipped the exact defect its own pass existed to remove.

## How to run a pass

1. **Generate lenses before scanning.** Generating lenses and generating findings are different activities, and doing the first one first is what breaks out of the previous pass's blind spot. Walk the matrix, walk the people, cross-synthesise.
1b. **If the thing runs, operate it before reading it.** One small real invocation, every printed number checked by hand, instrument validated first.
2. **Rank the candidates by expected yield, then say plainly which you are NOT applying and why.** A skipped lens with a reason is a decision. An unlisted lens is a blind spot.
3. **One read-only agent per lens, in parallel.** A cheaper model does the reading; you keep the judgement, verify, fix and commit.
4. **Give every agent the irreversibility framing.** "If we could never change this file again, what MUST be fixed now?" Ranks by consequence rather than by count.
4b. **Close the pass by running ONE extreme lens over the resulting BACKLOG, not over the code.** See the next section. Cheapest step in the process and the only one that improves items you are not touching.
5. **Require agents to say plainly when a dimension is clean**, to cite file and line, and to prefer a cheap reproduction over a read-only inference.
6. **Verify every finding before acting on it.**

## After the pass: five steps, all learned by skipping them

1. **Check file ownership BEFORE assigning cells, not after reading the reports.** Four of one round's most severe findings could not be fixed because other people's open pull requests owned the files. That was knowable up front.
2. **A log-mined finding must be re-checked against CURRENT state before it is reported as live.** Logs are history. One round reported a configuration entry as broken for three weeks with forty-nine log files as evidence; the entry had already been removed and one grep of the current config disproved it. Cheapest check in this list.
3. **Expect a verification failure rate and budget for it.** In one round, two of seven agent reports contained at least one claim that did not reproduce: a dead import that had two real uses, and a timing figure roughly double the measured value. Both were confidently stated with plausible evidence. **A report's own confidence carries no information about which of its claims will hold**, so the triage pass is part of the work rather than a formality.
4. **Audit your own CAPTURE, as a separate step after the fixing.** One round's capture check found six findings that had been missed entirely, a better return than any single cell. Fixing is absorbing: items you act on get remembered and items you defer quietly evaporate into an agent report nobody reopens. Grep the backlog for a distinctive phrase from each finding rather than trusting recall.
5. **Update the coverage grid before closing the pass**, from verified results rather than from intent.

## The prerequisite trap

Worth stating on its own, because it is the reason this framework nearly never got built.

A staged improvement step was handed to two consecutive sessions. Both were told in their opening instruction that it was non-negotiable and first. Both went straight to the fix list. It sat undone for three days while roughly twenty defects were fixed around it.

**A prerequisite that produces nothing the main work consumes will be skipped, however emphatically it is ordered first.**

The cause is structural rather than a discipline problem, and so is the fix. It is not a firmer instruction. It is to **make the main pass itself the experiment that validates the prerequisite**, so the artefact becomes the pass's closing step rather than its entry fee. Half the failure in this case was that the instruction was self-contradictory: it asked for the coverage grid to be written before the pass, when the same process requires the grid be built afterwards from verified results. The sessions that skipped it were half right.

## Sharpening prompts, once you are inside a cell

These do not generate new cells. They make a cell productive.

- What is true only at a BOUNDARY? Empty input, exactly one item, the very first run, the very last item, a resumed run, a clock change, a timezone that is not yours.
- What does this ASSUME about its environment that is never checked?
- Which failure here would be SILENT rather than loud, and which would be found by a user rather than by a test?
- What is untestable by construction, and what compensates for it?
- What did the last three passes' own fixes introduce?

## The inverse question, and the honest limit

Of the findings produced by reading-based auditing, how many could only ever have been found that way, and would a user ever actually hit them?

Ask it of any pass that reports a large finding count. In one twenty-six-finding pass, the categories a user could never reach were unjustified-constant items and comment-narrative items: real maintainability work with no user-visible failure mode. That is not wasted, but it should not be counted against the same yield as a data-loss finding, and a pass reporting a large count should say how many of its findings any user could ever reach.

**The single hardest result this framework has produced about itself.** On one day, a colleague using a tool in ordinary daily work reported four defects. The same day, a multi-agent audit of the same code produced twenty-six findings. The intersection was empty. A coverage gap between two processes examining one artefact would show partial overlap; zero overlap means the two are asking structurally different questions, and at least one of them is systematically unable to see what the other sees.

Reading and operating are not the same activity. This framework makes reading much better. It does not make reading sufficient.

### Say How Many of Your Findings a User Could Ever Reach

A pass that reports twenty-six findings sounds better than one that reports four. It may be worse.

Of one twenty-six-finding pass, the categories no user could ever hit were unjustified-constant items and comment-narrative items: real maintainability work with no user-visible failure mode. That work is worth doing and it should not be counted against the same yield as a finding that loses someone's data.

**Require every audit output to split its findings into those with a user-visible failure mode and those without.** It takes one line, it costs nothing, and it is the only thing standing between a finding count and an honest assessment of what the pass was worth.

## EXTREME lenses: forcing functions that re-rank

**These do not find new defects. They REORDER the ones you already have, and that is a different and often larger win.**

Every lens above answers "is there a defect here". These answer "given everything I know, what actually matters", by imposing a constraint severe enough that the honest answer changes. A backlog is a ranking, and **a ranking made under no constraint is mostly an artefact of the order things were found in.**

### The evidence this class is worth having

Two tool backlogs held 180 open items between them, already tiered by value across nine prior audit rounds. Asking one extreme question, *what would you fix if you could never touch this repo again*, promoted a bottom-tier item to first place: an override flag that silently overwrote hand-edited files, destroying a person's work with no trace and no confirmation.

It had been read past by nine rounds and correctly tiered as polish under the question "how valuable is this". Under the question "what is unrecoverable" it is the single most important item in either repo.

**Nothing was learned about the code. The ranking was simply wrong, and one sentence fixed it.**

### How to use them

Pick one. Apply it to the **whole backlog** rather than to the source. Write down what moved.

If nothing moves, the ranking was already sound and that is a real result worth recording, not a failed pass.

**Do not run more than two per pass.** Their value is in forcing a hard choice, and a pass that runs eight of them is back to unconstrained listing.

**One caution before you use these in company.** Several of these framings sharpen your own judgement and read badly in a shared artefact. "Imagine we can never change this again" or "what would we regret shipping" in a pull request comment reads as catastrophising rather than as analysis. Use them to arrive at the finding, then state the finding neutrally.

### The lenses

| Lens | The constraint | Why it re-ranks | Status |
|---|---|---|---|
| **Irreversibility** | *If we could never change this file again, what MUST be fixed now?* | Ranks by consequence rather than by count or by ease. The default for anything heading to wide release, an upstream merge or an ownership transfer. | Validated repeatedly |
| **Code frozen, docs open** | *The code is frozen. The documentation is not. What must the docs now SAY?* | The sharpest of the class, because it partitions the backlog cleanly. Anything a user can route around once TOLD becomes a documentation task, and only what destroys something before they can be told stays a code task. It also converts an undocumented destructive flag from a polish item into the last line of defence. | Validated, produced the promotion described above |
| **Blast radius already spent** | *This defect has been live for a year. How many records are ALREADY wrong?* | Converts a code question into a corpus measurement, and the number usually decides the priority by itself. Measured instances: 300 files carrying an unmarked section, 43 forked records, 57 drifted filenames, 520 stranded entries. **A defect with a blast radius of zero can wait however ugly the code is; one with 300 cannot, and reading the code tells you neither.** | Validated |
| **Assume every green is a false green** | *Every passing test and every clean measurement is lying. Prove one isn't.* | Inverts the burden of proof onto the instrument. One session produced four instances: a test asserting via the very helper it was testing, a probe truthiness-testing a tuple, a probe bypassing the test package's dependency stand-ins, and a claim built on console output mistaken for a log file. | Validated |
| **The environment you cannot test** | *This code only ever runs somewhere you have no access to. What does your suite actually prove?* | Any dependency faked locally makes local tests evidence about the fake. A destructive decision behind a faked parser is validated nowhere. Forces guards to be expressed in terms the local environment CAN exercise. | Validated, changed a guard's implementation |
| **Hostile input, informed attacker** | *Assume every externally-supplied string was chosen by someone who has read your source.* | Narrower and more productive than a generic security pass, because it starts from the real list of externally-controlled values rather than from a threat catalogue. Attachment filenames chosen by an outside party is not hypothetical, and it is what turned a byte-versus-character length cap from a curiosity into a real data-loss defect. | Validated |
| **One commit only** | *You get exactly ONE commit, then the repo closes. Which?* | Forces a single choice where a tier list lets you defer. What you pick reveals what you actually believe, and the gap between it and your current top item is the size of the ranking error. | Untried |
| **Delete it, do not fix it** | *This subsystem must be REMOVED, not repaired. What breaks, and who complains?* | The engineering algorithm's Delete step as an audit lens. Answers whether a feature earns its keep, and exposes coupling no correctness pass surfaces. Cheapest possible outcome, because a deleted subsystem needs no further audit ever. | Untried |
| **Total context loss** | *You vanish tonight. Someone inherits this with no history, no backlog and no access to you.* | Distinct from "the team inheriting it" on the people axis, which assumes a handover. This assumes none, so it targets what is UNDISCOVERABLE rather than what is undocumented: reasoning that exists only in a commit message, a constant whose basis was measured and never written down, a workaround whose deletion looks like a cleanup. | Untried |
| **The source is gone** | *The upstream this mirrors no longer exists. The local copy is all there is.* | For any tool that syncs, caches or mirrors, this flips which side is authoritative and re-ranks every "we can just re-fetch" dismissal. Several deletions judged safe BECAUSE the data is regenerable stop being safe the moment the source is deleted upstream, which for a mirror is a normal event rather than a catastrophe. | Untried |
| **The rushed expert** | *Not a first-time user. A competent one, in a hurry, on the worst day, who reaches for the override flag.* | The people axis tends to imagine the careful newcomer, who reads warnings. The person who actually loses data is the one who knows enough to pass the force flag and not enough to know what it skips. Ranks destructive-flag ergonomics above first-run ergonomics. | Untried |

### The pattern that generates more of these

Take any comfortable assumption the backlog rests on and **negate it absolutely, not partially.**

- "We can fix it later" becomes never.
- "We can re-fetch it" becomes the source is gone.
- "The tests pass" becomes every green is false.
- "A user will read the warning" becomes they are in a hurry and already typed the flag.
- "Someone will explain this" becomes there is nobody left to ask.

**A partial negation ("what if the source were slow") changes nothing. A total one ("what if the source were gone") changes the order.** That is the whole trick, and it is why these are worth writing down separately from the finding lenses.
