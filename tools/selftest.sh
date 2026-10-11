#!/bin/bash
# selftest.sh - self-test for the budget-tracking tools in this repo.
#
# Assertions, no network, no installs beyond python3 and bash:
#   1. statusline.py accepts synthetic status JSON on stdin, exits 0, and
#      writes a cache file containing the expected keys.
#   2. check-budget.sh reads that same cache and its output contains the
#      exact, distinctive percentage literals fed into statusline.py above -
#      a real round-trip across the statusline.py -> cache file ->
#      check-budget.sh boundary, not just "a percentage appeared somewhere".
#   3. with the cache file removed, check-budget.sh prints its no-data
#      message and exits 0 (the graceful-failure path the README promises).
#   4. every Claude Code settings.json snippet documented anywhere in this
#      repo uses only real settings.json keys (tools/selftest_settings.py
#      holds the one canonical key list; see that file for the reference).
#   5. every documented statusLine settings.json snippet (README.md,
#      docs/*.md) reduces to the same canonical form as every other one,
#      once the machine-specific command path is normalized away.
#   6. every fenced python/bash block in the hooks docs that is a whole,
#      standalone script (not a fragment) is syntactically valid.
#   7. every file in docs/ carries exactly one tier marker line (Core or
#      Field note) among its opening lines.
#   8. no long sentence appears in two places across this repo's .md files,
#      outside a short, scoped allow list (tools/selftest_dedup.py holds
#      the exceptions and the reason for each).
#   9. the token-baseline and session-brief tools pass their built-in
#      selftests, each including a positive control that must be flagged.
#  10. the generic privacy scan passes its own numbered positive and negative
#      controls (tools/selftest_privacy.sh: C1 file names with spaces, C2 staged
#      binaries, C3 shapes, C4 URL host and repo allowlists, C5 commit identity
#      plus tag and note scanning in history mode, C6 core.hooksPath install,
#      missing-terms warning and pre-push range), the installed hooks match the
#      tracked ones when hooksPath is not set, and the whole working tree is
#      clean under it.
#  11. the backlog tool's tests (tools/backlog_tests/run.py) all pass.
#  12. the shorthand-term hook and its glossary template pass their tests
#      (hooks/examples/test_shorthand_detector.py).
#  13. the doc linter passes its tests and the repo is clean under its
#      shipped ruleset (tools/doc_lint/).
#  14. the capacity checker passes its selftest and its example config parses.
#  15. the scratch-marker checker passes its selftest.
#  16. the prose and commit-message linter passes its selftest.
#  17. the hook-health checker and the example hook suite pass.
#
# Output discipline: silent pass, verbose fail. Each passing assertion
# prints one PASS line and nothing else. A failing assertion prints
# everything needed to debug it. The overall verdict is the LAST line.
#
# Usage: bash tools/selftest.sh

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# The repo's accepted interpreter pattern (see check-budget.sh): never a bare python3, which on some
# platforms is a Store alias that hangs.
PY=$(command -v python || command -v python3)

FAILED=0

# Isolate the cache file: statusline.py and check-budget.sh both locate
# their shared cache via Python's tempfile.gettempdir(), which checks the
# TMPDIR / TEMP / TMP environment variables (in that order) on every
# platform before falling back to a system default. Pointing TMPDIR at a
# scratch directory for the duration of this script means neither script
# ever touches a real user's cache file.
TEST_TMPDIR="$(mktemp -d)"
ORIG_TMPDIR="${TMPDIR:-}"
HAD_TMPDIR=0
if [ -n "${TMPDIR+x}" ]; then HAD_TMPDIR=1; fi
export TMPDIR="$TEST_TMPDIR"

cleanup() {
    if [ "$HAD_TMPDIR" = "1" ]; then
        export TMPDIR="$ORIG_TMPDIR"
    else
        unset TMPDIR
    fi
    rm -rf "$TEST_TMPDIR"
}
trap cleanup EXIT

CACHE_FILE="$TEST_TMPDIR/claude-statusline-data.json"

