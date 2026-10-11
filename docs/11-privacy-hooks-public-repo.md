# Part 11: Privacy Hooks for a Public Repo

> **Field note.** Written from practice rather than machine-checked, and not covered by `tools/selftest.sh`. Last reviewed 2026-08-02 against Claude Code v2.1.220. Opinionated, and it may lag the harness.

A public repo that sits beside private ones needs a commit-time guard that blocks private names, paths and personal identifiers before they reach history. This part covers the two git hooks this repo ships, the rule their output must follow, the generic scanner that backs them, and the two ways secrets still reach git when the design-time rules are followed. For Claude Code hooks in general, see [Part 8](08-hooks.md).

## The Tracked Git Hooks

`hooks/pre-commit` and `hooks/commit-msg` block a commit whose staged content or message references a private sibling repo, and `hooks/pre-push` scans the commits being pushed. Git config is never tracked, so a fresh clone runs none of them until you run the installer, which sets `core.hooksPath` to the tracked `hooks/` folder so the hooks that run can never drift from a stale copy:

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

The marker mechanism protects only against names of sibling repos and does nothing on a machine with no marker. A second layer, `hooks/privacy-scan.sh`, runs first in both hooks and fails closed on shapes that identify a machine, a person or a secret: absolute user paths (plain, JSON-escaped and `~user`), email addresses, IPv4 addresses, internal hostnames (`.corp`, `.internal`, `.local`, `.home` and similar), credential shapes (cloud access keys, chat webhooks, GitHub tokens, private key headers) and ticket-id shapes. Placeholder forms such as a user called `name`, documentation IP ranges and noreply addresses from `anthropic.com` or GitHub's `users.noreply.github.com` are allowed; a noreply address at any other domain is not. The same shapes run over staged file names, and file lists are NUL-delimited so a name with a space is scanned like any other.

Four tracked allowlists next to the scanner turn open-ended shapes into closed sets, and a miss is a hit. `url-allowlist.txt` lists public URL hosts, so a company domain or a single-label intranet host fails; `repo-allowlist.txt` lists public `owner/repo` pairs, so a link to a private repo fails; `ticket-allowlist.txt` lists synthetic or standards prefixes as `PREFIX-*` (never a real id); `binary-allowlist.txt` lists the only binaries allowed in, because a staged image, PDF or archive carries metadata the text scan cannot read. When a legitimate public host or repo trips the scan, add it to the list in a reviewed commit; when a host looks private, remove the link instead.

The scan also reads `private-terms.txt` inside your own `.git/` directory, one case-insensitive term per line, for names, employer, products and internal systems; that file is never tracked, so the terms are never published, and the scan prints a loud warning when it is missing or empty, because without it only shapes are checked. Like the marker layer it reports file and line, never the match.

Commit identity is a leak channel too. `pre-commit` refuses a commit whose author or committer email does not match a line of `author-allowlist.txt` (noreply patterns only), and the file has no override switch by design: policy changes by editing a tracked file in a reviewed commit.

`sh hooks/privacy-scan.sh tree` scans every non-ignored file and file name, tracked or not, which covers the gap that a hook sees only staged content. `tools/selftest_privacy.sh` holds numbered positive and negative controls for every check above; `tools/selftest.sh` runs both. `--no-verify` and non-git writes are not covered by the hooks, so the periodic whole-tree scan remains required, and history has its own scan (next section).

## Before Making a Repo Public: Scan History

A hook sees what is about to be committed. Publishing exposes every commit ever made, including files deleted long ago and messages written before the rules existed, so the pre-publish question is about history, not the tree. `sh hooks/privacy-scan.sh history` answers it with the same two layers (generic shapes plus your `private-terms.txt`) over every commit message, commit identity (author and committer name and email), annotated tag message, git note and distinct file version reachable from any ref, and also checks old file names. `hooks/pre-push` runs the same scan on only the commits being pushed, so it stays fast and is the last gate before anything leaves the machine. Output is a path with a short blob id, or `commit` with a short commit id, plus line numbers, never the match. `PRIVACY_TERMS_FILE` points it at a different term list, for scanning a repo other than the one the list lives in.

The routine is: put the terms in the untracked list, run the history scan, fix what it names, and run it again until it exits 0. A hit in an old file version means the tree is clean but the history is not; fixing it needs a history rewrite (see the section below), and every rewritten commit gets a new id, so do it before anyone clones. The scan reads every object, so it takes minutes on a long history; run it once at the decision point, not in a hook. It does not read binary files or anything outside git, so check those by eye. A clean run means the shapes and terms you listed are absent, not that nothing sensitive remains.

## What This Scan Cannot Catch

A pattern scan sees shapes and listed terms, never meaning. Prose about a named colleague or manager, a complaint about work, a personal story, the jargon of one company's domain, and a paraphrase or misspelling of a listed term all pass. A binary that is allowlisted is not read at all. Closing that gap needs a model-judged or human read of the diff as a stranger would read it, using a fresh reader that did not write the text; the scan only removes the mechanical cases first. The standing rules for what to write are in this repo's `CLAUDE.md`, under "Leak safety".

## Secrets That Get Into Git Anyway

Keeping secrets out of git (see [Part 12](12-workspace-repo.md)) is the design-time rule. Two things go wrong even when you follow it.

**An exact-path gitignore rule protects the file, not the secret.** `config/config.json` in `.gitignore` stops that one file from being staged, but not a copy - and a copy is exactly what a credential rotation or migration produces, as a `.bak`, a suffixed backup, or an editor copy. The copy usually holds the fresher secret and sails past the rule. Write ignore rules for anything holding a live credential as a glob (`config.json*`, not `config.json`), and verify coverage with `git check-ignore -v <path>` rather than assuming.

**A history rewrite that verifies clean is not necessarily finished.** `git filter-repo` (or `filter-branch`) plus a force push removes the offending commits from the remote, but not the local objects - anything named by a reflog entry stays reachable, and the default expiry holds entries for months. Worse, a GUI git client syncing in the background can fetch in the gap between the rewrite and the push, pull the un-rewritten history back from the not-yet-updated remote, and silently restore the removed objects - `git fsck --unreachable` will not catch this, because it respects reflogs. Treat the rewrite as finished only after: push, then `git reflog expire --expire=now --expire-unreachable=now --all`, then `git gc --prune=now`. Check with `du -sh .git` or `git count-objects -vH` before and after. Avoid touching a background-syncing GUI client in the gap, or push promptly enough to close it.

## Related

The `commit-msg` slot can also run the message-shape checks from [Part 25](25-config-driven-doc-linting.md). A public bug report or pull request description is the same exposure in a smaller space; `privacy-scan.sh msg FILE` works on a saved draft of one (see [Part 26](26-bug-reports-and-pr-descriptions.md)).
