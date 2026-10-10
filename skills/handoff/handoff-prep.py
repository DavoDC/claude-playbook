#!/usr/bin/env python3
"""handoff-prep.py - collect the MECHANICAL half of a session handoff prompt.

A handoff prompt (the thing you paste into a fresh session so it can continue
your work) must carry eleven things. Six are readable straight off disk: what is
already done, mid-flight state (branch, dirty and staged files, worktrees), live
constraints, which log rows exist, where prior work lives, and the issue keys in
play. This prints those six. The other five need judgment and stay with the
model.

The split exists because a fact recalled from conversation is a claim, while a
fact read off disk at handoff time is not. The expensive version of that failure
is real: a handoff once instructed two comments that had already been posted the
day before, and following it literally would have duplicated both.

CONFIGURE ME: the CONFIG block below is the only part that is installation
specific. Everything it names is optional - a missing path degrades to a skipped
section rather than an error, so the script is useful before it is tuned.

Usage:
    python3 handoff-prep.py            # human-readable block
    python3 handoff-prep.py --json     # same data, machine form
"""
import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

# ----------------------------- CONFIG -----------------------------
# Where scratch handoff files live, relative to the repo root.
TEMP_DIRNAME = "TEMP"

# Where per-day work logs live, relative to the repo root, named YYYY-MM-DD.md.
# Set to None if this workspace has no daily log.
DAILY_LOG_DIRNAME = None

# Extra repos to report on, as paths relative to the repo root's PARENT.
# Leave empty to report on the current repo alone.
SIBLING_REPOS = []

# Optional command printing budget/context/session status. None to skip.
STATUS_COMMAND = None

# Issue-key shapes to extract, e.g. r"\b(?:PROJ|OPS)-\d+\b". None to skip.
ISSUE_KEY_PATTERN = None
# --------------------------- END CONFIG ---------------------------


def repo_root():
    """The git root of wherever this is run from, falling back to cwd."""
    try:
        r = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and r.stdout.strip():
            return Path(r.stdout.strip())
    except Exception:
        pass
    return Path.cwd()


ROOT = repo_root()
TICKET_RE = re.compile(ISSUE_KEY_PATTERN) if ISSUE_KEY_PATTERN else None
DELETE_AFTER_RE = re.compile(r"DELETE[- ]AFTER:\s*(.+)", re.IGNORECASE)
# 6h48m, 2h, and the sub-hour 45m form. Requiring an "h" silently drops every
# under-an-hour row from the "already done" list.
DURATION_RE = re.compile(r"\b\d+h(?:\d+m)?\b|\b\d+m\b")


def run(cmd, cwd=None):
    """Run a command, returning stripped stdout or '' - never raising."""
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=20)
        return r.stdout.strip()
    except Exception:
        return ""


def todays_log():
    if not DAILY_LOG_DIRNAME:
        return None, None
    path = ROOT / DAILY_LOG_DIRNAME / f"{datetime.date.today().isoformat()}.md"
    if not path.exists():
        return path, None
    return path, path.read_text(encoding="utf-8", errors="replace").splitlines()


def collect_log(lines):
    """Work rows and issue keys from today's log. Rows carry a duration."""
    if lines is None:
        return {"rows": [], "tickets": [], "eod_line": ""}
    rows, tickets, eod = [], [], ""
    for ln in lines:
        s = ln.strip()
        if DURATION_RE.search(s) and s.startswith(("|", "-", "*")):
            rows.append(s)
        if re.search(r"EOD|Finish", s, re.IGNORECASE) and ":" in s and not eod:
            eod = s
        if TICKET_RE:
            for t in TICKET_RE.findall(s):
                if t not in tickets:
                    tickets.append(t)
    return {"rows": rows, "tickets": tickets, "eod_line": eod}


