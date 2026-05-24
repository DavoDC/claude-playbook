#!/usr/bin/env python3
"""Claude Code statusline script.

Configure in .claude/settings.json:
  {
    "statusline": {
      "command": "python3 /path/to/tools/statusline.py"
    }
  }

Claude Code calls this with status JSON on stdin every status update.
This script: (1) prints a formatted status line, (2) writes budget JSON to
a temp file at {tempdir}/claude-statusline-data.json so check-budget.sh
and session-status.sh can read it without making API calls.
"""
import sys, json, os, tempfile
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

try:
    d = json.load(sys.stdin)
except Exception:
    print('statusline parse error'); sys.exit(0)

# ANSI color codes
RESET   = '\033[0m'
BOLD    = '\033[1m'
DIM     = '\033[2m'
RED     = '\033[91m'
GREEN   = '\033[92m'
ORANGE  = '\033[38;5;208m'
MUTED   = '\033[38;5;250m'
PASTEL_HAIKU  = '\033[38;5;215m'
PASTEL_SONNET = '\033[38;5;153m'
PASTEL_OPUS   = '\033[38;5;183m'

def get_model_color(name):
    n = name.lower()
    if 'haiku'  in n: return PASTEL_HAIKU
    if 'sonnet' in n: return PASTEL_SONNET
    if 'opus'   in n: return PASTEL_OPUS
    return MUTED

def col_pct(pct, warn=80, crit=90):
    if pct is None: return '-'
    p = int(pct)
    if p >= crit:  return f'{RED}{p}%{RESET}'
    if p >= warn:  return f'{ORANGE}{p}%{RESET}'
    return f'{GREEN}{p}%{RESET}'

def fmt_countdown(ts):
    """Unix timestamp -> human countdown like '2h05m' or '4d17h'."""
    if not ts: return None
    try:
        diff = ts - datetime.now().timestamp()
        if diff <= 0: return '0m'
        d_ = int(diff // 86400)
        h  = int((diff % 86400) // 3600)
        m  = int((diff % 3600) // 60)
        if d_ > 0: return f'{d_}d{h}h'
        if h  > 0: return f'{h}h{m:02d}m'
        return f'{m}m'
    except Exception:
        return None

# Extract fields
model_raw    = (d.get('model') or {}).get('display_name', '?').replace(' context)', ')')
ctx          = d.get('context_window') or {}
ctx_pct      = ctx.get('used_percentage')
ctx_size     = ctx.get('context_window_size', 200000)
ctx_label    = '1M' if ctx_size >= 1_000_000 else f'{ctx_size // 1000}k'
rl           = d.get('rate_limits') or {}
five         = (rl.get('five_hour')  or {}).get('used_percentage')
week         = (rl.get('seven_day')  or {}).get('used_percentage')
five_resets  = (rl.get('five_hour')  or {}).get('resets_at')
week_resets  = (rl.get('seven_day')  or {}).get('resets_at')
version      = d.get('version', '?')

# Model label with color
color       = get_model_color(model_raw)
model_label = f'{color}{BOLD}{model_raw}{RESET} {MUTED}({ctx_label}){RESET}'

# Rate limit section
rl_parts = []
if five is not None:
    r = fmt_countdown(five_resets)
    s = f'5h: {col_pct(five, 75, 90)}'
    if r: s += f' (r {MUTED}{r}{RESET})'
    rl_parts.append(s)
if week is not None:
    r = fmt_countdown(week_resets)
    s = f'7d: {col_pct(week, 70, 85)}'
    if r: s += f' (r {MUTED}{r}{RESET})'
    rl_parts.append(s)

ctx_str = f'ctx: {col_pct(ctx_pct, 80, 95)}' if ctx_pct is not None else ''

# Optional: workspace indicator (set CLAUDE_WORKSPACE env var to highlight when in-workspace)
ws_path    = os.environ.get('CLAUDE_WORKSPACE', '').replace('\\', '/').rstrip('/')
cwd        = (d.get('cwd') or '').replace('\\', '/').rstrip('/')
ws_label   = ''
if ws_path and cwd:
    if cwd == ws_path or cwd.startswith(ws_path + '/'):
        ws_label = f'{GREEN}✔ Workspace{RESET} | '
    else:
        ws_label = f'{RED}outside workspace{RESET} | '

# Time/date
now      = datetime.now()
time_str = now.strftime('%I:%M%p').lstrip('0')
date_str = now.strftime('%a %d/%m/%Y')

# Effort/thinking mode
effort  = (d.get('effort')   or {}).get('level', '')
thnk    = (d.get('thinking') or {}).get('enabled', False)
effort_str = ''
if effort:
    abbr = {'low': 'low', 'medium': 'med', 'high': 'hi', 'xhigh': 'xhi', 'max': 'max'}.get(effort, effort)
    effort_str = f' {BOLD}{abbr}{RESET}'
    if thnk: effort_str += f' \033[96m+thnk{RESET}'

# Session name
sname = d.get('session_name', '')
sname_str = f' [{DIM}{sname}{RESET}]' if sname else ''

# Build output lines
parts = [x for x in rl_parts + ([ctx_str] if ctx_str else []) if x]
budget_str = ' | '.join(parts) or '-'

print(f'{ws_label}{model_label}{effort_str} | {budget_str}{sname_str}')
print(f'Claude v{version} | {time_str} | {date_str}')

# Write budget JSON to temp file for check-budget.sh / session-status.sh
try:
    payload = {
        'context_window': {'used_percentage': ctx_pct, 'context_window_size': ctx_size},
        'rate_limits': {
            'five_hour': {'used_percentage': five, 'resets_at': five_resets},
            'seven_day': {'used_percentage': week, 'resets_at': week_resets},
        },
        'model':   {'display_name': model_raw, 'id': (d.get('model') or {}).get('id', '?')},
        'version': version,
    }
    out = os.path.join(tempfile.gettempdir(), 'claude-statusline-data.json')
    with open(out, 'w') as f:
        json.dump(payload, f)
except Exception as e:
    sys.stderr.write(f'statusline write failed: {e}\n')
