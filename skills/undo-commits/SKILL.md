---
description: Undo the last N commits via git reset --soft, show staged diff, recommit cleanly. Safe - never rebases, never force-pushes.
effort: low
argument-hint: "[N] [repo-path]"
when_to_use: "Use when you need to undo commits, squash commits, or clean up commits. Runs git reset --soft HEAD~N, shows what's staged, then helps recommit with a clean message. NEVER rebase -i, NEVER force-push to shared repos."
---

# /undo-commits $ARGUMENTS

Undo the last N commits via `git reset --soft HEAD~N`. All changes stay staged, ready to recommit with a cleaner message.

**Synergy:** pairs with `/commit-chunks` (if the undone content needs splitting) and `/commit-all` (if re-committing as one chunk). If the goal is to split a commit, run `/commit-chunks` after this skill.

## Parsing args

- `$ARGUMENTS` may be: empty, a number N, a repo path, or "N path" in any order.
- Default N: **1** (undo just the last commit).
- Default repo: **current working directory**.
- If a path is given, use `git -C <path>` form - never `cd`.

## Steps

1. **Identify repo and N.** Parse `$ARGUMENTS`. If ambiguous (e.g. just a number), confirm: "Undo the last N commit(s) in `<repo>`?"

2. **Confirm current branch.** Run:
   ```bash
   git -C <repo> branch --show-current
   git -C <repo> log --oneline -$((N+2))
   ```
   Show the last N+2 commits so the user can see exactly what's being undone. Say: "About to undo these N commits - all changes will stay staged."

3. **Safety checks - STOP if any of these are true:**
   - The target commits are already pushed to a shared branch (`main`, `dev`, any remote-tracked branch with other contributors). Check: `git -C <repo> log --oneline origin/<branch>..HEAD` - if the commits to undo are NOT in this list, they're already on the remote. Warn: "These commits are already pushed. Undoing them locally will diverge your branch. Recommend creating a revert commit instead."
   - N > 20 - ask the user to confirm explicitly ("Undoing 20+ commits - confirm?").

4. **Run the reset:**
   ```bash
   git -C <repo> reset --soft HEAD~N
   ```

5. **Show staged result:**
   ```bash
   git -C <repo> diff --cached --stat
   git -C <repo> status --short
   ```
   Say: "Reset done. Here's what's staged:"

6. **Ask for the new commit message.** Say: "What message for the clean commit? (or say 'split' to use /commit-chunks instead)"

7. **Commit with the message given:**
   ```bash
   git -C <repo> commit -m "$(cat <<'EOF'
   <message from user>

   Co-Authored-By: Claude <model> <noreply@anthropic.com>
   EOF
   )"
   ```

8. If the user says "split" at step 6, invoke `/commit-chunks` instead of committing. The staged content from the reset is the input.

## Hard constraints

- **NEVER `git rebase -i`** - interactive rebase is not supported in non-interactive environments.
- **NEVER `git push --force`** without an explicit request.
- **NEVER undo commits that are already on a shared remote branch** without an explicit warning and user's go-ahead.
