# Caveman Help Mode

Display this reference card when invoked. One-shot: do NOT change level,
write files, or persist anything. Output in caveman style.

## Levels

| Level | Trigger | What changes |
|-------|---------|--------------|
| **lite** | `/caveman-protocol lite` | Drop filler. Keep sentence structure. |
| **full** | `/caveman-protocol` | Drop articles, filler, pleasantries, hedging. Fragments OK. Default. |
| **ultra** | `/caveman-protocol ultra` | Extreme compression. Bare fragments. One word when one word enough. |
| **wenyan-*** | `/caveman-protocol wenyan-lite\|wenyan-full\|wenyan-ultra` | Classical Chinese tiers. |

Level sticks until changed or session end.

## Modes

One-shot reports; the active level is untouched.

| Mode | Trigger | What it does |
|------|---------|--------------|
| **commit** | `/caveman-protocol commit` | Terse Conventional Commits message. Why over what. |
| **review** | `/caveman-protocol review` | One-line findings: `L42: bug: user null. Add guard.` |
| **compress** | `/caveman-protocol compress <file>` | Rewrite prose file in place; script-guarded, backup kept. |
| **stats** | `/caveman-protocol stats` | Honest savings card. No invented numbers. |
| **help** | `/caveman-protocol help` | This card. |

## Language

Keep user's language. User writes Portuguese, reply Portuguese caveman.
Compress the style, not the language. Technical terms, code, commands, and
exact error strings stay verbatim unless the user asks for translation.

## Deactivate

Say "stop caveman" or "normal mode". Resume anytime with `/caveman-protocol`.

## More

Levels and modes are defined in this skill; adapted from the upstream
caveman project: https://github.com/JuliusBrussee/caveman
