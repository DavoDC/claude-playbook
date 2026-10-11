# Part 26: Bug Reports and PR Descriptions a Stranger Can Act On

> **Field note.** Written from practice rather than machine-checked.

A bug report to an upstream project and a pull request description have the same reader: a maintainer who has never seen your machine, your session or your repo, who has a queue of other things to do, and who will spend the first minute deciding whether this one is worth the next ten. Everything you leave out is something they must guess or ask about, and a round trip costs days. This part is about writing both so that the reader can act on the first read. An assistant drafting on your behalf needs the same discipline spelled out, because by default it writes for the person who already knows the context, which is the one reader who will never see the text.

## Write for the Stranger

State the reader before writing: someone competent in the project, with none of your context. That rules out three habits. Do not use your own names for things (a local alias, a nickname for a file, a ticket number from a tracker they cannot open). Do not refer to the conversation that produced the bug ("as discussed", "the earlier error"). And do not assume the same environment: the version, the operating system, the shell and the configuration are part of the report, not background.

The test is cold-read: open the draft as if you had never seen the problem and ask whether you could reproduce it or review it from the text alone, with no other tab. If the answer depends on something only you have, that thing goes into the text or the sentence that leans on it goes out.

## Check That It Is Worth Filing

Most of the cost of a bad ticket falls on the maintainer, so spend a few minutes first on three checks.

Search the tracker, open and closed, for the error text and for the symptom in plain words. A duplicate wastes the maintainer's time and yours, and a closed issue often carries the workaround or the reason it will not be fixed. Read the changelog and the latest release notes, because the bug may be fixed in a version newer than yours, and reproduce on that version before reporting against an old one. Read the documentation for the feature, because a surprise that the docs describe is a request for a change in design, and it should be filed as one, not as a defect.

Then decide what you are reporting. A defect (it does not do what it says), a documentation gap (it does something reasonable that nobody wrote down) and a feature request (it does what it says and you want more) go to different places with different expectations. Naming the kind in the title saves a triage step.

## Evidence Comes First

Claims need evidence a stranger can check. Lead with what you saw, as exactly as you can capture it, and only then say what you think it means.

- **Exact error text, copied, not retyped.** Paste it in a code block with the full message and the lines of context before it. A paraphrase hides the detail the maintainer would recognise.
- **Versions.** The project version, the runtime or language version, the operating system and anything that sits between you and the project (a wrapper, a plugin, a proxy). For a command line tool, include the output of its version flag.
- **The command or input that triggered it,** complete, as run.
- **Logs or a trace,** trimmed to the relevant stretch but with the start and end of the failure included. Say that you trimmed them.
- **What you checked that shows the problem is in the project and not in your setup:** it fails on a clean install, on a second machine, with the configuration emptied.

Before pasting anything, read it for secrets and for private details: tokens in a URL, a home directory path with a username, a hostname, an email address. A bug report is public and permanent, and a pasted log is the commonest way a credential leaves a machine. Replace the sensitive part with a visible placeholder and say you did so (see [Part 11](11-privacy-hooks-public-repo.md) for the scanning habit).

## The Minimal Reproduction

A reproduction is the single most valuable part of a report, because it converts a story into a test. A good one is small, complete and runnable by someone else, in that order of priority.

Start from the failing case and remove things until the failure stops, then put the last thing back. Delete files, options, dependencies and steps one at a time and re-run after each removal. What remains is the minimum, and the act of reducing often shows the cause, in which case you may not need to file at all. If the failure needs your whole project, say so, and say what you tried to cut and what broke when you did.

Make it complete: a maintainer should be able to paste the steps into a fresh directory and see the same result. Number the steps. Include the files, in the text if they are short or in a small repository or gist if they are not. State the starting condition (a fresh clone, an empty configuration, a particular operating system), because a reproduction that depends on leftover state works only on your machine.

State how reliably it fails. "Every time" and "about one run in twenty" are different bugs, and the second needs the number of runs you tried and anything you noticed that correlates, such as load, timing or order. If you cannot reproduce it reliably, say that plainly and give what you have; an honest intermittent report is more useful than an invented deterministic one.

Run your own reproduction once before sending it, from scratch, following only the written steps. It is common for a step to be missing because you did it in a different session and forgot.

## Expected and Actual

Say what you expected to happen and what happened, in separate labelled lines, and say why you expected it. The expectation is the claim; without it the maintainer cannot tell a bug from a different opinion. Point at the source of the expectation: the documentation sentence, the previous version's behaviour, the specification, a sibling feature that does behave this way. If the only basis is your intuition, say so, because that changes how the report is triaged.

Keep the two apart from your diagnosis. "Expected: the file is written. Actual: exit code 1 and no file" is a report. "The writer has a race condition" is a hypothesis. Hypotheses are welcome, labelled as such and placed after the evidence, because a wrong confident diagnosis in the first line sends the maintainer down a path you chose for them.

## What You Tried

