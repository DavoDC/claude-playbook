#!/usr/bin/env python3
"""backlog.py: the only editor of a repo backlog (IDEAS.md). Stdlib only.

Spec: templates/BACKLOG-SPEC.md (item format, lifecycle, health rules).

Usage:
  backlog.py check  (<repo> | --file PATH | --all) [--json]   health rules; exit 1 on any fail
  backlog.py status (<repo> | --file PATH) [--json]           about 10 lines: counts, top ready, lint
  backlog.py add    (<repo> | --file PATH) "raw words" [--force]   dated INBOX append, duplicate-checked; creates `## INBOX` if the file has none
  backlog.py init | shape | next | brief | close | move | split | merge   see templates/BACKLOG-SPEC.md

<repo> resolves through the `locations` templates in config/backlog.json (see config/backlog.example.json).
"""
import argparse
import difflib
import glob
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
BASE_DIR = TOOLS_DIR.parent
DEFAULT_SETTINGS = {
    "agent_owner": "Claude",
    "human_owner": "Human",
    "locations": ["backlogs/{repo}/IDEAS.md", "../{repo}/docs/IDEAS.md"],
}


def load_config(path=None):
    """Settings from `path`, else $BACKLOG_CONFIG, else config/backlog.json; built-in defaults when none exists."""
    path = Path(path or os.environ.get("BACKLOG_CONFIG") or BASE_DIR / "config" / "backlog.json")
    cfg = dict(DEFAULT_SETTINGS)
    if path.is_file():
        cfg.update({k: v for k, v in json.loads(path.read_text(encoding="utf-8")).items() if k in DEFAULT_SETTINGS})
    return cfg


CONFIG = load_config()
AGENT = CONFIG["agent_owner"]
HUMAN = CONFIG["human_owner"]
HUMAN_SECTION = f"{HUMAN.upper()} ONLY"

TIERS = ["T0", "T1", "T2", "T3", "T4"]
STATES = {"inbox", "idea", "ready", "blocked", "in-progress"}
SIZES = {"S", "M", "L"}
REQUIRED = ["goal", "acceptance"]
MAX_ITEM_LINES = 25
T0_CAP = 10
IDEA_SHARE_MAX = 0.30
INBOX_MAX_DAYS = 7
DUP_RATIO = 0.6
ID_RE = re.compile(r"\b[A-Z][A-Z0-9]*-[A-Za-z0-9]+\b")
LOWER_ID_RE = re.compile(r"\b[a-z][a-z0-9]*-\d+\b")  # digits only: words like yt-dlp are not ids
RANGE_RE_IDS = re.compile(r"\b([A-Z][A-Z0-9]*)-([A-Za-z0-9]+) to \1-([A-Za-z0-9]+)\b")
FIELD_RE = re.compile(r"^- \*\*([^*]+?):\*\*\s*(.*)$")
TIER_HEADING = re.compile(r"^## TIER (\d)\b")
COMPLETION = [
    re.compile(r"~~[^~]+~~"),
    re.compile(r"^\s*-?\s*\*{0,2}Status:?\*{0,2}:?\s*\**\s*(done|fixed|complete|completed|shipped)\b", re.I),
    re.compile(r"\[[xX]\]"),
]
LETTERED = re.compile(r"^\s*-\s*\(?[a-f][.)]\s")


class BacklogError(Exception):
    pass


def upper_id(id_):
    """Backlog id prefixes are always uppercase (MS-25, never ms-25); the suffix is left alone."""
    pre, dash, rest = id_.partition("-")
    return pre.upper() + dash + rest


@dataclass
class Item:
    id: str
    title: str
    line: int
    end: int
    section_tier: str
    fields: dict = field(default_factory=dict)
    goal_count: int = 0
    lettered: int = 0
    tier: str = ""
    size: str = ""
    state: str = ""
    owner: str = ""
    state_note: str = ""
    lines: list = field(default_factory=list)

    @property
    def length(self):
        return self.end - self.line + 1


@dataclass
class Finding:
    level: str
    rule: str
    line: int
    msg: str
    id: str = ""

    def as_dict(self):
        return {"level": self.level, "rule": self.rule, "line": self.line, "id": self.id, "msg": self.msg}


@dataclass
class Doc:
    lines: list
    items: list
    sections: dict  # name -> (start_line_index, end_line_index) 0-based, end exclusive


def parse(text):
    lines = text.splitlines()
    sections = {}
    order = []
    for i, ln in enumerate(lines):
        if ln.startswith("## "):
            order.append((ln[3:].strip(), i))
    for n, (name, i) in enumerate(order):
        end = order[n + 1][1] if n + 1 < len(order) else len(lines)
        sections[name] = (i, end)
    items = []
    cur_tier = ""
    starts = []
    for i, ln in enumerate(lines):
        m = TIER_HEADING.match(ln)
        if m:
            cur_tier = f"T{m.group(1)}"
        elif ln.startswith("## "):
            cur_tier = ""
        elif ln.startswith("### ") and cur_tier:
            starts.append((i, cur_tier))
    for n, (i, tier) in enumerate(starts):
        # item ends at the next heading of any level, trailing blanks trimmed
        j = i + 1
        while j < len(lines) and not lines[j].startswith("#"):
            j += 1
        end = j - 1
        while end > i and not lines[end].strip():
            end -= 1
        hm = re.match(r"^### ([^:\s]+):\s*(.*)$", lines[i])
        id_, title = (hm.group(1), hm.group(2).strip()) if hm else (lines[i][4:].strip(), "")
        it = Item(id=id_, title=title, line=i + 1, end=end + 1, section_tier=tier, lines=lines[i:end + 1])
        for ln in lines[i + 1:end + 1]:
            fm = FIELD_RE.match(ln)
            if fm:
                label, val = fm.group(1).strip(), fm.group(2).strip()
                if label.lower().startswith("tier"):
                    parts = [p.strip() for p in val.split("/")]
                    if len(parts) == 4:
                        it.tier, it.size, it.state, it.owner = (re.split(r"\s*[(,]", q, maxsplit=1)[0].strip() for q in parts)
                        it.state_note = parts[2]
                    it.fields["tier"] = val
                else:
                    key = label.lower().split()[0].split("/")[0]
                    it.fields.setdefault(key, val)
                    if key == "goal":
                        it.goal_count += 1
            if LETTERED.match(ln):
                it.lettered += 1
        items.append(it)
    return Doc(lines=lines, items=items, sections=sections)


def _table_rows(doc):
    if "INDEX" not in doc.sections:
        return None
    s, e = doc.sections["INDEX"]
    rows = []
    for i in range(s, e):
        ln = doc.lines[i]
        if ln.startswith("|") and not ln.startswith("| id") and not ln.startswith("|--"):
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            rows.append((i + 1, cells))
    return rows


def _section_text(doc, name):
    if name not in doc.sections:
        return []
    s, e = doc.sections[name]
    return [(i + 1, doc.lines[i]) for i in range(s + 1, e)]


