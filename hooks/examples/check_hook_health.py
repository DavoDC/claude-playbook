#!/usr/bin/env python3
"""Fail loudly if a Claude Code settings file has hooks that can hang or point nowhere.

Usage: check_hook_health.py [settings.json ...]   (default: .claude/settings.json and ~/.claude/settings.json)
Checks: every hook has a numeric timeout; no command uses bare python3 (on some platforms that name
is a stub that hangs); every script path named in a command (hooks and statusLine) exists; no
shell script that a command names calls bare python3 itself; disableAllHooks is off.
Exit 0 healthy, 1 problems or an unreadable settings file. `--selftest` runs built-in positive controls.
"""
import json
import re
import sys
import tempfile
from pathlib import Path

BARE = re.compile(r"(?<![\w/.-])python3(?=\s)")
PATH = re.compile(r"(?:[A-Za-z]:)?[/\\][^\s\"']+\.(?:sh|py)")


def check(path):
    problems = []
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return [f"{path}: cannot parse settings: {e}"]
    if d.get("disableAllHooks"):
        problems.append(f"{path}: disableAllHooks is true")
    cmds = []
    for event, groups in (d.get("hooks") or {}).items():
        for g in groups:
            for h in g.get("hooks", []):
                cmd = h.get("command", "")
                if not isinstance(h.get("timeout"), (int, float)):
                    problems.append(f"{path}: {event} hook has no numeric timeout: {cmd}")
                cmds.append((event, cmd))
    if isinstance(d.get("statusLine"), dict):
        cmds.append(("statusLine", d["statusLine"].get("command", "")))
    for event, cmd in cmds:
        if BARE.search(cmd):
            problems.append(f"{path}: {event} uses bare python3: {cmd}")
        for p in PATH.findall(cmd):
            if not Path(p).exists():
                problems.append(f"{path}: {event} points at a missing file: {p}")
            elif p.endswith(".sh"):
                for n, line in enumerate(Path(p).read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                    if BARE.search(line.replace("command -v python3", "")) and not line.lstrip().startswith("#"):
                        problems.append(f"{p}:{n}: bare python3 inside a script that {event} runs")
    return problems


def selftest():
    """Each defect must be reported, and a clean file must pass: a checker that cannot fail proves nothing."""
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        sh = root / "ok.sh"
        sh.write_text("#!/bin/sh\npython x.py\n", encoding="utf-8")
        badsh = root / "bad.sh"
        badsh.write_text("#!/bin/sh\n# python3 in a comment is fine\npython3 x.py\n", encoding="utf-8")
        hook = lambda cmd, **kw: {"hooks": {"Stop": [{"hooks": [dict(command=cmd, **kw)]}]}}
        sp = (root / "s").as_posix()
        cases = [
            ("clean", hook(f"sh {sh.as_posix()}", timeout=5), 0),
            ("no timeout", hook(f"sh {sh.as_posix()}"), 1),
            ("bare python3", hook("python3 x.py", timeout=5), 1),
            ("missing script", hook(f"sh {sp}/gone.sh", timeout=5), 1),
            ("script calls python3", hook(f"sh {badsh.as_posix()}", timeout=5), 1),
            ("statusLine missing script", {"statusLine": {"type": "command", "command": f"sh {sp}/gone.sh"}}, 1),
            ("disableAllHooks", {"disableAllHooks": True}, 1),
        ]
        for name, cfg, want in cases:
            f = root / "settings.json"
            f.write_text(json.dumps(cfg), encoding="utf-8")
            got = 1 if check(f) else 0
            assert got == want, f"{name}: got {got}, wanted {want}"
        (root / "settings.json").write_text("{not json", encoding="utf-8")
        assert check(root / "settings.json"), "unparseable settings must be a problem"
    print("selftest: PASS")


def main(argv):
    if argv == ["--selftest"]:
        selftest()
        return 0
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
