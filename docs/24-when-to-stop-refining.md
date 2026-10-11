# Part 24: When To Stop Refining

> **Field note.** Written from practice rather than machine-checked.

Any piece of work can be improved a little more. Code can be cleaner, a document clearer, a design more general, a bug investigation deeper, a plan more detailed. Looking harder usually finds something, so "nothing left to improve" is a poor finish line: it is rarely reached, and the rounds spent chasing it tend to cost the most while changing the least. This part gives a stopping rule that works for any task (coding, research, writing, refactoring, debugging, design, planning, cleanup, audits) and for one person working alone on a personal project as well as for a team.

The rule has two halves. Before you start, write down what done means. While you work, check a small set of tests after each round and stop when the core ones say stop. Whatever is left gets recorded, not dropped.

## Why refinement does not end on its own

- **Improvements are unbounded, value is not.** Later rounds still find real things, but on most tasks they matter less than the early ones. Counting what a round found measures effort; asking what it changed measures progress.
- **Each fix is a new change to check.** Editing ten files creates ten files of new surface, so a fix-then-recheck loop can feed itself ([Part 16](16-auditing-your-own-changes.md) covers why).
- **Angles multiply.** Every new way of looking at the work (the lenses in [Part 13](13-audit-lenses.md) are one menu of them) is another full pass. Covering every angle is not a reachable goal; pick the ones that match the risks.
- **Nobody else says stop.** On a personal project there is often no reviewer, release date or manager. If you do not set the stop, the task sets it for you, usually at the point where you are tired of it rather than where it is good.

## Set the stop criteria before you start

Write a few lines before the first round, in the task note, the ticket, the commit plan or the prompt you give an assistant. A stop decided after seeing results drifts toward "one more round"; a stop decided beforehand does not.

1. **Done, as a check you can run.** State what done looks like as something you can answer yes or no to. "The import handles the three sample files and the test suite passes." "The doc lets a newcomer install the tool without asking anything." "I can name the root cause and reproduce the bug on demand." "The plan lists every step with an owner and a first action." If you cannot phrase done as a check, the task is not defined yet; fix that before refining anything.
2. **The value floor.** Name the smallest kind of issue still worth fixing in this pass. For code it might be "wrong behaviour or a missing test", not naming style. For writing, "a reader would be misled or stuck", not word choice. Below the floor, things get recorded, not fixed.
3. **The cost of being wrong.** One line on what happens if a defect survives. A throwaway script and a database migration deserve different floors. This line sets how strict the other tests are.
4. **Optional: a time box.** If you tend to over-polish, give the task a number of rounds or a block of time. This is a prompt to run the stopping test, not an order to stop (see below).

Four lines is enough. Longer than that and the criteria themselves become a thing to refine.

## The stopping test

After each round, check the core tests. They do not all have to pass; read them together.

### Core tests (apply to every task)

1. **Done check passes.** The criterion written at the start is met. This is the primary test. If it passes and the others are quiet, stop. If it fails, keep going no matter what the others say, unless you decide to change the criterion (and write down why).
2. **Nothing above the floor is left.** The best remaining known issue is below the value floor. Rank what you know about and look at the top item only: if that one is not worth fixing now, nothing below it is either.
3. **The last round changed little.** Judge the round by what it changed, not how much it found. A round that only produced rewording, renaming, or fixes nobody would notice is a strong signal. A round that changed a decision, a behaviour or a result is not. Two rounds in a row that changed little is a clear stop.
4. **A fresh reader or real use agrees.** Someone (or something) without your context uses the work for its purpose: a colleague reads the doc, a new session of an assistant follows the instructions, the script runs on real input, the fix survives the original reproduction. If they succeed without getting stuck or misled, the work is fit for use. For a solo project, "fresh reader" can be yourself after a break, a clean checkout, or a new assistant session given only the artefact.
5. **More work would cost more than the risk it removes.** Compare the cost of another round with the cost of a surviving defect, using the line you wrote at the start. When the work is easy to undo (a local refactor under version control, a draft, a config you can revert), a surviving issue is cheap and you should stop earlier. When it is hard to undo (published data, a deleted file, a migration, a message already sent), raise the floor and keep checking.

### Optional tests (use only when they exist)

- **Time box spent.** Useful as a trigger to step back and run the core tests honestly. Spending the box does not by itself mean stop; on personal work the box often runs out with the done check still failing, and the right move is to continue or to shrink the scope deliberately, not to drift on.
- **Budget spent.** If you work against a hard usage or money limit, running out ends the session but not the task. Record where you are so the next session resumes rather than restarts.
- **Deadline.** If something downstream genuinely needs the work now (a release, a review, a hand-off to someone else), ship once the known issues are not blockers and record them. Many personal projects have no deadline; do not invent one.