def check(doc, today=None):
    today = today or date.today()
    fs = []

    def add(level, rule, line, msg, id_=""):
        fs.append(Finding(level, rule, line, msg, id_))

    seen = {}
    for it in doc.items:
        if LOWER_ID_RE.fullmatch(it.id):
            add("fail", "lowercase-id", it.line, f"{it.id} has a lowercase prefix, write {upper_id(it.id)}", it.id)
        if it.id in seen:
            add("fail", "duplicate-id", it.line, f"{it.id} also at line {seen[it.id]}", it.id)
        seen.setdefault(it.id, it.line)
        if not (it.tier and it.size and it.state and it.owner):
            add("fail", "missing-field", it.line, "Tier / Size / State / Owner line missing or incomplete", it.id)
        else:
            if it.tier not in TIERS or it.size not in SIZES or it.state not in STATES:
                add("fail", "bad-value", it.line, f"tier {it.tier!r}, size {it.size!r} or state {it.state!r} not allowed", it.id)
            if it.tier != it.section_tier:
                add("fail", "tier-section", it.line, f"tier {it.tier} sits in the {it.section_tier} section", it.id)
            if it.state == "ready" and it.size == "L":
                add("fail", "ready-l", it.line, "size L is an epic, never ready: split it", it.id)
            if it.tier == "T0" and it.state == "idea":
                add("fail", "t0-idea", it.line, "an idea cannot sit in T0: shape it or demote it", it.id)
        for req in REQUIRED:
            if not it.fields.get(req):
                add("fail", "missing-field", it.line, f"no {req.capitalize()} line", it.id)
        if it.length > MAX_ITEM_LINES:
            add("fail", "item-too-long", it.line, f"{it.length} lines, max {MAX_ITEM_LINES}", it.id)
        if it.goal_count > 1 or it.lettered >= 3:
            add("fail", "multi-goal", it.line, "more than one goal or lettered sub-items: split by acceptance test", it.id)
        if it.state == "blocked":
            dep = it.fields.get("depends", "")
            first = dep.split("/")[0].strip().rstrip(".").lower()
            if (not first or first == "none") and "(" not in it.state_note:
                add("fail", "blocked-no-reason", it.line, "blocked item must name what unblocks it in Depends on", it.id)
        for k, ln in enumerate(it.lines):
            if any(p.search(ln) for p in COMPLETION):
                add("fail", "completion-marker", it.line + k, "completed items belong in HISTORY.md", it.id)
                break

    n = len(doc.items)
    t0 = [i for i in doc.items if i.tier == "T0"]
    if len(t0) > T0_CAP:
        add("warn", "t0-cap", doc.sections.get("TIER 0 BLOCKING", (0,))[0] + 1, f"T0 holds {len(t0)} items, cap about {T0_CAP}")
    ideas = sum(1 for i in doc.items if i.state == "idea")
    if n and ideas / n > IDEA_SHARE_MAX:
        add("warn", "idea-share", 1, f"{ideas} of {n} items are ideas ({ideas * 100 // n}%), triage before building")

    rows = _table_rows(doc)
    if rows is None:
        add("fail", "index-mismatch", 1, "no INDEX section")
    else:
        for ln, c in rows:
            for cell in (c[0], c[6] if len(c) > 6 else ""):
                for bad in LOWER_ID_RE.findall(cell):
                    add("fail", "lowercase-id", ln, f"INDEX row has {bad}, write {upper_id(bad)}", bad)
        want = [[i.id, i.title, i.tier, i.size, i.state, i.owner] for i in doc.items]
        got = [(ln, c) for ln, c in rows]
        want_ids = [w[0] for w in want]
        got_ids = [c[0] for _, c in got]
        for w in want:
            if w[0] not in got_ids:
                add("fail", "index-mismatch", 1, f"{w[0]} has no INDEX row", w[0])
        for ln, c in got:
            if c[0] not in want_ids:
                add("fail", "index-mismatch", ln, f"INDEX row {c[0]} has no item", c[0])
        by = {w[0]: w for w in want}
        for ln, c in got:
            w = by.get(c[0])
            if w and c[:6] != w:
                add("fail", "index-mismatch", ln, f"{c[0]} row differs from item: index {c[1:6]} vs item {w[1:]}", c[0])
        tiers = [c[2] for _, c in got if c[0] in by]
        if tiers != sorted(tiers):
            add("fail", "index-mismatch", got[0][0], "INDEX rows are not grouped in tier order (T0 first)")

    ids = set(seen)
    human = {i.id for i in doc.items if i.owner == HUMAN}
    dtext = " ".join(t for _, t in _section_text(doc, HUMAN_SECTION))
    if HUMAN_SECTION not in doc.sections:
        if human:
            add("fail", "human-only", 1, f"no {HUMAN_SECTION} section")
    else:
        dline = doc.sections[HUMAN_SECTION][0] + 1
        mentioned = set(ID_RE.findall(dtext))
        for i in sorted(human - mentioned):
            add("fail", "human-only", dline, f"{i} is {HUMAN}-owned but missing from {HUMAN_SECTION}", i)
        for i in sorted(mentioned - ids):
            add("warn", "human-only", dline, f"{i} mentioned in {HUMAN_SECTION} but is not an item", i)

    for ln, text in _section_text(doc, "INDEX"):
        if text.startswith("Epics"):
            for i in sorted(set(ID_RE.findall(text)) - ids):
                add("fail", "epic-unknown-id", ln, f"epic child {i} is not an item", i)
            for pre, a, b in RANGE_RE_IDS.findall(text):
                lo, hi = _suffix_val(a), _suffix_val(b)
                if lo is None or hi is None or type(lo) is not type(hi) or hi < lo or a.isdigit() != b.isdigit():
                    continue
                for n in range(lo, hi + 1):
                    cid = f"{pre}-{_suffix_str(n, a)}"
                    if cid not in ids:
                        add("fail", "epic-unknown-id", ln, f"epic child {cid} (in range {pre}-{a} to {pre}-{b}) is not an item", cid)

    if "INBOX" not in doc.sections and "INDEX" in doc.sections:
        add("warn", "inbox-missing", 1, "no INBOX section; `backlog.py add` creates it on first use")
    for ln, text in _section_text(doc, "INBOX"):
        m = re.match(r"^\s*[-*]\s*(\d{4}-\d{2}-\d{2})\b", text)
        if m:
            try:
                age = (today - datetime.strptime(m.group(1), "%Y-%m-%d").date()).days
            except ValueError:
                continue
            if age > INBOX_MAX_DAYS:
                add("fail", "inbox-stale", ln, f"INBOX entry is {age} days old, triage it")
    return fs


def is_strict(text):
    return re.search(r"^## INDEX\b", text, re.M) is not None


def unformatted_lowercase_ids(text):
    """Lowercase spellings of the prefixes a file itself uses in uppercase (ms-1 in a file with MS-1), so plain
    words like yt-dlp never match. Lets `check --all` catch the rule break in backlogs not yet in the strict format."""
    prefixes = {m.group(1) for m in re.finditer(r"\b([A-Z][A-Z0-9]*)-\d+\b", text)}
    if not prefixes:
        return []
    bad = re.compile(r"\b(" + "|".join(re.escape(p.lower()) for p in prefixes) + r")-(\d+)\b")
    fs = []
    for n, ln in enumerate(text.splitlines(), 1):
        for m in bad.finditer(ln):
            tok = m.group(0)
            fs.append(Finding("fail", "lowercase-id", n, f"{tok} has a lowercase prefix, write {upper_id(tok)}", tok))
    return fs


