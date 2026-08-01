---
description: Checklist to safely make a GitHub repo public - scan for secrets, check gitignore, verify README
---

# /make-public

Run a safety checklist on the current repository to verify it's ready to be made public.

## The only hard blockers for going public are:
1. **Secrets/credentials** in tracked files or git history
2. **Hardcoded personal paths** with PII (e.g. absolute user paths, email addresses, full names in unexpected places)

Being messy, having personal style, or having rough edges is NOT a blocker.

## Checklist to Run

### 1. Secret Scan (CRITICAL)
Search tracked files for patterns that look like secrets:
- API keys: `sk-`, `Bearer `, `_SECRET`, `_TOKEN`, `_KEY`, `_PASSWORD`, `api_key`, `apikey`
- Personal: email addresses matching `@`, hardcoded user paths (e.g. `C:\Users\username\`), personal IP addresses
- Auth: `Authorization:`, `password =`, `token =`, `.env` files tracked in git

Run: `git grep -i "api_key\|secret\|password\|token\|bearer" -- "*.py" "*.js" "*.json" "*.env" "*.cfg" "*.ini" 2>/dev/null | head -20`

Also check: `git ls-files | grep -i "\.env\|secret\|credential\|auth\|token"`

### 2. Gitignore Check
- Does `.gitignore` exist?
- Does it cover: `*.env`, `*.log`, `data/`, `node_modules/`, `__pycache__/`, `*.pyc`, build outputs?
- Are any sensitive files currently tracked that should be ignored?

Run: `git ls-files | grep -E "\.env$|\.log$|token|secret|credential" | head -10`

### 3. README Check
- Does README.md exist?
- Does it explain what the project does? (Even a one-liner is fine)
- Does it have any setup/usage instructions?

### 4. Recent Commits Check
- Run `git log --oneline -10` - any commit messages that reveal sensitive info?
- Check if any large binary files are accidentally tracked

### 5. Verdict
Based on the above, give one of:
- **READY** - no blockers found. Safe to make public.
- **NEEDS FIXES** - list specific files/lines to fix before going public
- **MAJOR ISSUE** - secrets found in git history (requires git-filter-repo + force push + key rotation)

## Notes
- Messy code, hardcoded relative paths, and rough README are all fine for public
- If secrets were committed historically (not just current files), history must be purged with git-filter-repo
- After making public, consider adding a Ko-fi badge to the README
- Default new repos to private at creation (`--private`). Making a repo public is always a separate, deliberate later decision, never the default.

## This Checklist Is Pre-Publish Only - It Is Not a Standing Guarantee

Everything above runs once, at the moment a repo goes public. It says nothing about a repo that has already been public for months. A write-time rule only stops *future* violations - it has no opinion about anything that leaked before the rule existed, or before this checklist was ever run against that repo. Treat "we added the rule" and "we swept for what already violates it" as two separate, both-required steps. Rerun this checklist periodically against every already-public repo, not just at the moment of first publishing.

When building or running a periodic re-scan, two blind spots recur and both need explicit handling:

- **Scan commit messages, not just file content.** A content-only scan (grepping tracked file contents, or a content-search tool like `git log -S`/`-G`) cannot see a secret or a private detail that was only ever typed into a commit message. That needs a separate pass over `git log` message text, not an assumption that the content scan already covered it.
- **A scan that cannot reach a target must never report a clean pass.** If the scan silently skips a repo it has no local access to, or drops one that moved or was renamed mid-sweep, printing "PASS - no leaks found" is a false all-clear - it describes what the tool *could see*, not what actually exists. A detector should state exactly what it examined (repo count scanned vs. repo count that exists) and refuse to call an incomplete sweep a pass; return an explicit incomplete/failed status instead, listing what was skipped by name.
