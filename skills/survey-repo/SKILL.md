---
description: Quick codebase summary - language, purpose, key files, tests, entry points, open TODOs
effort: low
argument-hint: "[optional: path to repo]"
allowed-tools: Read Grep Glob Bash(git *) Bash(ls *) Bash(find *) Bash(wc *) Bash(python3 *)
when_to_use: "Use when starting work in an unfamiliar repo, onboarding to a new codebase, or needing a quick orientation. Produces a one-page structured summary with overview, structure, entry points, tests, key files, open TODOs, recent activity, and quick health assessment."
---

# /survey-repo

Survey the repository in the current working directory (or a specified path) and produce a structured summary.

## What to produce

Output a markdown summary with these sections:

### 1. Overview
- Repository name and purpose (1-2 sentences)
- Primary language(s)
- Public or private (check for GitHub remote URL)

### 2. Structure
- List top-level directories and their purpose
- Identify: source dir, tests dir, config dir, scripts dir, docs dir

### 3. Entry Points
- How to run the app (check README, package.json scripts, setup.py, .bat files, Makefile)
- Main file or executable

### 4. Tests
- Test framework used (pytest, NUnit, xUnit, etc.)
- Number of test files and approximate test count
- How to run tests (command)

### 5. Key Files
- README, CLAUDE.md, HISTORY.md (CHANGELOG.md deliberately absent - anti-pattern), .gitignore - note any that are missing
- Config files: what settings are configurable

### 6. Open TODOs
- Check for TTD.md, TTD.txt, TODO.md, IDEAS.md - list any that exist with a one-line summary
- Check for TODO/FIXME comments in source code (top 5 if many)

### 7. Recent Activity
- Last 5 commits (git log --oneline -5)
- What has recently changed

### 8. Quick Assessment
- Health score: tests present? README present? .gitignore adequate?
- Anything obviously broken or missing?
- Any secrets/credentials at risk?

## Instructions

1. Run `git log --oneline -5` for recent commits
2. Run `ls` to see top-level structure
3. Read README.md (first 30 lines if long)
4. Check for CLAUDE.md and read it if present
5. Count test files with a glob
6. Check for TTD/TODO files
7. Synthesise into the structured summary above

Keep the summary concise - max 1 page. This is a quick orientation, not exhaustive documentation.
