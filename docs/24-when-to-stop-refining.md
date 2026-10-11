# Part 24: When To Stop Refining

> **Field note.** Written from practice rather than machine-checked.

Any piece of work can be improved a little more, and looking harder usually finds something, so "nothing left to improve" is a poor finish line: it is rarely reached, and the rounds spent chasing it cost the most while changing the least. This part gives a stopping rule for any task (coding, research, writing, refactoring, debugging, design, planning, audits), for a team or one person alone.

The rule has two halves. Before you start, write down what done means. After each round, check a small set of tests and stop when the core ones say stop. Whatever is left gets recorded, not dropped.

## Why refinement does not end on its own

- **Improvements are unbounded, value is not.** Later rounds still find real things, but they matter less than the early ones. Counting what a round found measures effort; asking what it changed measures progress.
- **Each fix is a new change to check.** A fix-then-recheck loop can feed itself ([Part 16](16-auditing-your-own-changes.md)).
- **Angles multiply.** Every new way of looking at the work (the lenses in [Part 14](14-audit-lenses.md) are one menu) is another full pass. Covering every angle is not reachable; pick the ones that match the risks.
- **Nobody else says stop.** With no reviewer or deadline, the task ends where you are tired of it, not where it is good.

## Set the stop criteria before you start

Write a few lines before the first round, in the task note, ticket or prompt. A stop decided after seeing results drifts toward "one more round".

1. **Done, as a check you can run.** Something answerable yes or no: "the import handles the three sample files and the suite passes", "a newcomer installs the tool from the doc without asking anything", "I can name the root cause and reproduce the bug on demand". If you cannot phrase done as a check, the task is not defined yet.
2. **The value floor.** The smallest kind of issue still worth fixing this pass: for code "wrong behaviour or a missing test", not naming style; for writing "a reader would be misled or stuck", not word choice. Below the floor, record, do not fix.
3. **The cost of being wrong.** One line on what happens if a defect survives; a throwaway script and a migration deserve different floors. This sets how strict the tests are.
4. **Optional: a time box,** as a prompt to run the stopping test, not an order to stop.

Four lines is enough; longer and the criteria become a thing to refine.

## The stopping test

After each round, read the core tests together; they do not all have to pass.

### Core tests (every task)

1. **Done check passes.** The primary test. If it passes and the others are quiet, stop. If it fails, keep going whatever the others say, unless you change the criterion and write down why.
2. **Nothing above the floor is left.** Rank what you know and look at the top item only: if that is not worth fixing now, nothing below it is.
3. **The last round changed little.** Judge by what it changed, not what it found. Rewording, renaming and fixes nobody would notice are a strong signal; a changed decision, behaviour or result is not. Two such rounds in a row is a clear stop.
4. **A fresh reader or real use agrees.** Someone or something without your context uses the work for its purpose: a colleague reads the doc, a new assistant session follows the instructions, the script runs on real input, the fix survives the original reproduction. Solo, that can be yourself after a break, a clean checkout, or a new session given only the artefact.
5. **More work would cost more than the risk it removes.** Use the cost line from the start. Easy to undo (local refactor, draft, revertible config): stop earlier. Hard to undo (published data, deleted file, migration, sent message): raise the floor and keep checking.

### Optional tests (only when they exist)

- **Time box spent.** A trigger to run the core tests honestly, not to stop by itself; if the done check still fails, continue or shrink the scope deliberately.
- **Budget spent.** Running out ends the session, not the task. Record where you are so the next session resumes.
- **Deadline.** If something downstream genuinely needs the work now, ship once the known issues are not blockers, and record them. Do not invent a deadline.

Write down which test ended the run: "Stopped: done check passed, last round was wording only" is useful; "felt done" is not.

## When someone says keep going

The owner of the work may be right. Handle it without giving in or arguing from habit.

1. **Show where you are against the criteria:** the done check, the top remaining item, what the last round changed.
2. **Ask what is still wrong.** A concrete problem was above the floor all along, or the done check missed something: add it to the criterion and continue.
3. **If they name no problem,** offer one more bounded round on a named area, or stop and record the remainder. Avoid an unbounded "keep improving"; it has no finish line.
4. **The owner decides.** Make the trade visible, not win it. If they raise the bar, write the new bar down.

The same applies to an assistant working for you: give it written stop criteria up front and ask it to report which test ended the run, which prevents both early "done" claims and endless polishing.

## What to do with what is left

Stopping is not discarding. Known issues below the line go to the backlog with a short note on why they matter and how big they are ([Part 3](03-ideas-and-roadmap.md)). If the same kind of issue keeps turning up, turn the check into a script, test or hook ([Part 2](02-improvement-loop.md)) instead of running more manual rounds; a mechanised check keeps catching that class.

## Worked examples

**A bug fix.** Done: the reported input no longer crashes, a regression test reproduces the original crash and passes, and the root cause fits in one sentence. Floor: wrong behaviour. Cost of error: medium. Round one removes the crash but the cause is a guess, so the done check fails and work continues. Round two finds the cause and adds the test; done passes. Two tidy-ups nearby are below the floor and go to the backlog. A suspicion that a similar path has the same bug is above the floor, so it gets one bounded look (a quick test, which passes). Stop: "done check passed, nothing above floor".

**A README for a personal tool.** Done: someone who has never seen the project installs and runs the main command from the README alone. Floor: a reader gets stuck or misled. Cost: low. Time box: two rounds. Round two is mostly rewording. A fresh assistant session given only the README and a clean folder gets the tool running. Stop; the urge to restructure the page goes to the backlog.

**A refactor.** Done: the module is split into the three planned files, all tests pass, and no caller imports from the old path (a missed caller breaks only at run time, so the import check is part of done). Round two fixes two missed callers found by searching for the old path. Round three starts renaming internal variables: below the floor and invisible to users. That is the signal; commit and record the ideas.

## Round shape that converges

- **Rank, then work from the top,** and stop when the next item is below the floor even if more are known.
- **Bound each round** (one area, one lens, a fixed number of items) so one noisy area cannot absorb the session.
- **Check the fixes once, with existing checks:** re-run the tests, linters or link checks covering what changed, not a new open-ended review.
- **Prefer a check to a pass.** A class a script can catch stays caught; a class needing a person to look comes back.

## Signs you are past the point

- New findings are rephrasings of recorded items.
- Changes are wording or naming nobody would notice.
- Describing a round takes longer than the round's changes.
- The reason for another round is "to be thorough" rather than a named risk or a failing done check.

Any one of these is a prompt to run the stopping test again, honestly.

## Related

- [Part 2: The Improvement Loop](02-improvement-loop.md) for turning recurring findings into checks.
- [Part 3: Ideas and Roadmap](03-ideas-and-roadmap.md) for where the remainder goes.
- [Part 14: Audit Lenses](14-audit-lenses.md) for the angles that generate findings.
- [Part 16: Auditing Your Own Changes](16-auditing-your-own-changes.md) for why each round creates new surface.
