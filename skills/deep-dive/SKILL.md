---
description: Deep dive a topic, file, directory, or repo - think hard, investigate thoroughly, miss nothing
effort: high
argument-hint: "[topic, file-path, or repo-name]"
when_to_use: "Use for thorough investigation of any topic: security analysis, architecture review, code audit, file/repo audit, or decision review. For file/repo audits, use commit-anchored delta to avoid re-reading unchanged files. Think hard, fix issues found, commit in chunks. Synergy: if investigation surfaces 'should this exist?' or 'what is the right approach?', follow up with /aristotle. For building after the investigation, use /think."
---

# Deep Dive: $ARGUMENTS

Think hard about this. Investigate deeply. Do not miss things.

A deep dive is more than file auditing. It means thorough investigation of a topic, question, or concern. The scope could be a security analysis, an architecture question, a decision review, a code quality audit, or anything that needs careful thought.

## Phase 0: Commit-anchored delta (for file/repo audits)

Skip Phase 0 if the scope is a pure concept (architecture question, decision review). For audits of files, directories, or repos:

1. **Establish the last anchor.** Check when you last reviewed this scope - use a git SHA, a timestamp file, or a prior audit record. If no prior anchor: full dive, read everything.

2. **Get only what changed:**
   ```bash
   git log --name-only --pretty=format: <anchor>..HEAD -- <path> | sort -u | grep -v '^$'
   ```
   Review ONLY the files that changed. Re-reading unchanged files is exactly the waste this prevents.

3. **Also check deletions** (for impact analysis):
   ```bash
   git log --name-only --pretty=format: --diff-filter=D <anchor>..HEAD -- <path> | sort -u | grep -v '^$'
   ```

4. **Record a new anchor** after the dive (git SHA or timestamp) so the next run can delta from here.

## Investigation (Phase 1+)

1. **Understand what is being asked.** Arguments may be a question, concern, file, repo, or topic. Adapt.

2. **Think from first principles.** Do not just check checklists. What could go wrong? What assumptions are baked in? For complex decisions use `/aristotle`.

3. **Read only the delta files.** Phase 0 told you what changed. Trust it.

4. **Cross-reference and compare.** Check related repos, specs, docs. Look for inconsistencies and gaps.

5. **Use parallel agents** for large deltas (one per subdirectory or sub-topic).

## Types of Deep Dive

- **Security analysis**: threat model, attack surface, credentials, network exposure.
- **Code review**: correctness, edge cases, error handling, spec compliance.
- **Architecture question**: trade-offs, alternatives, first principles.
- **File/repo audit**: inconsistencies, stale content, broken references.
- **Decision review**: is this the right call? What are we missing?

## File Audit Checks

1. Filename vs content match
2. Cross-references (paths exist)
3. Stale counts (verify numbers)
4. Inconsistencies between files
5. Em dashes (U+2014/U+2013)
6. Wrong dates/versions
7. Security concerns (secrets, credentials)

## Output

- **Report findings** with file paths and line numbers.
- **Fix what you can** immediately. Do not just report.
- **Commit fixes** in logical chunks.
- **Generalize**: after fixing an issue, grep ALL repos for the same pattern.
- **Queue follow-ups** in pending-actions.

## Rules

- No em dashes anywhere.
- Think hard. Investigation, not box-ticking.
