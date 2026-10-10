---
description: Show today's focus. Top 3 active priorities with next step, the rest of the queue, tactical items and health flags. Asks status and removes done items in place.
when_to_use: "Use at the start of a working day or when re-planning mid-day. Template skill: set the three source paths below to your own roadmap files first."
---

# /today - Today's Focus

**Template.** Replace the three sources with your own files. Any layout works if it has (a) an ordered priority table, (b) one file per priority holding its concrete next steps, (c) a short list of tactical cross-project items.

**Sources, in priority order:**
1. `<roadmap>/OVERVIEW.md`: the full priority table (canonical order)
2. The top 3 priority files it points at, read for concrete next steps
3. `<roadmap>/pending-actions.md`: high-priority tactical items
4. `<roadmap>/completed-actions.md`: what is already done today (recap only)

Design goals:
- **Show the whole roadmap, not just three items.** Full context means what is active, what is future or blocked, and what is tactical.
- **Read the priority files for depth.** The table shows order; the files show the next concrete step.
- **No duplication.** Reference by name; never restate content.
- **The skill reviews and prioritises.** It does not generate a copy of the plan.

## Steps

0. **Budget gate.** Run your budget script (for example `bash tools/session-status.sh`). If context is at or above 80 percent, stop with "ctx at X% - run /end-session first before planning the day." Otherwise proceed.

1. **Read in parallel:** the overview table (active priorities plus the future and blocked section), the high-priority part of pending-actions, and the completed-actions file for today's recap.

2. **Identify the top 3 active priorities** from the overview. Read their files in parallel and extract the next-steps section. If a file is marked blocked or paused, skip it and take the next non-blocked one.

3. **Lead with a completed-today recap** if two or more deliverables are already done today: "**Already done today: A, B.**" Skip it before noon with nothing done.

4. **Show the full picture in four blocks:**

   ```
   STRATEGIC FOCUS (top 3, each with its next concrete step):
   1. <priority> - <next step from its file>
   2. <priority> - <next step from its file>
   3. <priority> - <next step from its file>

   QUEUED (active, not today): #4 <name> | #5 <name> | ... (one line, all remaining)

   FUTURE/BLOCKED: <names, inline>

   TACTICAL (cross-project, from pending-actions high priority):
   - <task>
   ```
   Then ask: "Status on each? done / blocked / swap?"

5. **Roadmap health flags** (append after the blocks if any fire):
   - A top-3 file has no next-steps section: "needs next step defined".
   - Tactical high priority is empty: say so.
   - A priority has been in the top 3 for many sessions without a status update: "stale top pick, check it is still a priority".

6. **When the user reports items done:**
   - Strategic item done: note it complete, move its file to an archive folder, remove its row from the overview.
   - Tactical item done: delete it from pending-actions immediately; move it to completed-actions if it is external or loggable work.
   - Priority swap: edit the overview table row order directly.

## Rules

- **Never write a "today" block to any file.** The focus list lives in the conversation; the overview table is the source of truth.
- **Read priority files only for the top 3.** The queue and the future/blocked list show names only.
- **A blocked priority** appears under future/blocked, never in the strategic focus.
- **Always show the full queue** so the pipeline is visible without asking.
- **Mid-session re-runs:** pending-actions may be stale if `/end-session` has not run since the last block of work. Ask what has moved.
- **Do not edit other sections** of pending-actions unless asked.
- **No rule-reminder footnotes** in the shown list.
- **Feedback on the plan improves this skill.** When the user corrects, reorders or pushes back on the output, update this SKILL.md in the same session.
