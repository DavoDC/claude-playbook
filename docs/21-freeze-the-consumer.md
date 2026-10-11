# Part 21: Freeze the Consumer Before Repairing a Dependency

> **Field note.** Written from practice rather than machine-checked, and not covered by `tools/selftest.sh`. Last reviewed 2026-08-02 against Claude Code v2.1.220. Opinionated, and it may lag the harness.

A dependency that has been down is not idle: pending work (a deletion queue, sync job, scheduled task) has been silently suppressed, and the instant the connection is restored the backlog fires against state that may be months stale. A system failing safely for weeks is loaded.

The instinct is to restore the connection first because a broken one reads as safe. The outage is often the only thing between a stale, overdue queue and an irreversible action.

**How to apply, before touching the connection itself:**

1. Find the consumer of the broken dependency and read its pending work directly from storage - the queue table, the collection, the job list - rather than through the API, because the API usually needs the same dependency that is down.
2. Check for due dates or timestamps that passed during the outage. Overdue by any margin is the danger signal.
3. Freeze the consumer: disable the schedule, deactivate the job, pause the worker. Verify the freeze actually took effect.
4. Only then repair the dependency.
5. Clear or re-date the stale queue before unfreezing, so entries evaluate against a fresh clock rather than inheriting a due date from before the outage began.

This generalizes: paused cron jobs, disabled webhooks, a stopped worker with a full queue, an expired credential blocking a sync, a disconnected replica about to catch up. The one-line test before repairing any dependency: ask what the repair will *unblock*, and look at that queue first.

