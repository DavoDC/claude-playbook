#!/usr/bin/env python3
"""Tests for shorthand_detector.py against the shipped templates/shorthand-glossary.md.

Exit 0 only if every case behaves as expected. Includes a control: the same prompt run against a
glossary with no terms must produce nothing, proving a hit comes from the glossary and not from the
script. Prints one PASS line, or the failing cases.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "shorthand_detector.py")
TEMPLATE = os.path.join(HERE, "..", "..", "templates", "shorthand-glossary.md")


def run(prompt, glossary, state, raw=None):
    env = dict(os.environ, SHORTHAND_GLOSSARY=glossary, SHORTHAND_STATE_DIR=state)
    data = raw if raw is not None else json.dumps({"prompt": prompt})
    p = subprocess.run([sys.executable, SCRIPT], input=data, capture_output=True, text=True, env=env, timeout=20)
    return p.returncode, p.stdout


def context(out):
    return json.loads(out)["hookSpecificOutput"]["additionalContext"] if out.strip() else ""


def main():
    fails = []

    def expect(name, got, want):
        if got != want:
            fails.append("%s: got %r, wanted %r" % (name, got, want))

    with tempfile.TemporaryDirectory() as d:
        empty = os.path.join(d, "empty.md")
        open(empty, "w").write("# no terms here\n")
        state = os.path.join(d, "state")
        os.makedirs(state)

        code, out = run("please QUAD this", TEMPLATE, state)
        expect("hit exits 0", code, 0)
        expect("hit injects the term", "[SHORTHAND] QUAD:" in context(out), True)
        expect("case-insensitive hit", "[SHORTHAND] QUAD:" in context(run("quad now", TEMPLATE, state)[1]), True)
        expect("no term is silent", run("fix the bug please", TEMPLATE, state)[1], "")
        expect("substring does not match", run("the quadrant is wrong", TEMPLATE, state)[1], "")
        expect("pasted block ignored", run("<pasted_content id=1>QUAD</pasted_content> hi", TEMPLATE, state)[1], "")
        expect("fenced code ignored", run("log:\n```\nQUAD\n```\n", TEMPLATE, state)[1], "")
        expect("harness frame ignored", run("<system-reminder>QUAD</system-reminder>", TEMPLATE, state)[1], "")
        both = context(run("BLUF and OSTP", TEMPLATE, state)[1])
        expect("two terms in one prompt", "BLUF:" in both and "OSTP:" in both, True)
        expect("same term twice is one note", context(run("QUAD quad", TEMPLATE, state)[1]).count("QUAD:"), 1)
        first = context(run("do it one step at a time", TEMPLATE, state)[1])
        expect("alias gives a tip", "[SHORTHAND TIP]" in first and "OSTP" in first, True)
        expect("tip is capped to once a day", run("do it one step at a time", TEMPLATE, state)[1], "")
        code, out = run(None, TEMPLATE, state, raw="not json")
        expect("malformed payload exits 0", (code, out), (0, ""))
        code, out = run("QUAD", os.path.join(d, "missing.md"), state)
        expect("missing glossary fails open", (code, out), (0, ""))
        expect("control: empty glossary is silent", run("please QUAD this", empty, state)[1], "")

    with open(TEMPLATE, encoding="utf-8") as f:
        text = f.read()
    block = re.search(r"```glossary\n(.*?)```", text, re.DOTALL)
    rows = [l for l in (block.group(1).splitlines() if block else []) if l.strip()]
    expect("template has rows", len(rows) >= 3, True)
    expect("template carries QUAD", any(r.startswith("QUAD|") for r in rows), True)
    for r in rows:
        parts = r.split("|")
        expect("template row has 3 or 4 fields: " + parts[0], len(parts) in (3, 4), True)
        expect("template term is acronym-shaped: " + parts[0], bool(re.fullmatch(r"[A-Z][A-Za-z0-9]{2,7}", parts[0])), True)

    for f in fails:
        print("FAIL:", f)
    print("shorthand-detector:", "FAIL" if fails else "PASS (%d template rows)" % len(rows))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
