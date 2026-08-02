#!/usr/bin/env python3
"""loop-health.py - measure the improvement loop as set differences over logs.

The loop's health is NOT the number of rules you have. It is whether rules
reach anything, whether guards still fire, and whether the same lesson keeps
arriving under a new name.

Every number here is a set difference over recorded events. Nothing is
reconciled narratively, because a narrative can always be made to come out
even. A metric that cannot be computed is reported as UNKNOWN and treated as
a defect in the instrumentation, never as a zero.

Expected inputs, all plain append-only text logs, all optional:
  rules dir        one file per rule (e.g. memory/feedback/*.md)
  reference log    lines "<iso-date> <session-id> <path>"  - a rule file was read
  guard log        lines "<iso-date> <guard-name> <verdict>" - a guard ran
  capture log      lines "<iso-date> <rule-file> <topic-tag>" - a rule was written

Usage:
  python3 tools/loop-health.py
  python3 tools/loop-health.py --rules memory/feedback --days 90 --json
"""

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

UNKNOWN = "UNKNOWN"


def parse_log(path, fields):
    """Read an append-only whitespace-delimited log. Returns [] if absent.

    Absent and empty are DIFFERENT and the caller must be able to tell:
    absent means never instrumented, empty means instrumented and silent.
    """
    if not path or not os.path.exists(path):
        return None
    rows = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            parts = line.split(None, len(fields) - 1)
            if len(parts) < len(fields):
                continue
            rows.append(dict(zip(fields, (p.strip() for p in parts))))
    return rows


def within(rows, days):
    if rows is None:
        return None
    cutoff = date.today() - timedelta(days=days)
    kept = []
    for r in rows:
        try:
            when = datetime.fromisoformat(r["date"][:10]).date()
        except ValueError:
            continue
        if when >= cutoff:
            kept.append(r)
    return kept


