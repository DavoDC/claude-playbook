---
description: Deep dive a topic, file, directory, or repo - think hard, investigate thoroughly, miss nothing
---

# Deep Dive: $ARGUMENTS

Think hard about this. Investigate deeply. Do not miss things.

A deep dive is more than file auditing. It means thorough investigation of a topic, question, or concern. The scope could be a security analysis, an architecture question, a decision review, a code quality audit, or anything that needs careful thought.

## Investigation

1. **Understand what is being asked.** Arguments may be a question, concern, file, repo, or topic. Adapt.

2. **Think from first principles.** Do not just check checklists. What could go wrong? What assumptions are baked in? For complex decisions use `/aristotle`.

3. **Read thoroughly.** For file/repo audits, read what changed (git log/diff). For concept questions, gather the relevant context.

4. **Cross-reference and compare.** Check related repos, specs, docs. Look for inconsistencies and gaps.

5. **Use parallel agents** for large investigations (one per subdirectory or sub-topic).

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
- **Generalize**: after fixing an issue, grep all repos for the same pattern.
- **Queue follow-ups** in pending-actions.

## Rules

- No em dashes anywhere.
- Think hard. Investigation, not box-ticking.
