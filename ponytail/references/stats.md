# Ponytail Stats Verb

Display this scoreboard. One-shot: do NOT change level, write files, or
persist anything.

The figures are benchmark medians that the upstream ponytail project
measured and published: 5 everyday tasks (email validator, debounce, CSV
sum, countdown timer, rate limiter) on three model tiers. Source:
https://github.com/DietrichGebert/ponytail (`benchmarks/` and its README).

## Scoreboard

Render plain ASCII bars. The bar length shows the measured range; the label
carries the exact figure:

<template for="scoreboard">
  ponytail stats                    benchmark median · 5 tasks · 3 models

  Lines of code   no-skill  ████████████████████  100%
                  ponytail  ██▌·················    6-20%   ▼ 80-94%
  Cost            no-skill  ████████████████████  100%
                  ponytail  █████▌··············   23-53%  ▼ 47-77%
  Speed           ponytail  ▸ 3-6× faster

  This repo:  /ponytail debt   (shortcuts you deferred)
              /ponytail audit  (what's still cuttable)
</template>

## Honesty boundary

Benchmark medians only. NEVER print a per-repo savings number ("you saved X
lines/tokens here"): the unbuilt version was never written, so a live repo
has no baseline to subtract from. The only real per-repo figures come from
`/ponytail debt`, a counted ledger; the card points there.