def check_many(paths, skip_unformatted=False):
    """(results, any_fail, skipped): results maps path to (doc, findings); unformatted files are skipped when asked."""
    result, bad, skipped = {}, False, []
    for path in paths:
        text = Path(path).read_text(encoding="utf-8")
        if skip_unformatted and not is_strict(text):
            skipped.append(str(path))
            fs = unformatted_lowercase_ids(text)
            if fs:
                result[str(path)] = (parse(text), fs)
                bad = True
            continue
        doc = parse(text)
        fs = check(doc)
        bad = bad or any(f.level == "fail" for f in fs)
        result[str(path)] = (doc, fs)
    return result, bad, skipped


def status(doc):
    by_tier = {t: 0 for t in TIERS}
    by_state = {}
    for it in doc.items:
        by_tier[it.tier] = by_tier.get(it.tier, 0) + 1
        by_state[it.state] = by_state.get(it.state, 0) + 1
    n = len(doc.items)
    blocked_ids = {i.id for i in doc.items}
    top = [i.id for i in doc.items if i.state == "ready" and i.owner == AGENT][:5]
    return {
        "items": n,
        "by_tier": by_tier,
        "by_state": by_state,
        "t0_size": by_tier["T0"],
        "idea_share": (by_state.get("idea", 0) / n) if n else 0.0,
        "top_ready": top,
    }


def render_status(name, doc, findings):
    s = status(doc)
    fails = [f for f in findings if f.level == "fail"]
    warns = [f for f in findings if f.level == "warn"]
    titles = {i.id: i.title for i in doc.items}
    out = [
        f"{name}: {s['items']} items | T0 {s['by_tier']['T0']} T1 {s['by_tier']['T1']} T2 {s['by_tier']['T2']} T3 {s['by_tier']['T3']} T4 {s['by_tier']['T4']}",
        "states: " + ", ".join(f"{k} {v}" for k, v in sorted(s["by_state"].items())),
        f"T0 size {s['t0_size']} (cap about {T0_CAP}) | idea share {s['idea_share'] * 100:.0f}% (max {IDEA_SHARE_MAX * 100:.0f}%)",
        f"top ready ({AGENT}):",
    ]
    out += [f"  {i}: {titles[i]}" for i in s["top_ready"]] or ["  none"]
    inbox = [t for _, t in _section_text(doc, "INBOX") if re.match(r"^\s*[-*]\s*\d{4}-", t)]
    out.append(f"inbox: {len(inbox)} raw entries")
    out.append(f"check: {len(fails)} fail, {len(warns)} warn" + (" (run `backlog.py check` for detail)" if fails or warns else ""))
    return "\n".join(out)


def _norm(t):
    return re.sub(r"[^a-z0-9 ]", "", t.lower())


def find_duplicates(doc, text):
    n = _norm(text)
    hits = []
    cands = [(i.id, i.title) for i in doc.items]
    cands += [("INBOX", re.sub(r"^\s*[-*]\s*\d{4}-\d{2}-\d{2}:?\s*", "", t)) for _, t in _section_text(doc, "INBOX") if re.match(r"^\s*[-*]\s*\d{4}-", t)]
    nw = set(n.split())
    for cid, ctext in cands:
        c = _norm(ctext)
        cw = set(c.split())
        ratio = difflib.SequenceMatcher(None, n, c).ratio()
        overlap = len(nw & cw) / max(1, min(len(nw), len(cw)))
        if ratio >= DUP_RATIO or (len(cw) >= 4 and overlap >= 0.8):
            hits.append((cid, ctext))
    return hits


def _with_inbox_section(raw, doc):
    """Insert an empty `## INBOX` section: after INDEX when there is one, else before the first `## ` heading, else at the end."""
    lines = raw.split("\n")
    if "INDEX" in doc.sections:
        at = doc.sections["INDEX"][1]
    elif doc.sections:
        at = min(s for s, _ in doc.sections.values())
    else:
        at = len(lines) - 1 if lines and lines[-1] == "" else len(lines)
    block = ["## INBOX", "", "Raw captures, newest first, not yet shaped.", ""]
    if at and lines[at - 1].strip():
        block = [""] + block
    lines[at:at] = block
    return "\n".join(lines)


def add(path, text, force=False, today=None):
    text = " ".join(text.split())
    if not text:
        raise BacklogError("add needs non-empty raw text")
    path = Path(path)
    data = path.read_bytes().decode("utf-8")
    nl = "\r\n" if "\r\n" in data else "\n"
    raw = data.replace("\r\n", "\n")
    doc = parse(raw)
    if "INBOX" not in doc.sections:
        raw = _with_inbox_section(raw, doc)
        doc = parse(raw)
    dups = find_duplicates(doc, text)
    if dups and not force:
        listing = "; ".join(f"{i}: {t[:70]}" for i, t in dups[:3])
        raise BacklogError(f"possible duplicate ({listing}). Merge into it, or re-run with --force")
    today = (today or date.today()).isoformat()
    lines = raw.split("\n")
    s, e = doc.sections["INBOX"]
    body = lines[s + 1:e]
    bullets = [ln for ln in body if re.match(r"^\s*[-*]\s*\d{4}-", ln)]
    prose = [re.sub(r"\s*Empty as of \d{4}-\d{2}-\d{2}\.?", "", ln) for ln in body if ln.strip() and ln not in bullets]
    entry = f"- {today}: {text}"
    section = [""] + prose + ([""] if prose else []) + [entry] + bullets + [""]
    lines[s + 1:e] = section
    path.write_bytes(nl.join(lines).encode("utf-8"))
    where = "duplicate forced" if dups else "no duplicate found"
    return f"added to INBOX of {path} ({where}): {entry}"


SHA_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")
TEMPLATE = f"""# Ideas

## INDEX

| id | title | tier | size | state | owner | blocked-by |
|---|---|---|---|---|---|---|

## INBOX

Raw captures, newest first.

## {HUMAN_SECTION}

None.

## TIER 0 BLOCKING

## TIER 1 CORE

## TIER 2 QUALITY

## TIER 3 POLISH

## TIER 4 PARKED
"""
TIER_SECTION = {"T0": r"^## TIER 0\b", "T1": r"^## TIER 1\b", "T2": r"^## TIER 2\b", "T3": r"^## TIER 3\b", "T4": r"^## TIER 4\b"}


def _read(path):
    data = Path(path).read_bytes().decode("utf-8")
    return data.replace("\r\n", "\n"), ("\r\n" if "\r\n" in data else "\n")


def _write(path, lines, nl):
    Path(path).write_bytes(nl.join(lines).encode("utf-8"))


def _find(doc, id_, path=""):
    for it in doc.items:
        if it.id == id_:
            return it
    raise BacklogError(f"no item {id_}" + (f" in {path}" if path else ""))


def _sentence(text):
    text = " ".join(text.split())
    return text if not text or text[-1] in ".!?" else text + "."


RANGE_RE = re.compile(r"(,\s*)?\b([A-Z][A-Z0-9]*)-([A-Za-z0-9]+) to \2-([A-Za-z0-9]+)\b(\s*,)?")


def _suffix_val(s):
    """Orderable value of an id suffix: an int for digits, an ord for one letter, else None."""
    if s.isdigit():
        return int(s)
    return ord(s) if len(s) == 1 and s.isalpha() else None


def _suffix_str(v, like):
    return str(v) if like.isdigit() else chr(v)