# Distinctive synthetic percentages, deliberately all different from each
# other and from any real-world round number, so a substring match below
# can't accidentally pass by coincidence.
SYNTH_FIVE_HOUR=37
SYNTH_SEVEN_DAY=61
SYNTH_CTX=84

# ---------------------------------------------------------------------------
# Assertion 1: statusline.py accepts synthetic input, exits 0, writes cache
# ---------------------------------------------------------------------------
SYNTHETIC_JSON='{
  "model": {"display_name": "Claude Sonnet 5", "id": "claude-sonnet-5"},
  "context_window": {"used_percentage": '"$SYNTH_CTX"', "context_window_size": 200000},
  "rate_limits": {
    "five_hour": {"used_percentage": '"$SYNTH_FIVE_HOUR"', "resets_at": 9999999999},
    "seven_day": {"used_percentage": '"$SYNTH_SEVEN_DAY"', "resets_at": 9999999999}
  },
  "version": "0.0.0-selftest",
  "cwd": "/tmp/selftest",
  "effort": {"level": "high"},
  "thinking": {"enabled": false},
  "session_name": "selftest"
}'

STATUSLINE_OUTPUT=$(printf '%s' "$SYNTHETIC_JSON" | "$PY" "$SCRIPT_DIR/statusline.py" 2>&1)
STATUSLINE_EXIT=$?

ASSERT1_OK=1
if [ "$STATUSLINE_EXIT" -ne 0 ]; then
    ASSERT1_OK=0
    echo "FAIL: assertion 1 - statusline.py exited $STATUSLINE_EXIT, expected 0"
    echo "--- statusline.py output ---"
    echo "$STATUSLINE_OUTPUT"
    echo "----------------------------"
fi

if [ ! -f "$CACHE_FILE" ]; then
    ASSERT1_OK=0
    echo "FAIL: assertion 1 - cache file was not created at $CACHE_FILE"
    echo "TMPDIR was set to: $TEST_TMPDIR"
fi

if [ "$ASSERT1_OK" = "1" ]; then
    CACHE_CHECK=$("$PY" - "$CACHE_FILE" << 'PYEOF'
import json, sys
path = sys.argv[1]
try:
    with open(path) as f:
        data = json.load(f)
except Exception as e:
    print(f"UNREADABLE:{e}")
    sys.exit(0)

required_top = ["context_window", "rate_limits", "model", "version"]
missing = [k for k in required_top if k not in data]
if missing:
    print(f"MISSING_KEYS:{','.join(missing)}")
    sys.exit(0)

rl = data.get("rate_limits") or {}
if "five_hour" not in rl or "seven_day" not in rl:
    print("MISSING_KEYS:rate_limits.five_hour/seven_day")
    sys.exit(0)

print("OK")
PYEOF
)
    if [ "$CACHE_CHECK" != "OK" ]; then
        ASSERT1_OK=0
        echo "FAIL: assertion 1 - cache file content check: $CACHE_CHECK"
        echo "--- cache file content ---"
        cat "$CACHE_FILE"
        echo "---------------------------"
    fi
fi

if [ "$ASSERT1_OK" = "1" ]; then
    echo "PASS: assertion 1 - statusline.py exits 0 and writes a well-formed cache file"
else
    FAILED=1
fi

# ---------------------------------------------------------------------------
# Assertion 2: check-budget.sh reads that cache and round-trips the exact
# synthetic percentages fed into statusline.py above.
#
# The old version of this assertion only grepped for "any NN% pattern" in
# the output. That passes even when a key gets renamed on one side of the
# statusline.py -> cache file -> check-budget.sh boundary, as long as SOME
# percentage happens to survive elsewhere. Asserting the exact, distinctive
# literal strings below - "5h: 37%" and not just "\d+%" - fails the moment
# either script stops agreeing with the other on a key name or a field.
# ---------------------------------------------------------------------------
ASSERT2_OK=1
if [ "$ASSERT1_OK" != "1" ]; then
    ASSERT2_OK=0
    echo "FAIL: assertion 2 - skipped because assertion 1 did not produce a usable cache file"
