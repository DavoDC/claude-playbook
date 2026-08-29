# [Project Name]

<!-- One line: what does this project do? -->
[e.g. Python CLI that auto-manages OBS streaming when launching a known game.]

---

## Why It Exists

<!-- The real motivation, not just the mechanism. This shapes every design decision. -->
<!-- Example: "The time saving is secondary. The real value is psychological reassurance: -->
<!-- the user glances at a second monitor and confirms everything is handled at a glance." -->

[Explain the problem this solves and why this approach. One paragraph.]

---

## Repo Structure

```
src/
  main.py        - entry point
  [key files]    - what they do
tests/
docs/
  IDEAS.md       - pending work, ordered by priority
  HISTORY.md     - archive of shipped features
config/
  config.example.json   - template (tracked)
  config.json           - local config (gitignored)
```

---

## How to Run

**Users:** [describe the user-facing entry point, e.g. scripts/run.bat - double-click launcher]

**Claude (during development):** [raw command, e.g. `python src/main.py` from repo root]

<!-- These are different. Users get the friendly launcher; Claude needs the raw command. -->

---

## Config Format

```json
{
  "key": "value",
  "nested": {
    "example": "..."
  }
}
```

Config template: `config/config.example.json` (tracked in git)
Local config: `config/config.json` (gitignored - never commit this)

---

## Key Business Logic

<!-- Rules that aren't derivable from reading the code. This is where most of the value is. -->
<!-- Example: "The 5 most recent clips in Highlights/ root are protected - processing them -->
<!-- breaks the game's UI tracking. Subfolders are safe." -->

- [Non-obvious invariant 1]
- [Non-obvious invariant 2]

---

## Data Safety

<!-- For projects touching real files or irreversible operations -->

**[HIGH/CRITICAL if applicable]**
[e.g. "The library is the primary copy and is NOT frequently backed up. Before ANY file operation: verify it is safe and reversible. Prefer dry-run first. When in doubt, do nothing and ask."]

---

## Explicit Prohibitions

<!-- Named constraints are more reliable than implicit ones -->

- [e.g. "Only the user executes integration. Claude prepares workflows and stops before running any integration. No exceptions, even dry-run."]
- [e.g. "The importer MUST ONLY operate on staging/. Never on the main library."]

---

## Platform Gotchas

<!-- Anything that looks like it should work but doesn't -->

<!-- Example: -->
<!-- CRITICAL: Legacy csproj - manual file registration required. -->
<!-- New .cs files are NOT auto-included. Every new file must be added to .csproj manually. -->
<!-- If you forget: build fails with CS0103. -->

[List platform-specific gotchas here]

---

## Ideas and History

See `docs/IDEAS.md` for all pending work, ordered by priority.

When a feature ships: remove from IDEAS.md, add a dated entry to `docs/HISTORY.md`. Never mark done with checkmarks - remove the entry completely.
