#!/bin/sh
# Generic privacy scan for this repo. Safe to publish: it hardcodes no private term.
#
# Modes:
#   privacy-scan.sh staged        scan the staged diff and staged file names (used by pre-commit)
#   privacy-scan.sh author        check the author and committer identity of the commit being made
#   privacy-scan.sh msg FILE      scan a commit message file (used by commit-msg)
#   privacy-scan.sh tree          scan every non-ignored working-tree file and file name, tracked or not
#   privacy-scan.sh history [REV-LIST-ARGS]
#                                 pre-publish scan of EVERY commit message, commit identity, file
#                                 version, annotated tag and git note reachable from any ref,
#                                 including deleted files and old content. With arguments it scans
#                                 only that range (used by pre-push), for example: NEW --not OLD.
#                                 (reports path and commit or blob id, never the match)
#
# Two layers, both fail-closed (exit 1 on any hit):
#   1. Generic shapes that identify a machine, a person or a secret: absolute user paths (plain and
#      JSON-escaped), ~user paths, email addresses, IPv4 addresses, internal hostnames, credential
#      shapes, ticket ids, URL hosts and GitHub repo links that are not on a tracked allowlist.
#      Placeholder forms (a user called name, you, example...) and documentation ranges are allowed.
#   2. Your own terms: one per line in `<git-dir>/private-terms.txt` (names, employer,
#      product, internal system). That file lives inside .git, so it is never tracked
#      and never published. Matching is case-insensitive. A loud warning prints when it is missing.
#
# Tracked allowlists live next to this script (a missing one means nothing is allowed):
#   url-allowlist.txt     public URL hosts (exact, or *.suffix)
#   repo-allowlist.txt    public github owner/repo pairs
#   ticket-allowlist.txt  ticket id prefixes written PREFIX-* (never list a real id)
#   binary-allowlist.txt  repo paths of binary files allowed to be committed
#   author-allowlist.txt  one ERE per line; a commit identity email must match one in full
#
# Like the sibling hooks, it reports WHERE (file and line), never WHAT, so the output
# is safe to paste into a terminal, a CI log or an assistant transcript.

MODE="$1"
GIT_DIR_PATH=$(git rev-parse --git-dir 2>/dev/null)
TERMS_FILE="${PRIVACY_TERMS_FILE:-$GIT_DIR_PATH/private-terms.txt}"
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ALLOW_DIR="$SCRIPT_DIR"
if [ ! -f "$ALLOW_DIR/url-allowlist.txt" ]; then
    # An old-style install copied the hook into .git/hooks without the allowlists.
    top=$(git rev-parse --show-toplevel 2>/dev/null)
    [ -n "$top" ] && [ -f "$top/hooks/url-allowlist.txt" ] && ALLOW_DIR="$top/hooks"
fi

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

SHAPES='[A-Za-z]:\\+Users\\+[A-Za-z0-9._-]+|/(home|Users)/[A-Za-z0-9._-]+|(^|[^A-Za-z0-9_~])~[A-Za-z_][A-Za-z0-9._-]*/|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|\b([0-9]{1,3}\.){3}[0-9]{1,3}\b|\b[a-z0-9-]+\.(corp|internal|intranet|lan|local|home|localdomain)\b|(%5[Cc]|%2[Ff])+(Users|home)(%5[Cc]|%2[Ff])+[A-Za-z0-9._-]+|(^|[^\\A-Za-z0-9:])(\\\\[A-Za-z0-9][A-Za-z0-9._-]+\\[A-Za-z0-9$][A-Za-z0-9$._-]*|\\\\\\\\[A-Za-z0-9][A-Za-z0-9._-]+\\\\[A-Za-z0-9$][A-Za-z0-9$._-]*)|\b([0-9a-f]{1,4}:){7}[0-9a-f]{1,4}\b|\b([0-9a-f]{1,4}:){1,7}:([0-9a-f]{1,4}(:[0-9a-f]{1,4}){0,5})?|(^|[^:0-9a-z]):(:[0-9a-f]{1,4}){1,7}'
# Bare company hosts (no scheme) on common SaaS suffixes; checked against url-allowlist.txt.
BAREHOST='\b([a-z0-9-]+\.)+(atlassian\.net|slack\.com|sharepoint\.com|okta\.com|service-now\.com)\b'
ALLOW='[\\/](name|you|user|username|yourname|your-name|me|example)$|(%5[Cc]|%2[Ff])(name|you|user|username|yourname|your-name|me|example)$|\\(name|server|host|hostname|example)\\+[A-Za-z0-9$._-]+$|(:|[^0-9a-f])::1$|:2001:0*db8[:0-9a-f]*$|~(name|you|user|username|yourname|me|example)/$|:[A-Za-z0-9._%+-]+@users\.noreply\.github\.com$|:noreply@anthropic\.com$|@example\.|:(path|pathlib|os)\.home$|:(settings|config|env|application)\.local$|:(0\.0\.0\.0|127\.0\.0\.1|192\.0\.2\.[0-9]+|198\.51\.100\.[0-9]+|203\.0\.113\.[0-9]+)$'
# Case-sensitive credential shapes (AWS key id, Slack webhook and token, GitHub tokens, private key header).
CRED='AKIA[0-9A-Z]{16}|hooks\.slack\.com/services|xox[baprs]-[A-Za-z0-9-]{10,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----'
TICKET='\b[A-Z]{2,6}-[0-9]+\b'
URLRE='https?://[A-Za-z0-9._~%@:\\-]+'
REPORE='github\.com[:/][A-Za-z0-9._-]+/[A-Za-z0-9._-]+'
TAB=$(printf '\t')

