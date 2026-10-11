# Part 15: Reading a Measurement Before Trusting It

> **Field note.** Written from practice rather than machine-checked.

A tool, probe or signal can emit something shaped exactly like a measurement while having measured nothing. This part is about deciding whether a number, status or clean result can be believed: run the thing instead of reading it, check the instrument before the subject, know the input states that masquerade as results, and keep a success signal separate from the effect it claims. The lens generator that tells you what to examine is in [Part 14](14-audit-lenses.md); this part is about what to do with what comes back.

## Operate the tool, do not read it

**If the thing runs, run it before you read it.** This is the first lens to reach for on anything with an executable form, and it is not the same activity as imagining a user.

One short real invocation on real data, small enough that every printed number can be checked by hand, returned five findings that many prior reading-based rounds had gone past. It also **disproved the premise of a sixth**, the lens's strongest credential. A discrepancy quantified across more than two thousand log cycles, arithmetically sound and confidently reported, was a category error: two counters with plausible names measured different populations and were never required to agree. One entry that downloaded zero items and processed one settled it in a single line of real output.

So reading-based auditing does not merely miss things. It manufactures confident, quantified, false findings that survive review because the arithmetic checks out. Any finding derived purely from logs or source stays a hypothesis until something runs.

Four questions to ask of a real run:

- **Does each printed number equal what you can count yourself?** Real finds: a headline count that equalled the number of log lines rather than the sum of anything processed; a "Warnings: 0" printed six lines below a real warning; a "3 warnings, full detail in the log file" where the log file held no detail.
- **Does a printed count measure what its NAME says?** Trace every count and duration back to what it increments.
- **Does a BOUND remove real data on an ordinary run?** Find every threshold that drops, skips or truncates, then check the real corpus for what it catches. One three-hundred-character bound dropped three real records in a nine-second run, two at identical sizes, which reveals a shared template and makes the population measurable.
- **A warning that fires is not a warning that HELPS.** A filename-collision warning fired correctly on two real records, and both still mapped to one filename, so the second silently claimed the first's state. The warning shipped. The data loss did not stop.

Reading and operating are different activities, and a reading-based pass is not sufficient alone. A colleague using a tool in ordinary daily work reported four defects on the same day a multi-agent audit of the same code produced twenty-six findings, and the intersection was empty. Partial overlap would be a coverage gap; zero overlap means the two processes ask structurally different questions. Ask of any pass reporting a large count how many findings a user could ever reach: there, the unreachable categories were unjustified-constant and comment-narrative items, real maintainability work with no user-visible failure mode that should not count at the yield of a data-loss finding. Require every audit output to split its findings into those with a user-visible failure mode and those without. It takes one line and is the only thing standing between a finding count and an honest assessment of what the pass was worth.

## Validate the instrument before the subject

**Step one is always validation of the instrument.** Two earlier attempts at one kind of measurement produced clean-looking and invalid results: one called the wrong entry point, so the path under test never ran, and one compared two data structures whose element shapes differed between versions, yielding a confident and meaningless delta. Confirm the measurement exercises the path it claims to, and that both sides of a before-and-after comparison are the same shape.

The instrument that needs checking first is usually the one you wrote thirty seconds ago. A composed shell probe reports on its LAST component: pipe, wrap, background or substitute a command and the status you read belongs to the wrapper. The number is real, plausible and about the wrong subject. A check of whether a tool exits non-zero on bad input, written as the command piped into a truncating reader followed by an exit-code read, reports the reader's status (always success) and records the tool as exiting clean on an input it correctly rejected.

Two cheap rules. **One property per invocation**, nothing composed around it: run once with output discarded to read a status, again to read output. And **show the probe can return both answers before believing either**: point it at a case that must pass and one that must fail. A probe that has only ever produced one value has not been shown to measure anything, just as a test that has never failed has not been shown to assert anything.

**An intermittently flaky verification gate does not fail neutral.** It trains everyone to wave off failures as "just flaky", burying the real ones it occasionally catches, and manufactures failures unrelated to the change. Repair the gate's own reliability before trusting anything it reports. In one case a verification call timed out against a fixed threshold shorter than the endpoint's real response time under load, producing false failures that looked exactly like the change breaking something.

### A liveness check is not a function check

A 200 from an unauthenticated health endpoint proves the network path exists, not that the authenticated function behind it works. Probe the actual authenticated call.

The inverse is easier to miss: no visible login form in a page's markup is not evidence of no authentication wall if the page is client-rendered. One security review nearly concluded a service had no auth wall because its health endpoint returned 200 and the markup had no login form; authentication was enforced client-side and showed only as a 401 on the call the page made after loading. Read the network traffic the page generates, not only the markup it ships.

### "Only" is a trigger word, not a conclusion

