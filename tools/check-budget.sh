#!/bin/bash
# check-budget.sh - Read statusline JSON and format budget status for Claude
# Callable from Bash during sessions to check current budget
# Also sourced by session-context.sh for session-start injection

# Parse JSON using a Python one-liner (more reliable than jq on all platforms)
# Python finds the file using the same tempfile logic as statusline.py
BUDGET_JSON=$(python3 << 'PYEOF'
import json, sys, os, tempfile
from datetime import datetime, timedelta

try:
    # Use same logic as statusline.py: tempfile.gettempdir()
    statusline_file = os.path.join(tempfile.gettempdir(), 'claude-statusline-data.json')
    if not os.path.exists(statusline_file):
        print("Budget: no rate-limit data in statusline file")
        sys.exit(0)

    # Retry up to 3 times: statusline.py may be mid-write leaving the file momentarily empty
    import time
    data = None
    for attempt in range(3):
        try:
            with open(statusline_file) as f:
                content = f.read().strip()
            if content:
                data = json.loads(content)
                break
        except Exception:
            pass
        if attempt < 2:
            time.sleep(0.15)
    if data is None:
        print("Budget: statusline file unreadable (empty or mid-write)")
        sys.exit(0)
except Exception as e:
    print(f"error:{e}")
    sys.exit(1)

# Extract budget info
ctx = data.get('context_window') or {}
rl = data.get('rate_limits') or {}
five_hour = (rl.get('five_hour') or {})
seven_day = (rl.get('seven_day') or {})

ctx_pct = ctx.get('used_percentage')
ctx_size = ctx.get('context_window_size', 200000)
five_pct = five_hour.get('used_percentage')
seven_pct = seven_day.get('used_percentage')
five_resets = five_hour.get('resets_at')
seven_resets = seven_day.get('resets_at')

def format_time_remaining(timestamp):
    """Convert Unix timestamp to countdown."""
    if not timestamp:
        return None
    try:
        now = datetime.now().timestamp()
        diff = timestamp - now
        if diff <= 0:
            return '0m'

        days = int(diff // 86400)
        remaining = diff % 86400
        hours = int(remaining // 3600)
        minutes = int((remaining % 3600) // 60)

        if days > 0:
            return f'{days}d{hours}h'
        elif hours > 0:
            return f'{hours}h{minutes:02d}m'
        else:
            return f'{minutes}m'
    except Exception:
        return None

# Format output
parts = []

# 5-hour limit (FIRST)
if five_pct is not None:
    five_label = f'{int(five_pct)}%'
    reset_in = format_time_remaining(five_resets)
    if reset_in:
        parts.append(f'5h: {five_label} (r {reset_in})')
    else:
        parts.append(f'5h: {five_label}')

# 7-day limit (SECOND)
if seven_pct is not None:
    seven_label = f'{int(seven_pct)}%'
    reset_in = format_time_remaining(seven_resets)
    if reset_in:
        parts.append(f'7d: {seven_label} (r {reset_in})')
    else:
        parts.append(f'7d: {seven_label}')

# Context usage (THIRD)
if ctx_pct is not None:
    ctx_label = f'{int(ctx_pct)}%'
    parts.append(f'ctx: {ctx_label}')

if parts:
    budget_str = '  |  '.join(parts)
    print(f"Budget: {budget_str}")

    # Check for critical conditions
    if five_pct is not None and five_pct >= 83:
        reset_in = format_time_remaining(five_resets)
        # Parse "1h32m" / "2d3h" / "45m" to seconds using regex
        import re as _re
        def _t(s, pat): m = _re.search(pat, s or ''); return int(m.group(1)) if m else 0
        _secs = _t(reset_in, r'(\d+)d')*86400 + _t(reset_in, r'(\d+)h')*3600 + _t(reset_in, r'(\d+)m')*60 + 300
        # ScheduleWakeup clamps delaySeconds to 60-3600s, so a reset further out than an
        # hour needs a bounded wakeup that re-checks and reschedules, not one long sleep
        _clamped = max(60, min(_secs, 3600))
        print(f"5h NEARLY EXHAUSTED: {int(five_pct)}%, resets in {reset_in} - call ScheduleWakeup({_clamped}) now, then re-check and reschedule (capped at 3600s each time) until the reset has passed")

else:
    print("Budget: unable to parse rate limit data")

PYEOF
)

# Function for session-context.sh to source
format_budget_status() {
    python3 << 'PYEOF'
import json, sys, os, tempfile
from datetime import datetime

try:
    statusline_file = os.path.join(tempfile.gettempdir(), 'claude-statusline-data.json')
    with open(statusline_file) as f:
        data = json.load(f)
except Exception:
    print("Budget: no rate-limit data in statusline file")
    sys.exit(0)

# Extract budget info
ctx = data.get('context_window') or {}
rl = data.get('rate_limits') or {}
five_hour = (rl.get('five_hour') or {})
seven_day = (rl.get('seven_day') or {})

ctx_pct = ctx.get('used_percentage')
five_pct = five_hour.get('used_percentage')
seven_pct = seven_day.get('used_percentage')
five_resets = five_hour.get('resets_at')
seven_resets = seven_day.get('resets_at')

def format_time_remaining(timestamp):
    """Convert Unix timestamp to countdown."""
    if not timestamp:
        return None
    try:
        now = datetime.now().timestamp()
        diff = timestamp - now
        if diff <= 0:
            return '0m'

        days = int(diff // 86400)
        remaining = diff % 86400
        hours = int(remaining // 3600)
        minutes = int((remaining % 3600) // 60)

        if days > 0:
            return f'{days}d{hours}h'
        elif hours > 0:
            return f'{hours}h{minutes:02d}m'
        else:
            return f'{minutes}m'
    except Exception:
        return None

# Format output
parts = []

# 5-hour limit (FIRST)
if five_pct is not None:
    five_label = f'{int(five_pct)}%'
    reset_in = format_time_remaining(five_resets)
    if reset_in:
        parts.append(f'5h: {five_label} (r {reset_in})')
    else:
        parts.append(f'5h: {five_label}')

# 7-day limit (SECOND)
if seven_pct is not None:
    seven_label = f'{int(seven_pct)}%'
    reset_in = format_time_remaining(seven_resets)
    if reset_in:
        parts.append(f'7d: {seven_label} (r {reset_in})')
    else:
        parts.append(f'7d: {seven_label}')

# Context usage (THIRD)
if ctx_pct is not None:
    ctx_label = f'{int(ctx_pct)}%'
    parts.append(f'ctx: {ctx_label}')

if parts:
    budget_str = '  |  '.join(parts)
    print(f"Budget: {budget_str}")
else:
    print("Budget: no rate-limit data available")
PYEOF
}

# If sourced, function is defined above. If executed, run the main logic
if [ "$0" = "${BASH_SOURCE[0]}" ]; then
    echo "$BUDGET_JSON"
fi
