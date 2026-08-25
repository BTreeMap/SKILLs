# Ponytail Help Mode

Display this reference card when invoked. One-shot: do NOT change level,
write files, or persist anything.

## Levels

| Level | Trigger | What changes |
| --- | --- | --- |
| **lite** | `/ponytail lite` | Build what's asked, name the lazier alternative in one line. |
| **full** | `/ponytail` | The ladder enforced: YAGNI → reuse → stdlib → native → one line → minimum. Default. |
| **ultra** | `/ponytail ultra` | YAGNI extremist. Deletion before addition. Challenges requirements before building. |

The level sticks until changed or session end.

## Modes

One-shot reports; the active level is untouched.

| Mode | Trigger | What it does |
| --- | --- | --- |
| **review** | `/ponytail review` | Over-engineering-only diff review: `L42: yagni: factory, one product. Inline.` |
| **audit** | `/ponytail audit` | Whole-repo over-engineering audit: ranked list of what to delete. |
| **debt** | `/ponytail debt` | Harvest `ponytail:` shortcut comments into a tracked ledger. |
| **gain** | `/ponytail gain` | Benchmark-median impact scoreboard: less code, less cost, more speed. |
| **help** | `/ponytail help` | This card. |

## Deactivate

Say "stop ponytail" or "normal mode". Resume anytime with `/ponytail`.

## More

Levels are defined in this skill's SKILL.md; modes adapted from the upstream
ponytail project: https://github.com/DietrichGebert/ponytail