A hazardous first-found way to reach something is not proof there is no safe way. A search that stops at the first accessor or entry point and calls it the only one has stopped enumerating and started assuming; interface dumps surface the sharpest-looking entries first. In one case an SDK dump surfaced accessors hazardous enough to rule out on sight; the full member list held safe equivalents right next to them. Before writing "only", confirm the enumeration was exhaustive rather than merely unfinished.

### State an exoneration at the scope you actually tested

A multi-component product (service plus interface plus browser extension, client plus server) can have one layer cleared while another is the cause. Disabling a browser extension and seeing the symptom persist says nothing about the same software's desktop process. Name the tested scope in the finding ("the extension is cleared", never "the software is cleared") so the next investigator knows which layers remain unexamined.

## Four input states that masquerade as results

Any tool that measures by reading logs has an unchecked contract with them, tested only against inputs its author constructed. The failure is not a crash (a good outcome); each wrong-input state produces output that looks like a result, which is worse than looking clean because someone acts on it. Ordered by how convincing the output looks:

**ABSENT.** The log does not exist. Easy, usually handled, often the only one checked.

**EMPTY.** Exists, no rows. Must be reported distinctly from absent, because "nothing was recorded" and "nothing happened" are different facts and only one is good news. A tool returning zero for both reports the loop healthy when its instrumentation died. Blank must fail the run as an explicit unknown, never pass as a suspiciously good zero.

**SATURATED.** The computation returned 0% or 100%. It produces a number, so it reads as a finding rather than a gap. Both extremes signal two populations that do not intersect: one tool reported an entire rule corpus as never referenced, because the reference log tracked a different population and none of its entries could match. Check the intersection before giving an extreme a headline. The check is not only for extremes: two ordinary-looking numbers in a plausible range give no warning, which is why they get trusted. The two-counters case above was not saturated and survived many rounds. Before trusting any comparison between two measurements, state in one sentence what population each counts and confirm the sentences describe the same population.

**NO YIELD.** Exists, has rows in range, and the parser extracted almost none because the format moved. The most dangerous, because it defeats the emptiness check (an unparseable full log yields the same row set as an empty one) and has the longest silent life: nothing errors, the file keeps growing, the metric reads clean indefinitely. One log gained an extra field partway through its life and a parser written for the older shape reported an empty window over a file holding hundreds of in-window entries.

A four-question check, about ten minutes for any tool. Does it distinguish absent from empty in the output a human reads? On a 0% or 100% result, does anything verify the populations intersect? Does the parser compare its row count against a format-independent count of candidate lines (cheapest: lines starting with a date)? Does each state cause a non-zero exit, or only a message, since a message in a log nobody reads is not a guard?

Each check needs a negative case or it fires on everything and is disabled within a week. Saturation needs three cases: 100% flags, 0% flags, and a genuine partial does not flag and exits clean. Yield needs a loose threshold (half is reasonable), because the check is for a collapse rather than a drift. The yield case must assert the absence of the emptiness message as well as the presence of the yield message, because the defect prevented is a misclassification rather than a silence. Where a log's format may change, make the tolerant thing the parser and the strict thing the counter: accept every historical shape you know, then compare against a count that does not depend on shape. The parser survives the format change and the counter tells you when a new one arrived.

Two more states are confidently wrong rather than obviously missing. **TRUNCATED**: the log rotated or was capped, so the window holds less history than it claims and any per-window rate is wrong by an unknown factor; flag when the oldest in-window line is materially newer than the window start. **DUPLICATED**: the same event recorded twice, by two hooks or a re-run, inflating every count; check the exact-duplicate line proportion, where a non-trivial one is a writer defect.

**A list of things a human chose to block is not a list of things that are malicious.** Before turning a human-curated rejection list into training data or a classifier rule, split structural-spam entries from real preference entries. One exported block list mixed many disposable-subdomain spam entries with real retail and brand domains the owner blocked only because they did not want that mail; a classifier trained on it would have flagged legitimate senders as threats.

## A verdict without a coverage figure cannot be told apart from one that examined nothing

An assertion over a corpus reports pass or fail, but every assertion carries a parser, filter, minimum length or other structural exclusion, so it has examined only part of the corpus. The fraction examined is almost never reported, so a green result is silent about whether it examined thoroughly and found nothing, or examined almost nothing. Both print "pass."

This is distinct from mutation testing, which asks "can this assertion fail at all" (a property of its logic). Coverage asks "how much of the real population did this pass over" (a property of its reach, measured on an unmodified run). An assertion can survive every mutation and still examine almost nothing, because a parser regression or overzealous filter can silently shrink the population between runs.

Print a coverage figure alongside the verdict, as a raw pair rather than a percentage: units compared over the source population. This repo's cross-document duplication assertion does this (see `tools/selftest_dedup.py`), printing `coverage: N sentence(s) compared / M file(s) scanned` on both the passing and failing path. A raw pair invites "is that enough" against a corpus whose rough size you know; a percentage invites a target, and a target gets hit by whatever is cheapest. A parser regression that halves the analysable units leaves the verdict green while the printed number halves, the only place it is visible. And the figure is comparable across files and runs: one chapter yielding a handful of units where a similar chapter yields several times as many is itself a finding.

