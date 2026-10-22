# Book

## Layout

```text
<book>/
  book.json                   marker: book id, created, skill commit at start, held-out path
  README.md                   operator's plain guide
  AGENTS.md                   agents' standing instructions
  CLAUDE.md                   relative symlink to AGENTS.md; fallback line "Read AGENTS.md."
  limits.json                 governed: asset cap, bounds, thresholds, families
  preferences.json            focus sectors, exclusions, cadence, schedule, heartbeat_minutes, quiet_hours; through record
  universe.csv                copy of start's --universe:file
  data/raw/<source>/          immutable parquet per load; see sources
  data/returns/<run_id>.parquet  each run's gross and net series, immutable
  data/manifest.json          sha256, rows, dates per stored file; git ignores data/, so digests guard it
  data/features/              materialized features
  ledger/
    hypotheses.jsonl  critiques.jsonl  decisions.jsonl  fills.jsonl
    runs.jsonl  runs/<agent>.jsonl  incidents.jsonl  regimes.jsonl
    scored.jsonl
    pad/scratch.jsonl         agent's free memory, not ledger; agent appends and greps it
  proposals/  approvals/  rejected/
  strategies/<name>/
    signal.py  config.json  README.md  status  strategy-local helpers
  lib/                        agent's shared modules; signal.py imports lib.<module>
  tools/                      agent's scripts; read book through btm_finance.api
  research/<topic>/           notes, tables, sources per line of inquiry
  research/backlog/<id>.md    candidate hypothesis, ranked weekly; shape below
  research/calendar/          event calendars and trigger lists per event family
  research/weekly/            weekly research note, <YYYY-Www>.md
  research/critiques/  research/scored/  research/regime/  research/runs/  research/literature/  research/universe/
                              delegate outputs, one folder per unit
  delegates/<slug>.md         fixed brief per delegated unit, summon's six fields; lead edits after friction
  tests/                      tests for lib/ and tools/; conftest.py puts book root on sys.path
  tests/reference/            this book's pinned scorecard
  INDEX.md                    path | purpose, one line per lib module, tool, research topic, delegate brief
  features/  ext/
  .gitignore                  /data, __pycache__/, .worktrees/
  .worktrees/<agent>/         delegate worktree, data symlinked to book data/

<path start --held-out named>, default
${XDG_STATE_HOME:-$HOME/.local/state}/btm-skills/finance/<book-id>/held-out.json
                              {"<sector>": ["SYM", ...]}, sorted
```

- `research/<topic>/README.md`: status and open questions of that line of
  inquiry.
- `research/backlog/<id>.md`: one candidate hypothesis, not yet registered.
  State mechanism, counterparty, falsifier, odds, expected information gain,
  and which existing run (run id) it would differ from, and how. Combination
  entry names its two or three components and expected correlation bound
  (`families` Combinations). Rejected candidate stays, status line naming
  reason: critique item `multiplicity` reads it. Rank weekly; only top gets
  registered. No gate reads this shape.
- `research/calendar/`, `research/weekly/`: `README.md` status line, then
  one file per event family, one note per week.
- `data_snapshot` hashes sorted sha256 of source files under `data/raw/`
  only; `data/returns/` files never move it.
- `status` holds one word: `research`, `probe`, `paper`, `live`, or
  `retired`; absent or empty reads `research`.
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
- Update `INDEX.md` (`path | purpose`) and `research/<topic>/README.md` in
  same commit as file they describe. Delete dead script by commit lead
  merges, its `INDEX.md` line with it.
- Test `lib/` and `tools/` under `tests/`, run with `$U pytest "$B/tests"`.

