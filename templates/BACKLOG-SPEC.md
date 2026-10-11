# Backlog specification

**One file, governing every backlog.** Copy this into your workspace once. Point every `IDEAS.md` at it rather than restating the rules per repo, so improving the process improves every backlog at once. The reader it is designed for is an agent with no memory, a small context budget and a habit of doing exactly what one item says: each session pulls the next item, does it and closes it. `tools/backlog.py` enforces the format below.

## Principles

1. **One item is one pickable unit.** One goal, one agent run, one commit chunk. An "and" between two goals means two items. A theme is an id prefix and at most one epic line, never a block holding several different things.
2. **Read the summary, not the file.** The top of the file is an index in pick order. Read that (or the tool's `status`), open one item, and never read the rest. The index order is the run order.
3. **Every item is ready or says why not.** `ready` means a checkable acceptance test exists. No test means `idea`. A blocked item names what unblocks it.
4. **Detail falls with priority.** Top-tier items are fully specified; low-tier items may be two lines.
5. **Tier is the only priority word, and the top tier is small.** No "top priority" or "do now" labels: they inflate until nothing is prioritised.
6. **Only open work lives here.** Done items leave for `HISTORY.md` with the commit; durable facts go in reference docs; session state goes in the agent brief or log.
7. **Anything derivable is generated.** The index, the human-only list and the epic lines come from the items' fields, so they cannot drift.
8. **The script is the only editor.** Enforcement by mechanism, not by remembering prose.

## Layout

```
backlogs/<RepoName>/IDEAS.md      # forward-looking, ordered by leverage
backlogs/<RepoName>/HISTORY.md    # shipped record, dated
```

Give the workspace itself a folder here. It is a repo, it accumulates work, and it is the one everybody forgets.

**Keep these private.** A backlog names unreleased work, internal systems and people, which makes it the most context-leaking file you own. If a repo is or may become public or shared, the backlog lives in your workspace and never in the repo, and nothing in the repo points at it.

## Routing: what unblocks it, not what it is about

Picking the wrong list is the most common backlog defect, and the usual test ("is it about this repo?") often gets it wrong. Ask what unblocks the item, not what it is about.

| The item | Goes to | Why |
|---|---|---|
| Code, docs, tests or tooling scoped to ONE repo | that repo's `IDEAS.md` | a work session picks from here |
| Work on the workspace itself: a hook, a skill, a rule, a workspace tool | the workspace's own `IDEAS.md` | The workspace is a repo and deserves the same treatment as any other. Most people never create this one, and it is why workspace improvements live in scattered notes |
| The unattended run's work QUEUE, research, cross-repo sweeps | a separate queue file | A queue answers "what should tonight's run do", which spans every repo and includes work belonging to none. That is a different question from "what should be built in this repo next" |
| Blocked on a named person, with a deadline and a real consequence | `pending-actions.md`, capped and dated | High bar. An unbounded blocked list is a wish list |

People collapse the second and third rows, which is why a queue file grows to hundreds of items: repo-scoped work has nowhere else to go, so it accumulates in the queue and the queue stops functioning as one.

## Format

**Tiers, not phase numbers.** Phase numbering creates pressure to finish in order after the priorities have changed. A tier states the reason. Within a tier, order by leverage, never by date added.

```
# Ideas
## INDEX            table in pick order (generated)
## INBOX            raw captures, verbatim, newest first, not yet shaped
## <HUMAN> ONLY     items only the human owner can do (generated from owner)
## TIER 0 BLOCKING  nothing else matters until fixed; about 10 items at most
## TIER 1 CORE      what the repo exists to do
## TIER 2 QUALITY   makes it better, is not load-bearing
## TIER 3 POLISH    real, but would not be missed
## TIER 4 PARKED    explicit "do not build until told"
```

Index row: `id | title | tier | size | state | owner | blocked-by`. States: `inbox`, `idea`, `ready`, `blocked`, `in-progress`; there is no `done` state, because done items leave. Ids carry an UPPERCASE theme prefix (`MS-4`, never `ms-4`): a stable handle for briefs, `blocked-by` cells and commit messages.

**Item schema.** One `###` heading plus a short fixed body, about 25 lines at most; longer detail moves to a reference doc.

```
### <ID>: <verb-first title, one goal>
- **Tier / Size / State / Owner:** T0 / S / ready / Claude
- **Added:** YYYY-MM-DD
- **Goal:** one sentence, the outcome, not the method.
- **Acceptance:** checkable, ideally a command or an observed value.
- **Verify:** optional command; exit code 0 proves the acceptance (run by `close`).
- **Evidence / origin:** date, session, screenshot path; `Raw:` one verbatim line when exact words matter.
- **Depends on / blocks:** ids or "none".
- **Pointers:** files, docs, related ids. No pasted context.
```

The evidence and pointer lines make an item re-checkable a month later by someone who has forgotten the context. An item that changes what the program does also names the user-visible text it changes and the docs that describe it; `close --old-label "Old text"` greps the repo and warns where the old text still appears.

**Size** decides who can pick it up. **S:** one agent run, under about 30 minutes, one or two files. **M:** one agent run, several files, a written brief. **L:** an epic, never `ready`: split it into S and M items and keep one index line listing the children.

## Lifecycle

1. **Capture** the moment the idea exists: append the raw words to the INBOX, dated and verbatim, after a duplicate search. Never blocked on structure.
2. **Triage** at the next session start, or when the inbox holds three or more: turn each entry into items, merge it into an existing item, or drop it with a `HISTORY.md` note. An entry holding five things becomes five items.
3. **Ready:** goal, acceptance, size S or M. Anything unclear stays `idea` with a "missing:" note; never invent acceptance to look ready.
4. **Pick** the first unblocked, agent-owned `ready` item in the highest tier. Read only that item and give the agent that item, not the file.
5. **Close:** verify the acceptance (the `Verify:` command or stated evidence), move the item to `HISTORY.md` with what was done, the commit and the date, and delete the item and its index row in the same commit as the code.
6. **Split and merge:** two items with one shared acceptance test merge; one item with two tests splits. Superseded items go to `HISTORY.md` with a one-line reason.

**Never tick an item in place.** A ticked item still costs a read every time the file is opened, and the entire value of the active list is that everything in it is still true. Git history is the record of what was there.

## The one question that derives the tier

**"Why is this necessary, and what fails if we skip it?"**

- "broken or loses data without it" -> TIER 0
- "enables other work" -> TIER 1
- "improves something that works" -> TIER 2
- "would be nice" -> TIER 3
- "do not build yet" -> TIER 4
- **"cannot answer" -> the most valuable group.** Either not understood yet or no longer wanted, and both are decisions to take now.

That last group is the point. A list where every item has an answer is well-ordered whether or not it has tier labels; a list with tier labels and no answers is decorated, not prioritised.

## Banned

- Multi-goal headings, and bodies listing lettered sub-items that are separate work.
- Two lists claiming the same theme; use one epic line plus children.
- Completed items, done markers, strikethrough, "in flight" state paragraphs.
- A user's whole message pasted into an item: one `Raw:` line, the full text stays in the INBOX entry or session log.
- Reference material or design rationale inside items.
- Vague acceptance. Anything the agent cannot check alone gets a human owner and says what they must look at.
- A human owner on work the agent can run. A dry run, read-only scan or reversible test is agent-owned; if it is GUI-only, the first item is the CLI path that makes it runnable.
- Hand-editing generated sections or bypassing the script.

## Health rules

`python3 tools/backlog.py check` reports each failure with its line and rule name.

- Tier 0 holds at most about 10 items, all `ready` or `blocked`; an `idea` in TIER 0 is shaped or demoted at the next triage.
- The `idea` share stays under 30 percent; above that the backlog is mostly unshaped work and triage comes before building.
- No item over 25 lines, no `ready` item sized L, every item has tier, size, goal, acceptance and an `Added:` date, and each sits in its own tier's section.
- Index, human-only list and epic lines match what the items generate.
- No completion markers and no INBOX entry older than 7 days.
- Id prefixes are uppercase everywhere an id appears; `check --all` also scans unformatted files for lowercase spellings of prefixes they use in uppercase.

## The tool

`tools/backlog.py` is stdlib-only Python, mandatory arguments so a bad call fails instead of writing junk, and `--json` on the read commands. Commands that name a repo resolve it through `config/backlog.json`; `--file <path>` bypasses that.

| Step | Command | Effect |
|---|---|---|
| Capture | `add <repo> "raw words"` | dated INBOX append after a fuzzy duplicate search; refuses without `--force` |
| Triage | `shape <id> --title --tier --size --goal --acceptance --owner [--verify CMD]` | fills the schema, files the item in its tier, regenerates generated sections; refuses missing fields and size L; `--new` mints an item, `--from-inbox` consumes the raw lines |
| Pull | `next [--owner NAME]` | prints only the first unblocked ready item |
| Brief | `brief <id>` | agent brief from the item with a delegation preamble attached |
| Close | `close <id> --sha --summary [--evidence]` | runs `Verify:` (must exit 0) or needs evidence; writes the `HISTORY.md` entry; removes the item and its index row |
| Order | `move <id> --before <id2>` or `--tier N` | reorders, keeps generated sections in sync |
| Split, merge | `split <id> --into ...`, `merge <id> <id2>` | keeps origin quotes |
| Overview | `status <repo>` | counts by tier and state, tier 0 size, idea share, top ready items |
| Check | `check [--all]` | the health rules above; exit 1 on any failure |
| Start | `init` | creates a fresh strict-format file |

**Config.** Copy `config/backlog.example.json` to `config/backlog.json` (gitignored). `agent_owner` and `human_owner` name the two owners; the human-only section takes the human's name. `locations` lists path templates containing `{repo}`, relative to the repo root and tried in order, for example `backlogs/{repo}/IDEAS.md` then `../{repo}/docs/IDEAS.md`. Set `BACKLOG_CONFIG` to use a config elsewhere. The tests in `tools/backlog_tests/` run with `python3 tools/backlog_tests/run.py` and need no pytest.

**Enforce it by mechanism.** A prose rule relies on the agent following it; a hook that denies raw edits to the backlog files cannot be skipped (recipe: "Block raw edits to the backlog file" in `docs/09-hooks-recipes.md`). Useful companions: a SessionStart hook that injects `status` in place of "read IDEAS.md first", and a check that a commit message saying `closes <id>` fails unless the item is gone from `IDEAS.md` and present in `HISTORY.md`.

## Adopting it on an existing backlog

1. Read this spec first, then brief an agent with it plus the desired pick order.
2. The agent saves a BEFORE heading list, works in small chunks, saves an AFTER list and a mapping of every old heading to its new home (item, `HISTORY.md` entry, reference doc). Nothing may be unaccounted for.
3. Done work moves to `HISTORY.md`; multi-goal blocks split by acceptance test; overlapping themes merge into one epic with children; reference facts move to reference docs; priority adjectives become tier and position; long pasted messages shrink to one `Raw:` line.
4. Unclear items become `idea` with a "missing:" note, never invented acceptance.
5. Judge the file, the health rules and the mapping, not the agent's report; then triage the top tier down to a real blocking set.

## Close every pass by re-ranking

Adding items is easy; re-ranking is rare and is where the value is: a ranking made under no constraint is mostly an artefact of the order things were found in.

Apply ONE extreme lens to the LIST, not the code. Write down what moved. "Nothing moved" is a real result. Do not run more than two per pass.

This is the cheapest step in the process and the only one that improves items you are not touching. One measured instance: asking "what would you fix if you could never touch this repo again" of a 180-item backlog promoted a bottom-tier item to first place, because an item whose failure mode was silent, irreversible loss of a person's own work was correctly polish under "how valuable is this" yet the most important in the repo under "what is unrecoverable". Nothing was learned about the code.

## Two mechanical habits

- **Before editing any file in a repo with a backlog, grep the backlog for that filename.** Needs no insight, and catches the case where the file already has a queued item you would otherwise duplicate or contradict.
- **Cross-check open items against current code before trusting the list.** Fixes ship without items being closed, so any list left alone for weeks accumulates already-done entries, and every one costs a future session real time.

## Sources

- [Make Your Product Backlog DEEP (Roman Pichler)](https://www.romanpichler.com/blog/make-the-product-backlog-deep/)
- [How To Make Your Backlog Agent-Ready (StoriesOnBoard)](https://storiesonboard.com/blog/make-backlog-agent-ready)
- [Backlog.md (MrLesk), markdown-native tasks with acceptance criteria for agents](https://github.com/MrLesk/Backlog.md)
