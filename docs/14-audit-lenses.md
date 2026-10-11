# Part 14: Audit Lenses

> **Field note.** Written from practice rather than machine-checked.

An audit finds what its questions allow it to find. Most audits ask one question repeatedly, in more and more detail, and conclude the artefact is clean. This part is about generating the questions before you start scanning, recording coverage so the next pass starts wider instead of starting over, and running the pass. Two sibling parts cover what comes after a lens is applied: [Part 15](15-reading-a-measurement.md) on deciding whether a measurement can be believed, and [Part 16](16-auditing-your-own-changes.md) on auditing recent changes and the way correct parts compose into a wrong whole.

## The problem, stated precisely

A lens that is not on the list does not get applied by being thorough. In one recorded case, four parallel audits (a security readiness pass, a documentation parity pass, a failure-mode analysis and a month of log review) all missed that five tests held seventy percent of one test suite's runtime. Every pass was a correctness lens and none was wrong; runtime was simply not a question any of them asked, and no extra care within a correctness lens would have surfaced it.

**Breadth of lens beats depth within one.** That is the whole claim; everything below is machinery for getting breadth without an unbounded list of things to check.

## How completeness works: the generator is bounded, the list is not

Any artefact admits endlessly many questions, so a checklist grows forever and nobody can say when it is finished. The completeness claim lives one level up, with the generator.

**Two axes generate the lenses. The axes are a small fixed set. The lenses are not.**

- **SUBJECT**, what you point the lens at: product code, tests, the instrument, config, data and output, docs, the usage surface, dependencies and platform, history and process, your own recent changes, and the audit itself.
- **QUESTION**, what you ask of it: is it CORRECT, does it FAIL SAFELY, is it HONEST (does the claim match reality), is it CONSISTENT, is it USABLE, is it FAST ENOUGH, is it SECURE, and what is MISSING.

**A pass is complete when every cell has either a named lens being applied or a stated reason it is empty or not applicable.** Not when the list stops growing. Most cells will be empty for any given pass; what is not fine is never having looked.

**A subject examined under one QUESTION has not been examined under another.** "We already audited the code" is not a reason to skip the code. Coverage is a property of cells, never of subjects: the honest unit is `product code x fails safely`, not `product code`. A project that read the same source over seven rounds found new defects every round, because each round pointed at a slightly different question.

The framework's most reliable prediction: the cells nobody has walked are where the defects are. Not the hard cells, the unwalked ones. When a round finds a cluster of defects in an area audited four times already, look at which question is newly being asked; that found them, not extra diligence.

## The coverage grid, and why it needs three states

Record what you walked as a grid of subjects against questions, with four marks:

- `Y` walked, and holding.
- `W` **walked but proven weak: a defect escaped this cell.**
- `.` open, never walked.
- `-` not applicable.

**`W` is worse news than `.` and must never be quietly restored to `Y`.** An open cell is an honest gap the next round will look at. A `Y` standing next to a defect that escaped it is a false signal that stops the next round looking at all, and since every later round loads the grid to decide where to look, one flattering mark misdirects all of them. A `W` is cleared only by a pass that states what it changed about the lens, not by walking the cell again with the same question. Build the grid from verified results at the END of a pass, never from intent at the start (see "After the pass").

A worked example of a cell being walked, producing a true finding, and still being too weak: a data-correctness audit read a configuration flag controlling a conditional code path that decided whether an item needed reprocessing. It found a genuine defect on that line (the flag was read by bare truthiness, so the string "false" turned the feature on) and reported it. Three days later a real user hit a different defect on the same line: the skip decided on version equality alone, so it never reprocessed an item the user had deleted locally. The question asked was "is this value parsed correctly"; the defect answered to "can this decision lose data". Same subject, same line, different question. That is what `W` exists for.

## Which questions pay best

In descending yield:

