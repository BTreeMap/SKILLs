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
    pad/scratch.jsonl         kernel pad: free memory, not ledger
  proposals/  approvals/  rejected/  sent/
  strategies/<name>/
    signal.py  config.json  README.md  status
  features/  ext/
  tests/reference/            this book's pinned scorecard
  .gitignore                  data/

<path start --held-out named>, default
${XDG_STATE_HOME:-$HOME/.local/state}/btm-skills/finance/<book-id>/held-out.json
                              {"<sector>": ["SYM", ...]}, sorted
```

`book.json` `held_out` holds absolute held-out path; `measure --held-out`
reads list there. Agent never reads that file.

`data_snapshot` hashes sorted sha256 of source files under `data/raw/` only;
`data/returns/` files stay in manifest for integrity checks but never move
snapshot, so later run cannot change earlier run's.

`status` holds one word: `research`, `paper`, `live`, or `retired`; absent
or empty reads `research`. Operator writes `paper` or `live` with `promote`
decision naming strategy in same step; `paper_months` counts from it.
`runs.jsonl` is lead's; each delegate writes own `runs/<agent>.jsonl`; views
read union.

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
| hypothesis | `kw`, `strategy`, `family_id`, `capacity_class`, `falsifier`, `counterparty`, `min_holding_days`; optional `chain`, `expectation_source`, `discounted`, `confidence` (critique flags each one absent in family with `event: true`) |
| critique | `kw`, `run_id`, `blockers`, `concerns`, `by` |
| decision | `kw`, `subject`, `action`, `reason` |
| regime | `kw`, `as_of`, `confidence`; optional `falsified`, `supersedes`; any other field free JSON |
| fill | `symbol`, `side`, `quantity`, `price`, `date`, `strategy`, `dry_run` |
| run | `run_id`, `hypothesis_id`, `family_id`, `strategy`, `data_snapshot`, `code_hash`, `config`, `scorecard`; also `params`, `reasons`, `engine`, `tolerance`, `held_out`, `exclusions`, `refused`, `peers`, `span`, `returns`, `agent`, `code_files`, `regimes`, `regime_days`, `imports` |
| incident | `kind`; see Incidents |

`confidence` (0 to 1) is optional on hypothesis, critique, decision. `chain`
is chain id from `macro` table or `none`.

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
| `strategies/` except `status`, `features/`, `ext/`, `proposals/` | agent | edit on branch |
| `data/`, `universe.csv` | `load`, `start` | read through data model only; never edit |
| `bin/send` | operator | read; run plain or `--dry-run`; `--fills` is operator's |
| held-out list, path in `book.json` `held_out` | `start` | never read |

## What start writes

1. Directories above, `strategies/baseline/` with `status` `research`,
   static multi-factor `signal.py`, `config.json`, `README.md`; baseline
   hypothesis (`capacity_class: crowded`) through gate into
   `hypotheses.jsonl`.
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
| `sleeves` | Per strategy: `account` (`paper` or `live`), `run_id`, `sharpe_net`, `vol_net`, `max_drawdown`, `vol_weight`, `kelly_cap`, `divisor`, `weight`, `code_changed`, `unknown`, raw `signal` per name |
| `skipped` | Paper or live strategy with no run line, with reason |
| `targets` | Per name: `weight` of cap, per-sleeve `sleeves` weights and whole-share `quantity`, reference `price`, `sector` |
| `orders` | `symbol`, `side`, `quantity`, `price`, `adv_participation`, `strategy`, `limit` (null: market-on-open), `account`, `held`, `target`, `carried_from` |
| `summary` | `gross`, `net`, `cash` (1 minus net), `sectors` net weights, `top10` share of gross, `cost` in currency, one-way `turnover`, order count |
| `unmanaged` | Held positions in names sleeves do not see (outside research set; can include held-out names); never sold |
| `carried` | Unfilled orders of previous proposal; `merged` when an order here carries it |
| `cuts` | `kind: adv`: order cut to ADV bound, `symbol`, `strategy`, `wanted`, `kept` shares, `adv_participation`, `bound`. `kind: risk_share`: sleeve cut to risk-share cap, `strategy`, `wanted`, `kept` weights, `share` before cap, `bound` |
| `regime` | Regime record at proposal date: `id`, `as_of`, `stale`; null when none |
| `effective_streams` | Of sleeves with stored series; see `scorecard`; null when none |

Sizing, annual units, vol is std of run's stored net series times sqrt(252):

1. Sleeve weight is min(`vol_target / vol_net`,
   `kelly_fraction * sharpe_net / vol_net`); zero when Sharpe is null or
   negative.
2. Correlation divisor: weight over `divisor = 1 + sum_j |rho_ij|`, rho
   Pearson correlation of stored net series with each other sleeve on common
   dates; pair with under 20 common periods or no series adds 0.
3. Risk-share cap: risk is `weight * vol_net`; each sleeve's risk at most
   `max_strategy_risk_share` times sum of capped risks. Water-fill: riskiest
   sleeves share one level `s * U / (1 - k s)`, U uncapped risk, k capped
   count. Cap holds only with at least 1 / `max_strategy_risk_share` sleeves
   carrying risk; fewer, it is skipped. Each capped sleeve listed under
   `cuts` with `kind: risk_share`.
4. Sum of sleeve weights above 1 scales every sleeve down to sum 1, which
   keeps risk shares; rest is cash.
5. Name's net weight across sleeves above `sizing.max_weight` scales that
   name down in every sleeve alike.
6. Target is whole shares at last close on or before `date`, toward zero.
   Order is target minus held. Order whose quantity times price over 21-day
   dollar ADV passes `max_adv_participation` is cut to bound and listed
   under `cuts`; unknown ADV cuts it to zero.
7. Live sleeves share one real account: real shares no live sleeve filled
   (opening holdings, retired sleeves) first cover sleeves' buys in name
   order; rest lands on last sleeve, whose diff sells it. Paper sleeve holds
   only own dry-run fills.

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
