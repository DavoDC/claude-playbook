"""doc_lint: config-driven documentation linter. Stdlib only.

Checks are selected and parameterised only by a JSON config file; each rule is
{"id": ..., "type": <built-in check type>, "files": [globs], ...params}.
See docs/25-config-driven-doc-linting.md for the check types and how to add a rule.

Usage:
    python3 doc_lint.py --config <config.json> [--root PATH] [--json]

Exit codes: 0 clean, 1 findings, 2 config error.
"""
import argparse
import json
import os
import posixpath
import re
import sys
import time
from collections import namedtuple
from pathlib import Path
from urllib.parse import unquote

Finding = namedtuple("Finding", "path line rule message severity", defaults=("error",))
SEVERITIES = ("error", "warn")

DEFAULT_EXCLUDE_DIRS = {".git", "__pycache__", "node_modules", ".venv"}
CHECKS = {}


class ConfigError(Exception):
    pass


def check(name, required=(), regex_params=()):
    def deco(fn):
        CHECKS[name] = (fn, tuple(required), tuple(regex_params))
        return fn
    return deco


# ---------------------------------------------------------------- helpers

def glob_to_re(pattern):
    """Translate a glob (supports ** and *) to an anchored regex over posix rel paths."""
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def static_prefix(pattern):
    parts = pattern.split("/")
    keep = []
    for p in parts[:-1]:
        if any(c in p for c in "*?"):
            break
        keep.append(p)
    return "/".join(keep) + "/" if keep else ""


class Ctx:
    def __init__(self, root, config_dir):
        self.root = Path(root)
        self.config_dir = Path(config_dir)
        self._files = None
        self._lines = {}
        self._masks = {}
        self._slugs = {}

    def all_files(self):
        if self._files is None:
            found = []
            for dirpath, dirnames, filenames in os.walk(self.root):
                dirnames[:] = [d for d in dirnames if d not in DEFAULT_EXCLUDE_DIRS]
                for fn in filenames:
                    rel = Path(dirpath, fn).relative_to(self.root).as_posix()
                    found.append(rel)
            self._files = sorted(found)
        return self._files

    def select(self, rule, key="files"):
        incl = [glob_to_re(g) for g in rule.get(key, [])]
        excl = [glob_to_re(g) for g in rule.get("exclude", [])]
        return [f for f in self.all_files()
                if any(r.match(f) for r in incl) and not any(r.match(f) for r in excl)]

    def lines(self, rel):
        if rel not in self._lines:
            text = (self.root / rel).read_text(encoding="utf-8", errors="replace")
            self._lines[rel] = text.splitlines()
        return self._lines[rel]

    def in_code(self, rel):
        """Per-line bool: True for fence lines and lines inside a fenced block."""
        if rel not in self._masks:
            mask, fence = [], None
            lines = self.lines(rel)
            fm_end = -1
            if lines and lines[0].strip() == "---":
                for j in range(1, len(lines)):
                    if lines[j].strip() == "---":
                        fm_end = j
                        break
            for idx, ln in enumerate(lines):
                if idx <= fm_end:
                    mask.append(True)
                    continue
                m = re.match(r"^\s{0,3}(`{3,}|~{3,})", ln)
                if fence:
                    mask.append(True)
                    if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and not ln.strip().strip(m.group(1)[0]):
                        fence = None
                elif m:
                    fence = m.group(1)
                    mask.append(True)
                else:
                    mask.append(False)
            self._masks[rel] = mask
        return self._masks[rel]

    def exists(self, rel):
        return (self.root / rel).exists()

    def anchors(self, rel):
        if rel not in self._slugs:
            seen, slugs = {}, set()
            mask = self.in_code(rel)
            for i, ln in enumerate(self.lines(rel)):
                if mask[i]:
                    continue
                m = re.match(r"^\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$", ln)
                if not m:
                    continue
                base = slugify(m.group(1))
                n = seen.get(base, 0)
                seen[base] = n + 1
                slugs.add(base if n == 0 else "%s-%d" % (base, n))
            self._slugs[rel] = slugs
        return self._slugs[rel]


