#!/bin/sh
# Self-test for hooks/privacy-scan.sh. Each case has a positive control (must be
# blocked) and a negative control (must pass), so a scan that silently stopped
# checking fails here. Runs in a throwaway repo; touches nothing in this one.
set -u
HERE=$(cd "$(dirname "$0")/.." && pwd)
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
cd "$T" || exit 1
git init -q . && git config user.email t@example.com && git config user.name t
mkdir -p .git/hooks
cp "$HERE/hooks/privacy-scan.sh" "$HERE/hooks/pre-commit" "$HERE/hooks/commit-msg" .git/hooks/
chmod +x .git/hooks/*
FAIL=0

blocked() { # $1 label, $2 file content
    printf '%s\n' "$2" > f.txt && git add f.txt
    if sh .git/hooks/privacy-scan.sh staged >/dev/null 2>&1; then echo "FAIL: not blocked: $1"; FAIL=1; else echo "ok: blocked: $1"; fi
    git reset -q f.txt
}
allowed() {
    printf '%s\n' "$2" > f.txt && git add f.txt
    if sh .git/hooks/privacy-scan.sh staged >/dev/null 2>&1; then echo "ok: allowed: $1"; else echo "FAIL: wrongly blocked: $1"; FAIL=1; fi
    git reset -q f.txt
}

# Fixtures are split with an empty quote pair so this file never contains a literal
# match itself and the whole-tree scan can run over it.
IP=10.20.30.''40
blocked "windows user path" 'see C:\Users\''jsmith\notes'
blocked "unix home path" 'cd /home/''jsmith/work'
blocked "email" 'ask jane.doe@''acme.org'
blocked "ipv4" "host at $IP"
blocked "internal hostname" 'https://wiki.acme.''corp/page'
allowed "placeholder path" 'C:\Users\name\project and /home/you/x'
allowed "noreply and example email" 'noreply@anthropic.com and a@example.com'
allowed "loopback and doc range" "127.0.0.''1 and 203.0.113.''9"
allowed "settings.local filename" 'edit settings.local.json'

printf 'acmecorp\n' > .git/private-terms.txt
blocked "private term (case-insensitive)" 'we use AcmeCorp tooling'
allowed "unrelated text with terms file present" 'plain generic sentence'

# commit-msg path
printf 'fix for acmecorp build\n' > msg.txt
if sh .git/hooks/privacy-scan.sh msg msg.txt >/dev/null 2>&1; then echo "FAIL: commit message term not blocked"; FAIL=1; else echo "ok: blocked: commit message term"; fi
printf 'generic wording only\n' > msg.txt
if sh .git/hooks/privacy-scan.sh msg msg.txt >/dev/null 2>&1; then echo "ok: allowed: clean commit message"; else echo "FAIL: clean message blocked"; FAIL=1; fi

# the output must withhold the match
printf 'host at %s\n' "$IP" > f.txt && git add f.txt
OUT=$(sh .git/hooks/privacy-scan.sh staged 2>&1)
case "$OUT" in *"$IP"*) echo "FAIL: output echoed the match"; FAIL=1 ;; *) echo "ok: match withheld in output" ;; esac

# installed hooks must equal the tracked ones in the real repo (drift check)
if [ -d "$HERE/.git/hooks" ]; then
    for h in pre-commit commit-msg privacy-scan.sh; do
        if [ -f "$HERE/.git/hooks/$h" ] && ! cmp -s "$HERE/hooks/$h" "$HERE/.git/hooks/$h"; then
            echo "FAIL: installed $h differs from hooks/$h; run sh hooks/install.sh"; FAIL=1
        fi
    done
fi

[ "$FAIL" -eq 0 ] && echo "PRIVACY SELFTEST PASS" || echo "PRIVACY SELFTEST FAIL"
exit "$FAIL"
