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

A data-correctness audit read a specific line: a configuration flag controlling a conditional code path, meant to decide whether an item had changed and needed reprocessing. It found a genuine defect on that exact line, a configuration boolean read by bare truthiness so that the string "false" turned the feature on. It reported it correctly.

Three days later a real user hit a different defect **on the same line**: the skip decided on version equality alone, so it never reprocessed an item the user had deleted locally.

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

**Cross-synthesise, cheapest of all.** Put two comparable things side by side and the differences generate the questions for free. Two repos, two modules, your tool and the real artefact it imitates, this pass and the last one. **Run it both ways or the better design loses to whichever side was audited most recently.** In one instance, comparing two sibling tools revealed that one keyed all its state by an immutable record identifier rather than by filename, and the other did not, which is exactly why the filename-keyed tool had forked a meaningful number of live records in ordinary use, and the identifier-keyed one structurally could not.

A winner decided is not a decision recorded. When the sweep concludes one design should replace the other, the losing design is usually just deleted with nothing recording what it was or why it lost, so the next parity sweep rediscovers the same divergence and re-argues it at full price. Write the losing design down at the moment of decision - what it did differently and the concrete reason it lost - because that is the only moment the reason is cheap to capture. In the case above the record would read: filename keying was simpler to read but forked on any rename; discarded in favour of identifier keying, which survives a rename by construction.

**Before a shared-risk operation with many consumers, build the consumer list from live state rather than from documentation, and gate the change one consumer at a time.** Documentation of dependents drifts the moment a new one is wired up, so a plan built from it routes around the consumers nobody wrote down. Enumerate from the running configuration, baseline a verification check against current state, then act on one consumer, confirm the gate held, and move to the next. In one credential rotation, enumerating from live configuration surfaced several undocumented consumers and at least two integrations already broken independent of the rotation, both invisible to a documentation-based plan.

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

### Validate your own probe, not only the tool

The two invalid instruments above are both about the thing being measured: the wrong entry point, the mismatched data shapes. There is a third case, distinct from both, and it is about the measuring apparatus itself rather than its target.

The instrument that needs checking first is usually the one you wrote thirty seconds ago. A composed shell probe reports on its LAST component, not on the thing you meant to measure: pipe, wrap, background or substitute a command and the status you read belongs to the wrapper. The number is real, plausible and about the wrong subject, which is the profile of a finding that survives review. Nobody validates a one-liner.

In one case, a check of whether a tool exits non-zero on bad input was written as the command piped into a truncating reader followed by an exit-code read. The status was the reader's, always success, so the tool was recorded as exiting clean on an input it had correctly rejected. The wrong conclusion was nearly published.

Two cheap rules. **One property per invocation**, nothing composed around it: run once with output discarded to read a status, again to read output. And **show the probe can return both answers before believing either**: point it at a case that must pass and one that must fail. A probe that has only ever produced one value has not been shown to measure anything, just as a test that has never failed has not been shown to assert anything.

**An intermittently flaky verification gate does not fail neutral - it destroys the ability to tell a real failure from noise, in both directions.** It trains everyone to wave off failures as "just flaky," burying the real ones it occasionally catches, and it manufactures failures unrelated to the change, burning time on regressions that never existed. Repair the gate's own reliability before trusting anything it reports. This is the staged-verification twin of validating the probe: a probe that measures the wrong thing and a gate that measures the right thing unreliably are the same failure at different points in the pipeline. In one case a verification call timed out against a fixed threshold shorter than the endpoint's real response time under load, producing false failures that looked exactly like the change breaking something.

### A liveness check is not a function check

A 200 from an unauthenticated health or liveness endpoint proves the network path exists, not that the authenticated function behind it works. Probe the actual authenticated call, not the endpoint that tells a load balancer the process has not crashed.

The inverse is easier to miss: no visible login form in a page's markup is not evidence of no authentication wall if the page is client-rendered. One security review nearly concluded a service had no auth wall because its health endpoint returned 200 and the initial markup had no login form; authentication was enforced client-side and only showed as a 401 on the call the page made after loading. Read the network traffic the page generates, not only the markup it ships.