def slugify(text):
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[`*_~]", "", text).strip().lower()
    text = re.sub(r"[^\w\- ]", "", text, flags=re.UNICODE)
    return text.replace(" ", "-")


def blank_inline_code(line):
    return re.sub(r"`[^`]*`", lambda m: " " * len(m.group(0)), line)


LINK_RE = re.compile(r"\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
SCHEME_RE = re.compile(r"^([a-z][a-z0-9+.\-]*:|//)", re.I)


def links_in(ctx, rel):
    """Yield (line_no, target) for markdown links outside code."""
    mask = ctx.in_code(rel)
    for i, ln in enumerate(ctx.lines(rel)):
        if mask[i]:
            continue
        for m in LINK_RE.finditer(blank_inline_code(ln)):
            yield i + 1, m.group(1)


def split_target(target, from_rel):
    """Return (resolved_rel_or_None_for_external, anchor)."""
    if SCHEME_RE.match(target):
        return None, ""
    path, _, anchor = target.partition("#")
    path = unquote(path.split("?")[0])
    if not path:
        return from_rel, anchor
    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(from_rel), path))
    if path.endswith("/"):
        resolved += "/"
    return resolved, anchor


def read_list_file(ctx, rule, key):
    p = Path(rule[key])
    if not p.is_absolute():
        p = ctx.config_dir / p
    if not p.is_file():
        raise ConfigError("rule %r: %s %r not found" % (rule["id"], key, str(p)))
    out = []
    for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
        ln = ln.strip()
        if ln and not ln.startswith("#"):
            out.append(ln)
    return out


# ---------------------------------------------------------------- checks

@check("forbidden-pattern", required=["files", "patterns"], regex_params=["patterns"])
def c_forbidden_pattern(ctx, rule):
    pats = [(p, re.compile(p, re.I if rule.get("ignore_case") else 0)) for p in rule["patterns"]]
    skip_code = rule.get("skip_code", False)
    for rel in ctx.select(rule):
        mask = ctx.in_code(rel)
        for i, ln in enumerate(ctx.lines(rel)):
            if skip_code and mask[i]:
                continue
            for src, rx in pats:
                m = rx.search(ln)
                if m:
                    msg = rule.get("message") or "forbidden pattern /%s/" % src
                    yield Finding(rel, i + 1, rule["id"], "%s (matched %r)" % (msg, m.group(0)))


@check("required-pattern", required=["files", "pattern"], regex_params=["pattern"])
def c_required_pattern(ctx, rule):
    rx = re.compile(rule["pattern"], re.M)
    n = rule.get("within_lines")
    for rel in ctx.select(rule):
        lines = ctx.lines(rel)
        window = lines[:n] if n else lines
        if not rx.search("\n".join(window)):
            where = "in the first %d lines" % n if n else "anywhere"
            yield Finding(rel, 1, rule["id"], rule.get("message") or "required pattern /%s/ not found %s" % (rule["pattern"], where))


_LIST_RE = re.compile(r"^\s*([-*+]|\d+[.)])\s")
_HEAD_RE = re.compile(r"^\s{0,3}#{1,6}(\s|$)")
_HR_RE = re.compile(r"^\s*([-*_=])\1{2,}\s*$")


def is_prose_line(ln):
    if not ln.strip() or ln[0] in " \t|>":
        return False
    if ln.lstrip().startswith("<") or _LIST_RE.match(ln) or _HEAD_RE.match(ln) or _HR_RE.match(ln):
        return False
    return True


@check("max-line-shape", required=["files"])
def c_max_line_shape(ctx, rule):
    for rel in ctx.select(rule):
        mask = ctx.in_code(rel)
        lines = ctx.lines(rel)
        run = []
        for i, ln in enumerate(lines + [""]):
            if i < len(lines) and not mask[i] and is_prose_line(ln):
                run.append(i + 1)
                continue
            if len(run) >= 2:
                yield Finding(rel, run[0], rule["id"], rule.get("message") or "paragraph hard-wrapped across %d lines (%d-%d); one paragraph = one line" % (len(run), run[0], run[-1]))
            run = []


@check("index-sync", required=["index", "files"])
def c_index_sync(ctx, rule):
    index = rule["index"]
    if not ctx.exists(index):
        yield Finding(index, 1, rule["id"], "index file not found")
        return
    targets = set()
    link_lines = []
    for ln_no, tgt in links_in(ctx, index):
        res, _ = split_target(tgt, index)
        if res is not None:
            targets.add(res.rstrip("/"))
            link_lines.append((ln_no, res))
    files = [f for f in ctx.select(rule) if f != index]
    if rule.get("mode", "link") == "mention":
        text = "\n".join(ctx.lines(index))
        for f in files:
            p = Path(f)
            name = p.parent.name if rule.get("name_from") == "parent" else p.stem
            if not re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(name), text):
                yield Finding(index, 1, rule["id"], "%s is not mentioned in the index (name %r)" % (f, name))
        return
    for f in files:
        if f not in targets and posixpath.dirname(f) not in targets:
            yield Finding(index, 1, rule["id"], "%s is not linked from the index" % f)
    prefixes = [static_prefix(g) for g in rule["files"]]
    for ln_no, res in link_lines:
        bare = res.rstrip("/")
        if any(bare.startswith(p) or (bare + "/").startswith(p) for p in prefixes if p) or not any(prefixes):
            if not ctx.exists(bare):
                yield Finding(index, ln_no, rule["id"], "index link %s does not resolve" % res)


