# Book

Load when making a book or reading one of its files by hand. Book is
operator's private git repository; skill holds methods, book holds state.

## Layout

```text
<book>/
  book.json                   marker: book id, created, engine version
  limits.json                 human: asset cap, bounds, thresholds, families
  preferences.json            human: focus sectors, exclusions, cadence
  bin/send                    operator-only sender; adapter stub inside
  universe.csv                copy of start's --universe:file
  data/raw/<source>/          immutable parquet per load; see sources
  data/returns/<run_id>.parquet  each run's gross and net series, immutable
  data/manifest.json          sha256, rows, dates per stored file; written under lock
  data/features/              materialized features (later stage)
  ledger/
    hypotheses.jsonl  critiques.jsonl  decisions.jsonl  fills.jsonl
    runs.jsonl  runs/<agent>.jsonl  incidents.jsonl
    pad/scratch.jsonl         kernel pad, not chained
  proposals/  approvals/  rejected/  sent/
  strategies/<name>/
    signal.py  config.json  README.md  status
  features/  ext/
  tests/reference/            this book's pinned scorecard
  .claude/settings.json       deny rules

${XDG_STATE_HOME:-$HOME/.local/state}/btm-skills/finance/<book-id>/
  held-out.json               salted digests of held-out names
```

`data_snapshot` hashes sorted sha256 of source files under `data/raw/` only;
`data/returns/` files stay in manifest for integrity checks but never move
snapshot, so later run cannot change earlier run's.

`status` holds one word: `research`, `paper`, `live`, or `retired`.
`runs.jsonl` is lead's; each delegate writes own `runs/<agent>.jsonl`; views
read union.

## Ledger lines

Every line: `id`, `ts`, `prev`, then record. `prev` is sha256 hex of
previous line's exact bytes, newline excluded; `null` on line 1. Editing any
line, or removing one, breaks chain at next line; bare `check` names file
and line. Edit to last line shows only when next line lands.

| Kind | Required keys |
| --- | --- |
| hypothesis | `kw`, `strategy`, `family_id`, `capacity_class`, `falsifier`, `counterparty`, `min_holding_days` |
| critique | `kw`, `run_id`, `blockers`, `concerns`, `by` |
| decision | `kw`, `subject`, `action`, `reason` |
| fill | `symbol`, `side`, `quantity`, `price`, `date`, `strategy`, `dry_run` |
| run | `run_id`, `hypothesis_id`, `family_id`, `strategy`, `data_snapshot`, `code_hash`, `config`, `scorecard`; also `params`, `reasons`, `engine`, `tolerance`, `held_out`, `exclusions`, `refused`, `peers`, `span`, `returns`, `agent`, `code_files` |
| incident | `kind`; see Incidents |

Fill from `holdings` carries `holdings: true` and `price` equal to
`cost_basis`, `null` when none given. Fill from `bin/send` carries
`approval`, the approval file's name.

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

Every `check --live` line carries `strategy`, `value`, `limit`, `as_of`.
Same strategy and kind within 7 days of `as_of`: not appended again.

## Ownership

| Path | Writer | Agent may |
| --- | --- | --- |
| `limits.json`, `approvals/`, `strategies/*/status` | human | read |
| `preferences.json` | `record`, after user confirms | read; change through `record` |
| `ledger/` | `record` (fills also through `bin/send`) | append through `record` only |
| `strategies/` except `status`, `features/`, `ext/`, `proposals/` | agent | edit on branch |
| `data/`, `universe.csv` | `load`, `start` | read through data model only; never edit |
| `bin/send` | operator | read; run only `--dry-run`, by operator's hand |
| held-out list | `start` | never read |

## Deny rules

`start` merges these into `.claude/settings.json` under `permissions.deny`,
absolute paths with `//` prefix:

```text
Bash(*bin/send*)
Read(//<state>/btm-skills/finance/<book-id>/**)
Edit(//<book>/ledger/**)
Write(//<book>/ledger/**)
Edit(//<book>/approvals/**)
Write(//<book>/approvals/**)
```

Rules hold absolute paths: if book moves, ask operator to update them.

## What start writes

