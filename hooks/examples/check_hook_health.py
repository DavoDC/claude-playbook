#!/usr/bin/env python3
"""Fail loudly if a Claude Code settings file has hooks that can hang or point nowhere.

Usage: check_hook_health.py [settings.json ...]   (default: .claude/settings.json and ~/.claude/settings.json)
Checks: every hook has a numeric timeout; no command uses bare python3 (on some platforms that name
is a stub that hangs); every script path named in a command exists; disableAllHooks is off.
Exit 0 healthy, 1 problems.
"""
import json
import re
import sys
from pathlib import Path

BARE = re.compile(r"(?<![\w/.-])python3(?=\s)")
PATH = re.compile(r"(?:[A-Za-z]:)?[/\\][^\s\"']+\.(?:sh|py)")


def check(path):
    problems = []
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    if d.get("disableAllHooks"):
        problems.append(f"{path}: disableAllHooks is true")
    for event, groups in (d.get("hooks") or {}).items():
        for g in groups:
            for h in g.get("hooks", []):
                cmd = h.get("command", "")
                if not isinstance(h.get("timeout"), (int, float)):
                    problems.append(f"{path}: {event} hook has no numeric timeout: {cmd}")
                if BARE.search(cmd):
                    problems.append(f"{path}: {event} uses bare python3: {cmd}")
                for p in PATH.findall(cmd):
                    if not Path(p).exists():
                        problems.append(f"{path}: {event} points at a missing file: {p}")
    return problems


def main(argv):
    files = argv or [".claude/settings.json", str(Path.home() / ".claude" / "settings.json")]
    problems = []
    for f in files:
        if Path(f).exists():
            problems += check(f)
    if problems:
        print("HOOK HEALTH: FAIL")
        print("\n".join(problems))
        return 1
    print("HOOK HEALTH: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
