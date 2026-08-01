# Part 7: The Overnight Loop Workflow

This is one of the most powerful things you can do with Claude Code that most people don't know about.

The `/loop` skill runs a command on a repeating interval - indefinitely, waking up automatically via a scheduling tool. Combined with `/dev-session`, you can set a work loop before you go to sleep and wake up to finished features, committed and documented.

```
/loop 30m /dev-session myproject
```

This runs `/dev-session myproject` every 30 minutes. Each iteration: reads IDEAS.md, picks the next item, implements it, runs tests, moves it to HISTORY.md, commits. Then sleeps 30 minutes and does it again.

## Why It Works

The key is that `/dev-session` is self-contained. Each iteration:
1. Checks budget first - if rate limits are too high, it schedules a wakeup after the reset rather than hammering the API
2. Picks from IDEAS.md based on current priority - you don't need to pre-queue work
3. Handles its own commit and close-out
4. The next iteration starts fresh with the updated IDEAS.md

Without the budget gate (see [Part 5](05-budget-awareness.md)), the loop would hammer rate limits and fail. The budget awareness tooling is what makes overnight automation safe.

## /checkpoint - Restore Points During Loops

Use `/checkpoint` during overnight runs to create named restore points:

```
/checkpoint create pre-auth-refactor
```

This commits current state and logs the checkpoint with SHA and context percentage. If something goes wrong you can diff back to any named checkpoint and see exactly what changed.

Use checkpoints: before risky refactors, after each major task in an overnight loop, whenever touching 5+ files in a single iteration.

## Self-Paced Mode

```
/loop /dev-session myproject
```

No interval specified - the model decides how long to sleep based on what it just did. If the last iteration was a quick fix, it might sleep 15 minutes. If it was a large refactor, it might schedule a longer gap to avoid burning context on a session that needs to start fresh.

## Practical Tips

- Make sure `session-status.sh` is working before starting an overnight loop - the budget abort gate is what prevents the loop from hammering rate limits
- Check the loop's output in the morning using `git log --oneline` to see what was shipped
- `/loop` can be stopped by simply responding to the next wake-up - the loop continues only if the model calls `ScheduleWakeup` again at the end of each iteration
- Ensure IDEAS.md is well-ordered before starting - the loop picks the top item each time. If TIER 0 is a massive refactor, it will attempt that first.

## Building Your Own /loop

The mechanics: at the end of each iteration, call `ScheduleWakeup(delaySeconds, prompt)` where `prompt` is the same `/loop` invocation. This causes the session to wake up after `delaySeconds` and repeat.

The budget abort logic: before doing any work, check `session-status.sh`. If 5-hour rate >= 83%, call `ScheduleWakeup(min(seconds_until_reset, 3600), same_prompt)` and return without doing any work. `ScheduleWakeup` clamps its delay to between 60 and 3600 seconds, so a reset more than an hour away can't be skipped in one call - each wake re-checks the budget and, if the reset still hasn't passed, schedules another capped wakeup with the same prompt. The loop effectively pauses, waking periodically, until the rate limit actually resets.
