#!/bin/sh
# Generic privacy scan for this repo. Safe to publish: it hardcodes no private term.
#
# Modes:
#   privacy-scan.sh staged        scan added lines of the staged diff (used by pre-commit)
#   privacy-scan.sh msg FILE      scan a commit message file (used by commit-msg)
#   privacy-scan.sh tree          scan every non-ignored working-tree file, tracked or not
#   privacy-scan.sh history       pre-publish scan of EVERY commit message and every file version
#                                 reachable from any ref, including deleted files and old content
#                                 (reports path and commit or blob id, never the match)
#
# Two layers, both fail-closed (exit 1 on any hit):
#   1. Generic shapes that identify a machine or person: absolute user paths, email
#      addresses, IPv4 addresses, internal hostnames. Placeholder forms (a user called
#      name, you, example...) and documentation ranges are allowed.
#   2. Your own terms: one per line in `<git-dir>/private-terms.txt` (names, employer,
#      product, internal system). That file lives inside .git, so it is never tracked
#      and never published. Matching is case-insensitive.
#
# Like the sibling hooks, it reports WHERE (file and line), never WHAT, so the output
# is safe to paste into a terminal, a CI log or an assistant transcript.

MODE="$1"
GIT_DIR_PATH=$(git rev-parse --git-dir 2>/dev/null)
TERMS_FILE="${PRIVACY_TERMS_FILE:-$GIT_DIR_PATH/private-terms.txt}"

SHAPES='[A-Za-z]:\\Users\\[A-Za-z0-9._-]+|/(home|Users)/[A-Za-z0-9._-]+|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|\b([0-9]{1,3}\.){3}[0-9]{1,3}\b|\b[a-z0-9-]+\.(corp|internal|intranet|lan)\b'
ALLOW='[\\/](name|you|user|username|yourname|your-name|me|example)$|noreply@|@example\.|:(0\.0\.0\.0|127\.0\.0\.1|192\.0\.2\.[0-9]+|198\.51\.100\.[0-9]+|203\.0\.113\.[0-9]+)$'

# stdin -> "line numbers that hit", one per line
hits() {
    {
        grep -noEi "$SHAPES" | grep -Eiv "$ALLOW" | cut -d: -f1
    } 2>/dev/null
}

term_hits() {
    [ -s "$TERMS_FILE" ] || return 0
    grep -nFi -f "$TERMS_FILE" 2>/dev/null | cut -d: -f1
}

FOUND=0
scan_text() { # $1 label ; stdin text
    tmp=$(mktemp)
    cat > "$tmp"
    lines=$( { hits < "$tmp"; term_hits < "$tmp"; } | sort -un | tr '\n' ' ')
    rm -f "$tmp"
    if [ -n "$lines" ]; then
        echo "  $1 (line(s): $lines)"
        FOUND=1
    fi
}

case "$MODE" in
staged)
    list=$(git diff --cached --name-only --diff-filter=ACMR)
    for f in $list; do
        # Redirect from a file, never pipe into scan_text: a piped function runs in a
        # subshell and its FOUND=1 would be lost (the self-test caught exactly this).
        added=$(mktemp)
        git diff --cached -U0 -- "$f" | grep '^+' | grep -v '^+++' | sed 's/^+//' > "$added"
        scan_text "$f" < "$added"
        rm -f "$added"
        if [ -s "$TERMS_FILE" ] && echo "$f" | grep -qFi -f "$TERMS_FILE"; then
            echo "  $f (file name)"
            FOUND=1
        fi
    done
    ;;
msg)
    scan_text "commit message" < "$2"
    ;;
tree)
    top=$(git rev-parse --show-toplevel)
    for f in $(git -C "$top" ls-files --cached --others --exclude-standard); do
        case "$f" in *.png|*.jpg|*.jpeg|*.gif|*.ico|*.pdf|*.zip) continue ;; esac
        [ -f "$top/$f" ] || continue
        scan_text "$f" < "$top/$f"
    done
    ;;
history)
    work=$(mktemp -d)
    git rev-list --all > "$work/commits"
    while read -r c; do
        [ -n "$c" ] || continue
        git log -1 --format=%B "$c" > "$work/msg"
        scan_text "commit ${c%"${c#????????}"}" < "$work/msg"
    done < "$work/commits"
    # Every distinct file version ever stored: "<blob> <path>", listed once per blob.
    git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectname) %(rest)' \
        | grep '^blob ' | sort -u -k2,2 > "$work/blobs"
    while read -r _ sha path; do
        [ -n "$path" ] || continue
        case "$path" in *.png|*.jpg|*.jpeg|*.gif|*.ico|*.pdf|*.zip) continue ;; esac
        git cat-file -p "$sha" > "$work/blob" 2>/dev/null
        scan_text "$path @ ${sha%"${sha#???????}"}" < "$work/blob"
        if [ -s "$TERMS_FILE" ] && echo "$path" | grep -qFi -f "$TERMS_FILE"; then
            echo "  $path (file name, blob ${sha%"${sha#???????}"})"
            FOUND=1
        fi
    done < "$work/blobs"
    rm -rf "$work"
    ;;
*)
    echo "usage: privacy-scan.sh staged | msg FILE | tree | history" >&2
    exit 2
    ;;
esac

if [ "$FOUND" -ne 0 ]; then
    echo ""
    echo "ERROR: generic privacy scan hit (a user path, email, IP, internal hostname, or a term from"
    echo "your private-terms file). Locations are listed above; the match is withheld on purpose."
    echo "Use generic language or a placeholder (a user called name, an example.com address)."
    echo ""
    exit 1
fi

if [ ! -s "$TERMS_FILE" ] && [ "$MODE" = "staged" ]; then
    echo "note: no private-terms file at $TERMS_FILE; names and employer terms are not checked on this machine." >&2
fi
exit 0
