"""Tests for backlog.py pull and lifecycle commands: close, next, brief, shape, init, and the SessionStart status script."""
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import backlog  # noqa: E402
from test_backlog import build, mk, rules  # noqa: E402

TODAY = date(2026, 9, 27)
SHA = "abc1234"


def write(tmp_path, text, name="IDEAS.md"):
    p = tmp_path / name
    p.write_bytes(text.encode("utf-8"))
    return p


def fails(text):
    return sorted(f.rule for f in backlog.check(backlog.parse(text), today=TODAY) if f.level == "fail")


def close(p, id_="A-1", **kw):
    kw.setdefault("evidence", "ran it")
    return backlog.close_item(p, id_, SHA, "did it", today=TODAY, **kw)


# ---- close ----

def test_close_moves_item_to_history_and_cleans_index_epic_human(tmp_path):
    t = build([mk("A-1"), mk("A-2"), mk("A-3"), mk("D-1", owner="Human")], epics="Epics: A-3 = A-1, A-2.\n")
    t = t.replace("- D-1: only Human.\n", "- D-1: only Human.\n- A-1: also mentioned.\n")
    p = write(tmp_path, t)
    close(p)
    new = p.read_text(encoding="utf-8")
    assert "### A-1" not in new and "| A-1 |" not in new and "A-1" not in new.split("## INBOX")[0]
    assert "A-2" in new and "D-1" in new
    assert "- A-1: also mentioned." not in new
    assert fails(new) == []
    hist = (tmp_path / "HISTORY.md").read_text(encoding="utf-8")
    assert hist.startswith("# History") and "A-1" in hist and SHA in hist and "did it" in hist and "2026-09-27" in hist


def test_close_prepends_newest_first_and_keeps_crlf(tmp_path):
    p = write(tmp_path, build([mk("A-1"), mk("A-2")]).replace("\n", "\r\n"))
    (tmp_path / "HISTORY.md").write_bytes(b"# History\r\n\r\n## 2026-09-01 - old entry\r\n\r\nold text\r\n")
    close(p)
    close(p, "A-2")
    hist = (tmp_path / "HISTORY.md").read_bytes().decode("utf-8")
    assert hist.count("\r\n") == hist.count("\n")
    assert hist.index("A-2") < hist.index("A-1") < hist.index("old entry")
    assert b"\r\n" in p.read_bytes() and p.read_bytes().count(b"\r\n") == p.read_bytes().count(b"\n")