else
    BUDGET_OUTPUT=$(bash "$SCRIPT_DIR/check-budget.sh" 2>&1)
    BUDGET_EXIT=$?
    if [ "$BUDGET_EXIT" -ne 0 ]; then
        ASSERT2_OK=0
        echo "FAIL: assertion 2 - check-budget.sh exited $BUDGET_EXIT, expected 0"
        echo "--- check-budget.sh output ---"
        echo "$BUDGET_OUTPUT"
        echo "-------------------------------"
    else
        for EXPECTED in "5h: ${SYNTH_FIVE_HOUR}%" "7d: ${SYNTH_SEVEN_DAY}%" "ctx: ${SYNTH_CTX}%"; do
            if ! printf '%s' "$BUDGET_OUTPUT" | grep -qF -- "$EXPECTED"; then
                ASSERT2_OK=0
                echo "FAIL: assertion 2 - expected literal \"$EXPECTED\" in check-budget.sh output, not found"
            fi
        done
        if [ "$ASSERT2_OK" != "1" ]; then
            echo "--- check-budget.sh output ---"
            echo "$BUDGET_OUTPUT"
            echo "-------------------------------"
        fi
    fi
fi

if [ "$ASSERT2_OK" = "1" ]; then
    echo "PASS: assertion 2 - check-budget.sh round-trips the exact synthetic percentages from statusline.py"
else
    FAILED=1
fi

# ---------------------------------------------------------------------------
# Assertion 3: graceful no-data path. With the cache file removed,
# check-budget.sh must print its no-data message and exit 0, not fail. This
# is the only assertion testing the failure-mode promise the README makes:
# a missing/misconfigured statusline reports "no data", it does not error.
# ---------------------------------------------------------------------------
ASSERT3_OK=1
rm -f "$CACHE_FILE"
NODATA_OUTPUT=$(bash "$SCRIPT_DIR/check-budget.sh" 2>&1)
NODATA_EXIT=$?
# Literal message text, copied from check-budget.sh's own no-data branch.
EXPECTED_NODATA_MSG="Budget: no rate-limit data in statusline file"

if [ "$NODATA_EXIT" -ne 0 ]; then
    ASSERT3_OK=0
    echo "FAIL: assertion 3 - check-budget.sh exited $NODATA_EXIT with no cache file present, expected 0"
    echo "--- check-budget.sh output ---"
    echo "$NODATA_OUTPUT"
    echo "-------------------------------"
elif [ "$NODATA_OUTPUT" != "$EXPECTED_NODATA_MSG" ]; then
    ASSERT3_OK=0
    echo "FAIL: assertion 3 - expected exactly \"$EXPECTED_NODATA_MSG\""
    echo "--- check-budget.sh output ---"
    echo "$NODATA_OUTPUT"
    echo "-------------------------------"
fi

if [ "$ASSERT3_OK" = "1" ]; then
    echo "PASS: assertion 3 - check-budget.sh handles a missing cache file gracefully (no-data message, exit 0)"
else
    FAILED=1
fi

# ---------------------------------------------------------------------------
# Assertion 4: every settings.json snippet in the repo's docs uses only
# real settings keys, checked against one canonical list.
# ---------------------------------------------------------------------------
SETTINGS_OUTPUT=$("$PY" "$SCRIPT_DIR/selftest_settings.py" "$REPO_ROOT" 2>&1)
SETTINGS_EXIT=$?

if [ "$SETTINGS_EXIT" -eq 0 ]; then
    echo "PASS: assertion 4 - $SETTINGS_OUTPUT"
else
    FAILED=1
    echo "FAIL: assertion 4 - settings-key drift detected"
    echo "$SETTINGS_OUTPUT"
fi

# ---------------------------------------------------------------------------
# Assertion 5: every documented statusLine settings.json snippet reduces to
# the same canonical form as every other one. The key-drift check above only
# proves each key name is real - it says nothing about whether two docs
# structure the SAME setting differently (wrong nesting, an extra sibling
# key, a swapped value). This is the assertion that would have caught a
# past bug where a settings key was written wrongly in more than one place.
# ---------------------------------------------------------------------------
STATUSLINE_OUTPUT=$("$PY" "$SCRIPT_DIR/selftest_settings.py" "$REPO_ROOT" --statusline-agreement 2>&1)
STATUSLINE_SETTINGS_EXIT=$?

