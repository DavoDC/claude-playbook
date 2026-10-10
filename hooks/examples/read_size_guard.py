#!/usr/bin/env python3
"""PreToolUse (Read): deny a whole-file read of a large file; ask for offset/limit instead.

Env READ_GUARD_MAX_BYTES overrides the default ceiling. Fails open on any parse problem.
"""
import json
import os
import sys

MAX = int(os.environ.get("READ_GUARD_MAX_BYTES", "60000"))


def main():
    try:
        d = json.load(sys.stdin)
        if d.get("tool_name") != "Read":
            return 0
        ti = d.get("tool_input") or {}
        if ti.get("offset") is not None or ti.get("limit") is not None:
            return 0
        size = os.path.getsize(ti.get("file_path", ""))
    except Exception:
        return 0
    if size > MAX:
        print(f"Blocked: file is {size} bytes (ceiling {MAX}). Re-read a section with offset and limit, or search it.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
