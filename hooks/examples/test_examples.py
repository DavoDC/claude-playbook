#!/usr/bin/env python3
"""Run every example hook against sample payloads. Exit 0 only if all cases behave as expected.

Includes a POSITIVE CONTROL: a case whose expectation is deliberately wrong must be reported as a
mismatch, proving the runner can fail.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def run(script, payload, env_extra=None, raw=None):
    env = dict(os.environ, **(env_extra or {}))
    data = raw if raw is not None else json.dumps(payload)
    p = subprocess.run([sys.executable, os.path.join(HERE, script)], input=data, capture_output=True, text=True, env=env, timeout=20)
    return p.returncode, p.stdout, p.stderr


def main():
    fails = []
    with tempfile.TemporaryDirectory() as d:
        big = os.path.join(d, "big.txt")
        small = os.path.join(d, "small.txt")
        open(big, "w").write("x" * 5000)
        open(small, "w").write("x")
        env = {"READ_GUARD_MAX_BYTES": "1000", "EDIT_TRIPWIRE_STATE_DIR": d, "EDIT_TRIPWIRE_N": "2", "CONVENTION_REMINDER_STATE_DIR": d}

        def expect(name, got, want):
            if got != want:
                fails.append(f"{name}: got {got!r}, wanted {want!r}")

        expect("read big denied", run("read_size_guard.py", {"tool_name": "Read", "tool_input": {"file_path": big}}, env)[0], 2)
        expect("read big with limit allowed", run("read_size_guard.py", {"tool_name": "Read", "tool_input": {"file_path": big, "limit": 10}}, env)[0], 0)
        expect("read small allowed", run("read_size_guard.py", {"tool_name": "Read", "tool_input": {"file_path": small}}, env)[0], 0)
        expect("read malformed fails open", run("read_size_guard.py", None, env, raw="not json")[0], 0)
        expect("bash noisy denied", run("bash_output_cap.py", {"tool_name": "Bash", "tool_input": {"command": "pip list"}})[0], 2)
        expect("bash noisy with head allowed", run("bash_output_cap.py", {"tool_name": "Bash", "tool_input": {"command": "pip list | head -20"}})[0], 0)
        expect("bash quiet allowed", run("bash_output_cap.py", {"tool_name": "Bash", "tool_input": {"command": "ls"}})[0], 0)
        ed = {"tool_name": "Edit", "session_id": "s1", "tool_input": {"file_path": "a.py"}}
        expect("edit 1 silent", run("edit_without_agent_tripwire.py", ed, env)[1], "")
        expect("edit 2 nudges", "additionalContext" in run("edit_without_agent_tripwire.py", ed, env)[1], True)
        expect("edit 3 silent", run("edit_without_agent_tripwire.py", ed, env)[1], "")
        cr = {"tool_name": "Read", "session_id": "s1", "tool_input": {"file_path": "/x/CLAUDE.md"}}
        expect("convention first time", "allow" in run("convention_reminder.py", cr, env)[1], True)
        expect("convention second time silent", run("convention_reminder.py", cr, env)[1], "")
        expect("convention other file silent", run("convention_reminder.py", {"tool_name": "Read", "tool_input": {"file_path": "/x/a.txt"}}, env)[1], "")
        tr = os.path.join(d, "t.jsonl")
        rows = [
            {"type": "user", "message": {"content": "go"}},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {}}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "content": "RESUME: reset soon"}]}},
        ]
        with open(tr, "w") as f:
            f.write("\n".join(json.dumps(r) for r in rows))
        out = run("stop_resume_guard.py", {"transcript_path": tr})[1]
        expect("stop unscheduled blocks", '"block"' in out, True)
        expect("stop_hook_active allows", run("stop_resume_guard.py", {"transcript_path": tr, "stop_hook_active": True})[1], "")
        rows.append({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "ScheduleWakeup", "input": {}}]}})
        with open(tr, "w") as f:
            f.write("\n".join(json.dumps(r) for r in rows))
        expect("stop scheduled allows", run("stop_resume_guard.py", {"transcript_path": tr})[1], "")
        good = os.path.join(d, "good.json")
        bad = os.path.join(d, "bad.json")
        json.dump({"hooks": {"PreToolUse": [{"hooks": [{"command": "python x.py", "timeout": 5}]}]}}, open(good, "w"))
        json.dump({"hooks": {"PreToolUse": [{"hooks": [{"command": "python3 x.py"}]}]}}, open(bad, "w"))
        expect("health ok", run_health(good), 0)
        expect("health flags no-timeout and python3", run_health(bad), 1)
        # POSITIVE CONTROL: this expectation is wrong on purpose and must register as a mismatch.
        wrong_want_allowed = run("read_size_guard.py", {"tool_name": "Read", "tool_input": {"file_path": big}}, env)[0] == 0
        if wrong_want_allowed:
            fails.append("POSITIVE CONTROL: an oversized read was allowed, so the deny cases above prove nothing")
    for f in fails:
        print("FAIL:", f)
    print("examples:", "FAIL" if fails else "PASS")
    return 1 if fails else 0


def run_health(path):
    return subprocess.run([sys.executable, os.path.join(HERE, "check_hook_health.py"), path], capture_output=True, text=True, timeout=20).returncode


if __name__ == "__main__":
    sys.exit(main())
