# Part 23: When To Stop Refining

> **Field note.** Written from practice rather than machine-checked.

Every deep dive finds something. That is a property of looking, not evidence that the work is unfinished: a fresh lens on any artefact of useful size always turns up another issue, so "no more findings" is a target that is never reached. Without a stopping rule, refinement runs until the budget or the reader gives out, and the last rounds cost the most while changing the least. This part gives the rule for deciding that a body of work is finished enough to use.

## Why the loop never ends

Three things keep it open.

- **Findings are unbounded, importance is not.** The tenth round surfaces real issues, but they are smaller than the first round's. Counting findings measures effort; ranking them measures progress.
- **Each fix is a new change to audit.** A round that edits ten files creates ten files' worth of new surface, so a fix-and-recheck loop can feed itself indefinitely (see [Part 15](15-auditing-your-own-changes.md)).
- **Lenses multiply.** Every new angle in [Part 13](13-audit-lenses.md) is another full pass. Completeness across all angles is unreachable by design; the grid is a menu, not a checklist to finish.

## The stopping test

Stop a refinement run when any one of these holds, and say which one in the record.

1. **Severity floor.** The last round's best finding is below the bar you set at the start (cosmetic, no reader would be misled, nothing breaks). Set the bar before the round, not after seeing the findings.
2. **Diminishing returns.** Two consecutive rounds each produced fewer and smaller findings than the one before, and neither produced a finding that changed a decision.
3. **Fresh-reader pass.** A reader with no context can use the artefact for its stated purpose without being misled. This is the test that matters; the others are proxies for it.
4. **Budget.** The time or usage allotted at the start is spent. Spending the allotment is a valid stop even with findings left, provided the remainder is written down.
5. **Deadline.** Something downstream (a release, a review, a hand-off) needs the artefact now, and the known issues are not blockers.

## Set the bar before you start

Write three lines before the first round: the purpose ("a stranger can adopt this without help"), the severity floor ("blocks use or misleads"), and the budget ("three rounds"). A stop decided after seeing results drifts toward "one more round"; a stop decided before cannot.

## What to do with what is left

Stopping is not discarding. Every finding below the line goes to the backlog with its severity, in the form [Part 3](03-ideas-and-roadmap.md) describes, so the next run starts from the list instead of rediscovering it. Findings that keep recurring in the same shape are a signal to mechanise the check ([Part 2](02-improvement-loop.md)) rather than to run more manual rounds; that is the productive way to keep finding fewer.

## Round shape that converges

- **Rank, then fix from the top.** Fix the highest-severity findings first and stop fixing when the next one is below the floor, even if more are known.
- **Cap the round.** A fixed number of findings per round (or per lens) prevents one noisy lens from dominating.
- **Audit the fixes once, not forever.** Re-check the files a round touched with the same tests that guard them (a suite, a linter, a broken-link check). Do not open a new open-ended audit of the fixes.
- **Prefer a check to a pass.** A finding class that a script can catch is closed for good; a finding class that needs a human pass will be back.

## Signs you are past the point

- Findings are rephrasings of ones already in the backlog.
- Fixes are wording changes with no reader-visible effect.
- Each round's report is longer than its fixes.
- The reason for another round is "to be thorough" rather than a named risk.

When two of these show up, stop, record the remainder, and ship.

## Related

- [Part 13: Audit Lenses](13-audit-lenses.md) for the angles that generate findings.
- [Part 15: Auditing Your Own Changes](15-auditing-your-own-changes.md) for why each round creates new surface.
- [Part 2: The Improvement Loop](02-improvement-loop.md) for turning recurring findings into checks.
- [Part 3: Ideas and Roadmap](03-ideas-and-roadmap.md) for where deferred findings go.