@check("link-resolve", required=["files"])
def c_link_resolve(ctx, rule):
    anchors_on = rule.get("check_anchors", True)
    for rel in ctx.select(rule):
        for ln_no, tgt in links_in(ctx, rel):
            res, anchor = split_target(tgt, rel)
            if res is None:
                continue
            bare = res.rstrip("/")
            if not ctx.exists(bare):
                yield Finding(rel, ln_no, rule["id"], "link target %s does not exist" % tgt)
                continue
            if anchors_on and anchor and bare.lower().endswith(".md") and (ctx.root / bare).is_file():
                if slugify(unquote(anchor)) not in ctx.anchors(bare):
                    yield Finding(rel, ln_no, rule["id"], "anchor #%s not found in %s" % (anchor, bare))


@check("name-reference", required=["files", "pattern", "exists_in"], regex_params=["pattern"])
def c_name_reference(ctx, rule):
    rx = re.compile(rule["pattern"])
    allow = set(rule.get("allow", []))
    if rule.get("allow_file"):
        allow |= set(read_list_file(ctx, rule, "allow_file"))
    scope = rule.get("scope", "text")
    for rel in ctx.select(rule):
        mask = ctx.in_code(rel)
        for i, ln in enumerate(ctx.lines(rel)):
            if mask[i]:
                continue
            if scope == "inline-code":
                chunks = [m.group(1).strip() for m in re.finditer(r"`([^`]+)`", ln)]
            else:
                chunks = [blank_inline_code(ln)]
            for chunk in chunks:
                for m in rx.finditer(chunk):
                    name = m.group(1) if rx.groups else m.group(0)
                    if name in allow or any(ctx.exists(t.format(name=name)) for t in rule["exists_in"]):
                        continue
                    yield Finding(rel, i + 1, rule["id"], rule.get("message") or "%r not found (looked for %s) and not on the allow-list" % (m.group(0), ", ".join(t.format(name=name) for t in rule["exists_in"])))


