# Ponytail Stats Verb

Display this scoreboard. One-shot: do NOT change level, write files, or
persist anything.

Figures are benchmark medians upstream ponytail project measured and
published: 5 everyday tasks (email validator, debounce, CSV sum, countdown
timer, rate limiter) on three model tiers. Source:
https://github.com/DietrichGebert/ponytail (`benchmarks/` and its README).

## Scoreboard

Render plain ASCII bars. Bar length shows measured range; label carries
exact figure:

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

Benchmark medians only. NEVER print per-repo savings number ("you saved X
lines/tokens here"): unbuilt version was never written, so live repo has no
baseline to subtract from. Only real per-repo figures come from
`/ponytail debt`, a counted ledger; card points there.
