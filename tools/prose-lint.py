#!/usr/bin/env python3
"""Lint prose files and commit messages for three shape rules.

Rules:
  hardwrap  a paragraph broken across lines (two adjacent short prose lines with no blank between)
  dash      an em dash or en dash character
  subject   (commit messages only) the subject is over --subject-max chars, or line 2 is not blank

Hard wrapping is the shape most editors and GitHub's description box render as ragged fragments;
dashes are a house-style choice the config of doc_lint.py enforces for docs, and this script
enforces it for files and messages that lint does not walk. Comment lines (starting with #),
git trailers (Key: value) and fenced code are exempt where they would be false positives.

Usage:
  prose-lint.py FILE [FILE ...]            lint markdown/text files (hardwrap, dash)
  prose-lint.py --commit-msg MSGFILE       lint a commit message (subject, hardwrap, dash)
  prose-lint.py --selftest
Options: --subject-max N (default 72), --no-dash to skip the dash rule.
Exit codes: 0 clean, 1 findings, 2 usage or unreadable file.
Wiring a git commit-msg hook is shown in docs/24-config-driven-doc-linting.md.
"""
import argparse
import re
import sys
import tempfile
from pathlib import Path

EM, EN = chr(0x2014), chr(0x2013)
DASHES = EM + EN
LIST_RE = re.compile(r"^\s*([-*+]|\d+[.)])\s")
TRAILER_RE = re.compile(r"^[A-Za-z][A-Za-z-]*:\s")
BOLD_RE = re.compile(r"^\s*\*\*[^*]+\*\*\.?\s*$")
HR_RE = re.compile(r"^\s*([-*_])\1{2,}\s*$")
SHORT = 100


def exempt(s, second=False):
    if not s.strip() or re.match(r"^\s{0,3}#", s) or s.lstrip().startswith(">"):
        return True
    if HR_RE.match(s) or "|" in s or BOLD_RE.match(s) or s.endswith("  "):
        return True
    return bool(second and LIST_RE.match(s))


def hardwrap_hits(lines):
    """1-indexed line numbers where line and the next one look like a wrapped paragraph."""
    start = 0
    if lines and lines[0].rstrip("\n") == "---":
        for i in range(1, len(lines)):
            if lines[i].rstrip("\n") == "---":
                start = i + 1
                break
    hits, fence = [], False
    for i in range(start, len(lines) - 1):
        a, b = lines[i].rstrip("\n"), lines[i + 1].rstrip("\n")
        if a.strip().startswith("```"):
            fence = not fence
            continue
        if fence or b.strip().startswith("```"):
            continue
        if exempt(a) or exempt(b, second=True):
            continue
        if len(a) < SHORT and len(b) < SHORT:
            hits.append(i + 1)
    return hits


def dash_hits(lines):
    fence, out = False, []
    for n, line in enumerate(lines, 1):
        if line.strip().startswith("```"):
            fence = not fence
        if not fence and any(c in line for c in DASHES):
            out.append(n)
    return out


def lint_text(text, dash=True):
    lines = [l + "\n" for l in text.replace("\r\n", "\n").split("\n")]
    found = [("hardwrap", n) for n in hardwrap_hits(lines)]
    if dash:
        found += [("dash", n) for n in dash_hits(lines)]
    return found


def lint_commit(msg, subject_max=72, dash=True):
    lines = [l for l in msg.replace("\r\n", "\n").split("\n") if not l.startswith("#")]
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines:
        return []
    found = []
    if len(lines[0]) > subject_max:
        found.append(("subject", "1: %d chars, max %d" % (len(lines[0]), subject_max)))
    if len(lines) > 1 and lines[1].strip():
        found.append(("subject", "2: line 2 must be blank"))
    body = [l for l in lines[1:] if not TRAILER_RE.match(l)]
    found += lint_text("\n".join(body), dash)
    if dash and any(c in lines[0] for c in DASHES):
        found.append(("dash", "1: subject"))
    return found


def selftest():
    wrapped = "This paragraph is broken\nacross two short lines.\n"
    assert lint_text(wrapped) == [("hardwrap", 1)], lint_text(wrapped)
    assert lint_text("One long line.\n\n- item one\n- item two\n\n| a | b |\n| c | d |\n") == []
    assert lint_text("```\nshort\nshort\n```\n") == []
    assert lint_text("A dash %s here.\n" % EM) == [("dash", 1)]
    assert lint_text("A dash %s here.\n" % EN, dash=False) == []
    assert lint_commit("Fix the parser\n\nBody in one line.\n") == []
    assert lint_commit("x" * 73 + "\n")[0][0] == "subject"
    assert lint_commit("Subject\nnot blank\n")[0] == ("subject", "2: line 2 must be blank")
    assert lint_commit("Subject\n\nfirst short line\nsecond short line\n")[0][0] == "hardwrap"
    assert lint_commit("Subject\n\nOne line.\n\nCo-Authored-By: A <a@b>\nSigned-off-by: A\n") == []
    assert lint_commit("# comment only\n") == []
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "a.md"
        f.write_text(wrapped, encoding="utf-8")
        assert main([str(f)]) == 1
        f.write_text("Clean line.\n", encoding="utf-8")
        assert main([str(f)]) == 0
        assert main([str(Path(d) / "missing.md")]) == 2
    print("selftest: PASS")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("files", nargs="*")
    ap.add_argument("--commit-msg")
    ap.add_argument("--subject-max", type=int, default=72)
    ap.add_argument("--no-dash", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        selftest()
        return 0
    if not a.files and not a.commit_msg:
        ap.print_usage(sys.stderr)
        return 2
    bad = 0
    try:
        if a.commit_msg:
            text = Path(a.commit_msg).read_text(encoding="utf-8", errors="replace")
            for rule, where in lint_commit(text, a.subject_max, not a.no_dash):
                print("%s: %s: %s" % (a.commit_msg, rule, where))
                bad = 1
        for f in a.files:
            text = Path(f).read_text(encoding="utf-8", errors="replace")
            for rule, line in lint_text(text, not a.no_dash):
                print("%s:%s: %s" % (f, line, rule))
                bad = 1
    except OSError as e:
        print("cannot read: %s" % e, file=sys.stderr)
        return 2
    return bad


if __name__ == "__main__":
    sys.exit(main())
