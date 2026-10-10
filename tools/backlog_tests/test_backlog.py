"""Tests for backlog.py: parser, check, add, status. Run: python3 tools/backlog_tests/run.py"""
import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import backlog  # noqa: E402


def item(id_, title="Do the thing", tier="T1", size="S", state="ready", owner="Claude", extra=""):
    return (
        f"### {id_}: {title}\n"
        f"- **Tier / Size / State / Owner:** {tier} / {size} / {state} / {owner}\n"
        f"- **Added:** 2026-09-26\n"
        f"- **Goal:** one goal.\n"
        f"- **Acceptance:** `pytest` exits 0.\n"
        f"- **Depends on / blocks:** none / none.\n"
        f"{extra}\n"
    )


TIER_NAMES = {"T0": "TIER 0 BLOCKING", "T1": "TIER 1 CORE", "T2": "TIER 2 QUALITY", "T3": "TIER 3 POLISH", "T4": "TIER 4 PARKED"}


def build(items, inbox="Raw captures.\n", index=True, human=None, epics=""):
    """items: list of (tier, item_text, id, title, size, state, owner)."""
    rows = "".join(
        f"| {i} | {t} | {tier} | {s} | {st} | {o} | none |\n" for tier, _, i, t, s, st, o in sorted(items, key=lambda x: x[0])
    )
    dav = human if human is not None else "".join(
        f"- {i}: only Human.\n" for _, _, i, _, _, _, o in items if o == "Human"
    )
    out = "# Ideas\n\n## INDEX\n\n| id | title | tier | size | state | owner | blocked-by |\n|---|---|---|---|---|---|---|\n"
    out += rows if index else ""
    out += f"\n{epics}\n## INBOX\n\n{inbox}\n## HUMAN ONLY\n\n{dav}\n"
    for tier in TIER_NAMES:
        out += f"## {TIER_NAMES[tier]}\n\n"
        for it in items:
            if it[0] == tier:
                out += it[1] + "\n"
    return out


def mk(id_, tier="T1", title="Do the thing", size="S", state="ready", owner="Claude", extra=""):
    return (tier, item(id_, title, tier, size, state, owner, extra), id_, title, size, state, owner)


def rules(text, level=None):
    doc = backlog.parse(text)
    fs = backlog.check(doc)
    return {f.rule for f in fs if level is None or f.level == level}


def test_clean_backlog_passes():
    t = build([mk("A-1"), mk("A-2", tier="T0"), mk("B-1", owner="Human")])
    assert not rules(t, "fail")


def test_parse_items_and_fields():
    doc = backlog.parse(build([mk("A-1", tier="T0", size="M", state="blocked")]))
    (it,) = doc.items
    assert (it.id, it.tier, it.size, it.state, it.owner) == ("A-1", "T0", "M", "blocked", "Claude")
    assert it.title == "Do the thing"
    assert "goal" in it.fields and "acceptance" in it.fields


def test_missing_acceptance_fails():
    t = build([mk("A-1")]).replace("- **Acceptance:** `pytest` exits 0.\n", "")
    assert "missing-field" in rules(t, "fail")


def test_item_over_25_lines_fails():
    extra = "".join(f"- **Pointers:** line {n}\n" for n in range(25))
    assert "item-too-long" in rules(build([mk("A-1", extra=extra)]), "fail")


def test_multi_goal_heading_fails():
    extra = "- **Goal:** a second goal.\n"
    assert "multi-goal" in rules(build([mk("A-1", extra=extra)]), "fail")


def test_lettered_subitems_fail():
    extra = "- a. first\n- b. second\n- c. third\n"
    assert "multi-goal" in rules(build([mk("A-1", extra=extra)]), "fail")


def test_ready_size_l_fails():
    assert "ready-l" in rules(build([mk("A-1", size="L", state="ready")]), "fail")


def test_idea_l_ok():
    assert "ready-l" not in rules(build([mk("A-1", size="L", state="idea")]))


def test_t0_idea_fails():
    assert "t0-idea" in rules(build([mk("A-1", tier="T0", state="idea")]), "fail")


def test_t0_cap_warns():
    items = [mk(f"A-{n}", tier="T0") for n in range(11)]
    assert "t0-cap" in rules(build(items), "warn")
    assert "t0-cap" not in rules(build(items[:10]))