### "Only" is a trigger word, not a conclusion

A hazardous or unusable first-found way to reach something is not proof there is no safe way. When a search stops at the first accessor, method or entry point and calls it the only one, it has stopped enumerating and started assuming. Interface dumps and member tables surface the sharpest-looking entries first, not because they are the only ones. In one case an SDK dump surfaced accessors hazardous enough to rule out on sight; the full member list held safe equivalents right next to them. Before writing "only", confirm the enumeration was exhaustive rather than merely unfinished. It is the coverage-pair discipline below applied to a single interface instead of a population of files.

### Two features each existing is not evidence they compose

Confirming capability A exists and capability B exists answers a narrower question than "does A feed B". Composition across components or vendors needs its own verification step. In one case a tool could filter records against a stored list and a separate scheduler could run rules on a timer, and the assumption was that the scheduler drove the filter engine; it had no way to invoke it. The two had been built and tested next to each other, never through each other. This is "operate the tool, do not read it" at a seam: only running the actual call across the boundary confirms the connection.

### State an exoneration at the scope you actually tested

A multi-component product (service plus interface plus browser extension, client plus server, CLI plus daemon) can have one layer cleared while another layer of the same product is the cause. Disabling a browser extension and seeing the symptom persist says nothing about the same software's desktop process, which can independently hold the resource.

Name the tested scope in the finding - "the extension is cleared", never "the software is cleared" - so the next investigator knows which layers remain unexamined.

### Severity and "patched" both depend on context you have to go check separately

Two checks from the security question, both about not trusting a label for the thing it claims to guarantee.

**Severity is vulnerability class multiplied by the privilege of the process running it, never the class alone.** "Remote code execution" describes the mechanism, not the blast radius; check what account the vulnerable process runs as before ranking. In one case an RCE in a subtitle-management tool running under a maximal system-level service account became "unauthenticated full host compromise".

**An enabled auto-updater is evidence of an update mechanism, never of being patched.** An updater can run faithfully while tracking a branch, channel or tag that never received the fix. Check which channel it tracks and whether that channel shipped the fix. In one audit a service's updater tracked a branch that never got a known fix, and a nearby container was pinned to a floating tag frozen since before the fix; both looked current from configuration alone.

## A verdict without a coverage figure cannot be told apart from one that examined nothing

An assertion over a corpus of files, records, log lines or sentences reports pass or fail, but it has examined only part of the corpus, because every assertion carries a parser, filter, minimum length or other structural exclusion. The fraction examined is almost never reported, so a green result is silent about whether it examined thoroughly and found nothing, or examined almost nothing. Both print "pass."

This is distinct from mutation testing. Mutation testing asks "can this assertion fail at all" (a property of its logic). Coverage asks "how much of the real population did this pass over" (a property of its reach, measured on an unmodified run). An assertion can survive every mutation and still examine almost nothing, because a parser regression or overzealous filter can silently shrink the population between runs.

Print a coverage figure alongside the verdict, as a raw pair rather than a percentage: units compared over the source population. This repo's cross-document duplication assertion does this - see `tools/selftest_dedup.py` - printing `coverage: N sentence(s) compared / M file(s) scanned` on both the passing and failing path. A raw pair invites "is that enough" against a corpus whose rough size you know; a percentage invites a target, and a target gets hit by whatever is cheapest.

Two payoffs. A parser regression that halves the analysable units leaves the verdict green while the printed number halves, the only place it is visible. And the figure is comparable across files and runs: one chapter yielding a handful of units where a similar chapter yields several times as many is itself a finding.

The counter-argument: printed numbers get optimised, and the cheapest way to raise coverage is to loosen the parser until it emits meaningless fragments, inflating numerator and denominator together. The figure must stay diagnostic, read by a human deciding whether a result is trustworthy, and never be gated on or treated as a target.

