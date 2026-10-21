# Scorecard

Load before reading, explaining, or arguing from scorecard or standing.
`measure` writes one per run line under `scorecard`, with `reasons` beside
it naming why any field is null; `check <strategy>` applies thresholds from
`limits.json`. Run line key `peers` lists run ids whose stored series fed
`sr_var` and PBO matrix, in order used; `measure --repeat` rebuilds from
that list.

## Units

* Returns decimal, never percent: 0.01 is 1%. Sharpe annualized with 252
  periods unless field says per period, on excess return: return minus
  `_factors` `rf` (0 where none loaded); cash earns `rf`.
* Probabilities in [0, 1]. Costs proportional decimals; `commission_bps`
  only is basis points.

## Fields

| Field | What, units | `check` rule (`limits.json` key) | Source |
| --- | --- | --- | --- |
| `sharpe_gross` | annualized Sharpe of daily excess return before costs | none; read beside `sharpe_net` | |
| `sharpe_net` | annualized Sharpe after half-spread, commission, impact at 1x | none; compared with baseline strategy | |
| `dsr` | deflated Sharpe, probability true Sharpe beats best of `trials` noise trials | promote at or above 0.95 (`thresholds.dsr`) | Bailey and Lopez de Prado 2014 |
| `trials` | run lines in family including this one, refused and held-out ones too | within `families.<id>.trials` budget | Bailey and Lopez de Prado 2014 |
| `pbo` | probability of backtest overfitting by CSCV, 16 blocks | promote below 0.10 (`pbo_promote`); discard at or above 0.50 (`pbo_discard`) | Bailey, Borwein, Lopez de Prado, Zhu 2017 |
| `walk_forward` | `folds` (`thresholds.folds`, default 5), `embargo` (= `holding_days`), `sharpe` list of net Sharpe per purged test fold, `mean`, `positive` share | none; critique reads it | Lopez de Prado 2018 ch. 7 |
| `regimes` | annualized net Sharpe under `year` by calendar year and under `vol` by tercile `low`, `mid`, `high` | none; critique reads concentration | |
| `perturbation` | net Sharpe per param under `-20%` and `+20%` | none; critique reads cliff edges | |
| `factor` | `alpha_annual` (decimal), `t_alpha` (Newey-West), `loadings` per factor, `model` label, factor names joined by `+` (`ff5+mom`), `r2`, `n` periods | t at or above 3.0 (`t_empirical`); 2.0 with stated `mechanism` (`t_mechanism`) | Harvey, Liu, Zhu 2016; Fama and French 2015; Carhart 1997 |
| `turnover_annual` | one-way turnover per year, half of summed absolute weight change, decimal of capital | none; drives `cost_share` | |
| `cost_share` | share of gross excess PnL lost to costs, [0, 1]; 1 when gross excess PnL is not positive | at most 0.25 (`max_cost_share`) | |
| `adv_participation_max` | largest trade over trailing 21-day dollar ADV at `asset_cap`, decimal | at most 0.02 (`max_adv_participation`) | |
| `min_holding_days_realized` | turnover-implied mean holding, trading days: periods times mean gross exposure over one-way weight traded | at least 5 (`min_holding_days`) | |
| `capacity` | net Sharpe at `0.1x`, `1x`, `20x` `asset_cap`, square-root impact on; `1x` equals `sharpe_net` | see Rules | |
| `spread_model` | `half_spread_mean` (trade-weighted, charged), `abdi_ranaldo_mean` and `corwin_schultz_mean` on traded cells, `gap_mean`, `abdi_ranaldo_share` (cells where it was primary), `fallbacks` count, `primary` rule text | none; logged for quarterly refit | Corwin and Schultz 2012; Abdi and Ranaldo 2017 |
| `max_drawdown` | largest peak-to-trough fall of net wealth, positive decimal | live review at 1.5x (`drawdown_review_multiple`) | |

## Rules

* `measure` refuses before running: no hypothesis names strategy;
  `holding_days` under `min_holding_days`; `config.json` `family_id` other
  than hypothesis's; `signal.py` failing on import. After running,
  `cost_share`, `adv_participation_max`, or `min_holding_days_realized` out
  of bound: run line still written with `refused`, exit 1.
* DSR: promote at or above 0.95. `sr` per period; `sr_var` is variance of
  per-period net Sharpe across family's runs, this one included. One trial:
  SR0 is 0, DSR is probabilistic Sharpe against zero, still held to 0.95.
