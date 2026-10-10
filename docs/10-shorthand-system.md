# Part 10: The Shorthand System

> **Field note.** Written from practice. The hook and glossary template it describes are exercised by `tools/selftest.sh` (assertion 12), but the habit itself is not.

A shorthand is a short term you type in a prompt that triggers a behaviour you have already defined. Instead of re-explaining a multi-step routine each time, you type one word and the definition arrives in Claude's context with your message. The definitions live in a single glossary file, and a small `UserPromptSubmit` hook ([Part 8](08-hooks.md) covers the event) finds the terms you typed and injects the matching definitions. This part covers the file format, the hook, the rules that keep the glossary small and honest, and one worked term.

## Why a glossary and not a rule or a skill

The same instruction typed from scratch drifts: the third time you explain a routine you leave out the step you cared about. The options for fixing that sit at different costs:

- **An always-loaded rule** fires every turn. Right for behaviour you want on every turn, wrong for a routine you want only when you ask for it, because it spends context on every message to serve the few where it applies.
- **A skill** is the right home for a procedure with real depth, but it needs a slash command or a trigger phrase and loads a whole file.
- **A shorthand** costs nothing until typed. The row is one definition line, injected only on the prompts that contain the term, and it can point at a longer document for the full behaviour.

So a shorthand is the middle tier for a routine you invoke on demand and can state in a short paragraph. If the behaviour should always apply, it belongs in an always-loaded file instead (see the deletion rule below).

## The glossary file

All the data is one markdown file with a fenced block tagged `glossary`. One row per line, pipe-delimited:

`TERM|definition|source|aliases`

- **TERM** is what you type. It is matched as a whole word, case-insensitively, so `quad` and `QUAD` both hit and `quadrant` does not.
- **definition** is the instruction Claude receives. Write it as an imperative paragraph on one line. It must not contain a pipe character.
- **source** names the file that owns the full behaviour. The glossary is only the index and the match list; a long procedure lives in its own process doc and the row points at it.
- **aliases** are comma-separated long forms of the same request, such as "one step at a time". They never trigger the definition. They trigger a one-line tip, at most once per term per day, suggesting you type the short term next time. Leave the field empty if there are none.

Terms you rejected go in a fenced block tagged `glossary-dismissed`, in the same row format, so a discovery pass does not propose them again. `templates/shorthand-glossary.md` is a ready file with three generic terms; copy it to `.claude/shorthand-glossary.md` and replace the rows.

## The hook

`hooks/examples/shorthand_detector.py` is the mechanism, and the glossary is the data. Adding a term is a new row, never a code change. On each prompt it:

1. Skips the prompt if it opens with a known harness or agent frame (a relayed message, a system notification) rather than text you typed.
2. Removes pasted blocks and fenced code from the text before matching, so a log you pasted that happens to contain a term never fires it.
3. Matches each term whole-word against what is left and, for each hit, adds a `[SHORTHAND] TERM: definition (source: ...)` line as `additionalContext`.
4. Checks aliases the other way: a long form present without its short term yields the once-a-day tip.

It is advisory only and it fails open. A missing or malformed glossary, an unreadable payload or any exception ends in exit 0 with no output, because a `UserPromptSubmit` hook that exits 2 erases the prompt you just typed. Register it under `UserPromptSubmit` in `settings.json` with an explicit numeric timeout and a real interpreter name, and run the health check from [Part 9](09-hooks-recipes.md) afterwards. `SHORTHAND_GLOSSARY` overrides the glossary path.

## Rules that keep the glossary useful

**The data lives only in the glossary file, never in the hook.** A term hard-coded in the script is a second copy that will disagree with the file.

**A term earns a row only if it is acronym-shaped and rare in ordinary prose.** Matching is whole-word, so a common English word or an abbreviation used for something else fires inside normal sentences. If you would plausibly type the term while describing something else, it does not belong.

**Delete a row the moment its behaviour is promoted into an always-loaded file.** Once a rule loads on every turn, a glossary hit on top of it is a duplicate injection. The glossary is for what you want on demand, so promotion ends the row's job.

**Discovery is proposal-only.** A script can scan your prompt history for repeated phrases and suggest adoption candidates, and flag existing terms that are never typed as retirement candidates. It must never edit the glossary. A term is added only when you approve it, and a declined one goes to the dismissed block.

**An unfamiliar all-caps token is looked up, not interpreted.** When a prompt holds a token Claude does not recognise, it checks the glossary rows and any `[SHORTHAND]` context first. Guessing a meaning (reading a shorthand for a documentation routine as a tool name) is the failure the glossary exists to prevent.

## Worked example: QUAD

QUAD is the shorthand for turning one session's mistakes and successes into durable improvements, and it shows what a good definition does: it fixes the order, the slots and the limits so the behaviour is the same each time. The shipped template holds its one-paragraph definition; the structure is:

1. **Enumerate before acting.** List every issue, mistake or success in view, across the whole session or recent window rather than only the latest, as a numbered list. Fixing the first item and stopping is the failure this step prevents.
2. **Four slots per item.** Each item gets a fix for the instance itself; the specific lesson written into the doc that governs that kind of work; the general lesson written into a feedback file, widening an existing rule when one already covers the ground so the folder does not fill with near-duplicates; and one backlog line naming the mechanical check, a test, lint rule or hook, that would have caught the problem without anyone remembering.
3. **Merge by shared lesson.** Items that teach the same general lesson share one feedback entry, and the reply says they were merged.
4. **Cap the output.** At most four doc edits and one backlog line per item, and a slot that does not apply is skipped rather than padded.

The fourth slot is what makes it more than a retrospective. A lesson written only as prose depends on someone reading it at the right moment, and the backlog line forces the question of what would have caught the problem mechanically. The pieces it stitches together are covered elsewhere: the feedback files and rule hierarchy in [Part 2](02-improvement-loop.md), backlog lines in [Part 3](03-ideas-and-roadmap.md), and the checks in [Part 8](08-hooks.md).

QUAD also shows the tier test above. If you find yourself typing it at the end of every session, promote the behaviour to an always-loaded rule or an end-of-session skill and delete the row.
