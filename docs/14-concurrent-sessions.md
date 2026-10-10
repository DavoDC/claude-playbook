# Part 14: Concurrent Sessions on One Working Tree

> **Field note.** Written from practice rather than machine-checked, and not covered by `tools/selftest.sh`. Last reviewed 2026-08-02 against Claude Code v2.1.220. Opinionated, and it may lag the harness.

Several agent sessions at once is now normal: a foreground session, an unattended loop and background subagents can all be live against one checkout, sharing one working tree, temp directory and set of logs, with nothing in the harness isolating them. Every failure below is silent and most produce a plausible-looking result, so they survive review.

**The design rule is worth more than the hazard list:** give every new temp file, log, cache, index or state file a session identifier when it is created, and ask "what happens when three of these run at once?" at creation time. Retrofitting session scope onto a file other tools already parse costs an order of magnitude more, and until done every consumer is quietly wrong.

The hazards, in cost order:

- **Commits capture a sibling session's work, and staging explicit paths does not prevent it.** `git add <paths>` controls what you add; `git commit` ships the *entire index*, including whatever a sibling staged seconds earlier. Two sessions naming only their own files to `git add` can still ship each other's in-progress work. Pass the pathspec to the commit, not just the add:

  ```
  git commit -m "..." -- path/one.md path/two.py
  ```

  This is the costliest hazard in the set because it corrupts git history, which is the one record everything else gets reconstructed from. Verify rather than trust: `git show --stat HEAD` after committing should list exactly the files you intended and nothing else.
- **"The latest entry" in a shared log is not necessarily yours.** Any hook in any session appends to shared logs. Reading the tail to find out what *this* session did returns whatever was written most recently by *any* session. Filter by session id, never by recency.
- **Day-scoped counters span every session.** Token counts, violation tallies and similar daily aggregates sum all concurrent sessions. Correct as a daily total, wrong for every per-session claim derived from it.
- **The statusline cache is last-writer-wins.** One cache path, every session writing it, so the context percentage on screen may belong to a different session. Have the statusline write its session id into the cache and have consumers check it.
- **Shared state files assume a single reader.** Read-modify-write with no locking loses whichever write landed first, with no error.

One inversion worth noting: account-wide rate-limit windows are genuinely shared, so another session's budget number is the right one to act on. What is wrong there is attributing the spend to this session.

## Worked Example: Locking a Shared Background Step

Two sessions can each reasonably decide a background consolidation step (rebuilding an index, compacting a log, a cleanup pass) needs to run now. Two racing runs are worse than either alone: partial writes, duplicated work, a half-written file.

Take an exclusive lock before the step starts; if a peer holds it, wait briefly then exit cleanly rather than race it.

```
if acquire_lock("consolidate.lock", wait=5s):
    run_consolidation_step()
    release_lock("consolidate.lock")
else:
    exit(0)  # a peer is already doing this; nothing to do here
```

Keep the wait short: this is a "someone else has it, stand down" check, not a queue. Lock utilities vary by platform (a `mkdir`-based lock works anywhere with a filesystem; `flock` is Unix-only; Windows needs a named mutex or exclusive file handle), so use what your stack already has.

## A Stale Lock Is a Recoverable State, Not a Permanent Wait

The lock pattern covers the live case. It has no path for a lock whose holder is dead (crashed session, killed process, mid-run reboot), and the failure is silent: a lock file left by a nonexistent process blocks every future run forever, and each blocked run exits cleanly with "a peer is already doing this", which was once true and is now false.

The fix is a discriminator run before deciding to wait, not a longer wait. All three checks should say stale before breaking the lock: is the PID in the lock file still running under that name (not reused by an unrelated process); is the lock's age past any duration the step has legitimately taken, with margin so a slow real run isn't mistaken for a dead one; and does the recorded owner still hold the resource the lock protects, checked directly rather than inferred from the file's existence. Any one saying "still live" means keep waiting.

Log every broken stale lock. A lock silently cleared on every stale-looking read is one bug from never protecting anything, and an over-eager discriminator recreates the race under the appearance of safety.


## Git Rules For Shared Trees

Three rules follow from several sessions sharing one working tree. Never amend: by the time you amend, HEAD may be a sibling session's commit, so the amend rewrites its message and leaves yours untouched. Fix a wrong message or trailer with a new commit. Always scope a commit with a pathspec. After a `git mv`, the pathspec must name the old paths as well as the new ones, because the move stages a deletion at each old path and a pathspec listing only the new paths commits the additions and leaves the deletions staged; confirm with `git status --short` afterwards, since the commit looks right either way.
