---
description: Read recent session history, find patterns, update workspace config and memory. Delta-first - only reads sessions since last reflection.
---

# /reflection

Extract improvements from recent sessions and apply them to the workspace. The self-improving feedback loop made explicit.

## When to run

Every 5-10 sessions, or after any significant block of work. More often than that wastes tokens re-reading unchanged history.

---

## Steps

### 1. Find what's new since last reflection

If you track a `last-reflection-sha` file:
```bash
git log $(cat memory/last-reflection-sha.txt)..HEAD --oneline -- memory/session-history.md
```

If no prior anchor: read the last 10-15 sessions from `memory/session-history.md`.

### 2. Read only the new sessions

Extract sessions added since last reflection. For each session, look for:

- **Repeated corrections** - same behavior corrected 2+ times = should be a rule
- **Successful patterns** - technique that worked well, worth naming and keeping
- **Implicit preferences** - things you said yes to without ever writing them down
- **Skills or tools built** - not yet documented anywhere

### 3. Route each finding

| Finding type | Where it goes |
|---|---|
| Correction repeated 2+ times | `memory/feedback/feedback_<topic>.md` |
| Cross-cutting hard rule | `.claude/rules/enforced-rules.md` |
| CLAUDE.md principle | workspace `CLAUDE.md` |
| Context/memory fact | `memory/MEMORY.md` + linked file |

### 4. Make the updates

Write each file. Keep changes minimal - one rule per feedback file, one principle per CLAUDE.md addition.

### 5. Record the anchor

```bash
git rev-parse HEAD > memory/last-reflection-sha.txt
```

Next reflection uses this to skip already-reviewed sessions.

### 6. Commit

```
mem: reflection - N sessions reviewed, M improvements applied
```

---

## Output

Brief summary: sessions reviewed, patterns found, files updated. If nothing found: say so - that's signal too (the workspace is stable).

---

## What makes a good reflection

The value is in the routing decision. A correction that happened once might be noise. Twice is a pattern. Three times is a rule that belongs in enforced-rules.md. 

Don't make CLAUDE.md additions too specific ("when user says X, do Y"). Make them principles ("always do Z when approaching type-of-situation"). Specific rules go stale; principles don't.
