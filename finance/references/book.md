# Book

## Layout

```text
<book>/
  book.json                   marker: book id, created, package version at start, held-out path
  AGENTS.md                   agents' standing instructions
  CLAUDE.md                   relative symlink to AGENTS.md; fallback line "Read AGENTS.md."
  limits.json                 asset cap, bounds, thresholds, families
  preferences.json            focus sectors, exclusions, cadence; edited on operator's word
  universe.csv                copy of start's --universe:file
  data/raw/<source>/          immutable parquet per load; see sources
  data/returns/<run_id>.parquet  each run's gross and net series, immutable
  data/manifest.json          sha256, rows, dates per stored file; .gitignore holds data/, so digests guard it
  data/features/              materialized features
  ledger/
    hypotheses.jsonl  critiques.jsonl  decisions.jsonl  fills.jsonl
    runs.jsonl  runs/<agent>.jsonl  incidents.jsonl
    pad/scratch.jsonl         agent's free memory, not ledger; agent appends and greps it
  proposals/
  strategies/<name>/
    signal.py  config.json  README.md  status  strategy-local helpers
  lib/                        agent's shared modules; signal.py imports lib.<module>
  tools/                      agent's scripts; read book through btm_finance.api
  research/<topic>/           notes, tables, sources per line of inquiry
  research/backlog/<id>.md    candidate hypothesis, ranked weekly; shape below
  research/critiques/  research/runs/  research/literature/  research/universe/
                              delegate outputs, one folder per unit
  tests/                      tests for lib/ and tools/; conftest.py puts book root on sys.path
  INDEX.md                    path | purpose header
  .gitignore                  /data, __pycache__/

<path start --held-out named>, default
${XDG_STATE_HOME:-$HOME/.local/state}/btm-skills/finance/<book-id>/held-out.json
                              {"<sector>": ["SYM", ...]}, sorted
```

- `research/<topic>/README.md`: status and open questions of that line of
  inquiry.
- `research/backlog/<id>.md`: one candidate hypothesis, not yet registered.
  State mechanism, counterparty, falsifier, odds, expected information gain,
  and which existing run (run id) it would differ from, and how. Rejected
  candidate stays, status line naming reason: critique item `multiplicity`
  reads it. Rank weekly; only top gets registered. No gate reads this shape.
- `data_snapshot` hashes sorted sha256 of source files under `data/raw/`
  only; `data/returns/` files never move it.
- `status` holds one word: `research`, `live`, or `retired`; absent or empty
  reads `research`; older `paper` or `probe` reads `live`.
- `runs.jsonl` is lead's; each delegate writes own `runs/<agent>.jsonl`;
  views read union.

## Agent-written code

- Write script when step would otherwise repeat by hand or needs more than
  few lines. Put it in `tools/` if it runs, `lib/` if it is imported.
- `lib/`: one module per concern; docstring at top states purpose, inputs,
  outputs.
- `tools/`: `<verb>-<object>.py`, docstring header stating what it reads and
  writes, `argparse` for arguments. Run with `PYTHONPATH` set to book root,
  so `import lib.<module>` resolves.
- Read ledger and data only through `btm_finance.api`. Append to ledger only
  through `record`: script writes batch file, lead runs `record`.
- Accessor `Market` lacks: add it in `lib/market_ext.py`, wrapping `api`.
- Test `lib/` and `tools/` under `tests/`, run with `$U pytest "$B/tests"`.

`btm_finance.api`: `open_book(path)`; `ledger(book, kind)` for newest-wins
rows of one kind, superseded lines dropped (`run` joins every runs file,
oldest first); `research(book).at(day)` for `Market` on last bar on or
before `day` over research names, `.dates` for bar dates. None serves
held-out names.

## Ledger lines

Every line: `id`, `ts`, then record. `record` writes each batch in one write
under lock, whole or not at all. File ending in line without newline is cut
by some other hand, as is line that is not JSON object: `record` refuses to
append, names file and line; repaired only on operator's word. Bare `check`
derives `warnings` on every call: each cut line (file, line,
`problem: cut line`), each undecodable line (file, line, first 40 bytes),
and each `supersedes` naming no id of its kind; never stored, never
repaired, no incident line.

