#!/usr/bin/env python3
"""UserPromptSubmit: inject the definition of any shorthand term typed in a prompt.

The data lives in one glossary file (see templates/shorthand-glossary.md); this script only
matches and injects, so adding a term never means editing code. A term is matched whole-word and
case-insensitively against what the user typed, after pasted and fenced-code blocks and
harness-injected frames are ignored. A hit adds a one-line [SHORTHAND] note as additionalContext.
If a long-form alias appears without the short term, one [SHORTHAND TIP] per term per day suggests
the short form. Advisory only: it fails open and ALWAYS exits 0, because a UserPromptSubmit hook
that exits 2 erases the user's prompt.

Settings: SHORTHAND_GLOSSARY (path to the glossary file; default
$CLAUDE_PROJECT_DIR/.claude/shorthand-glossary.md), SHORTHAND_STATE_DIR (where the once-a-day tip
markers go; default the system temp dir).
"""
import datetime
import json
import os
import re
import sys
import tempfile

FENCE_RE = re.compile(r"```glossary\r?\n(.*?)```", re.DOTALL)
IGNORED_RE = re.compile(r"<pasted_content[^>]*>.*?</pasted_content[^>]*>|```.*?```", re.IGNORECASE | re.DOTALL)
FRAME_MARKERS = ("<system-reminder", "<task-notification", "<agent-message", "[system notification", "<wake reason=")


def parse_glossary(text):
    """Return (term, definition, source, aliases) rows from the fenced glossary block, or []."""
    m = FENCE_RE.search(text)
    if not m:
        return []
    rows = []
    for line in m.group(1).splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3 or not parts[0]:
            continue
        aliases = [a.strip() for a in parts[3].split(",") if a.strip()] if len(parts) > 3 else []
        rows.append((parts[0], parts[1], parts[2], aliases))
    return rows


def word_re(phrase):
    return re.compile(r"(?<![A-Za-z0-9_])" + re.escape(phrase) + r"(?![A-Za-z0-9_])", re.IGNORECASE)


def tip_due(term):
    """True the first time a tip for this term is due today; records it so the cap holds."""
    state = os.environ.get("SHORTHAND_STATE_DIR") or tempfile.gettempdir()
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", term)
    marker = os.path.join(state, "shorthand-tip-%s-%s" % (safe, datetime.date.today().isoformat()))
    if os.path.exists(marker):
        return False
    try:
        open(marker, "w").write("1")
    except OSError:
        return False
    return True


def main():
    try:
        prompt = json.load(sys.stdin).get("prompt", "")
        if not isinstance(prompt, str) or not prompt:
            return 0
        if any(marker in prompt.strip()[:200].lower() for marker in FRAME_MARKERS):
            return 0
        default = os.path.join(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd(), ".claude", "shorthand-glossary.md")
        with open(os.environ.get("SHORTHAND_GLOSSARY") or default, encoding="utf-8", errors="replace") as f:
            rows = parse_glossary(f.read())
        typed = IGNORED_RE.sub(" ", prompt)
        notes, seen = [], set()
        for term, definition, source, aliases in rows:
            if term.upper() in seen:
                continue
            if word_re(term).search(typed):
                seen.add(term.upper())
                notes.append("[SHORTHAND] %s: %s (source: %s)" % (term, definition, source))
                continue
            for alias in aliases:
                if word_re(alias).search(typed):
                    if tip_due(term):
                        seen.add(term.upper())
                        notes.append('[SHORTHAND TIP] You wrote "%s" - next time you can just type %s.' % (alias, term))
                    break
        if notes:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "\n".join(notes)}}))
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
