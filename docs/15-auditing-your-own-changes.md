# Part 15: Auditing Your Own Changes and Their Compositions

> **Field note.** Written from practice rather than machine-checked.

The most overlooked audit subject is the recent change set, and the most dangerous defects are not in any one part but in how correct parts combine. This part covers auditing recent changes as a scope, auditing by consequence rather than by file, composition defects, and the review shapes that fail when independent workers or independent edits are merged. The lens generator is in [Part 13](13-audit-lenses.md); how to judge a measurement is in [Part 14](14-reading-a-measurement.md).

## Your own recent changes, as a subject

No round ever points anything at this, and it is high-yield ground. Run a log of the last week's commits with file statistics and treat the changed-file list as the audit scope rather than the whole repo. For each changed file, list its callers and its state dependents, then ask which of those were re-tested. The answer is usually none. The commit-anchored version of this scope, which keeps the anchor between rounds, is in [Part 19](19-commit-anchored-delta.md).

**Hardening commits first.** Which recent commits were framed as fixes, guards, caps or safety, and what did each one break? A change framed as protective is the one whose author and reviewers are least likely to ask what it breaks, which makes hardening commits the highest-risk input to this subject rather than the safest.

**Key-derivation changes are MIGRATIONS.** Did any recent change alter how a filename, slug, path or cache key is derived? If so, every record keyed by that value has forked, and the old records are still on disk under the old key. Grep the diff for changes to any sanitising, truncating or slugifying function, then ask what is keyed by its output.

**A cache, allowlist or trust decision keyed more broadly than the evidence that earned it silently admits everything else under that key.** When evidence justifies trusting one address, file or exact string and the decision is stored under a broader key (a whole domain, a whole path prefix), ask what else that key now covers before shipping. The broadening is rarely deliberate, just the more convenient data structure. One endorsed-senders list keyed by domain rather than address accidentally endorsed several major public mail providers. Ask "does this key admit anything I did not mean to admit" when the key is chosen, not after the list is too large to audit.

**Sweep merged pull requests for what they introduced.** Not a re-review of the author's judgement, a search for what got through. Read each pull request's own diff, never its description. For each behaviour added, ask what input class it now handles differently and whether that class previously worked. A fast-merged, clean-reviewed pull request can still ship data loss that only a real user finds.

**Distinguish a new feature under-delivering from a regression before ranking either.** A new check that is imperfect leaves every non-matching case no worse off. A changed behaviour can make a working case fail. Ask whether the previous code handled the failing input correctly; if there was no check at all before, it is not a regression however ugly it looks.

## Audit by consequence, not only by file

A file-by-file audit and a consequence-first audit find different defects, and the second finds the dangerous ones. Reading every function surfaces what is wrong with code that is present. It does not reliably surface what is wrong with code that is missing, because an absent guard has no line to land on. The worst defects in a workflow tool live in the composition: a protection applied on only one path, a value rebuilt between two steps, an argument omitted under a condition.

Before an audit, write the two or three concrete bad outcomes in the user's terms (a wrong file moved, a wrong number believed, the job left half done) and file findings under those headings. Trace each outcome backwards through every branch that can reach it, including the branch where a protection is skipped because a condition was not met. Rank by consequence, not by how much code a finding touches, and run this pass separately from the file-by-file one. If the honest answer is that very little is at risk, say so plainly.

## Composition defects: correct parts, wrong whole

A change assembled from independently written pieces can be made of entirely correct pieces and still be wrong, because the defect lives in the composition and every review looked at a part.

Typical shape: a set of recommendations argues one point in its main framework section and again, independently, in a list of smaller standalone edits. The recipient applies both, correctly, since each reads as a distinct reasonable instruction, and the result is one chapter making the same argument twice, a few lines apart, in different words. No existing check catches it: a sentence-level duplication check sees two different sentences; a per-file review sees two coherent files; the recipient sees two reasonable instructions. The duplication exists only in the merged result, which nobody read as a whole.

Capability checks have the same shape. Confirming capability A exists and capability B exists answers a narrower question than "does A feed B". In one case a tool could filter records against a stored list and a separate scheduler could run rules on a timer, and the assumption was that the scheduler drove the filter engine; it had no way to invoke it. The two had been built and tested next to each other, never through each other. Only running the actual call across the boundary confirms the connection.

Two habits, one per side of the handover:

- When handing over more than about three edits to one target, include a claim index: one line per distinct claim, naming which file argues it. It takes minutes and is the only artefact in which the merged result is legible before the merge.
- After applying a multi-part change, read the result once as a reader, not as a diff. The diff shows two correct additions; the document shows the same paragraph twice.

This reaches past documentation: whenever parts are reviewed independently and merged automatically, the merged artefact is unreviewed by construction - a pull request built from several branches, a configuration merged from layered files, a rule set assembled from several sources.

## Correlated readers are not corroboration

Splitting a large reading job across parallel workers is right, but handing each the same list of "things already covered, skip these" destroys the property the parallelism was bought for. Agreement reads as corroboration but is not, if all were told the same thing: they agree because of the instruction, not the material. Their misses correlate too, clustering where the shared list was thin or wrong, which is where an independent second read pays most. A real instance had a hand-written shared skip list across eight parallel readers, and a couple of dozen already-covered items still came through, bunched in the same places.

Two acceptable shapes. Derive each worker's exclusion list independently and accept the duplicated effort, or keep the shared list and **state up front that overlap is expected and that agreement carries no evidential weight**. A shared list plus a coverage claim is not acceptable, because the claim then measures the list rather than the corpus. The same applies to asking a second worker to check a first worker's output under the same brief. Independence is a property of the inputs, not of the process count.
