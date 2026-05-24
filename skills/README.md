# Skills

Claude Code custom slash commands. Each skill is a `SKILL.md` file defining what Claude should do when you type `/<name>`.

## How to Install a Skill

Copy the skill folder to `.claude/skills/<name>/` in your workspace:

```
.claude/
  skills/
    aristotle/
      SKILL.md     <- the skill definition
    premortem/
      SKILL.md
    dev-session/
      SKILL.md
```

Claude Code will make it available as `/<name>` in any session run from that workspace.

## What's Here

| Skill | What it does |
|-------|-------------|
| `aristotle/` | First principles deconstruction - strips assumptions, finds axioms, rebuilds from zero |
| `premortem/` | Pre-mortem risk analysis - classifies risks as Tigers/Paper Tigers/Elephants, produces revised plan |

## How Skill Files Work

A SKILL.md is just a markdown file that Claude reads when you invoke the skill. It defines:
- What the skill does and when to use it (frontmatter)
- Step-by-step instructions for Claude to follow
- The output format
- When to use it vs related skills

There is no special syntax. Any markdown file with clear instructions works.

## Skills Worth Building Yourself

These are described in [docs/08-skills.md](../docs/08-skills.md) and are worth implementing as custom skills:

- **`/dev-session`** - the structured session workflow from [docs/04-dev-session.md](../docs/04-dev-session.md)
- **`/end-session`** - session drain, task reconcile, memory commit
- **`/commit-chunks`** - commit staged changes in logical chunks with generated messages
- **`/loop`** - repeat a command on a schedule (overnight automation)
- **`/reflection`** - read recent session history, extract patterns, update rules

## Tips

- Keep skill files focused. One skill does one thing well.
- Add `when_to_use` frontmatter so Claude can suggest the right skill: `when_to_use: "Use when designing a system or when facing a 'should this exist?' question."`
- Skills that run tools (Bash, Read, Write) should be specific about paths and arguments
- Build skills for things you do repeatedly, not one-off tasks
