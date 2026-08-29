# Part 4: The /dev-session Skill - Smart Session Composition

> **Core.** Part of the maintained quick-start path. The tools and settings snippets it references are asserted by `tools/selftest.sh` on every push.

`/dev-session <repo>` is the most valuable skill for actual project work. It is not just "start coding" - it is a full structured workflow that picks the right work, manages scope, enforces TDD, tracks budget, and closes out properly.

## What Problem It Solves

The failure mode it prevents: starting a session without a clear item, doing something vaguely related to the project, spending tokens on the wrong thing, and ending with nothing cleanly shipped. Having the session structured around a definite scope contract is worth the overhead.

## How It Integrates With IDEAS.md

`/dev-session` does not decide what to work on. It reads the ordering IDEAS.md defines and takes the top actionable item, deriving its purpose from the file rather than from conversation context. The contract for what IDEAS.md is and how that ordering works is defined once, in [Part 3 - How IDEAS.md and /dev-session Work Together](03-ideas-and-roadmap.md#how-ideasmd-and-dev-session-work-together); it is not restated here, because a contract stated in two places is a contract that will eventually disagree with itself.

---

## The Phase Walkthrough

### Phase 0 - Locate and Orient

Resolves the repo path (checks a repo index first, falls back to filesystem). Reads CLAUDE.md - if it's missing, stops. Then checks for unprocessed `feedback_*.txt` files. If any exist, it stops and says so: feedback files update IDEAS.md, so IDEAS.md is stale until they're processed.

### Phase 1 - Budget Check + Pick the Item (MANDATORY STOP GATE)

Before picking any item, checks current budget state (see [Part 5](05-budget-awareness.md)):
- If 5-hour rate >= 83%: abort the session entirely, schedule a wakeup for after reset
- If 7-day rate >= 85% or context >= 80%: pick quick-win only, warn
- If 7-day >= 70% or context >= 60%: proceed with caution, smallest item only
- Otherwise: normal session, intelligent batching allowed

Then scans IDEAS.md top to bottom: TIER 0 blocking bugs first, then TIER 1, then quick wins. Never picks something vague or low priority while TIER 0 items exist. If nothing actionable is found, stops and says so rather than guessing.

**Intelligent batching:** after picking the primary item, it decides whether to add a secondary item based on token budget, causal linkage, and complexity. Two causally linked items in one session is fine; two unrelated TIER 0s from different subsystems is not - it pollutes the commit history and makes it hard to understand what caused what.

### Phase 1b - Scope Definition (Committed Before Any Code)

Writes a one-sentence scope statement with explicit IN/OUT lists before reading any code:

```
SCOPE: Fix duplicate detection - handle featured artists in track names
IN SCOPE: regex pattern fix in duplicate_detector.py, test coverage
OUT OF SCOPE: tag fixing, routing changes, anything in the sync tool
```

This is committed as `scope: ...` before implementation begins. It forces clarity upfront. High scope churn (lots of IDEAS.md changes mid-session) is a signal that scoping was skipped.

### Phase 2 - Test Plan First (TDD Gate)

Before reading any implementation code, designs 3-5 test scenarios that must pass. Writes test stubs (names only, no implementation), commits them, then reads the code. This is strict TDD - test design happens while understanding of the problem is fresh and unconstricted by the existing implementation.

### Phase 3 - Implement

Follows TDD: write the failing test first, implement to make it pass, run tests. Never declares done with failing tests.

One gap TDD alone does not close: a language the workspace has no local interpreter, compiler, or linter for. "The tests pass" and "the file is syntactically valid" are different claims, and a manual delimiter count - do the braces balance, do the quotes look closed - answers neither reliably past a few dozen lines, because a human scanning a diff is bad at exactly the kind of counting a parser does for free. Before declaring generated code in an unfamiliar language done, install a throwaway real parser or linter for it - a compiler's check-only mode, a language server, or a minimal standalone parser package usually takes under a minute to add - rather than trusting eyeballed delimiter matching. A several-hundred-line script had been "verified" this way, by manual counting alone, for some time before an actual parser was installed and surfaced real syntax defects within a minute of running it.

### Phase 4 - Verify in Real Environment

Tests passing in isolation is not enough. Asks the user to confirm the thing works end-to-end before closing out. Also audits the README: if a new feature shipped, the README should reflect it.

### Phase 5 - Close Out

Moves completed item(s) from IDEAS.md to HISTORY.md. Evaluates whether to continue in the same session or drain (based on budget and whether the next item is causally linked or independent - unrelated items drain now to keep each session's outcome clean).

### Phase 10 - Rule Capture (Mandatory)

At the end, scans session output for transferable lessons: surprising gotchas, edge cases, diagnostic approaches, generalizable patterns. For each lesson, creates or updates a feedback file. If lessons are found but no rule files created, the session cannot end. This is the enforcement mechanism for the improvement loop.

---

## Building Your Own /dev-session

The phases above are the spec. Implement them as a SKILL.md file in `.claude/skills/dev-session/SKILL.md`. Key things to encode:

1. **The budget gate is non-negotiable.** Without it, the skill will start work at 90% rate limit and get throttled mid-session. See [Part 5](05-budget-awareness.md) for how to wire it in.

2. **The scope commitment step prevents the most waste.** Every time this step is skipped, the session ends with a messy diff and unclear commit messages. Force it.

3. **IDEAS.md must be the single source of truth.** Never ask the user "what do you want to work on?" - read IDEAS.md. If IDEAS.md is empty or unclear, ask the user to order it, then start.

4. **Phase 10 is the improvement loop made mandatory.** If there are no feedback files created and no rule captures, the session failed at its meta-level goal even if the code shipped.
