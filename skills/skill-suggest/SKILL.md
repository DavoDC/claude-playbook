---
description: Context-aware skill suggestions - get relevant skills based on your task
---

# /skill-suggest - Smart Skill Recommendations

Get intelligent skill recommendations based on your current task or question.

## Usage

Describe your task and get the most relevant skills suggested:

```bash
/skill-suggest <task description>
```

### Examples

**Bug fix:** `I found a bug in the login flow and need to fix it`
-> Suggests: `/deep-dive` (root cause), `/dev-session` (implementation)

**New feature:** `I'm building a new feature and writing tests first`
-> Suggests: `/dev-session` (TDD), `/commit-chunks` (organize commits)

**Understanding code:** `I'm starting on this new project and need an overview`
-> Suggests: `/survey-repo` (quick overview), `/deep-dive` (thorough analysis)

**Session end:** `I'm finishing up and want to wrap everything up`
-> Suggests: `/end-session`, `/reflection`, `/commit-chunks`

## Options

- `--top N` - Show top N suggestions (default: 5)
- `--detailed` - Include full description and "best for" guidance

## How it works

The skill suggester analyzes your task description and:
1. Detects the **intent** (exploration, debugging, implementation, testing, etc.)
2. Matches **keywords** against available skills
3. Ranks skills by relevance and shows the top matches
4. Optionally provides detailed guidance on each skill

## The Skill Map

Skills are categorized by intent:

| Intent | Primary Skills | Use When |
|--------|---|---|
| **Exploration** | `/survey-repo`, `/deep-dive` | Understanding code, learning, starting new work |
| **Implementation** | `/dev-session`, `/commit-chunks` | Building features, writing code, TDD |
| **Debugging** | `/deep-dive` | Finding bugs, fixing issues, security checks |
| **Review** | `/self-audit`, `/validate-rules` | Code review, auditing, validation |
| **Documentation** | `/reflection` | Extracting learnings, improving workspace |
| **Workspace** | `/end-session`, `/health` | Session cleanup, workspace maintenance |

## When to ignore suggestions

The suggester uses keyword matching, which can produce false positives:
- It suggests `/deep-dive` for any "bug" mention, even if it's already diagnosed
- It suggests `/dev-session` for "test" mentions, even in documentation contexts

Use your judgment: **read the "best for" description** to confirm a skill is right for your situation.

## Pro tips

- Use `--detailed` when trying new skills or unfamiliar with options
- If nothing suggested matches, try `/survey-repo` or `/deep-dive` as safe defaults
- The skill suggester itself is a way to explore what skills exist