`btm_finance.api`: `open_book(path)`; `ledger(book, kind)` for newest-wins
rows of one kind, superseded lines dropped (`run` joins every runs file,
oldest first); `research(book).at(day)` for `Market` on last bar on or
before `day` over research names, `.dates` for bar dates;
`research(book).folds("train")` for same over training blocks only (first
`thresholds.folds - 1` of `thresholds.folds` equal contiguous blocks of bar
dates; `scorecard`), miner delegate's only price reader; `receipt(text)`
checks delegate's final message; `outside_scope(book, commit, scope)` lists
each path `git diff main...<commit>` names outside scope entries (entry
ending in `/` holds paths under it). None serves held-out names.

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
| hypothesis | `kw`, `strategy`, `family_id`, `capacity_class`, `falsifier`, `falsifier_by`, `counterparty`, `min_holding_days`; optional `odds` (`p_win`, `payoff`, `horizon_days`, `kelly_implied`), `chain`, `expectation_source`, `discounted`, `confidence` (critique flags each one absent in family with `event: true`) |
| critique | `kw`, `run_id`, `blockers`, `concerns`, `by` |
| decision | `kw`, `subject`, `action`, `reason`; optional `odds`, `applied` (governed paths) with `objects` (path to committed blob id, stamped by `record`); `forgo` names strategy |
| scored | `kw`, `subject` (live hypothesis id), `resolved`, `outcome`, `realized_return`, `brier`, `log_score`, `attribution` (`market`, `factor`, `currency`, `idiosyncratic`, `costs`) |
| regime | `kw`, `as_of`, `confidence`; optional `falsified`, `supersedes`; any other field free JSON |
| fill | `symbol`, `side`, `quantity`, `price`, `date`, `strategy`, `dry_run` |
| run | `run_id`, `hypothesis_id`, `family_id`, `strategy`, `data_snapshot`, `code_paths`, `code_objects` (path to committed blob id), `config`, `scorecard`; also `params`, `reasons`, `engine` (skill commit, `numpy`, `pyarrow`), `tolerance`, `held_out`, `exclusions`, `refused`, `peers`, `span`, `returns`, `agent`, `regimes`, `regime_days`, `imports` |
| incident | `kind`; see Incidents |

`chain` is chain id from `macro` table or `none`. `start` sets baseline's
`falsifier_by` one year after start date. `scored` scores stated `p_win`
against outcome: `brier` is squared error of probability, `log_score` log of
probability given to what happened.

Regime line in suggested shape; `record` reads only `kw`, `as_of`,
`confidence`, `falsified`, `supersedes`:

```json
{"id": "<id>", "ts": "<ts>", "kw": ["late", "cycle"], "as_of": "YYYY-MM-DD", "short_cycle": "easing|mid-expansion|late-expansion|tightening|contraction", "long_cycle": "early|bubble|top|depression|deleveraging|normalization", "bubble_count": {"count": 2, "evidence": ["<item 1 evidence>", "<item 4 evidence>"]}, "policy_mix": ["austerity|defaults|transfers|printing"], "other_forces": {"internal_order": "...", "external_order": "...", "nature": "...", "technology": "..."}, "observables": {"<name>": {"value": "<as reported>", "as_of": "YYYY-MM-DD", "source": "<url>"}}, "confidence": 0.6, "falsified": ["<chain id>"], "supersedes": "<regime id>"}
```

Gate refuses `as_of` that is not ISO date, `confidence` outside 0 to 1,
unknown chain id under `falsified`, `supersedes` naming no live regime id.
Vocabularies above are never checked; `evidence` count other than
`bubble_count.count` is signal only. Regime record is newest live line by
`as_of`, later line winning tie; `stale` when `as_of` is more than
`limits.regime_stale_days` (default 90) before today, or before proposal
date in proposal file.

Fill from `holdings` has `holdings: true` and `price` equal to `cost_basis`,
`null` when none given. Fill from `record --fills:file` or `--dry-run` has
`approval`, approval file's stem.

## Incidents

`incidents.jsonl` lines come from scripts, never from `record`:

| `kind` | Writer | Keys, or breach |
| --- | --- | --- |
| `integrity` | any read of `data/` | `file`, `problem`, `expected`, `found` |
| `drawdown` | `check --live` | realized drawdown over `drawdown_review_multiple` times run's `max_drawdown` |
| `underperform` | `check --live` | consecutive months below baseline sleeve, at `underperform_months` or over |
| `slippage` | `check --live` | mean fill-minus-reference share, signed by side (reference: `price` of order with fill's symbol and side in proposal its approval names), over run's `half_spread_mean` plus largest `commission_bps` |
| `tracking` | `check --live` | annualized std of realized minus model daily return over `thresholds.tracking_error` (default 0.05) |
| `stale` | `check --live` | trading days since last bar over 5 |

Every `check --live` line has `strategy`, `value`, `limit`, `as_of`, `by`.
Same strategy and kind within 7 days of `as_of`: not appended again.

## Ownership

| Path | Writer | Agent may |
| --- | --- | --- |
| `limits.json`, `approvals/*.json`, `strategies/*/status` (governed) | agent, only on operator's instruction in chat, same turn | change, commit, then record `decision` (spine Invariants) |
| `preferences.json` | `record`, after user confirms | read; change through `record` |
| `ledger/` except `pad/` | `record`; run lines `measure`; incident lines `load`, `check --live` | append through `record` only; bare `check` warns on any other write it can see |
| `ledger/pad/scratch.jsonl` | agent | append lines, grep; never gated |
| `strategies/` except `status`, `lib/`, `tools/`, `research/`, `tests/` except `reference/`, `INDEX.md`, `features/`, `ext/`, `proposals/` | agent | edit on branch |
| `README.md`, `AGENTS.md`, `CLAUDE.md` | `start --answers:file` | edit operator-facing prose on branch; keep `AGENTS.md` `## Invariants` verbatim from template; keep `CLAUDE.md` link or fallback line |
| `data/`, `universe.csv` | `load`, `start` | read through data model only; never edit |
| held-out list, path in `book.json` `held_out` | `start` | never read |

## What start writes

1. Directories above, `strategies/baseline/` with `status` `research`,
   static multi-factor `signal.py`, `config.json`, `README.md`; baseline
   hypothesis (`capacity_class: crowded`) through gate. Empty
   `lib/__init__.py`; `tests/conftest.py`; `research/backlog/`,
   `research/calendar/`, `research/weekly/`, each with `README.md` of one
   status line; `INDEX.md` with column line `path | purpose`, one row per
   those three folders and per seeded brief. `delegates/` seeded with
   starter briefs for `author`, `critique`, `miner`, `reader`, `scorer`,
   `regime`, `janitor`, at most 25 lines each.
2. `preferences.json`, `limits.json` defaults, then `book.json` with
   `held_out` path.
3. Held-out list: per sector, first quarter of `--universe:file` names by
   symbol sort, half rounded up; deterministic. Receipt reports path and
   count only. Without universe, empty list and `signal:` saying so.
4. With `--answers:file`: `README.md`, `AGENTS.md`, `CLAUDE.md` and answers
   (`onboard`). Without: none of three files, `onboarded` false.
5. `.gitignore` holding `/data`, `__pycache__/`, `.worktrees/` (existing
   lines kept); `git init -b main` unless path is inside git work tree. Then
   one commit `start: <id>` on current branch, `onboard` decision naming
   every governed file it wrote by blob id, and second commit of that
   decision line.

## Proposal file

`recommend <date>` writes `proposals/<date>.json` once; `--force` writes
`<date>.2.json`, then `.3`; `check <date>` reads newest. Sleeves see
research names only, through `Market` on `as_of`, last bar on or before
`date`, weights set exactly as `measure` sets them, ADV clip included
(`scorecard`).

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

Sizing, annual units, vol is std of run's stored net series times sqrt(252):

1. Tier from ledger, through proposal's `as_of`: `backtest` with no fills;
   `paper` when sleeve's dry-run fills span at least
   `thresholds.paper_min_days` (63) calendar days from first fill to `as_of`
   and realized path's tracking error against `measure`'s model path (as
   `check --live` computes it) is at or under `thresholds.tracking_error`;
   `live` same on real fills. Fewer days or tracking breach keeps lower
   tier. Status `probe` gives tier `probe`.
2. `edge_scale = min(1, max(0, (dsr - 0.5) / 0.45))`, 0 when `dsr` null: 0
   at DSR 0.5, 2/3 at 0.8, 1 at 0.95.
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
   null, reason under `reasons.ruin`, no scaling. Risk share lands under
   `advisory`; no cut.
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
trade-weighted half-spread plus `commission_bps` of symbol's exchange.

## Approval file

`check <date>` prints `approval_template` with every order, `date` set to
proposal date, `reply` empty. Approved copy (spine Propose and approve step
3):

```json
{"date": "YYYY-MM-DD", "proposal": "<proposal stem>", "reply": "<operator's words>", "orders": [{"symbol": "...", "side": "buy|sell", "quantity": 10, "price": 12.5, "adv_participation": 0.004, "strategy": "<name>", "limit": null}]}
```

`check <book> approvals/<date>.json` (path absolute or book-relative,
resolving under `approvals/`) checks: `date` is today (UTC); `reply`
non-empty; file clean and some `approve` decision names its committed blob,
so edit after yes fails until committed and recorded again; `proposal` names
file under `proposals/`; every order's `symbol`, `side`, `strategy` match
order of that proposal; `adv_participation` at most
`limits.max_adv_participation`; strategy `status` `paper`, `probe`, or
`live`. Returns `orders` (each with `account` its strategy trades),
`problems` (empty when valid), `next`; exit 1 on any problem.

`record --dry-run` records fill per paper order at `price` with
`dry_run: true`; refuses file failing `check` or holding `probe` or `live`
order. `record --fills:file` table: CSV with header
`symbol,side,quantity,price,date` (optional `strategy` column), or JSON list
of objects with same keys. Each fill must name order's `symbol` and `side`
(`strategy` too when two sleeves share both), on non-`paper` strategy,
positive `quantity` and `price`, `date` not after today; fills land
`dry_run: false`. Either way `record` builds `fills` batch with `approval`
set to file stem and sends it through gate: any miss refuses whole table. No
file moves. `approve` decision answers proposal: it leaves open proposals.
