---
description: Check context level using actual ctx% from statusline data
effort: low
when_to_use: "Use to quickly check how full the context window is before starting a large task, or when the session feels sluggish. Reports a one-line verdict: light / moderate / heavy with recommendation."
---

Run your session status script (e.g. `bash tools/session-status.sh`) to get the current ctx%.

Report based on ctx% value:
- ctx < 40%: "Context light - no compact needed (ctx=X%)"
- ctx 40-69%: "Context moderate (ctx=X%) - compact if starting a large task"
- ctx >= 70%: "Context heavy (ctx=X%) - run /end-session then /compact now"
- No data (script absent or no output): fall back to counting exchanges: if >15, warn; otherwise clear.

One line only. No preamble. No explanation.
