# Scorecard

`measure` writes one per run line under `scorecard`, with `reasons` naming
why any field is null; `check <strategy>` applies thresholds from
`limits.json`. Run line stamps `asset_cap` the run was priced at; `peers`
lists run ids whose stored series fed `sr_var` and PBO, in order used.

## Units

- Returns decimal, never percent. Sharpe annualized over 252 periods on
  excess return: return minus `_factors` `rf` (0 where none loaded); cash
  earns `rf`.
- Probabilities in [0, 1]. Costs proportional decimals; only
  `commission_bps` is basis points: one number, or map by exchange, missing
  exchange reads `other`, else 0 with `signal:`.

## Fields

| Field | What, units | `check` rule (`limits.json` key) |
| --- | --- | --- |
| `sharpe_gross` | Sharpe before costs | none |
| `sharpe_net` | Sharpe after half-spread, commission, impact at 1x cap | sizing input; read beside baseline |
| `dsr` | deflated Sharpe: probability true Sharpe beats best of `trials` noise trials | promote at or above 0.95 (`thresholds.dsr`) |
| `trials` | family's run lines spending a trial, this one included, refused and held-out ones too | within `families.<id>.trials` |
| `pbo` | probability of backtest overfitting, CSCV, 16 blocks | promote below 0.10 (`pbo_promote`); discard at or above 0.50 (`pbo_discard`) |
| `walk_forward` | `folds` (`thresholds.folds`), `embargo` (= `holding_days`), net `sharpe` per purged test fold, `mean`, `positive` share, `post_cutoff` | none; critique `hindsight` reads `post_cutoff` |
| `by_year` | net Sharpe per calendar year, keyed `2019` | none; critique `concentration` reads it |
| `perturbation` | net Sharpe per param at `-20%`, `+20%` | none; critique reads cliffs |
| `factor` | `alpha_annual`, `t_alpha` (Newey-West), `loadings`, `model` (`ff5+mom`), `r2`, `n` | t at or above 3.0 (`t_empirical`); 2.0 when hypothesis has `mechanism` (`t_mechanism`) |
| `turnover_annual` | one-way turnover per year | none |
| `cost_share` | share of gross excess PnL lost to costs; 1 when gross is not positive | at most 0.25 (`max_cost_share`) |
| `capacity` | net Sharpe at `0.1x`, `1x`, `20x` `asset_cap`, square-root impact on | Capacity rule |
| `adv_participation_max` | largest trade over 21-day dollar ADV at cap | none; clipped to `max_adv_participation` |
| `adv_clipped`, `adv_clipped_share` | cells clipped to ADV bound; gross clip removed over gross intended | none; critique `costs-capacity` reads it |
| `min_holding_days_realized` | turnover-implied mean holding, trading days | at least 5 (`min_holding_days`) |
| `max_drawdown` | largest peak-to-trough fall of net wealth, positive | live review at 1.5x (`drawdown_review_multiple`) |
| `half_spread_mean` | half-spread charged, trade-weighted, decimal | none; `check --live` slippage reads it |
| `extra` | one number per `lib/metrics/<name>.py` | never |

## Rules

- `measure` refuses before running, writing nothing: no hypothesis names
  strategy; `config.json` `family_id` other than hypothesis's; policy gate
  without `--reason`; `signal.py` failing on import. After running,
  `cost_share` or `min_holding_days_realized` out of bound: line written
  with `refused`, exit 1.
- Trial: every run line spends one but a re-measure at new cap (newest
  research run's `code_hash` unchanged, `asset_cap` differs), written with
  `trial: false`. `trials`, family `trials_used`, `trials_per_day` skip
  `trial: false`.
- ADV clip: after `max_weight` and thin-name drop, each weight clipped to
  `max_adv_participation * adv_dollar(21) / asset_cap`; unknown ADV clips to
  0; clipped weight stays cash.
- Spread: traded name pays Abdi-Ranaldo half-spread when its 21-day dollar
  ADV is below that day's universe median, Corwin-Schultz at or above. A
  missing estimate takes the other estimator, then that day's median over
  traded names; `lib/costs.py`, when present, replaces all of this.
- DSR: `sr_var` is variance of per-period net Sharpe across family's runs.
  One trial: DSR is probabilistic Sharpe against zero, still held to 0.95.
- PBO: matrix is this strategy's 2k + 1 variants (each of k params at -20%,
  0, +20%) plus stored series of family's other research runs, on common
  dates. Null under 2 trials or 32 common periods; null blocks.
- t: residual alpha on `mkt_rf`, `smb`, `hml`, `rmw`, `cma`, `mom`; adds
  `qmj` or `bab` when `families.<id>.touches` names `quality` or `low_risk`
  and field is loaded. No `_factors`: `factor` null, blocks.
- Capacity: net Sharpe at 1x must be positive and at most
  `capacity_tolerance` (0.20, relative) below 0.1x; null blocks. 20x is
  reported, never gated: within tolerance of 0.1x means sleeve scales.
- Walk-forward: contiguous test folds; training drops `embargo` periods each
  side; strategies fit nothing, so every fold is out of sample.
  `post_cutoff`: net Sharpe of folds starting after `limits.model_cutoff`,
  joined; null with reason when cutoff null or no fold starts after it.
- Universe per rebalance: drop preference exclusions, close under
  `price_floor`, ADV under `adv_multiple` times largest intended position at
  cap. Delisted name takes terminal return from `limits.delisting`, then
  cash. Missing bar inside a name's history is non-session day: price
  carried, no trade.

## Repeat

`measure <strategy> --repeat <run id>` reruns one line from its inputs,
writes nothing.

- Refuses before running, naming each: `code_files` path whose AST digest
  (parsed JSON for `config.json`) moved, or module reached now but not then;
  line without `code_hash`; recorded hook digest moved or vanished; source
  file under `data/raw/` changed, vanished, or loaded after run; peer
  returns file unlisted, changed, or gone.
- Reruns with line's `config`, `params`, `exclusions`, `held_out`,
  `asset_cap`, recorded hooks, exactly its `peers`, trial count
  `trials - 1`; other `limits.json` keys as they stand now.
- Compares every scorecard leaf within `tolerance`: absolute when both at or
  below 1, relative above; null meets null; text matches. Moved `engine`
  version is advisory. Exit 0 reproduced, 1 otherwise.