A checker's own subject list can go stale by the same shrinking-population mechanism, one level up. The coverage pair catches a corpus shrinking under a checker that scans everything it is told to; it misses a checker whose subject list (patterns, rules, paths) is a hand-maintained copy of a real list elsewhere. The copy stops updating when the real list changes, and the checker keeps passing while covering a shrinking fraction, invisible to the figure because it measures against the checker's own stale idea of the corpus. In one case a verifier's hardcoded pattern dictionary covered a small fraction of the real patterns while still reporting a clean pass. Derive the checker's subject list from the artefact at run time rather than restating a copy in its source.

## Correlated readers are not corroboration

Splitting a large reading job across parallel workers is right, but handing each the same list of "things already covered, skip these" destroys the property the parallelism was bought for. Agreement reads as corroboration but is not, if all were told the same thing: they agree because of the instruction, not the material. Their misses correlate too, clustering where the shared list was thin or wrong, which is where an independent second read pays most. A real instance had a hand-written shared skip list across eight parallel readers, and a couple of dozen already-covered items still came through, bunched in the same places.

Two acceptable shapes. Derive each worker's exclusion list independently and accept the duplicated effort, or keep the shared list and **state up front that overlap is expected and that agreement carries no evidential weight**. A shared list plus a coverage claim is not acceptable, because the claim then measures the list rather than the corpus.

The same applies to asking a second worker to check a first worker's output under the same brief. Independence is a property of the inputs, not of the process count.

## Four input states that masquerade as results

Any tool that measures by reading logs has an unchecked contract with them. It is tested against inputs its author constructed, which the author's assumptions held for. The failure is not a crash (a good outcome); each wrong-input state produces output that looks like a result, sometimes an interesting one, which is worse than looking clean because someone acts on it.

Four states, ordered by how convincing the output looks.

**ABSENT.** The log does not exist. Easy, usually handled, often the only one checked.

**EMPTY.** Exists, no rows. Must be reported distinctly from absent, because "nothing was recorded" and "nothing happened" are different facts and only one is good news. A tool returning zero for both reports the loop healthy when its instrumentation died. This is the log-level instance of the rule stated earlier for metrics: blank must fail the run as an explicit unknown, never pass as a suspiciously good zero.

**SATURATED.** The computation returned 0% or 100%. It produces a number, so it reads as a finding rather than a gap. Both extremes signal two populations that do not intersect. In one case a tool reported an entire rule corpus as never referenced, because the reference log tracked a different population and none of its entries could ever match. Check the intersection before giving an extreme a headline.

The population check is not only for extremes. Two ordinary-looking numbers in a plausible range give no warning, which is why they get trusted. The two-counters case under "Operate the tool, do not read it" was not saturated - a discrepancy across thousands of cycles, arithmetic sound - and survived many rounds because neither number looked like it needed questioning. Before trusting any comparison between two measurements, state in one sentence what population each counts and confirm the sentences describe the same population.

**NO YIELD.** Exists, has rows in range, and the parser extracted almost none because the format moved. The most dangerous, because it defeats the emptiness check (an unparseable full log yields the same row set as an empty one) and has the longest silent life: nothing errors, the file keeps growing, the metric reads clean indefinitely. In one case a log gained an extra field partway through its life and a parser written for the older shape reported an empty window over a file holding hundreds of in-window entries. Same shape as the headline count that equalled the number of log lines: confidently wrong rather than obviously missing.

A four-question check, about ten minutes for any tool. Does it distinguish absent from empty in the output a human reads, not just internally? On a 0% or 100% result, does anything verify the populations intersect? Does the parser compare its row count against a format-independent count of candidate lines (cheapest: lines matching only a date at the start)? Does each state cause a non-zero exit, or only a message, since a message in a log nobody reads is not a guard?

