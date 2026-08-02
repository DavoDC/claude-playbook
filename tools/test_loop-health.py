#!/usr/bin/env python3
"""Repeatable test suite for loop-health.py.

Covers the original scenarios plus regressions for the empty-vs-absent
capture log fix, an exit-code parity check between the --json and non-JSON
branches, the misaligned-fields fifth input state, and a dedicated contract
check that all three exit codes (0 clean, 1 finding, 2 instrument defect)
land where the spec says. Silent on pass, verbose on fail, per workspace
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
        if rc != 2:
            ok = False
            detail.append("EXPECTED exit code 2 (could not measure), got " + str(rc))
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
        if rc != 2:
            ok = False
            detail.append("EXPECTED exit code 2 (could not measure), got " + str(rc))
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
        if rc != 2:
            ok = False
            detail.append("EXPECTED exit code 2 (could not measure), got " + str(rc))
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
        # This fixture measures cleanly (no instrumentation defects) but the
        # data it measures is genuinely unhealthy: an orphaned rule, a guard
        # that has become the normal state, and a repeated topic are all
        # real findings about the SYSTEM, not about the instrument. That is
        # exit code 1, not 0 - a fully populated run is not the same thing
        # as a clean one.
        if not report.get("findings"):
            ok = False
            detail.append("EXPECTED non-empty findings for orphan/noisy-guard/"
                          f"repeat data, got {report.get('findings')!r}")
        if rc != 1:
            ok = False
            detail.append("EXPECTED exit code 1 (measured, findings present) "
                          f"on this fixture, got {rc}")

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
        if rc != 2:
            ok = False
            detail.append("EXPECTED exit code 2 (could not measure) for an "
                          f"empty-but-present capture log, got {rc}")
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


# ---------------------------------------------------------------------
# Case 9 (new, BUG 2/saturation regression): unreferenced_pct comes out at
# exactly 100% because every logged reference points OUTSIDE the corpus.
# Must be flagged as a broken instrument, reporting the 0-of-N intersection.
# ---------------------------------------------------------------------
def case9():
    d = new_tempdir()
    try:
        rules_dir = os.path.join(d, "rules")
        os.makedirs(rules_dir)
        for rn in ("feedback_a.md", "feedback_b.md"):
            with open(os.path.join(rules_dir, rn), "w", encoding="utf-8") as fh:
                fh.write("content\n")

        ref_log = os.path.join(d, "ref.log")
        with open(ref_log, "w", encoding="utf-8") as fh:
            fh.write(f"{d_ago(1)} sess-1 some/other/outside_a.md\n")
            fh.write(f"{d_ago(2)} sess-2 some/other/outside_b.md\n")

        rc, out, err = run(d, [
            "--rules", rules_dir,
            "--reference-log", ref_log,
            "--guard-log", os.path.join(d, "no-such-guard.log"),
            "--capture-log", os.path.join(d, "no-such-capture.log"),
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

        if report.get("unreferenced_pct") != 100:
            ok = False
            detail.append(f"EXPECTED unreferenced_pct == 100, got "
                          f"{report.get('unreferenced_pct')!r}")
        defects = report.get("instrumentation_defects", [])
        if not any("100%" in dd and "0 of 2" in dd for dd in defects):
            ok = False
            detail.append("EXPECTED a saturation defect reporting '100%' and "
                          f"the 0-of-2 intersection; not found. defects={defects!r}")
        if rc != 2:
            ok = False
            detail.append(f"EXPECTED exit code 2 for a saturation defect, got {rc}")
        record("9 SATURATION AT 100%", ok, "\n".join(detail))
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------
# Case 10 (new, BUG 2/saturation regression): unreferenced_pct comes out at
# exactly 0% because every rule file is referenced. Must still be flagged,
# reporting the full N-of-N intersection so a reader can see it's the good
# extreme, not just trust the bare 0%.
# ---------------------------------------------------------------------
def case10():
    d = new_tempdir()
    try:
        rules_dir = os.path.join(d, "rules")
        os.makedirs(rules_dir)
        for rn in ("feedback_a.md", "feedback_b.md"):
            with open(os.path.join(rules_dir, rn), "w", encoding="utf-8") as fh:
                fh.write("content\n")

        ref_log = os.path.join(d, "ref.log")
        with open(ref_log, "w", encoding="utf-8") as fh:
            fh.write(f"{d_ago(1)} sess-1 feedback_a.md\n")
            fh.write(f"{d_ago(2)} sess-2 feedback_b.md\n")

        rc, out, err = run(d, [
            "--rules", rules_dir,
            "--reference-log", ref_log,
            "--guard-log", os.path.join(d, "no-such-guard.log"),
            "--capture-log", os.path.join(d, "no-such-capture.log"),
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

        if report.get("unreferenced_pct") != 0:
            ok = False
            detail.append(f"EXPECTED unreferenced_pct == 0, got "
                          f"{report.get('unreferenced_pct')!r}")
        defects = report.get("instrumentation_defects", [])
        if not any("0%" in dd and "2 of 2" in dd for dd in defects):
            ok = False
            detail.append("EXPECTED a saturation defect reporting '0%' and "
                          f"the 2-of-2 intersection; not found. defects={defects!r}")
        if rc != 2:
            ok = False
            detail.append(f"EXPECTED exit code 2 for a saturation defect, got {rc}")
        record("10 SATURATION AT 0%", ok, "\n".join(detail))
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------
# Case 11 (new): a genuine PARTIAL unreferenced_pct (neither 0 nor 100)
# must NOT be flagged as a saturation defect. Without this, a saturation
# check that fires on everything would look identical to a correct one. The
# happy-path fixture also carries real findings (an orphan, a noisy guard, a
# repeated topic), so the exit code here is 1 (measured, findings present),
# not 0 - what this case is actually pinning down is the ABSENCE of a
# saturation defect, checked directly against instrumentation_defects.
# ---------------------------------------------------------------------
def case11():
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

        pct = report.get("unreferenced_pct")
        if pct in (0, 100):
            ok = False
            detail.append(f"EXPECTED a partial unreferenced_pct (not 0 or 100), "
                          f"got {pct!r}")
        defects = report.get("instrumentation_defects", [])
        if any("suspicious" in dd for dd in defects):
            ok = False
            detail.append(f"EXPECTED no saturation defect on a genuine partial "
                          f"result, got defects={defects!r}")
        if defects:
            ok = False
            detail.append(f"EXPECTED no instrumentation defects at all on this "
                          f"fixture, got defects={defects!r}")
        if rc != 1:
            ok = False
            detail.append("EXPECTED exit code 1 (measured, findings present - "
                          f"this fixture has real orphans/noise/repeats), got {rc}")
        record("11 SATURATION - PARTIAL DOES NOT FLAG", ok, "\n".join(detail))
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------
# Case 12 (new, BUG 3/parse-yield regression): a capture log full of
# in-window dated lines in an unrecognised (comma-joined, no whitespace)
# shape must report a PARSE YIELD COLLAPSE defect and must NOT also claim
# the log is empty - the failure being prevented is a misclassification,
# not a silence.
# ---------------------------------------------------------------------
def case12():
    d = new_tempdir()
    try:
        rules_dir = os.path.join(d, "rules")
        os.makedirs(rules_dir)
        with open(os.path.join(rules_dir, "feedback_x.md"), "w", encoding="utf-8") as fh:
            fh.write("content\n")

        cap_log = os.path.join(d, "cap.log")
        with open(cap_log, "w", encoding="utf-8") as fh:
            for i in range(1, 5):
                fh.write(f"{d_ago(i)},feedback_x.md,sometopic\n")  # no whitespace

        rc, out, err = run(d, [
            "--rules", rules_dir,
            "--reference-log", os.path.join(d, "no-such-ref.log"),
            "--guard-log", os.path.join(d, "no-such-guard.log"),
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
        if not any("PARSE YIELD COLLAPSE" in dd for dd in defects):
            ok = False
            detail.append(f"EXPECTED a PARSE YIELD COLLAPSE defect for the capture "
                          f"log; not found. defects={defects!r}")
        if any("capture log is EMPTY" in dd for dd in defects):
            ok = False
            detail.append("EXPECTED the collapse to NOT also be reported as an "
                          f"empty log (misclassification); defects={defects!r}")
        if report.get("repeat_topics") != "UNKNOWN":
            ok = False
            detail.append(f"EXPECTED repeat_topics == UNKNOWN on collapse, got "
                          f"{report.get('repeat_topics')!r}")
        if rc != 2:
            ok = False
            detail.append(f"EXPECTED exit code 2 on a collapse defect, got {rc}")
        record("12 PARSE YIELD COLLAPSE, not EMPTY", ok, "\n".join(detail))
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------
# Case 13 (new): a capture log with one line in each accepted shape (plain
# "YYYY-MM-DD ..." and bracketed "[YYYY-MM-DD] ...") must parse BOTH and
# cluster them into the same topic. Without this, a fix that merely swaps
# which single shape is accepted looks identical to one that accepts both.
# ---------------------------------------------------------------------
def case13():
    d = new_tempdir()
    try:
        rules_dir = os.path.join(d, "rules")
        os.makedirs(rules_dir)
        with open(os.path.join(rules_dir, "feedback_x.md"), "w", encoding="utf-8") as fh:
            fh.write("content\n")

        cap_log = os.path.join(d, "cap.log")
        with open(cap_log, "w", encoding="utf-8") as fh:
            fh.write(f"{d_ago(5)} feedback_x.md sametopic\n")     # plain shape
            fh.write(f"[{d_ago(3)}] feedback_x.md sametopic\n")   # bracketed shape

        rc, out, err = run(d, [
            "--rules", rules_dir,
            "--reference-log", os.path.join(d, "no-such-ref.log"),
            "--guard-log", os.path.join(d, "no-such-guard.log"),
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

        tagged = report.get("repeat_topics_tagged", {})
        if "sametopic" not in tagged or len(tagged.get("sametopic", [])) != 2:
            ok = False
            detail.append(f"EXPECTED repeat_topics_tagged['sametopic'] with both "
                          f"lines clustered (2 entries), got {tagged!r}")
        defects = report.get("instrumentation_defects", [])
        if any("capture" in dd.lower() for dd in defects):
            ok = False
            detail.append(f"EXPECTED no capture-log defect when both accepted "
                          f"shapes parse cleanly, got defects={defects!r}")
        record("13 BOTH ACCEPTED FORMATS CLUSTER TOGETHER", ok, "\n".join(detail))
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------
# Case 14 (new, fifth-input-state regression): a capture log where every
# row parses, every date recovers, and the file is neither empty nor
# below the parse-yield floor - every existing guard passes - but the
# fields hold something other than their names say, because the log's
# actual shape is "[date time] [session] correction: message" rather than
# "date rule topic". "rule" ends up holding a bare time token and "topic"
# ends up holding an entire sentence. This must be caught as its own
# state (misaligned), not silently clustered and not folded into
# absent/empty/saturated/collapsed.
# ---------------------------------------------------------------------
def case14():
    d = new_tempdir()
    try:
        rules_dir = os.path.join(d, "rules")
        os.makedirs(rules_dir)
        with open(os.path.join(rules_dir, "feedback_x.md"), "w", encoding="utf-8") as fh:
            fh.write("content\n")

        cap_log = os.path.join(d, "cap.log")
        with open(cap_log, "w", encoding="utf-8") as fh:
            for i in range(1, 11):
                fh.write(f"[{d_ago(i)} 07:3{i % 10}:2{i % 10}] [sess-0] "
                         f"correction: no dont do that, use Y instead, item {i}\n")

        rc, out, err = run(d, [
            "--rules", rules_dir,
            "--reference-log", os.path.join(d, "no-such-ref.log"),
            "--guard-log", os.path.join(d, "no-such-guard.log"),
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
        if not any("MISALIGNED FIELDS" in dd for dd in defects):
            ok = False
            detail.append("EXPECTED a MISALIGNED FIELDS defect for the capture "
                          f"log; not found. defects={defects!r}")
        if report.get("repeat_topics") != "UNKNOWN":
            ok = False
            detail.append(f"EXPECTED repeat_topics == UNKNOWN on misalignment, "
                          f"got {report.get('repeat_topics')!r}")
        if report.get("repeat_topics_tagged") is not None:
            ok = False
            detail.append("EXPECTED no clustering result at all on misalignment "
                          f"(not even a wrong one), got repeat_topics_tagged="
                          f"{report.get('repeat_topics_tagged')!r}")
        if rc != 2:
            ok = False
            detail.append(f"EXPECTED exit code 2 (could not measure) on a "
                          f"misaligned capture log, got {rc}")
        record("14 MISALIGNED FIELDS (fifth state)", ok, "\n".join(detail))
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------
# Case 15 (new, exit-code contract): the three outcomes need three exit
# codes, checked directly rather than inferred from other cases - 0 for a
# clean measured run, 1 for a measured run with a real system finding, 2
# for a run that could not measure at all.
# ---------------------------------------------------------------------
def case15():
    # 0: measured, no defects, no findings. An empty (but present) rules dir
    # sidesteps the 0%/100% saturation defect entirely, since unreferenced_pct
    # is only computed when there is at least one rule file - with zero rule
    # files there is nothing to be orphaned and nothing to saturate on.
    d0 = new_tempdir()
    try:
        rules_dir = os.path.join(d0, "rules")
        os.makedirs(rules_dir)
        ref_log = os.path.join(d0, "ref.log")
        guard_log = os.path.join(d0, "guard.log")
        cap_log = os.path.join(d0, "cap.log")
        with open(ref_log, "w", encoding="utf-8") as fh:
            fh.write(f"{d_ago(1)} sess-1 some_file.md\n")
        with open(guard_log, "w", encoding="utf-8") as fh:
            fh.write(f"{d_ago(1)} quiet-guard allow\n")
        with open(cap_log, "w", encoding="utf-8") as fh:
            fh.write(f"{d_ago(1)} some_file.md onlytopic\n")

        rc, out, err = run(d0, [
            "--rules", rules_dir, "--reference-log", ref_log,
            "--guard-log", guard_log, "--capture-log", cap_log, "--json",
        ])
        ok = rc == 0
        detail = [f"exit code: {rc}", out, "STDERR: " + err]
        if not ok:
            detail.append(f"EXPECTED exit code 0 (clean measured run), got {rc}")
        record("15a exit code 0 (clean)", ok, "\n".join(detail))
    finally:
        shutil.rmtree(d0, ignore_errors=True)

    # 1: measured, a real finding (an orphaned rule) present. Two rule files
    # with only one referenced gives a 50% unreferenced_pct - partial, so it
    # is a genuine finding rather than the 0%/100% saturation defect case.
    d1 = new_tempdir()
    try:
        rules_dir = os.path.join(d1, "rules")
        os.makedirs(rules_dir)
        for rn in ("feedback_orphan.md", "feedback_referenced.md"):
            with open(os.path.join(rules_dir, rn), "w", encoding="utf-8") as fh:
                fh.write("content\n")
        ref_log = os.path.join(d1, "ref.log")
        guard_log = os.path.join(d1, "guard.log")
        cap_log = os.path.join(d1, "cap.log")
        with open(ref_log, "w", encoding="utf-8") as fh:
            fh.write(f"{d_ago(1)} sess-1 feedback_referenced.md\n")
        with open(guard_log, "w", encoding="utf-8") as fh:
            fh.write(f"{d_ago(1)} quiet-guard allow\n")
        with open(cap_log, "w", encoding="utf-8") as fh:
            fh.write(f"{d_ago(1)} feedback_referenced.md onlytopic\n")

        rc, out, err = run(d1, [
            "--rules", rules_dir, "--reference-log", ref_log,
            "--guard-log", guard_log, "--capture-log", cap_log, "--json",
        ])
        ok = True
        detail = [f"exit code: {rc}", out, "STDERR: " + err]
        try:
            report = json.loads(out)
        except Exception as e:
            ok = False
            report = {}
            detail.append(f"JSON PARSE FAILED: {e}")

        if report.get("instrumentation_defects"):
            ok = False
            detail.append("EXPECTED no instrumentation defects on this fixture "
                          f"(partial pct, not saturated), got "
                          f"{report.get('instrumentation_defects')!r}")
        if not report.get("findings"):
            ok = False
            detail.append(f"EXPECTED a non-empty findings list (the orphaned "
                          f"rule), got {report.get('findings')!r}")
        if rc != 1:
            ok = False
            detail.append(f"EXPECTED exit code 1 (measured, findings present), "
                          f"got {rc}")
        record("15b exit code 1 (finding, no defect)", ok, "\n".join(detail))
    finally:
        shutil.rmtree(d1, ignore_errors=True)

    # 2: could not measure at all.
    d2 = new_tempdir()
    try:
        rc, out, err = run(d2, [
            "--rules", os.path.join(d2, "no-such-rules"),
            "--reference-log", os.path.join(d2, "no-such-ref.log"),
            "--guard-log", os.path.join(d2, "no-such-guard.log"),
            "--capture-log", os.path.join(d2, "no-such-capture.log"),
            "--json",
        ])
        ok = rc == 2
        detail = [f"exit code: {rc}", out, "STDERR: " + err]
        if not ok:
            detail.append(f"EXPECTED exit code 2 (could not measure), got {rc}")
        record("15c exit code 2 (instrument defect)", ok, "\n".join(detail))
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
    case9()
    case10()
    case11()
    case12()
    case13()
    case14()
    case15()

    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    if passed != total:
        print(f"{total - passed} of {total} cases failed (see detail above).")

    verdict = "PASS" if passed == total else "FAIL"
    print(f"VERDICT: {verdict} ({passed}/{total})")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
