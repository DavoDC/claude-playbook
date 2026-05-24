---
description: Create, list, or verify named checkpoints during long sessions or loops
effort: low
argument-hint: "[create <name> | list | verify <name>]"
when_to_use: "Use during overnight loops after each major task, before risky refactors, or in any session touching 5+ files. Subcommands: create (commits + logs), list (today's checkpoints), verify (diff since checkpoint). Defaults to create with timestamp name. Use before risky operations so you have a restore point."
---

# /checkpoint - Named Session Checkpoints

Lightweight restore points during overnight/loop runs. Three subcommands: `create`, `list`, `verify`.

## Usage

`/checkpoint create <name>` - commit current state as a named checkpoint
`/checkpoint list` - show all checkpoints for today
`/checkpoint verify <name>` - compare current tree to a named checkpoint

If no subcommand given, defaults to `create` with a timestamp name.

## Steps

### create [name]

1. If name not given, use `HHMM` (current time).
2. Commit any dirty tracked files with: `git commit -m "checkpoint: <name>" -- <all dirty paths>`. If nothing dirty, note "clean tree - checkpoint logged only."
3. Append one row to `memory/logs/session-checkpoints.log` (or create this file if it doesn't exist):
   ```
   [YYYY-MM-DD HH:MM] name=<name> sha=<short-sha> note=<one-line-what-was-just-done>
   ```
4. Report: `Checkpoint '<name>' at <sha>.`

### list

Read `memory/logs/session-checkpoints.log`, filter for today's date, print as table. If no entries today, say so.

### verify <name>

1. Find the sha for `<name>` in the checkpoint log.
2. Run `git diff <sha>..HEAD --stat` to show what changed since that checkpoint.
3. Report files changed, insertions, deletions. Flag if working tree is also dirty (uncommitted changes on top).

## Rules

- Never force-push or amend checkpoint commits - they are restore anchors.
- Use during: overnight loops after each major task, any session that touches 5+ files, before a risky refactor.
- Keep checkpoint names short and descriptive: `pre-guard-refactor`, `after-ecc-scan`, `end-of-loop-1`.
