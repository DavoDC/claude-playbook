# Part 19: Reframing a Blocked Problem

> **Field note.** Written from practice rather than machine-checked, and not covered by `tools/selftest.sh`. Last reviewed 2026-08-02 against Claude Code v2.1.220. Opinionated, and it may lag the harness.

Two examples where restating the problem beat pushing harder on it.

## Using /aristotle to Find the Real Problem

During development of a build script, `/aristotle` was run on: "why does the build script hardcode VS paths?"

The deconstruction: the assumption was that Visual Studio installs to a predictable location; the irreducible truth was that MSBuild must be found at runtime, not compile time. The Aristotelian Move: replace the hardcoded path with `vswhere` (Microsoft's tool for locating VS installations). The script went from fragile to portable in one change, and the pattern was applied across multiple repos.

Typical outcome: the stated problem ("hardcoded path") dissolves into a better-framed one ("runtime discovery"), whose solution is simpler than any fix for the original.

## Working Around an API Registration Wall

Some platforms gate API access behind a registration process an individual can no longer complete (a corporate approval step, a closed waitlist, a category closed to new registrants). Probing for a way around the wall as an individual often burns rounds without changing the outcome.

The reframe: an established free, open-source client for the same platform almost certainly holds its own long-standing registration, obtained before the wall or through a category open to vendors. Switching to that client reaches the same data through ordinary sign-in. In one case a personal-account API path was closed by a registration requirement individuals could no longer obtain; an established open-source client reached the same data with none of the blocked path involved.

The legitimate boundary: use the vendor's software as intended, and never extract or borrow its client credentials to call the API from your own code. The first walks through an open door; the second copies someone else's key.
