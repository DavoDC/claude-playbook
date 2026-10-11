# Shorthand glossary

A short term typed in a prompt triggers a defined behaviour instead of re-explaining it each time. This file is the only place the terms live. The hook `hooks/examples/shorthand_detector.py` reads the fenced block below on every prompt and injects the definition of any term it finds. Copy this file to `.claude/shorthand-glossary.md` (or point `SHORTHAND_GLOSSARY` at it) and replace the rows with your own. The full system, including the rules for what earns a row, is in `docs/11-shorthand-system.md`.

## Terms

One row per line, pipe-delimited: `TERM|definition|source|aliases`. The source is the file that owns the full behaviour; the aliases are comma-separated long forms that trigger a one-a-day tip to type the short term instead (leave empty for none). A definition must not contain a pipe character.

```glossary
QUAD|First list every issue, mistake or success in view (the whole session or recent window, not only the latest) as a numbered list. Then give each item four slots: fix the instance; write the specific lesson into the doc that governs that kind of work; write the general lesson into a feedback file, widening an existing rule rather than adding a duplicate; add one backlog line naming the mechanical check that would have caught it. Merge items that share a lesson into one feedback entry and say so. Cap it at four doc edits and one backlog line, and skip a slot that does not apply rather than padding it.|.claude/processes/reflect-on-every-error.md|fix the instance and save the lesson
BLUF|Concise reply: answer first, then at most a few short sentences or a small table. No preamble, recap or hedging. Applies to the reply only, not to a document rewrite.|.claude/processes/communication.md|concise reply,keep it short
OSTP|One step then pause: give exactly one step, question or action per message, then wait for the answer before the next. No batching and no parallel work.|.claude/processes/communication.md|one step at a time,step by step
```

## Dismissed candidates

Terms you declined, kept in the same row format so a discovery pass stops proposing them again.

```glossary-dismissed
```