The counter-argument: printed numbers get optimised, and the cheapest way to raise coverage is to loosen the parser until it emits meaningless fragments, inflating numerator and denominator together. The figure must stay diagnostic, read by a human deciding whether a result is trustworthy, never gated on or treated as a target.

A checker's own subject list can go stale by the same mechanism, one level up. The coverage pair catches a corpus shrinking under a checker that scans everything it is told to; it misses a checker whose subject list (patterns, rules, paths) is a hand-maintained copy of a real list elsewhere. The copy stops updating and the checker keeps passing while covering a shrinking fraction. One verifier's hardcoded pattern dictionary covered a small fraction of the real patterns while reporting a clean pass. Derive the subject list from the artefact at run time rather than restating a copy in source.

## A success signal proves acceptance, never effect

A 2xx response, a zero exit code, a green interface state or an enabled toggle answers only "was the request accepted?", not whether the effect happened. Four shapes:

- **An endpoint can return a hardcoded success code regardless of whether the write took.** A `PUT` returning 202 on every call, including ones where the underlying write silently failed, is not hypothetical.
- **A polling or wait loop must report *why* it stopped waiting.** "Timed out" and "the thing you are waiting for will never happen" are different facts wearing the same failure message.
- **A vendor interface showing "Done" can mean terminated, not succeeded.** A firmware updater presented three completion-looking states, only one of which meant the update had applied.
- **A number on a page its operator can edit is not a measurement.** A goal or progress figure someone can set directly tells you what was typed, not what happened.

The common fix: find the independent artefact the effect should have produced (the row that should exist, the file that should be newer, the log line the vendor's own process writes) and check that instead of, or in addition to, the surface signal.

**A staged-rollout gate has its own version: writing it as elapsed time rather than as the observation being waited for.** "Wait 24 hours" is a proxy for "enough time for the real signal to arrive" and fails silently both ways, idling after the evidence arrived or moving on before it has. Write the gate as the thing itself: the log line, the metric crossing, the report landing.

Two labels that need the same check. **Severity is vulnerability class multiplied by the privilege of the process running it, never the class alone.** "Remote code execution" describes the mechanism, not the blast radius; an RCE in a subtitle-management tool running under a maximal system-level service account became "unauthenticated full host compromise". **An enabled auto-updater is evidence of an update mechanism, never of being patched.** It can run faithfully while tracking a branch, channel or tag that never received the fix. In one audit a service's updater tracked a branch that never got a known fix, and a nearby container was pinned to a floating tag frozen since before the fix; both looked current from configuration alone.

## Three outcomes need three exit states

A measurement tool has three outcomes needing different responses: measured and healthy (no action); measured and unhealthy (a real defect in the system under test); could not measure (absent log, saturated result, near-zero yield: investigate the instrument, not the system). Two exit codes collapse the last two into one non-zero exit, distinguishable only by reading the message.

That is tolerable only while a human reads every run, and fails once anything downstream consumes only the exit code (CI gate, cron alerting, dashboard). The two carry opposite urgency: a real regression is usually gradual and survivable for a day, but a broken instrument silently invalidates every following run, including future runs that report healthy when the data drifts back into a plausible range by coincidence. A collapsed code also trains the reader that the tool always complains.

Use a third exit state: 0 measured-and-clean, 1 measured-with-findings, 2 could-not-measure. Every input-state classification above maps to exit 2, since each means the tool never got a trustworthy read. State the mapping in the tool's `--help` text, where a wrapper author reliably looks. Exit 2 conventionally means "usage error" in some CLI traditions, so pick the mapping that suits the surrounding tooling, on purpose, and document it.

### The layer above can throw away a correct diagnosis

The harder version is when the tool gets it right and the layer consuming it destroys the distinction. A status reporter builds its line by running a budget checker and extracting percentages with pattern matches. Unable to read its data source, the checker says so in plain words with a specific reason. Those words contain no percentages, so every match returns empty, and the reporter interpolates empty strings into its template and exits zero: a well-formed status line with blank fields and a success code. A blank looks like an answer, and sessions carry on entirely unmeasured.

- **Extracting a value by pattern match needs an explicit missing case.** No match yields empty, and empty formats fine. Route it to could-not-measure, not into the template.
- **Pass the underlying reason through.** Discarding a good explanation and substituting silence manufactures false confidence.
- **A diagnostic correct at every layer but the last is broken.** Audit the thing that renders the measurement, usually smaller, newer, considered trivial and untested, not the component that produces it.

This is the same family as an advisory routed to a channel nobody reads: a correct signal destroyed on the way to its audience, invisible from the generating component.
