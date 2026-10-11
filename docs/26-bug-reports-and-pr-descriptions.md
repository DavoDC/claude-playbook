# Part 26: Bug Reports and PR Descriptions a Stranger Can Act On

> **Field note.** Written from practice rather than machine-checked.

A bug report to an upstream project and a pull request description have the same reader: a maintainer who has never seen your machine, session or repo, who has a queue of other things to do, and who spends the first minute deciding whether this one is worth the next ten. Everything you leave out is something they must guess or ask about, and a round trip costs days. Write both so the reader can act on the first read. An assistant drafting for you needs this spelled out, because by default it writes for the person who already knows the context, the one reader who will never see the text.

## Write for the Stranger

State the reader before writing: someone competent in the project, with none of your context. That rules out your own names for things (a local alias, a nickname for a file, a ticket number from a tracker they cannot open), references to the conversation that produced the bug ("as discussed", "the earlier error"), and assuming the same environment: version, operating system, shell and configuration are part of the report, not background.

The test is cold-read: open the draft as if you had never seen the problem and ask whether you could reproduce or review it from the text alone. If the answer depends on something only you have, put that thing in the text or cut the sentence that leans on it.

## Check That It Is Worth Filing

Most of the cost of a bad ticket falls on the maintainer, so check three things first.

- Search the tracker, open and closed, for the error text and the symptom in plain words. A closed issue often carries the workaround or the reason it will not be fixed.
- Read the changelog and latest release notes: the bug may be fixed in a newer version, and you should reproduce on that version before reporting against an old one.
- Read the documentation for the feature: a surprise the docs describe is a request for a design change, and should be filed as one.

Then decide what you are reporting: a defect (it does not do what it says), a documentation gap (it does something reasonable nobody wrote down) or a feature request (it does what it says and you want more). They go to different places with different expectations; naming the kind in the title saves a triage step.

## Evidence Comes First

Lead with what you saw, as exactly as you can capture it, and only then say what you think it means.

- **Exact error text, copied, not retyped,** in a code block with the lines of context before it. A paraphrase hides the detail the maintainer would recognise.
- **Versions:** the project, the runtime or language, the operating system and anything between you and the project (a wrapper, plugin, proxy). For a command line tool, its version flag output.
- **The command or input that triggered it,** complete, as run.
- **Logs or a trace,** trimmed to the relevant stretch with the start and end of the failure included; say that you trimmed them.
- **What shows the problem is in the project and not your setup:** it fails on a clean install, on a second machine, with the configuration emptied.

Before pasting anything, read it for secrets and private details: tokens in a URL, a home directory path with a username, a hostname, an email address. A bug report is public and permanent, and a pasted log is the commonest way a credential leaves a machine. Replace the sensitive part with a visible placeholder and say you did so (scanning habit: [Part 12](12-privacy-hooks-public-repo.md)).

## The Minimal Reproduction

A reproduction is the most valuable part of a report because it converts a story into a test. A good one is small, complete and runnable by someone else, in that order of priority.

- **Small:** start from the failing case and remove files, options, dependencies and steps one at a time, re-running after each, until the failure stops, then put the last thing back. Reducing often shows the cause, in which case you may not need to file. If the failure needs your whole project, say so and say what you tried to cut.
- **Complete:** a maintainer can paste the numbered steps into a fresh directory and see the same result. Include short files in the text, longer ones in a small repository or gist, and state the starting condition (fresh clone, empty configuration, operating system), because a reproduction relying on leftover state works only on your machine.
- **Honest about reliability:** "every time" and "about one run in twenty" are different bugs; for the second, give the number of runs and anything that correlates (load, timing, order). An honest intermittent report beats an invented deterministic one.

Run your own reproduction once from scratch, following only the written steps; a step is often missing because you did it in another session.

## Expected and Actual

State what you expected and what happened, in separate labelled lines, and why you expected it. The expectation is the claim; without it the maintainer cannot tell a bug from a different opinion. Point at its source: the documentation sentence, the previous version's behaviour, the specification, a sibling feature. If the only basis is your intuition, say so, because that changes triage.

Keep both apart from your diagnosis. "Expected: the file is written. Actual: exit code 1 and no file" is a report; "the writer has a race condition" is a hypothesis. Hypotheses are welcome, labelled and placed after the evidence, because a wrong confident diagnosis in the first line sends the maintainer down a path you chose for them.

## What You Tried

List what you did to narrow it down, including what did not work: it tells the maintainer where not to look and shows the report is not a first reaction. Useful entries: versions that do and do not show the problem (a bisect range is excellent), settings you changed, your workaround, what you ruled out. Negative results count as much as positive ones ("does not happen with the cache disabled").

