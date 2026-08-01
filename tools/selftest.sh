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
#
# Output discipline: silent pass, verbose fail. Each passing assertion
# prints one PASS line and nothing else. A failing assertion prints
# everything needed to debug it. The overall verdict is the LAST line.
#
# Usage: bash tools/selftest.sh

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

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

STATUSLINE_OUTPUT=$(printf '%s' "$SYNTHETIC_JSON" | python3 "$SCRIPT_DIR/statusline.py" 2>&1)
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
    CACHE_CHECK=$(python3 - "$CACHE_FILE" << 'PYEOF'
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
SETTINGS_OUTPUT=$(python3 "$SCRIPT_DIR/selftest_settings.py" "$REPO_ROOT" 2>&1)
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
STATUSLINE_OUTPUT=$(python3 "$SCRIPT_DIR/selftest_settings.py" "$REPO_ROOT" --statusline-agreement 2>&1)
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
HOOKS_DOC_1="$REPO_ROOT/docs/09-hooks.md"
HOOKS_DOC_2="$REPO_ROOT/docs/09-hooks-recipes.md"
HOOKBLOCK_DIR="$TEST_TMPDIR/hookblocks"
mkdir -p "$HOOKBLOCK_DIR"

ASSERT6_OK=1

BLOCKS_FOUND=$(python3 - "$HOOKBLOCK_DIR" "$HOOKS_DOC_1" "$HOOKS_DOC_2" << 'PYEOF'
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
            BLOCK_ERR=$(python3 -m py_compile "$BLOCK_PATH" 2>&1)
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
# Verdict (always last line, so `tail -3` gives the result)
# ---------------------------------------------------------------------------
if [ "$FAILED" -eq 0 ]; then
    echo "VERDICT: PASS - all assertions passed"
    exit 0
else
    echo "VERDICT: FAIL - see failures above"
    exit 1
fi
