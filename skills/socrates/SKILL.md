---
description: Socratic Rule Evaluator - examine every principle against 5 questions, delete zombies, strengthen weak ones, simplify verbose ones
effort: high
argument-hint: "<file, rule-set, or principle to evaluate>"
when_to_use: "Use to interrogate EXISTING rules/principles for justification - before adding a rule to enforced-rules.md, when auditing a rule set, or when a rule feels stale. /aristotle deconstructs forward (designing); /socrates examines backward (keeping). For new-thing design use /think."
---

Five questions per principle:
1. Still true? (conditions, paths, tools current?)
2. Justified from first principles? (real incident / system constraint, not convention)
3. Best practice or just "what we've always done"?
4. Still violated? (check logs, commits, feedback files - never-fires = zombie or success)
5. Zombie? (already covered by higher-tier enforcement - hook/guard/harness?)

Verdict scheme:
| Verdict   | Meaning                      | Action                             |
|-----------|------------------------------|------------------------------------|
| JUSTIFIED | Survives all 5 questions     | Keep as-is                         |
| VERBOSE   | Justified but over-stated    | Simplify to core trigger form      |
| WEAK      | Justified but doesn't fire   | Strengthen - move to hook, sharpen |
| ZOMBIE    | Fails Q1, Q4, or Q5         | Delete                             |
| DEAD-REF  | Rule fine; cross-refs broken | Fix the refs                       |

Output format: table of per-principle verdicts (scanable, not prose), then one-paragraph summary of totals. Every principle must receive a verdict - "nothing should be unexamined."

Anti-pattern: emerging with 0 zombies = you summarised, not questioned.

When NOT to use: designing new things (/aristotle), ranking (/prioritise), rules just written (give it 2 weeks before questioning).

Synergy: wire to a recurring task (quarterly) that passes your enforced-rules.md + CLAUDE.md as arguments. The skill is single source of truth for the method; the recurring task is just the trigger + scope.
