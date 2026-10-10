# Part 10: Privacy Hooks for a Public Repo

> **Field note.** Written from practice rather than machine-checked, and not covered by `tools/selftest.sh`. Last reviewed 2026-08-02 against Claude Code v2.1.220. Opinionated, and it may lag the harness.

A public repo that sits beside private ones needs a commit-time guard that blocks private names, paths and personal identifiers before they reach history. This part covers the two git hooks this repo ships, the rule their output must follow, the generic scanner that backs them, and the two ways secrets still reach git when the design-time rules are followed. For Claude Code hooks in general, see [Part 8](08-hooks.md).

## The Two Tracked Git Hooks

`hooks/pre-commit` and `hooks/commit-msg` block a commit whose staged content or message references a private sibling repo. `.git/hooks/` is never tracked by git, so a fresh clone has neither installed until you run:

```
sh hooks/install.sh
```

Neither hook hardcodes any repo name or path, which keeps it safe in a public repo. Each derives its blocklist at runtime by globbing the parent of this repo for `.private-root` marker files: a sibling repo opts in by dropping a `.private-root` file at its root, optionally with a repo-relative subfolder name (for example a feedback or notes folder) as its first non-comment line. The token list is the private repo's directory name plus that subfolder's first path component, generated fresh on every commit from whatever markers exist on the machine. The same convention applies at Claude Code write-time in a write guard that honours `.private-root`.

These are POSIX `sh`, so they run only for commits through Git Bash, never a GUI client's own commit flow; see "Critical for Windows" in [Part 8](08-hooks.md#critical-for-windows) and port them to `.ps1` or `.bat` if you commit through a Windows GUI client.

## A Privacy Guard Must Report WHERE, Never WHAT

A hook that finds a private token and echoes the matching line has printed it into the terminal, any CI log that captured the run, and the transcript of any assistant committing on your behalf, a wider audience than the commit it blocked. The wrong version looks more helpful, which is why it is easy to write. So the pre-commit hook prints file names and the commit-msg hook prints line numbers; neither prints the match. A location is enough to act on and costs nothing if it leaks.

The general form applies to any check over sensitive data: a rule that names the thing it protects instantiates the leak it exists to prevent. The public copy of a privacy rule says "no private repo names"; the private copy is where the names live. The same split applies to the guard's own output.

When one of a pair of hooks implements a safety rule, check the other for that rule specifically, by name, rather than reading it for general correctness. A rationale in a comment does not propagate to the sibling file, and a reviewer who just read the good version is least likely to notice the bad one.

## The Generic Layer: `hooks/privacy-scan.sh`

The marker mechanism protects only against names of sibling repos and does nothing on a machine with no marker. A second layer, `hooks/privacy-scan.sh`, runs first in both hooks and fails closed on shapes that identify a machine or person: absolute user paths, email addresses, IPv4 addresses and internal hostnames (placeholder forms such as a user called `name`, `noreply@` addresses and documentation IP ranges are allowed). It also reads `private-terms.txt` inside your own `.git/` directory, one case-insensitive term per line, for names, employer, products and internal systems; that file is never tracked, so the terms are never published. Like the marker layer it reports file and line, never the match.

`sh hooks/privacy-scan.sh tree` scans every non-ignored file, tracked or not, which covers the gap that a hook sees only staged content. `tools/selftest_privacy.sh` holds positive and negative controls and checks that installed hooks equal the tracked ones; `tools/selftest.sh` runs both. History, `--no-verify` and non-git writes are not covered, so the periodic whole-tree scan remains required.

## Secrets That Get Into Git Anyway

Keeping secrets out of git (see [Part 11](11-workspace-repo.md)) is the design-time rule. Two things go wrong even when you follow it.

**An exact-path gitignore rule protects the file, not the secret.** `config/config.json` in `.gitignore` stops that one file from being staged, but not a copy - and a copy is exactly what a credential rotation or migration produces, as a `.bak`, a suffixed backup, or an editor copy. The copy usually holds the fresher secret and sails past the rule. Write ignore rules for anything holding a live credential as a glob (`config.json*`, not `config.json`), and verify coverage with `git check-ignore -v <path>` rather than assuming.

**A history rewrite that verifies clean is not necessarily finished.** `git filter-repo` (or `filter-branch`) plus a force push removes the offending commits from the remote, but not the local objects - anything named by a reflog entry stays reachable, and the default expiry holds entries for months. Worse, a GUI git client syncing in the background can fetch in the gap between the rewrite and the push, pull the un-rewritten history back from the not-yet-updated remote, and silently restore the removed objects - `git fsck --unreachable` will not catch this, because it respects reflogs. Treat the rewrite as finished only after: push, then `git reflog expire --expire=now --expire-unreachable=now --all`, then `git gc --prune=now`. Check with `du -sh .git` or `git count-objects -vH` before and after. Avoid touching a background-syncing GUI client in the gap, or push promptly enough to close it.