# stdin "N:match" lines, prints N for those not covered by the allowlist file $2 (kind $1).
not_allowed() {
    awk -v kind="$1" -v af="$2" '
    BEGIN { while ((getline l < af) > 0) { sub(/#.*/, "", l); gsub(/[ \t\r]/, "", l); if (l != "") al[tolower(l)] = 1 } }
    {
        i = index($0, ":"); n = substr($0, 1, i - 1); m = tolower(substr($0, i + 1)); ok = 0
        if (kind == "ticket") { p = m; sub(/-.*/, "", p); ok = ((p "-*") in al) }
        else if (kind == "host") {
            sub(/^https?:\/\//, "", m); gsub(/\\/, "", m); sub(/^.*@/, "", m); sub(/:.*$/, "", m); sub(/\.+$/, "", m)
            if (m in al) ok = 1
            else { s = m; while ((j = index(s, ".")) > 0) { s = substr(s, j); if (("*" s) in al) { ok = 1; break } s = substr(s, 2) } }
        } else if (kind == "repo") { sub(/^github\.com[:\/]/, "", m); sub(/\.git$/, "", m); sub(/\.+$/, "", m); ok = (m in al) }
        if (!ok) print n
    }'
}

# $1 file -> line numbers hit by any generic shape, one per line
shape_lines() {
    # One cheap pass first: most text holds no candidate at all, and spawning the filters below is
    # what makes a whole-tree or whole-history scan slow. The gate is a superset of every shape.
    grep -aqEi "$SHAPES|$CRED|$TICKET|$URLRE|$REPORE|$BAREHOST" "$1" 2>/dev/null || return 0
    {
        grep -anoEi "$SHAPES" "$1" | grep -Eiv "$ALLOW" | cut -d: -f1
        grep -anoE "$CRED" "$1" | cut -d: -f1
        grep -anoEi "$TICKET" "$1" | not_allowed ticket "$ALLOW_DIR/ticket-allowlist.txt"
        grep -anoEi "$URLRE" "$1" | not_allowed host "$ALLOW_DIR/url-allowlist.txt"
        grep -anoEi "$BAREHOST" "$1" | not_allowed host "$ALLOW_DIR/url-allowlist.txt"
        grep -anoEi "$REPORE" "$1" | not_allowed repo "$ALLOW_DIR/repo-allowlist.txt"
    } 2>/dev/null
}

term_hits() {
    [ -s "$TERMS_FILE" ] || return 0
    grep -anFi -f "$TERMS_FILE" 2>/dev/null | cut -d: -f1
}

FOUND=0
# Fast clean check on a file: succeeds when it holds no shape candidate and no private term, so the
# common case costs two process spawns instead of dozens.
quick_clean() {
    grep -aqEi "$SHAPES|$CRED|$TICKET|$URLRE|$REPORE|$BAREHOST" "$1" 2>/dev/null && return 1
    [ -s "$TERMS_FILE" ] && grep -aqFi -f "$TERMS_FILE" "$1" 2>/dev/null && return 1
    return 0
}

scan_text() { # $1 label ; $2 file holding the text
    quick_clean "$2" && return 0
    lines=$( { shape_lines "$2"; term_hits < "$2"; } | sort -un | tr '\n' ' ')
    if [ -n "$lines" ]; then
        echo "  $1 (line(s): $lines)"
        FOUND=1
    fi
}

scan_name() { # $1 file name: generic shapes and private terms
    printf '%s\n' "$1" > "$WORK/name"
    quick_clean "$WORK/name" && return 0
    bad=$( { shape_lines "$WORK/name"; term_hits < "$WORK/name"; } | head -1)
    if [ -n "$bad" ]; then
        echo "  $1 (file name)"
        FOUND=1
    fi
}

# Is $1 (an email) matched IN FULL by a line of author-allowlist.txt? Empty or missing list: no.
email_ok() {
    if [ ! -f "$WORK/author-pats" ]; then
        grep -vE '^[[:space:]]*(#|$)' "$ALLOW_DIR/author-allowlist.txt" 2>/dev/null | tr -d '\r' > "$WORK/author-pats"
    fi
    [ -s "$WORK/author-pats" ] && printf '%s\n' "$1" | grep -Exqf "$WORK/author-pats"
}

# The identity git would record for the commit being made (author or committer).
check_identity() { # $1 AUTHOR|COMMITTER
    ident=$(git var "GIT_$1_IDENT" 2>/dev/null)
    email=$(printf '%s' "$ident" | sed -n 's/^.*<\(.*\)>.*$/\1/p')
    name=$(printf '%s' "$ident" | sed -n 's/ *<.*$//p')
    if ! email_ok "$email"; then
        echo "  $1 identity: email is not on hooks/author-allowlist.txt"
        FOUND=1
    fi
    printf '%s\n%s\n' "$name" "$email" > "$WORK/ident"
    scan_text "$1 identity" "$WORK/ident"
}

binary_allowed() { # $1 repo path
    tr -d '\r' < "$ALLOW_DIR/binary-allowlist.txt" 2>/dev/null | grep -qxF -- "$1"
}

blob_allowed() { # $1 full blob id; reviewed synthetic fixtures kept in old history
    grep -vE '^[[:space:]]*(#|$)' "$ALLOW_DIR/blob-allowlist.txt" 2>/dev/null | tr -d '\r' | cut -d' ' -f1 | grep -qxF -- "$1"
}

warn_terms() {
    if [ ! -s "$TERMS_FILE" ]; then
        {
            echo "WARNING ============================================================"
            echo "WARNING: no private-terms file at $TERMS_FILE (missing or empty)."
            echo "WARNING: names, employer, product and internal-system terms are NOT"
            echo "WARNING: being checked on this machine. Only generic shapes are."
            echo "WARNING: Create the file, one term per line, inside your .git folder."
            echo "WARNING ============================================================"
        } >&2
    fi
}

case "$MODE" in
staged|msg|tree|history) warn_terms ;;
esac

case "$MODE" in
staged)
    git diff --cached --name-only --diff-filter=ACMR -z > "$WORK/names"
    if ! tr -d '\n' < "$WORK/names" | cmp -s - "$WORK/names"; then
        echo "  a staged file name contains a newline and cannot be scanned safely"
        FOUND=1
    fi
    tr '\0' '\n' < "$WORK/names" > "$WORK/list"
    while IFS= read -r f; do
        [ -n "$f" ] || continue
        scan_name "$f"
        git diff --cached -U0 -- ":(literal)$f" > "$WORK/diff"
        if grep -q '^Binary files ' "$WORK/diff"; then
            if ! binary_allowed "$f"; then
                echo "  $f (binary file; its content cannot be scanned, so add it to hooks/binary-allowlist.txt only after checking it by hand)"
                FOUND=1
            fi
            continue
        fi
        # Pass a file, never pipe into scan_text: a piped function runs in a
        # subshell and its FOUND=1 would be lost (the self-test caught exactly this).
        sed -n '/^+++/d; s/^+//p' "$WORK/diff" > "$WORK/added"
        scan_text "$f" "$WORK/added"
    done < "$WORK/list"
    ;;
author)
    check_identity AUTHOR
    check_identity COMMITTER
    ;;
msg)
    scan_text "commit message" "$2"
    ;;