@check("heading-uniqueness-across-files", required=["files"], regex_params=["ignore"])
def c_heading_uniqueness(ctx, rule):
    lo, hi = rule.get("min_level", 2), rule.get("max_level", 6)
    ignore = [re.compile(p, re.I) for p in rule.get("ignore", [])]
    first = {}
    for rel in ctx.select(rule):
        mask = ctx.in_code(rel)
        for i, ln in enumerate(ctx.lines(rel)):
            if mask[i]:
                continue
            m = re.match(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$", ln)
            if not m or not (lo <= len(m.group(1)) <= hi):
                continue
            raw = re.sub(r"[`*_]", "", m.group(2)).strip()
            if any(p.search(raw) for p in ignore):
                continue
            key = re.sub(r"\s+", " ", raw.lower())
            if key not in first:
                first[key] = (rel, i + 1)
            elif first[key][0] != rel and not (rel, key) in first:
                first[(rel, key)] = True
                o = first[key]
                yield Finding(rel, i + 1, rule["id"], "heading %r also in %s:%d (possible duplication)" % (raw, o[0], o[1]))


@check("max-words", required=["files", "limit"])
def c_max_words(ctx, rule):
    skip_code = rule.get("skip_code", True)
    for rel in ctx.select(rule):
        mask = ctx.in_code(rel)
        n = sum(len(ln.split()) for i, ln in enumerate(ctx.lines(rel)) if not (skip_code and mask[i]))
        if n > rule["limit"]:
            yield Finding(rel, 1, rule["id"], rule.get("message") or "%d words exceeds limit %d" % (n, rule["limit"]))


@check("min-words", required=["files", "limit"])
def c_min_words(ctx, rule):
    skip_code = rule.get("skip_code", True)
    for rel in ctx.select(rule):
        mask = ctx.in_code(rel)
        n = sum(len(ln.split()) for i, ln in enumerate(ctx.lines(rel)) if not (skip_code and mask[i]))
        if n < rule["limit"]:
            yield Finding(rel, 1, rule["id"], rule.get("message") or "%d words is under minimum %d" % (n, rule["limit"]))


@check("forbidden-terms-file", required=["files", "terms_file"])
def c_forbidden_terms_file(ctx, rule):
    terms = [t.lower() for t in read_list_file(ctx, rule, "terms_file")]
    reveal = rule.get("reveal_terms", False)
    for rel in ctx.select(rule):
        for i, ln in enumerate(ctx.lines(rel)):
            low = ln.lower()
            for n, t in enumerate(terms, 1):
                if t in low:
                    shown = t if reveal else "%s***" % t[:2]
                    yield Finding(rel, i + 1, rule["id"], "forbidden term #%d from terms file (%s)" % (n, shown))


@check("sequential-numbering", required=["files", "number_pattern"], regex_params=["number_pattern"])
def c_sequential_numbering(ctx, rule):
    pat = re.compile(rule["number_pattern"])
    last = set(rule.get("unnumbered_last", []))
    by_num = {}
    for rel in sorted(ctx.select(rule)):
        base = posixpath.basename(rel)
        m = pat.search(base)
        if not m:
            if base not in last:
                yield Finding(rel, 1, rule["id"], "no number in filename and not in unnumbered_last")
            continue
        by_num.setdefault(int(m.group(1)), []).append(rel)
    for n, rels in sorted(by_num.items()):
        if len(rels) > 1:
            for rel in rels[1:]:
                yield Finding(rel, 1, rule["id"], "shared number %d with %s" % (n, rels[0]))
    expected = 1
    for n in sorted(by_num):
        if n != expected:
            yield Finding(by_num[n][0], 1, rule["id"], "gap: expected number %d, found %d" % (expected, n))
        expected = n + 1
    if rule.get("heading_part"):
        for n, rels in by_num.items():
            for rel in rels:
                mask = ctx.in_code(rel)
                for i, ln in enumerate(ctx.lines(rel)):
                    if mask[i] or not re.match(r"^\s{0,3}#\s", ln):
                        continue
                    hm = re.search(r"\bPart (\d+)\b", ln)
                    if not hm:
                        yield Finding(rel, i + 1, rule["id"], "first heading has no 'Part N'")
                    elif int(hm.group(1)) != n:
                        yield Finding(rel, i + 1, rule["id"], "heading says Part %s but filename number is %d" % (hm.group(1), n))
                    break


# ---------------------------------------------------------------- engine

def validate(rules):
    seen = set()
    for r in rules:
        rid = r.get("id")
        if not rid:
            raise ConfigError("rule without an id: %r" % (r,))
        if rid in seen:
            raise ConfigError("duplicate rule id %r" % rid)
        seen.add(rid)
        t = r.get("type")
        if t not in CHECKS:
            raise ConfigError("rule %r: unknown type %r (known: %s)" % (rid, t, ", ".join(sorted(CHECKS))))
        if r.get("severity", "error") not in SEVERITIES:
            raise ConfigError("rule %r: severity must be one of %s" % (rid, ", ".join(SEVERITIES)))
        _, required, regex_params = CHECKS[t]
        for p in required:
            if p not in r:
                raise ConfigError("rule %r (%s): missing required param %r" % (rid, t, p))
        for p in regex_params:
            if p not in r:
                continue
            vals = r[p] if isinstance(r[p], list) else [r[p]]
            for v in vals:
                try:
                    re.compile(v)
                except re.error as e:
                    raise ConfigError("rule %r: bad regex in %r: %s" % (rid, p, e))


def run(config, root, config_dir):
    rules = config.get("rules", [])
    validate(rules)
    ctx = Ctx(root, config_dir)
    findings = []
    for r in rules:
        if r.get("enabled", True) is False:
            continue
        fn = CHECKS[r["type"]][0]
        sev = r.get("severity", "error")
        findings.extend(f._replace(severity=sev) for f in fn(ctx, r))
    findings.sort(key=lambda f: (f.path, f.line, f.rule))
    return findings


def main(argv=None):
    ap = argparse.ArgumentParser(description="Config-driven documentation linter")
    ap.add_argument("--config", required=True)
    ap.add_argument("--root")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    t0 = time.perf_counter()
    cfg_path = Path(args.config).resolve()
    try:
        config = json.loads(cfg_path.read_text(encoding="utf-8"))
        root = Path(args.root) if args.root else (cfg_path.parent / config.get("root", ".")).resolve()
        findings = run(config, root.resolve(), cfg_path.parent)
    except (ConfigError, OSError, ValueError) as e:
        print("doc_lint config error: %s" % e, file=sys.stderr)
        return 2
    elapsed = time.perf_counter() - t0
    counts = {}
    for f in findings:
        counts[f.rule] = counts.get(f.rule, 0) + 1
    if args.json:
        print(json.dumps({"findings": [f._asdict() for f in findings], "counts": counts,
                          "elapsed_s": round(elapsed, 3)}, indent=2))
        print("elapsed %.3fs" % elapsed, file=sys.stderr)
    else:
        for f in findings:
            tag = "warn: " if f.severity == "warn" else ""
            print("%s:%d: [%s] %s%s" % (f.path, f.line, f.rule, tag, f.message))
        for rid in sorted(counts):
            print("  %s: %d" % (rid, counts[rid]))
        print("%d finding(s) in %d rule(s); elapsed %.3fs" % (len(findings), len(counts), elapsed))
    return 1 if any(f.severity == "error" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