def _strip_id(text, id_):
    """Remove one id from a list line: ranges `A-1 to A-9` are split around it, plain ids drop with their comma."""
    pre, _, suf = id_.partition("-")
    target = _suffix_val(suf)

    def rng(m):
        lo, hi = _suffix_val(m.group(3)), _suffix_val(m.group(4))
        if m.group(2) != pre or target is None or lo is None or hi is None or type(lo) is not type(hi) or not lo <= target <= hi:
            return m.group(0)
        if m.group(3).isdigit() != suf.isdigit():
            return m.group(0)
        parts = []
        for a, b in ((lo, target - 1), (target + 1, hi)):
            if a > b:
                continue
            first, last = f"{pre}-{_suffix_str(a, suf)}", f"{pre}-{_suffix_str(b, suf)}"
            parts.append(first if a == b else f"{first} to {last}")
        body = ", ".join(parts)
        if body:
            return (m.group(1) or "") + body + (m.group(5) or "")
        return ", " if (m.group(1) and m.group(5)) else ""

    out = RANGE_RE.sub(rng, text)
    out = re.sub(rf"(,\s*)?(?<![\w-])(?<!to ){re.escape(id_)}(?![\w-])(?! to )(\s*,)?", lambda m: ", " if (m.group(1) and m.group(2)) else "", out)
    return re.sub(r"  +", " ", out)


def _section_range(lines, name):
    """(start, end) of a `## name...` section in lines, end exclusive; None when absent."""
    start = None
    for i, ln in enumerate(lines):
        if ln.startswith("## "):
            if start is not None:
                return start, i
            if ln[3:].strip() == name or re.match(name, ln):
                start = i
    return (start, len(lines)) if start is not None else None


def _dep_ids(it):
    return ID_RE.findall(it.fields.get("depends", "").split("/")[0])


def next_item(doc, owner=None):
    """First unblocked ready item of `owner`, highest tier first, document order within a tier."""
    owner = owner or AGENT
    ids = {i.id for i in doc.items}
    def open_dep(it):
        return any(d in ids and d != it.id for d in _dep_ids(it))
    cands = [i for i in doc.items if i.state == "ready" and i.owner.lower() == owner.lower() and not open_dep(i)]
    cands.sort(key=lambda i: TIERS.index(i.tier) if i.tier in TIERS else len(TIERS))
    return cands[0] if cands else None


DELEGATION_PREAMBLE = """You are doing implementation work from a self-contained brief. Read it fully before acting.

- Do the work described, not more. If you find something adjacent worth
  fixing, name it in your report rather than doing it unprompted.
- Verify your own change before reporting done: run the relevant test(s),
  re-read the diff, confirm the claim you're about to make is literally true.
- Report the artifact, not a summary of intent - what file(s) changed, what
  the test run actually showed, any deviation from the brief and why.
- If you hit something genuinely ambiguous that the brief doesn't resolve,
  stop and ask rather than guessing past it."""


def brief(doc, id_):
    """A delegation preamble, the item verbatim, and one line per related item named in Depends or Pointers."""
    it = _find(doc, id_)
    by = {i.id: i for i in doc.items}
    text = it.fields.get("depends", "") + " " + it.fields.get("pointers", "")
    rel = [f"- {r}: {by[r].title} ({by[r].state})" for r in dict.fromkeys(ID_RE.findall(text)) if r in by and r != id_]
    out = "\n".join(it.lines)
    out += "\n\nRelated items (titles only):\n" + "\n".join(rel) if rel else ""
    return DELEGATION_PREAMBLE + "\n\n" + out


def shape_checklist(doc, id_):
    it = _find(doc, id_)
    return [
        (bool(it.fields.get("goal")), "Goal: one sentence, the outcome not the method"),
        (bool(it.fields.get("acceptance")), "Acceptance: checkable, ideally a command or an observed value"),
        (it.size in ("S", "M"), f"Size S or M (now {it.size or 'unset'}; L is an epic, split it)"),
        (it.tier in TIERS, f"Tier T0 to T4 (now {it.tier or 'unset'})"),
        (it.owner in (AGENT, HUMAN), f"Owner {AGENT} or {HUMAN} (now {it.owner or 'unset'})"),
        (it.goal_count <= 1 and it.lettered < 3, "One goal only: no second Goal line, no lettered sub-items"),
        (it.length <= MAX_ITEM_LINES, f"At most {MAX_ITEM_LINES} lines (now {it.length})"),
        (True, "Verify (optional, " + ("set" if it.fields.get("verify") else "not set") + "): command that proves the acceptance, close runs it"),
    ]


def _table_bounds(lines):
    """(first_row_index, end_index) of the INDEX table body, rows only."""
    rng = _section_range(lines, "INDEX")
    if not rng:
        raise BacklogError("no INDEX section")
    sep = next((i for i in range(rng[0], rng[1]) if lines[i].startswith("|--")), None)
    if sep is None:
        raise BacklogError("INDEX has no table")
    end = sep + 1
    while end < rng[1] and lines[end].startswith("|"):
        end += 1
    return sep + 1, end


def _regen_index(lines, fresh=()):
    """Rewrite INDEX rows from the items, tier grouped; existing order and blocked-by cells kept, `fresh` ids go last in their tier."""
    doc = parse("\n".join(lines))
    a, b = _table_bounds(lines)
    old = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in lines[a:b]]
    order = {c[0]: n for n, c in enumerate(old) if c and c[0] not in fresh}
    blocked = {c[0]: c[6] for c in old if len(c) > 6}
    items = sorted(enumerate(doc.items), key=lambda p: (TIERS.index(p[1].tier) if p[1].tier in TIERS else 9, order.get(p[1].id, 10 ** 6 + p[0])))
    rows = [f"| {i.id} | {i.title} | {i.tier} | {i.size} | {i.state} | {i.owner} | {blocked.get(i.id, 'none')} |" for _, i in items]
    lines[a:b] = rows


def _human_sync(lines, id_, title, is_human):
    rng = _section_range(lines, HUMAN_SECTION)
    if not rng:
        return
    s, e = rng
    body = lines[s + 1:e]
    mention = [k for k, ln in enumerate(body) if re.search(rf"\b{re.escape(id_)}\b", ln)]
    if is_human and not mention:
        body = [ln for ln in body if not re.match(r"^\s*none\.?\s*$", ln, re.I)]
        k = len(body)
        while k > 0 and not body[k - 1].strip():
            k -= 1
        body.insert(k, f"- {id_}: {_sentence(title)}")
    elif not is_human and mention:
        for k in reversed(mention):
            others = set(ID_RE.findall(body[k])) - {id_}
            if others:
                body[k] = _strip_id(body[k], id_)
            else:
                del body[k]
    if not any(ln.strip() for ln in body):
        body = ["", "None.", ""]
    lines[s + 1:e] = body


def _new_fails(before_raw, after_lines, today):
    def keys(text):
        return {(f.rule, f.id) for f in check(parse(text), today=today) if f.level == "fail"}
    return keys("\n".join(after_lines)) - keys(before_raw)


def _set_field(body, label, value, pos):
    """Set `- **label:** value` in place, or insert at pos; None keeps what is there. Returns the index after the field."""
    pat = re.compile(rf"^- \*\*{re.escape(label)}:\*\*")
    for k, ln in enumerate(body):
        if pat.match(ln):
            if value is not None:
                body[k] = f"- **{label}:** {value}"
            return k + 1
    if value is None:
        return pos
    body.insert(pos, f"- **{label}:** {value}")
    return pos + 1


