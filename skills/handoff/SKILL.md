---
description: Write the handoff prompt that starts a fresh session on this work: pre-loads mechanical state from disk, adds only the judgment a script cannot, as one pasteable scratch file.
effort: medium
argument-hint: "[what the next session should do - omit it and Step 1 asks]"
when_to_use: "Use when context is high and the work is not finished, when a genuinely different kind of work would be better done in a clean context, or when the user says 'handoff', 'prompt for a new session', 'write the prompt for the next session', 'I want to start a fresh session on this'. Also offer it unprompted at high context with work still mid-flight. NOT when the work is finished, and NOT as a replacement for whatever end-of-session routine this setup has. Synergy: an end-session routine records what happened, /handoff instructs what happens next."
---

## Pre-loaded session state
!`python .claude/skills/handoff/handoff-prep.py 2>/dev/null`

# /handoff - the prompt that starts the next session

**Architecture:** `handoff-prep.py` (already run above) owns every fact readable from disk. This skill adds only what needs judgment. Do not re-gather what the block above printed, and do not restate it wholesale either: select from it.

## Step 0: is a handoff the right move? Decide before writing anything.

| Situation | Do this instead |
|---|---|
| Work is finished, nothing mid-flight | Nothing. A handoff prompt for finished work is pure overhead. |
| Context high but the task has one small step left | Finish it. A handoff costs more than the step. |
| Same work, just a full context | Offer compaction first. |
| Different KIND of work next, or a long task with real state | **Handoff. Continue.** |

Say which row applies in one sentence. If it is not the last row, stop and say so rather than writing a file.

## Steps

### 1. Pin the task as an OUTCOME

Take `$ARGUMENTS`. If it names an area rather than a result ("the PR", "the migration"), convert it to a finished state ("post the review comment set on PR 212 and the two related issue comments"). **If there is no argument and the session's work does not name one obvious next outcome, ask. One question, then proceed.** A receiving session with a vague objective invents scope, which is the most expensive failure this skill exists to prevent.

**Manual-test check:** if the handoff asks the human to reboot, log off or run a manual test, the prompt must name the command that renders the verdict (a backticked command such as `python -m src.boot_report`), and that command must already exist. If it does not, building it is the first step of the handoff, not the test. A backlog linter that refuses the same wording is worth having.

### 2. Stamp every outward-facing instruction, NOW, before writing it

For each instruction telling the next session to DO something visible to anyone else (post a comment, reply on a thread, publish a page, deploy, message a person): **verify its current state live in this step and write the finding into the prompt with today's date.** Not "post the comment on ISSUE-893" but "as at 15:15 today ISSUE-893 carries no such comment, so post it".

- Issue TITLES are not identifiers and drift. Use keys, and read the issue's own description and comments, never a title match.
- Same for any pointer-to-a-document instruction: say when that document was last checked for internal consistency. "Everything is in that doc" plus a doc that contradicts itself is an instruction that cannot be followed.

This is the step that gets skipped, and the one with a recorded cost. the cost was a duplicated comment.

### 3. Name the exact filters behind any search the plan rests on

If the prompt says a sweep is done, say what it filtered on. A conclusion hides its gap; a filter shows it.

### 4. Write the prompt to `<scratch>/`, using the template below

Name it `<scratch>/HANDOFF-<slug>.md` where the slug is the work, not the date: `<scratch>/HANDOFF-vendor-import.md`. One prefix keeps the set greppable and sorted together.

### 5. Commit it, then hand over the path

An uncommitted scratch file can be deleted by a concurrent session. Commit, then give the user the path and one line saying to paste from the marker down. Never print the prompt body into the terminal: wrapping mangles whitespace and the file is the artefact.

## Template

```markdown
# Handoff: <the outcome, in one line>

> DELETE-AFTER: the Definition of Done below is met, or a newer handoff supersedes this. Not merely because a session ended.

**Everything above the marker is for the human. Paste from the marker down into the fresh session.**

Why a fresh session: <context percent, budget left, and what makes the next work a different kind>

---

## PROMPT STARTS HERE

You are continuing <work>. Read this whole prompt before acting.

### Scope, and it is a hard boundary
<what is in. Then what is deliberately OUT, each with its reason.>

### Goal
<the outcome. The stop condition, which is never "when a batch finishes".>

### Start here, in this order
1. <exact command or file, not an area>
2. ...

### State as at <date time>
<selected from the pre-load block: branch, dirty and staged files, worktrees, scratch files with their DELETE-AFTER, log rows already written so you APPEND not duplicate, issue keys with when each was last read live>

### Already done, do not redo
<the expensive omission. Be specific.>

### How to work, and these are not generic reminders
<only lessons that cost THIS session real time. Delete this heading if there are none. Generic advice here trains the reader to skip the section.>

### Budget and stop conditions
<context ceiling to stop at, whether pushing is allowed>

### What is NOT yours to decide
<escalate with evidence and a recommendation, do not action alone>

### Definition of Done
<checkable conditions, and say which are met when you report>

### Before you do anything else
If this prompt failed to tell you something you needed, add one line to "How to work" above and commit it, now, not at the end of your work. That loop is why this file is generated rather than written from scratch, and a lesson recorded at the end is a lesson forgotten.
```

## Rules

- **Select from the pre-load block, never paste it whole.** A prompt that dumps every repo's status buries the two lines that matter.
- **Every path clickable, every issue paired with a short textual label on first mention.**
- **No instruction without its verification date.** An unstamped outward-facing instruction is the defect, not a stylistic miss.
- **One file per handoff.** Superseding an existing `HANDOFF-*.md` means editing it, not adding a second.

## Log the run

If this setup has a skill-run log, append one line recording whether the run was clean, cost more than it should, or did the wrong thing. Improving a skill from evidence is impossible once the run's context is gone, which is why the line is written during the run and not after.
