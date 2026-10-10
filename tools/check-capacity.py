#!/usr/bin/env python3
"""Capacity check for files that load into every session (CLAUDE.md, rules, memory index).

A limit on one file misses the case where each file sits under its own cap while the sum keeps
growing, so this checks both: per-file limits (bytes and/or lines, soft and hard) and group
budgets (the combined bytes of a list of files). Run it BEFORE editing a limited file so you can
size one consolidated edit to fit, instead of editing, being told you are over, and trimming again.

Usage:
  check-capacity.py [--config FILE] [--root DIR] [PATH ...]
  check-capacity.py --selftest

With no PATH every configured file and group is checked. With PATH only that file is reported
(plus any group it belongs to). A path with no configured limit prints NO LIMIT and exits 0.
Config default: config/capacity.json next to this repo's tools/ folder (copy
config/capacity.example.json); paths in it are relative to --root (default: current directory),
and a leading ~ is expanded for files that live in your home directory.

Exit codes: 0 all within hard limits (soft overruns print WARN), 1 a hard limit is exceeded,
2 config error. Silent-ish by design: one line per file or group.
"""
import argparse
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG = os.path.join(HERE, "..", "config", "capacity.json")


class ConfigError(Exception):
    pass


def load_config(path):
    try:
        with open(path, encoding="utf-8") as fh:
            cfg = json.load(fh)
    except (OSError, ValueError) as exc:
        raise ConfigError("cannot read config %s: %s" % (path, exc))
    if not isinstance(cfg.get("files", {}), dict) or not isinstance(cfg.get("groups", []), list):
        raise ConfigError("config needs 'files' (object) and/or 'groups' (list)")
    for name, lim in cfg.get("files", {}).items():
        _check_limits(name, lim, ("soft_bytes", "hard_bytes", "max_lines"))
    for grp in cfg.get("groups", []):
        if not grp.get("name") or not isinstance(grp.get("files"), list):
            raise ConfigError("every group needs a name and a files list")
        _check_limits(grp["name"], grp, ("soft_bytes", "hard_bytes"))
    return cfg


def _check_limits(name, lim, keys):
    if not any(k in lim for k in keys):
        raise ConfigError("%s: set at least one of %s" % (name, ", ".join(keys)))
    for k in keys:
        if k in lim and (not isinstance(lim[k], int) or lim[k] <= 0):
            raise ConfigError("%s: %s must be a positive integer" % (name, k))


def measure(path):
    """(bytes, lines) or None when the file does not exist."""
    path = os.path.expanduser(path)
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as fh:
        data = fh.read()
    return len(data), data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)


def level(value, soft, hard):
    if hard is not None and value > hard:
        return "OVER"
    if soft is not None and value > soft:
        return "WARN"
    return "OK"


def check_file(root, name, lim):
    m = measure(os.path.join(root, name))
    if m is None:
        return "NOT FOUND", "%s: does not exist yet" % name
    size, lines = m
    worst, parts = "OK", []
    for label, value, soft, hard in (("bytes", size, lim.get("soft_bytes"), lim.get("hard_bytes")),
                                     ("lines", lines, None, lim.get("max_lines"))):
        if soft is None and hard is None:
            continue
        lv = level(value, soft, hard)
        cap = hard if hard is not None else soft
        parts.append("%d/%d %s (%d left)" % (value, cap, label, cap - value))
        if lv == "OVER" or (lv == "WARN" and worst == "OK"):
            worst = lv
    return worst, "%s: %s" % (name, ", ".join(parts))


def check_group(root, grp):
    total, missing = 0, []
    for name in grp["files"]:
        m = measure(name if os.path.isabs(os.path.expanduser(name)) else os.path.join(root, name))
        if m is None:
            missing.append(name)
        else:
            total += m[0]
    lv = level(total, grp.get("soft_bytes"), grp.get("hard_bytes"))
    cap = grp.get("hard_bytes") or grp.get("soft_bytes")
    note = " (missing: %s)" % ", ".join(missing) if missing else ""
    return lv, "group %s: %d/%d bytes combined (%d left)%s" % (grp["name"], total, cap, cap - total, note)


def run(cfg, root, paths):
    results = []
    files = cfg.get("files", {})
    wanted = [os.path.normpath(p) for p in paths]
    if wanted:
        for p in wanted:
            rel = os.path.relpath(p, root) if os.path.isabs(p) else p
            hit = next((k for k in files if os.path.normpath(k) == os.path.normpath(rel)), None)
            if hit:
                results.append(check_file(root, hit, files[hit]))
            in_group = [g for g in cfg.get("groups", []) if any(os.path.normpath(f) == os.path.normpath(rel) for f in g["files"])]
            results.extend(check_group(root, g) for g in in_group)
            if not hit and not in_group:
                results.append(("NO LIMIT", "%s has no configured limit" % p))
    else:
        results.extend(check_file(root, k, v) for k, v in sorted(files.items()))
        results.extend(check_group(root, g) for g in cfg.get("groups", []))
    return results


def selftest():
    with tempfile.TemporaryDirectory() as root:
        def put(name, text):
            with open(os.path.join(root, name), "w", encoding="utf-8", newline="") as fh:
                fh.write(text)
        put("small.md", "a\nb\n")
        put("warn.md", "x" * 60)
        put("over.md", "x" * 200)
        put("lines.md", "l\n" * 10)
        put("g1.md", "x" * 40)
        put("g2.md", "x" * 40)
        cfg = {"files": {"small.md": {"hard_bytes": 100}, "warn.md": {"soft_bytes": 50, "hard_bytes": 100},
                         "over.md": {"hard_bytes": 100}, "lines.md": {"max_lines": 5}, "gone.md": {"hard_bytes": 10}},
               "groups": [{"name": "pair", "files": ["g1.md", "g2.md"], "soft_bytes": 70, "hard_bytes": 100},
                          {"name": "tight", "files": ["g1.md", "g2.md"], "hard_bytes": 60}]}
        got = {r[1].split(":")[0]: r[0] for r in run(cfg, root, [])}
        expect = {"small.md": "OK", "warn.md": "WARN", "over.md": "OVER", "lines.md": "OVER",
                  "gone.md": "NOT FOUND", "group pair": "WARN", "group tight": "OVER"}
        assert got == expect, "levels differ: %r != %r" % (got, expect)
        one = run(cfg, root, ["over.md"])
        assert [r[0] for r in one] == ["OVER"], one
        assert run(cfg, root, ["unlisted.md"])[0][0] == "NO LIMIT"
        assert [r[0] for r in run(cfg, root, ["g1.md"])] == ["WARN", "OVER"], "group membership lookup"
        try:
            _check_limits("x", {}, ("hard_bytes",))
        except ConfigError:
            pass
        else:
            raise AssertionError("a limit-less entry must be a config error")
    print("selftest: PASS")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--config", default=os.environ.get("CAPACITY_CONFIG") or DEFAULT_CONFIG)
    ap.add_argument("--root", default=".")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        selftest()
        return 0
    try:
        results = run(load_config(args.config), args.root, args.paths)
    except ConfigError as exc:
        print("capacity config error: %s" % exc, file=sys.stderr)
        return 2
    for lv, text in results:
        print("%s: %s" % (lv, text))
    return 1 if any(lv == "OVER" for lv, _ in results) else 0


if __name__ == "__main__":
    sys.exit(main())