Each check needs a negative case or it fires on everything and is disabled within a week. Saturation needs three cases: 100% flags, 0% flags, and a genuine partial does not flag and exits clean. Yield needs a loose threshold (half is reasonable), because the check is for a collapse rather than a drift and a tight threshold over mixed historical formats fires constantly. The yield case must assert the absence of the emptiness message as well as the presence of the yield message, because the defect prevented is a misclassification rather than a silence.

Costless counter-measure: where a log's format may change, make the tolerant thing the parser and the strict thing the counter. Accept every historical shape you know, then compare against a count that does not depend on shape. The parser survives the format change and the counter tells you when a new one arrived.

Two more states. **TRUNCATED**: the log rotated or was capped, so the window holds less history than it claims and any per-window rate is wrong by an unknown factor; flag when the oldest in-window line is materially newer than the window start. **DUPLICATED**: the same event recorded twice, by two hooks or a re-run, inflating every count; check the exact-duplicate line proportion, where a non-trivial one is a writer defect. Both share the shape of the other four: confidently wrong rather than obviously missing.

**A list of things a human chose to block is not a list of things that are malicious.** Before turning a "blocked senders", "denied hosts" or similar human-curated rejection list into training data or a classifier rule, split it into structural-spam entries and real preference entries. "Blocked" records a convenience decision, not a malice verdict. One exported block list mixed many disposable-subdomain spam entries with real retail and brand domains the owner blocked purely because they did not want that mail; a classifier trained on it would have flagged legitimate senders as threats.

## A success signal proves acceptance, never effect

A 2xx response, a zero exit code, a green interface state or an enabled toggle all answer only "was the request accepted?", not whether the effect happened. This is distinct from the input states above and shows up well outside tooling.

Four shapes:

- **An endpoint can return a hardcoded success code regardless of whether the write took.** A `PUT` returning 202 on every call, including ones where the underlying write silently failed, is not hypothetical - it happened, and nothing in the response distinguished a real write from a no-op.
- **A polling or wait loop must report *why* it stopped waiting, not only that the awaited state never arrived.** "Timed out" and "the thing you are waiting for will never happen" are different facts wearing the same failure message.
- **A vendor interface showing "Done" can mean terminated, not succeeded.** A firmware updater presented three different completion-looking states, only one of which meant the update had applied, and the difference cost real time before it was understood.
- **A number on a page its operator can edit is not a measurement.** A goal or progress figure someone can set directly, rather than one derived from a source event, tells you what was typed, not what happened.

The common fix: find the independent artifact the effect should have produced - the row that should exist, the file that should be newer, the log line the vendor's own process writes - and check that instead of, or in addition to, the surface signal.

**A staged-rollout gate has its own version: writing it as elapsed time rather than as the observation being waited for.** "Wait 24 hours" is a proxy for "enough time for the real signal to arrive" and fails silently both ways, idling after the evidence arrived or moving on before it has. Write the gate as the thing itself - the log line, the metric crossing, the report landing. A duration is satisfied by the calendar, not produced by the system being watched. In one case the confirming evidence arrived within an hour; a 24-hour gate would have idled the other twenty-three for a reason unrelated to risk.

## Three outcomes need three exit states

A measurement tool (the duplication check, a coverage scan, any input-state guard above) has three outcomes needing different responses: measured and healthy (no action); measured and unhealthy (a real defect in the system under test); could not measure (absent log, saturated result, near-zero yield - investigate the instrument, not the system). Two exit codes collapse the last two into one non-zero exit, distinguishable only by reading the message.

That is tolerable only while a human reads every run, and fails once anything downstream consumes only the exit code (CI gate, cron alerting, status dashboard). The two carry opposite urgency: a real regression is usually gradual and survivable for a day, but a broken instrument silently invalidates every following run, including future runs that report healthy when the data drifts back into a plausible range by coincidence. A collapsed code also trains the reader that the tool always complains, so the first genuine regression arrives on a channel everyone discounts.

Use a third exit state: 0 measured-and-clean, 1 measured-with-findings, 2 could-not-measure. Every input-state classification above (absent, empty, saturated, no yield, truncated, duplicated) maps to exit 2, since each means the tool never got a trustworthy read. State the mapping in the tool's `--help` text, where a wrapper author reliably looks.

