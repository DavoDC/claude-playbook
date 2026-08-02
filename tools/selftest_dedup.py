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


# Lines that are pure structure and carry no prose of their own - blanked
# entirely. Matched against the STRIPPED line, so leading indentation (nested
# lists, indented code) does not defeat the match.
_HRULE_RE = re.compile(r"^([-*_])\s*(?:\1\s*){2,}$")
_HEADING_RE = re.compile(r"^#{1,6}(?:\s|$)")
_TABLE_OR_QUOTE_RE = re.compile(r"^[|>]")

# List markers: bullet (-, *, +) or ordinal (1. / 1)) followed by whitespace.
# Requiring the trailing whitespace is what keeps this from also matching
# "**bold**" - a line starting with emphasis has no space after the first
# "*", so it is prose and falls through untouched instead of being blanked.
_LIST_MARKER_RE = re.compile(r"^(?:[-*+]|\d+[.)])\s+(.*)$")
# A markdown checkbox immediately after the list marker is also structure,
# not prose - stripped separately so "- [ ] Do the thing" contributes "Do
# the thing" rather than "[ ] Do the thing".
_CHECKBOX_RE = re.compile(r"^\[[ xX]\]\s*")


def _declassify_line(line):
    """Return the prose contribution of one line: None to blank it entirely,
    or the text to keep (marker stripped for list items, unchanged
    otherwise)."""
    stripped = line.strip()
    if _HRULE_RE.match(stripped):
        return None
    if _HEADING_RE.match(stripped):
        return None
    if _TABLE_OR_QUOTE_RE.match(stripped):
        return None
    m = _LIST_MARKER_RE.match(stripped)
    if m:
        item = _CHECKBOX_RE.sub("", m.group(1)).rstrip()
        # Force a sentence boundary at the end of each list item. Without
        # this, an item that does not itself end in punctuation (common in
        # short checklist entries and numbered steps) bleeds into whatever
        # line follows it once markers are no longer blanking the line, and
        # two files that happen to share a run of short list items can then
        # be reported as sharing one long welded "sentence" that never
        # existed as a unit in either source - the same false-boundary
        # failure mode the numbered-marker defect produced, in a new spot.
        if item and item[-1] not in ".!?":
            item += "."
        return item
    return line


def sentences(text):
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = "\n".join(
        contribution
        for contribution in (_declassify_line(line) for line in text.split("\n"))
        if contribution is not None
    )
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
    files_scanned = 0
    units_compared = 0
    for path in find_md_files(root):
        files_scanned += 1
        rel = os.path.relpath(path, root).replace("\\", "/")
        with open(path, encoding="utf-8", errors="replace") as fh:
            for s in sentences(fh.read()):
                units_compared += 1
                h = hashlib.sha1(s.lower().encode()).hexdigest()
                seen.setdefault(h, [s, []])[1].append(rel)

    # Coverage figure, printed on both pass and fail: the raw pair of how
    # many analysable units were compared and how many files they were drawn
    # from. A verdict without this cannot be told apart from one that
    # examined almost nothing and found nothing - which is exactly what let
    # a real duplicate sit undetected before this script's line-blanking was
    # fixed. A raw pair invites the question "is that enough files/units?";
    # a percentage would invite a target instead.
    coverage = f"coverage: {units_compared} sentence(s) compared / {files_scanned} file(s) scanned"

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
        print(f"OK: no unscoped sentence of {MIN_WORDS}+ words appears twice{extra}. root={root} {coverage}")
        return 0

    print(f"FAIL: {len(dups)} duplicated passage(s). root={root} {coverage}")
    for s, paths in dups:
        print(f"  in {', '.join(paths)}:")
        print(f"    {s[:200]}")
    return 1


if __name__ == "__main__":
    default_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else default_root))
