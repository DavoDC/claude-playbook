---
description: Audit and rewrite text to remove AI writing patterns - for letters, emails, messages, READMEs, or anything written to a person
---

# Human Voice: Remove AI Writing Patterns

Audit and rewrite any text to sound like a person wrote it, not an AI. Use for letters, emails, messages, Ko-fi descriptions, GitHub READMEs, or anything written to another person.

Adapted from: https://github.com/conorbronsdon/avoid-ai-writing (v3.3.1, MIT)

---

## Modes

**rewrite** (default) - flag AI patterns and return a clean rewritten version.

**detect** - flag patterns only, no rewriting. Use when you want to see what's flagged and decide yourself, or for text you didn't write.

Trigger detect mode when user says: "detect", "flag only", "audit only", "just flag", "scan", or "what AI patterns are in this".

---

## Auto-detect context

Infer the context from the content if not specified:

| Signal | Context |
|--------|---------|
| Salutation ("Hi X", "Dear X") or sign-off | personal-message |
| Short + casual, no structure | casual |
| Ko-fi / GitHub README / public post | public-content |
| No strong signals | personal-message (default for this skill) |

---

## What to fix

### Always flag - Tier 1 words (replace on sight)

| Replace | With |
|---------|------|
| delve / delve into | explore, look at, dig into |
| landscape (metaphor) | field, space, industry |
| realm | area, field |
| paradigm | model, approach |
| embark | start, begin |
| testament to | shows, proves |
| robust | strong, reliable |
| comprehensive | thorough, complete |
| cutting-edge | latest, newest |
| leverage (verb) | use |
| pivotal | important, key |
| underscores | highlights, shows |
| meticulous / meticulously | careful, precise |
| seamless / seamlessly | smooth, easy |
| game-changer | say specifically what changed |
| utilize | use |
| nestled | is in, sits in |
| vibrant | (describe what makes it active, or cut) |
| thriving | growing, active |
| showcasing | showing, demonstrating |
| deep dive | look at, examine |
| unpack | explain, break down |
| intricate / intricacies | complex, detailed |
| ever-evolving | changing, growing |
| holistic | complete, full |
| actionable | practical, useful |
| impactful | effective, significant |
| learnings | lessons, findings |
| best practices | what works, standard approach |
| at its core | (cut - just state the thing) |
| synergy | describe the actual combined effect |
| in order to | to |
| due to the fact that | because |
| serves as | is |
| features (inflated) | has, includes |
| boasts | has |
| commence | start |
| ascertain | find out, determine |
| endeavor | effort, attempt, try |
| embrace (metaphor) | adopt, use, switch to |

### Flag when 2+ appear in the same paragraph - Tier 2

harness, navigate, foster, elevate, unleash, streamline, empower, bolster, spearhead, resonate, revolutionize, facilitate, nuanced, crucial, multifaceted, ecosystem (metaphor), myriad, plethora, encompass, catalyze, reimagine, cultivate, illuminate, transformative, cornerstone, paramount, poised, burgeoning, overarching

### Chatbot artifacts - always remove

"I hope this helps!", "Certainly!", "Absolutely!", "Great question!", "Feel free to reach out", "Let me know if you need anything else", "Happy to help", "Of course!", "Definitely!"

These are chat interface tics. Remove entirely from anything written to a person.

### Sycophantic openers - remove

"That's a great point", "You're absolutely right", "Excellent question" - in a letter or message these sound fake. Just respond to what was said.

### Transition phrases - rewrite or cut

"Moreover", "Furthermore", "Additionally" - restructure so the connection is obvious, or use "and", "also".

"In today's X" / "In an era where" - cut or state specific context.

"It's worth noting that" / "Notably" - just state the fact.

"In conclusion" / "To summarize" - your ending should speak for itself.

"When it comes to" - just talk about the thing directly.

"At the end of the day" - cut.

"That said" / "That being said" - cut or use "but" / "however". Don't overuse.

### Formulaic patterns to remove

- "Whether you're X or Y" - false breadth. Pick the actual audience.
- "I recently had the pleasure of X-ing" - just say what happened: "I talked to", "I read".
- "Here's what I found interesting" - just say the interesting thing.
- "Let's explore / Let's take a look / Let me walk you through" - just start with the point.
- "Step 1: / Step 2:" visible reasoning chains in prose - state the conclusion then the reason.

### Significance inflation

"Marking a pivotal moment", "a watershed moment", "this is truly remarkable" - inflates ordinary events. State what happened and let the reader judge.

### Generic endings - cut or make specific

"The future looks bright", "Only time will tell", "As we move forward", "I look forward to hearing from you" (if it's filler not genuine). End with something specific to what was said.

### Acknowledgment loops - cut

"You're asking about", "To answer your question", "The question of whether" - restating the prompt before answering. Just answer.

### Vague attributions

"Experts say", "Studies show", "Research suggests" without a source - either cite specifically or state the claim directly.

### Structural tells

- **Uniform paragraph length** - vary deliberately. Some one-sentence paragraphs. Some longer. If every paragraph is the same size, fix it.
- **Excessive bullet lists** - for personal messages, prose is almost always better than bullets. Bullets only if genuinely listing discrete items.
- **Bold overuse** - in a letter or email, almost never bold anything.
- **Too many headers** - personal messages and letters don't have section headers. Remove them.
- **Formulaic opening** - don't open with broad context. Lead with the actual thing you're saying.

### Missing human voice

- **No opinions** - AI is relentlessly neutral. If the author has a view, it should be in the text.
- **Over-polished** - natural disfluency, informal phrasing, and the odd imperfect sentence are what make text sound human. Don't sand away all personality.
- **Sentence length uniformity** - mix short punchy sentences (3-8 words) with longer ones. Fragments are fine. Vary it.

---

## Severity

**P0 - fix immediately:** chatbot artifacts, vague attributions without source, significance inflation on minor things.

**P1 - fix before sending:** Tier 1 word violations, formulaic openers/closers, acknowledgment loops, excessive bullets/headers in personal text.

**P2 - polish if time:** generic transitions, uniform paragraph length, copula avoidance (serves as, boasts, features).

---

## Output (rewrite mode)

1. **Issues found** - bullet list of every AI pattern, with the offending text quoted.
2. **Rewritten version** - full clean version. Preserve all specific facts and the original intent.
3. **What changed** - brief summary of major edits.
4. **Second-pass audit** - re-read the rewrite, catch anything that survived. Fix inline and note what changed. If clean, say so.

## Output (detect mode)

1. **Issues found** - bulleted, grouped by severity (P0/P1/P2), offending text quoted.
2. **Assessment** - for each flag: clear problem, or judgment call? Note which ones must fix vs. worth a second look.

---

## Tone goal

Direct. Specific. Sounds like a real person wrote it, not an AI assistant. Vary the rhythm. Be concrete. Have opinions where appropriate. The text should sound like a real person talking to another real person.

If the original is already strong, say so and only cut what needs cutting. Don't over-edit.
