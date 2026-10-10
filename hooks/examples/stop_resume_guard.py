#!/usr/bin/env python3
"""Stop hook: block a turn that printed a line starting `RESUME:` but never scheduled the resume.

Your budget script prints `RESUME: ...` when usage is high. If, after the last real user message,
such a line appears in a tool result and no one-shot schedule (CronCreate with recurring false, or
ScheduleWakeup) follows it, the stop is blocked with an instruction. stop_hook_active true always
allows the stop, so this cannot loop. Fails open.
"""
import json
import re
import sys

RESUME = re.compile(r"^RESUME:.*$", re.MULTILINE)


def content(e):
    m = e.get("message")
    return m.get("content") if isinstance(m, dict) else None


def real_user(e):
    if e.get("type") != "user" or e.get("isMeta"):
        return False
    c = content(e)
    if isinstance(c, str):
        return True
    return isinstance(c, list) and not any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c)


def text(b):
    c = b.get("content")
    if isinstance(c, str):
        return c
    return "\n".join(x.get("text", "") for x in c if isinstance(x, dict)) if isinstance(c, list) else ""


def scheduled(b):
    if b.get("name") == "ScheduleWakeup":
        return True
    inp = b.get("input")
    return b.get("name") == "CronCreate" and isinstance(inp, dict) and inp.get("recurring") is False


def unscheduled(entries):
    start = 0
    for i, e in enumerate(entries):
        if real_user(e):
            start = i + 1
    line = None
    for e in entries[start:]:
        c = content(e)
        for b in c if isinstance(c, list) else []:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_result":
                m = RESUME.search(text(b))
                if m:
                    line = m.group(0)
            elif b.get("type") == "tool_use" and line and scheduled(b):
                line = None
    return line


def main():
    try:
        p = json.load(sys.stdin)
        if p.get("stop_hook_active"):
            return 0
        entries = []
        with open(p["transcript_path"], encoding="utf-8", errors="replace") as f:
            for ln in f:
                try:
                    e = json.loads(ln)
                except ValueError:
                    continue
                if isinstance(e, dict):
                    entries.append(e)
        line = unscheduled(entries)
        if line:
            reason = ("A budget RESUME line was printed but the resume was never scheduled: " + line +
                      "\nSchedule a one-shot resume (CronCreate recurring=false or ScheduleWakeup) with a prompt that continues the paused work, then stop.")
            print(json.dumps({"decision": "block", "reason": reason}))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