def test_idea_share_warns():
    items = [mk("A-1", state="idea"), mk("A-2", state="idea"), mk("A-3"), mk("A-4")]
    assert "idea-share" in rules(build(items), "warn")
    items = [mk("A-1", state="idea")] + [mk(f"B-{n}") for n in range(4)]
    assert "idea-share" not in rules(build(items))


@pytest.mark.parametrize("marker", ["- **Status:** done\n", "- ~~struck~~\n", "- [x] finished\n"])
def test_completion_markers_fail(marker):
    assert "completion-marker" in rules(build([mk("A-1", extra=marker)]), "fail")


def test_index_missing_row_fails():
    t = build([mk("A-1"), mk("A-2")])
    t = t.replace("| A-2 | Do the thing | T1 | S | ready | Claude | none |\n", "")
    assert "index-mismatch" in rules(t, "fail")


def test_index_wrong_state_fails():
    t = build([mk("A-1")]).replace("| T1 | S | ready |", "| T1 | S | idea |")
    assert "index-mismatch" in rules(t, "fail")


def test_index_not_in_tier_order_fails():
    t = build([mk("A-1", tier="T0"), mk("A-2", tier="T1")])
    rows = [ln for ln in t.splitlines(keepends=True) if ln.startswith("| A-")]
    t = t.replace("".join(rows), "".join(reversed(rows)))
    assert "index-mismatch" in rules(t, "fail")


def test_human_only_missing_item_fails():
    t = build([mk("A-1", owner="Human")], human="- nothing here\n")
    assert "human-only" in rules(t, "fail")


def test_epic_unknown_child_fails():
    t = build([mk("A-1")], epics="Epics (theme tags): REL: A-1, ZZ-9.\n")
    assert "epic-unknown-id" in rules(t, "fail")


def test_duplicate_id_fails():
    t = build([mk("A-1"), mk("A-1")])
    assert "duplicate-id" in rules(t, "fail")


def test_tier_section_mismatch_fails():
    t = build([mk("A-1", tier="T1")]).replace("T1 / S / ready", "T2 / S / ready")
    assert "tier-section" in rules(t, "fail")


def test_blocked_without_reason_fails():
    t = build([mk("A-1", state="blocked")])
    assert "blocked-no-reason" in rules(t, "fail")


def test_old_inbox_entry_fails_and_fresh_passes():
    old = (date.today() - timedelta(days=9)).isoformat()
    new = date.today().isoformat()
    assert "inbox-stale" in rules(build([mk("A-1")], inbox=f"- {old}: old thing\n"), "fail")
    assert "inbox-stale" not in rules(build([mk("A-1")], inbox=f"- {new}: fresh thing\n"))


def test_findings_carry_line_numbers():
    t = build([mk("A-1", size="L", state="ready")])
    (f,) = [f for f in backlog.check(backlog.parse(t)) if f.rule == "ready-l"]
    assert t.splitlines()[f.line - 1].startswith("### A-1")


# ---- status ----

def test_status_counts():
    t = build([mk("A-1", tier="T0"), mk("A-2", state="idea"), mk("A-3", owner="Human")])
    s = backlog.status(backlog.parse(t))
    assert s["items"] == 3
    assert s["by_tier"]["T0"] == 1
    assert s["by_state"]["idea"] == 1
    assert s["t0_size"] == 1
    assert round(s["idea_share"], 2) == 0.33
    assert s["top_ready"][0] == "A-1"


def test_status_text_is_short():
    t = build([mk(f"A-{n}") for n in range(20)])
    text = backlog.render_status("x", backlog.parse(t), backlog.check(backlog.parse(t)))
    assert len(text.splitlines()) <= 14


# ---- add ----

def test_add_appends_dated_entry_and_refuses_duplicate(tmp_path):
    f = tmp_path / "IDEAS.md"
    f.write_text(build([mk("A-1", title="Retry title variations before giving up")]), encoding="utf-8")
    msg = backlog.add(f, "brand new unrelated capture about tray colours")
    today = date.today().isoformat()
    assert f"- {today}: brand new unrelated capture about tray colours" in f.read_text(encoding="utf-8")
    assert "INBOX" in msg
    with pytest.raises(backlog.BacklogError):
        backlog.add(f, "Retry title variations before giving up please")
    backlog.add(f, "Retry title variations before giving up please", force=True)
    assert f.read_text(encoding="utf-8").count("giving up please") == 1


