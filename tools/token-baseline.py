#!/usr/bin/env python3
"""Token baseline: measure context cost from Claude Code transcripts (read-only).

Reads the .jsonl session transcripts Claude Code writes for a project and reports
how much context each turn carried: the median first-turn size (what every session
pays before you type anything), the average per turn, compaction count, oversized
shell results, which tools return the most bytes, and which files get read most.

Usage:
  token-baseline.py --dir <transcript-dir> [--sessions N] [--json]
  token-baseline.py --dir <transcript-dir> --check [--ceilings FILE]
  token-baseline.py --dir <transcript-dir> --ratchet [--ceilings FILE]
  token-baseline.py --dir <transcript-dir> --append [--metrics FILE]
  token-baseline.py --selftest

--dir     Folder of session .jsonl files. Default: derived from the current directory
          (~/.claude/projects/<cwd with every non-alphanumeric character as '-'>).
          Verify it exists on your machine; the naming is an observed convention, not
          a documented one.
--check   Exit 1 if a measured value exceeds its ceiling in the ceilings file.
          Silent on pass, verbose on fail.
--ratchet Lower ceilings to the current measurement (plus --margin percent headroom)
          where that is lower. Ceilings only ever move down; a regression is fixed,
          never absorbed by raising the number.
--append  Append one dated JSON line to the metrics file, to chart the trend.
"""
import argparse
import collections
import datetime
import glob
import json
import os
import re
import statistics
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CEILINGS = os.path.join(HERE, "token-ceilings.example.json")
DEFAULT_METRICS = "token-baseline.jsonl"
HOOK_ATTACH = ("hook_additional_context", "hook_system_message")
RATCHET_KEYS = ("first_turn_median", "avg_ctx_per_turn")


def default_dir():
    mangled = re.sub(r"[^A-Za-z0-9]", "-", os.getcwd())
    return os.path.join(os.path.expanduser("~"), ".claude", "projects", mangled)