def topic_of(filename):
    """Crude topic key from a rule filename. Deliberately lossy.

    Matching on the full name misses every repeat, because the second
    occurrence of a lesson almost never arrives with the same wording.
    Stopwords are dropped so 'feedback_commit_explicit_paths' and
    'feedback_always_name_paths_when_committing' can collide.
    """
    stem = re.sub(r"\.(md|txt)$", "", os.path.basename(filename))
    stem = re.sub(r"^(feedback|rule|lesson)[_-]", "", stem)
    stop = {"the", "a", "an", "and", "or", "to", "of", "in", "on", "for",
            "is", "be", "not", "no", "never", "always", "when", "must"}
    words = [w for w in re.split(r"[_\-\s]+", stem.lower()) if w and w not in stop]
    return frozenset(words)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rules", default="memory/feedback",
                    help="directory of rule files, one rule per file")
    ap.add_argument("--reference-log", default="logs/rule-references.log")
    ap.add_argument("--guard-log", default="logs/guard-fires.log")
    ap.add_argument("--capture-log", default="logs/rule-captures.log")
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    report = {"window_days": args.days, "generated": date.today().isoformat()}
    defects = []

    # ---- Inventory -------------------------------------------------------
    if os.path.isdir(args.rules):
        rule_files = sorted(f for f in os.listdir(args.rules)
                            if f.endswith((".md", ".txt")))
        report["rule_count"] = len(rule_files)
    else:
        rule_files = []
        report["rule_count"] = UNKNOWN
        defects.append(f"rules directory not found: {args.rules}")

    refs = within(parse_log(args.reference_log, ["date", "session", "path"]), args.days)
    fires = within(parse_log(args.guard_log, ["date", "guard", "verdict"]), args.days)
    caps = within(parse_log(args.capture_log, ["date", "rule", "topic"]), args.days)

    # ---- Difference 1: rules that reach nothing --------------------------
    if refs is None:
        report["unreferenced_rules"] = UNKNOWN
        defects.append("no reference log: cannot tell which rules are ever loaded")
    elif not refs:
        report["unreferenced_rules"] = UNKNOWN
        defects.append("reference log is EMPTY over the window - instrumentation "
                       "is silent, which is not the same as zero")
    else:
        seen = {os.path.basename(r["path"]) for r in refs}
        orphans = [f for f in rule_files if f not in seen]
        report["unreferenced_rules"] = orphans
        report["unreferenced_pct"] = (
            round(100 * len(orphans) / len(rule_files)) if rule_files else UNKNOWN)

    # ---- Difference 2: guards that never fire, and guards that always do --
    if fires is None:
        report["guard_fires"] = UNKNOWN
        defects.append("no guard log: cannot tell which guards are dead or noisy")
    elif not fires:
        report["guard_fires"] = UNKNOWN
        defects.append("guard log is EMPTY over the window - either nothing "
                       "triggered a guard, or guards stopped logging. Check which.")
    else:
        per_guard = Counter(r["guard"] for r in fires)
        blocks = Counter(r["guard"] for r in fires
                         if r["verdict"].lower() in ("block", "blocked", "deny"))
        report["guard_fires"] = dict(per_guard.most_common())
        # A guard whose fires are nearly all blocks, at high volume, has become
        # the normal state rather than an exception. That is a signal about
        # something upstream, not proof the guard is earning its place.
        report["guards_now_normal_state"] = [
            g for g, n in per_guard.items()
            if n >= 20 and blocks.get(g, 0) / n > 0.5]

    # ---- Difference 3: the same lesson arriving twice --------------------
    if caps is None:
        report["repeat_topics"] = UNKNOWN
        defects.append("no capture log: cannot measure repeat violations, which "
                       "is the loop's primary health signal")
    elif not caps:
        report["repeat_topics"] = UNKNOWN
        defects.append("capture log is EMPTY over the window - instrumentation "
                       "is silent, which is not the same as zero repeats")
    else:
        by_topic = defaultdict(list)
        for c in caps:
            by_topic[c["topic"]].append(c)
        explicit = {t: [c["rule"] for c in v] for t, v in by_topic.items() if len(v) > 1}

        # Filename-similarity fallback, for corpora with no topic tags.
        # Tested and it is weak: two rules about the same lesson worded
        # differently ("commit_explicit_paths" vs "name_paths_when_committing")
        # share one word and score 0.33, below the threshold. It catches near
        # duplicates only. The topic tag above is the real mechanism, and this
        # is here so an untagged corpus gets something rather than nothing.
        fuzzy = []
        keys = [(f, topic_of(f)) for f in rule_files]
        for i, (fa, ka) in enumerate(keys):
            for fb, kb in keys[i + 1:]:
                if len(ka) >= 2 and len(kb) >= 2:
                    overlap = len(ka & kb) / min(len(ka), len(kb))
                    if overlap >= 0.6:
                        fuzzy.append([fa, fb])

        report["repeat_topics_tagged"] = explicit
        report["repeat_topics_suspected"] = fuzzy
        # Trend is the actual signal. A count without a direction says nothing.
        halves = defaultdict(int)
        cutoff = date.today() - timedelta(days=args.days // 2)
        for t, v in by_topic.items():
            if len(v) < 2:
                continue
            dated = []
            for c in v:
                try:
                    when = datetime.fromisoformat(c["date"][:10]).date()
                except ValueError:
                    continue
                dated.append((when, c))
            if len(dated) < 2:
                continue
            dated.sort(key=lambda pair: pair[0])
            for when, c in dated[1:]:
                halves["recent" if when >= cutoff else "earlier"] += 1
        report["repeats_earlier_half"] = halves.get("earlier", 0)
        report["repeats_recent_half"] = halves.get("recent", 0)
        report["direction"] = (
            "improving" if halves.get("recent", 0) < halves.get("earlier", 0)
            else "flat or worsening" if halves else UNKNOWN)

    report["instrumentation_defects"] = defects

    # ---- Output ----------------------------------------------------------
    if args.json:
        print(json.dumps(report, indent=2, default=list))
        return 1 if defects else 0

    print(f"Loop health, last {args.days} days")
    print(f"  rules on disk ................ {report['rule_count']}")
    ur = report.get("unreferenced_rules")
    if ur == UNKNOWN:
        print("  never referenced ............. UNKNOWN (see defects)")
    else:
        print(f"  never referenced ............. {len(ur)} "
              f"({report.get('unreferenced_pct')}%)")
        for f in ur[:10]:
            print(f"      {f}")
        if len(ur) > 10:
            print(f"      ... and {len(ur) - 10} more")
    print(f"  repeats, earlier half ........ {report.get('repeats_earlier_half', UNKNOWN)}")
    print(f"  repeats, recent half ......... {report.get('repeats_recent_half', UNKNOWN)}")
    print(f"  direction .................... {report.get('direction', UNKNOWN)}")
    noisy = report.get("guards_now_normal_state") or []
    if noisy:
        print("  guards that have become the normal state:")
        for g in noisy:
            print(f"      {g}  (review what is upstream of it)")
    susp = report.get("repeat_topics_suspected") or []
    if susp and susp != UNKNOWN:
        print(f"  suspected duplicate rules .... {len(susp)}")
        for a, b in susp[:5]:
            print(f"      {a}  ~  {b}")

    if defects:
        print("\nINSTRUMENTATION DEFECTS - these are not zeros, they are gaps:")
        for d in defects:
            print(f"  - {d}")
        print("\nA metric that cannot be computed is a defect to fix, not a "
              "clean result. Do not report this run as healthy.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