if [ "$STATUSLINE_SETTINGS_EXIT" -eq 0 ]; then
    echo "PASS: assertion 5 - $STATUSLINE_OUTPUT"
else
    FAILED=1
    echo "FAIL: assertion 5 - statusLine snippets disagree with each other"
    echo "$STATUSLINE_OUTPUT"
fi

# ---------------------------------------------------------------------------
# Assertion 6: fenced python and bash blocks in the hooks docs that are
# whole, standalone scripts are syntactically valid (python3 -m py_compile /
# bash -n).
#
# NOTE: this is a SYNTAX check only, not a behaviour check. A block passing
# here means it parses - it says nothing about whether the hook does the
# right thing at runtime. Green here must never be read as "these hooks
# work".
#
# Skip rule for telling a whole script apart from a fragment: a block only
# counts if its FIRST line is a shebang ("#!..."). Every fragment in these
# two docs - a WRONG/CORRECT comparison that contains an intentional
# SyntaxError for illustration, a bare "python3 -c ..." one-liner, a snippet
# meant to be pasted into the middle of an existing hook - lacks a shebang,
# because none of them are standalone scripts. Every full recipe in these
# docs opens with one. This is deliberately the ONLY signal used: a block is
# not excluded just because it contains a "..." placeholder in a comment
# (the fail-open wrapper example does exactly that and is still a complete,
# valid, checkable script), so the rule stays a single unambiguous check
# instead of a pile of heuristics that could disagree with each other.
# ---------------------------------------------------------------------------
HOOKS_DOC_1="$REPO_ROOT/docs/08-hooks.md"
HOOKS_DOC_2="$REPO_ROOT/docs/09-hooks-recipes.md"
HOOKS_DOC_3="$REPO_ROOT/docs/10-hook-failure-modes.md"
HOOKBLOCK_DIR="$TEST_TMPDIR/hookblocks"
mkdir -p "$HOOKBLOCK_DIR"

ASSERT6_OK=1

BLOCKS_FOUND=$("$PY" - "$HOOKBLOCK_DIR" "$HOOKS_DOC_1" "$HOOKS_DOC_2" "$HOOKS_DOC_3" << 'PYEOF'
import re, sys, os

out_dir = sys.argv[1]
doc_paths = sys.argv[2:]

FENCE_RE = re.compile(r"```(python|bash)\n(.*?)```", re.DOTALL)

n = 0
manifest = []
for doc_path in doc_paths:
    with open(doc_path, encoding="utf-8") as f:
        text = f.read()
    for m in FENCE_RE.finditer(text):
        lang, block = m.group(1), m.group(2)
        lines = block.splitlines()
        first_line = lines[0] if lines else ""
        if not first_line.startswith("#!"):
            # Fragment, not a whole script - see the skip-rule comment in
            # selftest.sh for why shebang presence is the chosen signal.
            continue
        n += 1
        ext = "py" if lang == "python" else "sh"
        out_path = os.path.join(out_dir, f"block{n}.{ext}")
        # newline="" everywhere in this block: on Windows, text-mode writes
        # translate every "\n" to "\r\n". Left alone that plants a stray
        # \r on the end of the "lang" field of every manifest.tsv row (and
        # inside the extracted scripts themselves), which silently breaks
        # the `[ "$LANG" = "python" ]` comparison below and makes every
        # python block get bash-syntax-checked instead of py_compile'd.
        with open(out_path, "w", encoding="utf-8", newline="") as out:
            out.write(block)
        manifest.append(f"{out_path}\t{doc_path}\t{lang}")

with open(os.path.join(out_dir, "manifest.tsv"), "w", encoding="utf-8", newline="") as f:
    f.write("\n".join(manifest))

print(n)
PYEOF
)

