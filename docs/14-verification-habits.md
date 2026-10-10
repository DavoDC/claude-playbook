# Part 14: Verification and Iteration Habits

> **Field note.** Written from practice rather than machine-checked, and not covered by `tools/selftest.sh`. Last reviewed 2026-08-02 against Claude Code v2.1.220. Opinionated, and it may lag the harness.

## Re-test Inherited Constraints Before Planning Around Them

A capability limit written into a doc as a bare fact becomes an unquestioned ceiling. A session observes something not working, guesses why ("my plan tier doesn't support this"), and a later session reads the guess as settled fact and plans around it, sometimes for weeks. Nobody re-tests it because it is presented as established, not as a hypothesis.

A false ceiling is invisible and self-reinforcing: it throws no error, it produces a smaller plan. You never see what you didn't attempt, and the more important the constraint, the more work is built on it unexamined. It is usually plausible - "the plan tier doesn't allow it" explains the symptom, costs nothing to believe, and is unfalsifiable without a test nobody runs.

**How to apply:**
- Never write a capability limit as a bare fact. Record its evidence and provenance: what was observed and which model or session concluded it. A smaller or less careful model's judgment carries different weight, and a reader must be able to discount it.
- Re-test inherited constraints before building strategy on them, especially load-bearing ones. The re-test is nearly always cheaper than the plan that assumes the answer - often one settings check versus weeks of a degraded workflow.
- Be most suspicious of constraints that conveniently explain a disappointment. A story that closes an investigation deserves the most scrutiny.

## Enumerate Before You Confirm

A yes/no probe against something unfamiliar (an SDK, an API, a config surface) spends a full round trip per failure and teaches almost nothing: you learn the one call was wrong, not what the right one looks like. When round trips are expensive (human-mediated step, slow deploy, rate-limited call) this compounds fast.

Enumerate first: list the members, methods, config keys and accepted values before attempting any specific call. One enumeration costs about the same as one guess but returns the whole answer space, making the next call likely right. Repeated guessed calls against an unfamiliar interface is itself the signal to switch to enumeration rather than try a third or fourth guess.

## Check for a Shipped Introspection Tool Before Building a Custom Probe

A case of enumerate-first: before writing a custom probe against an unfamiliar system, check whether it already ships an introspection, dump or debug tool. Look in the settings surface already open, in CLI help output (`--help`, `--dump-config`, `--debug`), and in the platform's docs before reaching for a script. In one case an already-configured header/dump tool sat in an already-open settings file the whole time; a single keypress resolved what two rounds of guessing at a custom probe could not. A second guessed probe is the signal to look for the tool already there.

## Build the Observation Harness Before You Iterate

Never iterate on something you cannot observe. Before any round of AI-driven iteration on an app, game or simulation, build the measurement rig first, cheaply, on the cheaper tier, before the expensive session starts.

For functional work (games, sims, anything with internal state), separate pure logic from presentation so it runs headless, then expose a small documented control-and-observe API: set or seed state, inject inputs, step the simulation, return a full state snapshot as structured data. Ship a headless runner plus an autonomous driver that plays real scenarios and reports structured metrics, so balance and correctness are checked with numbers instead of vibes. A premium session handed the same control surface can self-verify mid-build, catching problems (like an unwinnable difficulty setting) through telemetry instead of a human noticing later.

For subjective work (art direction, feel, UX), the equivalent is an objective capture rig: comparable before/after captures so a taste judgment has something concrete to point at.

Put the observation harness in the brief as an explicit deliverable for any AI-built game, sim or app; it pays back every round, whether a human or another model runs it.

## Replace the Human Keypress With a File-Based Trigger

The harness answers how you measure a change. A separate question is what triggers the next observation: which step in the loop needs a human action (keypress, manual reload, click to re-run), and can a file- or signal-based trigger replace it? To be safe unattended it needs three properties: it consumes itself before acting, so a mid-run crash cannot fire the same trigger twice on restart; it costs nothing while idle; and it echoes a stable run-id to a fixed output location, so whatever watches for the result always knows where to look.

Worth building even when a harness exists, since one that waits on a human to press "reload" has solved only the measurement half, not the round-trip-time half. In one case a toolchain's built-in hot-reload-on-file-touch was repurposed as this trigger, cutting the human round trip from several minutes to well under two.

## A Green Test Suite Does Not Prove the Live Process Survived

**A test suite passing after a risky edit is not evidence that the live process the edit was applied to is still running.** An offline suite exercises logic against mocks and fixtures; it cannot reproduce races that only appear against the real environment (a process exiting between being listed and being queried, a library timing out under load, a network flake), because the mocks exist to remove them. A hot-reload or auto-restart mechanism will execute a change that crashes the process and fails to restart it, while the suite stays green because it never touched the live process.

In one case a run of edits to a long-running watched process each triggered a real self-restart; the suite passed at every step because it mocked the process-listing library, so it never hit the race, which raised an exception the headless process swallowed uncaught. The dashboard it served went dark and stayed dark, undetected, because nothing in the suite watched the live process.

**How to apply:** treat every save under hot-reload or auto-restart as a live deploy. After any edit risky enough to touch process, OS or network calls, check the live process directly - health endpoint, process list, newest log tail - before the next edit, rather than batching risky edits and checking once. An earlier edit could be the one that killed it, and every edit stacked on a dead process is wasted work that looks productive.

This is the process-liveness counterpart to the file-trigger and harness material: those cover whether the logic is correct and the loop runs without a human; this covers whether the process they drive is still there, which a green suite is silent on.