Offer a theory or fix at the end, marked as a guess. If you are willing to send a patch, say so, but ask whether one would be welcome before writing a large one.

## The Title and the Shape of the Report

The title states the symptom in the project's own vocabulary, specific enough to find by search: "Export fails with exit 1 when the output directory is read-only", not "Export broken". Put the version or area in only when the tracker's convention asks.

Use the project's issue template if it has one and fill every field; an empty field is the commonest reason for a request for more information. Without one, use a stable order: summary in one or two sentences, environment, steps to reproduce, expected, actual, what you tried, notes. One problem per report: two symptoms that might share a cause are two reports that link to each other, since they will be fixed and closed separately.

Keep the tone factual and short: no apology, frustration or history of how you came to use the project. Assume good faith in replies, answer questions with data, and update the report if you learn something that changes it. If you find the cause yourself, post it and close the report.

## The Pull Request Description

A pull request is a bug report plus a proposed answer, so it needs the same evidence and stranger-readable shape, and then it must help the reviewer judge a diff. The reviewer has the code but not your reasoning, and the description is the only place that reasoning survives after the branch is merged and forgotten.

Open with what the change does and why in two or three sentences: the problem or goal, and the approach in one line. Link the issue it addresses, using the tracker's closing keyword only when the merge really finishes the work. Then give what a diff cannot show:

- **Why this approach,** and the alternative you rejected with the reason (the part reviewers most often have to ask for).
- **What is deliberately not in the change,** so the omission is not read as an oversight.
- **How you tested it:** commands run and results, cases that now have a test, manual checks, and what you did not test.
- **Risk and how to undo it:** what else calls this code, what could regress, whether it touches data or a public interface, whether reverting it alone is safe.
- **For a change in behaviour, before and after,** as output or a screenshot.

Keep the change reviewable: one purpose per pull request, a diff small enough to read in a sitting, mechanical changes (rename, reformat) in their own commits or request, no unrelated cleanup mixed into a fix. If a large change is unavoidable, say where to start reading and in what order.

Write the description to stand on its own: no reference to review comments, a chat or "the earlier version". When review changes the approach, edit the description to match the final change rather than leaving a trail of corrections. Match the project's contribution guide: commit message format, branch name, sign-off, required checks.

## Using an Assistant to Draft Them

An assistant is good at the bulk of this and weak in three predictable places; check them before sending.

- It writes from the session it is in, so it leaks context: names of local files, conversation references, a private repository or path it was just working in. Run the privacy scan over the draft and read it once for anything a stranger could not know.
- It states a diagnosis as fact because the draft flows better; move any unverified cause into a labelled guess.
- It describes the intended fix as tested when it only ran the change; make it list the commands it ran and their output, and re-run the reproduction yourself on a clean checkout. The principle is [Part 15](15-reading-a-measurement.md): a claim of success is evidence only when you can see what was measured.

Give the assistant the stranger as an explicit constraint ("the reader has none of this context and cannot ask a question") and the structure above as a template, ask it to list every assumption it made about the reader, then do the cold read yourself. Whoever sends the report owns what it claims.

## Which Parts a Check Can Enforce

Each rule above gets one of two answers: a mechanical check that can see a violation, or a reason it stays a review question.

| Rule | Mechanical check | Otherwise |
|------|------------------|-----------|
| No private paths, hostnames, emails or tokens in the text | `hooks/privacy-scan.sh msg FILE` on a drafted description, and `tree` or `history` on a repo before publishing it ([Part 12](12-privacy-hooks-public-repo.md)) | none needed |
| Description is one line per paragraph, with no dashes | `tools/prose-lint.py FILE` ([Part 25](25-config-driven-doc-linting.md)) | none needed |
| Commit subject fits and body is not wrapped | `tools/prose-lint.py --commit-msg` | none needed |
| Required sections present (environment, steps, expected, actual) | A `required-pattern` rule in the doc linter, applied to a saved draft or to a template file | The linter checks the headings exist, not that the content is useful |
| Reproduction is minimal and complete | none | Only running it from scratch proves it |
| Expected behaviour has a stated source | none | A reviewer judges whether the source is real |
| Evidence is accurate and nothing was invented | none | Compare against the raw output |
| The change is one purpose and reviewable | none | A diff size limit is a proxy; the question is whether one sentence describes it |

The last four rows are the point: they are the rules a stranger will notice and nothing in the tooling will, which is why the cold read is a step and not a courtesy.
