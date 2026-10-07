# Ponytail Help Verb

Display a reference card built from SKILL.md, then stop. One-shot: do NOT
change level, write files, or persist anything.

Render these sections in order:

1. **Levels**: one row per row of the Levels table, with its trigger:
   `/ponytail lite`, `/ponytail` (full, the default), `/ponytail ultra`. On
   the full row, list the ladder's rungs in order. Then state that the level
   sticks until changed or session end.
2. **Verbs**: one row per row of the Verbs table, with the trigger
   `/ponytail <verb>`. On the review row, show a sample finding:
   `L42: yagni: factory, one product. Inline.` Then state that verbs are
   one-shot and leave the level untouched, and that `build` is the default
   verb: the stance itself, with no reference file.
3. **Deactivate**: say "stop ponytail" or "normal mode"; resume anytime with
   `/ponytail`.
4. **More**: levels are defined in this skill's SKILL.md; review, audit,
   debt, and stats are adapted from the upstream ponytail project:
   https://github.com/DietrichGebert/ponytail
