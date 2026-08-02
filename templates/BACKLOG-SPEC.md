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

| The item | Goes to |
|---|---|
| Scoped to one repo | that repo's `IDEAS.md` |
| Work on the workspace itself | the workspace's `IDEAS.md` |
| The unattended run's queue, research, cross-repo sweeps | a separate queue file |
| Blocked on a named person, with a deadline | `pending-actions.md`, capped and dated |

## Format

**Tiers, not phase numbers.** Phase numbering creates pressure to finish in order after the priorities have changed. A tier states the reason.

- **T0 blocking** - nothing else in this repo matters until it is fixed.
- **T1 core** - what the repo exists to do.
- **T2 quality** - makes it better, is not load-bearing.
- **T3 nice to have** - real, but would not be missed.

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

- "broken or loses data without it" -> T0
- "enables other work" -> T1
- "improves something that works" -> T2
- "would be nice" -> T3
- **"cannot answer" -> the most valuable group.** Either not understood yet or no longer wanted, and both are decisions to take now.

## Close every pass by re-ranking

Apply ONE extreme lens to the LIST, not the code. Write down what moved. "Nothing moved" is a real result. Do not run more than two per pass.

## Two mechanical habits

- **Before editing any file in a repo with a backlog, grep the backlog for that filename.** Needs no insight, and catches the case where the file already has a queued item you would otherwise duplicate or contradict.
- **Cross-check open items against current code before trusting the list.** Fixes ship without items being closed, so any list left alone for weeks accumulates already-done entries, and every one costs a future session real time.
