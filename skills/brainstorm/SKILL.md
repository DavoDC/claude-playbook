---
description: Structured idea generation for genuinely open-ended problems - Six Thinking Hats, SCAMPER, total negation, reverse brainstorming. Generates options; hand them to /prioritise to rank or /think to build.
effort: medium
argument-hint: "<the open question, or one candidate idea to generate variations from>"
when_to_use: "Use when the request is genuinely open-ended - 'think broadly', 'no constraints', 'what else could we do', 'brainstorm X', 'give me options', 'I'm stuck on how to approach this' - rather than 'pick from a known list'. Also use when ONE candidate exists and you want adjacent or better ones. Synergy: /brainstorm GENERATES, /prioritise RANKS what comes out, /think BUILDS the winner, /premortem attacks it, /aristotle deconstructs a problem that is not actually open-ended. Do NOT use when a single obvious next action already exists."
---

# /brainstorm $ARGUMENTS

Generate options for a genuinely open-ended problem, using a named method rather than free association.

## Step 0: Is this actually open-ended?

One question, and it is a real gate rather than politeness. Running a structured method over a decision that does not need one is pure overhead, and it is the fastest way to make a skill like this unwelcome.

- **A single obvious next action, or a low-stakes choice** -> stop. Say so, and do the thing.
- **Existing rules or principles being questioned** -> `/socrates`, which examines backward. Not this.
- **A design under concrete pressure** (a bug exposing a design flaw, a scope change, review push-back) -> `/aristotle`, which deconstructs forward. Not this.
- **A plan that already exists and needs attacking** -> `/premortem`. Not this.
- **Genuinely blank page, or one candidate wanting siblings** -> continue.

## Step 1: Pick ONE method, from the shape of the input

Do not run all of them. Each is a different tool, and running four is unconstrained listing with extra narration.

| Input shape | Method | Why this one |
|---|---|---|
| Blank page, no candidate yet | Free association or mind mapping, then SCAMPER once a first candidate exists | There is nothing to react to yet |
| Exactly ONE candidate, want adjacent or better | **SCAMPER** | Seven prompts that generate variations from a thing that exists |
| ONE idea to evaluate from every angle before committing | **Six Thinking Hats** | Stops an idea dying on the first objection, or passing on gut feel |
| Stuck inside one framing | **Total negation** | Separates load-bearing constraints from inherited assumptions |
| Safety, security or correctness work | **Reverse brainstorming** | Produces safeguards rather than features |
| An existing backlog or shipped thing, hunting the worst issues | **The Freeze** | Re-ranks by consequence rather than by count |

**State which method you picked and why, in one line, before running it.** A method chosen silently is indistinguishable from no method.

### Six Thinking Hats

Evaluate ONE idea from six separate angles, one at a time, instead of blending praise, critique and risk into a single unstructured judgement.

- **White, facts:** what do we actually know, verified rather than assumed?
- **Red, gut:** what is the immediate unfiltered reaction, excitement or unease?
- **Black, risk:** what could go wrong, who could this upset, what is the failure mode?
- **Yellow, benefits:** what is the best case, concretely, if this works?
- **Green, creative alternative:** is there a different shape of the same idea that dodges the Black-hat risk while keeping the Yellow-hat benefit?
- **Blue, process:** given all five, what is the actual next step and in what order?

The Green hat is where the value usually is, and it is the one people skip. Black followed by Green is the productive pair: an idea killed at Black without a Green pass has been rejected rather than improved.

### SCAMPER

Seven prompts for generating variations, useful once you have ONE candidate and want adjacent ones rather than a blank page.

- **Substitute** - swap one component for another.
- **Combine** - merge two separate ideas into one.
- **Adapt** - reuse a pattern from elsewhere for this purpose.
- **Modify** - change the scale, scope or frequency.
- **Put to another use** - what else could this capability be used for once it exists?
- **Eliminate** - what can be cut entirely, and does a smaller cheaper fix cover most of the value?
- **Reverse** - invert the direction. Start from the destination and verify backward to the source, rather than source-forward.