_BEHAVIOUR_RE = re.compile(r"\b(quit|stop|close|start|always)\b", re.I)
_UI_STRING_RE = re.compile(r'"[^"\n]+"')
_DOC_PATH_RE = re.compile(r"[\w./-]+\.(?:md|txt|rst)\b|\bdocs?/", re.I)


def behaviour_warning(goal, acceptance):
    """Warn (never block) when a behaviour change names neither the user-visible text it changes nor a doc."""
    text = f"{goal} {acceptance}"
    if not _BEHAVIOUR_RE.search(text) or _UI_STRING_RE.search(text) or _DOC_PATH_RE.search(text):
        return ""
    return ("WARNING: goal or acceptance describes a behaviour change (quit, stop, close, start, always) but names no "
            'quoted user-visible text ("Menu label") and no doc path; add the label or message it changes and the docs '
            "that describe it (templates/BACKLOG-SPEC.md, Acceptance)")


def _old_label_hits(labels, cwd):
    out = []
    for label in labels:
        r = subprocess.run(["git", "grep", "-nF", "-e", label, "--", ".", ":(exclude)**/IDEAS.md", ":(exclude)**/HISTORY.md"],
                           cwd=str(cwd), capture_output=True, text=True, timeout=60)
        hits = r.stdout.strip().splitlines() if r.returncode == 0 else []
        if hits:
            out.append(f"WARNING: old label {label!r} still appears in {len(hits)} place(s): " + "; ".join(h[:120] for h in hits[:5]))
    return out


def shape(path, id_, *, title=None, tier=None, size=None, goal=None, acceptance=None, owner=None, verify=None,
          new=False, from_inbox=None, today=None):
    today = today or date.today()
    raw, nl = _read(path)
    lines = raw.split("\n")
    doc = parse(raw)
    if new:
        id_ = upper_id(id_)
    exists = next((i for i in doc.items if i.id == id_), None)
    if new:
        if exists:
            raise BacklogError(f"item {id_} exists already; shape it without --new")
        miss = [n for n, v in (("title", title), ("tier", tier), ("size", size), ("goal", goal), ("acceptance", acceptance), ("owner", owner)) if not v]
        if miss:
            raise BacklogError("--new needs " + ", ".join(f"--{m}" for m in miss))
        cur = {"title": title, "tier": tier, "size": size, "owner": owner, "goal": goal, "acceptance": acceptance}
        base = []
    else:
        if not exists:
            raise BacklogError(f"no item {id_} in {path}; use --new to create it")
        if exists.state in ("blocked", "in-progress"):
            raise BacklogError(f"{id_} is {exists.state}; shape only turns an idea or inbox item into ready")
        cur = {"title": title or exists.title, "tier": tier or exists.tier, "size": size or exists.size,
               "owner": owner or exists.owner, "goal": goal or exists.fields.get("goal", ""),
               "acceptance": acceptance or exists.fields.get("acceptance", "")}
        base = list(exists.lines[1:])
    if not cur["goal"]:
        raise BacklogError(f"{id_} needs a Goal (--goal)")
    if not cur["acceptance"]:
        raise BacklogError(f"{id_} needs an Acceptance (--acceptance)")
    if cur["tier"] not in TIERS:
        raise BacklogError(f"tier {cur['tier']!r} must be one of {', '.join(TIERS)}")
    if cur["size"] == "L":
        raise BacklogError("size L is an epic, never ready: split it into S and M items first")
    if cur["size"] not in ("S", "M"):
        raise BacklogError(f"size {cur['size']!r} must be S or M")
    named = {AGENT.lower(): AGENT, HUMAN.lower(): HUMAN}
    if cur["owner"].strip().lower() not in named:
        raise BacklogError(f"owner {cur['owner']!r} must be {AGENT} or {HUMAN}")
    cur["owner"] = named[cur["owner"].strip().lower()]
    keys = [from_inbox] if isinstance(from_inbox, str) else list(from_inbox or [])
    origins = []
    if keys:
        if not new:
            raise BacklogError("--from-inbox only works with --new")
        rng = _section_range(lines, "INBOX")
        taken = set()
        for key in keys:
            hits = [k for k in range(rng[0] + 1, rng[1]) if re.match(r"^\s*[-*]\s*\d{4}-\d{2}-\d{2}", lines[k]) and key.lower() in lines[k].lower()] if rng else []
            if len(hits) != 1:
                raise BacklogError(f"--from-inbox {key!r} matches {len(hits)} INBOX entries, need exactly 1")
            if hits[0] in taken:
                raise BacklogError(f"--from-inbox {key!r} names an INBOX entry another --from-inbox already took")
            taken.add(hits[0])
            origins.append((key, re.sub(r"^\s*[-*]\s*\d{4}-\d{2}-\d{2}:?\s*", "", lines[hits[0]]).strip()))
    tier_line = f"- **Tier / Size / State / Owner:** {cur['tier']} / {cur['size']} / ready / {cur['owner']}"
    pos = 0
    for k, ln in enumerate(base):
        if re.match(r"^- \*\*Tier[^*]*:\*\*", ln):
            base[k] = tier_line
            pos = k + 1
            break
    else:
        base.insert(0, tier_line)
        pos = 1
    has = lambda label: any(re.match(rf"^- \*\*{re.escape(label)}:\*\*", ln) for ln in base)
    pos = _set_field(base, "Added", None if has("Added") else today.isoformat(), pos)
    pos = _set_field(base, "Goal", goal or None, pos)
    pos = _set_field(base, "Acceptance", acceptance or None, pos)
    pos = _set_field(base, "Verify", f"`{verify.strip('`')}`" if verify else None, pos)
    if origins:
        pos = _set_field(base, "Evidence / origin", " ".join(f"Raw: {o}" for _, o in origins), pos)
    if new:
        base.append("- **Depends on / blocks:** none / none.")
    block = [f"### {id_}: {cur['title']}"] + base
    fresh = set()
    if exists and cur["tier"] == exists.section_tier:
        lines[exists.line - 1:exists.end] = block
    else:
        if exists:
            i0 = exists.line - 1
            del lines[i0:exists.end]
            if 0 < i0 < len(lines) and not lines[i0].strip() and not lines[i0 - 1].strip():
                del lines[i0]
            fresh.add(id_)
        rng = _section_range(lines, TIER_SECTION[cur["tier"]])
        if not rng:
            raise BacklogError(f"no section for {cur['tier']}")
        k = rng[1]
        while k > rng[0] + 1 and not lines[k - 1].strip():
            k -= 1
        ins = [""] + block
        if k < len(lines) and lines[k].strip():
            ins.append("")
        lines[k:k] = ins
        fresh.add(id_)
    for key, origin in origins:
        rng = _section_range(lines, "INBOX")
        hit = next(k for k in range(rng[0] + 1, rng[1]) if origin in lines[k] and key.lower() in lines[k].lower())
        del lines[hit]
        if 0 < hit < len(lines) and not lines[hit].strip() and not lines[hit - 1].strip():
            del lines[hit]
    _regen_index(lines, fresh)
    _human_sync(lines, id_, cur["title"], cur["owner"] == HUMAN)
    bad = _new_fails(raw, lines, today)
    if bad:
        raise BacklogError("shape would leave the backlog failing check: " + ", ".join(f"{r} {i}".strip() for r, i in sorted(bad)))
    _write(path, lines, nl)
    msg = f"shaped {id_} ({cur['tier']} / {cur['size']} / ready / {cur['owner']}) in {path}"
    warn = behaviour_warning(cur["goal"], cur["acceptance"])
    return msg + ("\n" + warn if warn else "")