tree)
    top=$(git rev-parse --show-toplevel)
    git -C "$top" ls-files --cached --others --exclude-standard -z | tr '\0' '\n' > "$WORK/list"
    while IFS= read -r f; do
        [ -n "$f" ] || continue
        scan_name "$f"
        case "$f" in *.png|*.jpg|*.jpeg|*.gif|*.ico|*.pdf|*.zip) continue ;; esac
        [ -f "$top/$f" ] || continue
        scan_text "$f" "$top/$f"
    done < "$WORK/list"
    ;;
history)
    shift
    ALLREFS=0
    if [ "$#" -eq 0 ]; then set -- --all; ALLREFS=1; fi
    git rev-list "$@" > "$WORK/commits"
    # Lines 1 to 4 of each scanned commit text are author name, author email, committer name and
    # committer email; the commit message follows.
    while read -r c; do
        [ -n "$c" ] || continue
        git log -1 --format='%an%n%ae%n%cn%n%ce%n%B' "$c" > "$WORK/c"
        scan_text "commit ${c%"${c#????????}"}" "$WORK/c"
    done < "$WORK/commits"
    # Identity emails must be on the allowlist: check each distinct address once, then name the
    # commits only if one is bad.
    git log "$@" --format='%ae%n%ce' | sort -u > "$WORK/emails"
    badmail=0
    while IFS= read -r e; do
        email_ok "$e" || badmail=1
    done < "$WORK/emails"
    if [ "$badmail" -eq 1 ]; then
        git log "$@" --format="%h${TAB}%ae${TAB}%ce" > "$WORK/idlog"
        while IFS="$TAB" read -r h ae ce; do
            if ! email_ok "$ae" || ! email_ok "$ce"; then
                echo "  commit $h (author or committer email not on hooks/author-allowlist.txt)"
                FOUND=1
            fi
        done < "$WORK/idlog"
    fi
    if [ "$ALLREFS" -eq 1 ]; then
        # Annotated tags: the tag object holds a message and a tagger identity.
        git for-each-ref --format='%(objecttype) %(refname)' refs/tags > "$WORK/tags"
        while read -r type ref; do
            [ "$type" = "tag" ] || continue
            git cat-file tag "$ref" > "$WORK/tagobj"
            scan_text "tag ${ref#refs/tags/}" "$WORK/tagobj"
            temail=$(sed -n 's/^tagger .*<\(.*\)>.*$/\1/p' "$WORK/tagobj")
            if [ -n "$temail" ] && ! email_ok "$temail"; then
                echo "  tag ${ref#refs/tags/} (tagger email not on hooks/author-allowlist.txt)"
                FOUND=1
            fi
        done < "$WORK/tags"
        # Git notes: one blob per annotated object, under any notes ref.
        git for-each-ref --format='%(refname)' refs/notes > "$WORK/nrefs"
        while read -r nref; do
            git notes --ref "$nref" list > "$WORK/nlist" 2>/dev/null
            while read -r nblob nobj; do
                [ -n "$nblob" ] || continue
                git cat-file -p "$nblob" > "$WORK/note"
                scan_text "note on ${nobj%"${nobj#????????}"}" "$WORK/note"
            done < "$WORK/nlist"
        done < "$WORK/nrefs"
    fi
    # Every distinct file version ever stored: "<blob> <path>", listed once per blob.
    git rev-list --objects "$@" | git cat-file --batch-check='%(objecttype) %(objectname) %(rest)' \
        | grep '^blob ' | sort -u -k2,2 > "$WORK/blobs"
    while read -r _ sha path; do
        [ -n "$path" ] || continue
        blob_allowed "$sha" && continue
        short=${sha%"${sha#???????}"}
        printf '%s\n' "$path" > "$WORK/pname"
        if [ -n "$( { shape_lines "$WORK/pname"; term_hits < "$WORK/pname"; } | head -1)" ]; then
            echo "  $path (file name, blob $short)"
            FOUND=1
        fi
        case "$path" in *.png|*.jpg|*.jpeg|*.gif|*.ico|*.pdf|*.zip) continue ;; esac
        git cat-file -p "$sha" > "$WORK/blob" 2>/dev/null
        scan_text "$path @ $short" "$WORK/blob"
    done < "$WORK/blobs"
    ;;
*)
    echo "usage: privacy-scan.sh staged | author | msg FILE | tree | history [REV-LIST-ARGS]" >&2
    exit 2
    ;;
esac

if [ "$FOUND" -ne 0 ]; then
    echo ""
    echo "ERROR: privacy scan hit. Locations are listed above."
    echo "The match is withheld on purpose."
    echo ""
    echo "What it looks for:"
    echo "- a user path, email, IP or internal hostname"
    echo "- a credential shape or a ticket id"
    echo "- a URL host or repo link not on its allowlist"
    echo "- an unlisted binary"
    echo "- a commit identity not on the author allowlist"
    echo "- a term from your private-terms file"
    echo ""
    echo "Fix: use generic wording or a placeholder."
    echo "Public hosts, repos and ticket prefixes go in the"
    echo "tracked allowlists in hooks/. A reviewed synthetic"
    echo "test fixture in old history goes in"
    echo "hooks/blob-allowlist.txt (history scan only)."
    echo ""
    exit 1
fi
exit 0
