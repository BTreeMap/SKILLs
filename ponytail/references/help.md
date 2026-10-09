# Ponytail Help Verb

Display reference card built from SKILL.md, then stop. One-shot: do NOT
change level, write files, or persist anything.

Render these sections in order:

1. **Levels**: one row per row of Levels table, with its trigger:
   `/ponytail basic`, `/ponytail` (full, the default), `/ponytail maximum`.
   On full row, list ladder's rungs in order. Then state level sticks until
   changed or session end.
2. **Verbs**: one row per row of Verbs table, with trigger
   `/ponytail <verb>`. On examine row, show sample finding:
   `L42: yagni: factory, one product. Inline.` Then state verbs are one-shot
   and leave level untouched, and `write` is default verb: the stance
   itself, with no reference file.
3. **Deactivate**: say "stop ponytail" or "normal mode"; resume anytime with
   `/ponytail`.
4. **More**: levels defined in this skill's SKILL.md; examine, audit, debt,
   measure adapted from upstream ponytail project:
   https://github.com/DietrichGebert/ponytail