List what you did to narrow it down, including what did not work. It tells the maintainer where not to look and shows that the report is not a first reaction. Useful entries: versions that do and do not show the problem (a bisect range is excellent), options and settings you changed, the workaround you are using, and what you ruled out. Record the negative results as plainly as the positive ones, since "does not happen with the cache disabled" is as informative as any stack trace.

If you have a theory about the cause or a fix, offer it at the end, marked as a guess. If you are willing to send a patch, say so, but ask whether a patch would be welcome before writing a large one.

## The Title and the Shape of the Report

The title states the symptom in the project's own vocabulary, specific enough to find by search: "Export fails with exit 1 when the output directory is read-only" and not "Export broken" or "Bug". Put the version or area in the title only when the tracker's convention asks for it.

Use the project's issue template if it has one, and fill every field it asks for; an empty template field is the commonest reason for a request for more information. If it has none, use a stable order: summary in one or two sentences, environment, steps to reproduce, expected, actual, what you tried, notes. One problem per report. Two symptoms that might share a cause are two reports that link to each other, because they will be fixed, closed and discussed separately.

Keep the tone factual and short. Skip the apology, the frustration and the history of how you came to use the project. Thank the maintainers once, at the end, if you like. Assume good faith in the replies, answer questions with data, and update the report if you learn something that changes it. If you find the cause yourself, post it and close the report, so nobody works on a solved problem.

## The Pull Request Description

A pull request is a bug report plus a proposed answer, so it needs the same evidence and the same stranger-readable shape, and then it needs to help the reviewer judge a diff. The reviewer has the code but not your reasoning, and the description is the only place that reasoning survives, long after the branch is merged and forgotten.

Open with what the change does and why, in two or three sentences: the problem or goal, and the approach in one line. Link the issue it addresses, using the tracker's closing keyword only when the merge really finishes the work. Then give the reviewer what a diff cannot show:

- **Why this approach,** and the alternative you rejected with the reason. This is the part reviewers most often have to ask for.
- **What is deliberately not in the change,** so the reviewer does not read the omission as an oversight.
- **How you tested it:** the commands run and their results, the cases that now have a test, and the manual checks. Say what you did not test.
- **Risk and how to undo it:** what else calls this code, what could regress, whether the change touches data or a public interface, and whether reverting it alone is safe.
- **For a change in behaviour, before and after,** as output or a screenshot, so the effect is visible without checking out the branch.

Keep the change reviewable. One purpose per pull request, a diff small enough to read in a sitting, and mechanical changes (a rename, a reformat) in their own commits or their own request, so the logic change is not buried. If the change is large by necessity, say where to start reading and in what order. Do not mix an unrelated cleanup into a fix, since it enlarges the review and obscures the revert.

Write the description to stand on its own. Do not refer to review comments, to a chat, or to "the earlier version"; a reader opening it next year should understand it. When review changes the approach, edit the description to match the final change rather than leaving a trail of corrections below it. Match the project's contribution guide where it has one: the commit message format, the branch name, the sign-off, the checks that must pass.

## Using an Assistant to Draft Them

An assistant is good at the bulk of this and weak in three predictable places, so check those before sending.

It writes from the session it is in, so it leaks context: names of local files, conversation references, a private repository or path it was just working in. Run the privacy scan over the draft, and read it once for anything a stranger could not know. It states a diagnosis as fact, because the draft flows better that way, so move any cause you have not verified into a labelled guess. And it describes the intended fix as tested when it only ran the change; make it list the commands it ran and their output, and re-run the reproduction yourself on a clean checkout. The principle is the one in [Part 14](14-reading-a-measurement.md): a claim of success is evidence only when you can see what was measured.

Give the assistant the stranger as an explicit constraint ("the reader has none of this context and cannot ask a question") and the structure above as a template, and ask it to list every assumption it made about the reader. Then do the cold read yourself. Whoever sends the report owns what it claims.

## Which Parts a Check Can Enforce

Each rule above gets one of two answers: a mechanical check that can see a violation, or a reason it stays a review question.

| Rule | Mechanical check | Otherwise |
|------|------------------|-----------|
| No private paths, hostnames, emails or tokens in the text | `hooks/privacy-scan.sh msg FILE` on a drafted description, and `tree` or `history` on a repo before publishing it ([Part 11](11-privacy-hooks-public-repo.md)) | none needed |
| Description is one line per paragraph, with no dashes | `tools/prose-lint.py FILE` ([Part 25](25-config-driven-doc-linting.md)) | none needed |
| Commit subject fits and body is not wrapped | `tools/prose-lint.py --commit-msg` | none needed |
| Required sections present (environment, steps, expected, actual) | A `required-pattern` rule in the doc linter, applied to a saved draft or to a template file | The linter checks the headings exist, not that the content is useful |
| Reproduction is minimal and complete | none | Only running it from scratch proves it |
| Expected behaviour has a stated source | none | A reviewer judges whether the source is real |
| Evidence is accurate and nothing was invented | none | Compare against the raw output |
| The change is one purpose and reviewable | none | A diff size limit is a proxy; the question is whether one sentence describes it |

The last four rows are the point of the table: they are the rules a stranger will notice, and nothing in the tooling will. They are the reason the cold read is a step and not a courtesy.
