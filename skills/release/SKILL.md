---
description: Create a tagged GitHub release - detect version, write changelog, create git tag, draft release notes
---

# /release - Create a Tagged GitHub Release

Guide for creating a proper tagged release for a repo. Detects version, writes changelog from commits, creates git tag, drafts GitHub Release notes.

## Steps

### 1. Find Current Version
Check for version in this order:
- `version.txt` or `VERSION` file in root
- `*.csproj` -> `<Version>` or `<AssemblyVersion>` tag
- `setup.py` / `pyproject.toml` -> `version =`
- `package.json` -> `"version":`
- Git tags -> `git tag --sort=-v:refname | head -5`
- If none found: ask the user for the version number

### 2. Propose Next Version
- Show current version (or "no version found")
- Propose next version using semantic versioning (SemVer):
  - Patch bump (v1.0.0 -> v1.0.1): bug fixes only
  - Minor bump (v1.0.0 -> v1.1.0): new features, backward compatible
  - Major bump (v1.0.0 -> v2.0.0): breaking changes
- Confirm with the user before continuing

### 3. Generate Changelog from Commits
```bash
# Get commits since last tag (or all if no tags)
git log $(git describe --tags --abbrev=0 2>/dev/null || git rev-list --max-parents=0 HEAD)..HEAD --oneline
```
- Group commits by type: Features, Fixes, Docs, Other
- Write a clean changelog section (not raw commit messages - summarise)

### 4. Check for Hardcoded Secrets (pre-release safety)
Quick scan before tagging:
```bash
git diff HEAD~20..HEAD -- . | grep -iE "(api_key|secret|password|token|credential)" | grep "^+" | grep -v "^+++"
```
- If anything suspicious found: STOP and warn before proceeding

### 5. Create the Tag
```bash
git tag -a v{VERSION} -m "Release v{VERSION}"
```
- Do NOT push the tag yet - user pushes via GitHub Desktop or CLI

### 6. Draft GitHub Release Notes
Write a release draft in this format:

```markdown
## v{VERSION} - {Date}

### What's New
- [feature 1]
- [feature 2]

### Bug Fixes
- [fix 1]

### Notes
- Requires: [dependencies/requirements]
- Download: See Assets below
```

- Paste the draft for the user to copy into GitHub's Release UI
- Remind them to: push the tag, then go to GitHub -> Releases -> Draft new release -> select the tag

### 7. Update Version File
If a version file was found in step 1, update it to the new version number.

## Rules

- **Never push** - user pushes tags and releases
- **Never release if secrets found** - always check first
- **Draft only** - provide the release notes as text to paste, don't attempt to use GitHub API
- **Version file update is optional** - only if a version file exists; don't create one from scratch
- **Always tag on the current HEAD** - confirm `git status` is clean before tagging

## Quick Usage

```
/release                    -> release current repo
/release v2.1.0            -> skip version detection, use this version
```
