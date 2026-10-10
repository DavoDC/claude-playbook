# Part 15: Verification and Iteration Habits

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

## A Bounded Search Cannot Prove an Absence

"Grep before claiming" covers presence. The absence case is more damaging: a bounded search finds nothing and the result is reported as "there is no such thing". A false positive gets discarded on the next line; a false negative closes the investigation, and the reader builds on the absence.

Every individual bound is reasonable, which is why it fails. `grep "end session"` misses `end-session`, `endsession`, `endSession` and `End Session`, and misses all of them again in a `.txt` file when limited to `*.md`. And the person whose data you search may already have noticed the problem and worked around it: filters, archiving habits, renaming conventions and routing rules relocate evidence out of where a naive search looks, and the more diligently someone organised around a problem, the more thoroughly that hides it. A mail search of a top-level inbox returns nothing when filing rules route everything into subfolders.

- Enumerate the variant axes **before** the pass: case, separators (space, hyphen, underscore, none), word forms (singular, plural, tense, gerund), partial forms inside longer identifiers, and surface (file types, directories, archives included or not).
- Before searching a user's data for evidence of a habit, find out what they built to cope with it (rules, filters, folder conventions); their fix has probably relocated the evidence.
- Take one of two exits: run the search unbounded and report the absence as a finding, or **state the bound in the same sentence as the answer**. "No hits under `docs/` in markdown files" is true. "There is no such rule" is untested.
- Treat a clean zero on a plausible query as a scope bug until proven otherwise, and re-run the search one notch broader before closing the investigation.

## Read the Payload Before Reusing a Known Cause

When a failure repeats, the cheapest and most dangerous hypothesis is the one already on file. A previously diagnosed cause explains the symptom at the right level of vagueness, but two different bugs can produce the identical user-visible failure, and only the full error payload distinguishes them.

The evidence is often already captured and unread: a stack dump, an argument list or an echoed value that states plainly, a few lines down, that the argument was a boolean where an object was expected. Its presence makes the situation feel already investigated.

Before reusing a previous diagnosis, ask what observation would distinguish the old cause from a new one, and check whether it is already sitting in output you have not read. If a failure repeats unchanged, read it more closely; never re-run it. That is the retry discipline in [Part 2](02-improvement-loop.md), applied to reading rather than re-attempting.

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

## Test Quality: A Green Run Is Not Evidence

"TDD always" is the most common workspace rule and the least self-enforcing, because coverage and test counts both rise when weak tests are added. A suite can grow while its ability to detect a defect stays flat. The question is whether each test would fail if the feature were broken.

Smells that pass a green run, in the tests:
- **Structural string-scan:** asserts the source text contains a function name or config key. Renaming a variable breaks it; shipping a bug does not.
- **Assertion-free:** calls the code and asserts nothing.
- **Dodger:** tests a helper, wrapper or re-implementation rather than the real entry point, so the tested and shipped paths differ.
- **Over-mocked:** exercises its own mocks, worst when a mock's signature has drifted from the real object so every real call would raise unnoticed.
- **Assertion roulette:** many unlabelled assertions in one test, so a failure does not say which behaviour regressed.
- **Meaningless but valid field:** a raw heap address rendered as a string, a `tostring()` dump standing in for a real value, or an integer enum shown as a bare number all satisfy "exists and has the right type". Read the actual value in the assertion, not its shape.
- **Invented fixtures only:** a suite built entirely on fixtures proves nothing about the real corpus, disk or store it protects, however well scoped each test. Every project needs at least one check, however coarse, that reads the real thing.
- **Coverage skew:** a high test count concentrated on easy pure functions while the main orchestration path and primary output writer sit at zero behavioural coverage. Look at what the suite covers, not how much.

Smells in the code under test, which a suite built around the intended failure will not notice:
- **A handler wider than the risk it guards.** Wrapping a whole loop or function body in try/except, rather than the one call that can fail, makes any unrelated exception (a console encoding error inside a stray `print()`) trigger the same fallback as the real failure. Scope every handler to the smallest block that can raise the error you handle.
- **A resolver that cannot tell absent from malformed.** See "Absent Is Not Malformed" in [Part 9](09-hooks-recipes.md#absent-is-not-malformed).

The strong version, in order: drive the **real entry point** production uses; mock **only true boundaries** (network, database, clock, auth, filesystem) and run everything inside for real; assert **observable outcomes** (returned value, written file, emitted record, resulting state) rather than call sequences, since asserting a call tests the implementation you wrote while asserting the outcome tests the behaviour you wanted; and **mutation-verify anything that matters** by reintroducing the bug, watching the test fail, then restoring the source. A test you have never seen fail is unverified, and checking takes seconds.

Watch for a suspiciously perfect result. A 100% match, zero-diff or "everything accounted for" on real data is what a self-comparison bug, a loose match key or a filter dropping the hard cases would also produce. Before reporting a clean result as good news, rule out the boring explanation. And when verification turns up a real defect, do not fix it in the same pass; hand the fix to a fresh check, since a fix validated by the reasoning that missed the bug is re-asserted, not verified.

**A test runner's own output needs the same design discipline as the code it tests.** Most frameworks print every test's chatter pass or fail, so the log a human or agent must read is mostly noise. Use a runner that captures each test's console output, discards it on a pass, and surfaces it with the failure message only on failure: `[PASS] name` on success, the captured trace plus `[FAIL] name: reason` on failure. Failures get more context, since the trace is no longer interleaved with passing traces. Put the pass/fail counts and overall result on the LAST lines, never the first, so a human or script can `tail` the file for the answer.

## The Bottleneck Is Often a Human Action, Not Model Budget

Budget readouts measure whether the model has capacity left. Also check the opposite: whether finished work sits idle waiting on a small human action (a click, a yes/no answer, plugging something in, approving a change). It is easy to miss, because when budget is healthy the instinct is to keep building, the wrong response to a queue never blocked on building.

Keep an explicit ranked list of "waiting on a human action" items and work it down before starting new work, as you would check the budget axes. The two constraints are measured by different instruments: nothing shows how much finished work is parked behind a click. When usage is well under the ceiling and output still feels stalled, look there first.

This is not an argument against delegating when delegation is right; see [Part 13](13-multi-agent-orchestration.md#when-to-delegate-vs-do-it-directly). It is an argument for checking, before delegating or building more, whether the bottleneck is capacity to build or a short list only a human can finish.
