#!/bin/sh
# Points git at this repo's tracked hooks directory (core.hooksPath = hooks), so the hooks that
# run are always the tracked files and can never drift from a stale copy. .git/config is never
# tracked by git itself, so a fresh clone has no protection until this script runs once.
#
# Usage: sh hooks/install.sh   (run from anywhere inside the repo)
#
# Old installs copied the hooks into .git/hooks/. Those copies are ignored once core.hooksPath is
# set; they are left in place and are no longer checked for drift.

set -e

REPO_ROOT=$(git rev-parse --show-toplevel)

for hook in pre-commit commit-msg pre-push privacy-scan.sh; do
    chmod +x "$REPO_ROOT/hooks/$hook"
done
git -C "$REPO_ROOT" config core.hooksPath hooks
echo "core.hooksPath = hooks (pre-commit, commit-msg, pre-push now run from the tracked files)"

echo "Done. See docs/08-hooks.md for what these hooks check."
