---
description: Full first-principles build workflow - Aristotle deconstruction then 5-step engineering algorithm then instantiation check. The three Core Thinking Principles in one invocable skill.
effort: xhigh
argument-hint: "<problem, design decision, or thing to build>"
when_to_use: "Use when designing or building anything non-trivial: new feature, new skill, new process, architecture decision. Chains /aristotle (strip assumptions, rebuild from zero) with the 5-step engineering algorithm (question->delete->simplify->accelerate->automate) and the instantiation check (does the fix embody what it prevents?). Use /aristotle alone for pure deconstruction. Use /prioritise alone for ranking. /think is for building. Use /socrates to EXAMINE existing rules/principles (not build new ones - if /aristotle's Phase 0 routes to /socrates, /think does not apply)."
---

# /think $ARGUMENTS

The three Core Thinking Principles as one workflow. Run in order - do not skip phases.

**Synergy:** /aristotle is the deconstruction engine (for new design OR existing systems under concrete pressure). /socrates is the examination engine (for existing rules/principles WITHOUT concrete pressure - /aristotle's Phase 0 routes there). /prioritise is the ranking interface. /think is the build interface that chains /aristotle + 5-step + instantiation. **If /aristotle Phase 0 routes to /socrates, /think does not apply** - the input was examine-shaped, not build-shaped. Run /socrates directly and return.

## Step 1: Aristotle First Principles

Invoke `/aristotle` on the problem. Full 5-phase deconstruction:
- Assumption autopsy
- Irreducible truths
- Reconstruct from zero (3 candidates)
- Assumption vs truth map
- The Aristotelian Move (single highest-leverage action)

## Step 2: 5-Step Engineering Algorithm

Apply to the Aristotelian Move (Phase 5 output). In order - do not skip, do not reverse:

1. **Question** - is this actually needed? Whose need does it serve?
2. **Delete** - actively try to remove 10% of it. If nothing was deleted, you haven't deleted enough.
3. **Simplify** - for what remains: fewer steps, fewer dependencies, shorter.
4. **Accelerate** - make the remaining essential parts faster.
5. **Automate** - last. Never automate what should be deleted.

## Step 3: Instantiation Check

Before shipping: **does the solution embody the problem it prevents?**

- A security rule that requires trusting untrusted input = instantiates the problem.
- A complexity-reducing refactor that adds a new abstraction layer = instantiates the problem.
- A feedback file about not duplicating content that duplicates content = instantiates the problem.

If yes: redesign. Demand elegance.

## Final gate

"Would I design this differently now?" If yes - redesign before shipping.