1. **HONEST** (the claim does not match the code) and **MISSING** (nothing is wrong, something is absent): the richest, and the least natural to ask.
2. **FAILS SAFELY.**
3. **USABLE:** rarely asked at all, and it produces defects in the artefacts with the largest audience.
4. **CORRECT:** the most-asked and by now the most exhausted.

Bias a new pass toward HONEST, MISSING and USABLE; a round that is mostly CORRECT will confirm what the last one said.

## Three generators, in increasing cheapness

**The matrix**, above. Walk the cells.

**Walk the PEOPLE.** Who else touches this and what do they see? A first-time user, a security reviewer, someone debugging at two in the morning with only the log, a packager, someone on the other operating system, someone with narrower permissions than you, the team inheriting it, yourself in a year. The people axis catches things the subject axis words too neutrally.

**Cross-synthesise, cheapest of all.** Put two comparable things side by side (two repos, two modules, your tool and the real artefact it imitates, this pass and the last) and the differences generate the questions for free. **Run it both ways or the better design loses to whichever side was audited most recently.** In one instance, comparing two sibling tools showed one keyed all its state by an immutable record identifier rather than by filename, which is exactly why the filename-keyed tool had forked a meaningful number of live records in ordinary use and the identifier-keyed one structurally could not.

A winner decided is not a decision recorded. The losing design is usually just deleted with nothing recording what it was or why it lost, so the next parity sweep re-argues the same divergence at full price. Write the losing design down at the moment of decision, the only moment the reason is cheap to capture ("filename keying was simpler to read but forked on any rename; discarded for identifier keying, which survives a rename by construction").

**Before a shared-risk operation with many consumers, build the consumer list from live state rather than from documentation, and gate the change one consumer at a time.** Documentation of dependents drifts the moment a new one is wired up, so a plan built from it routes around the consumers nobody wrote down. Enumerate from the running configuration, baseline a verification check against current state, then act on one consumer, confirm the gate held, and move to the next. In one credential rotation, enumerating from live configuration surfaced several undocumented consumers and at least two integrations already broken independent of the rotation.

## EXTREME lenses: forcing functions that re-rank

**These do not find new defects. They REORDER the ones you already have, often a larger win.** The generators above answer "is there a defect here"; these answer "given everything I know, what actually matters", by imposing a constraint severe enough that the honest answer changes. A backlog is a ranking, and **a ranking made under no constraint is mostly an artefact of the order things were found in.**

A backlog already tiered by value across many rounds can still be wrong. Asking *what would you fix if you could never touch this repo again* can promote a bottom-tier item to first place: one whose failure mode is silent, irreversible loss of a person's own work, with no trace and no confirmation. Under "how valuable is this" it reads as polish; under "what is unrecoverable" it is the most important item in the repo. Nothing is learned about the code; the ranking was simply wrong.

Pick one lens, apply it to the **whole backlog** rather than to the source, and write down what moved. If nothing moves, the ranking was already sound, a real result worth recording. **Do not run more than two per pass:** their value is in forcing a hard choice, and a pass running eight is back to unconstrained listing.

Several of these framings sharpen your judgement and read badly in a shared artefact ("what would we regret shipping" in a pull request comment reads as catastrophising). Use them to arrive at the finding, then state the finding neutrally.

