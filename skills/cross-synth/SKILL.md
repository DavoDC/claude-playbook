---
description: Cross-synthesise any set of things (repos, files, docs, patterns, configs, tests, features) to find similarities, differences, gaps, and opportunities. General-purpose pattern-matching across multiple subjects. Like /deep-dive but for comparing N things sideways rather than one thing deeply.
effort: medium
argument-hint: "[subjects to compare, e.g. 'tests' | 'auth' | 'RepoA RepoB']"
when_to_use: "Use when comparing multiple subjects side-by-side: test coverage across repos, auth patterns across tools, config consistency, security controls, documentation completeness, or any 'does X do the same thing as Y?' question. Supports natural language like /cross-synth tests, /cross-synth auth, or /cross-synth <subjects...>."
---

# /cross-synth - Cross-Synthesis

Compare any N subjects (repos, files, documents, configs, processes, features, test suites) side-by-side. Find what's shared, what's missing, what's inconsistent, and what one subject can teach the others.

**This is horizontal analysis.** `/deep-dive` goes deep on one thing. `/cross-synth` goes wide across many.

---

## When to use

- "Do RepoA and RepoB handle auth the same way?"
- "Cross-synthesise the test coverage across all three repos"
- "Compare the error handling patterns across these files"
- "What can RepoA's upload deduplication teach RepoB?"
- "Are our security controls consistent across tools?"
- "Compare how each tool handles config validation"
- "Any time I want to know if the other repos are doing something the same as/better than this one"

---

## Input parsing

- **No args:** Ask what to compare (subjects or theme).
- **`/cross-synth [theme]`:** Cross-synthesise a specific theme (e.g. `auth`, `error-handling`, `config`, `security`).
- **`/cross-synth <subject1> [subject2] [...]`:** Compare the listed subjects. Can be repos, file globs, doc paths, or abstract topics.
- **`/cross-synth [description of what to compare]`:** Natural language works - parse the intent and proceed.

---

## The Process (5 phases)

### Phase 1 - Inventory

For each subject, collect the raw material:
- Code: grep for patterns, function signatures, class names, test names
- Docs: read the key sections
- Config: read the schema and defaults
- Tests: extract class names and test method names

Collect with minimal reading - just enough to see the shape of each subject.

### Phase 2 - Classify

Choose a classification dimension appropriate to the subject:

| Subject | Good dimensions |
|---|---|
| Test coverage | by theme (auth/pagination/cache/error-handling/...) |
| Auth patterns | by stage (discovery/token-request/refresh/revoke/...) |
| Config | by category (required/optional/security/format/...) |
| Error handling | by error class (network/auth/not-found/rate-limit/...) |
| Security controls | by threat (injection/auth-bypass/data-leak/...) |
| Documentation | by section (setup/usage/troubleshooting/security/...) |

Pick 5-10 dimensions. More is noise.

### Phase 3 - Build the matrix

One column per subject. One row per dimension. Mark each cell:
- **Y** / **STRONG** - well covered, multiple examples
- **partial** / **weak** - some coverage, gaps visible
- **N** / **NONE** - absent
- **N/A** - doesn't apply by design (document WHY so it's not re-flagged)

Note **by-design differences** explicitly - they are as important as the gaps.

### Phase 4 - Gap analysis

For each empty/weak cell, evaluate:
1. **Is the gap by design?** Document it and move on.
2. **Is it a real gap?** The behaviour exists but isn't covered/documented/implemented.
3. **What would filling it look like?** Be specific: function name, file, scenario.

Priority tiers:
- **HIGH:** Silent failure mode (data loss, security bypass, hard-to-diagnose bug)
- **MEDIUM:** User-visible failure, diagnostic friction, maintenance burden
- **LOW:** Nice-to-have, defensive depth, future-proofing

### Phase 5 - Synthesis

Two outputs:

**Gap list (actionable):** For each HIGH/MEDIUM gap, one specific recommendation:
```
[SUBJECT] [DIMENSION]: <what to add/change>
- Where: `<function/file>`
- What: <specific change - not vague>
- Why: <silent failure mode or user impact>
- Effort: S/M/L
```

**Insight list (learning transfers):** What did Subject A teach us about Subject B?
```
Subject A does X well -> Subject B should adopt the same pattern
```

---

## Output format

```
## Cross-Synthesis: [subjects] - [dimension/theme]

### Coverage Matrix
[table]

### By Design (not gaps)
- [pattern]: [why it's intentional in each subject]

### Gaps
**HIGH**
- [Subject] [theme]: [description]
  - Where: [file/function]
  - What: [specific fix]
  - Effort: S/M/L

**MEDIUM**
[same format]

### Learning Transfers (what each subject can teach the others)
- [Subject A] -> [Subject B]: [what to adopt]

### What's working well (reinforce)
- [shared pattern that all subjects do correctly]
```

---

## Implement mode (`/cross-synth [args] --implement`)

If asked to implement:
1. Pick the single highest-priority gap
2. TDD: write failing test first
3. Confirm it fails (proof of gap)
4. Implement or document why no fix needed
5. Run full suite, confirm 0 regressions
6. One repo per session - don't scatter changes

Never implement without `--implement` or explicit instruction. Default is analysis only.