def test_add_newest_first_and_file_still_checks(tmp_path):
    f = tmp_path / "IDEAS.md"
    f.write_text(build([mk("A-1")]), encoding="utf-8")
    backlog.add(f, "first capture zebra")
    backlog.add(f, "second capture giraffe")
    text = f.read_text(encoding="utf-8")
    assert text.index("giraffe") < text.index("zebra")
    assert not rules(text, "fail")


def test_add_without_inbox_creates_it_before_first_section(tmp_path):
    f = tmp_path / "IDEAS.md"
    f.write_text("# Ideas\n\nintro prose\n\n## TOP\n\nbody\n\n## LATER\n\nmore\n", encoding="utf-8")
    backlog.add(f, "something new", today=date(2026, 9, 29))
    text = f.read_text(encoding="utf-8")
    assert text == (
        "# Ideas\n\nintro prose\n\n## INBOX\n\nRaw captures, newest first, not yet shaped.\n\n"
        "- 2026-09-29: something new\n\n## TOP\n\nbody\n\n## LATER\n\nmore\n"
    )


def test_add_without_inbox_creates_it_after_index(tmp_path):
    f = tmp_path / "IDEAS.md"
    f.write_text("# Ideas\n\n## INDEX\n\n| id |\n|---|\n\n## HUMAN ONLY\n\nNone.\n", encoding="utf-8")
    backlog.add(f, "something new", today=date(2026, 9, 29))
    text = f.read_text(encoding="utf-8")
    assert text.index("## INDEX") < text.index("## INBOX") < text.index("## HUMAN ONLY")
    assert text.count("## INBOX") == 1


def test_add_without_any_heading_appends_inbox(tmp_path):
    f = tmp_path / "IDEAS.md"
    f.write_text("# Ideas\n\nno structure\n", encoding="utf-8")
    backlog.add(f, "something", today=date(2026, 9, 29))
    text = f.read_text(encoding="utf-8")
    assert text.startswith("# Ideas\n\nno structure\n")
    assert text.rstrip().endswith("- 2026-09-29: something")
    backlog.add(f, "second zebra thing", today=date(2026, 9, 29))
    assert f.read_text(encoding="utf-8").count("## INBOX") == 1


def test_add_created_inbox_keeps_crlf(tmp_path):
    f = tmp_path / "IDEAS.md"
    f.write_bytes(b"# Ideas\r\n\r\n## TOP\r\n\r\nbody\r\n")
    backlog.add(f, "something", today=date(2026, 9, 29))
    data = f.read_bytes()
    assert b"\n" not in data.replace(b"\r\n", b"")
    assert b"## INBOX" in data


def test_check_treats_created_inbox_like_any_inbox(tmp_path):
    f = tmp_path / "IDEAS.md"
    f.write_text("# Ideas\n\n## TOP\n\nbody\n", encoding="utf-8")
    backlog.add(f, "old capture", today=date(2026, 1, 1))
    doc = backlog.parse(f.read_text(encoding="utf-8"))
    assert "inbox-stale" in {x.rule for x in backlog.check(doc, today=date(2026, 9, 29))}
    assert "inbox-missing" not in {x.rule for x in backlog.check(doc, today=date(2026, 9, 29))}


def test_check_warns_when_formatted_file_lacks_inbox():
    text = build([mk("A-1")]).replace("## INBOX\n\nRaw captures.\n\n", "")
    assert "inbox-missing" in rules(text, "warn")
    assert "inbox-missing" not in rules(text, "fail")


def test_check_silent_on_inbox_for_legacy_file_without_index():
    assert "inbox-missing" not in rules("# Ideas\n\n## TOP\n\nbody\n")


def test_add_requires_nonempty_text(tmp_path):
    f = tmp_path / "IDEAS.md"
    f.write_text(build([mk("A-1")]), encoding="utf-8")
    with pytest.raises(backlog.BacklogError):
        backlog.add(f, "   ")


# ---- CLI ----

def test_cli_check_json_and_exit_code(tmp_path):
    good = tmp_path / "good.md"
    good.write_text(build([mk("A-1")]), encoding="utf-8")
    bad = tmp_path / "bad.md"
    bad.write_text(build([mk("A-1", size="L")]), encoding="utf-8")
    script = str(HERE.parent / "backlog.py")
    r = subprocess.run([sys.executable, script, "check", str(good), "--json"], capture_output=True, text=True)
    assert r.returncode == 0 and json.loads(r.stdout)["ok"] is True
    r = subprocess.run([sys.executable, script, "check", str(bad), "--json"], capture_output=True, text=True)
    assert r.returncode == 1
    assert any(f["rule"] == "ready-l" for f in json.loads(r.stdout)["findings"])