def init_backlog(path):
    path = Path(path)
    if path.exists():
        raise BacklogError(f"{path} exists; init never overwrites")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(TEMPLATE.encode("utf-8"))
    return f"created {path}"


def _default_cwd(path):
    """Directory `close` runs Verify in: the repo root for `docs/IDEAS.md`, else the folder holding the backlog."""
    path = Path(path).resolve()
    return path.parent.parent if path.parent.name == "docs" else path.parent


def close_item(path, id_, sha, summary, evidence="", today=None, history_path=None, cwd=None, old_labels=(), verify_timeout=600):
    today = today or date.today()
    if not SHA_RE.match(sha or ""):
        raise BacklogError(f"sha {sha!r} is not a git commit sha (7 to 40 hex characters)")
    summary = " ".join((summary or "").split())
    if not summary:
        raise BacklogError("close needs --summary")
    path = Path(path)
    raw, nl = _read(path)
    doc = parse(raw)
    it = _find(doc, id_, path)
    verify = it.fields.get("verify", "").strip().strip("`").strip()
    proof = " ".join(evidence.split())
    if verify:
        try:
            r = subprocess.run(verify, shell=True, cwd=str(cwd or _default_cwd(path)), capture_output=True, text=True, timeout=verify_timeout)
        except subprocess.TimeoutExpired:
            raise BacklogError(f"Verify command timed out after {verify_timeout}s: {verify} (raise it with --verify-timeout SECONDS)")
        if r.returncode != 0:
            tail = (r.stdout + r.stderr).strip().splitlines()[-5:]
            raise BacklogError(f"Verify command exited {r.returncode}: {verify}\n" + "\n".join(tail))
        proof = f"Verify `{verify}` exited 0." + (f" {_sentence(proof)}" if proof else "")
    elif not proof:
        raise BacklogError(f"{id_} has no Verify command: pass --evidence saying what proves the acceptance")
    lines = raw.split("\n")
    i0 = it.line - 1
    del lines[i0:it.end]
    if 0 < i0 < len(lines) and not lines[i0].strip() and not lines[i0 - 1].strip():
        del lines[i0]
    rng = _section_range(lines, "INDEX")
    if rng:
        keep = []
        for k in range(rng[0] + 1, rng[1]):
            ln = lines[k]
            if ln.startswith("|") and ln.strip().strip("|").split("|")[0].strip() == id_:
                continue
            keep.append(_strip_id(ln, id_) if ln.startswith("Epics") else ln)
        lines[rng[0] + 1:rng[1]] = keep
    _human_sync(lines, id_, it.title, False)
    bad = _new_fails(raw, lines, today)
    if bad:
        raise BacklogError("close would leave the backlog failing check: " + ", ".join(f"{r} {i}".strip() for r, i in sorted(bad)))
    para = f"Moved from IDEAS.md: {id_} ({it.title}), done in commit {sha}. {_sentence(summary)} {proof}".strip()
    goal = it.fields.get("goal", "")
    if goal:
        para += f" Goal was: {_sentence(goal)}"
    entry = [f"## {today.isoformat()} - Closed: {id_} {it.title}", "", " ".join(para.split()), ""]
    hpath = Path(history_path) if history_path else path.with_name("HISTORY.md")
    if hpath.exists() and hpath.stat().st_size:
        hraw, hnl = _read(hpath)
    else:
        hraw, hnl = "# History\n\n", nl
    hl = hraw.split("\n")
    at = next((k for k, ln in enumerate(hl) if ln.startswith("## ")), None)
    if at is None:
        while hl and not hl[-1].strip():
            hl.pop()
        hl += [""] + entry
    else:
        hl[at:at] = entry
    _write(hpath, hl, hnl)
    _write(path, lines, nl)
    msg = f"closed {id_} in {path}; history entry in {hpath}"
    warns = _old_label_hits(list(old_labels or ()), cwd or _default_cwd(path))
    return "\n".join([msg] + warns)


def _dep_parts(val):
    """(depends_ids, blocks_ids) parsed from a `Depends on / blocks` field value."""
    parts = [p.strip() for p in (val or "").split("/")]
    while len(parts) < 2:
        parts.append("")
    return ID_RE.findall(parts[0]), ID_RE.findall(parts[1])


def _combine_csv(a, b):
    """Comma-separated free text from two fields, concatenated and deduped (case-insensitive), order kept."""
    items = [s.strip() for s in re.split(r",\s*", (a or "").strip()) if s.strip()]
    items += [s.strip() for s in re.split(r",\s*", (b or "").strip()) if s.strip()]
    out = []
    seen = set()
    for x in items:
        if x.lower() not in seen:
            seen.add(x.lower())
            out.append(x)
    return ", ".join(out)


def _edit_epic_id(text, old_id, new_ids):
    """Replace one epic child id with one or more replacement ids, splitting a range if old_id sits inside it
    (same range-membership logic as `_strip_id`, but insert `new_ids` at the gap instead of leaving it empty)."""
    pre, _, suf = old_id.partition("-")
    target = _suffix_val(suf)
    joined = ", ".join(new_ids)

    def rng(m):
        if m.group(2) != pre or target is None:
            return m.group(0)
        lo, hi = _suffix_val(m.group(3)), _suffix_val(m.group(4))
        if lo is None or hi is None or type(lo) is not type(hi) or not lo <= target <= hi or m.group(3).isdigit() != suf.isdigit():
            return m.group(0)
        parts = []
        for a, b in ((lo, target - 1), (target + 1, hi)):
            if a > b:
                continue
            first, last = f"{pre}-{_suffix_str(a, suf)}", f"{pre}-{_suffix_str(b, suf)}"
            parts.append(first if a == b else f"{first} to {last}")
        if len(parts) == 2:
            body = f"{parts[0]}, {joined}, {parts[1]}"
        elif len(parts) == 1:
            body = f"{joined}, {parts[0]}" if lo == target else f"{parts[0]}, {joined}"
        else:
            body = joined
        return (m.group(1) or "") + body + (m.group(5) or "")

    out = RANGE_RE.sub(rng, text)
    lit = re.compile(rf"(?<![\w-])(?<!to ){re.escape(old_id)}(?![\w-])(?! to )")
    return lit.sub(joined, out) if lit.search(out) else out


def _replace_id_in_epics(lines, old_id, new_ids):
    """Replace one epic child id with one or more ids (joined) in every `Epics` line, splitting a range if needed."""
    rng = _section_range(lines, "INDEX")
    if not rng:
        return
    for k in range(rng[0] + 1, rng[1]):
        if lines[k].startswith("Epics"):
            lines[k] = _edit_epic_id(lines[k], old_id, new_ids)


def _dedupe_epic_id(lines, id_):
    """Collapse `id_, id_[, id_...]` runs left by a merge into one occurrence, in every `Epics` line."""
    rng = _section_range(lines, "INDEX")
    if not rng:
        return
    pat = re.compile(rf"\b{re.escape(id_)}\b(\s*,\s*{re.escape(id_)}\b)+")
    for k in range(rng[0] + 1, rng[1]):
        if lines[k].startswith("Epics") and pat.search(lines[k]):
            lines[k] = pat.sub(id_, lines[k])