def collect_repos():
    """Branch, dirty count, staged files and worktrees, for repos not clean-on-main.

    A clean repo on its default branch carries no handoff information, so
    reporting it is noise. Anything dirty, staged, ahead, or on a topic branch is
    exactly the mid-flight state the receiving session cannot otherwise see.
    """
    targets = [("(this repo)", ROOT)] + [(r, ROOT.parent / r) for r in SIBLING_REPOS]
    out = []
    for label, p in targets:
        if not (p / ".git").exists():
            continue
        branch = run(["git", "-C", str(p), "branch", "--show-current"])
        dirty = [l for l in run(["git", "-C", str(p), "status", "--short"]).splitlines() if l.strip()]
        staged = [l for l in dirty if l[:1] not in (" ", "?")]
        ahead = run(["git", "-C", str(p), "rev-list", "--count", "@{upstream}..HEAD"])
        # Reported verbatim, never resolved: worktrees are often registered with
        # relative paths that resolve to nothing from where this runs, so a
        # computed absolute path would be a fabricated one.
        wt = [" ".join(l.split()[:1] + l.split()[2:])
              for l in run(["git", "-C", str(p), "worktree", "list"]).splitlines()[1:] if l.split()]
        if not (dirty or wt or branch not in ("main", "master") or (ahead and ahead != "0")):
            continue
        out.append({
            "repo": label, "branch": branch, "dirty_count": len(dirty),
            # git status --short emits two status columns then a space, but a
            # leading-space form arrives with one. Slicing a fixed width eats
            # the first character of the path.
            "staged": [l[2:].strip() for l in staged][:15],
            "ahead": ahead or "unknown (no upstream)",
            "worktrees": wt,
            "last_commit": run(["git", "-C", str(p), "log", "-1", "--format=%h %s"]),
        })
    return out


def collect_temp():
    """Scratch files with their DELETE-AFTER condition, so nothing dies unnoticed."""
    d = ROOT / TEMP_DIRNAME
    if not d.is_dir():
        return []
    out = []
    for f in sorted(d.iterdir()):
        if f.name.startswith(".") or f.name == "desktop.ini":
            continue
        cond = ""
        if f.is_file() and f.suffix == ".md":
            try:
                m = DELETE_AFTER_RE.search(f.read_text(encoding="utf-8", errors="replace")[:2000])
                cond = m.group(1).strip() if m else "MISSING - every scratch file needs one"
            except Exception:
                cond = "unreadable"
        out.append({"name": f.name, "is_dir": f.is_dir(), "delete_after": cond})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    log_path, lines = todays_log()
    data = {
        "generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "root": str(ROOT),
        "daily_log": str(log_path) if log_path else None,
        "daily_log_exists": lines is not None,
        "log": collect_log(lines),
        "repos": collect_repos(),
        "temp": collect_temp(),
        "status": run(STATUS_COMMAND, cwd=str(ROOT)) if STATUS_COMMAND else "",
    }

    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    p = print
    p(f"=== HANDOFF PREP  {data['generated']}  root={data['root']} ===")
    if data["status"]:
        p("")
        p("-- Live constraints (item 6) --")
        p(data["status"])
    if DAILY_LOG_DIRNAME:
        p("")
        p(f"-- Work log (items 3, 7): {data['daily_log']} --")
        if not data["daily_log_exists"]:
            p("  Does not exist yet. Say so in the prompt.")
        else:
            p(f"  {len(data['log']['rows'])} row(s) written - the new session APPENDS, never duplicates:")
            for r in data["log"]["rows"][-12:]:
                p(f"    {r}")
        if TICKET_RE:
            tix = data["log"]["tickets"]
            p("")
            p("-- Issue keys in play (item 11) --")
            p("  " + (", ".join(tix) if tix else "none found"))
            p("  STAMP EACH ONE: re-read it live before writing any instruction about it.")
    p("")
    p("-- Mid-flight repo state (item 5) --")
    if not data["repos"]:
        p("  Clean and on the default branch. Nothing mid-flight.")
    for r in data["repos"]:
        p(f"  {r['repo']}: branch={r['branch']} dirty={r['dirty_count']} ahead={r['ahead']}")
        p(f"    last commit: {r['last_commit']}")
        if r["staged"]:
            p(f"    STAGED but uncommitted: {', '.join(r['staged'])}")
        for w in r["worktrees"]:
            p(f"    worktree: {w}")
    p("")
    p(f"-- {TEMP_DIRNAME}/, where prior work lives (item 2) --")
    if not data["temp"]:
        p("  empty")
    for t in data["temp"]:
        p(f"  {t['name']} ({'dir' if t['is_dir'] else 'file'}) DELETE-AFTER: {t['delete_after'] or 'n/a'}")
    p("")
    p("-- Still yours to write, and no script can (items 1, 4, 8, 9, 10) --")
    p("  1. The single task as an OUTCOME, not an area.")
    p("  4. What is deliberately OUT of scope, with the reason.")
    p("  8. A last-verified stamp on every outward-facing instruction.")
    p("  9. The exact filters behind any search the plan depends on.")
    p("  10. What the previous session learned, so the next prompt is better.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
