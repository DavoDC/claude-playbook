#!/bin/bash
# selftest.sh - self-test for the budget-tracking tools in this repo.
#
# Three assertions, no network, no installs beyond python3 and bash:
#   1. statusline.py accepts synthetic status JSON on stdin, exits 0, and
#      writes a cache file containing the expected keys.
#   2. check-budget.sh reads that same cache and emits a percentage.
#   3. every Claude Code settings.json snippet documented anywhere in this
#      repo uses only real settings.json keys (tools/selftest_settings.py
#      holds the one canonical key list; see that file for the reference).
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

# ---------------------------------------------------------------------------
# Assertion 1: statusline.py accepts synthetic input, exits 0, writes cache
# ---------------------------------------------------------------------------
SYNTHETIC_JSON='{
  "model": {"display_name": "Claude Sonnet 5", "id": "claude-sonnet-5"},
  "context_window": {"used_percentage": 42, "context_window_size": 200000},
  "rate_limits": {
    "five_hour": {"used_percentage": 33, "resets_at": 9999999999},
    "seven_day": {"used_percentage": 12, "resets_at": 9999999999}
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
# Assertion 2: check-budget.sh parses that cache and emits a percentage
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
    elif ! printf '%s' "$BUDGET_OUTPUT" | grep -Eq '[0-9]+%'; then
        ASSERT2_OK=0
        echo "FAIL: assertion 2 - no NN% pattern found in check-budget.sh output"
        echo "--- check-budget.sh output ---"
        echo "$BUDGET_OUTPUT"
        echo "-------------------------------"
    fi
fi

if [ "$ASSERT2_OK" = "1" ]; then
    echo "PASS: assertion 2 - check-budget.sh reads the cache and emits a percentage"
else
    FAILED=1
fi

# ---------------------------------------------------------------------------
# Assertion 3: every settings.json snippet in the repo's docs uses only
# real settings keys, checked against one canonical list.
# ---------------------------------------------------------------------------
SETTINGS_OUTPUT=$(python3 "$SCRIPT_DIR/selftest_settings.py" "$REPO_ROOT" 2>&1)
SETTINGS_EXIT=$?

if [ "$SETTINGS_EXIT" -eq 0 ]; then
    echo "PASS: assertion 3 - $SETTINGS_OUTPUT"
else
    FAILED=1
    echo "FAIL: assertion 3 - settings-key drift detected"
    echo "$SETTINGS_OUTPUT"
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
