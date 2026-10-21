# Book

Load when making a book or reading one of its files by hand. Book is
operator's private git repository; skill holds methods, book holds state.

## Layout

```text
<book>/
  book.json                   marker: book id, created, engine version, held-out path
  limits.json                 human: asset cap, bounds, thresholds, families
  preferences.json            human: focus sectors, exclusions, cadence
  bin/send                    operator's checker: approval check, order table, fill recorder
  universe.csv                copy of start's --universe:file
  data/raw/<source>/          immutable parquet per load; see sources
  data/returns/<run_id>.parquet  each run's gross and net series, immutable
  data/manifest.json          sha256, rows, dates per stored file; written under lock
  data/features/              materialized features (later stage)
  ledger/
    hypotheses.jsonl  critiques.jsonl  decisions.jsonl  fills.jsonl
    runs.jsonl  runs/<agent>.jsonl  incidents.jsonl  regimes.jsonl
    scored.jsonl
    pad/scratch.jsonl         kernel pad: free memory, not ledger
  proposals/  approvals/  rejected/  sent/
  strategies/<name>/
    signal.py  config.json  README.md  status  strategy-local helpers
  lib/                        agent's shared modules; signal.py imports lib.<module>
  tools/                      agent's scripts; read book through btm_finance.api
  research/<topic>/           notes, tables, sources per line of inquiry
  tests/                      tests for lib/ and tools/; conftest.py puts book root on sys.path
  tests/reference/            this book's pinned scorecard
  INDEX.md                    one line per lib module, tool, research topic
  features/  ext/
  .gitignore                  data/

<path start --held-out named>, default
${XDG_STATE_HOME:-$HOME/.local/state}/btm-skills/finance/<book-id>/held-out.json
                              {"<sector>": ["SYM", ...]}, sorted
```

`book.json` `held_out` holds absolute held-out path; `measure --held-out`
reads list there. Agent never reads that file.

Run book tests through binding `R` with `pytest <book>/tests` in place of
`btm-finance`. `tools/` script reads book through `btm_finance.api`, never
ledger or parquet files: `open_book(path)`; `ledger(book, kind)` for
newest-wins rows of one kind, superseded lines dropped (`run` joins every
runs file, oldest first); `research(book).at(day)` for `Market` on last bar
on or before `day` over research names, `.dates` for bar dates. None serves
held-out names.

`data_snapshot` hashes sorted sha256 of source files under `data/raw/` only;
`data/returns/` files stay in manifest for integrity checks but never move
snapshot, so later run cannot change earlier run's.

`status` holds one word: `research`, `probe`, `paper`, `live`, or `retired`;
absent or empty reads `research`. Operator writes `probe`, `paper`, or
`live` with `promote` decision naming strategy in same step; `paper_months`
counts from it. `probe` trades live at fixed `sizing.probe_weight` so
out-of-sample fills accrue. `runs.jsonl` is lead's; each delegate writes own
`runs/<agent>.jsonl`; views read union.

## Ledger lines

Every line: `id`, `ts`, then record. Ledger is append-only; correction is
new line carrying `supersedes`. `record` writes each batch in one write
under lock, whole or not at all. File ending in line without newline is cut
by some other hand, as is line that is not JSON object: `record` refuses to
append, names file and line; operator repairs it. Bare `check` derives
`warnings` on every call: each cut line (file, line, `problem: cut line`),
each undecodable line (file, line, first 40 bytes), and each `supersedes`
naming no id of its kind; never stored, never repaired, no incident line.
Filesystem modes enforce nothing: these warnings are the append-only check.

| Kind | Required keys |
| --- | --- |
| hypothesis | `kw`, `strategy`, `family_id`, `capacity_class`, `falsifier`, `falsifier_by`, `counterparty`, `min_holding_days`; optional `odds` (`p_win`, `payoff`, `horizon_days`, `kelly_implied`), `chain`, `expectation_source`, `discounted`, `confidence` (critique flags each one absent in family with `event: true`) |
| critique | `kw`, `run_id`, `blockers`, `concerns`, `by` |
| decision | `kw`, `subject`, `action`, `reason`; optional `odds`; `forgo` names strategy |
| scored | `kw`, `subject` (live hypothesis id), `resolved`, `outcome`, `realized_return`, `brier`, `log_score`, `attribution` (`market`, `factor`, `currency`, `idiosyncratic`, `costs`) |
| regime | `kw`, `as_of`, `confidence`; optional `falsified`, `supersedes`; any other field free JSON |
| fill | `symbol`, `side`, `quantity`, `price`, `date`, `strategy`, `dry_run` |
| run | `run_id`, `hypothesis_id`, `family_id`, `strategy`, `data_snapshot`, `code_hash`, `config`, `scorecard`; also `params`, `reasons`, `engine`, `tolerance`, `held_out`, `exclusions`, `refused`, `peers`, `span`, `returns`, `agent`, `code_files`, `regimes`, `regime_days`, `imports` |
| incident | `kind`; see Incidents |

