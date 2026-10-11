# Part 20: The Commit-Anchored Delta Pattern

> **Field note.** Written from practice rather than machine-checked, and not covered by `tools/selftest.sh`. Last reviewed 2026-08-02 against Claude Code v2.1.220. Opinionated, and it may lag the harness.

Used by both `/reflection` and `/deep-dive`, this pattern applies to any repeating audit workflow.

**The problem:** re-reading everything on every reflection or audit wastes tokens, since most files haven't changed.

**The solution:** store an anchor after each run - a git SHA recording the state you last audited. Next time, `git diff <anchor>..HEAD` gives exactly what changed. Read only those files.

In practice an `audit.py` tool manages these anchors. Each scope/lens pair (e.g., `workspace:session-history content`) has its own anchor. Three outcomes when you query the delta:
- No prior anchor: full dive required
- Anchor exists, nothing changed: skip entirely
- Anchor exists, changes found: read only those files

So `/reflection` stays fast even when session-history.md has thousands of lines (it reads only new sessions), and two consecutive `/deep-dive` calls on the same scope skip the second unless something changed.

## Building Your Own Audit Tool

The core data structure: a JSON file mapping `scope:lens` -> `{sha, date, findings_path}`. On each audit run:

1. Run `git rev-parse HEAD` to get current SHA
2. If no prior anchor: audit everything, store current SHA
3. If prior anchor exists: `git diff <stored_sha>..HEAD -- <scope_path>` to get changed files
4. Audit only changed files
5. After audit: store new SHA as anchor

The lens (content/staleness/security/etc.) tracks different audit types separately: a content audit and a staleness audit of the same folder can sit at different anchors.

The delta says WHICH files to re-read, not what to ask of them; asking the same question of new files is how a fifth audit round confirms the fourth. [Part 13](13-audit-lenses.md) covers generating the questions before you scan and recording coverage so "have we looked at this" is answerable.

Reading the changed files is not the same as running them; see [Operate the tool, do not read it](14-reading-a-measurement.md#operate-the-tool-do-not-read-it).
