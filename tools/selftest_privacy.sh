#!/bin/sh
# Self-test for hooks/privacy-scan.sh. Each case has a positive control (must be
# blocked) and a negative control (must pass), so a scan that silently stopped
# checking fails here. Runs in throwaway repos; touches nothing in this one.
#
# Numbered controls (each has at least a positive or a positive and a negative case):
#   C1  P0  a file name with a space is scanned as one file
#   C2  P0  a staged binary is blocked unless its path is in hooks/binary-allowlist.txt
#   C3  P1  JSON-escaped and ~user paths, credential shapes, .local/.home/.localdomain hosts,
#           ticket ids (with hooks/ticket-allowlist.txt), noreply tightening, shapes in file names
#   C4  P1  URL hosts and GitHub repo links must be on the tracked allowlists
#   C5  P1  author and committer identity at commit time; in history mode also commit identity,
#           annotated tag messages and tagger identity, and git notes
#   C6  P2  install.sh sets core.hooksPath, loud warning without a terms file, pre-push scans
#           only the pushed range
set -u
HERE=$(cd "$(dirname "$0")/.." && pwd)
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
cd "$T" || exit 1
git init -q . && git config user.email t@example.com && git config user.name t && git config core.autocrlf false
mkdir -p .git/hooks
cp "$HERE/hooks/privacy-scan.sh" "$HERE/hooks/pre-commit" "$HERE/hooks/commit-msg" "$HERE/hooks/pre-push" .git/hooks/ 2>/dev/null
cp "$HERE"/hooks/*.txt .git/hooks/ 2>/dev/null
chmod +x .git/hooks/pre-commit .git/hooks/commit-msg .git/hooks/pre-push 2>/dev/null
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

blocked_file() { # $1 label, $2 file name, $3 content (printf format, so \000 makes a binary)
    printf "$3" > "$2" && git add -- "$2"
    if sh .git/hooks/privacy-scan.sh staged >/dev/null 2>&1; then echo "FAIL: not blocked: $1"; FAIL=1; else echo "ok: blocked: $1"; fi
    git reset -q -- "$2"; rm -f -- "$2"
}
allowed_file() {
    printf "$3" > "$2" && git add -- "$2"
    if sh .git/hooks/privacy-scan.sh staged >/dev/null 2>&1; then echo "ok: allowed: $1"; else echo "FAIL: wrongly blocked: $1"; FAIL=1; fi
    git reset -q -- "$2"; rm -f -- "$2"
}

# Fixtures are split with an empty quote pair so this file never contains a literal
# match itself and the whole-tree scan can run over it.
IP=10.20.30.''40
blocked "windows user path" 'see C:\Users\''jsmith\notes'
blocked "unix home path" 'cd /home/''jsmith/work'
blocked "email" 'ask jane.doe@''acme.org'
blocked "ipv4" "host at $IP"
SCHEME=https:   # a variable, so this file never contains a literal URL
blocked "internal hostname" "${SCHEME}//wiki.acme."'corp/page'
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
git reset -q f.txt; rm -f f.txt

# C1 (P0): a file name with a space must still be scanned (the list used to split on spaces).
blocked_file "C1 shape inside a file whose name has a space" 'my notes.txt' 'C:\\Users\\''jsmith\\x\n'
allowed_file "C1 clean file whose name has a space" 'my notes.txt' 'nothing private\n'

# C2 (P0): a staged binary is blocked unless its path is in hooks/binary-allowlist.txt.
blocked_file "C2 binary with a path inside, not allowlisted" 'secret.gif' 'GIF89a\000\001 C:\\Users\\''jsmith\\x \000'
blocked_file "C2 clean binary, not allowlisted" 'plain.gif' 'GIF89a\000\001\000'
printf 'plain.gif\n' >> .git/hooks/binary-allowlist.txt
allowed_file "C2 clean binary, allowlisted" 'plain.gif' 'GIF89a\000\001\000'
cp "$HERE/hooks/binary-allowlist.txt" .git/hooks/binary-allowlist.txt 2>/dev/null

# C3 (P1): more shapes, each with a positive and a negative control.
blocked "C3 json-escaped windows path" 'C:\\Users\\''jsmith\\x'
allowed "C3 json-escaped placeholder path" 'C:\\Users\\name\\x'
blocked "C3 tilde user path" 'see ~''jsmith/notes'
allowed "C3 tilde home and placeholder" 'cd ~/work and ~name/x'
blocked "C3 aws access key" 'key AKIA''ABCDEFGHIJKLMNOP'
allowed "C3 short aws-like prefix" 'key AKIAshort'
blocked "C3 slack webhook" 'hooks.slack.com/''services/T000/B000/abcd'
allowed "C3 slack host without a webhook path" 'see the hooks.slack.com docs'
blocked "C3 github token" 'ghp_''abcdefghijklmnopqrstuvwxyz0123456789'
blocked "C3 github fine-grained token" 'github_pat_''abcdefghijklmnopqrstuvwxyz0123'
allowed "C3 token prefix named in prose" 'tokens start with ghp_ or github_pat_'
blocked "C3 private key header" '-----BEGIN RSA PRIVATE ''KEY-----'
allowed "C3 key header named in prose" 'a BEGIN PRIVATE KEY header'
blocked "C3 .local hostname" 'ssh build01.globex.''local'
blocked "C3 .home hostname" 'ssh nas.''home'
blocked "C3 .localdomain hostname" 'ssh box.''localdomain'
allowed "C3 code that only looks like a host" 'Path.home() and settings.local.json'
blocked "C3 ticket id shape" 'fixed in GLX-''4821'
allowed "C3 allowlisted ticket prefix and standard name" 'see MS-''3 and UTF-8'
blocked "C3 noreply at a company domain" 'noreply@globex''soft.com'
allowed "C3 github noreply address" 'by 12345+name@users.noreply.github.com'
blocked_file "C3 email-shaped file name" 'jsmith@globex.''com.txt' 'clean\n'
blocked_file "C3 term in a file name with a space" 'acmecorp notes.txt' 'clean\n'

# C4 (P1): URL hosts and GitHub repo links must be on the tracked allowlists.
blocked "C4 URL host not on the allowlist" "see ${SCHEME}//jira.globex"'soft.com/browse'
blocked "C4 single-label host with a port" "see ${SCHEME}//buildbox:8080/x"
blocked "C4 GitHub repo not on the allowlist" "see ${SCHEME}//github.com/"'someuser/secret-repo'
allowed "C4 allowlisted hosts and repo" "see ${SCHEME}//github.com/DavoDC/claude-playbook and ${SCHEME}//code.claude.com/docs/en/hooks and ${SCHEME}//example.com/x"
allowed "C4 localhost URL" "run ${SCHEME}//localhost:8080/health"

# C5 (P1): author and committer identity. Needs the allowlist copy and a real commit.
printf 'clean\n' > a.txt && git add a.txt
if git -c user.email=jane@example.invalid commit -qm "clean change" >/dev/null 2>&1; then echo "FAIL: C5 bad author email not blocked"; FAIL=1; else echo "ok: blocked: C5 bad author email at commit time"; fi
if GIT_COMMITTER_EMAIL=jane@example.invalid git -c user.email=1+t@users.noreply.github.com commit -qm "clean change" >/dev/null 2>&1; then echo "FAIL: C5 bad committer email not blocked"; FAIL=1; else echo "ok: blocked: C5 bad committer email at commit time"; fi
if git -c user.email=1+t@users.noreply.github.com commit -qm "clean change" >/dev/null 2>&1; then echo "ok: allowed: C5 noreply identity commits"; else echo "FAIL: C5 noreply identity wrongly blocked"; FAIL=1; fi

# C6 (P2): install.sh sets core.hooksPath; the missing-terms warning is loud; pre-push scans the pushed range.
I=$(mktemp -d)
( cd "$I" && git init -q . && mkdir hooks && cp "$HERE"/hooks/* hooks/ 2>/dev/null; sh hooks/install.sh >/dev/null 2>&1 )
if [ "$(git -C "$I" config core.hooksPath)" = "hooks" ]; then echo "ok: C6 install.sh sets core.hooksPath"; else echo "FAIL: C6 install.sh did not set core.hooksPath"; FAIL=1; fi
printf 'x\n' > w.txt && git add w.txt
if PRIVACY_TERMS_FILE=/nonexistent/terms sh .git/hooks/privacy-scan.sh staged 2>&1 | grep -q 'WARNING'; then echo "ok: C6 loud warning when the terms file is missing"; else echo "FAIL: C6 no loud warning for a missing terms file"; FAIL=1; fi
if sh .git/hooks/privacy-scan.sh staged 2>&1 | grep -q 'WARNING'; then echo "FAIL: C6 warning shown although the terms file exists"; FAIL=1; else echo "ok: C6 no warning when the terms file exists"; fi
git reset -q w.txt; rm -f w.txt
P=$(mktemp -d); ZERO=0000000000000000000000000000000000000000
( cd "$P" && git init -q . && git config user.email '1+t@users.noreply.github.com' && git config user.name t
  printf 'host at %s\n' "$IP" > old.txt && git add old.txt && git commit -qm "leak"
  git rm -q old.txt && git commit -qm "drop leak" && printf 'clean\n' > n.txt && git add n.txt && git commit -qm "more" )
C2H=$(git -C "$P" rev-parse HEAD~1); C3H=$(git -C "$P" rev-parse HEAD)
if (cd "$P" && echo "refs/heads/main $C3H refs/heads/main $ZERO" | sh "$HERE/hooks/pre-push" origin url >/dev/null 2>&1); then echo "FAIL: C6 pre-push let a leaky first push through"; FAIL=1; else echo "ok: blocked: C6 pre-push on a full outgoing history"; fi
if (cd "$P" && echo "refs/heads/main $C3H refs/heads/main $C2H" | sh "$HERE/hooks/pre-push" origin url >/dev/null 2>&1); then echo "ok: allowed: C6 pre-push scans only the pushed range"; else echo "FAIL: C6 pre-push scanned history behind the remote"; FAIL=1; fi
rm -rf "$I" "$P"

# history mode: a leak that was committed and later deleted must still be found, in a file
# version and in a commit message; a clean history must pass; the output must withhold the match.
H=$(mktemp -d)
( cd "$H" && git init -q . && git config user.email 1+t@users.noreply.github.com && git config user.name t
  printf 'host at %s\n' "$IP" > old.txt && git add old.txt && git commit -qm "add notes"
  git rm -q old.txt && printf 'clean\n' > new.txt && git add new.txt && git commit -qm "drop notes" )
HOUT=$(cd "$H" && sh "$HERE/hooks/privacy-scan.sh" history 2>&1); HRC=$?
if [ "$HRC" -ne 0 ] && echo "$HOUT" | grep -q 'old.txt'; then echo "ok: blocked: leak deleted from the tree but present in history"; else echo "FAIL: history scan missed a deleted leak"; FAIL=1; fi
case "$HOUT" in *"$IP"*) echo "FAIL: history output echoed the match"; FAIL=1 ;; *) echo "ok: match withheld in history output" ;; esac
( cd "$H" && printf 'about acmecorp\n' > m.txt && git add m.txt && git commit -qm "mention acmecorp build" )
printf 'acmecorp\n' > "$H/terms.txt"
if (cd "$H" && PRIVACY_TERMS_FILE="$H/terms.txt" sh "$HERE/hooks/privacy-scan.sh" history 2>&1 | grep -q 'commit '); then echo "ok: blocked: private term in a commit message in history"; else echo "FAIL: history scan missed a term in a commit message"; FAIL=1; fi
C=$(mktemp -d)
( cd "$C" && git init -q . && git config user.email 1+t@users.noreply.github.com && git config user.name t
  printf 'plain text\n' > a.txt && git add a.txt && git commit -qm "initial" )
if (cd "$C" && sh "$HERE/hooks/privacy-scan.sh" history >/dev/null 2>&1); then echo "ok: allowed: clean history"; else echo "FAIL: clean history wrongly blocked"; FAIL=1; fi
rm -rf "$H" "$C"

# C5 (history): commit identity, annotated tag messages and git notes are scanned. One tiny repo.
G=$(mktemp -d)
printf 'acmecorp\n' > "$G/terms.txt"
gscan() { (cd "$G" && PRIVACY_TERMS_FILE="$G/terms.txt" sh "$HERE/hooks/privacy-scan.sh" history 2>&1); }
( cd "$G" && git init -q . && git config user.email 1+t@users.noreply.github.com && git config user.name t
  printf 'plain\n' > a.txt && git add a.txt && git commit -qm "initial"
  git tag -a v0 -m "clean release" && git notes add -m "clean note" )
if gscan >/dev/null; then echo "ok: allowed: C5 history with a clean tag and a clean note"; else echo "FAIL: C5 clean tag and note wrongly blocked"; FAIL=1; fi
( cd "$G" && git tag -a v1 -m "acmecorp release" )
if gscan | grep -q 'tag v1'; then echo "ok: blocked: C5 term in an annotated tag message"; else echo "FAIL: C5 history missed a term in a tag message"; FAIL=1; fi
( cd "$G" && git tag -d v1 >/dev/null && git -c user.email=jane@example.invalid tag -a v2 -m "clean release" )
if gscan | grep -q 'tag v2'; then echo "ok: blocked: C5 bad tagger identity in history"; else echo "FAIL: C5 history missed a bad tagger identity"; FAIL=1; fi
( cd "$G" && git tag -d v2 >/dev/null && git notes add -f -m "about acmecorp" )
if gscan | grep -q 'note'; then echo "ok: blocked: C5 term in a git note"; else echo "FAIL: C5 history missed a term in a git note"; FAIL=1; fi
( cd "$G" && git notes remove HEAD >/dev/null && git -c user.email=jane@example.invalid commit -q --allow-empty -m "second" )
if gscan | grep -q 'commit '; then echo "ok: blocked: C5 bad author and committer email in history"; else echo "FAIL: C5 history missed a bad commit identity"; FAIL=1; fi
rm -rf "$G"

# installed hooks must equal the tracked ones in the real repo (drift check). With core.hooksPath
# pointing at hooks/ the copies in .git/hooks are inert, so only compare them for old installs.
if [ -d "$HERE/.git/hooks" ] && [ "$(git -C "$HERE" config core.hooksPath)" != "hooks" ]; then
    for h in pre-commit commit-msg pre-push privacy-scan.sh; do
        if [ -f "$HERE/.git/hooks/$h" ] && ! cmp -s "$HERE/hooks/$h" "$HERE/.git/hooks/$h"; then
            echo "FAIL: installed $h differs from hooks/$h; run sh hooks/install.sh"; FAIL=1
        fi
    done
fi

[ "$FAIL" -eq 0 ] && echo "PRIVACY SELFTEST PASS" || echo "PRIVACY SELFTEST FAIL"
exit "$FAIL"
