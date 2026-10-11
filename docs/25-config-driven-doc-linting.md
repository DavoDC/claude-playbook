# Part 25: Config-Driven Doc Linting

> **Core.** Part of the maintained quick-start path. The tools and settings snippets it references are asserted by `tools/selftest.sh` on every push.

A rule about how your docs must look is forgotten the moment a session is busy, and a reviewer who reads for meaning does not count dashes, check that an index lists every file or notice a numbering gap. This part shows how to turn those prose rules into checks that run every time, using `tools/doc_lint/`: a small standard-library linter where each rule is a JSON entry, so adding a rule is a config edit, not a code change.

## Why a config and not a script per rule

One script per rule means repeated file walking, code-block exemptions and output formats. A config-driven linter pays that once: the engine owns file selection (globs), code-fence masking, output and exit codes, and a rule only says which files, which check type and which parameters. A rule costs a few lines, every rule reports as `path:line: [rule-id] message`, and a mistyped rule fails loudly as a config error instead of silently checking nothing.

## Running it

```
python3 tools/doc_lint/doc_lint.py --config tools/doc_lint/doc_lint.config.json [--root PATH] [--json]
```

Exit 0 means clean, 1 means findings, 2 means the config itself is wrong (unknown type, missing parameter, duplicate id, bad regex). The root defaults to the config's `root`, resolved against the config file. `--json` prints findings and per-rule counts for other tools to read. `tools/selftest.sh` runs the linter's unit tests and then lints this repo with the shipped config, so a doc that breaks one of its own rules fails CI.

## Config shape

A config is `{"root": "..", "rules": [ ... ]}`. Each rule carries `id` (unique), `type`, `files` (globs relative to the root, with `*` and `**`) and the parameters its type needs. Optional keys on every rule: `exclude` (globs), `message` (replaces the default text), `severity` (`error`, the default, fails the run; `warn` is printed but leaves the exit code at 0, which suits a soft size limit) and `enabled: false` to park a rule without deleting it. The folders `.git`, `__pycache__`, `node_modules` and `.venv` are never scanned. Paths for list files (`terms_file`, `allow_file`) resolve against the config file, not the working directory.

## The check types

| Type | What it flags | Parameters |
|------|---------------|------------|
| `forbidden-pattern` | any line matching a regex | `patterns`, `ignore_case`, `skip_code` |
| `required-pattern` | a file where the regex is absent | `pattern`, `within_lines` (window from the top) |
| `max-line-shape` | a paragraph hard-wrapped over several lines; lists, tables, quotes, headings, code and front matter are exempt | none |
| `index-sync` | a file not linked from the index, or an index link into that area that does not resolve | `index`, `mode` (`link` or `mention`), `name_from` |
| `link-resolve` | a relative link or `#anchor` that does not resolve | `check_anchors` |
| `name-reference` | a referenced name (a `/command`, say) with no file or folder behind it and not on the allow list | `pattern`, `exists_in`, `allow`, `allow_file`, `scope` |
| `heading-uniqueness-across-files` | the same heading in two files, a prompt to check for duplicated content | `min_level`, `max_level`, `ignore` |
| `max-words` | a file over a word limit, code excluded | `limit`, `skip_code` |
| `min-words` | a file under a word minimum, code excluded | `limit`, `skip_code` |
| `sequential-numbering` | filenames whose numbers have gaps, repeats or a wrong start, and a first heading whose "Part N" disagrees with the filename | `number_pattern`, `unnumbered_last`, `heading_part` |
| `forbidden-terms-file` | any term from a list file, with the term masked in the output | `terms_file`, `reveal_terms` |

`index-sync` has two modes. `link` mode wants every matching file linked from the index and every index link into that area to resolve, which fits a README guide table. `mention` mode wants only the file's name to appear in the index text, which fits a skills list that mentions each skill by name.

## Which rules to write first

Start from the rules you already state in prose and ask of each one: can a check see a violation? The shipped `doc_lint.config.json` is a worked answer for this repo and the template to copy. Its rules fall into five groups.

- **Style and hygiene:** no em or en dashes, one paragraph per line, no dead official-docs URL form.
- **Privacy and personal data:** no personal outcome figures, no usage counts or personal rankings, no maintenance narration ("changed on DATE"). These are regex heuristics: they catch the numeric and dated shapes and miss the rest, so a clean run proves the shapes are absent, not that the prose is free of them.
- **Shape of a doc:** a tier marker under the title, one H1 that opens the file, no vague titles such as "Misc", a word ceiling that signals a doc holding more than one topic.
- **Structure across docs:** every doc indexed exactly once, links and anchors that resolve, command names that exist as skills, doc numbers sequential with no gaps, no heading repeated across docs.
- **Private terms:** a `forbidden-terms-file` rule reading a list that stays outside the repo. The shipped rule is disabled and points at the untracked per-machine list the privacy hooks already use (see [Part 12](12-privacy-hooks-public-repo.md)); enable it on a machine that has the list. Never put the terms in the config, which is tracked.

