---
description: Lean numbered list of next best steps based on current session and project state
effort: low
when_to_use: "Use when the user types /whats-next and wants a quick, concrete list of what to do next, not a summary or status report."
---

# /whats-next

Output ONLY a numbered list. No headers, no preamble, no summary before or after.

Each item:
- One concrete next action.
- Prefixed with `[Claude]` (Claude can do this autonomously) or `[You]` (requires the human: a decision, a manual check, or an interactive step). Never omit this prefix.
- Any file or folder path is a clickable absolute-path markdown link, never a bare or relative path.

To decide what's next, use judgment from what is actually live right now: in-progress tasks mentioned earlier in this conversation, the project's task list (for example `docs/IDEAS.md` or a pending-actions file), recent session history, and current git status if relevant. Do not run a fixed generic checklist; draw only from what genuinely applies right now.

As many items as are genuinely useful, but stay lean: favour fewer high-value steps over padding.
