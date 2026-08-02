---
description: Deep investigation of a topic, file, directory or repo. Generates lenses before scanning, reads only the delta since the last dive, and reports coverage as well as findings.
effort: high
argument-hint: "<topic, question, file, directory or repo>"
when_to_use: "Use for thorough investigation of anything: security analysis, architecture review, code audit, file or repo audit, decision review. For a repo or file audit it uses a commit-anchored delta so repeating it is cheap. Synergy: /aristotle if the investigation surfaces 'should this exist?', /think to build afterwards, /brainstorm if the problem turns out to be open-ended rather than investigative, /prioritise to rank what comes out."
---

# /deep-dive $ARGUMENTS

Thorough investigation. Not box-ticking, and not a read-through with a summary at the end.

Two things make this different from asking for a careful look. It reads only what changed since the last dive of the same scope, and **it decides what to ask before it decides what to read.**

## Phase 0: Scope, delta, and lenses

Skip only the delta step if the scope is a pure concept, an architecture question or a decision review. Never skip the lens step.

### 0a. Name the scope and get the delta

Scope format: `<repo>` or `<repo>:<path>`. Look up the last recorded commit anchor for this scope, and list the files changed since. **Read only those.** That is the entire point of the anchor.

If the stored anchor no longer exists in the history, report that distinctly. It means the history was rewritten or the clone was replaced, and every file must be treated as changed. Silently reporting everything as changed, or nothing, both hide a real event.

### 0b. Generate lenses BEFORE scanning, and rank them

**Generating lenses and generating findings are different activities. Doing the first one first is what breaks out of the previous pass's blind spot.**

Read `docs/12-audit-lenses.md` and walk its generator rather than picking from a list:

- **The matrix.** SUBJECT (product code, tests, the instrument, config, data and output, docs, the usage surface, dependencies and platform, history and process, our own recent changes, the audit itself) crossed with QUESTION (correct, fails safely, honest, consistent, usable, fast enough, secure, missing).
- **The people.** A first-time user, a security reviewer, someone debugging at two in the morning with only the log, a packager, someone on the other operating system, someone with narrower permissions, the team inheriting it, yourself in a year.
- **Cross-synthesis.** Put this beside a comparable thing and the differences generate the questions for free. Run it both ways.

Then **rank candidates by expected yield and state plainly which you are NOT applying and why.** A skipped lens with a reason is a decision. An unlisted lens is a blind spot.

Bias toward HONEST, MISSING and USABLE. They are the highest-yield and the least natural to ask. Treat a plan that is mostly CORRECT as a plan to confirm what the last pass said.

### 0c. If the thing RUNS, operate it before reading it

One small real invocation, on real data, whose output you can verify arithmetically by hand.

**Validate the instrument first.** Confirm the invocation actually exercises the path you think it does, and that both sides of any before-and-after comparison are the same shape. Two prior attempts at this produced clean-looking and entirely invalid results by skipping this.

Then check every printed number against what you can count yourself. A finding derived purely from logs or source is a hypothesis until something runs.

## Phase 1: Investigate

1. **Understand what is actually being asked.** The argument may be a question, a concern, a file, a repo or a topic. Adapt.
2. **Think from first principles.** What could go wrong? What assumptions are baked in? What is true only at a boundary: empty input, exactly one item, the first run, the last item, a resumed run, a clock change?
3. **One read-only agent per lens, in parallel**, for anything large. A cheaper model does the reading; you keep the judgement, the verification, the fixes and the commits. Do not let the agents edit: it causes mid-audit conflicts and it moves judgement to the wrong place.
4. **Every agent prompt has five parts.** Name and fence the cell ("do not report correctness bugs, that is another cell"). State what a prior round already found there and declare it out of scope. Demand a method rather than a verdict. Require the clean answer explicitly, or an agent with no permission to find nothing will invent something. Require file and line for the claim AND for the evidence.
5. **Give every agent the irreversibility framing** for anything heading to a release, a merge or a handover: "if we could never change this file again, what MUST be fixed now?" Ranks by consequence rather than by count.

## Phase 2: Verify before acting

**Every report is a claim, not a result.**

Expect a real verification failure rate and budget for it. In one measured round, two of seven agent reports contained at least one claim that did not reproduce, both confidently stated with plausible evidence. **A report's own confidence carries no information about which claims will hold.**

Two specific checks, both cheap and both learned the hard way:

- **Re-check any log-mined finding against current state.** Logs are history. One round reported a config entry broken for three weeks with forty-nine log files as evidence; it had already been removed, and one grep of the current config disproved it.
- **Try to refute your own finding before reporting it.** When a hypothesis fails its own reproduction, do not fix on it anyway.

## Phase 3: Fix, and generalise every fix

- **Fix what you can. Do not just report.** Commit in logical chunks.
- **Every fix is a class, not an instance.** Express the defect as a greppable pattern and sweep the file, the repo, then the sibling repo. If you cannot write the grep, you have not understood the defect yet.
- **Prefer a safe default to a remembered rule.** If the fix could be a default, a guard or a required argument instead of a note telling someone to be careful, make it the default.
- **Route what you do not fix**, immediately, to the backlog. Never drop a real finding because it was inconvenient to fix today. A high-regression-risk file deserves a precisely written backlog item and a deliberate pass, not a rushed change under the same time pressure its own history warns about.

## Phase 4: Close the pass

All five, and all five were learned by skipping them.

1. **Check file ownership before assigning work, not after reading the reports.** Findings in files owned by someone else's open pull request cannot be fixed, and that is knowable up front.
2. **Run ONE extreme lens over the resulting BACKLOG, not over the code.** See Part 12. Cheapest step in the process and the only one that improves items you are not touching. Record what moved. "Nothing moved" is a real result.
3. **Audit your own CAPTURE as a separate step, after the fixing.** Fixing is absorbing: what you act on gets remembered and what you defer evaporates into a report nobody reopens. Grep the backlog for a distinctive phrase from each finding rather than trusting recall. One round's capture check found six findings missed entirely, a better return than any single lens.
4. **Record the new anchor** for this scope so the next dive reads only the delta.
5. **Update the coverage record**, from verified results, at the end. Never from intent at the start.

## Output

The report has two halves and both are required.

**Findings**, with file and line, ranked by consequence rather than by count. State how many of them a user could ever actually reach; maintainability findings are real work but should not be counted against the same yield as a data-loss finding.

**Coverage.** Which cells were walked, which were deliberately skipped and why, and which are not applicable. **An audit with no coverage statement cannot be built on by the next one**, which is how successive rounds re-walk the same few cells and conclude the artefact is clean.

## Rules

- Never re-read files outside the delta. That is the whole point.
- A subject examined under one question has NOT been examined under another. "We already audited the code" is never a reason to skip the code.
- If a defect escaped a cell your record marks as walked, mark that cell **weak**. Do not quietly restore it. A false green misdirects every later pass, not just this one.