## Adding a rule

Append an object to `rules` with a built-in type, for example a banned phrase:

```
{"id": "no-todo", "type": "forbidden-pattern", "files": ["docs/*.md"], "patterns": ["TODO"]}
```

Run the linter. A new check type is justified only when no built-in type can express the rule: add one function with the `@check(...)` decorator in `doc_lint.py`, write its test first in `tools/doc_lint/test_doc_lint.py`, and add its row to the table above.

Two habits keep the rule set honest. First, give every rule a positive control: a test (or a scratch file) that violates it and proves it fires, because a pattern with a typo checks nothing and looks identical to a clean repo (see [Part 19](19-verification-habits.md)). Second, when a new rule is added, run it over the whole tree before committing: it will find existing violations, and the choice is to fix them in the same change or to narrow the rule's `files`, never to leave the suite red.

## Repo health is three rules, not a second tool

A repo-health check (broken links, numbering gaps, an index that has drifted from the files) needs no separate script, because three types already express it. They are the structural rules: a failure in any of them means the repo's shape is wrong, not its prose.

```
{"id": "links", "type": "link-resolve", "files": ["README.md", "docs/**/*.md"]},
{"id": "numbering", "type": "sequential-numbering", "files": ["docs/*.md"],
 "number_pattern": "^(\\d+)-", "unnumbered_last": ["checklist.md"], "heading_part": true},
{"id": "docs-index", "type": "index-sync", "index": "README.md", "files": ["docs/*.md"]}
```

Each catches a defect that review misses because nothing in the changed file looks wrong. A rename leaves links to the old name dangling in files it never touched (`link-resolve` finds them; with `check_anchors` also a link whose heading was reworded). A deleted or inserted doc leaves a gap or repeat in the numbers (`sequential-numbering`; with `heading_part` also a "Part N" title that no longer matches its file). A doc nobody added to the README table is invisible to a reader (`index-sync`, which in the other direction finds an index row whose target moved).

Two cautions. Decide which side of an index is the source of truth: files that must all be indexed, or an index whose entries must all exist; `mention` mode suits a looser second index. And a renumbering fires all three at once: do it as one change with `git mv`, fix links and the index row in the same commit, and run the linter before staging.

## Files and commit messages outside the config

The config walks files in the repo. Two shape rules apply just as well to text it never sees, so `tools/prose-lint.py` carries them standalone: no hard-wrapped paragraph, and no em or en dash. Pointed at files it checks those two; pointed at a commit message with `--commit-msg` it adds a third, that the subject fits `--subject-max` characters (default 72) and line 2 is blank.

A subject over the limit gets cut or spills into the description in most git front ends, and a body wrapped at 72 columns reads as ragged fragments in a box that already wraps. Write each paragraph as one line and use bullets for lists. Comment lines, trailers such as `Co-Authored-By:`, fenced code, tables, headings and quotes are exempt.

To check every message at commit time, call it from a `commit-msg` hook. Git passes the message file as the first argument:

```
#!/bin/sh
python3 "$(dirname "$0")/../../tools/prose-lint.py" --commit-msg "$1" || exit 1
```

If the repo already has a `commit-msg` hook (the privacy one from [Part 12](12-privacy-hooks-public-repo.md) is one), add the line to it instead of replacing the file. Run `python3 tools/prose-lint.py --selftest` to see the positive controls; it is asserted by `tools/selftest.sh`. The detector is deliberately blunt: two adjacent prose lines under 100 characters is a wrap. It will not catch a wrap at 110 columns, and it does not parse markdown, so treat a clean run as the absence of the common shape.

## What stays prose

Some rules need judgement: whether a sentence is about a mechanism or a person, whether two docs argue the same idea in different words, whether the voice matches, whether a section sits in the doc a reader would open first. The heading-duplication rule and the repeated-sentence assertion in `tools/selftest.sh` catch only the cheap cases of duplication. When you add a prose rule to your own maintenance guide, write beside it either the lint rule id that enforces it or the reason it cannot be a rule; a rule with neither will be forgotten.

## Retargeting

To lint another repo: copy `doc_lint.config.json`, change `root`, adjust the `files` globs to the folders that repo has, delete the rules that do not apply, and point `terms_file` at that machine's private list. The linter needs only Python 3 and has no dependencies. Run it from a pre-commit hook or a CI step with the same command; the exit code is the contract.

For size and scratch-file rules that need a different shape of check (a byte budget, an expiry date), see [Part 1](01-claude-md.md) and [Part 13](13-workspace-repo.md).