if ! [ "$BLOCKS_FOUND" -gt 0 ] 2>/dev/null; then
    ASSERT6_OK=0
    echo "FAIL: assertion 6 - found 0 shebang-prefixed python/bash blocks across the hooks docs."
    echo "This means the extractor did not run, not that it passed - the fence"
    echo "pattern or shebang signal in selftest.sh is not matching anything."
fi

if [ "$ASSERT6_OK" = "1" ]; then
    while IFS=$'\t' read -r BLOCK_PATH DOC_PATH LANG; do
        [ -z "$BLOCK_PATH" ] && continue
        if [ "$LANG" = "python" ]; then
            BLOCK_ERR=$("$PY" -m py_compile "$BLOCK_PATH" 2>&1)
            BLOCK_RC=$?
        else
            BLOCK_ERR=$(bash -n "$BLOCK_PATH" 2>&1)
            BLOCK_RC=$?
        fi
        if [ "$BLOCK_RC" -ne 0 ]; then
            ASSERT6_OK=0
            echo "FAIL: assertion 6 - $BLOCK_PATH (from $DOC_PATH) failed a $LANG syntax check"
            echo "--- error ---"
            echo "$BLOCK_ERR"
            echo "-------------"
        fi
    done < "$HOOKBLOCK_DIR/manifest.tsv"
fi

if [ "$ASSERT6_OK" = "1" ]; then
    echo "PASS: assertion 6 - $BLOCKS_FOUND whole-script block(s) in the hooks docs pass a syntax check (syntax only, not a behaviour check)"
else
    FAILED=1
fi

# ---------------------------------------------------------------------------
# Assertion 7: every file in docs/ carries exactly one tier marker line
# (Core or Field note) among its opening lines. The marker line is what
# tells a reader whether a doc's claims are machine-asserted by this same
# script or are dated, unverified field notes - a doc with zero markers
# gives no signal either way, and a doc with two is ambiguous about which
# one is authoritative. Only the opening lines are scanned (not the whole
# file) so a marker-shaped line appearing later, inside a quoted example or
# a worked-through recipe, cannot be mistaken for the file's own tier.
# ---------------------------------------------------------------------------
ASSERT7_OK=1
MARKER_RE='^> \*\*(Core|Field note)\.\*\*'
DOCS_CHECKED=0

