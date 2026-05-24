# Skills

Claude Code custom slash commands. Each skill is a `SKILL.md` file defining what Claude should do when you type `/<name>`.

## How to Install a Skill

Copy the skill folder to `.claude/skills/<name>/` in your workspace:

```
.claude/
  skills/
    aristotle/
      SKILL.md     <- the skill definition
    think/
      SKILL.md
    survey-repo/
      SKILL.md
```

Claude Code will make it available as `/<name>` in any session run from that workspace.

## What's Here

| Skill | What it does |
|-------|-------------|
| `aristotle/` | First principles deconstruction - strips assumptions, finds axioms, rebuilds from zero |
| `premortem/` | Pre-mortem risk analysis - classifies risks as Tigers/Paper Tigers/Elephants, produces revised plan |
| `think/` | Full build workflow - /aristotle + 5-step engineering algorithm + instantiation check |
| `prioritise/` | Rank any list by leverage - Aristotle's "who benefits, are they a bottleneck?" lens |
| `refine-ideas/` | Clarify IDEAS.md priorities - one question per item ("why necessary?"), groups by answer |
| `survey-repo/` | Quick codebase summary - language, purpose, key files, tests, entry points, open TODOs |
| `deep-dive/` | Deep investigation of a topic, file, or repo - security analysis, code review, architecture |
| `cross-synth/` | Cross-synthesise any N subjects - find similarities, differences, gaps, learning transfers |
| `commit-chunks/` | Commit changed files in logical chunks - one commit per feature/fix/topic |
| `commit-all/` | One-shot commit of everything in git status - no planning, no splitting |
| `step-commits/` | Plan changes as atomic commits upfront, implement one at a time |
| `undo-commits/` | Undo last N commits via git reset --soft, recommit cleanly. Safe - never rebases |
| `checkpoint/` | Named session checkpoints - create/list/verify restore points during long runs |
| `human-voice/` | Audit and rewrite text to remove AI patterns - for emails, READMEs, anything to a person |
| `make-public/` | Safety checklist before making a repo public - secrets, gitignore, README |
| `release/` | Create a tagged GitHub release - version detection, changelog, release notes |
| `skill-suggest/` | Context-aware skill recommendations based on your task description |
| `validate-rules/` | Pre-commit validation - TDD ratio, em-dash check, rule file changes |
| `process-feedback/` | Process a feedback file - product tasks AND Claude learnings (dual pass, both mandatory) |

## How Skill Files Work

A SKILL.md is just a markdown file that Claude reads when you invoke the skill. It defines:
- What the skill does and when to use it (frontmatter)
- Step-by-step instructions for Claude to follow
- The output format
- When to use it vs related skills

There is no special syntax. Any markdown file with clear instructions works.

## Skills Worth Building Yourself

These are described in [docs/08-skills.md](../docs/08-skills.md) and are worth implementing as custom skills for your own setup:

- **`/dev-session`** - the structured session workflow from [docs/04-dev-session.md](../docs/04-dev-session.md)
- **`/end-session`** - session drain, task reconcile, memory commit
- **`/loop`** - repeat a command on a schedule (overnight automation)
- **`/reflection`** - read recent session history, extract patterns, update rules
- **`/health`** - workspace health check (hook counts, file bloat, etc.)

## Tips

- Keep skill files focused. One skill does one thing well.
- Add `when_to_use` frontmatter so Claude can suggest the right skill at the right time.
- Skills that run tools (Bash, Read, Write) should be specific about paths and arguments.
- Build skills for things you do repeatedly, not one-off tasks.
- The best skills encode your exact workflow, not a generic version of it.