* PBO: trial matrix is this strategy's 2k + 1 variants (each of k params at
  -20%, 0, +20%, one at a time) plus stored net series of family's other
  research runs, on dates all cover. Null when fewer than 2 trials or fewer
  than 32 common periods; null blocks. Promote below 0.10. At or above 0.50:
  discard. Trailing rows past whole blocks dropped.
* t-stat: residual alpha t on Fama-French five plus momentum (`_factors`
  fields `mkt_rf`, `smb`, `hml`, `rmw`, `cma`, `mom`); at or above 3.0 for
  empirical family, 2.0 only when hypothesis states ex-ante `mechanism`.
  Adds `qmj` or `bab` when `families.<id>.touches` names `quality` or
  `low_risk` and field is loaded. No `_factors`: `factor` null, blocks.
* Capacity: net Sharpe at 1x must be positive and within 20%
  (`capacity_tolerance`) of 0.1x. Net Sharpe at 20x still within 20% of
  0.1x, or hypothesis `capacity_class: crowded`: blocked as `crowded` until
  decision line with `action: override` names strategy. Edge surviving at
  twenty times cap is one institutions can hold, so likely crowded;
  hypothesis registered `in_band` showing it needs `override` with reason.
* Walk-forward: test folds contiguous; training drops `embargo` periods each
  side of test fold; strategies fit nothing, so every fold is out of sample.
* Regimes: vol tercile from 21-day volatility of equal-weight universe
  return, lagged one day.
* Spread: half-spread at decision day from 21-day estimates; Abdi-Ranaldo
  primary below median ADV of universe that day, Corwin-Schultz at or above;
  other estimator, then day's median, fills a gap. Corwin-Schultz reads low
  when daily high and low come from few trades; trust it on liquid names
  only.
* Universe filters per rebalance: preference exclusions (symbols, sectors),
  close under `price_floor`, ADV under `adv_multiple` times largest intended
  position at `asset_cap`. Delisted name returns its terminal return by
  exchange from `limits.delisting` on delisting day, then cash.
* Interior missing bar (NaN close between name's first and last bar) is
  non-session day on its exchange: price carried, return 0, no trade, no
  volatility, spread, or ADV observation; next bar returns whole move since
  last close; rebalance landing there fills at carried close. Universe
  spanning exchanges is supported.

## Regimes and streams

Run line, beside scorecard and outside it (reference pin never covers it):

* `regimes`: ids of regime records whose span overlaps evidence window.
  Record holds from its `as_of` to next live record's `as_of`; last holds
  open-ended. `regime_days`: evidence periods per id, `none` for periods
  before first record. Cost O(R log R + R log T).

`check <strategy>` adds three advisory fields, never blockers:

* `regime_concentration`: share of run's `regime_days` per id, `none`
  included; empty when run predates stamp.
* `correlation`: per paper or live sleeve (strategy itself left out),
  Pearson correlation of run's stored net series with sleeve's newest
  research run series on common dates; null under 20 common periods or zero
  variance.
* `effective_streams`: over paper and live sleeves plus this strategy, each
  with stored series: `N_eff = 1 / mean(R)`, R correlation matrix with 1 on
  diagonal, null pairs left out, mean floored at 1/n so `1 <= N_eff <= n`.
  Copy of sleeve gives 1; n independent streams give n. Under
  `limits.min_effective_streams` (default 2): `signal:` line, strategy adds
  trial, not stream.

## Repeat

`measure <strategy> --repeat <run id>` reruns one line from its own inputs
and writes nothing: no run line, no returns file, no incident.

* Refuses before running, naming each moved input: `signal.py` or book-local
  module it imports whose `ast.dump` sha256, or `config.json` whose
  canonical-JSON sha256, differs from line's `code_files`, or `btm_finance`
  version folded into `code_hash`; source file under `data/raw/` changed or
  vanished since listed in manifest, or loaded after run; listed peer whose
  returns file is unlisted, changed, or gone.
* Reruns with line's `config`, `params`, `held_out`, `exclusions`, and
  exactly its `peers` for `sr_var` and PBO, trial count `trials - 1`;
  `limits.json` is read as it stands now.
* Compares every scorecard leaf: numbers within line's `tolerance`
  (`repeat_tolerance`), absolute when both are at or below 1, relative to
  larger above; null must meet null; text must match. Each diff names field
  path, recorded, recomputed, rule.
* `numpy` or `pyarrow` version moved: advisory only. Exit 0 reproduced, 1
  otherwise. Cost: one `measure` run plus one re-hash of the store.