Counter-argument: exit 2 conventionally means "usage error" in some CLI traditions, a different meaning from "ran correctly but could not get a trustworthy read." Pick the mapping that suits the surrounding tooling, on purpose, and document it.

### The layer above can throw away a correct diagnosis

The harder version is when the tool gets it right and the layer consuming it destroys the distinction.

A status reporter built its line by running a budget checker and extracting percentages from its output with pattern matches. The checker behaved perfectly: unable to read its data source, it said so in plain words with a specific reason. Those words contained no percentages, so every match returned empty, and the reporter interpolated empty strings into its template and exited zero: a well-formed status line with blank fields and a success code. A blank looks like an answer. Sessions carried on entirely unmeasured, and the fault was noticed only when a person said they had never got a reading.

Three things generalise:

- **Extracting a value by pattern match needs an explicit missing case.** No match yields empty, and empty formats fine. Route it to could-not-measure, not into the template.
- **Pass the underlying reason through.** Discarding a good explanation and substituting silence is worse than no check, because it manufactures false confidence.
- **A diagnostic correct at every layer but the last is broken.** Audit the thing that renders the measurement, usually smaller, newer, considered trivial and untested, not the component that produces it.

Same family as an advisory routed to a channel nobody reads: a correct signal destroyed on the way to its audience, invisible from the generating component, so an audit scoped there will not enumerate either.

## Your own recent changes, as a subject

No round ever points anything at this, and it is high-yield ground.

Run a log of the last week's commits with file statistics and treat the changed-file list as the audit scope rather than the whole repo. For each changed file, list its callers and its state dependents, then ask which of those were re-tested. The answer is usually none.

**Hardening commits first.** Which recent commits were framed as fixes, guards, caps or safety, and what did each one break? A change framed as protective is the one whose author and reviewers are least likely to ask what it breaks, which makes hardening commits the highest-risk input to this subject rather than the safest. The worst defect in the case that produced this subject arrived inside a path-length hardening commit.

**Key-derivation changes are MIGRATIONS.** Did any recent change alter how a filename, slug, path or cache key is derived? If so, every record keyed by that value has forked, and the old records are still on disk under the old key. Grep the diff for changes to any sanitising, truncating or slugifying function, then ask what is keyed by its output. This one shape produced three separate defects in a single day across two tools.

**A cache, allowlist or trust decision keyed more broadly than the evidence that earned it silently admits everything else under that key.** When evidence justifies trusting one address, file or exact string and the decision is stored under a broader key (a whole domain, a whole path prefix), ask what else that key now covers before shipping. The broadening is rarely deliberate, just the more convenient data structure. One endorsed-senders list keyed by domain rather than address accidentally endorsed several major public mail providers. Ask "does this key admit anything I did not mean to admit" when the key is chosen, not after the list is too large to audit.

**Sweep merged pull requests for what they introduced.** Not a re-review of the author's judgement, a search for what got through. Read each pull request's own diff, never its description. For each behaviour added, ask what input class it now handles differently and whether that class previously worked. Across six merged pull requests this found one live regression no backlog held, and two more already fixed **after each had caused a real incident**. A fast-merged, clean-reviewed pull request can still ship data loss that only a real user finds.

**Distinguish a new feature under-delivering from a regression before ranking either.** A new check that is imperfect leaves every non-matching case no worse off. A changed behaviour can make a working case fail. Ask whether the previous code handled the failing input correctly; if there was no check at all before, it is not a regression however ugly it looks.

## Audit by Consequence, Not Only by File

A file-by-file audit and a consequence-first audit find different defects, and the second finds the dangerous ones. Reading every function surfaces what is wrong with code that is present. It does not reliably surface what is wrong with code that is missing, because an absent guard has no line to land on. The worst defects in a workflow tool live in the composition: a protection applied on only one path, a value rebuilt between two steps, an argument omitted under a condition.