1. Directories above, `strategies/baseline/` with `status` `research`,
   static multi-factor `signal.py`, `config.json`, `README.md`; baseline
   hypothesis (`capacity_class: crowded`) through gate into
   `hypotheses.jsonl`.
2. `.claude/settings.json` deny rules; existing settings kept.
3. `bin/send` (mode 755) with `RECORD` bound to this skill's realpath.
4. `preferences.json`, `limits.json` defaults, then `book.json`.
5. Held-out list: per sector, quarter of `--universe:file` names, half
   rounded up, whose salted digests sort first; without universe, empty list
   and `signal:` saying so.

## Proposal file

`advise <date>` writes `proposals/<date>.json` once; `--force` writes
`<date>.2.json`, then `.3`; `check <date>` reads newest. Sleeves see
research names only, through `Market` on `as_of`, last bar on or before
`date`, weights set exactly as `score` sets them.

| Field | Holds |
| --- | --- |
| `date`, `as_of`, `cap` | Proposal date, last bar used, `limits.asset_cap` |
| `sleeves` | Per strategy: `account` (`paper` or `live`), `run_id`, `sharpe_net`, `vol_net`, `max_drawdown`, `vol_weight`, `kelly_cap`, `weight`, `code_changed`, `unknown`, raw `signal` per name |
| `skipped` | Paper or live strategy with no run line, with reason |
| `targets` | Per name: `weight` of cap, per-sleeve `sleeves` weights and whole-share `quantity`, reference `price`, `sector` |
| `orders` | `symbol`, `side`, `quantity`, `price`, `adv_participation`, `strategy`, `limit` (null: market-on-open), `account`, `held`, `target`, `carried_from` |
| `summary` | `gross`, `net`, `cash` (1 minus net), `sectors` net weights, `top10` share of gross, `cost` in currency, one-way `turnover`, order count |
| `unmanaged` | Positions in names sleeves do not see; never sold |
| `carried` | Unfilled orders of previous proposal; `merged` when an order here carries it |
| `cuts` | Orders cut to ADV bound: `wanted`, `kept`, participation, bound |

Sizing, annual units, vol is std of run's stored net series times sqrt(252):

1. Sleeve weight is min(`vol_target / vol_net`,
   `kelly_fraction * sharpe_net / vol_net`); zero when Sharpe is null or
   negative.
2. Sum of sleeve weights above 1 scales every sleeve down to sum 1; rest is
   cash.
3. Name's net weight across sleeves above `sizing.max_weight` scales that
   name down in every sleeve alike.
4. Target is whole shares at last close on or before `date`, toward zero.
   Order is target minus held. Order whose quantity times price over 21-day
   dollar ADV passes `max_adv_participation` is cut to bound and listed
   under `cuts`; unknown ADV cuts it to zero.
5. Live sleeves share one real book: real shares no live sleeve filled
   (opening holdings, retired sleeves) first cover sleeves' buys in name
   order; rest lands on last sleeve, whose diff sells it. Paper sleeve holds
   only own dry-run fills.

Order of previous proposal carries when no fill of same symbol, sleeve,
side, and book is dated on or after that proposal, and no `reject` decision
names its stem. Estimated cost: notional times run's trade-weighted
half-spread plus `commission_bps`. `ext/` plug-ins stay deferred.

## Approval file

`check <date>` prints `approval_template` with every order, `date` set to
proposal date. Operator copies it to `approvals/<YYYY-MM-DD>.json`, edits
quantities, sets `date` and file name to send day:

```json
{"date": "YYYY-MM-DD", "proposal": "<proposal stem>", "orders": [{"symbol": "...", "side": "buy|sell", "quantity": 10, "price": 12.5, "adv_participation": 0.004, "strategy": "<name>", "limit": null}]}
```

`bin/send` checks, in order: file resolves under `approvals/`; `date` is
today (UTC); every order's `adv_participation` at most
`limits.max_adv_participation` and strategy `status` `live` (`paper` too in
dry run); then prints order table, asks typed `yes` on terminal, calls
`submit`, records fills, moves file to `sent/`. `--dry-run` skips prompt,
fills at `price` with `dry_run: true`, moves nothing.