| Lens | The constraint | Why it re-ranks | Status |
|---|---|---|---|
| **Irreversibility** | *If we could never change this file again, what MUST be fixed now?* | Ranks by consequence rather than by count or ease. The default for anything heading to wide release, an upstream merge or an ownership transfer. | Validated repeatedly |
| **Code frozen, docs open** | *The code is frozen. The documentation is not. What must the docs now SAY?* | The sharpest of the class, because it partitions the backlog cleanly. Anything a user can route around once TOLD becomes a documentation task; only what destroys something before they can be told stays a code task. It also converts an undocumented destructive flag from a polish item into the last line of defence. | Validated |
| **Blast radius already spent** | *This defect has been live for a year. How many records are ALREADY wrong?* | Converts a code question into a corpus measurement, and the number usually decides the priority. **A defect with a blast radius of zero can wait however ugly the code is; one with hundreds of affected records cannot, and reading the code tells you neither.** | Validated |
| **Assume every green is a false green** | *Every passing test and every clean measurement is lying. Prove one isn't.* | Inverts the burden of proof onto the instrument. Typical finds: a test asserting via the very helper it was testing, a probe truthiness-testing a tuple, a probe bypassing the test package's dependency stand-ins, a claim built on console output mistaken for a log file. | Validated |
| **The environment you cannot test** | *This code only ever runs somewhere you have no access to. What does your suite actually prove?* | Any dependency faked locally makes local tests evidence about the fake; a destructive decision behind a faked parser is validated nowhere. Forces guards to be expressed in terms the local environment CAN exercise. | Validated |
| **Hostile input, informed attacker** | *Assume every externally-supplied string was chosen by someone who has read your source.* | Narrower and more productive than a generic security pass, because it starts from the real list of externally-controlled values. Attachment filenames chosen by an outside party turn a byte-versus-character length cap from a curiosity into a real data-loss defect. | Validated |
| **One commit only** | *You get exactly ONE commit, then the repo closes. Which?* | Forces a single choice where a tier list lets you defer; the gap between it and your current top item is the size of the ranking error. | Untried |
| **Delete it, do not fix it** | *This subsystem must be REMOVED, not repaired. What breaks, and who complains?* | The engineering algorithm's Delete step as an audit lens. Answers whether a feature earns its keep, exposes coupling no correctness pass surfaces, and a deleted subsystem needs no further audit ever. | Untried |
| **Total context loss** | *You vanish tonight. Someone inherits this with no history, no backlog and no access to you.* | Distinct from "the team inheriting it", which assumes a handover. This targets what is UNDISCOVERABLE rather than undocumented: reasoning that exists only in a commit message, a constant whose basis was measured and never written down, a workaround whose deletion looks like a cleanup. | Untried |
| **The source is gone** | *The upstream this mirrors no longer exists. The local copy is all there is.* | For any tool that syncs, caches or mirrors, this flips which side is authoritative and re-ranks every "we can just re-fetch" dismissal. Deletions judged safe BECAUSE the data is regenerable stop being safe once the source is deleted upstream, a normal event for a mirror. | Untried |
| **The rushed expert** | *Not a first-time user. A competent one, in a hurry, on the worst day, who reaches for the override flag.* | The people axis tends to imagine the careful newcomer, who reads warnings. The person who loses data knows enough to pass the force flag and not enough to know what it skips. Ranks destructive-flag ergonomics above first-run ergonomics. | Untried |

To generate more, take any comfortable assumption the backlog rests on and **negate it absolutely, not partially.**

- "We can fix it later" becomes never.
- "We can re-fetch it" becomes the source is gone.
- "The tests pass" becomes every green is false.
- "A user will read the warning" becomes they are in a hurry and already typed the flag.
- "Someone will explain this" becomes there is nobody left to ask.

**A partial negation ("what if the source were slow") changes nothing. A total one ("what if the source were gone") changes the order.**

## How to walk a cell

One read-only agent per cell, or per subject where its open questions are related. The prompt that works has five parts; dropping any one measurably degrades the result.

1. **Name the cell explicitly and fence it.** "You are assigned SUBJECT x QUESTION. Do not report correctness bugs, that is another cell." Without the fence every agent drifts to correctness, because that is what auditing feels like.
2. **State what a prior round already found in that area and declare it out of scope,** so the agent hunts new ground instead of reporting a fixed defect as live.
3. **Demand a method, not a verdict.** Normalise and count rather than eyeball; run the real thing rather than read it; give real numbers with their source, never an impression.
4. **Require the clean answer.** "State explicitly which parts came back CLEAN. Do not manufacture findings." An agent with no permission to find nothing will invent something, and that noise costs more to triage than the real findings are worth.
5. **Require file and line for every claim,** for the claim and for the evidence. A finding you cannot verify in one jump is one you will not verify.

