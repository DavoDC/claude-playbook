---
description: Pre-commit validation - verify workspace rules are followed before pushing. Checks repo index, pending-actions discipline, scope documentation, TDD ratio, and rule file changes.
---

# /validate-rules

Pre-commit validation gate. Run BEFORE `git push` to catch rule violations early.

```bash
/validate-rules [repo]
```

**Output:** Check results (pass / fail / warning) with actionable fixes.

---

## Checks Performed

### 1. Learnings Without A Rule File
- Do this session's commit messages mention a learning, correction, finding or lesson while no rule file (`feedback_*.md`, enforced-rules, CLAUDE.md) changed?
- FAIL: `git log` since session start mentions one, `git diff --name-only` shows no rule file touched
- FIX: Write the feedback file now, while the incident is still in context
- WHY: This is the improvement loop's actual leak. A learning that stays in the transcript is lost at the end of the session, and nothing else in the workflow notices it went missing.

### 2. Scope Documentation (if /dev-session session)
- Did this session include a scope commit?
- FAIL: `git log --oneline | grep scope:` returns nothing
- WARNING: Scope found but no updates during session
- PASS: Scope defined and documented

### 3. TDD Ratio (if code commits present)
- Count test commits vs feature commits
- FAIL: Test commits < 10% of feature commits
- WARNING: Test commits 10-25% (minimum acceptable, could be better)
- PASS: Test commits >= 25% of feature commits

### 4. Rule File Changes (if learnings found)
- Are there any commit messages mentioning learnings, findings, patterns, edge cases?
- FAIL: Learnings found but NO rule files updated
- PASS: For each learning, at least one rule file changed (enforced-rules.md, feedback/, CLAUDE.md)

### 5. Em-Dash Check
- Scan staged files for Unicode em/en dashes (U+2014, U+2013)
- FAIL: Em-dashes found
- PASS: Only regular hyphens (-) found

### 6. Pending-Actions Discipline
- If this repo appears in a cross-repo pending-actions file: FAIL (repo-specific tasks belong in the repo's own IDEAS.md)
- PASS: No repo-specific entries in cross-repo task list

---

## Automation

**Add to your workflow:**
```bash
# Before every git push, run validation
/validate-rules
# Fix any issues
git add [fixed files]
git commit -m "fix: address validation warnings"
git push
```

---

## Notes

- This skill is READ-ONLY (no modifications). It reports findings only.
- Fixes are usually single commits (add to index, update scope, etc.)
- For TDD ratio failures: re-run /dev-session with TDD gate to improve ratio on next feature
- For rule file failures: a rule capture step in /dev-session should have created them
