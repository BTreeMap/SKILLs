# Ponytail Gain Mode

Display this scoreboard when invoked. One-shot: do NOT change level, write
files, or persist anything.

The figures are benchmark medians published by the upstream ponytail project
(5 everyday tasks - email validator, debounce, CSV sum, countdown timer,
rate limiter - across three model tiers). They are measured there, not
computed from the current repository. Source:
https://github.com/DietrichGebert/ponytail (`benchmarks/` and its README).

## Scoreboard

Render plain ASCII bars. The bar length shows the measured range; the label
carries the exact figure:

<scoreboard>
  ponytail gain                     benchmark median · 5 tasks · 3 models

  Lines of code   no-skill  ████████████████████  100%
                  ponytail  ██▌·················    6–20%   ▼ 80–94%
  Cost            no-skill  ████████████████████  100%
                  ponytail  █████▌··············   23–53%  ▼ 47–77%
  Speed           ponytail  ▸ 3–6× faster

  This repo:  /ponytail debt   (shortcuts you deferred)
              /ponytail audit  (what's still cuttable)
</scoreboard>

## Honesty Boundary

These are benchmark medians, not this repo. NEVER print a per-repo savings
number ("you saved X lines/tokens here"): the unbuilt version was never
written, so there is no real baseline to subtract from in a live repo. The
only real per-repo figures come from `/ponytail debt` (a counted ledger);
this card points there instead of inventing one.

## Boundaries

One-shot display. Edits nothing, changes no level.
