#!/usr/bin/env python3
"""Repeatable test suite for loop-health.py.

Covers the six original scenarios plus a case specifically for the
empty-vs-absent capture log fix, and an exit-code parity check between the
--json and non-JSON branches. Silent on pass, verbose on fail, per workspace
convention: the combined verdict is the LAST line of output, so `tail -1`
gives the answer.

Not a unit-test framework - deliberately simple pass/fail script, run as a
plain subprocess harness against the CLI, same approach as run_tests.py.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "loop-health.py")

results = []  # list of (case_name, passed_bool, detail_str)


def run(cwd, args):
    """Run loop-health.py with given args from cwd. Return (returncode, stdout, stderr)."""
    cmd = [sys.executable, SCRIPT] + args
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def record(name, passed, detail):
    results.append((name, passed, detail))
    if not passed:
        print(f"[FAIL] {name}")
        print("  ---- detail ----")
        for line in detail.splitlines():
            print(f"  {line}")
        print("  ----------------")


def new_tempdir():
    return tempfile.mkdtemp(prefix="loophealth_")


def d_ago(n, base=None):
    base = base or date.today()
    return (base - timedelta(days=n)).isoformat()


# ---------------------------------------------------------------------
# Case 1: NOTHING PRESENT - no rules dir, no logs
# ---------------------------------------------------------------------
def case1():
    d = new_tempdir()
    try:
        rc, out, err = run(d, [
            "--rules", os.path.join(d, "no-such-rules"),
            "--reference-log", os.path.join(d, "no-such-ref.log"),
            "--guard-log", os.path.join(d, "no-such-guard.log"),
            "--capture-log", os.path.join(d, "no-such-capture.log"),
        ])
        ok = True
        detail = [f"exit code: {rc}", out, "STDERR: " + err]
        if rc != 1:
            ok = False
            detail.append("EXPECTED exit code 1, got " + str(rc))
        if "UNKNOWN" not in out:
            ok = False
            detail.append("EXPECTED 'UNKNOWN' to appear in output")
        if "INSTRUMENTATION DEFECTS" not in out:
            ok = False
            detail.append("EXPECTED non-empty instrumentation_defects section")
        record("1 NOTHING PRESENT", ok, "\n".join(detail))
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------
# Case 2: RULES PRESENT, LOGS ABSENT
# ---------------------------------------------------------------------
def case2():
    d = new_tempdir()
    try:
        rules_dir = os.path.join(d, "rules")
        os.makedirs(rules_dir)
        rule_names = ["feedback_alpha.md", "feedback_beta.md", "feedback_gamma.md",
                      "feedback_delta.txt", "not_a_rule.py"]
        for rn in rule_names:
            with open(os.path.join(rules_dir, rn), "w", encoding="utf-8") as fh:
                fh.write("# rule\nsome content\n")

        rc, out, err = run(d, [
            "--rules", rules_dir,
            "--reference-log", os.path.join(d, "no-such-ref.log"),
            "--guard-log", os.path.join(d, "no-such-guard.log"),
            "--capture-log", os.path.join(d, "no-such-capture.log"),
            "--json",
        ])
        ok = True
        detail = [f"exit code: {rc}", out, "STDERR: " + err]
        if rc != 1:
            ok = False
            detail.append("EXPECTED exit code 1, got " + str(rc))
        try:
            report = json.loads(out)
        except Exception as e:
            ok = False
            report = {}
            detail.append(f"JSON PARSE FAILED: {e}")

        expected_rule_count = 4  # .md and .txt only, not .py
        if report.get("rule_count") != expected_rule_count:
            ok = False
            detail.append(f"EXPECTED rule_count == {expected_rule_count}, "
                          f"got {report.get('rule_count')!r}")
        for field in ("unreferenced_rules", "guard_fires", "repeat_topics"):
            if report.get(field) != "UNKNOWN":
                ok = False
                detail.append(f"EXPECTED {field} == UNKNOWN, got {report.get(field)!r}")
        record("2 RULES PRESENT, LOGS ABSENT", ok, "\n".join(detail))
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------
# Case 3: LOGS PRESENT BUT EMPTY - all three logs, the critical case
# ---------------------------------------------------------------------
def case3():
    d = new_tempdir()
    try:
        rules_dir = os.path.join(d, "rules")
        os.makedirs(rules_dir)
        with open(os.path.join(rules_dir, "feedback_x.md"), "w", encoding="utf-8") as fh:
            fh.write("content\n")

        ref_log = os.path.join(d, "ref.log")
        guard_log = os.path.join(d, "guard.log")
        cap_log = os.path.join(d, "cap.log")
        # Create the files but leave them EMPTY (0 bytes) - instrumented but silent.
        for p in (ref_log, guard_log, cap_log):
            open(p, "w", encoding="utf-8").close()

        rc, out, err = run(d, [
            "--rules", rules_dir,
            "--reference-log", ref_log,
            "--guard-log", guard_log,
            "--capture-log", cap_log,
            "--json",
        ])
        ok = True
        detail = [f"exit code: {rc}", out, "STDERR: " + err]
        if rc != 1:
            ok = False
            detail.append("EXPECTED exit code 1, got " + str(rc))
        try:
            report = json.loads(out)
        except Exception as e:
            ok = False
            report = {}
            detail.append(f"JSON PARSE FAILED: {e}")

        defects = report.get("instrumentation_defects", [])
        checks = [
            ("reference log is EMPTY", "reference"),
            ("guard log is EMPTY", "guard"),
            ("capture log is EMPTY", "capture"),
        ]
        for needle, label in checks:
            if not any(needle in dd for dd in defects):
                ok = False
                detail.append(f"EXPECTED a defect distinguishing EMPTY {label} log "
                              f"from an absent one; not found. defects={defects!r}")
        for field in ("unreferenced_rules", "guard_fires", "repeat_topics"):
            if report.get(field) != "UNKNOWN":
                ok = False
                detail.append(f"EXPECTED {field} == UNKNOWN for empty logs, "
                              f"got {report.get(field)!r}")
        record("3 LOGS PRESENT BUT EMPTY", ok, "\n".join(detail))
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------
# Case 4: FULL HAPPY PATH
# ---------------------------------------------------------------------
def build_happy_fixture(d):
    rules_dir = os.path.join(d, "rules")
    os.makedirs(rules_dir)
    rule_names = [
        "feedback_alpha_topic.md",     # referenced, tagged topic "alpha" once
        "feedback_beta_topic.md",      # referenced, tagged topic "beta" twice (repeat)
        "feedback_gamma_topic.md",     # NEVER referenced -> orphan
        "feedback_delta_topic.md",     # referenced
    ]
    for rn in rule_names:
        with open(os.path.join(rules_dir, rn), "w", encoding="utf-8") as fh:
            fh.write("content\n")

    ref_log = os.path.join(d, "ref.log")
    guard_log = os.path.join(d, "guard.log")
    cap_log = os.path.join(d, "cap.log")

    with open(ref_log, "w", encoding="utf-8") as fh:
        fh.write(f"{d_ago(5)} sess-001 feedback_alpha_topic.md\n")
        fh.write(f"{d_ago(4)} sess-002 feedback_beta_topic.md\n")
        fh.write(f"{d_ago(3)} sess-003 feedback_delta_topic.md\n")
        # gamma never appears here -> orphan/unreferenced

    with open(guard_log, "w", encoding="utf-8") as fh:
        # a guard with 20+ fires, mostly blocks -> should land in
        # guards_now_normal_state
        for i in range(16):
            fh.write(f"{d_ago(i % 30)} noisy-guard block\n")
        for i in range(6):
            fh.write(f"{d_ago(i % 30)} noisy-guard allow\n")
        # a quiet guard, mostly allows, should NOT be flagged
        for i in range(3):
            fh.write(f"{d_ago(i)} quiet-guard allow\n")

    with open(cap_log, "w", encoding="utf-8") as fh:
        # topic 'alpha' captured once - not a repeat
        fh.write(f"{d_ago(80)} feedback_alpha_topic.md alpha\n")
        # topic 'beta' captured twice (repeat), earlier + recent half
        fh.write(f"{d_ago(85)} feedback_beta_topic.md beta\n")
        fh.write(f"{d_ago(2)} feedback_beta_topic_v2.md beta\n")
        # topic 'delta' captured once
        fh.write(f"{d_ago(10)} feedback_delta_topic.md delta\n")

    return rules_dir, ref_log, guard_log, cap_log


def case4():
    d = new_tempdir()
    try:
        rules_dir, ref_log, guard_log, cap_log = build_happy_fixture(d)

        rc, out, err = run(d, [
            "--rules", rules_dir,
            "--reference-log", ref_log,
            "--guard-log", guard_log,
            "--capture-log", cap_log,
            "--days", "90",
            "--json",
        ])
        ok = True
        detail = [f"exit code: {rc}", out, "STDERR: " + err]

        try:
            report = json.loads(out)
        except Exception as e:
            ok = False
            report = {}
            detail.append(f"JSON PARSE FAILED: {e}")

        orphans = report.get("unreferenced_rules")
        if orphans != ["feedback_gamma_topic.md"]:
            ok = False
            detail.append(f"EXPECTED unreferenced_rules == "
                          f"['feedback_gamma_topic.md'], got {orphans!r}")

        noisy = report.get("guards_now_normal_state", [])
        if "noisy-guard" not in noisy:
            ok = False
            detail.append(f"EXPECTED 'noisy-guard' in guards_now_normal_state, "
                          f"got {noisy!r}")
        if "quiet-guard" in noisy:
            ok = False
            detail.append("EXPECTED 'quiet-guard' NOT flagged as normal-state "
                          "(too few fires)")

        tagged = report.get("repeat_topics_tagged", {})
        if "beta" not in tagged or len(tagged.get("beta", [])) != 2:
            ok = False
            detail.append(f"EXPECTED repeat_topics_tagged['beta'] with 2 entries, "
                          f"got {tagged!r}")

        direction = report.get("direction")
        detail.append(f"direction reported: {direction!r} "
                      f"(earlier={report.get('repeats_earlier_half')}, "
                      f"recent={report.get('repeats_recent_half')})")
        if direction not in ("improving", "flat or worsening"):
            ok = False
            detail.append(f"EXPECTED a concrete direction value, got {direction!r}")

        # beta's earliest-dated line (85 days ago) is the "original"; its
        # second line (2 days ago) is the repeat and falls in the recent half.
        if report.get("repeats_earlier_half") != 0 or report.get("repeats_recent_half") != 1:
            ok = False
            detail.append("EXPECTED repeats_earlier_half == 0 and "
                          f"repeats_recent_half == 1, got earlier="
                          f"{report.get('repeats_earlier_half')!r} recent="
                          f"{report.get('repeats_recent_half')!r}")

        if report.get("instrumentation_defects"):
            ok = False
            detail.append("EXPECTED no instrumentation_defects on a fully "
                          f"populated run, got {report.get('instrumentation_defects')!r}")
        if rc != 0:
            ok = False
            detail.append(f"EXPECTED exit code 0 on a fully populated/clean "
                          f"run, got {rc}")

        record("4 FULL HAPPY PATH", ok, "\n".join(detail))
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------
# Case 5: --json mode produces valid, parseable JSON
# ---------------------------------------------------------------------
def case5():
    d = new_tempdir()
    try:
        rules_dir = os.path.join(d, "rules")
        os.makedirs(rules_dir)
        with open(os.path.join(rules_dir, "feedback_x.md"), "w", encoding="utf-8") as fh:
            fh.write("content\n")
        rc, out, err = run(d, [
            "--rules", rules_dir,
            "--reference-log", os.path.join(d, "absent-ref.log"),
            "--guard-log", os.path.join(d, "absent-guard.log"),
            "--capture-log", os.path.join(d, "absent-cap.log"),
            "--json",
        ])
        ok = True
        detail = [f"exit code: {rc}", out, "STDERR: " + err]
        try:
            parsed = json.loads(out)
            if not isinstance(parsed, dict):
                ok = False
                detail.append("EXPECTED parsed JSON to be a dict")
        except Exception as e:
            ok = False
            detail.append(f"JSON PARSE FAILED: {e}")
        record("5 --json valid JSON", ok, "\n".join(detail))
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------
# Case 6: malformed log line does not crash it
# ---------------------------------------------------------------------
def case6():
    d = new_tempdir()
    try:
        rules_dir = os.path.join(d, "rules")
        os.makedirs(rules_dir)
        with open(os.path.join(rules_dir, "feedback_x.md"), "w", encoding="utf-8") as fh:
            fh.write("content\n")

        ref_log = os.path.join(d, "ref.log")
        guard_log = os.path.join(d, "guard.log")
        cap_log = os.path.join(d, "cap.log")

        with open(ref_log, "w", encoding="utf-8") as fh:
            fh.write("tooshort\n")               # too few fields, dropped by parse_log
            fh.write("not-a-date sess-1 x.md\n")  # bad date, dropped by within()
            fh.write(f"{date.today().isoformat()} sess-2 feedback_x.md\n")  # valid

        with open(guard_log, "w", encoding="utf-8") as fh:
            fh.write("badline\n")  # too few fields
            fh.write(f"{date.today().isoformat()} some-guard block\n")

        with open(cap_log, "w", encoding="utf-8") as fh:
            fh.write("nope\n")  # too few fields
            fh.write(f"{date.today().isoformat()} feedback_x.md sometopic\n")

        rc, out, err = run(d, [
            "--rules", rules_dir,
            "--reference-log", ref_log,
            "--guard-log", guard_log,
            "--capture-log", cap_log,
            "--json",
        ])
        ok = True
        detail = [f"exit code: {rc}", out, "STDERR: " + err]
        if "Traceback" in err or "Traceback" in out:
            ok = False
            detail.append("SCRIPT CRASHED - traceback present")
        try:
            json.loads(out)
        except Exception as e:
            ok = False
            detail.append(f"JSON PARSE FAILED after malformed lines: {e}")
        record("6 malformed log line survives", ok, "\n".join(detail))
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------
# Case 7 (new, BUG 1 regression test): capture log present but EMPTY,
# reference and guard logs both populated and healthy. The capture-log
# empty-vs-absent gap must produce its own defect and a non-zero exit,
# not just ride along on the ref/guard defects.
# ---------------------------------------------------------------------
def case7():
    d = new_tempdir()
    try:
        rules_dir = os.path.join(d, "rules")
        os.makedirs(rules_dir)
        with open(os.path.join(rules_dir, "feedback_x.md"), "w", encoding="utf-8") as fh:
            fh.write("content\n")

        ref_log = os.path.join(d, "ref.log")
        guard_log = os.path.join(d, "guard.log")
        cap_log = os.path.join(d, "cap.log")

        with open(ref_log, "w", encoding="utf-8") as fh:
            fh.write(f"{d_ago(1)} sess-1 feedback_x.md\n")
        with open(guard_log, "w", encoding="utf-8") as fh:
            fh.write(f"{d_ago(1)} some-guard allow\n")
        open(cap_log, "w", encoding="utf-8").close()  # present, 0 bytes

        rc, out, err = run(d, [
            "--rules", rules_dir,
            "--reference-log", ref_log,
            "--guard-log", guard_log,
            "--capture-log", cap_log,
            "--json",
        ])
        ok = True
        detail = [f"exit code: {rc}", out, "STDERR: " + err]

        try:
            report = json.loads(out)
        except Exception as e:
            ok = False
            report = {}
            detail.append(f"JSON PARSE FAILED: {e}")

        defects = report.get("instrumentation_defects", [])
        if not any("capture log is EMPTY" in dd for dd in defects):
            ok = False
            detail.append("EXPECTED a defect distinguishing EMPTY capture log "
                          f"from an absent one; not found. defects={defects!r}")
        if report.get("repeat_topics") != "UNKNOWN" and report.get("repeat_topics_tagged") is not None:
            # repeat_topics itself is only set on the None/empty branches; the
            # populated branch never sets it at all, so its absence here is
            # what proves the empty-log branch was taken.
            ok = False
            detail.append("EXPECTED the empty-capture-log branch (repeat_topics "
                          f"== UNKNOWN), got repeat_topics_tagged="
                          f"{report.get('repeat_topics_tagged')!r}")
        if rc != 1:
            ok = False
            detail.append("EXPECTED non-zero exit code for an empty-but-present "
                          f"capture log, got {rc}")
        record("7 CAPTURE LOG PRESENT BUT EMPTY (BUG 1 regression)", ok, "\n".join(detail))
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------
# Case 8 (new): --json and non-JSON branches must agree on exit code,
# both for a clean run and for a defect-laden run.
# ---------------------------------------------------------------------
def case8():
    d = new_tempdir()
    try:
        rules_dir, ref_log, guard_log, cap_log = build_happy_fixture(d)
        args_common = [
            "--rules", rules_dir,
            "--reference-log", ref_log,
            "--guard-log", guard_log,
            "--capture-log", cap_log,
            "--days", "90",
        ]
        rc_json, _, _ = run(d, args_common + ["--json"])
        rc_text, _, _ = run(d, args_common)
        ok = True
        detail = [f"json exit: {rc_json}", f"text exit: {rc_text}"]
        if rc_json != rc_text:
            ok = False
            detail.append("EXPECTED --json and text exit codes to match on a "
                          "clean run")
        record("8a exit code parity, clean run", ok, "\n".join(detail))
    finally:
        shutil.rmtree(d, ignore_errors=True)

    d2 = new_tempdir()
    try:
        args_common = [
            "--rules", os.path.join(d2, "no-such-rules"),
            "--reference-log", os.path.join(d2, "no-such-ref.log"),
            "--guard-log", os.path.join(d2, "no-such-guard.log"),
            "--capture-log", os.path.join(d2, "no-such-capture.log"),
        ]
        rc_json, _, _ = run(d2, args_common + ["--json"])
        rc_text, _, _ = run(d2, args_common)
        ok = True
        detail = [f"json exit: {rc_json}", f"text exit: {rc_text}"]
        if rc_json != rc_text:
            ok = False
            detail.append("EXPECTED --json and text exit codes to match on a "
                          "defect-laden run")
        record("8b exit code parity, defect run", ok, "\n".join(detail))
    finally:
        shutil.rmtree(d2, ignore_errors=True)


def main():
    if not os.path.exists(SCRIPT):
        print(f"FATAL: script not found at {SCRIPT}")
        print("VERDICT: FAIL (script missing)")
        sys.exit(2)

    case1()
    case2()
    case3()
    case4()
    case5()
    case6()
    case7()
    case8()

    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    if passed != total:
        print(f"{total - passed} of {total} cases failed (see detail above).")

    verdict = "PASS" if passed == total else "FAIL"
    print(f"VERDICT: {verdict} ({passed}/{total})")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