for DOC_PATH in "$REPO_ROOT"/docs/*.md; do
    [ -f "$DOC_PATH" ] || continue
    DOCS_CHECKED=$((DOCS_CHECKED + 1))
    MARKER_COUNT=$(head -n 10 "$DOC_PATH" | grep -cE "$MARKER_RE")
    if [ "$MARKER_COUNT" -ne 1 ]; then
        ASSERT7_OK=0
        echo "FAIL: assertion 7 - $DOC_PATH has $MARKER_COUNT tier marker line(s) in its opening lines, expected exactly 1"
    fi
done

if [ "$DOCS_CHECKED" -eq 0 ]; then
    ASSERT7_OK=0
    echo "FAIL: assertion 7 - found 0 files under docs/*.md to check."
    echo "This means the glob did not run, not that it passed."
fi

if [ "$ASSERT7_OK" = "1" ]; then
    echo "PASS: assertion 7 - all $DOCS_CHECKED file(s) under docs/ carry exactly one tier marker line"
else
    FAILED=1
fi

# ---------------------------------------------------------------------------
# Assertion 8: no long sentence appears in two places across this repo's .md
# files, outside a short, scoped allow list. This is the check the other
# assertions above don't cover - they check settings snippets, scripts, and
# tier markers, but nothing here asserts prose, and prose is where the
# single-source rule actually breaks: a correction lands in one copy while
# another quietly disagrees. The allow list in tools/selftest_dedup.py is
# scoped per exception to the exact files it was cleared between, so the
# same sentence turning up in a third file still fails.
# ---------------------------------------------------------------------------
DEDUP_OUTPUT=$("$PY" "$SCRIPT_DIR/selftest_dedup.py" "$REPO_ROOT" 2>&1)
DEDUP_EXIT=$?

if [ "$DEDUP_EXIT" -eq 0 ]; then
    echo "PASS: assertion 8 - $DEDUP_OUTPUT"
else
    FAILED=1
    echo "FAIL: assertion 8 - duplicated prose detected outside the scoped allow list"
    echo "$DEDUP_OUTPUT"
fi

# ---------------------------------------------------------------------------
# Assertion 9: the token-baseline and session-brief tools pass their built-in
# selftests. Each selftest includes a positive control that must be flagged,
# so a tool that silently stopped checking would fail here.
# ---------------------------------------------------------------------------
for TOOL in token-baseline.py session-brief.py; do
    TOOL_OUTPUT=$("$PY" "$SCRIPT_DIR/$TOOL" --selftest 2>&1)
    if [ $? -eq 0 ]; then
        echo "PASS: assertion 9 - $TOOL selftest ($TOOL_OUTPUT)"
    else
        FAILED=1
        echo "FAIL: assertion 9 - $TOOL selftest"
        echo "$TOOL_OUTPUT"
    fi
done

# ---------------------------------------------------------------------------
# Assertion 10: the generic privacy scan passes its own positive and negative
# controls (including the history mode: a deleted leak and a term in an old
# commit message are found, a clean history passes), the installed hooks match
# the tracked ones, and the whole working tree is clean under it.
# ---------------------------------------------------------------------------
PRIV_OUTPUT=$(sh "$SCRIPT_DIR/selftest_privacy.sh" 2>&1 | tail -1)
if [ "$PRIV_OUTPUT" = "PRIVACY SELFTEST PASS" ]; then
    echo "PASS: assertion 10 - privacy scan controls ($PRIV_OUTPUT)"
else
    FAILED=1
    echo "FAIL: assertion 10 - privacy scan controls ($PRIV_OUTPUT)"
fi
# The tree scan reads the repo of the CURRENT directory, so every call goes through this function, which
# enters the repo root first: running this script from another directory (even another git repo) must
# still scan this repo.
playbook_tree_scan() { (cd "$REPO_ROOT" && sh "$REPO_ROOT/hooks/privacy-scan.sh" tree 2>&1); }
if TREE_OUTPUT=$(playbook_tree_scan); then
    echo "PASS: assertion 10 - working tree is clean under the generic privacy scan"
else
    FAILED=1
    echo "FAIL: assertion 10 - generic privacy scan hit in the working tree"
    echo "$TREE_OUTPUT"
fi
# Control: from inside a different git repo that holds a leak, the unrooted scan finds the other repo
# (positive control: the other repo is scannable), while playbook_tree_scan still scans this repo.
OTHER_REPO="$TEST_TMPDIR/other-repo"
mkdir -p "$OTHER_REPO"
(cd "$OTHER_REPO" && git init -q . && printf 'ask jane.doe@%s\n' "acme-corp.org" > leak.txt && git add leak.txt) >/dev/null 2>&1
UNROOTED=$(cd "$OTHER_REPO" && sh "$REPO_ROOT/hooks/privacy-scan.sh" tree 2>&1)
ROOTED=$(cd "$OTHER_REPO" && playbook_tree_scan)
ROOTED_EXIT=$?
case "$UNROOTED" in *"leak.txt"*) UNROOTED_SEES_OTHER=1 ;; *) UNROOTED_SEES_OTHER=0 ;; esac
case "$ROOTED" in *"leak.txt"*) ROOTED_SEES_OTHER=1 ;; *) ROOTED_SEES_OTHER=0 ;; esac
if [ "$UNROOTED_SEES_OTHER" -eq 1 ] && [ "$ROOTED_SEES_OTHER" -eq 0 ] && [ "$ROOTED_EXIT" -eq 0 ]; then
    echo "PASS: assertion 10 - tree scan is anchored to this repo when run from another git repo"
else
    FAILED=1
    echo "FAIL: assertion 10 - tree scan anchoring (unrooted sees other=$UNROOTED_SEES_OTHER, rooted sees other=$ROOTED_SEES_OTHER, rooted exit=$ROOTED_EXIT)"
fi

# ---------------------------------------------------------------------------
# Assertion 11: the backlog tool's own tests pass (stdlib runner, no pytest).
# The runner exits non-zero when nothing ran, so an empty suite cannot pass.
# ---------------------------------------------------------------------------
BACKLOG_OUTPUT=$("$PY" "$SCRIPT_DIR/backlog_tests/run.py" 2>&1)
BACKLOG_EXIT=$?
if [ "$BACKLOG_EXIT" -eq 0 ] && [ "$(printf '%s\n' "$BACKLOG_OUTPUT" | tail -1)" = "BACKLOG TESTS PASS" ]; then
    echo "PASS: assertion 11 - $(printf '%s\n' "$BACKLOG_OUTPUT" | tail -2 | head -1)"
else
    FAILED=1
    echo "FAIL: assertion 11 - backlog tool tests failed (exit $BACKLOG_EXIT)"
    echo "$BACKLOG_OUTPUT"
fi

# ---------------------------------------------------------------------------
# Assertion 12: the shorthand-term hook behaves against the shipped glossary
# template (hit, miss, ignored paste/fence/frame, tip cap, fail-open) and the
# template rows are well formed. Includes an empty-glossary control.
# ---------------------------------------------------------------------------
SHORTHAND_OUTPUT=$("$PY" "$REPO_ROOT/hooks/examples/test_shorthand_detector.py" 2>&1)
if [ $? -eq 0 ]; then
    echo "PASS: assertion 12 - $SHORTHAND_OUTPUT"
else
    FAILED=1
    echo "FAIL: assertion 12 - shorthand hook tests failed"
    echo "$SHORTHAND_OUTPUT"
fi

# ---------------------------------------------------------------------------
# Assertion 13: the doc linter passes its unit tests, and this repo is clean
# under the shipped ruleset (tools/doc_lint/doc_lint.config.json). The tests
# include a positive control per check type, so a rule that stopped firing
# fails here; the repo run proves the docs obey their own rules.
# ---------------------------------------------------------------------------
LINT_TEST_OUTPUT=$(cd "$SCRIPT_DIR/doc_lint" && "$PY" -m unittest test_doc_lint 2>&1)
LINT_TEST_EXIT=$?
if [ "$LINT_TEST_EXIT" -eq 0 ]; then
    echo "PASS: assertion 13 - doc_lint unit tests ($(printf '%s\n' "$LINT_TEST_OUTPUT" | grep -E '^Ran ' | head -1))"
else
    FAILED=1
    echo "FAIL: assertion 13 - doc_lint unit tests failed"
    echo "$LINT_TEST_OUTPUT"
fi
LINT_REPO_OUTPUT=$("$PY" "$SCRIPT_DIR/doc_lint/doc_lint.py" --config "$SCRIPT_DIR/doc_lint/doc_lint.config.json" --root "$REPO_ROOT" 2>&1)
if [ $? -eq 0 ]; then
    echo "PASS: assertion 13 - repo is clean under the shipped doc_lint ruleset"
else
    FAILED=1
    echo "FAIL: assertion 13 - doc_lint findings in this repo"
    echo "$LINT_REPO_OUTPUT"
fi

# ---------------------------------------------------------------------------
# Assertion 14: the capacity checker passes its built-in selftest, which
# includes positive controls (a soft overrun warns, a hard overrun fails, a
# group over budget fails while each member is under its own limit) and a
# check that the shipped example config parses.
# ---------------------------------------------------------------------------
CAP_OUTPUT=$("$PY" "$SCRIPT_DIR/check-capacity.py" --selftest 2>&1)
CAP_EXIT=$?
if [ "$CAP_EXIT" -eq 0 ]; then
    CAP_CFG_OUTPUT=$("$PY" "$SCRIPT_DIR/check-capacity.py" --config "$REPO_ROOT/config/capacity.example.json" --root "$TEST_TMPDIR" 2>&1)
    CAP_CFG_EXIT=$?
else
    CAP_CFG_EXIT=0
fi
if [ "$CAP_EXIT" -eq 0 ] && [ "$CAP_CFG_EXIT" -ne 2 ]; then
    echo "PASS: assertion 14 - check-capacity.py ($CAP_OUTPUT; example config parses)"
else
    FAILED=1
    echo "FAIL: assertion 14 - check-capacity.py"
    echo "$CAP_OUTPUT"
    echo "$CAP_CFG_OUTPUT"
fi

# ---------------------------------------------------------------------------
# Assertion 15: the scratch-marker checker passes its selftest (a reached
# date, an aged free-text condition and a missing marker are flagged; a
# future date and a fresh entry are not) and exits 2 on a missing folder.
# ---------------------------------------------------------------------------
SCR_OUTPUT=$("$PY" "$SCRIPT_DIR/scratch-overdue.py" --selftest 2>&1)
SCR_EXIT=$?
"$PY" "$SCRIPT_DIR/scratch-overdue.py" --dir "$TEST_TMPDIR/no-such-scratch-dir" >/dev/null 2>&1
SCR_MISSING_EXIT=$?
if [ "$SCR_EXIT" -eq 0 ] && [ "$SCR_MISSING_EXIT" -eq 2 ]; then
    echo "PASS: assertion 15 - scratch-overdue.py ($SCR_OUTPUT; missing folder exits 2)"
else
    FAILED=1
    echo "FAIL: assertion 15 - scratch-overdue.py (selftest exit $SCR_EXIT, missing-folder exit $SCR_MISSING_EXIT, wanted 0 and 2)"
    echo "$SCR_OUTPUT"
fi

# ---------------------------------------------------------------------------
# Assertion 16: the prose and commit-message linter passes its selftest and
# refuses a long subject, a wrapped paragraph and a dash character.
# ---------------------------------------------------------------------------
PL_OUTPUT=$("$PY" "$SCRIPT_DIR/prose-lint.py" --selftest 2>&1)
PL_EXIT=$?
PL_OUTPUT=$(echo "$PL_OUTPUT" | tail -1)
printf 'Subject\n\nfirst short line\nsecond short line\n' > "$TEST_TMPDIR/pl-msg.txt"
"$PY" "$SCRIPT_DIR/prose-lint.py" --commit-msg "$TEST_TMPDIR/pl-msg.txt" >/dev/null 2>&1
PL_BAD_EXIT=$?
if [ "$PL_EXIT" -eq 0 ] && [ "$PL_BAD_EXIT" -eq 1 ]; then
    echo "PASS: assertion 16 - prose-lint.py ($PL_OUTPUT; wrapped message exits 1)"
else
    FAILED=1
    echo "FAIL: assertion 16 - prose-lint.py (selftest exit $PL_EXIT, wrapped-message exit $PL_BAD_EXIT, wanted 0 and 1)"
    echo "$PL_OUTPUT"
fi

# ---------------------------------------------------------------------------
# Assertion 17: the hook-health checker flags each defect it names (missing
# timeout, bare python3 in a command or in a script the command runs, missing
# script, bad statusLine, disableAllHooks, unparseable settings) and passes a
# clean file; the example hook suite, which drives it, also passes.
# ---------------------------------------------------------------------------
HH_OUTPUT=$("$PY" "$REPO_ROOT/hooks/examples/check_hook_health.py" --selftest 2>&1)
HH_EXIT=$?
HX_OUTPUT=$("$PY" "$REPO_ROOT/hooks/examples/test_examples.py" 2>&1)
HX_EXIT=$?
if [ "$HH_EXIT" -eq 0 ] && [ "$HX_EXIT" -eq 0 ]; then
    echo "PASS: assertion 17 - hook health ($HH_OUTPUT) and example hooks ($HX_OUTPUT)"
else
    FAILED=1
    echo "FAIL: assertion 17 - hook health selftest exit $HH_EXIT, example hooks exit $HX_EXIT"
    echo "$HH_OUTPUT"
    echo "$HX_OUTPUT"
fi

# ---------------------------------------------------------------------------
# Verdict (always last line, so `tail -3` gives the result)
# ---------------------------------------------------------------------------
if [ "$FAILED" -eq 0 ]; then
    echo "VERDICT: PASS - all assertions passed"
    exit 0
else
    echo "VERDICT: FAIL - see failures above"
    exit 1
fi