def move(path, id_, *, before=None, tier=None, today=None):
    today = today or date.today()
    if bool(before) == bool(tier):
        raise BacklogError("move needs exactly one of --before or --tier")
    raw, nl = _read(path)
    lines = raw.split("\n")
    doc = parse(raw)
    it = _find(doc, id_, path)
    if before:
        other = _find(doc, before, path)
        if other.tier != it.tier:
            raise BacklogError(f"--before {before} is in {other.tier}, {id_} is in {it.tier}; move reorders within a tier only, use --tier to change tier")
        a, b = _table_bounds(lines)
        rows = lines[a:b]

        def row_id(ln):
            return ln.strip().strip("|").split("|")[0].strip()

        idx_from = next(k for k, ln in enumerate(rows) if row_id(ln) == id_)
        row = rows.pop(idx_from)
        idx_to = next(k for k, ln in enumerate(rows) if row_id(ln) == before)
        rows.insert(idx_to, row)
        lines[a:b] = rows
        result = f"moved {id_} before {before} in {path}"
    else:
        if tier not in TIERS:
            raise BacklogError(f"tier {tier!r} must be one of {', '.join(TIERS)}")
        if tier == it.tier:
            raise BacklogError(f"{id_} is already in {tier}")
        i0 = it.line - 1
        block = list(lines[i0:it.end])
        for k, ln in enumerate(block):
            if re.match(r"^- \*\*Tier[^*]*:\*\*", ln):
                block[k] = f"- **Tier / Size / State / Owner:** {tier} / {it.size} / {it.state} / {it.owner}"
                break
        del lines[i0:it.end]
        if 0 < i0 < len(lines) and not lines[i0].strip() and not lines[i0 - 1].strip():
            del lines[i0]
        rng = _section_range(lines, TIER_SECTION[tier])
        if not rng:
            raise BacklogError(f"no section for {tier}")
        k = rng[1]
        while k > rng[0] + 1 and not lines[k - 1].strip():
            k -= 1
        ins = [""] + block
        if k < len(lines) and lines[k].strip():
            ins.append("")
        lines[k:k] = ins
        _regen_index(lines, {id_})
        result = f"moved {id_} to {tier} in {path}"
    bad = _new_fails(raw, lines, today)
    if bad:
        raise BacklogError("move would leave the backlog failing check: " + ", ".join(f"{r} {i}".strip() for r, i in sorted(bad)))
    _write(path, lines, nl)
    return result


def split(path, id_, into, today=None):
    """Remove `id_` and file each `into` entry (`id2` or `id2:title`) as its own item in the same tier/section."""
    today = today or date.today()
    if len(into) < 2:
        raise BacklogError("split needs at least 2 children (--into id1[:title1] id2[:title2] ...)")
    children = []
    for token in into:
        cid, _, ctitle = token.partition(":")
        cid = upper_id(cid.strip())
        if not cid.strip():
            raise BacklogError(f"bad --into token {token!r}, want id or id:title")
        children.append((cid, ctitle.strip()))
    seen_new = set()
    for cid, _ in children:
        if cid in seen_new:
            raise BacklogError(f"duplicate new id {cid} in --into")
        seen_new.add(cid)
    raw, nl = _read(path)
    lines = raw.split("\n")
    doc = parse(raw)
    it = _find(doc, id_, path)
    existing_ids = {i.id for i in doc.items}
    for cid, _ in children:
        if cid in existing_ids:
            raise BacklogError(f"{cid} already exists; split needs fresh ids")
    body = list(it.lines[1:])
    i0 = it.line - 1
    del lines[i0:it.end]
    if 0 < i0 < len(lines) and not lines[i0].strip() and not lines[i0 - 1].strip():
        del lines[i0]
    _human_sync(lines, id_, it.title, False)
    _replace_id_in_epics(lines, id_, [cid for cid, _ in children])
    fresh = set()
    for cid, ctitle in children:
        block = [f"### {cid}: {ctitle or it.title}"] + list(body)
        rng = _section_range(lines, TIER_SECTION[it.tier])
        if not rng:
            raise BacklogError(f"no section for {it.tier}")
        k = rng[1]
        while k > rng[0] + 1 and not lines[k - 1].strip():
            k -= 1
        ins = [""] + block
        if k < len(lines) and lines[k].strip():
            ins.append("")
        lines[k:k] = ins
        fresh.add(cid)
        if it.owner == HUMAN:
            _human_sync(lines, cid, ctitle or it.title, True)
    _regen_index(lines, fresh)
    bad = _new_fails(raw, lines, today)
    if bad:
        raise BacklogError("split would leave the backlog failing check: " + ", ".join(f"{r} {i}".strip() for r, i in sorted(bad)))
    _write(path, lines, nl)
    return f"split {id_} into {', '.join(cid for cid, _ in children)} in {path}"


def merge(path, id_, id2, *, goal=None, acceptance=None, today=None):
    """Fold `id2` into `id_`: Depends and Pointers combined and deduped, id2 removed, its epic references repointed."""
    today = today or date.today()
    if id_ == id2:
        raise BacklogError("merge needs two different ids")
    raw, nl = _read(path)
    lines = raw.split("\n")
    doc = parse(raw)
    it = _find(doc, id_, path)
    it2 = _find(doc, id2, path)
    if it.tier != it2.tier:
        raise BacklogError(f"{id_} is {it.tier}, {id2} is {it2.tier}; merge only works within one tier")
    dep1, blk1 = _dep_parts(it.fields.get("depends", ""))
    dep2, blk2 = _dep_parts(it2.fields.get("depends", ""))
    deps = [d for d in dict.fromkeys(dep1 + dep2) if d not in (id_, id2)]
    blks = [b for b in dict.fromkeys(blk1 + blk2) if b not in (id_, id2)]
    dep_val = f"{', '.join(deps) if deps else 'none'} / {', '.join(blks) if blks else 'none'}."
    pointers = _combine_csv(it.fields.get("pointers", ""), it2.fields.get("pointers", ""))
    body = list(it.lines[1:])

    def set_field(label, value):
        pat = re.compile(rf"^- \*\*{re.escape(label)}:\*\*")
        for k, ln in enumerate(body):
            if pat.match(ln):
                body[k] = f"- **{label}:** {value}"
                return
        body.append(f"- **{label}:** {value}")

    set_field("Depends on / blocks", dep_val)
    if pointers:
        set_field("Pointers", pointers)
    if goal:
        set_field("Goal", _sentence(goal))
    if acceptance:
        set_field("Acceptance", _sentence(acceptance))
    kept = [f"{k} {it2.fields[k]}" for k in ("goal", "acceptance", "evidence") if it2.fields.get(k) and it2.fields[k] != it.fields.get(k)]
    if kept:
        note = " ".join(_sentence(f"Merged from {id2}: {' | '.join(kept)}").split())
        old = it.fields.get("evidence", "")
        set_field("Evidence / origin", f"{old} {note}".strip())
    i0 = it.line - 1
    lines[i0:it.end] = [f"### {id_}: {it.title}"] + body
    doc2 = parse("\n".join(lines))
    it2b = _find(doc2, id2, path)
    j0 = it2b.line - 1
    del lines[j0:it2b.end]
    if 0 < j0 < len(lines) and not lines[j0].strip() and not lines[j0 - 1].strip():
        del lines[j0]
    _replace_id_in_epics(lines, id2, [id_])
    _dedupe_epic_id(lines, id_)
    _human_sync(lines, id2, it2.title, False)
    _regen_index(lines)
    bad = _new_fails(raw, lines, today)
    if bad:
        raise BacklogError("merge would leave the backlog failing check: " + ", ".join(f"{r} {i}".strip() for r, i in sorted(bad)))
    _write(path, lines, nl)
    return f"merged {id2} into {id_} in {path}"


