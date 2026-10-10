#!/usr/bin/env python3
"""Flag scratch entries that are past their delete-after condition or carry no marker at all.

A scratch folder is only temporary if something forces the question "is this still needed?".
Each entry declares a line `DELETE-AFTER: <condition>` in the first lines of its README.md (a
folder) or of the file itself (a loose file). This script reads those lines and lists:
  - a date YYYY-MM-DD: overdue on or after that date
  - free text: a script cannot judge it, so it is flagged only when nothing in the entry has
    changed for --max-age days (default 14), as "needs review"
  - no marker: flagged once it is --max-age days old
A folder with no README of its own whose children are folders is a group (for example one folder
per repo): its children are scanned instead. Prints nothing when nothing is flagged.

Why the marker is phrased as a test still to run: docs/12-workspace-repo.md.

Usage:
  scratch-overdue.py [--dir SCRATCH] [--today YYYY-MM-DD] [--max-age DAYS]
  scratch-overdue.py --selftest

--dir   The scratch folder to scan (default: $SCRATCH_DIR, else ./TEMP).
Exit codes: 0 nothing flagged, 1 something flagged (usable as a gate), 2 --dir is not a folder.
"""
import argparse
import datetime
import os
import re
import sys
import tempfile
from pathlib import Path

MARKER = re.compile(r"DELETE-AFTER:\s*(.*)")
DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})\b")
HEAD_LINES = 5


def newest_mtime(p):
    files = [p] if p.is_file() else [f for f in p.rglob("*") if f.is_file()]
    return max([f.stat().st_mtime for f in files] or [p.stat().st_mtime])


def condition(p):
    """The text after the first DELETE-AFTER: in the entry's head, or None."""
    src = p / "README.md" if p.is_dir() else p
    try:
        head = src.read_text(encoding="utf-8", errors="replace").splitlines()[:HEAD_LINES]
    except OSError:
        return None
    for line in head:
        m = MARKER.search(line)
        if m:
            return m.group(1).strip()
    return None


def entries(scratch):
    out = []
    for p in sorted(scratch.iterdir()):
        if p.name.startswith("."):
            continue
        if p.is_dir() and not (p / "README.md").exists() and any(c.is_dir() for c in p.iterdir()):
            out.extend(sorted(c for c in p.iterdir() if not c.name.startswith(".")))
        else:
            out.append(p)
    return out


def overdue(scratch, today, max_age=14):
    flagged = []
    for p in entries(scratch):
        name = p.relative_to(scratch).as_posix()
        cond = condition(p)
        age = (today - datetime.date.fromtimestamp(newest_mtime(p))).days
        m = DATE.match(cond) if cond else None
        if m:
            if today >= datetime.date.fromisoformat(m.group(1)):
                flagged.append((name, "DELETE-AFTER date %s reached" % m.group(1)))
        elif age >= max_age:
            why = "free-text DELETE-AFTER, needs review" if cond else "no DELETE-AFTER marker"
            flagged.append((name, "%s, untouched %d days" % (why, age)))
    return flagged


def selftest():
    with tempfile.TemporaryDirectory() as d:
        scratch = Path(d)
        today = datetime.date(2030, 6, 15)
        old = datetime.datetime(2030, 5, 1).timestamp()
        fresh = datetime.datetime(2030, 6, 14).timestamp()

        def make(rel, text, aged=False):
            p = scratch / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
            stamp = old if aged else fresh
            os.utime(p, (stamp, stamp))

        make("due/README.md", "DELETE-AFTER: 2030-06-01\n")
        make("future/README.md", "DELETE-AFTER: 2030-12-31\n", aged=True)
        make("text-old/README.md", "x\nDELETE-AFTER: the rotation check passes\n", aged=True)
        make("text-new/README.md", "DELETE-AFTER: the rotation check passes\n")
        make("bare-old/notes.md", "no marker\n", aged=True)
        make("loose-old.txt", "DELETE-AFTER: still being tested\n", aged=True)
        make("group/work-a/README.md", "DELETE-AFTER: 2030-01-01\n")
        got = dict(overdue(scratch, today))
        want = {"due", "text-old", "bare-old", "loose-old.txt", "group/work-a"}
        assert set(got) == want, "flagged %r, wanted %r" % (sorted(got), sorted(want))
        assert "needs review" in got["text-old"] and "no DELETE-AFTER" in got["bare-old"], got
        assert overdue(scratch, today, max_age=1000) == [
            ("due", got["due"]), ("group/work-a", got["group/work-a"])], "max-age must not touch dated entries"
    print("selftest: PASS")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dir", default=os.environ.get("SCRATCH_DIR") or "TEMP")
    ap.add_argument("--today")
    ap.add_argument("--max-age", type=int, default=14)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        selftest()
        return 0
    scratch = Path(a.dir)
    if not scratch.is_dir():
        print("scratch folder not found: %s" % scratch, file=sys.stderr)
        return 2
    today = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()
    flagged = overdue(scratch, today, a.max_age)
    for name, why in flagged:
        print("%s/%s: %s" % (scratch.name, name, why))
    return 1 if flagged else 0


if __name__ == "__main__":
    sys.exit(main())