| Kind | Required keys |
| --- | --- |
| hypothesis | `kw`, `strategy`, `family_id`, `falsifier`, `falsifier_by`, `counterparty`, `min_holding_days`; optional `odds` (`p_win`, `payoff`, `horizon_days`, `kelly_implied`), `confidence` |
| critique | `kw`, `run_id`, `blockers`, `concerns`, `by` |
| decision | `kw`, `subject`, `action`, `reason`; optional `odds` |
| fill | `symbol`, `side`, `quantity`, `price`, `date`, `strategy`; `proposal` stem, null for `opening` |
| run | `run_id`, `hypothesis_id`, `family_id`, `strategy`, `data_snapshot`, `code_hash`, `code_files` (path to own digest), `config`, `scorecard`; also `params`, `reasons`, `engine` (package version), `tolerance`, `held_out`, `exclusions`, `refused`, `peers`, `span`, `returns`, `agent`, `imports` |
| incident | `kind`; see Incidents |

`start` sets baseline's `falsifier_by` one year after start date. An older
book's `scored.jsonl` lines read as `close` decisions; `regimes.jsonl` is
ignored with one signal.

Fill from `record --fills:file` has `proposal`, the `--proposal` stem; older
fill's `approval` stem reads as `proposal`.

## Incidents

`incidents.jsonl` lines come from scripts, never from `record`:

| `kind` | Writer | Keys, or breach |
| --- | --- | --- |
| `integrity` | any read of `data/` | `file`, `problem`, `expected`, `found` |
| `drawdown` | `check --live` | realized drawdown over `drawdown_review_multiple` times run's `max_drawdown` |
| `slippage` | `check --live` | mean fill-minus-reference share, signed by side (reference: `price` of order with fill's symbol and side in proposal it names), over run's `half_spread_mean` plus largest `commission_bps` |
| `tracking` | `check --live` | annualized std of realized minus model daily return over `thresholds.tracking_error` (default 0.05) |
| `stale` | `check --live` | trading days since last bar over 5 |

Every `check --live` line has `strategy`, `value`, `limit`, `as_of`, `by`.
Same strategy and kind within 7 days of `as_of`: not appended again.

## Ownership

| Path | Writer | Agent may |
| --- | --- | --- |
| `limits.json`, `preferences.json`, `strategies/*/status` | agent, only on operator's instruction in chat, same turn | change, then record `decision` (spine Invariants) |
| `ledger/` except `pad/` | `record`; run lines `measure`; incident lines `load`, `check --live` | append through `record` only; bare `check` warns on any other write it can see |
| `ledger/pad/scratch.jsonl` | agent | append lines, grep; never gated |
| `strategies/` except `status`, `lib/`, `tools/`, `research/`, `tests/`, `INDEX.md`, `proposals/` | agent | edit |
| `AGENTS.md`, `CLAUDE.md` | `start` | keep `AGENTS.md` `## Invariants` verbatim from template; keep `CLAUDE.md` link or fallback line |
| `data/`, `universe.csv` | `load`, `start` | read through data model only; never edit |
| held-out list, path in `book.json` `held_out` | `start` | never read |

## What start writes

1. Directories above, `strategies/baseline/` with `status` `research`,
   static multi-factor `signal.py`, `config.json`, `README.md`; baseline
   hypothesis through gate. Empty `lib/__init__.py`; `tests/conftest.py`;
   empty ledger files; `INDEX.md` with column line `path | purpose`.
2. `preferences.json`, `limits.json` defaults, `AGENTS.md` from template,
   `CLAUDE.md`, then `book.json` with `held_out` path.
3. Held-out list: per sector, first quarter of `--universe:file` names by
   symbol sort, half rounded up; deterministic. Receipt reports path and
   count only. Without universe, empty list and `signal:` saying so.
4. `.gitignore` holding `/data`, `__pycache__/` (existing lines kept);
   `git init -b main` unless path is inside git work tree. Commits nothing.

## Proposal file

`check --propose <date>` writes `proposals/<date>.json` once; `--force`
writes `<date>.2.json`, then `.3`; `check <date>` reads newest. Sleeves see
research names only, through `Market` on `as_of`, last bar on or before
`date`, weights set exactly as `measure` sets them, ADV clip included
(`scorecard`).

| Field | Holds |
| --- | --- |
| `date`, `as_of`, `cap` | Proposal date, last bar used, `limits.asset_cap` |
| `sleeves` | Per strategy: `tier` (`backtest`, `tracked`), `edge_scale`, `run_id`, `sharpe_net`, `vol_net`, `max_drawdown`, `kelly_cap`, `weight`, `code_changed`, `unknown`, raw `signal` per name, `adv_participation` (largest target over ADV at cap) |
| `sizing`, `extensions` | `default` or `lib/sizing.py`; proposal hooks present, `<hook>/<name>` to digest |
| `skipped` | Live strategy with no run line, with reason |
| `targets` | Per name: `weight` of cap, per-sleeve `sleeves` weights and whole-share `quantity`, reference `price`, `sector` |
| `orders` | `symbol`, `side`, `quantity`, `price`, `adv_participation`, `strategy`, `limit` (null: market-on-open), `held`, `target`, `carried_from` |
| `summary` | `gross`, `net`, `cash` (1 minus net), `sectors` net weights, `top10` share of gross, `cost` in currency, one-way `turnover`, order count |
| `unmanaged` | Held positions in names sleeves do not see (outside research set; can include held-out names); never sold |
| `carried` | Unfilled orders of previous proposal; `merged` when an order here carries it |
| `cuts` | `kind: adv`: order cut to ADV bound, `symbol`, `strategy`, `wanted`, `kept` shares, `adv_participation`, `bound`. `kind: ruin`: every sleeve scaled to ruin bound, `loss` before scaling, `bound`, `scale` |
| `ruin` | `loss` (1st-percentile 252-day loss before scaling), `bound`, `scale`, `paths`, `horizon`, `block`, `periods` (common dates), `seed`; null with `reasons.ruin` |
| `reasons` | Why a null field is null: `ruin` |

Sizing, annual units, vol is std of run's stored net series times sqrt(252):

1. Tier from ledger, through proposal's `as_of`: `backtest` with no fills;
   `tracked` when sleeve's real fills span at least
   `thresholds.tracked_days` (63) calendar days from first fill to `as_of`
   and realized path's tracking error against `measure`'s model path (as
   `check --live` computes it) is at or under `thresholds.tracking_error`.
   Fewer days or tracking breach keeps `backtest`.
2. `edge_scale = min(1, max(0, (dsr - 0.5) / 0.45))`, 0 when `dsr` null: 0
   at DSR 0.5, 2/3 at 0.8, 1 at 0.95.
3. Sleeve weight is `kelly_cap`, or `lib/sizing.py`'s weight when book has
   one,
   `kelly_cap = kelly_fraction.<tier> * edge_scale * sharpe_net / vol_net`;
   zero when Sharpe is null or negative. `max_weight` bounds names (step 5),
   not sleeves. Sleeve with no real fill takes exactly
   `sizing.entry_weight`.
4. Sum of sleeve weights above 1 scales every sleeve down to sum 1; rest is
   cash. Then ruin: joint stationary block bootstrap (mean block 21 days) of
   weighted sleeves' stored net series on common dates, 1000 paths of 252
   days, generator seeded from proposal date's ordinal, so proposal
   reproduces. Loss is 1 minus compounded wealth; statistic is loss at 1st
   percentile of wealth. Over `sizing.ruin_bound` (0.35): every sleeve
   scales by `ruin_bound / loss` once, one `cuts` entry `kind: ruin`. Under
   252 common periods, or weighted sleeve with no stored series: `ruin`
   null, reason under `reasons.ruin`, no scaling.
5. Name's net weight across sleeves above `sizing.max_weight` scales that
   name down in every sleeve alike.
6. Target is whole shares at last close on or before `date`, toward zero.
   Order is target minus held. Order whose quantity times price over 21-day
   dollar ADV passes `max_adv_participation` is cut to bound and listed
   under `cuts`; unknown ADV cuts it to zero.
7. Sleeves share one real account: real shares no sleeve filled (opening
   holdings, retired sleeves) first cover sleeves' buys in name order; rest
   lands on last sleeve, whose diff sells it. Older dry-run fills count
   toward no position.

Order of previous proposal carries when no real fill of same symbol, sleeve,
and side is dated on or after that proposal, and no `reject` decision names
its stem. Estimated cost: notional times run's trade-weighted half-spread
plus `commission_bps` of symbol's exchange.

## Fill table

`record --fills:file <table> --proposal <stem>` table: CSV with header
`symbol,side,quantity,price,date` (optional `strategy` column), or JSON list
of objects with same keys. Each fill must name an order's `symbol` and
`side` in `proposals/<stem>.json` (`strategy` too when two sleeves share
both), positive `quantity` and `price`, `date` not after today. `record`
builds `fills` batch with `proposal` set to stem and sends it through gate:
any miss refuses whole table. `approve` decision answers proposal: it leaves
open proposals.