Before an audit, write the two or three concrete bad outcomes in the user's terms (a wrong file moved, a wrong number believed, the job left half done) and file findings under those headings. Trace each outcome backwards through every branch that can reach it, including the branch where a protection is skipped because a condition was not met. Rank by consequence, not by how much code a finding touches, and run this pass separately from the file-by-file one. If the honest answer is that very little is at risk, say so plainly.

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

## After the pass: six steps, all learned by skipping them

1. **Check file ownership BEFORE assigning cells, not after reading the reports.** Four of one round's most severe findings could not be fixed because other people's open pull requests owned the files. That was knowable up front.
2. **A log-mined finding must be re-checked against CURRENT state before it is reported as live.** Logs are history. One round reported a configuration entry as broken for three weeks with forty-nine log files as evidence; the entry had already been removed and one grep of the current config disproved it. Cheapest check in this list.
3. **Expect a verification failure rate and budget for it.** In one round, two of seven agent reports contained at least one claim that did not reproduce: a dead import that had two real uses, and a timing figure roughly double the measured value. Both were confidently stated with plausible evidence. **A report's own confidence carries no information about which of its claims will hold**, so the triage pass is part of the work rather than a formality.
4. **Audit your own CAPTURE, as a separate step after the fixing.** One round's capture check found six findings that had been missed entirely, a better return than any single cell. Fixing is absorbing: items you act on get remembered and items you defer quietly evaporate into an agent report nobody reopens. Grep the backlog for a distinctive phrase from each finding rather than trusting recall.
5. **Update the coverage grid before closing the pass**, from verified results rather than from intent.
6. **Record a refuted hypothesis, not only a confirmed finding, before closing the pass.** A finding is written down because it gets fixed; an investigation that concluded "not true" usually leaves no trace, so the next pass forms the same hypothesis and pays the same cost to re-derive the same "no." A finding stops mattering once fixed, but a refutation stays true and keeps saving the investigation every round. Record one line per refutation: the hypothesis, how it was tested, what the test showed, and the date. The date matters because a refutation can expire when the code underneath changes; a dated one invites a re-test when it may have gone stale, an undated one is trusted past expiry or ignored. This complements the rule for untested capability limits - see [Part 15](15-verification-habits.md#re-test-inherited-constraints-before-planning-around-them) - which stops an untested guess hardening into fact; this stops a tested refutation evaporating unwritten.

## The prerequisite trap

The reason this framework nearly never got built. A staged improvement step was handed to two consecutive sessions, each told in the opening instruction that it was non-negotiable and first. Both went straight to the fix list. It sat undone for three days while roughly twenty defects were fixed around it.

**A prerequisite that produces nothing the main work consumes will be skipped, however emphatically it is ordered first.**

The cause and fix are structural, not a firmer instruction: **make the main pass itself the experiment that validates the prerequisite**, so the artefact becomes the pass's closing step rather than its entry fee. Half the failure was a self-contradictory instruction: it asked for the coverage grid before the pass, when the process requires building it afterwards from verified results. The sessions that skipped it were half right.

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

**Require every audit output to split its findings into those with a user-visible failure mode and those without.** It takes one line, it costs nothing, and it is the only thing standing between a finding count and an honest assessment of what the pass was worth.

## EXTREME lenses: forcing functions that re-rank

**These do not find new defects. They REORDER the ones you already have, and that is a different and often larger win.**

Every lens above answers "is there a defect here". These answer "given everything I know, what actually matters", by imposing a constraint severe enough that the honest answer changes. A backlog is a ranking, and **a ranking made under no constraint is mostly an artefact of the order things were found in.**

### The evidence this class is worth having

Two tool backlogs held 180 open items between them, already tiered by value across nine prior audit rounds. Asking one extreme question, *what would you fix if you could never touch this repo again*, promoted a bottom-tier item to first place: an item whose failure mode was silent, irreversible loss of a person's own work, with no trace and no confirmation.

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