Inside a cell, these prompts make the walk productive: What is true only at a BOUNDARY (empty input, exactly one item, the first run, the last item, a resumed run, a clock change, a timezone that is not yours)? What does this ASSUME about its environment that is never checked? Which failure here would be SILENT rather than loud, and found by a user rather than a test? What is untestable by construction, and what compensates? What did the last three passes' own fixes introduce?

## How to run a pass

1. **Generate lenses before scanning.** Generating lenses and generating findings are different activities, and doing the first first is what breaks out of the previous pass's blind spot. Walk the matrix, walk the people, cross-synthesise.
2. **If the thing runs, operate it before reading it.** One small real invocation, every printed number checked by hand, instrument validated first ([Part 15](15-reading-a-measurement.md#operate-the-tool-do-not-read-it)).
3. **Rank the candidates by expected yield, then say plainly which you are NOT applying and why.** A skipped lens with a reason is a decision. An unlisted lens is a blind spot.
4. **One read-only agent per lens, in parallel.** A cheaper model does the reading; you keep the judgement, verify, fix and commit. When the readers share an exclusion list, read [Correlated readers are not corroboration](16-auditing-your-own-changes.md#correlated-readers-are-not-corroboration) first.
5. **Give every agent the irreversibility framing** ("If we could never change this file again, what MUST be fixed now?"), and require them to say plainly when a dimension is clean, to cite file and line, and to prefer a cheap reproduction over a read-only inference.
6. **Verify every finding before acting on it.** Every report is a claim, so reproduce the consequential ones yourself. An agent has recommended documenting an output artefact the tool had stopped producing, which would have shipped the exact defect its pass existed to remove.
7. **Close the pass by running ONE extreme lens over the resulting BACKLOG, not over the code.** Cheapest step in the process and the only one that improves items you are not touching.

## After the pass: six steps, all learned by skipping them

1. **Check file ownership BEFORE assigning cells, not after reading the reports.** Four of one round's most severe findings could not be fixed because other people's open pull requests owned the files, which was knowable up front.
2. **A log-mined finding must be re-checked against CURRENT state before it is reported as live.** Logs are history. One round reported a configuration entry as broken for three weeks with forty-nine log files as evidence; the entry had already been removed and one grep of the current config disproved it.
3. **Expect a verification failure rate and budget for it.** In one round, two of seven agent reports contained at least one claim that did not reproduce: a dead import that had two real uses, and a timing figure roughly double the measured value, both confidently stated with plausible evidence. **A report's own confidence carries no information about which of its claims will hold,** so triage is part of the work.
4. **Audit your own CAPTURE, as a separate step after the fixing.** One round's capture check found six findings missed entirely, a better return than any single cell. Fixing is absorbing: items you act on get remembered and items you defer evaporate into an agent report nobody reopens. Grep the backlog for a distinctive phrase from each finding rather than trusting recall.
5. **Update the coverage grid before closing the pass,** from verified results rather than intent. A prerequisite that produces nothing the main work consumes will be skipped however emphatically it is ordered first (structural fix: [Part 2](02-improvement-loop.md#why-the-step-you-ordered-first-keeps-getting-skipped)), so make the grid the closing step built from verified results, not the entry fee.
6. **Record a refuted hypothesis, not only a confirmed finding.** A finding is written down because it gets fixed; an investigation that concluded "not true" usually leaves no trace, so the next pass forms the same hypothesis and pays the same cost to re-derive the same "no". Record one line per refutation: the hypothesis, how it was tested, what the test showed, and the date. The date matters because a refutation can expire when the code underneath changes; a dated one invites a re-test, an undated one is trusted past expiry or ignored. This complements the rule for untested capability limits ([Part 19](19-verification-habits.md#re-test-inherited-constraints-before-planning-around-them)), which stops an untested guess hardening into fact; this stops a tested refutation evaporating unwritten.