def _norm_path(s):
    """Path from a CLI string: quotes stripped, ~ expanded, and Git Bash `/c/...` mapped to `C:/...` on Windows."""
    s = str(s).strip().strip('"')
    m = re.match(r"^/([a-zA-Z])(/.*)?$", s) if os.name == "nt" else None
    if m:
        s = f"{m.group(1).upper()}:{m.group(2) or '/'}"
    return Path(os.path.expanduser(s))


def resolve_repo(name, base=None, locations=None):
    """First existing path among the configured `locations` templates, `{repo}` replaced by `name`, relative to `base`."""
    base = Path(base) if base else BASE_DIR
    tried = [(base / loc.replace("{repo}", name)) for loc in (locations or CONFIG["locations"])]
    for cand in tried:
        if cand.exists():
            return cand.resolve()
    raise BacklogError(f"no backlog for repo {name!r}: looked at " + " and ".join(str(t) for t in tried))


def all_backlogs(base=None, locations=None):
    base = Path(base) if base else BASE_DIR
    found = []
    for loc in (locations or CONFIG["locations"]):
        found += sorted(Path(p).resolve() for p in glob.glob(str(base / loc.replace("{repo}", "*"))) if Path(p).is_file())
    return list(dict.fromkeys(found))


def _target(args):
    if getattr(args, "file", None):
        return _norm_path(args.file)
    if getattr(args, "repo", None):
        return _norm_path(args.repo) if _norm_path(args.repo).is_file() else resolve_repo(args.repo)
    raise BacklogError("give a <repo> or --file PATH")


def main(argv=None):
    # A legacy console encoding (cp1252) must not crash printing backlog text that holds an emoji.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(prog="backlog.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("check", "status"):
        p = sub.add_parser(name)
        p.add_argument("repo", nargs="?")
        p.add_argument("--file")
        p.add_argument("--json", action="store_true")
        if name == "check":
            p.add_argument("--all", action="store_true")
    p = sub.add_parser("add")
    p.add_argument("repo_or_text", nargs="+")
    p.add_argument("--file")
    p.add_argument("--force", action="store_true")
    for name in ("close", "next", "brief", "shape", "init", "move", "split", "merge"):
        p = sub.add_parser(name)
        p.add_argument("parts", nargs="*")
        p.add_argument("--file")
        if name == "close":
            p.add_argument("--sha", required=True)
            p.add_argument("--summary", required=True)
            p.add_argument("--evidence", default="")
            p.add_argument("--cwd")
            p.add_argument("--verify-timeout", dest="verify_timeout", type=int, default=600)
            p.add_argument("--old-label", dest="old_label", action="append", default=[])
        if name == "next":
            p.add_argument("--owner", default=AGENT)
        if name == "shape":
            p.add_argument("--new", action="store_true")
            p.add_argument("--from-inbox", dest="from_inbox", action="append")
            for f in ("title", "tier", "size", "goal", "acceptance", "owner", "verify"):
                p.add_argument("--" + f)
        if name == "move":
            p.add_argument("--before")
            p.add_argument("--tier")
        if name == "split":
            p.add_argument("--into", nargs="+", required=True)
        if name == "merge":
            p.add_argument("--goal")
            p.add_argument("--acceptance")
    args = ap.parse_args(argv)
    try:
        if args.cmd in ("close", "next", "brief", "shape", "init", "move", "split", "merge"):
            want = 0 if args.cmd in ("next", "init") else (2 if args.cmd == "merge" else 1)
            parts = list(args.parts)
            if args.file:
                path = _norm_path(args.file)
            elif len(parts) == want + 1:
                if _norm_path(parts[0]).is_file():
                    path = _norm_path(parts[0])
                elif args.cmd == "init":
                    path = BASE_DIR / CONFIG["locations"][0].replace("{repo}", parts[0])
                else:
                    path = resolve_repo(parts[0])
                parts = parts[1:]
            else:
                usage_id = " <id> <id2>" if want == 2 else (" <id>" if want else "")
                raise BacklogError(f"usage: {args.cmd} (<repo> | --file PATH)" + usage_id)
            if len(parts) != want:
                raise BacklogError(f"{args.cmd} takes {'no id' if not want else ('an <id>' if want == 1 else 'two ids')}")
            if args.cmd == "init":
                print(init_backlog(path))
            elif args.cmd == "next":
                it = next_item(parse(path.read_text(encoding="utf-8")), owner=args.owner)
                print("\n".join(it.lines) if it else f"no unblocked ready item for {args.owner}")
            elif args.cmd == "brief":
                print(brief(parse(path.read_text(encoding="utf-8")), parts[0]))
            elif args.cmd == "close":
                print(close_item(path, parts[0], args.sha, args.summary, evidence=args.evidence, cwd=_norm_path(args.cwd) if args.cwd else None, old_labels=args.old_label, verify_timeout=args.verify_timeout))
            elif args.cmd == "move":
                print(move(path, parts[0], before=args.before, tier=args.tier))
            elif args.cmd == "split":
                print(split(path, parts[0], args.into))
            elif args.cmd == "merge":
                print(merge(path, parts[0], parts[1], goal=args.goal, acceptance=args.acceptance))
            else:
                fields = {f: getattr(args, f) for f in ("title", "tier", "size", "goal", "acceptance", "owner", "verify")}
                if args.new or args.from_inbox or any(fields.values()):
                    print(shape(path, parts[0], new=args.new, from_inbox=args.from_inbox, **fields))
                else:
                    for ok, text in shape_checklist(parse(path.read_text(encoding="utf-8")), parts[0]):
                        print(f"[{'x' if ok else ' '}] {text}")
            return 0
        if args.cmd == "add":
            parts = args.repo_or_text
            if args.file:
                path, text = _norm_path(args.file), " ".join(parts)
            else:
                if len(parts) < 2:
                    raise BacklogError('usage: add <repo> "raw words" (or --file PATH "raw words")')
                path, text = resolve_repo(parts[0]), " ".join(parts[1:])
            print(add(path, text, force=args.force))
            return 0
        many = args.cmd == "check" and args.all
        result, bad, skipped = check_many(all_backlogs() if many else [_target(args)], skip_unformatted=many)
        for p in skipped:
            print(f"{p}: SKIP not in the strict format (no INDEX section), not checked", file=sys.stderr)
        if args.cmd == "status":
            (path, (doc, fs)), = result.items()
            if args.json:
                print(json.dumps({**status(doc), "findings": [f.as_dict() for f in fs]}))
            else:
                print(render_status(Path(path).parent.name if Path(path).parent.name != "docs" else Path(path).parent.parent.name, doc, fs))
            return 0
        if args.json:
            flat = [dict(f.as_dict(), file=p) for p, (_, fs) in result.items() for f in fs]
            print(json.dumps({"ok": not bad, "findings": flat}))
        else:
            for p, (_, fs) in result.items():
                for f in fs:
                    print(f"{p}:{f.line}: {f.level.upper()} {f.rule} {f.id} {f.msg}")
            print("backlog check:", "FAIL" if bad else "ok")
        return 1 if bad else 0
    except (BacklogError, FileNotFoundError, PermissionError) as e:
        print(f"backlog.py: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