`confidence` (0 to 1) is optional on hypothesis, critique, decision. `chain`
is chain id from `macro` table or `none`. `start` sets baseline's
`falsifier_by` one year after start date. `record` refuses `kelly_implied`
more than 0.01 from `p_win - (1 - p_win) / payoff`. Hypothesis line carrying
`supersedes` spends one trial of its family in bare `check`'s `trials_used`
only when its `falsifier_by` is later than superseded line's; same or
earlier kill date (odds added, text corrected) spends nothing; scorecard
`trials` (DSR) counts backtests only. Bare `check` derives `overdue` and
`unscored` warnings from hypothesis, decision, and scored lines; `scored`
line naming hypothesis clears both.

Regime line in suggested shape; `record` reads only `kw`, `as_of`,
`confidence`, `falsified`, `supersedes`:

```json
{"id": "<id>", "ts": "<ts>", "kw": ["late", "cycle"], "as_of": "YYYY-MM-DD", "short_cycle": "easing|mid-expansion|late-expansion|tightening|contraction", "long_cycle": "early|bubble|top|depression|deleveraging|normalization", "bubble_count": {"count": 2, "evidence": ["<item 1 evidence>", "<item 4 evidence>"]}, "policy_mix": ["austerity|defaults|transfers|printing"], "other_forces": {"internal_order": "...", "external_order": "...", "nature": "...", "technology": "..."}, "observables": {"<name>": {"value": "<as reported>", "as_of": "YYYY-MM-DD", "source": "<url>"}}, "confidence": 0.6, "falsified": ["<chain id>"], "supersedes": "<regime id>"}
```

Gate refuses `as_of` that is not ISO date, `confidence` outside 0 to 1,
unknown chain id under `falsified`, `supersedes` naming no live regime id.
Vocabularies above are `macro` guidance, never checked; `evidence` count
other than `bubble_count.count` is signal only. Regime record is newest live
line by `as_of`, later line winning tie; `stale` when `as_of` is more than
`limits.regime_stale_days` (default 90) before today, or before proposal
date in proposal file.

Fill from `holdings` has `holdings: true` and `price` equal to `cost_basis`,
`null` when none given. Fill from `bin/send` has `approval`, the approval
file's name.

## Incidents

`incidents.jsonl` lines come from scripts, never from `record`:

