#!/usr/bin/env python3
"""PreToolUse (Bash): deny commands known to flood context unless their output is already limited.

A command matching a noisy pattern must pipe through head, tail, grep or wc, or redirect to a file.
Edit NOISY for your own habits. Fails open on any parse problem.
"""
import json
import re
import sys

NOISY = [r"\bgit\s+log\b(?!.*(-n\s*\d|--oneline|-\d))", r"\bfind\s+/", r"\bnpm\s+(ls|list)\b", r"\bpip\s+list\b", r"\bcat\s+\S*\.log\b"]
LIMITED = re.compile(r"\|\s*(head|tail|grep|wc)\b|>\s*\S+")


def main():
    try:
        d = json.load(sys.stdin)
        if d.get("tool_name") != "Bash":
            return 0
        cmd = (d.get("tool_input") or {}).get("command", "")
    except Exception:
        return 0
    if any(re.search(p, cmd) for p in NOISY) and not LIMITED.search(cmd):
        print("Blocked: this command can print a very large result. Limit it (| head -50, a count flag) or redirect to a file and read a section.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