def _lines(path):
    with open(path, encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            try:
                yield json.loads(line)
            except Exception:
                continue


def _ctx(usage):
    return ((usage.get("input_tokens") or 0) + (usage.get("cache_read_input_tokens") or 0)
            + (usage.get("cache_creation_input_tokens") or 0))


def _subagent_first(files):
    out = []
    for f in files:
        sub = os.path.join(os.path.splitext(f)[0], "subagents")
        for sf in glob.glob(os.path.join(sub, "*.jsonl")):
            for o in _lines(sf):
                if o.get("type") == "assistant":
                    t = _ctx((o.get("message") or {}).get("usage") or {})
                    if t:
                        out.append(t)
                        break
    return out


def measure(directory, sessions):
    files = sorted(glob.glob(os.path.join(directory, "*.jsonl")), key=os.path.getmtime)[-sessions:]
    tool_bytes, tool_n = collections.Counter(), collections.Counter()
    read_files, hook_ctx, hook_n = collections.Counter(), collections.Counter(), collections.Counter()
    agent_models = collections.Counter()
    first_ctx, turns, total, compacts, big_bash = [], 0, 0, 0, 0
    for f in files:
        first = None
        id2tool = {}
        for o in _lines(f):
            if o.get("isCompactSummary") or (o.get("type") == "system" and o.get("subtype") == "compact_boundary"):
                compacts += 1
            m = o.get("message") or {}
            content = m.get("content") if isinstance(m.get("content"), list) else []
            if o.get("type") == "assistant":
                tot = _ctx(m.get("usage") or {})
                if tot:
                    turns += 1
                    total += tot
                    if first is None:
                        first = tot
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "tool_use":
                        inp = c.get("input") or {}
                        id2tool[c.get("id")] = (c.get("name"), inp.get("file_path", ""))
                        if c.get("name") in ("Agent", "Task"):
                            agent_models[inp.get("model", "MISSING")] += 1
            if o.get("type") == "attachment":
                a = o.get("attachment") or {}
                if a.get("type") in HOOK_ATTACH:
                    body = a.get("content") or a.get("additionalContext") or ""
                    if not isinstance(body, str):
                        body = json.dumps(body)
                    if body.strip():
                        k = a.get("hookName") or a.get("type")
                        hook_ctx[k] += len(body)
                        hook_n[k] += 1
            if o.get("type") == "user":
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "tool_result":
                        nm, fp = id2tool.get(c.get("tool_use_id"), ("?", ""))
                        s = len(json.dumps(c.get("content")))
                        tool_bytes[nm] += s
                        tool_n[nm] += 1
                        if nm == "Read":
                            read_files[os.path.basename(fp)] += s
                        if nm in ("Bash", "PowerShell") and s > 8000:
                            big_bash += 1
        if first:
            first_ctx.append(first)
    sub = _subagent_first(files)
    n = len(files)
    return {
        "sessions": n,
        "turns": turns,
        "avg_ctx_per_turn": total // max(turns, 1),
        "first_turn_median": int(statistics.median(first_ctx)) if first_ctx else 0,
        "compactions": compacts,
        "compactions_per_session": round(compacts / max(n, 1), 2),
        "big_bash_results_over_8kb": big_bash,
        "tool_result_bytes": dict(tool_bytes.most_common(12)),
        "tool_result_calls": {k: tool_n[k] for k in tool_bytes},
        "top_read_files": dict(read_files.most_common(10)),
        "hook_context_bytes": {k: [v, hook_n[k]] for k, v in hook_ctx.most_common(10)},
        "agent_models": dict(agent_models),
        "subagent_first_turn_median": int(statistics.median(sub)) if sub else 0,
        "subagent_count": len(sub),
    }


def check(result, ceilings_path):
    with open(ceilings_path, encoding="utf-8") as fh:
        ceilings = json.load(fh)
    fails = []
    for key, limit in ceilings.items():
        if key.startswith("_"):
            continue
        val = result.get(key)
        if isinstance(val, (int, float)) and val > limit:
            fails.append(f"{key}={val} exceeds ceiling {limit}")
    return fails


def ratchet(result, ceilings_path, margin_pct):
    """Lower ceilings toward the measurement. Never raises one. Returns the changes."""
    with open(ceilings_path, encoding="utf-8") as fh:
        ceilings = json.load(fh)
    changes = []
    for key in RATCHET_KEYS:
        val = result.get(key)
        if key in ceilings and isinstance(val, (int, float)) and val > 0:
            proposed = int(val * (1 + margin_pct / 100.0))
            if proposed < ceilings[key]:
                changes.append(f"{key}: {ceilings[key]} -> {proposed}")
                ceilings[key] = proposed
    if changes:
        with open(ceilings_path, "w", encoding="utf-8") as fh:
            json.dump(ceilings, fh, indent=2)
            fh.write("\n")
    return changes


def _synthetic_transcript(path, first_tokens, later_tokens):
    rows = []
    for i, t in enumerate([first_tokens] + later_tokens):
        rows.append({"type": "assistant", "message": {"usage": {"input_tokens": t}, "content": []}})
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


def selftest():
    """Synthetic transcripts, no real data. Includes a positive control that MUST fail."""
    failures = []
    with tempfile.TemporaryDirectory() as d:
        _synthetic_transcript(os.path.join(d, "a.jsonl"), 40000, [60000, 80000])
        _synthetic_transcript(os.path.join(d, "b.jsonl"), 50000, [70000])
        r = measure(d, 10)
        if r["sessions"] != 2 or r["turns"] != 5:
            failures.append(f"measure counted sessions={r['sessions']} turns={r['turns']}, expected 2 and 5")
        if r["first_turn_median"] != 45000:
            failures.append(f"first_turn_median={r['first_turn_median']}, expected 45000")
        if r["avg_ctx_per_turn"] != 60000:
            failures.append(f"avg_ctx_per_turn={r['avg_ctx_per_turn']}, expected 60000")
        cpath = os.path.join(d, "ceilings.json")
        with open(cpath, "w", encoding="utf-8") as fh:
            json.dump({"first_turn_median": 50000, "avg_ctx_per_turn": 100000}, fh)
        if check(r, cpath):
            failures.append("check failed on a measurement under its ceilings")
        # POSITIVE CONTROL: a ceiling below the measurement MUST be reported. If this
        # control ever passes silently, check() has stopped checking.
        with open(cpath, "w", encoding="utf-8") as fh:
            json.dump({"first_turn_median": 1000}, fh)
        if not check(r, cpath):
            failures.append("POSITIVE CONTROL: a ceiling of 1000 against 45000 was not flagged")
        # Ratchet moves down, never up.
        with open(cpath, "w", encoding="utf-8") as fh:
            json.dump({"first_turn_median": 50000, "avg_ctx_per_turn": 1000}, fh)
        ratchet(r, cpath, 5)
        with open(cpath, encoding="utf-8") as fh:
            after = json.load(fh)
        if after["first_turn_median"] != 47250:
            failures.append(f"ratchet set first_turn_median={after['first_turn_median']}, expected 47250")
        if after["avg_ctx_per_turn"] != 1000:
            failures.append("ratchet raised a ceiling")
    for f in failures:
        print("FAIL:", f)
    print("selftest:", "FAIL" if failures else "PASS")
    return 1 if failures else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sessions", type=int, default=40)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--ratchet", action="store_true")
    ap.add_argument("--margin", type=float, default=5.0, help="percent headroom kept by --ratchet")
    ap.add_argument("--append", action="store_true")
    ap.add_argument("--dir", default=None)
    ap.add_argument("--ceilings", default=DEFAULT_CEILINGS)
    ap.add_argument("--metrics", default=DEFAULT_METRICS)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    directory = args.dir or default_dir()
    if not os.path.isdir(directory):
        print(f"transcript directory not found: {directory} (pass --dir)", file=sys.stderr)
        return 2
    t0 = time.time()
    r = measure(directory, args.sessions)
    if r["sessions"] == 0:
        print(f"no .jsonl transcripts in {directory}", file=sys.stderr)
        return 2
    if args.append:
        line = dict(date=datetime.date.today().isoformat(), **{k: r[k] for k in (
            "sessions", "turns", "avg_ctx_per_turn", "first_turn_median", "compactions",
            "big_bash_results_over_8kb", "agent_models", "subagent_first_turn_median")})
        with open(args.metrics, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(line) + "\n")
    if args.ratchet:
        for c in ratchet(r, args.ceilings, args.margin) or ["no ceiling lowered"]:
            print("ratchet:", c)
    fails = check(r, args.ceilings) if args.check else []
    if args.json:
        print(json.dumps(r, indent=2))
    elif not (args.check and not fails) and not args.ratchet:
        for k, v in r.items():
            print(f"{k}: {v}")
    for f in fails:
        print("FAIL:", f)
    print(f"elapsed {time.time() - t0:.1f}s", file=sys.stderr)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