def test_cli_status_and_add(tmp_path):
    f = tmp_path / "IDEAS.md"
    f.write_text(build([mk("A-1")]), encoding="utf-8")
    script = str(HERE.parent / "backlog.py")
    r = subprocess.run([sys.executable, script, "status", "--file", str(f)], capture_output=True, text=True)
    assert r.returncode == 0 and "A-1" in r.stdout
    r = subprocess.run([sys.executable, script, "add", "--file", str(f), "hello capture"], capture_output=True, text=True)
    assert r.returncode == 0 and "hello capture" in f.read_text(encoding="utf-8")


def test_resolve_repo_follows_configured_locations_in_order(tmp_path):
    base = tmp_path / "ws"
    (base / "backlogs" / "R1").mkdir(parents=True)
    (base / "backlogs" / "R1" / "IDEAS.md").write_text("x")
    assert backlog.resolve_repo("R1", base=base).name == "IDEAS.md"
    (tmp_path / "Sibling" / "docs").mkdir(parents=True)
    (tmp_path / "Sibling" / "docs" / "IDEAS.md").write_text("x")
    assert "Sibling" in str(backlog.resolve_repo("Sibling", base=base))
    with pytest.raises(backlog.BacklogError):
        backlog.resolve_repo("Nope", base=base)


def test_all_backlogs_lists_every_location(tmp_path):
    base = tmp_path / "ws"
    (base / "backlogs" / "R1").mkdir(parents=True)
    (base / "backlogs" / "R1" / "IDEAS.md").write_text("x")
    (tmp_path / "Sibling" / "docs").mkdir(parents=True)
    (tmp_path / "Sibling" / "docs" / "IDEAS.md").write_text("x")
    names = {p.parent.name if p.parent.name != "docs" else p.parent.parent.name for p in backlog.all_backlogs(base=base)}
    assert names == {"R1", "Sibling"}


def test_config_names_the_two_owners(tmp_path):
    cfg = tmp_path / "c.json"
    cfg.write_text('{"agent_owner": "Bot", "human_owner": "Ana"}', encoding="utf-8")
    loaded = backlog.load_config(cfg)
    assert (loaded["agent_owner"], loaded["human_owner"]) == ("Bot", "Ana")
    assert loaded["locations"] == backlog.DEFAULT_SETTINGS["locations"]
    assert backlog.load_config(tmp_path / "missing.json")["agent_owner"] == backlog.DEFAULT_SETTINGS["agent_owner"]


def test_lowercase_id_in_heading_and_index_fails():
    t = build([mk("ms-1")])
    fs = [f for f in backlog.check(backlog.parse(t)) if f.rule == "lowercase-id"]
    assert len(fs) == 2  # heading + index row
    assert "MS-1" in fs[0].msg


def test_lowercase_id_in_blocked_by_cell_fails():
    t = build([mk("MS-1"), mk("MS-2")]).replace("| MS-2 | Do the thing | T1 | S | ready | Claude | none |", "| MS-2 | Do the thing | T1 | S | ready | Claude | ms-1 |")
    assert "lowercase-id" in rules(t, "fail")


def test_uppercase_ids_pass_lowercase_rule():
    assert "lowercase-id" not in rules(build([mk("MS-1")]))


def test_shape_new_uppercases_minted_id(tmp_path):
    p = tmp_path / "IDEAS.md"
    p.write_text(build([mk("MS-1")]), encoding="utf-8")
    backlog.shape(p, "ms-9", new=True, title="T", tier="T1", size="S", goal="g", acceptance="`true` exits 0", owner="Claude")
    text = p.read_text(encoding="utf-8")
    assert "### MS-9:" in text and "ms-9" not in text


def test_split_uppercases_child_ids(tmp_path):
    p = tmp_path / "IDEAS.md"
    p.write_text(build([mk("MS-1", size="M")]), encoding="utf-8")
    backlog.split(p, "MS-1", ["ms-2:A", "ms-3:B"])
    text = p.read_text(encoding="utf-8")
    assert "### MS-2:" in text and "### MS-3:" in text and "ms-2" not in text

