#!/bin/sh
# Installs this repo's tracked git hooks into .git/hooks/, where git actually
# reads them from. .git/hooks/ is never tracked by git itself (it's inside
# .git), so a fresh clone has none of these until this script runs once.
#
# Usage: sh hooks/install.sh   (run from anywhere inside the repo)

set -e

REPO_ROOT=$(git rev-parse --show-toplevel)
SRC_DIR="$REPO_ROOT/hooks"
DEST_DIR="$REPO_ROOT/.git/hooks"

mkdir -p "$DEST_DIR"

for hook in pre-commit commit-msg; do
    cp "$SRC_DIR/$hook" "$DEST_DIR/$hook"
    chmod +x "$DEST_DIR/$hook"
    echo "installed: $hook"
done

echo "Done. See docs/09-hooks.md for what these hooks check."
