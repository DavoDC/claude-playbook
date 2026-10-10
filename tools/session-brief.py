#!/usr/bin/env python3
"""Emit a byte-capped session-start orientation brief.

Instead of letting a session read a long task list and a long session history just to
orient, print a few lines: the first N open items from a task list and the latest M
session headings from a history file. Hard cap in BYTES (not lines), so a pathological
file cannot blow the budget. Wire it into a SessionStart hook; its stdout becomes
context.

Usage:
  session-brief.py [--root DIR] [--tasks FILE] [--history FILE] [--cap BYTES]
                   [--items N] [--sessions M] [--section HEADING]
  session-brief.py --selftest

Paths are relative to --root (default: current directory). A missing file yields
an empty section, never an error: a brief that crashes the session start is worse
than no brief.

Item format: a markdown list line that starts with a bold lead, e.g. `- **Fix the parser** details`.
--section limits item search to the lines under the first `## ` heading containing that text.
History format: lines starting with `## Session` are headings.
"""
import argparse
import os
import re
import sys
import tempfile

BOLD = re.compile(r"^(?:\d+\.|-)\s+\*\*(.+?)\*\*")


def read_lines(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().splitlines()
    except OSError:
        return []


def items(src, section, limit):
    pool = src
    if section:
        start = next((i for i, l in enumerate(src) if l.startswith("## ") and section in l), None)
        pool = []
        if start is not None:
            for l in src[start + 1:]:
                if l.startswith("## "):
                    break
                pool.append(l)
    return [m.group(1)[:90] for m in map(BOLD.match, pool) if m][:limit]


def build(root, tasks, history, cap, n_items, n_sessions, section):
    out = ["Brief (read source files only by section, with offset/limit):", f"Open items ({tasks}):"]
    out += [f"- {t}" for t in items(read_lines(os.path.join(root, tasks)), section, n_items)] or ["- (none found)"]
    heads = [l[3:].strip()[:80] for l in read_lines(os.path.join(root, history)) if l.startswith("## Session")][:n_sessions]
    out += [f"Recent sessions ({history}):"] + [f"- {h}" for h in heads]
    text = "\n".join(out) + "\n"
    return text.encode("utf-8")[:cap].decode("utf-8", "ignore")


def selftest():
    failures = []
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "tasks.md"), "w", encoding="utf-8") as f:
            f.write("## Later\n- **Not this one** x\n## Waiting\n" + "".join(f"- **Item {i}** detail\n" for i in range(9)))
        with open(os.path.join(d, "hist.md"), "w", encoding="utf-8") as f:
            f.write("".join(f"## Session {i} - day\nbody\n" for i in range(9, 0, -1)))
        out = build(d, "tasks.md", "hist.md", 1500, 5, 3, "Waiting")
        if "Item 0" not in out or "Item 5" in out:
            failures.append("did not take exactly the first 5 items of the section")
        if "Not this one" in out:
            failures.append("leaked an item from outside the section")
        if "Session 9" not in out or "Session 6" in out:
            failures.append("did not take exactly the newest 3 session headings")
        small = build(d, "tasks.md", "hist.md", 120, 5, 3, "Waiting")
        if len(small.encode("utf-8")) > 120:
            failures.append(f"cap violated: {len(small.encode('utf-8'))} bytes > 120")
        # POSITIVE CONTROL: a deliberately oversized brief with no cap applied MUST exceed the cap,
        # proving the size assertion above can fail.
        uncapped = build(d, "tasks.md", "hist.md", 10**6, 5, 3, "Waiting")
        if len(uncapped.encode("utf-8")) <= 120:
            failures.append("POSITIVE CONTROL: uncapped brief was not larger than the small cap")
        empty = build(d, "missing.md", "missing2.md", 1500, 5, 3, None)
        if "(none found)" not in empty:
            failures.append("missing files did not degrade to an empty section")
    for f in failures:
        print("FAIL:", f)
    print("selftest:", "FAIL" if failures else "PASS")
    return 1 if failures else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--tasks", default="pending-actions.md")
    ap.add_argument("--history", default="session-history.md")
    ap.add_argument("--cap", type=int, default=1500)
    ap.add_argument("--items", type=int, default=5)
    ap.add_argument("--sessions", type=int, default=3)
    ap.add_argument("--section", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    sys.stdout.write(build(a.root, a.tasks, a.history, a.cap, a.items, a.sessions, a.section))
    return 0


if __name__ == "__main__":
    sys.exit(main())
