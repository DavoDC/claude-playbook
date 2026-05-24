#!/bin/bash
# session-status.sh - Output budget status in a compact 2-line format.
# Called by /dev-session and /loop at session start to make budget-aware decisions.
#
# Output format:
#   WorkspaceName | Model (200k) | 5h: 43% (r 1h14m) | 7d: 23% (r 6d8h) | ctx: 43%
#   Claude v2.1.143 | 10:35AM | Sun 24/05/2026
#
# Usage: bash tools/session-status.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Workspace name
WORKSPACE_NAME=$(basename "$REPO_ROOT")

# Model from statusline JSON (written by statusline.py on each CC update)
MODEL=$(python3 << 'PYEOF'
import json, os, tempfile
try:
    f = os.path.join(tempfile.gettempdir(), 'claude-statusline-data.json')
    d = json.load(open(f))
    name = (d.get('model') or {}).get('display_name', '')
    print(name.replace('Claude ', '') if name else 'Unknown')
except Exception:
    print('Unknown')
PYEOF
)

# Budget info from check-budget.sh
BUDGET_OUTPUT=$("$SCRIPT_DIR/check-budget.sh" 2>/dev/null || echo "Budget unavailable")
BUDGET_5H=$(echo "$BUDGET_OUTPUT" | grep -o '5h: [0-9]*% ([^)]*)' | head -1)
BUDGET_7D=$(echo "$BUDGET_OUTPUT" | grep -o '7d: [0-9]*% ([^)]*)' | head -1)
BUDGET_CTX=$(echo "$BUDGET_OUTPUT" | grep -o 'ctx: [0-9]*%' | head -1)

# Time and date
CURRENT_TIME=$(date +"%I:%M%p")
CURRENT_DATE=$(date +"%a %d/%m/%Y")

# Claude version
CLAUDE_VERSION=$(python3 << 'PYEOF'
import json, os, tempfile, re
try:
    f = os.path.join(tempfile.gettempdir(), 'claude-statusline-data.json')
    v = json.load(open(f)).get('version', '')
    if v and v != '?':
        print(v); exit()
except Exception:
    pass
agent = os.environ.get('AI_AGENT', '')
m = re.search(r'(\d+)-(\d+)-(\d+)', agent)
if m:
    print(f'{m.group(1)}.{m.group(2)}.{m.group(3)}')
else:
    print('?')
PYEOF
)

echo "$WORKSPACE_NAME | $MODEL (200k) | $BUDGET_5H | $BUDGET_7D | $BUDGET_CTX"
echo "Claude v$CLAUDE_VERSION | $CURRENT_TIME | $CURRENT_DATE"