Reverse is the highest-yield prompt and the least natural. A worked instance: "verify the source matches what we exported" inverted to "verify what we exported matches what actually landed at the destination", which catches a completely different and real failure mode that the first check structurally cannot see.

### Total negation

Take a constraint the problem is framed by and remove it **absolutely**, not partially. Not to actually remove a real constraint, but to see which ones are load-bearing and which were inherited assumptions nobody re-examined.

A partial negation ("what if we had a bit more time") changes nothing. A total one ("what if this had to ship today" or "what if this constraint did not exist at all") changes the answer.

### Reverse brainstorming

Ask "how could we make this worse, or cause the exact failure we are trying to prevent?" then invert each answer into a safeguard. Better than forward brainstorming for security and correctness work, because failure modes are easier to imagine concretely than protections are.

### The Freeze

"Imagine this is frozen the moment it ships and we can never change it again. What MUST be fixed now?"

Re-ranks by consequence instead of by count or recency. What it pulls to the top: silent failures, data loss, security exposure, and anything whose blast radius grows with the user base. What it pushes down: tooling, tests, documentation polish, performance that is good enough, and features. If it can be fixed after release without anyone being harmed in the meantime, it is not freeze-critical.

Use it before a wider release, an upstream merge, a handover or an ownership transfer. **Do not paste the framing itself into a shared artefact**: it sharpens your judgement and reads as catastrophising in a pull request comment. Distil to the neutral finding first.

## Step 2: Generate past the comfortable stopping point

The first three ideas are the ones that were already implicit in the question.

**Keep going to at least eight before evaluating any of them.** Separate generation from judgement completely: an idea killed while it is still being written is an idea nobody got to build on, and it is the reason most brainstorms produce three options.

**Include at least one option you expect to reject, and say why you expect to reject it.** It marks the edge of the space, and occasionally it is the one that survives.

## Step 3: Hand off. Do not rank here

`/brainstorm` generates. `/prioritise` ranks. `/think` builds. Ending this skill with a ranked list would make it a worse version of a skill that already exists.

One exception for the handoff itself: when two or more genuine candidates compete for one scarce slot with differentiated stakes, run disqualifying gates before any scoring. Gates are pass or fail and are not averageable, so an idea that fails one is not rescued by scoring well elsewhere.

1. **Is it needed at all**, and could a cheaper approach plausibly handle it?
2. **Is this your call to make**, or someone else's system and decision? If the latter, the idea has to become a neutral input to their decision rather than a redesign pushed at them.
3. **Is there a real destination** for the result? No destination means delete or rescope now, not "work out delivery later".
4. **Does the proposed artefact match the actual need**, or does the need live one level down?
5. **Does the idea recreate the problem it is meant to solve?** A simplification that adds an abstraction layer. A cost-cutting measure that degrades the thing being protected. A scoring system whose own overhead becomes the waste it exists to prevent.

Score only the survivors, and **multiply rather than sum**, so a near-zero on any dimension correctly tanks the total instead of being averaged away.

**Re-apply the gates to the actual delivery shape, not the one-line pitch.** A candidate can pass every gate in summary while the detailed plan quietly reintroduces a violation. This is a recorded failure, not a hypothetical one.

## Step 4: Save the output before the context goes

Every surviving option lands on a real list in the same pass. Anything held only in conversation is lost at the next compaction.

**Rejected options get one line each with the reason.** A rejection with no recorded reason gets regenerated by the next brainstorm and costs the same effort twice.

## Related

- `docs/12-audit-lenses.md` "EXTREME lenses" - total negation made systematic, applied to an existing backlog rather than to a blank page.
- `/prioritise` - ranks what this produces.
- `/think` - builds the winner.
- `/premortem` - attacks the winner before you commit to it.
