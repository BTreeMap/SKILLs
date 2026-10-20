# Scorecard

Load only when reading or explaining a scorecard. `score` writes one per run
line under `scorecard`; `check` applies thresholds from `limits.json`.

## Units

* Returns decimal, never percent: 0.01 is 1%. Sharpe annualized with 252
  periods unless field says per period.
* Probabilities in [0, 1]. Costs proportional decimals; `commission_bps`
  only is basis points.
* Engine: `btm_finance.engine`, pure numpy, no I/O. Each function states
  units and complexity in its docstring.

## Fields

| Field | What, units | `check` rule (`limits.json` key) | Source |
| --- | --- | --- | --- |
| `sharpe_gross` | annualized Sharpe of daily excess return before costs | none; read beside `sharpe_net` | |
| `sharpe_net` | annualized Sharpe after half-spread and commission | none; compared with baseline strategy | |
| `dsr` | deflated Sharpe, probability true Sharpe beats best of `trials` noise trials | promote at or above 0.95 (`thresholds.dsr`) | Bailey and Lopez de Prado 2014 |
| `trials` | family trial count feeding `dsr`, integer | within `families.<id>.trials` budget | Bailey and Lopez de Prado 2014 |
| `pbo` | probability of backtest overfitting by CSCV, 16 blocks | promote below 0.10 (`pbo_promote`); discard at or above 0.50 (`pbo_discard`) | Bailey, Borwein, Lopez de Prado, Zhu 2017 |
| `walk_forward` | net Sharpe per purged test fold, annualized | embargo at least `min_holding_days` | Lopez de Prado 2018 ch. 7 |
| `regimes` | annualized Sharpe by year and by vol tercile `low`, `mid`, `high` | none; critique reads concentration | |
| `perturbation` | net Sharpe with each parameter at plus and minus 20% | none; critique reads cliff edges | |
| `factor` | annualized alpha (decimal), Newey-West t, loadings, model label, R^2 | t above 3.0 (`t_empirical`); above 2.0 with stated `mechanism` (`t_mechanism`) | Harvey, Liu, Zhu 2016; Fama and French 2015; Carhart 1997 |
| `turnover_annual` | one-way turnover per year, decimal of capital (1.0 = 100%) | none; drives `cost_share` | |
| `cost_share` | share of gross PnL lost to costs, [0, 1] | at most 0.25 (`max_cost_share`) | |
| `adv_participation_max` | largest trade over daily dollar ADV at `asset_cap`, decimal | at most 0.02 (`max_adv_participation`) | |
| `min_holding_days_realized` | shortest realized holding, trading days | at least 5 (`min_holding_days`) | |
| `capacity` | net Sharpe at 0.1x, 1x, 20x `asset_cap`, square-root impact on | 1x within 20% of 0.1x (`capacity_tolerance`); still within at 20x: crowded (`crowded_multiple`) | |
| `spread_model` | half-spread per name, estimator used, gap between estimators, decimal | none; logged for quarterly refit | Corwin and Schultz 2012; Abdi and Ranaldo 2017 |
| `max_drawdown` | largest peak-to-trough fall of wealth, positive decimal | live review at 1.5x (`drawdown_review_multiple`) | |

## Rules

* DSR: promote at or above 0.95. `sr` per period; `trials` counts every run
  in family, failed ones too. One trial: SR0 is 0, DSR is probabilistic
  Sharpe against zero.
* PBO: promote below 0.10. At or above 0.50: discard run outright. Between:
  no promotion, may stay in research. Trailing rows past whole blocks
  dropped.
* t-stat: residual alpha t on Fama-French five plus momentum above 3.0 for
  empirical family; above 2.0 only when hypothesis states ex-ante
  `mechanism` and counterparty. Add QMJ and BAB when family touches quality
  or low risk.
* Capacity: net Sharpe at 1x within 20% of 0.1x, else under capacity at cap.
  Net Sharpe at 20x still within 20% of 0.1x: capacity above 20x cap, flag
  crowded.
* Walk-forward: test folds contiguous; training drops `embargo` periods each
  side of test fold; embargo at least holding period.
* Spread: Abdi-Ranaldo primary below median ADV, Corwin-Schultz above; both
  logged with gap. Corwin-Schultz reads low when daily high and low come
  from few trades; trust it on liquid names only.
