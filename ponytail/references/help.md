# Ponytail Help Verb

Display this reference card when invoked. One-shot: do NOT change level,
write files, or persist anything.

## Levels

| Level | Trigger | What changes |
| --- | --- | --- |
| **lite** | `/ponytail lite` | Build what's asked, name the lazier alternative in one line. |
| **full** | `/ponytail` | The ladder enforced: YAGNI → reuse → stdlib → native → one line → minimum. Default. |
| **ultra** | `/ponytail ultra` | YAGNI extremist. Deletion before addition. Challenges requirements before building. |

The level sticks until changed or session end.

## Verbs

One-shot; the active level is untouched. `build` is the default verb: the
stance itself, no reference file.

| Verb | Trigger | What it does |
| --- | --- | --- |
| **design** | `/ponytail design` | YAGNI kill list before code: skip / covered / build, rung per survivor. |
| **refactor** | `/ponytail refactor` | Apply the cuts to existing code, behavior preserved. The verb that edits. |
| **review** | `/ponytail review` | Over-engineering-only diff review: `L42: yagni: factory, one product. Inline.` |
| **audit** | `/ponytail audit` | Whole-repo over-engineering audit: ranked list of what to delete. |
| **test** | `/ponytail test` | The one minimal runnable check that fails if the logic breaks. |
| **teach** | `/ponytail teach` | Explain a ladder decision to a named audience. |
| **debt** | `/ponytail debt` | Harvest `ponytail:` shortcut comments into a tracked ledger. |
| **gain** | `/ponytail gain` | Benchmark-median impact scoreboard: less code, less cost, more speed. |
| **help** | `/ponytail help` | This card. |

## Deactivate

Say "stop ponytail" or "normal mode". Resume anytime with `/ponytail`.

## More

Levels are defined in this skill's SKILL.md; review, audit, debt, and gain
are adapted from the upstream ponytail project:
https://github.com/DietrichGebert/ponytail
