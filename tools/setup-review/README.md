# Setup review: compare your setup with this playbook

A short procedure for reviewing an existing Claude Code setup (rules, memory, skills, hooks, settings, scripts and habits) against this playbook. It shows where your setup matches, where it does something better, and what you could borrow. It also gives you a clearer picture of your own setup. Judge each item on its evidence.

## Before you start

Use the latest version of this playbook, and note its short commit hash so you know which version you compared against.

## Principles

- **Read-only.** Change nothing in the playbook or in your setup while reviewing. The only write is your improvement list in Step 4.
- **Evidence.** Each item names the file, setting or command that shows it, taken from live files rather than memory.
- **Focus on impact.** Cover every area below, but within an area keep to the highest and medium impact items. Skip low-impact and rarely used ones.
- **Applies to any kind of work.** Keep items that would help anyone using Claude. Where an idea is tied to one field or tool, note the general principle behind it.
- **Describe patterns, not specifics.** Use general terms, for example "a ticket system" or "a data store".
- **Tentative.** A difference is not automatically an improvement. Use "appears" and "may" where it is a judgement.

## Step 1: inventory your setup

Walk the whole setup, not a sample. Cover each area, and anything else you find:

1. Rules and enforcement: written guidance, blocking or warning checks, permissions, review steps; how each is enforced or only hoped for, how rules are added, trimmed and retired, and how you learn one was ignored.
2. Key process documents: how sessions run, how work is planned, how mistakes become lessons, how work is checked, when to call something done.
3. Context discipline: what loads into every session, how that stays small, and how new rules are routed to narrower places (a skill, an on-demand document, a project file, a check).
4. Instruction files and how they load.
5. Memory: where it lives, how it is indexed, kept current and pruned.
6. Skills and commands: the 10 to 15 that matter most.
7. Automatic checks (hooks): what they block, warn about or record.
8. Settings and permissions.
9. Subagents and delegation.
10. Scripts and tools you rely on.
11. Logs, audits and status reports.
12. Planning and backlog conventions.
13. Git conventions and safety checks.
14. Testing, verification and "done" habits.
15. Safety, privacy and secrets handling.
16. Session habits: start, hand over, recover, resume.
17. Self-improvement: how mistakes become lasting fixes.
18. Anything else that does not fit above.

## Step 2: read the playbook

Read enough to judge each item from Step 1: `docs/` (start with `docs/checklist.md`), `skills/`, `tools/`, `templates/`, and the top-level README and CLAUDE.md. Read the relevant passage, not just the headings.

## Step 3: mark each item

- **SAME**: essentially identical. Nothing to do.
- **DIFFERENT**: both cover it, but your approach differs. Say why yours may be better, or "unclear which is better". Keep what works; consider whether the playbook's version fixes a weakness of yours.
- **MISSING-HERE**: the playbook has it and your setup does not.

Also note any playbook passage that seems wrong, stale or unclear for your use.

## Step 4: your improvement list

For each MISSING-HERE item, and each DIFFERENT item where the playbook looks stronger, add one short line to your own backlog, worded "Consider adopting <item> from this playbook (<file>)". If you have no backlog, keep a scratch note. Do not adopt anything during the review; pick items off the list afterwards, highest impact first, and prove each in your own setup before relying on it.
