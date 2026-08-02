#!/usr/bin/env python3
"""Assertion: no long sentence appears in two places in the repo, except a
short list of deliberately-scoped exceptions.

Prose is where the single-source rule actually breaks: a correction lands in
one copy while another quietly keeps the old wording. This walks every .md
file, splits it into sentences, and flags any sentence of MIN_WORDS or more
that appears (case-insensitively, whitespace-normalized) in more than one
file - or twice in the same file.

Scoped allow list: a bare substring allow list is a blind spot - clearing a
sentence once silences it everywhere forever, including a genuinely
accidental third copy added later for an unrelated reason. Each ALLOW entry
instead names the exact, closed set of files the repetition is cleared
between, plus a mandatory reason. A duplicate is let through only when every
file it was actually found in is a subset of that entry's file set. The same
sentence turning up in any file outside that set still fails - the entry
does not grow to cover it.
"""
import hashlib
import os
import re
import sys

MIN_WORDS = 14

# Each entry: sentence substring to match, the closed set of files the
# repetition is cleared between (repo-relative, forward slashes), and the
# reason it is a deliberate restatement rather than an unfixed defect. Every
# field is required by construction (ALLOW is a list of 3-tuples) so an
# entry can't be added without a reason.
ALLOW = [
    (
        "Cheapest step in the process and the only one that improves items you are not touching.",
        frozenset({"docs/12-audit-lenses.md", "skills/deep-dive/SKILL.md"}),
        "skills/deep-dive/SKILL.md restates the audit-lenses closing "
        "re-rank line so someone reading the skill standalone gets the "
        "point without also opening the chapter it points at.",
    ),
    (
        "Grep the backlog for a distinctive phrase from each finding rather than trusting recall.",
        frozenset({"docs/12-audit-lenses.md", "skills/deep-dive/SKILL.md"}),
        "skills/deep-dive/SKILL.md restates the audit-lenses backlog-dedup "
        "instruction for the same standalone-reading reason as the entry "
        "above.",
    ),
]


def sentences(text):
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"^\s*[|>#\-*].*$", " ", text, flags=re.M)
    for s in re.split(r"(?<=[.!?])\s+", text):
        s = " ".join(s.split())
        if len(s.split()) >= MIN_WORDS:
            yield s


def find_md_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules")]
        for fn in sorted(filenames):
            if fn.endswith(".md"):
                yield os.path.join(dirpath, fn)


def allow_entry_for(sentence):
    """Return the ALLOW entry whose substring matches this sentence, or
    None. First match wins - entries are not expected to overlap."""
    for allowed_substr, files, reason in ALLOW:
        if allowed_substr in sentence:
            return allowed_substr, files, reason
    return None


def main(root):
    seen = {}
    for path in find_md_files(root):
        rel = os.path.relpath(path, root).replace("\\", "/")
        with open(path, encoding="utf-8", errors="replace") as fh:
            for s in sentences(fh.read()):
                h = hashlib.sha1(s.lower().encode()).hexdigest()
                seen.setdefault(h, [s, []])[1].append(rel)

    dups = []
    cleared = []
    for h, (s, paths) in seen.items():
        uniq = sorted(set(paths))
        occurrences = uniq if len(uniq) > 1 else [paths[0] + " (twice)"]
        if len(paths) <= 1:
            continue

        entry = allow_entry_for(s)
        if entry is not None:
            _substr, allowed_files, reason = entry
            if set(uniq).issubset(allowed_files):
                cleared.append((s, occurrences, reason))
                continue
            # Matches an allow-list sentence but shows up outside the
            # files that entry cleared - e.g. a third file. The entry
            # does not extend to cover this; it still fails.

        dups.append((s, occurrences))

    if not dups:
        extra = f" ({len(cleared)} scoped exception(s) applied)" if cleared else ""
        print(f"OK: no unscoped sentence of {MIN_WORDS}+ words appears twice{extra}.")
        return 0

    print(f"FAIL: {len(dups)} duplicated passage(s).")
    for s, paths in dups:
        print(f"  in {', '.join(paths)}:")
        print(f"    {s[:200]}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
