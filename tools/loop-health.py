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

Exit codes (a wrapper script should branch on these, not just check nonzero):
  0  measured, no defects and no findings - nothing to do
  1  measured successfully, findings present - investigate the SYSTEM
  2  could not measure - an instrumentation defect - investigate the
     INSTRUMENT first; every other number this run produced is suspect
     until it is fixed. Every input-state classification (absent, empty,
     saturated, collapsed, misaligned) is an instrumentation defect and
     maps here, never to 1.

Note on 2: some CLI conventions (getopt, argparse itself) reserve exit code
2 for a usage error. This tool reuses it for a different reason - a broken
measurement source, not a bad invocation - because "could not measure" is a
fundamentally different failure from "result 1: unhealthy" and a caller
needs to be able to tell them apart from the exit code alone. If that
collision matters for your wrapper, check the JSON "instrumentation_defects"
field instead of relying only on the exit code.
"""

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

UNKNOWN = "UNKNOWN"

DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")

# Format-independent candidate scan: looks for a date-shaped token anywhere
# in roughly the first 20 characters of a line, regardless of punctuation
# around it or which column it landed in. Deliberately separate from the
# lenient row parser below - this is the strict cross-check that catches the
# lenient parser silently dropping rows it should have kept.
CANDIDATE_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
CANDIDATE_HEAD_CHARS = 20

# A collapse, not a drift, is what this guards against. A log with a mix of
# historical line shapes will legitimately fail to parse some fraction of
# its lines forever, and a tight floor fires on every such log until
# someone turns the check off. Losing half a log to an unrecognised format
# is still worth flagging as a defect; losing a handful of stray malformed
# lines is normal and must not trip this.
PARSE_YIELD_FLOOR = 0.5

# A plausible topic/rule token: short, no internal whitespace, no sentence
# punctuation. Real filenames ("feedback_x.md"), tags ("alpha"), and guard
# names ("noisy-guard") all satisfy this. A full log message or sentence
# fragment that landed in the wrong field because the columns shifted does
# not - that is exactly the shape a misaligned field produces, and exactly
# what the positional split() below cannot tell from a well-formed value on
# its own. Slash is allowed so path-like fields (a reference log's "path")
# pass too; anything with a colon, comma, bracket, quote or space fails.
TOKEN_RE = re.compile(r"^[\w./\-]{1,64}$")

# Same reasoning as PARSE_YIELD_FLOOR: a few misshapen rows in an otherwise
# normal log are not the signal. Most of the window failing the shape check
# is the signal - the log's column layout does not match what this tool
# expects, and clustering on it anyway produces a confident, wrong answer.
MISALIGNED_FLOOR = 0.5


def _field_shape_ok(value):
    """True if value is a plausible short token, not a shifted sentence."""
    return bool(value) and bool(TOKEN_RE.match(value))


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


def _row_date(row, date_key="date"):
    """Recover the date from a parsed row, tolerant of surrounding
    punctuation ("[2026-08-01]", "2026-08-01,") and of a shifted field
    order (a newly inserted column pushes the date into a field keyed by
    the wrong name).

    The primary lookup is the "date" key itself. Only if that fails do we
    fall back to scanning every other value in the row for a date-shaped
    token - and that fallback is gated on the REST of the row looking
    plausible (each other field passes the same short-token shape check
    used against misaligned rows elsewhere in this file). Without that
    gate, a misaligned row that happens to have a date-shaped value
    sitting in some other field gets "rescued" by this function even
    though every other field is garbage - which is precisely what let a
    misaligned capture log sail past every guard before this fix: the
    date always parsed, so the row always looked like a keeper.
    """
    primary = row.get(date_key, "")
    m = DATE_RE.search(primary)
    if m:
        try:
            return datetime.fromisoformat(m.group()).date()
        except ValueError:
            pass

    others = [v for k, v in row.items() if k != date_key]
    if not others or not all(_field_shape_ok(v) for v in others):
        return None
    for value in others:
        m = DATE_RE.search(value)
        if not m:
            continue
        try:
            return datetime.fromisoformat(m.group()).date()
        except ValueError:
            continue
    return None


def within(rows, days):
    if rows is None:
        return None
    cutoff = date.today() - timedelta(days=days)
    kept = []
    for r in rows:
        when = _row_date(r)
        if when is not None and when >= cutoff:
            kept.append(r)
    return kept


def count_window_candidates(path, days):
    """Strict, format-independent count of lines that LOOK like an in-window
    dated entry, computed straight from the raw file - never through
    parse_log/within. This is the cross-check: if the lenient parser above
    recovers far fewer in-window rows than this finds candidates, the gap is
    the parser failing to recognise a line shape, not the log being empty.
    """
    if not path or not os.path.exists(path):
        return 0
    cutoff = date.today() - timedelta(days=days)
    n = 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = CANDIDATE_DATE_RE.search(line[:CANDIDATE_HEAD_CHARS])
            if not m:
                continue
            try:
                when = datetime.fromisoformat(m.group()).date()
            except ValueError:
                continue
            if when >= cutoff:
                n += 1
    return n


def load_window(label, path, fields, days):
    """Load and classify one log's window: "absent" (never instrumented),
    "collapsed" (present, but the lenient parser recovered far fewer rows
    than the strict candidate count says are actually in-window - a parser
    defect, not a silence), "empty" (present, genuinely nothing to parse),
    or "ok". Collapsed and absent both return no usable rows, but they are
    different defects and must never be reported with the same message -
    collapsed is a misclassification to fix, not a silence to shrug at.
    """
    if not path or not os.path.exists(path):
        return "absent", None, None
    parsed = within(parse_log(path, fields), days)
    candidates = count_window_candidates(path, days)
    if candidates > 0 and len(parsed) < candidates * PARSE_YIELD_FLOOR:
        return "collapsed", None, (
            f"{label} log: only {len(parsed)} of {candidates} lines that look "
            "like in-window dated entries actually parsed - PARSE YIELD "
            "COLLAPSE, most likely a line shape the parser does not "
            "recognise yet, not a real result. Treating this metric as "
            "UNKNOWN, not empty.")
    if not parsed:
        return "empty", None, None
    return "ok", parsed, None


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
    # Two different lists for two different questions. "defects" is about the
    # INSTRUMENT: could this run measure at all. "findings" is about the
    # SYSTEM: given a successful measurement, is there a problem in it. They
    # drive different exit codes below because they need different human
    # responses - a broken instrument is urgent in a way an unhealthy-but-
    # measured system is not, since it silently invalidates every other
    # number this run produced.
    defects = []
    findings = []

    # ---- Inventory -------------------------------------------------------
    if os.path.isdir(args.rules):
        rule_files = sorted(f for f in os.listdir(args.rules)
                            if f.endswith((".md", ".txt")))
        report["rule_count"] = len(rule_files)
    else:
        rule_files = []
        report["rule_count"] = UNKNOWN
        defects.append(f"rules directory not found: {args.rules}")

    ref_status, refs, ref_defect = load_window(
        "reference", args.reference_log, ["date", "session", "path"], args.days)
    fire_status, fires, fire_defect = load_window(
        "guard", args.guard_log, ["date", "guard", "verdict"], args.days)
    cap_status, caps, cap_defect = load_window(
        "capture", args.capture_log, ["date", "rule", "topic"], args.days)

    # ---- Difference 1: rules that reach nothing --------------------------
    if ref_status == "absent":
        report["unreferenced_rules"] = UNKNOWN
        defects.append("no reference log: cannot tell which rules are ever loaded")
    elif ref_status == "collapsed":
        report["unreferenced_rules"] = UNKNOWN
        defects.append(ref_defect)
    elif ref_status == "empty":
        report["unreferenced_rules"] = UNKNOWN
        defects.append("reference log is EMPTY over the window - instrumentation "
                       "is silent, which is not the same as zero")
    else:
        seen = {os.path.basename(r["path"]) for r in refs}
        orphans = [f for f in rule_files if f not in seen]
        report["unreferenced_rules"] = orphans
        pct = (round(100 * len(orphans) / len(rule_files)) if rule_files else UNKNOWN)
        report["unreferenced_pct"] = pct
        # 0% and 100% are the two shapes a reference log tracking a
        # DIFFERENT population than the corpus produces - not confident
        # results. The intersection between logged references and the
        # corpus is what tells a reader which situation they are in, so
        # report it rather than the bare percentage.
        if pct in (0, 100):
            rule_set = set(rule_files)
            intersecting = sum(
                1 for r in refs if os.path.basename(r["path"]) in rule_set)
            defects.append(
                f"unreferenced_pct came out at a suspicious {pct}% - only "
                f"{intersecting} of {len(refs)} logged references land "
                "inside the corpus at all. Treat this as a broken "
                "instrument, not a confident result, until the log is "
                "shown to cover the corpus.")
        elif orphans:
            findings.append(
                f"{len(orphans)} rule(s) never referenced ({pct}%): "
                + ", ".join(orphans[:5])
                + (", ..." if len(orphans) > 5 else ""))

    # ---- Difference 2: guards that never fire, and guards that always do --
    if fire_status == "absent":
        report["guard_fires"] = UNKNOWN
        defects.append("no guard log: cannot tell which guards are dead or noisy")
    elif fire_status == "collapsed":
        report["guard_fires"] = UNKNOWN
        defects.append(fire_defect)
    elif fire_status == "empty":
        report["guard_fires"] = UNKNOWN
        defects.append("guard log is EMPTY over the window - either nothing "
                       "triggered a guard, or guards stopped logging. Check which.")
    elif fires and (sum(1 for r in fires if _field_shape_ok(r.get("guard", ""))
                        and _field_shape_ok(r.get("verdict", "")))
                    / len(fires) < MISALIGNED_FLOOR):
        # Found by the first run against a real guard log rather than by the
        # synthetic suite, which only ever feeds this branch clean
        # whitespace-delimited rows. A real log that was pipe- and
        # bracket-delimited rather than "<date> <guard> <verdict>" parsed with
        # no error and no defect: split(None, 2) handed the HH:MM:SS] time
        # fragment to the "guard" field, and the breakdown below duly reported
        # timestamps as guard names. A confident wrong answer, silently. The
        # capture-log branch below already had exactly this check; this branch
        # did not, and both parse the same way and are equally exposed.
        shaped_ok = sum(1 for r in fires if _field_shape_ok(r.get("guard", ""))
                        and _field_shape_ok(r.get("verdict", "")))
        report["guard_fires"] = UNKNOWN
        defects.append(
            f"guard log: only {shaped_ok} of {len(fires)} in-window rows have "
            "plausible guard/verdict fields (short, no internal whitespace, no "
            "sentence punctuation) - MISALIGNED FIELDS, most likely the log's "
            "column layout does not match what this tool expects, not a real "
            "guard-fire distribution. Treating this metric as UNKNOWN, not a "
            "clustering result.")
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
        if report["guards_now_normal_state"]:
            findings.append(
                "guard(s) now firing as the normal state, not an exception: "
                + ", ".join(report["guards_now_normal_state"]))

    # ---- Difference 3: the same lesson arriving twice --------------------
    if cap_status == "absent":
        report["repeat_topics"] = UNKNOWN
        defects.append("no capture log: cannot measure repeat violations, which "
                       "is the loop's primary health signal")
    elif cap_status == "collapsed":
        report["repeat_topics"] = UNKNOWN
        defects.append(cap_defect)
    elif cap_status == "empty":
        report["repeat_topics"] = UNKNOWN
        defects.append("capture log is EMPTY over the window - instrumentation "
                       "is silent, which is not the same as zero repeats")
    elif caps and (sum(1 for c in caps if _field_shape_ok(c.get("rule", ""))
                       and _field_shape_ok(c.get("topic", ""))) / len(caps)
                   < MISALIGNED_FLOOR):
        # A fifth input state, distinct from absent/empty/saturated/collapsed:
        # every one of those guards can pass - the log exists, is non-empty,
        # parses at the expected line-length, and every row's date recovers
        # cleanly - while the fields still hold something other than their
        # names say, because the column layout does not match what this tool
        # expects. Clustering on "topic" in that state produces a confident,
        # wrong answer (whole log messages reported as topics, "rule" holding
        # a bare timestamp) rather than an absence, so it needs its own name
        # rather than folding into one of the other four.
        shaped_ok = sum(1 for c in caps if _field_shape_ok(c.get("rule", ""))
                        and _field_shape_ok(c.get("topic", "")))
        report["repeat_topics"] = UNKNOWN
        defects.append(
            f"capture log: only {shaped_ok} of {len(caps)} in-window rows have "
            "plausible rule/topic fields (short, no internal whitespace, no "
            "sentence punctuation) - MISALIGNED FIELDS, most likely the "
            "log's column layout does not match what this tool expects, not "
            "a real topic distribution. Treating this metric as UNKNOWN, not "
            "a clustering result.")
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
        if explicit:
            findings.append(
                f"{len(explicit)} topic(s) captured more than once: "
                + ", ".join(list(explicit)[:5])
                + (", ..." if len(explicit) > 5 else ""))
        # Trend is the actual signal. A count without a direction says nothing.
        halves = defaultdict(int)
        cutoff = date.today() - timedelta(days=args.days // 2)
        for t, v in by_topic.items():
            if len(v) < 2:
                continue
            dated = []
            for c in v:
                when = _row_date(c)
                if when is None:
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
    report["findings"] = findings

    # ---- Exit code ---------------------------------------------------------
    # Three outcomes, three codes - see EXIT_CODE_HELP in --help. A defect
    # (could not measure) always wins over a finding (measured, unhealthy):
    # a broken instrument makes every other number in this report suspect,
    # including the findings, so it must not be reported as "just" a finding.
    exit_code = 2 if defects else (1 if findings else 0)

    # ---- Output ----------------------------------------------------------
    if args.json:
        print(json.dumps(report, indent=2, default=list))
        return exit_code

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

    if findings:
        print("\nFINDINGS - measured successfully, and there is a problem in "
              "the SYSTEM:")
        for f in findings:
            print(f"  - {f}")
        if defects:
            print("  (treat these as unverified until the instrument defects "
                  "below are fixed - a broken instrument makes every other "
                  "number in this report suspect)")

    if defects:
        print("\nINSTRUMENTATION DEFECTS - these are not zeros, they are gaps:")
        for d in defects:
            print(f"  - {d}")
        print("\nA metric that cannot be computed is a defect to fix, not a "
              "clean result. Do not report this run as healthy.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
