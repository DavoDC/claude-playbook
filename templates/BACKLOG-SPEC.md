# Backlog specification

**One file, governing every backlog.** Copy this into your workspace once. Point every `IDEAS.md` at it rather than restating the rules per repo, so improving the process improves every backlog at once.

## Layout

```
backlogs/<RepoName>/IDEAS.md      # forward-looking, ordered by leverage
backlogs/<RepoName>/HISTORY.md    # shipped record, dated
```

Give the workspace itself a folder here. It is a repo, it accumulates work, and it is the one everybody forgets.

**Keep these private.** A backlog names unreleased work, internal systems and people, which makes it the most context-leaking file you own. If a repo is or may become public or shared, the backlog lives in your workspace and never in the repo, and nothing in the repo points at it.

## Routing: what unblocks it, not what it is about

Picking the wrong list is the most common backlog defect, and the usual test ("is it about this repo?") gets it wrong regularly. The better test is what unblocks the item, not what it is about.

| The item | Goes to | Why |
|---|---|---|
| Code, docs, tests or tooling scoped to ONE repo | that repo's `IDEAS.md` | `/dev-session` picks from here |
| Work on the workspace itself: a hook, a skill, a rule, a workspace tool | the workspace's own `IDEAS.md` | The workspace is a repo and deserves the same treatment as any other. Most people never create this one, and it is why workspace improvements live in scattered notes |
| The unattended run's work QUEUE, research, cross-repo sweeps | a separate queue file | A queue answers "what should tonight's run do", which spans every repo and includes work belonging to none. That is a different question from "what should be built in this repo next" |
| Blocked on a named person, with a deadline and a real consequence | `pending-actions.md`, capped and dated | High bar. An unbounded blocked list is a wish list |

The distinction between the second and third rows is the one people collapse, and collapsing it is why a queue file grows to hundreds of items: repo-scoped engineering work has nowhere else to go, so it accumulates in the queue and the queue stops functioning as a queue.

## Format

**Tiers, not phase numbers.** Phase numbering creates pressure to finish in order after the priorities have changed. A tier states the reason.

- **TIER 0 blocking** - nothing else in this repo matters until it is fixed.
- **TIER 1 core** - what the repo exists to do.
- **TIER 2 quality** - makes it better, is not load-bearing.
- **TIER 3 nice to have** - real, but would not be missed.

Within a tier, order by leverage, never by date added.

**Item shape.** One bolded outcome line, the why, then an evidence pointer. The evidence pointer is what makes an item re-checkable a month later by someone who has forgotten the context. An item without one decays into a wish.

```
- [ ] **What changes, stated as an outcome.** Why it is necessary: what fails if it is skipped.
  Evidence: `path/to/file.py:120`, or the audit or note that produced it.
```

## Lifecycle

1. **Add** the moment the idea exists. Context is lost at the next compaction and anything off disk is gone.
2. **Refine** with the one question below, once the list passes roughly ten items.
3. **Rank**, then re-rank with one extreme lens per pass.
4. **Ship**, then **MOVE** the line to `HISTORY.md` with the date, the result and the commit.
5. **Delete** it from `IDEAS.md` in the same commit.

**Never tick an item in place.** A ticked item still costs a read every time the file is opened, and the entire value of the active list is that everything in it is still true. Git history is the record of what was there.

## The one question that derives the tier

**"Why is this necessary, and what fails if we skip it?"**

- "broken or loses data without it" -> TIER 0
- "enables other work" -> TIER 1
- "improves something that works" -> TIER 2
- "would be nice" -> TIER 3
- **"cannot answer" -> the most valuable group.** Either not understood yet or no longer wanted, and both are decisions to take now.

That last group is the point. A list where every item has an answer is well-ordered whether or not it has tier labels; a list with tier labels and no answers is decorated, not prioritised.

## Close every pass by re-ranking

Adding items to a backlog is easy and everybody does it. Re-ranking one is rare, and it is where the value is: a ranking made under no constraint is mostly an artefact of the order things were found in.

Apply ONE extreme lens to the LIST, not the code. Write down what moved. "Nothing moved" is a real result. Do not run more than two per pass.

This is the cheapest step in the whole process and the only one that improves items you are not touching. One measured instance: asking "what would you fix if you could never touch this repo again" of a 180-item backlog promoted a bottom-tier item to first place, because an override flag that silently destroyed hand-edited work had been correctly tiered as polish under "how valuable is this" and was the most important item in the repo under "what is unrecoverable". Nothing was learned about the code.

## Two mechanical habits

- **Before editing any file in a repo with a backlog, grep the backlog for that filename.** Needs no insight, and catches the case where the file already has a queued item you would otherwise duplicate or contradict.
- **Cross-check open items against current code before trusting the list.** Fixes ship without items being closed, so any list left alone for weeks accumulates already-done entries, and every one costs a future session real time.
