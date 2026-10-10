#!/usr/bin/env python3
"""PostToolUse (Edit|Write): after N direct edits in one session, nudge once toward delegation.

Observes only: emits additionalContext, never blocks. State is a per-session file in the temp dir
(seam EDIT_TRIPWIRE_STATE_DIR). Env EDIT_TRIPWIRE_N sets the threshold. Fails open.
"""
import json
import os
import re
import sys
import tempfile

N = int(os.environ.get("EDIT_TRIPWIRE_N", "8"))


def main():
    try:
        d = json.load(sys.stdin)
        if d.get("tool_name") not in ("Edit", "Write"):
            return 0
        sid = re.sub(r"[^A-Za-z0-9_-]", "_", str(d.get("session_id") or "nosession"))[:64]
        path = os.path.join(os.environ.get("EDIT_TRIPWIRE_STATE_DIR") or tempfile.gettempdir(), f"edit-tripwire-{sid}")
        n = int(open(path).read()) if os.path.exists(path) else 0
        n += 1
        with open(path, "w") as f:
            f.write(str(n))
    except Exception:
        return 0
    if n == N:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext":
              f"{N} edits made directly this session. If the remaining work is mechanical, hand it to one subagent with a precise brief."}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
