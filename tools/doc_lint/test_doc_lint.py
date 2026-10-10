"""Tests for doc_lint. Run: python3 -m unittest test_doc_lint -v (from this folder)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import doc_lint  # noqa: E402

EM = chr(0x2014)
EN = chr(0x2013)
DASH_CLASS = "[" + EN + EM + "]"


def make_tree(files):
    d = tempfile.mkdtemp(prefix="doclint_")
    root = Path(d)
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return root


def run_rules(files, rules):
    root = make_tree(files)
    return doc_lint.run({"rules": rules}, root, root)


def ids(findings):
    return [f.rule for f in findings]


class ForbiddenPattern(unittest.TestCase):
    def test_flags_em_and_en_dash_with_line(self):
        f = run_rules({"a.md": "ok\nbad " + EM + " here\nalso " + EN + " there\n"},
                      [{"id": "dash", "type": "forbidden-pattern", "files": ["*.md"], "patterns": [DASH_CLASS]}])
        self.assertEqual([(x.line, x.rule) for x in f], [(2, "dash"), (3, "dash")])

    def test_clean_file_has_no_findings(self):
        f = run_rules({"a.md": "fine - text\n"},
                      [{"id": "dash", "type": "forbidden-pattern", "files": ["*.md"], "patterns": [DASH_CLASS]}])
        self.assertEqual(f, [])

    def test_exclude_glob(self):
        f = run_rules({"a.md": "x" + EM + "y\n", "skip/b.md": "x" + EM + "y\n"},
                      [{"id": "d", "type": "forbidden-pattern", "files": ["**/*.md"], "exclude": ["skip/**"], "patterns": [EM]}])
        self.assertEqual([x.path for x in f], ["a.md"])

    def test_skip_code_option(self):
        text = "```\nWIDGET here\n```\nWIDGET out\n"
        f = run_rules({"a.md": text}, [{"id": "t", "type": "forbidden-pattern", "files": ["*.md"],
                                         "patterns": ["\\bWIDGET\\b"], "skip_code": True}])
        self.assertEqual([x.line for x in f], [4])


class RequiredPattern(unittest.TestCase):
    RULE = {"id": "tier", "type": "required-pattern", "files": ["docs/*.md"], "pattern": "^> \\*\\*(Core|Field note)\\.", "within_lines": 4}

    def test_missing_flagged(self):
        f = run_rules({"docs/a.md": "# A\n\ntext\n"}, [self.RULE])
        self.assertEqual(ids(f), ["tier"])

    def test_present_within_window(self):
        f = run_rules({"docs/a.md": "# A\n\n> **Core.** hi\n"}, [self.RULE])
        self.assertEqual(f, [])

    def test_present_outside_window_flagged(self):
        f = run_rules({"docs/a.md": "# A\n\n\n\n\n> **Core.** hi\n"}, [self.RULE])
        self.assertEqual(ids(f), ["tier"])


class MaxLineShape(unittest.TestCase):
    RULE = {"id": "wrap", "type": "max-line-shape", "files": ["*.md"]}

    def test_hard_wrapped_paragraph_flagged_once(self):
        f = run_rules({"a.md": "first line of prose\nsecond line of prose\nthird\n"}, [self.RULE])
        self.assertEqual([(x.line) for x in f], [1])

    def test_lists_tables_headings_code_quotes_exempt(self):
        text = "# H\n\n- a\n- b\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n> q1\n> q2\n\n```\nx\ny\n```\n\n1. one\n2. two\n"
        self.assertEqual(run_rules({"a.md": text}, [self.RULE]), [])

    def test_yaml_front_matter_exempt(self):
        text = "---\nname: x\ndescription: y\n---\n\nbody\n"
        self.assertEqual(run_rules({"a.md": text}, [self.RULE]), [])

    def test_single_line_paragraphs_ok(self):
        self.assertEqual(run_rules({"a.md": "one\n\ntwo\n"}, [self.RULE]), [])


class IndexSync(unittest.TestCase):
    RULE = {"id": "idx", "type": "index-sync", "index": "README.md", "files": ["docs/*.md"]}

    def test_unlisted_file_flagged(self):
        f = run_rules({"README.md": "[a](docs/a.md)\n", "docs/a.md": "x", "docs/b.md": "x"}, [self.RULE])
        self.assertEqual(len(f), 1)
        self.assertIn("docs/b.md", f[0].message)

    def test_dead_link_flagged_with_line(self):
        f = run_rules({"README.md": "x\n[a](docs/a.md)\n[gone](docs/gone.md)\n", "docs/a.md": "x"}, [self.RULE])
        self.assertEqual([(x.path, x.line) for x in f], [("README.md", 3)])

    def test_synced_clean(self):
        f = run_rules({"README.md": "[a](docs/a.md) [L](LICENSE)\n", "docs/a.md": "x"}, [self.RULE])
        self.assertEqual(f, [])

    def test_directory_link_covers_skill_folder(self):
        rule = {"id": "idx", "type": "index-sync", "index": "skills/README.md", "files": ["skills/*/SKILL.md"]}
        f = run_rules({"skills/README.md": "[x](x/)\n", "skills/x/SKILL.md": "x"}, [rule])
        self.assertEqual(f, [])

    def test_mention_mode(self):
        rule = {"id": "m", "type": "index-sync", "index": "docs/08.md", "files": ["skills/*/SKILL.md"],
                "mode": "mention", "name_from": "parent"}
        files = {"docs/08.md": "uses `/alpha` often", "skills/alpha/SKILL.md": "x", "skills/beta/SKILL.md": "x"}
        f = run_rules(files, [rule])
        self.assertEqual(len(f), 1)
        self.assertIn("beta", f[0].message)


class LinkResolve(unittest.TestCase):
    RULE = {"id": "link", "type": "link-resolve", "files": ["**/*.md"]}

    def test_dead_file_link(self):
        f = run_rules({"a.md": "x\n[b](b.md)\n"}, [self.RULE])
        self.assertEqual([(x.line, x.rule) for x in f], [(2, "link")])

    def test_good_link_and_external_ignored(self):
        f = run_rules({"a.md": "[b](b.md) [w](https://x.invalid/y) [m](mailto:a@b.c)\n", "b.md": "# B\n"}, [self.RULE])
        self.assertEqual(f, [])

    def test_anchor_same_file_and_cross_file(self):
        files = {"a.md": "# Top\n[ok](#top) [bad](#nope) [x](b.md#sec-one) [y](b.md#missing)\n",
                 "b.md": "# B\n## Sec One\n"}
        f = run_rules(files, [self.RULE])
        self.assertEqual(len(f), 2)
        self.assertTrue(all("anchor" in x.message for x in f))

    def test_links_in_code_ignored(self):
        f = run_rules({"a.md": "`[a](nope.md)`\n```\n[a](nope.md)\n```\n"}, [self.RULE])
        self.assertEqual(f, [])


class NameReference(unittest.TestCase):
    RULE = {"id": "name", "type": "name-reference", "files": ["*.md"], "scope": "inline-code",
            "pattern": "^/([a-z][a-z0-9-]*)$", "exists_in": ["skills/{name}/SKILL.md"], "allow": ["help"]}

    def test_unknown_flagged_known_and_allowed_ok(self):
        files = {"a.md": "use `/real` and `/help` and `/ghost`\n", "skills/real/SKILL.md": "x"}
        f = run_rules(files, [self.RULE])
        self.assertEqual(len(f), 1)
        self.assertIn("ghost", f[0].message)

    def test_allow_file(self):
        rule = dict(self.RULE, allow=[], allow_file="allow.txt")
        files = {"a.md": "`/ghost`\n", "allow.txt": "# c\nghost\n"}
        root = make_tree(files)
        f = doc_lint.run({"rules": [rule]}, root, root)
        self.assertEqual(f, [])


class HeadingUniqueness(unittest.TestCase):
    RULE = {"id": "dup", "type": "heading-uniqueness-across-files", "files": ["docs/*.md"], "ignore": ["^Summary$"]}

    def test_same_heading_two_files(self):
        f = run_rules({"docs/a.md": "## Setup\n", "docs/b.md": "## setup\n"}, [self.RULE])
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].path, "docs/b.md")

    def test_same_file_and_ignored_not_flagged(self):
        f = run_rules({"docs/a.md": "## Setup\n## Setup\n## Summary\n", "docs/b.md": "## Summary\n"}, [self.RULE])
        self.assertEqual(f, [])

    def test_headings_in_code_ignored(self):
        f = run_rules({"docs/a.md": "## Setup\n", "docs/b.md": "```\n## Setup\n```\n"}, [self.RULE])
        self.assertEqual(f, [])


class MaxWords(unittest.TestCase):
    def test_over_limit(self):
        f = run_rules({"a.md": "w " * 11}, [{"id": "mw", "type": "max-words", "files": ["*.md"], "limit": 10}])
        self.assertEqual(ids(f), ["mw"])

    def test_code_not_counted(self):
        f = run_rules({"a.md": "a b\n```\n" + "x " * 50 + "\n```\n"},
                      [{"id": "mw", "type": "max-words", "files": ["*.md"], "limit": 10}])
        self.assertEqual(f, [])


class ForbiddenTermsFile(unittest.TestCase):
    def test_terms_read_from_file_and_masked(self):
        files = {"a.md": "nothing\nmentions SecretThing here\n", "terms.txt": "# comment\n\nsecretthing\n"}
        root = make_tree(files)
        rule = {"id": "terms", "type": "forbidden-terms-file", "files": ["a.md"], "terms_file": "terms.txt"}
        f = doc_lint.run({"rules": [rule]}, root, root)
        self.assertEqual([(x.line, x.rule) for x in f], [(2, "terms")])
        self.assertNotIn("secretthing", f[0].message.lower())

    def test_missing_terms_file_is_config_error(self):
        root = make_tree({"a.md": "x"})
        rule = {"id": "terms", "type": "forbidden-terms-file", "files": ["*.md"], "terms_file": "nope.txt"}
        with self.assertRaises(doc_lint.ConfigError):
            doc_lint.run({"rules": [rule]}, root, root)


class SequentialNumbering(unittest.TestCase):
    def rule(self, **kw):
        r = {"id": "seq", "type": "sequential-numbering", "files": ["docs/*.md"],
             "number_pattern": "^(\\d+)-", "unnumbered_last": ["checklist.md"]}
        r.update(kw)
        return r

    def test_gapless_passes(self):
        f = run_rules({"docs/01-a.md": "# Part 1: A\n", "docs/02-b.md": "# Part 2: B\n", "docs/checklist.md": "# C\n"},
                      [self.rule(heading_part=True)])
        self.assertEqual(f, [])

    def test_gap_flagged(self):
        f = run_rules({"docs/01-a.md": "x\n", "docs/03-b.md": "x\n"}, [self.rule()])
        self.assertEqual(ids(f), ["seq"])
        self.assertIn("gap", f[0].message)

    def test_shared_number_flagged(self):
        f = run_rules({"docs/01-a.md": "x\n", "docs/02-b.md": "x\n", "docs/02-c.md": "x\n"}, [self.rule()])
        self.assertTrue(any("shared" in x.message for x in f))

    def test_must_start_at_one(self):
        f = run_rules({"docs/02-a.md": "x\n"}, [self.rule()])
        self.assertEqual(ids(f), ["seq"])

    def test_unlisted_unnumbered_flagged(self):
        f = run_rules({"docs/01-a.md": "x\n", "docs/notes.md": "x\n"}, [self.rule()])
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].path, "docs/notes.md")

    def test_heading_part_mismatch(self):
        f = run_rules({"docs/01-a.md": "# Part 2: A\n"}, [self.rule(heading_part=True)])
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].line, 1)

    def test_heading_missing_part_flagged(self):
        f = run_rules({"docs/01-a.md": "# Title\n"}, [self.rule(heading_part=True)])
        self.assertEqual(len(f), 1)

    def test_heading_not_checked_by_default(self):
        f = run_rules({"docs/01-a.md": "# Part 9: A\n"}, [self.rule()])
        self.assertEqual(f, [])


class Config(unittest.TestCase):
    def test_unknown_type(self):
        with self.assertRaises(doc_lint.ConfigError):
            run_rules({"a.md": "x"}, [{"id": "x", "type": "bogus", "files": ["*.md"]}])

    def test_missing_param(self):
        with self.assertRaises(doc_lint.ConfigError):
            run_rules({"a.md": "x"}, [{"id": "x", "type": "max-words", "files": ["*.md"]}])

    def test_duplicate_ids(self):
        r = {"id": "x", "type": "max-words", "files": ["*.md"], "limit": 5}
        with self.assertRaises(doc_lint.ConfigError):
            run_rules({"a.md": "x"}, [r, dict(r)])

    def test_default_excludes_git(self):
        f = run_rules({".git/x.md": "a" + EM + "b\n"}, [{"id": "d", "type": "forbidden-pattern", "files": ["**/*.md"], "patterns": [EM]}])
        self.assertEqual(f, [])


class Cli(unittest.TestCase):
    def _run(self, files, rules, *extra):
        root = make_tree(files)
        cfg = root / "cfg.json"
        cfg.write_text(json.dumps({"root": ".", "rules": rules}), encoding="utf-8")
        return subprocess.run([sys.executable, str(HERE / "doc_lint.py"), "--config", str(cfg), "--root", str(root), *extra],
                              capture_output=True, text=True, encoding="utf-8")

    RULE = {"id": "dash", "type": "forbidden-pattern", "files": ["*.md"], "patterns": [EM]}

    def test_exit_1_and_format(self):
        p = self._run({"a.md": "x" + EM + "y\n"}, [self.RULE])
        self.assertEqual(p.returncode, 1)
        self.assertIn("a.md:1: [dash]", p.stdout)
        self.assertIn("elapsed", (p.stdout + p.stderr).lower())

    def test_exit_0_clean(self):
        self.assertEqual(self._run({"a.md": "ok\n"}, [self.RULE]).returncode, 0)

    def test_json_output(self):
        p = self._run({"a.md": "x" + EM + "y\n"}, [self.RULE], "--json")
        data = json.loads(p.stdout)
        self.assertEqual(data["findings"][0]["rule"], "dash")
        self.assertEqual(data["counts"]["dash"], 1)
        self.assertEqual(p.returncode, 1)

    def test_config_error_exit_2(self):
        p = self._run({"a.md": "x"}, [{"id": "b", "type": "bogus", "files": ["*.md"]}])
        self.assertEqual(p.returncode, 2)


if __name__ == "__main__":
    unittest.main()
