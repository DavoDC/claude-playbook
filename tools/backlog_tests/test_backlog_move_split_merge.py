"""Tests for backlog.py move, split, merge. Run: python3 tools/backlog_tests/run.py"""
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import backlog  # noqa: E402
from test_backlog import build, mk  # noqa: E402

TODAY = date(2026, 9, 27)


def write(tmp_path, text, name="IDEAS.md"):
    p = tmp_path / name
    p.write_bytes(text.encode("utf-8"))
    return p


def fails(text):
    return sorted(f.rule for f in backlog.check(backlog.parse(text), today=TODAY) if f.level == "fail")


def run_cli(*args):
    r = subprocess.run([sys.executable, str(HERE.parent / "backlog.py"), *args], capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


# ---- move ----

def test_move_before_reorders_index_only_same_tier_and_section(tmp_path):
    p = write(tmp_path, build([mk("A-1"), mk("A-2"), mk("A-3")]))
    before = p.read_text(encoding="utf-8")
    backlog.move(p, "A-3", before="A-1", today=TODAY)
    new = p.read_text(encoding="utf-8")
    rows = [c[0] for _, c in backlog._table_rows(backlog.parse(new))]
    assert rows == ["A-3", "A-1", "A-2"]
    doc = backlog.parse(new)
    a3 = next(i for i in doc.items if i.id == "A-3")
    assert a3.tier == "T1" and a3.section_tier == "T1"
    # item bodies (outside INDEX) are unchanged, only the table order moved
    assert before.split("## TIER 1")[1] == new.split("## TIER 1")[1]
    assert fails(new) == []


def test_move_tier_changes_tier_line_section_and_index_row(tmp_path):
    p = write(tmp_path, build([mk("A-1", tier="T2"), mk("B-1", tier="T0")]))
    backlog.move(p, "A-1", tier="T0", today=TODAY)
    new = p.read_text(encoding="utf-8")
    doc = backlog.parse(new)
    a1 = next(i for i in doc.items if i.id == "A-1")
    assert (a1.tier, a1.section_tier) == ("T0", "T0")
    row = next(c for _, c in backlog._table_rows(doc) if c[0] == "A-1")
    assert row[2] == "T0"
    assert "### A-1" in new.split("## TIER 0")[1].split("## TIER 1")[0]
    assert fails(new) == []


def test_move_refuses_before_across_tiers_and_writes_nothing(tmp_path):
    p = write(tmp_path, build([mk("A-1", tier="T0"), mk("A-2", tier="T1")]))
    before = p.read_text(encoding="utf-8")
    with pytest.raises(backlog.BacklogError):
        backlog.move(p, "A-2", before="A-1", today=TODAY)
    assert p.read_text(encoding="utf-8") == before


def test_move_refuses_both_flags_and_neither(tmp_path):
    p = write(tmp_path, build([mk("A-1"), mk("A-2")]))
    before = p.read_text(encoding="utf-8")
    with pytest.raises(backlog.BacklogError):
        backlog.move(p, "A-1", before="A-2", tier="T0", today=TODAY)
    with pytest.raises(backlog.BacklogError):
        backlog.move(p, "A-1", today=TODAY)
    assert p.read_text(encoding="utf-8") == before


def test_move_refuses_unknown_id(tmp_path):
    p = write(tmp_path, build([mk("A-1"), mk("A-2")]))
    before = p.read_text(encoding="utf-8")
    with pytest.raises(backlog.BacklogError):
        backlog.move(p, "Z-9", before="A-1", today=TODAY)
    with pytest.raises(backlog.BacklogError):
        backlog.move(p, "A-1", before="Z-9", today=TODAY)
    with pytest.raises(backlog.BacklogError):
        backlog.move(p, "A-1", tier="T5", today=TODAY)
    assert p.read_text(encoding="utf-8") == before


# ---- split ----

def test_split_creates_children_removes_original_and_passes_check(tmp_path):
    p = write(tmp_path, build([mk("A-1", title="Original thing")]))
    backlog.split(p, "A-1", ["A-1a:First half", "A-1b:Second half"], today=TODAY)
    new = p.read_text(encoding="utf-8")
    assert "### A-1:" not in new
    doc = backlog.parse(new)
    ids = {i.id for i in doc.items}
    assert {"A-1a", "A-1b"} <= ids
    a1a = next(i for i in doc.items if i.id == "A-1a")
    assert a1a.title == "First half" and a1a.tier == "T1" and a1a.section_tier == "T1"
    assert fails(new) == []


def test_split_custom_title_and_default_title(tmp_path):
    p = write(tmp_path, build([mk("A-1", title="Shared title")]))
    backlog.split(p, "A-1", ["A-1a:Custom title", "A-1b"], today=TODAY)
    doc = backlog.parse(p.read_text(encoding="utf-8"))
    titles = {i.id: i.title for i in doc.items}
    assert titles["A-1a"] == "Custom title"
    assert titles["A-1b"] == "Shared title"


def test_split_refuses_fewer_than_two_children(tmp_path):
    p = write(tmp_path, build([mk("A-1")]))
    before = p.read_text(encoding="utf-8")
    with pytest.raises(backlog.BacklogError):
        backlog.split(p, "A-1", ["A-1a"], today=TODAY)
    assert p.read_text(encoding="utf-8") == before


def test_split_refuses_duplicate_new_id_and_writes_nothing(tmp_path):
    p = write(tmp_path, build([mk("A-1"), mk("A-2")]))
    before = p.read_text(encoding="utf-8")
    with pytest.raises(backlog.BacklogError):
        backlog.split(p, "A-1", ["A-2", "A-3"], today=TODAY)
    with pytest.raises(backlog.BacklogError):
        backlog.split(p, "A-1", ["A-3", "A-3"], today=TODAY)
    assert p.read_text(encoding="utf-8") == before


def test_split_inherits_fields_and_updates_epic_line(tmp_path):
    extra = "- **Pointers:** see docs/x.md\n"
    t = build([mk("A-1", extra=extra), mk("A-2")], epics="Epics: X: A-1, A-2.\n")
    p = write(tmp_path, t)
    backlog.split(p, "A-1", ["A-1a", "A-1b"], today=TODAY)
    new = p.read_text(encoding="utf-8")
    doc = backlog.parse(new)
    a1a = next(i for i in doc.items if i.id == "A-1a")
    assert a1a.fields.get("pointers") == "see docs/x.md"
    epics_line = next(ln for ln in new.splitlines() if ln.startswith("Epics"))
    assert "A-1a" in epics_line and "A-1b" in epics_line and "A-1," not in epics_line
    assert fails(new) == []


# ---- merge ----

def test_merge_combines_depends_and_pointers_without_duplication(tmp_path):
    a = mk("A-1", extra="- **Pointers:** shared.md, only-a.md\n")
    a = (a[0], a[1].replace("- **Depends on / blocks:** none / none.\n", "- **Depends on / blocks:** A-9 / none.\n")) + a[2:]
    b = mk("A-2", extra="- **Pointers:** shared.md, only-b.md\n")
    b = (b[0], b[1].replace("- **Depends on / blocks:** none / none.\n", "- **Depends on / blocks:** A-9, A-8 / none.\n")) + b[2:]
    p = write(tmp_path, build([a, b, mk("A-8", title="dep"), mk("A-9", title="dep2")]))
    backlog.merge(p, "A-1", "A-2", today=TODAY)
    new = p.read_text(encoding="utf-8")
    doc = backlog.parse(new)
    ids = {i.id for i in doc.items}
    assert "A-2" not in ids and "A-1" in ids
    a1 = next(i for i in doc.items if i.id == "A-1")
    assert a1.fields["depends"].startswith("A-9, A-8")
    assert a1.fields["pointers"] == "shared.md, only-a.md, only-b.md"
    assert fails(new) == []


def test_merge_keeps_own_goal_and_acceptance_unless_overridden(tmp_path):
    a = mk("A-1")
    a = (a[0], a[1].replace("- **Goal:** one goal.\n", "- **Goal:** goal A.\n")) + a[2:]
    b = mk("A-2")
    b = (b[0], b[1].replace("- **Goal:** one goal.\n", "- **Goal:** goal B.\n")) + b[2:]
    p = write(tmp_path, build([a, b]))
    backlog.merge(p, "A-1", "A-2", today=TODAY)
    doc = backlog.parse(p.read_text(encoding="utf-8"))
    a1 = next(i for i in doc.items if i.id == "A-1")
    assert a1.fields["goal"] == "goal A."
    p2 = write(tmp_path, build([a, b]), name="IDEAS2.md")
    backlog.merge(p2, "A-1", "A-2", goal="overridden goal.", acceptance="overridden acc.", today=TODAY)
    doc2 = backlog.parse(p2.read_text(encoding="utf-8"))
    a1b = next(i for i in doc2.items if i.id == "A-1")
    assert a1b.fields["goal"] == "overridden goal." and a1b.fields["acceptance"] == "overridden acc."
    assert fails(p2.read_text(encoding="utf-8")) == []


def test_merge_refuses_cross_tier_and_writes_nothing(tmp_path):
    p = write(tmp_path, build([mk("A-1", tier="T0"), mk("A-2", tier="T1")]))
    before = p.read_text(encoding="utf-8")
    with pytest.raises(backlog.BacklogError):
        backlog.merge(p, "A-1", "A-2", today=TODAY)
    assert p.read_text(encoding="utf-8") == before


def test_merge_refuses_unknown_id(tmp_path):
    p = write(tmp_path, build([mk("A-1")]))
    before = p.read_text(encoding="utf-8")
    with pytest.raises(backlog.BacklogError):
        backlog.merge(p, "A-1", "Z-9", today=TODAY)
    with pytest.raises(backlog.BacklogError):
        backlog.merge(p, "Z-9", "A-1", today=TODAY)
    assert p.read_text(encoding="utf-8") == before


def test_merge_repoints_epic_reference_from_id2_to_id(tmp_path):
    t = build([mk("A-1"), mk("A-2"), mk("A-3")], epics="Epics: X: A-1, A-2, A-3.\n")
    p = write(tmp_path, t)
    backlog.merge(p, "A-1", "A-2", today=TODAY)
    new = p.read_text(encoding="utf-8")
    epics_line = next(ln for ln in new.splitlines() if ln.startswith("Epics"))
    assert "A-2" not in epics_line
    assert epics_line.count("A-1") == 1
    assert fails(new) == []


# ---- CLI ----

def test_cli_move_split_merge(tmp_path):
    p = write(tmp_path, build([mk("A-1"), mk("A-2"), mk("A-3", tier="T0")]))
    code, out, err = run_cli("move", "--file", str(p), "A-2", "--before", "A-1")
    assert code == 0, err
    rows = [c[0] for _, c in backlog._table_rows(backlog.parse(p.read_text(encoding="utf-8")))]
    assert rows.index("A-2") < rows.index("A-1")

    code, out, err = run_cli("split", "--file", str(p), "A-1", "--into", "A-1a:One", "A-1b:Two")
    assert code == 0, err
    doc = backlog.parse(p.read_text(encoding="utf-8"))
    assert {"A-1a", "A-1b"} <= {i.id for i in doc.items}

    code, out, err = run_cli("merge", "--file", str(p), "A-1a", "A-1b")
    assert code == 0, err
    doc = backlog.parse(p.read_text(encoding="utf-8"))
    ids = {i.id for i in doc.items}
    assert "A-1a" in ids and "A-1b" not in ids


def test_merge_keeps_text_of_removed_item(tmp_path):
    a = mk("A-1")
    a = (a[0], a[1].replace("- **Goal:** one goal.\n", "- **Goal:** goal A.\n")) + a[2:]
    b = mk("A-2", extra="- **Evidence / origin:** Raw: seen twice.\n")
    b = (b[0], b[1].replace("- **Goal:** one goal.\n", "- **Goal:** goal B unique.\n").replace("`pytest` exits 0.", "acceptance B unique.")) + b[2:]
    p = write(tmp_path, build([a, b]))
    backlog.merge(p, "A-1", "A-2", today=TODAY)
    new = p.read_text(encoding="utf-8")
    a1 = next(i for i in backlog.parse(new).items if i.id == "A-1")
    assert a1.fields["goal"] == "goal A."
    ev = a1.fields.get("evidence", "")
    assert "goal B unique" in ev and "acceptance B unique" in ev and "seen twice" in ev
    assert fails(new) == []
