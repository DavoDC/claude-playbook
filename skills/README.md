# Skills

## What Are Skills?

A skill is a modular, reusable set of instructions stored in a file that teaches Claude how to perform a specific, structured task.

When you type `/survey-repo`, Claude reads the `survey-repo/SKILL.md` file and follows the instructions inside. That's it. No plugins, no API calls, no special setup - just a markdown file that Claude reads and executes.

**Analogy:** Installing an app on your phone to give it a new capability. Before the app exists, the phone can't do the thing. After you install it, it can.

---

## Skills vs Memories - Common Confusion

People often mix these up. Here's the distinction:

| | **Skills** | **Memories** |
|---|---|---|
| **What they are** | Instructions for HOW to do a task | Facts about WHO you are and HOW you work |
| **Example** | "When I type /survey-repo, scan the codebase and produce a structured summary" | "This user prefers Python. No em dashes. TDD always." |
| **Stored as** | `SKILL.md` files in `.claude/skills/` | `feedback_*.md` files + CLAUDE.md |
| **Scope** | Task-oriented, reusable across projects | User-centric, applies to every session |
| **Shared?** | Yes - copy the folder to any workspace | No - personal to your setup |
| **Phone analogy** | Installing an app (new capability) | Notes app where Claude jots down things about you |

**In short:** Skills are what Claude knows how to **do**. Memories are what Claude knows about **you**.

A skill without memory works fine - it just does the task generically. Memory without skills works fine too - Claude knows your preferences but has no shortcuts. The combination is where the system compounds: Claude knows your preferences AND has fast, structured workflows tuned to how you work.

---

## How to Install a Skill

Copy the skill folder to `.claude/skills/<name>/` in your workspace:

```
your-workspace/
  .claude/
    skills/
      aristotle/
        SKILL.md
      think/
        SKILL.md
      survey-repo/
        SKILL.md
```

Claude Code makes it available as `/<name>` in any session run from that workspace. No configuration needed.

---

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

---

## How Skill Files Work

A SKILL.md is a markdown file that Claude reads when you invoke the skill. It defines:
- What the skill does and when to use it (optional frontmatter)
- Step-by-step instructions for Claude to follow
- The output format
- When to use it vs related skills

There is no special syntax. Clear markdown instructions are enough. Claude reads the file and follows them.

---

## Skills Worth Building Yourself

These are described in [docs/08-skills.md](../docs/08-skills.md) and are worth implementing as custom skills for your own setup:

- **`/dev-session`** - the structured session workflow from [docs/04-dev-session.md](../docs/04-dev-session.md)
- **`/end-session`** - session drain, task reconcile, memory commit
- **`/loop`** - repeat a command on a schedule (overnight automation)
- **`/reflection`** - read recent session history, extract patterns, update rules
- **`/health`** - workspace health check (hook counts, file bloat, etc.)

---

## Tips

- Keep skill files focused. One skill does one thing well.
- Add `when_to_use` frontmatter so Claude can suggest the right skill at the right time.
- The best skills encode your exact workflow, not a generic version of it.
- Build skills for things you do repeatedly, not one-off tasks.
- Pair skills with memories: the skill defines the structure, your CLAUDE.md/feedback files shape how Claude behaves inside it.
