---
description: Pre-mortem risk analysis - imagine the plan already failed, work backward to find every reason why. Classifies risks as Tigers / Paper Tigers / Elephants, synthesises most likely failure, most dangerous failure, and hidden assumption, then produces a concrete revised plan. Output goes to terminal (like /aristotle), not TEMP.
effort: high
argument-hint: "<plan, decision, or initiative to stress-test>"
when_to_use: "Use before any major implementation, architecture decision, ERP migration step, or commitment where the cost of being wrong is high. TRIGGERS: 'premortem this/the', 'run a premortem', 'stress-test this plan', 'what could kill this', 'find the blind spots', 'poke holes in this', 'what am I missing'. SKIP: vague ideas with no concrete plan, irreversible decisions already made, simple feedback requests."
---

# /premortem - Pre-Mortem Risk Analysis

A pre-mortem exploits prospective hindsight: people explain past events far better than they predict future ones. By placing the failure in the past (fictitiously), the analysis generates more specific, honest failure modes than "what could go wrong?" does. Gary Klein (HBR 2007); Kahneman called it his single most valuable decision-making technique.

Claude defaults to agreeable, optimistic analysis. The "this already failed" frame breaks that pattern.

---

## Step 0: Gather Context

Before running, scan what is already available:
- Read back through the current conversation for the plan, decision, or initiative
- Check for relevant workspace files (CLAUDE.md, memory files, project docs, TEMP files the user referenced)
- Use Glob/Read - spend at most 30 seconds on this

You need three things to proceed:
1. **What is it?** - describe it back in one sentence
2. **Who does it affect / who is involved?** - team, stakeholders, dependencies
3. **What does success look like?** - failure is the inverse of success

If one is missing, ask one question at a time. Infer from context wherever possible.

---

## Step 1: Set the Frame

State this explicitly before generating failure modes:

> "It is [timeframe] from now. [Plan name] has failed completely. [One vivid sentence describing the disaster.] We are looking back: what went wrong?"

**Timeframe guidance:**
- Technical / implementation plans: 2-6 weeks
- ERP migrations, architecture decisions: 1-3 months
- Strategic / business decisions: 3-6 months

Match to the plan's natural review horizon.

---

## Step 2: Generate Failure Modes (no filter, 8-12)

Generate every genuine failure mode. No filtering for likelihood at this stage. Cover all five categories:

| Category | Question to ask |
|---|---|
| **Execution** | What implementation step broke, took too long, or was done wrong? |
| **Technical** | What assumption about the system, tool, or data turned out to be false? |
| **People** | What coordination gap, ownership gap, or skill gap caused the failure? |
| **External** | What did an upstream dependency, teammate, or external actor do (or not do)? |
| **Assumptions** | What was the plan taking for granted that turned out not to be true? |

Each failure mode: 1-2 sentences, specific to this plan, grounded in actual details provided. If there are only 5 genuine failure modes, list 5. If there are 12, list 12. Do not pad or cut short.

---

## Step 3: Classify Each Failure Mode

**Tiger** - Real, evidence-backed risk. A specific, plausible failure scenario the team could describe concretely. Ignoring it would be negligent.

**Paper Tiger** - Sounds alarming but, on close inspection, is unlikely or low-impact. Often raised from general anxiety rather than specific knowledge.

**Elephant** - The thing everyone knows about but nobody says. Political, organisational, or interpersonal. Often the actual cause of failure when plans fail. Signal: the room goes quiet when this comes up.

For each Tiger, assign urgency:
- **Launch-Blocking** - plan must not proceed until this is mitigated
- **Fast-Follow** - must be addressed within 1-2 weeks of starting
- **Track** - monitor; address if it escalates

**Elephants require explicit handling:** Name them directly ("The plan assumes X, but nobody has said this out loud"). Assess: is this a Tiger in disguise? If yes, reclassify. If no, either assign an owner or consciously accept with documented rationale.

---

## Step 4: Synthesise

After classifying, produce:

**Most Likely Failure** - which Tiger has the highest probability given what you know? State why in one sentence.

**Most Dangerous Failure** - which Tiger would cause the most damage if it occurred, even if less likely? This is the one worth insuring against even at low probability.

**Hidden Assumption** - across all failure modes, what is the single biggest thing the plan takes for granted that has not been questioned? Often an Elephant in disguise. This is frequently where the real value of the pre-mortem lives.

**Revised Plan** - for each Launch-Blocking Tiger and the Most Dangerous Failure, one concrete action that reduces the risk. Not "consider X" - state specifically what to do, by when, and who owns it.

**Pre-Action Checklist** - 3-5 specific things to verify or put in place before executing. Each item must prevent or detect one identified failure mode.

**Revised Confidence** - after this analysis, how confident is the plan likely to succeed (score/10 with brief rationale)? What single change would raise confidence most?

---

## Step 5: Output to Terminal

Output the full pre-mortem directly to the conversation (terminal), same as /aristotle. **Do NOT write to a TEMP file.** Skills should put output in front of the user, not accumulate scratch files unless the artefact is genuinely a draft for editing or multi-line copy-paste content.

End with a 3-sentence summary: most likely failure, hidden assumption, single most important plan revision.

---

## Output Structure (in terminal)

# Pre-Mortem: [Plan Name]
Date: YYYY-MM-DD | Timeframe: [X weeks]

## The Plan
[One paragraph: what it is, who it affects, success criteria]

## Time Jump
It is [X] from now. [Plan name] has failed. [Vivid disaster sentence.]

## Failure Modes

| # | Category | Failure Mode | Classification | Urgency |
|---|----------|--------------|----------------|---------|
| 1 | Technical | ... | Tiger | Launch-Blocking |
| 2 | Assumptions | ... | Elephant | - |
| 3 | External | ... | Paper Tiger | - |

## Deep Dives (Tigers only)

### [Tiger Title]
**Story:** [2-3 sentences: how it actually played out]
**Underlying assumption:** [One sentence: what was taken for granted]
**Early warning signs:** [1-2 observable signals this is starting to happen]

## Synthesis

**Most Likely Failure:** ...
**Most Dangerous Failure:** ...
**Hidden Assumption:** ...

## Revised Plan

| Action | Addresses | Owner | By When |
|--------|-----------|-------|---------|

## Pre-Action Checklist
- [ ] ...

## Revised Confidence
[Score/10 + one paragraph: rationale and what raises it]

---

## Notes

- Do not sugarcoat. The point of a pre-mortem is to say things reality will say, before reality does.
- The synthesis is the product. Most readers skim failure modes and read the synthesis. Make it specific and actionable.
- Revised plan items must be concrete: "test with 5 pages before committing to the full backfill" beats "consider testing."
- Elephants are frequently the actual cause of failure when projects fail. Never skip the explicit Elephant check.
- This skill pairs well with /aristotle: run /aristotle first to stress-test the design, then /premortem to stress-test the execution plan.

$ARGUMENTS