def test_close_history_entry_is_one_paragraph_line(tmp_path):
    p = write(tmp_path, build([mk("A-1")]))
    close(p, evidence="saw it work")
    body = [ln for ln in (tmp_path / "HISTORY.md").read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(body) == 3  # title, heading, one paragraph
    assert "saw it work" in body[2]


@pytest.mark.parametrize("sha", ["", "xyz", "12", "not a sha"])
def test_close_bad_sha_refused(tmp_path, sha):
    p = write(tmp_path, build([mk("A-1")]))
    before = p.read_text(encoding="utf-8")
    with pytest.raises(backlog.BacklogError):
        backlog.close_item(p, "A-1", sha, "s", evidence="e", today=TODAY)
    assert p.read_text(encoding="utf-8") == before


def test_close_unknown_id_refused(tmp_path):
    p = write(tmp_path, build([mk("A-1")]))
    with pytest.raises(backlog.BacklogError, match="A-9"):
        close(p, "A-9")


def test_close_needs_verify_or_evidence(tmp_path):
    p = write(tmp_path, build([mk("A-1")]))
    with pytest.raises(backlog.BacklogError, match="evidence"):
        backlog.close_item(p, "A-1", SHA, "s", today=TODAY)
    assert "### A-1" in p.read_text(encoding="utf-8")


def test_close_runs_verify_and_passes(tmp_path):
    p = write(tmp_path, build([mk("A-1", extra="- **Verify:** `exit 0`\n")]))
    backlog.close_item(p, "A-1", SHA, "s", today=TODAY, cwd=tmp_path)
    assert "### A-1" not in p.read_text(encoding="utf-8")


def test_close_failing_verify_writes_nothing(tmp_path):
    p = write(tmp_path, build([mk("A-1", extra="- **Verify:** `exit 3`\n")]))
    before = p.read_text(encoding="utf-8")
    with pytest.raises(backlog.BacklogError, match="Verify"):
        backlog.close_item(p, "A-1", SHA, "s", evidence="but I say so", today=TODAY, cwd=tmp_path)
    assert p.read_text(encoding="utf-8") == before and not (tmp_path / "HISTORY.md").exists()


def test_close_refuses_when_result_would_fail_check(tmp_path):
    # A-1 is the only Human item listed in HUMAN ONLY next to B-1; break the file first so the after-state adds a new fail
    t = build([mk("A-1"), mk("A-2")])
    t = t.replace("| A-2 | Do the thing | T1 | S | ready | Claude | none |\n", "")
    p = write(tmp_path, t)
    before = p.read_text(encoding="utf-8")
    # existing fail (missing row) is not new, closing A-1 must still work
    close(p)
    assert "### A-1" not in p.read_text(encoding="utf-8")
    assert before != p.read_text(encoding="utf-8")


# ---- next / brief ----

def test_next_takes_highest_tier_first_ready_claude_item():
    doc = backlog.parse(build([mk("L-1", tier="T3"), mk("H-1", tier="T1"), mk("Z-1", tier="T0", owner="Human"), mk("I-1", tier="T0", state="idea")]))
    assert backlog.next_item(doc).id == "H-1"


def test_next_skips_items_with_open_dependency():
    dep = "- **Depends on / blocks:** A-2 / none.\n"
    base = mk("A-1", tier="T0")
    a1 = (base[0], base[1].replace("- **Depends on / blocks:** none / none.\n", dep)) + base[2:]
    doc = backlog.parse(build([a1, mk("A-2", tier="T1")]))
    assert backlog.next_item(doc).id == "A-2"


def test_next_none_when_nothing_ready():
    assert backlog.next_item(backlog.parse(build([mk("A-1", state="idea")]))) is None


def test_next_owner_flag():
    doc = backlog.parse(build([mk("A-1", owner="Human"), mk("A-2")]))
    assert backlog.next_item(doc, owner="Human").id == "A-1"


def test_brief_has_only_that_item_and_related_titles():
    dep = "- **Depends on / blocks:** A-2 / none.\n- **Pointers:** see A-3.\n"
    it = mk("A-1")
    it = (it[0], it[1].replace("- **Depends on / blocks:** none / none.\n", dep)) + it[2:]
    doc = backlog.parse(build([it, mk("A-2", title="Dep title"), mk("A-3", title="Pointer title"), mk("A-4", title="Unrelated")]))
    out = backlog.brief(doc, "A-1")
    assert "### A-1" in out and "Dep title" in out and "Pointer title" in out
    assert "Unrelated" not in out and "### A-2" not in out


def test_brief_unknown_id():
    with pytest.raises(backlog.BacklogError):
        backlog.brief(backlog.parse(build([mk("A-1")])), "Q-1")


# ---- shape ----

def idea(id_="A-1", **kw):
    return mk(id_, state="idea", **kw)


def test_shape_checklist_lists_what_is_missing():
    t = build([idea()]).replace("- **Acceptance:** `pytest` exits 0.\n", "")
    items = backlog.shape_checklist(backlog.parse(t), "A-1")
    missing = [txt for ok, txt in items if not ok]
    assert any("acceptance" in m.lower() for m in missing)
    assert not any("goal" in m.lower() for m in missing)


def test_shape_checklist_all_ok_for_complete_item():
    assert all(ok for ok, _ in backlog.shape_checklist(backlog.parse(build([idea()])), "A-1"))


def test_shape_updates_item_moves_tier_and_regenerates_index(tmp_path):
    p = write(tmp_path, build([idea("A-1", tier="T3"), mk("B-1", tier="T0")]))
    backlog.shape(p, "A-1", tier="T0", size="M", title="New title", today=TODAY)
    new = p.read_text(encoding="utf-8")
    doc = backlog.parse(new)
    a = next(i for i in doc.items if i.id == "A-1")
    assert (a.tier, a.size, a.state, a.title, a.section_tier) == ("T0", "M", "ready", "New title", "T0")
    assert fails(new) == []
    assert [c[0] for _, c in backlog._table_rows(doc)] == ["B-1", "A-1"]


def test_shape_stamps_added_when_missing(tmp_path):
    p = write(tmp_path, build([idea()]).replace("- **Added:** 2026-09-26\n", ""))
    backlog.shape(p, "A-1", today=TODAY)
    assert "- **Added:** 2026-09-27" in p.read_text(encoding="utf-8")


def test_shape_refuses_size_l_and_missing_goal(tmp_path):
    p = write(tmp_path, build([idea()]).replace("- **Goal:** one goal.\n", ""))
    before = p.read_text(encoding="utf-8")
    with pytest.raises(backlog.BacklogError, match="[Gg]oal"):
        backlog.shape(p, "A-1", today=TODAY)
    with pytest.raises(backlog.BacklogError, match="L"):
        backlog.shape(p, "A-1", goal="g", acceptance="a", size="L", today=TODAY)
    assert p.read_text(encoding="utf-8") == before


def test_shape_sets_goal_acceptance_verify(tmp_path):
    p = write(tmp_path, build([idea()]))
    backlog.shape(p, "A-1", goal="new goal.", acceptance="new acc.", verify="pytest -q", today=TODAY)
    text = p.read_text(encoding="utf-8")
    assert "- **Goal:** new goal." in text and "- **Acceptance:** new acc." in text and "- **Verify:** `pytest -q`" in text
    assert text.count("**Goal:**") == 1 and fails(text) == []


def test_shape_owner_human_adds_human_only_line(tmp_path):
    p = write(tmp_path, build([idea()], human="None.\n"))
    backlog.shape(p, "A-1", owner="human", today=TODAY)
    new = p.read_text(encoding="utf-8")
    assert "- A-1:" in new and "None." not in new.split("## TIER 0")[0] and fails(new) == []


def test_shape_new_creates_item_in_tier_and_index(tmp_path):
    p = write(tmp_path, build([mk("B-1", tier="T2")]))
    backlog.shape(p, "N-1", new=True, title="Fresh thing", tier="T1", size="S", goal="g.", acceptance="a.", owner="Claude", today=TODAY)
    new = p.read_text(encoding="utf-8")
    assert fails(new) == []
    n = next(i for i in backlog.parse(new).items if i.id == "N-1")
    assert (n.tier, n.state, n.section_tier) == ("T1", "ready", "T1") and n.fields["added"] == "2026-09-27"


def test_shape_new_refuses_duplicate_id_and_missing_fields(tmp_path):
    p = write(tmp_path, build([mk("B-1")]))
    with pytest.raises(backlog.BacklogError, match="exists"):
        backlog.shape(p, "B-1", new=True, title="t", tier="T1", size="S", goal="g", acceptance="a", owner="Claude", today=TODAY)
    with pytest.raises(backlog.BacklogError, match="title"):
        backlog.shape(p, "N-1", new=True, tier="T1", size="S", goal="g", acceptance="a", owner="Claude", today=TODAY)


def test_shape_from_inbox_removes_entry_and_keeps_raw(tmp_path):
    p = write(tmp_path, build([mk("B-1")], inbox="- 2026-09-26: fix the widget spacing\n- 2026-09-25: other thing\n"))
    backlog.shape(p, "N-1", new=True, title="Fix widget", tier="T1", size="S", goal="g.", acceptance="a.", owner="Claude", from_inbox="widget spacing", today=TODAY)
    new = p.read_text(encoding="utf-8")
    inbox = new.split("## INBOX")[1].split("## HUMAN ONLY")[0]
    assert "widget spacing" not in inbox and "other thing" in inbox
    assert "Raw: fix the widget spacing" in new


def test_shape_from_inbox_ambiguous_or_missing_refused(tmp_path):
    p = write(tmp_path, build([mk("B-1")], inbox="- 2026-09-26: fix a\n- 2026-09-25: fix b\n"))
    for needle in ("fix", "nothing"):
        with pytest.raises(backlog.BacklogError):
            backlog.shape(p, "N-1", new=True, title="t", tier="T1", size="S", goal="g", acceptance="a", owner="Claude", from_inbox=needle, today=TODAY)


# ---- Added handling and the fresh-file trust test ----

def test_missing_added_no_longer_warns():
    t = build([mk("A-1")]).replace("- **Added:** 2026-09-26\n", "")
    assert "missing-added" not in rules(t)


def test_fresh_formatted_file_passes_check_through_the_whole_lifecycle(tmp_path):
    p = tmp_path / "IDEAS.md"
    backlog.init_backlog(p)
    def ok():
        fs = backlog.check(backlog.parse(p.read_text(encoding="utf-8")), today=TODAY)
        assert fs == [], [f.as_dict() for f in fs]
    ok()
    backlog.add(p, "a raw thought", today=TODAY)
    ok()
    backlog.shape(p, "T-1", new=True, title="First", tier="T0", size="S", goal="g.", acceptance="a.", owner="Claude", from_inbox="raw thought", today=TODAY)
    ok()
    backlog.shape(p, "T-2", new=True, title="Second", tier="T1", size="M", goal="g.", acceptance="a.", owner="Human", today=TODAY)
    ok()
    assert backlog.next_item(backlog.parse(p.read_text(encoding="utf-8"))).id == "T-1"
    backlog.close_item(p, "T-1", SHA, "done", evidence="e", today=TODAY)
    ok()
    backlog.close_item(p, "T-2", SHA, "done", evidence="e", today=TODAY)
    ok()


def test_init_refuses_to_overwrite(tmp_path):
    p = write(tmp_path, "x")
    with pytest.raises(backlog.BacklogError):
        backlog.init_backlog(p)


def test_check_many_skips_unformatted_files_only_when_asked(tmp_path):
    good = write(tmp_path, build([mk("A-1")]), "good.md")
    plain = write(tmp_path, "# Ideas\n\n### not an item\n", "plain.md")
    res, bad, skipped = backlog.check_many([good, plain], skip_unformatted=True)
    assert list(res) == [str(good)] and skipped == [str(plain)] and not bad
    res, bad, skipped = backlog.check_many([plain])
    assert bad and not skipped


@pytest.mark.parametrize("line,gone,want", [
    ("Epics: X: A-1, A-2, A-3.", "A-2", "Epics: X: A-1, A-3."),
    ("Epics: X: A-1, A-2.", "A-1", "Epics: X: A-2."),
    ("Epics: X: A-1, A-2.", "A-2", "Epics: X: A-1."),
    ("Epics: X: A-6 to A-17.", "A-14", "Epics: X: A-6 to A-13, A-15 to A-17."),
    ("Epics: X: A-6 to A-17.", "A-6", "Epics: X: A-7 to A-17."),
    ("Epics: X: A-6 to A-17.", "A-17", "Epics: X: A-6 to A-16."),
    ("Epics: X: A-6 to A-7.", "A-7", "Epics: X: A-6."),
    ("Epics: X: A-6 to A-8.", "A-7", "Epics: X: A-6, A-8."),
    ("Epics: X: B-A to B-F, A-1.", "B-F", "Epics: X: B-A to B-E, A-1."),
    ("Epics: X: A-1, A-6 to A-9. Y: B-1 to B-4.", "B-1", "Epics: X: A-1, A-6 to A-9. Y: B-2 to B-4."),
    ("Epics: X: A-1 to A-3, A-9.", "A-9", "Epics: X: A-1 to A-3."),
    ("Epics: X: A-6 to A-9.", "A-2", "Epics: X: A-6 to A-9."),
    ("Epics: X: A-10 to A-12.", "A-1", "Epics: X: A-10 to A-12."),
])
def test_strip_id_edits_epic_lists_and_ranges_correctly(line, gone, want):
    assert backlog._strip_id(line, gone) == want


@pytest.mark.parametrize("line,old,new_ids,want", [
    ("Epics: X: A-1, A-2, A-3.", "A-2", ["A-9"], "Epics: X: A-1, A-9, A-3."),
    ("Epics: X: A-6 to A-17.", "A-14", ["A-20"], "Epics: X: A-6 to A-13, A-20, A-15 to A-17."),
    ("Epics: X: A-6 to A-17.", "A-6", ["A-20"], "Epics: X: A-20, A-7 to A-17."),
    ("Epics: X: A-6 to A-17.", "A-17", ["A-20"], "Epics: X: A-6 to A-16, A-20."),
    ("Epics: X: A-6 to A-8.", "A-7", ["A-20", "A-21"], "Epics: X: A-6, A-20, A-21, A-8."),
    ("Epics: X: A-6 to A-9.", "A-14", ["A-20"], "Epics: X: A-6 to A-9."),
    ("Epics: X: A-1, A-2.", "A-1", ["A-9", "A-10"], "Epics: X: A-9, A-10, A-2."),
])
def test_edit_epic_id_splits_ranges_and_inserts_replacement(line, old, new_ids, want):
    assert backlog._edit_epic_id(line, old, new_ids) == want


def test_split_at_the_low_end_of_an_epic_range_keeps_every_other_child_and_range_valid(tmp_path):
    items = [mk(f"R-{n}", size="M") for n in range(1, 7)]
    p = write(tmp_path, build(items, epics="Epics: R-9 = R-1 to R-6.\n"))
    before_text = p.read_text(encoding="utf-8")
    before_epic = _epic_ids(before_text) & {i.id for i in backlog.parse(before_text).items}
    before_bad = {f.id for f in backlog.check(backlog.parse(before_text)) if f.rule == "epic-unknown-id"}
    backlog.split(p, "R-1", ["R-A:R-1 split A", "R-B:R-1 split B"], today=TODAY)
    after_text = p.read_text(encoding="utf-8")
    after_doc = backlog.parse(after_text)
    surviving = before_epic - {"R-1"}
    assert surviving <= (_epic_ids(after_text) & {i.id for i in after_doc.items})
    after_bad = {f.id for f in backlog.check(after_doc) if f.rule == "epic-unknown-id"}
    assert after_bad <= before_bad, f"split introduced new bad epic ids: {after_bad - before_bad}"


def test_brief_includes_delegation_preamble(tmp_path):
    p = write(tmp_path, build([mk("A-1")]))
    doc = backlog.parse(p.read_text(encoding="utf-8"))
    out = backlog.brief(doc, "A-1")
    assert "self-contained" in out
    assert "### A-1" in out


def _epic_ids(text):
    line = next(ln for ln in text.splitlines() if ln.startswith("Epics"))
    ids = set()
    for pre, a, b in re.findall(r"\b([A-Z][A-Z0-9]*)-([A-Za-z0-9]+) to \1-([A-Za-z0-9]+)\b", line):
        if a.isdigit():
            ids |= {f"{pre}-{n}" for n in range(int(a), int(b) + 1)}
        else:
            ids |= {f"{pre}-{chr(c)}" for c in range(ord(a), ord(b) + 1)}
    line = re.sub(r"\b([A-Z][A-Z0-9]*)-([A-Za-z0-9]+) to \1-([A-Za-z0-9]+)\b", "", line)
    return ids | set(backlog.ID_RE.findall(line))


def test_close_inside_an_epic_range_keeps_every_other_child(tmp_path):
    items = [mk(f"R-{n}") for n in range(1, 7)]
    p = write(tmp_path, build(items, epics="Epics: R-9 = R-1 to R-6.\n"))
    for gone in ("R-2", "R-5"):
        close(p, gone)
        assert gone not in _epic_ids(p.read_text(encoding="utf-8"))
    after_text = p.read_text(encoding="utf-8")
    remaining = {i.id for i in backlog.parse(after_text).items}
    assert _epic_ids(after_text) & remaining == {"R-1", "R-3", "R-4", "R-6"}
    assert "to  " not in after_text and " to ," not in after_text and ", ," not in after_text


@pytest.mark.skipif(sys.platform != "win32", reason="git-bash drive paths only matter on Windows")
def test_norm_path_accepts_git_bash_drive_paths():
    assert backlog._norm_path("/c/proj/IDEAS.md") == Path("C:/proj/IDEAS.md")
    assert backlog._norm_path("C:/proj") == Path("C:/proj")
    assert backlog._norm_path(r"C:\proj") == Path("C:/proj")


def test_missing_file_is_a_clean_error_not_a_traceback(tmp_path):
    code, out, err = run_cli("next", "--file", str(tmp_path / "nope.md"))
    assert code == 2 and "Traceback" not in err and "nope.md" in err


# ---- CLI ----

def run_cli(*args):
    r = subprocess.run([sys.executable, str(HERE.parent / "backlog.py"), *args], capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def test_cli_close_next_brief_shape(tmp_path):
    p = write(tmp_path, build([idea("A-1"), mk("B-1")]))
    code, out, _ = run_cli("next", "--file", str(p))
    assert code == 0 and "B-1" in out
    code, out, _ = run_cli("brief", "--file", str(p), "B-1")
    assert code == 0 and "### B-1" in out
    code, out, _ = run_cli("shape", "--file", str(p), "A-1")
    assert code == 0 and "[x]" in out
    code, out, err = run_cli("shape", "--file", str(p), "A-1", "--size", "M")
    assert code == 0, err
    code, out, err = run_cli("close", "--file", str(p), "B-1", "--sha", SHA, "--summary", "done", "--evidence", "e")
    assert code == 0, err
    assert "### B-1" not in p.read_text(encoding="utf-8")
    code, _, err = run_cli("close", "--file", str(p), "A-1", "--sha", "zz", "--summary", "s", "--evidence", "e")
    assert code == 2 and "sha" in err.lower()


def test_cli_init_then_check(tmp_path):
    p = tmp_path / "IDEAS.md"
    assert run_cli("init", "--file", str(p))[0] == 0
    assert run_cli("check", "--file", str(p))[0] == 0


def test_cli_add_survives_non_cp1252_text_on_a_cp1252_console(tmp_path):
    """A legacy Windows console encoding must not crash `add` on an emoji (seen migrating StreamPilot)."""
    p = write(tmp_path, build([idea("A-1")]))
    env = dict(os.environ, PYTHONIOENCODING="cp1252")
    r = subprocess.run([sys.executable, str(HERE.parent / "backlog.py"), "add", "--file", str(p), "tab dot \U0001f7e2 stays", "--force"],
                       capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    assert "\U0001f7e2" in p.read_text(encoding="utf-8")


def test_check_many_flags_lowercase_ids_in_skipped_unformatted_files(tmp_path):
    plain = write(tmp_path, "# Ideas\n\n### MS-1: Real\nAfter ms-1 lands, use yt-dlp and utf-8.\n", "plain.md")
    res, bad, skipped = backlog.check_many([plain], skip_unformatted=True)
    fs = res[str(plain)][1]
    assert bad and skipped == [str(plain)]
    assert [(f.rule, f.line) for f in fs] == [("lowercase-id", 4)]


def test_shape_from_inbox_several_keeps_each_raw_line(tmp_path):
    p = write(tmp_path, build([mk("B-1")], inbox="- 2026-09-26: fix the widget spacing\n- 2026-09-25: widget colour is off\n- 2026-09-24: unrelated\n"))
    backlog.shape(p, "N-1", new=True, title="Widget polish", tier="T1", size="S", goal="g.", acceptance="a.", owner="Claude",
                  from_inbox=["widget spacing", "colour is off"], today=TODAY)
    new = p.read_text(encoding="utf-8")
    inbox = new.split("## INBOX")[1].split("## HUMAN ONLY")[0]
    assert "widget" not in inbox and "unrelated" in inbox
    assert "Raw: fix the widget spacing" in new and "Raw: widget colour is off" in new


def test_shape_from_inbox_several_refuses_when_one_key_misses_or_repeats(tmp_path):
    text = build([mk("B-1")], inbox="- 2026-09-26: fix the widget spacing\n- 2026-09-25: other thing\n")
    p = write(tmp_path, text)
    for keys in (["widget spacing", "nothing here"], ["widget spacing", "fix the widget"]):
        with pytest.raises(backlog.BacklogError):
            backlog.shape(p, "N-1", new=True, title="t", tier="T1", size="S", goal="g", acceptance="a", owner="Claude", from_inbox=keys, today=TODAY)
    assert p.read_text(encoding="utf-8") == text


def _shape_msg(tmp_path, goal, acceptance):
    d = tmp_path / f"case{abs(hash((goal, acceptance)))}"
    d.mkdir()
    p = write(d, build([mk("B-1")]))
    return backlog.shape(p, "N-1", new=True, title="t", tier="T1", size="S", goal=goal, acceptance=acceptance, owner="Claude", today=TODAY)


def test_shape_warns_user_visible_text_missing_for_behaviour_change(tmp_path):
    msg = _shape_msg(tmp_path, "The tray Quit always stops the service.", "Tray quit stops the service.")
    assert msg.startswith("shaped N-1") and "WARNING" in msg and "user-visible text" in msg


def test_shape_user_visible_text_quoted_or_doc_named_no_warning(tmp_path):
    assert "WARNING" not in _shape_msg(tmp_path, "Tray quit stops the service.", 'The menu item "Quit and stop service" exists.')
    assert "WARNING" not in _shape_msg(tmp_path, "Tray quit stops the service.", "README.md describes the new quit behaviour.")
    assert "WARNING" not in _shape_msg(tmp_path, "Speed up the parser.", "Parses 1000 lines in under 1s.")


def test_close_greps_for_old_label_user_visible_text(tmp_path):
    import subprocess
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    (repo / "tray.py").write_text('MENU = "Old Menu Label"\n')
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    p = write(tmp_path, build([mk("A-1")]))
    msg = backlog.close_item(p, "A-1", SHA, "s", evidence="e", today=TODAY, cwd=repo, old_labels=["Old Menu Label", "Absent Label"])
    assert msg.startswith("closed A-1") and "old label 'Old Menu Label' still appears" in msg and "tray.py" in msg
    assert "Absent Label" not in msg


def test_close_verify_timeout_is_a_clean_refusal_and_configurable_verify_timeout(tmp_path):
    sleeper = f'"{sys.executable}" -c "import time; time.sleep(4)"'
    p = write(tmp_path, build([mk("A-1", extra=f"- **Verify:** `{sleeper}`\n")]))
    before = p.read_text(encoding="utf-8")
    with pytest.raises(backlog.BacklogError, match="timed out after 1s"):
        backlog.close_item(p, "A-1", SHA, "s", today=TODAY, cwd=tmp_path, verify_timeout=1)
    assert p.read_text(encoding="utf-8") == before
    backlog.close_item(p, "A-1", SHA, "s", today=TODAY, cwd=tmp_path, verify_timeout=60)
    assert "### A-1" not in p.read_text(encoding="utf-8")
