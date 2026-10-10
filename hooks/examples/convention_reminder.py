#!/usr/bin/env python3
"""PreToolUse (Read|Write|Edit): inject a one-line convention the first time a given file is touched.

Allows the call and adds additionalContext, once per file per session. Never blocks.
Edit REMINDERS to match your own file conventions. Fails open.
"""
import hashlib
import json
import os
import re
import sys
import tempfile

REMINDERS = {
    "BACKLOG.md": "BACKLOG.md: finished items move to HISTORY.md; no done markers here.",
    "CLAUDE.md": "CLAUDE.md: orientation and harm prevention only; detail belongs in a reference doc.",
}


def main():
    try:
        d = json.load(sys.stdin)
        if d.get("tool_name") not in ("Read", "Write", "Edit"):
            return 0
        fp = (d.get("tool_input") or {}).get("file_path", "")
        msg = REMINDERS.get(os.path.basename(fp))
        if not msg:
            return 0
        sid = re.sub(r"[^A-Za-z0-9_-]", "_", str(d.get("session_id") or "nosession"))[:64]
        key = hashlib.md5(fp.replace(os.sep, "/").lower().encode()).hexdigest()[:12]
        marker = os.path.join(os.environ.get("CONVENTION_REMINDER_STATE_DIR") or tempfile.gettempdir(), f"convention-{sid}-{key}")
        if os.path.exists(marker):
            return 0
        open(marker, "w").write("1")
    except Exception:
        return 0
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow", "additionalContext": msg}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