Write down which test ended the run. "Stopped: done check passed, last round was wording only" is a useful record. "Stopped: felt done" is not.

## When someone says keep going

Often the person who wants more is the owner of the work (you, a user, a client), and they may be right. Handle it without either giving in or arguing from habit.

1. **Show where you are against the criteria.** Report the done check, the top remaining item and what the last round changed. This turns "keep going" into a conversation about the bar, not about effort.
2. **Ask what is still wrong.** If they name a concrete problem, it was above the floor all along, or the done check was missing something. Add it to the criterion and continue.
3. **If they want more without naming a problem,** offer a choice: one more bounded round on a named area, or stop and record the remainder. Either is fine; an unbounded "keep improving" is the one option to avoid, because it has no finish line.
4. **The owner decides.** If it is their project, they set the bar. Your job is to make the trade visible, not to win it. If they raise the bar, write the new bar down so the next stop is judged against it.

The same applies when an assistant is working for you. Giving it written stop criteria up front, and asking it to report which test ended the run, prevents both early "done" claims and endless polishing.

## What to do with what is left

Stopping is not discarding. Every known issue below the line goes to the backlog with a short note on why it matters and how big it is, in the form [Part 3](03-ideas-and-roadmap.md) describes, so the next session starts from the list instead of rediscovering it. If the same kind of issue keeps turning up, that is a sign to turn the check into a script, test or hook ([Part 2](02-improvement-loop.md)) rather than to run more manual rounds. A mechanised check keeps catching that class for as long as it runs, which is the productive way to find fewer things next time.

## Worked examples

**A bug fix (debugging).** Before starting: done is "the reported input no longer crashes, a regression test reproduces the original crash and now passes, and I can state the root cause in one sentence". Floor: "wrong behaviour", not "I would have written this function differently". Cost of error: medium, it ships to users. After round one the crash is gone but the root cause is a guess. The done check fails, so continue. Round two finds the real cause and adds the test. The done check passes. The remaining items are two tidy-ups in nearby code and a suspicion that a similar path has the same bug. The tidy-ups are below the floor and go to the backlog. The suspicion is above the floor (possible wrong behaviour), so it gets one bounded look: a quick test of the similar path, which passes. Stop, recorded as "done check passed, nothing above floor".

**A README for a personal tool (writing).** Before starting: done is "someone who has never seen the project can install and run the main command from the README alone". Floor: "a reader gets stuck or misled". Cost of error: low, it is easy to edit later. Time box: two rounds. Round one rewrites the install steps. Round two produces mostly rewording. The test is a fresh assistant session given only the README and a clean folder; it gets the tool running. Done check passes, the last round changed little, and the work is easily reversible. Stop. The urge to restructure the whole page is noted in the backlog as an idea, not done now.

**A refactor (code cleanup).** Before starting: done is "the module is split into the three planned files, behaviour is unchanged (all tests pass), and no caller imports from the old path". Floor: "anything that could change behaviour or break a caller". Cost of error: low under version control, but a missed caller would break at run time, so the import check is part of done. Round one does the split, round two fixes two missed callers found by searching for the old path. Round three starts renaming internal variables. That is below the floor and changes nothing a user sees, which is the signal: stop, commit, and record the naming ideas.

## Round shape that converges

- **Rank, then work from the top.** Fix the most valuable items first and stop when the next one is below the floor, even if more are known.
- **Bound each round.** Decide the scope of a round before starting it (one area, one lens, a fixed number of items) so that one noisy area cannot absorb the session.
- **Check the fixes once, with existing checks.** Re-run the tests, linters or link checks that cover what changed. Do not open a new open-ended review of the fixes themselves.
- **Prefer a check to a pass.** A class of issue that a script can catch stays caught while the script runs; a class that needs a person to look will come back.

## Signs you are past the point

- New findings are rephrasings of items already recorded.
- Changes are wording or naming with no effect anyone would notice.
- Describing a round takes longer than the round's changes.
- The reason for another round is "to be thorough" rather than a named risk or a failing done check.

Any one of these is a prompt to run the stopping test again, honestly, and stop if it says so.

## Related

- [Part 2: The Improvement Loop](02-improvement-loop.md) for turning recurring findings into checks.
- [Part 3: Ideas and Roadmap](03-ideas-and-roadmap.md) for where the remainder goes.
- [Part 13: Audit Lenses](13-audit-lenses.md) for the angles that generate findings.
- [Part 16: Auditing Your Own Changes](16-auditing-your-own-changes.md) for why each round creates new surface.