| `kind` | Writer | Keys, or breach |
| --- | --- | --- |
| `integrity` | any read of `data/` | `file`, `problem`, `expected`, `found` |
| `drawdown` | `check --live` | realized drawdown over `drawdown_review_multiple` times run's `max_drawdown` |
| `underperform` | `check --live` | consecutive months below baseline sleeve, at `underperform_months` or over |
| `slippage` | `check --live` | mean fill-minus-reference share, signed by side (reference: `price` of order with fill's symbol and side in proposal its approval names), over run's `half_spread_mean` plus commission |
| `tracking` | `check --live` | annualized std of realized minus model daily return over `thresholds.tracking_error` (default 0.05) |
| `stale` | `check --live` | trading days since last bar over 5 |

Every `check --live` line has `strategy`, `value`, `limit`, `as_of`, `by`.
Same strategy and kind within 7 days of `as_of`: not appended again.

## Ownership

| Path | Writer | Agent may |
| --- | --- | --- |
| `limits.json`, `approvals/`, `strategies/*/status` | human | read |
| `preferences.json` | `record`, after user confirms | read; change through `record` |
| `ledger/` | `record`; run lines `measure`; incident lines `load`, `check --live`; `bin/send` fills through `record` | append through `record` only; bare `check` warns on any other write it can see |
| `strategies/` except `status`, `lib/`, `tools/`, `research/`, `tests/` except `reference/`, `INDEX.md`, `features/`, `ext/`, `proposals/` | agent | edit on branch |
| `data/`, `universe.csv` | `load`, `start` | read through data model only; never edit |
| `bin/send` | operator | read; run plain or `--dry-run`; `--fills` is operator's |
| held-out list, path in `book.json` `held_out` | `start` | never read |

## What start writes

1. Directories above, `strategies/baseline/` with `status` `research`,
   static multi-factor `signal.py`, `config.json`, `README.md`; baseline
   hypothesis (`capacity_class: crowded`) through gate into
   `hypotheses.jsonl`. Empty `lib/__init__.py`; `tests/conftest.py`;
   `INDEX.md` holding header and column line
   `path | purpose | last touched`, nothing else. Bare `check` warns when
   `INDEX.md` is absent.
2. `bin/send` (mode 755) with `RECORD` bound to this skill's realpath.
3. `preferences.json`, `limits.json` defaults, then `book.json` with
   `held_out` path.
4. Held-out list at `--held-out` path, default under `XDG_STATE_HOME`; path
   inside book refused before any write. Per sector, first quarter of
   `--universe:file` names by symbol sort, half rounded up; deterministic,
   no randomness. Plain JSON, sector to symbols; receipt reports path and
   count only. Without universe, empty list and `signal:` saying so.
5. `.gitignore` holding `data/` (existing lines kept); `git init -q` unless
   path is inside git work tree. Receipt `git`: `init`, `inside`, `failed`,
   or `absent` (no `git` on PATH, with `signal:` line).

## Proposal file

`recommend <date>` writes `proposals/<date>.json` once; `--force` writes
`<date>.2.json`, then `.3`; `check <date>` reads newest. Sleeves see
research names only, through `Market` on `as_of`, last bar on or before
`date`, weights set exactly as `measure` sets them.

| Field | Holds |
| --- | --- |
| `date`, `as_of`, `cap` | Proposal date, last bar used, `limits.asset_cap` |
| `sleeves` | Per strategy: `account` (`paper` or `live`), `tier` (`backtest`, `paper`, `live`, `probe`), `edge_scale`, `run_id`, `sharpe_net`, `vol_net`, `max_drawdown`, `vol_weight`, `kelly_cap`, `divisor`, `weight`, `code_changed`, `unknown`, raw `signal` per name |
| `skipped` | Probe, paper, or live strategy with no run line, with reason |
| `targets` | Per name: `weight` of cap, per-sleeve `sleeves` weights and whole-share `quantity`, reference `price`, `sector` |
| `orders` | `symbol`, `side`, `quantity`, `price`, `adv_participation`, `strategy`, `limit` (null: market-on-open), `account`, `held`, `target`, `carried_from` |
| `summary` | `gross`, `net`, `cash` (1 minus net), `sectors` net weights, `top10` share of gross, `cost` in currency, one-way `turnover`, order count |
| `unmanaged` | Held positions in names sleeves do not see (outside research set; can include held-out names); never sold |
| `carried` | Unfilled orders of previous proposal; `merged` when an order here carries it |
| `cuts` | `kind: adv`: order cut to ADV bound, `symbol`, `strategy`, `wanted`, `kept` shares, `adv_participation`, `bound`. `kind: ruin`: every sleeve scaled to ruin bound, `loss` before scaling, `bound`, `scale` |
| `regime` | Regime record at proposal date: `id`, `as_of`, `stale`; null when none |
| `effective_streams` | Of sleeves with stored series; see `scorecard`; null when none |
| `ruin` | `loss` (1st-percentile 252-day loss before scaling), `bound`, `scale`, `paths`, `horizon`, `block`, `periods` (common dates), `seed`; null with `reasons.ruin` |
| `advisory` | `risk_share` per sleeve (`weight * vol_net` over book's sum, null without vol), `bound` (`max_strategy_risk_share`), `over` names past it; never a cut |
| `reasons` | Why a null field is null: `ruin` |

Sizing, annual units, vol is std of run's stored net series times sqrt(252).
Fractional Kelly trades growth for security (Kelly 1956; Thorp 2006); ruin
bound caps the security side (MacLean, Thorp, Ziemba 2010).

1. Tier from ledger, through proposal's `as_of`: `backtest` with no fills;
   `paper` when sleeve's dry-run fills span at least
   `thresholds.paper_min_days` (63) calendar days from first fill to `as_of`
   and realized path's tracking error against `measure`'s model path (as
   `check --live` computes it) is at or under `thresholds.tracking_error`;
   `live` same on real fills. Fewer days or tracking breach keeps lower
   tier. Status `probe` gives tier `probe`.
2. `edge_scale = min(1, max(0, (dsr - 0.5) / 0.45))`, 0 when `dsr` null: 0
   at DSR 0.5, 2/3 at 0.8, 1 at 0.95 (Bailey and Lopez de Prado 2014).
3. Sleeve weight is min(`vol_target / vol_net`, `kelly_cap`),
   `kelly_cap = kelly_fraction.<tier> * edge_scale * sharpe_net / vol_net`;
   zero when Sharpe is null or negative. Probe sleeve takes exactly
   `sizing.probe_weight`, no vol or Kelly sizing, no divisor.
4. Correlation divisor: weight over `divisor = 1 + sum_j |rho_ij|`, rho
   Pearson correlation of stored net series with each other sleeve on common
   dates; pair with under 20 common periods or no series adds 0.
5. Sum of sleeve weights above 1 scales every sleeve down to sum 1; rest is
   cash. Then ruin: joint stationary block bootstrap (mean block 21 days) of
   weighted sleeves' stored net series on common dates, 1000 paths of 252
   days, generator seeded from proposal date's ordinal, so proposal
   reproduces. Loss is 1 minus compounded wealth; statistic is loss at 1st
   percentile of wealth. Over `sizing.ruin_bound` (0.35): every sleeve
   scales by `ruin_bound / loss` once, one `cuts` entry `kind: ruin`. Under
   252 common periods, or weighted sleeve with no stored series: `ruin`
   null, reason under `reasons.ruin`, no scaling. Cost O(T S + P H). Risk
   share (`weight * vol_net` over sum) lands under `advisory`; no cut.
6. Name's net weight across sleeves above `sizing.max_weight` scales that
   name down in every sleeve alike.
7. Target is whole shares at last close on or before `date`, toward zero.
   Order is target minus held. Order whose quantity times price over 21-day
   dollar ADV passes `max_adv_participation` is cut to bound and listed
   under `cuts`; unknown ADV cuts it to zero.
8. Probe and live sleeves share one real account: real shares no live sleeve
   filled (opening holdings, retired sleeves) first cover sleeves' buys in
   name order; rest lands on last sleeve, whose diff sells it. Paper sleeve
   holds only own dry-run fills.

Order of previous proposal carries when no fill of same symbol, sleeve,
side, and account (paper or real) is dated on or after that proposal, and no
`reject` decision names its stem. Estimated cost: notional times run's
trade-weighted half-spread plus `commission_bps`. `ext/` plug-ins stay
deferred.

## Approval file

`check <date>` prints `approval_template` with every order, `date` set to
proposal date. Operator copies it to `approvals/<YYYY-MM-DD>.json`, edits
quantities, sets `date` and file name to send day:

```json
{"date": "YYYY-MM-DD", "proposal": "<proposal stem>", "orders": [{"symbol": "...", "side": "buy|sell", "quantity": 10, "price": 12.5, "adv_participation": 0.004, "strategy": "<name>", "limit": null}]}
```

`bin/send` places no order. It checks, in order: file resolves under
`approvals/`; `date` is today (UTC); `proposal` names file under
`proposals/`; every order's `symbol`, `side`, `strategy` match order of that
proposal, `adv_participation` at most `limits.max_adv_participation`,
strategy `status` `live` (`paper` too with `--dry-run`). Then it prints
order table. Plain run stops there. `--dry-run` records fill per order at
`price` with `dry_run: true`, moves nothing. Operator places each order by
hand at broker, pastes fills into table, runs `--fills <table>`: CSV with
header `symbol,side,quantity,price,date` (optional `strategy` column), or
JSON list of objects with same keys. Each fill must name order's `symbol`
and `side` (`strategy` too when two sleeves share both), positive `quantity`
and `price`, `date` not after today; any miss refuses table whole. Fills go
through `record` with `approval` set; file moves to `sent/`.
