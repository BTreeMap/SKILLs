# Sources

Load before first `load` of any source, or when `load` exits 2. Every route
here writes raw store; strategy code never reads it, only data model.

## Route ladder

Take first rung that serves need; drop rung only on evidence (exit 2 twice,
missing names, field absent).

| Need | First | Then | Last |
| --- | --- | --- | --- |
| Daily bars | `tiingo` | `csv` from any vendor export | none: name gap to operator |
| Fundamentals, point in time | `edgar` (US filers) | `csv` from vendor with release dates | disable fundamentals families for those names |
| Factor returns | `french` | `csv` with symbol `_factors` | none |
| Delistings, index membership | `csv` | none | record gap; survivorship then open in every critique |
| Canadian names | `csv` | `tiingo` for prices only | no fundamentals |

## Raw store

```text
data/raw/<source>/<stem>.bars.parquet     symbol, date, open, high, low, close, volume, adj_factor, exchange
data/raw/<source>/<stem>.events.parquet   symbol, field, event_time, knowledge_time, value
data/manifest.json                        per file: path, sha256, rows, source, table, loaded_at, since, through
```

- `stem` is load day (UTC); second load same day takes `<day>-2`, then `-3`.
  File never overwritten. Load yielding no rows writes nothing.
- Every `load` re-hashes every listed file first. Changed bytes or missing
  file: one `integrity` line in `ledger/incidents.jsonl`, exit 1 naming
  file, nothing fetched. File stays in place: tell operator, never delete or
  rewrite it; operator restores from backup.
- `data_snapshot` is sha256 over sorted digests of source files only; runs'
  returns files stay listed for integrity but never move it. `score` stamps
  it on every run line.
- Same `(symbol, date)` bar in two files: latest `loaded_at` wins. Same
  `(symbol, field, event_time, knowledge_time)` event: same rule. Correct
  vendor error by loading fixed rows with `--since` at their first date.
- `--since` default: day after source's last `through`; first load reaches
  25 years back. Rows before `--since` are dropped with `signal:` count.
- Bar knowledge time is bar date. Event `knowledge_time` is day value became
  public; every model accessor hides rows known after its day.

## csv

Universal route: any vendor export, delistings, membership history.
`--config:file` required:

```json
{"bars": "<path>.csv", "events": "<path>.csv", "columns": {"symbol": "Ticker", "date": "Day"}}
```

- Paths absolute or relative to working directory; give `bars`, `events`, or
  both.
- `columns` maps canonical name to file's header; file lacking mapped header
  falls back to canonical name. Headers match case-insensitively.
- Bars: `symbol`, `date`, `close` required; `open`, `high`, `low`, `volume`,
  `exchange` optional (NaN, empty); `adj_factor` optional, 1.0 when blank.
  `adj_factor` is cumulative: adjusted price is `close` times it. Store raw
  prices plus factor, never vendor's adjusted series alone.
- Events: `symbol`, `field`, `event_time`, `knowledge_time`, `value` all
  required. Dates `YYYY-MM-DD`.
- Delisting: field `delisting`, `event_time` last trading day, value
  `performance` (stored 1) or `merger` (stored 2). Terminal return then
  follows `limits.json` `delisting` by exchange.
- Membership: one field per index (`member_<index>`), value 1 on entry, 0 on
  exit, `knowledge_time` announcement day.
- Exchange values `nyse`, `amex`, `nasdaq`, `tsx`; anything else reads as
  `other`. `universe.csv` column `exchange` overrides bars column.
- Knowledge-time caveat: only as honest as export. Vendor file lacking
  release dates gives no point-in-time guarantee; say so on every run that
  uses it.

## french

Ken French data library, daily FF5 (2x3) and momentum zips from
`https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/`. No config
fields.

- Stored as events, symbol `_factors`, fields `mkt_rf`, `smb`, `hml`, `rmw`,
  `cma`, `mom`, `rf`, in decimal (files are percent). Missing markers
  dropped.
- `event_time` = `knowledge_time` = return date. Approximation: library
  publishes with lag and revises history; true knowledge time is later.
- Factors feed only scorecard's factor regression, never a signal.
- Trap: file layout (header line starting with comma, `YYYYMMDD` rows,
  copyright footer) is parsed strictly; changed layout exits 2 naming
  column. North America factors for Canadian names are approximation; load
  them through `csv`.

## edgar

SEC XBRL companyfacts for US filers. Ticker map from
`https://www.sec.gov/files/company_tickers.json`, then
`https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json` per name.
Config optional:

```json
{"tags": ["Revenues", "NetIncomeLoss"], "symbols": ["AAA", "BBB"]}
```

- Default tags: `Revenues`, `NetIncomeLoss`, `StockholdersEquity`, `Assets`,
  `Liabilities`, `CommonStockSharesOutstanding`, `OperatingIncomeLoss`,
  `NetCashProvidedByUsedInOperatingActivities`. Default symbols:
  `universe.csv`.
- Keeps forms `10-K`, `10-Q` only. `event_time` = period `end`,
  `knowledge_time` = `filed`. Restatement arrives as row with later `filed`;
  earlier row stays visible before it.
- Field naming: instant or one-quarter span keeps tag; fiscal-year span gets
  `<tag>:fy`; year-to-date spans dropped. Fourth quarter exists only as
  `:fy` minus three quarters: derive, never assume.
- One unit per tag: `USD`, else `shares`, else first listed.
- Pacing: script stays under SEC fair-access rate; request header names
  skill and contact. Ticker missing from map or company without facts:
  `signal:` and skipped.
- Traps: share class spelled with `-` (`BRK.B` looked up as `BRK-B`);
  issuers switch tags across years (`Revenues` versus
  `RevenueFromContractWithCustomerExcludingAssessedTax`): add both to `tags`
  and reconcile in feature code. `filed` is accept date, not market
  reaction; filings after close reach prices next session.
- Canadian filers (40-F, 6-K) are absent: fundamentals families disabled for
  them.

## tiingo

Daily prices from `https://api.tiingo.com/tiingo/daily/<ticker>/prices`.
Token from environment variable `TIINGO_API_KEY`, sent as header, never
logged or written. Missing variable: exit 1; ask operator to set it, never
ask for token in conversation. Config optional: `{"symbols": [...]}`,
default `universe.csv`.

- `adj_factor` = `adjClose / close`; raw OHLCV kept.
- `divCash` nonzero becomes event `dividend`, `splitFactor` not 1 becomes
  event `split`, both dated on ex-date bar.
- Knowledge-time caveat: dividend is announced before ex-date; storing
  ex-date as knowledge time is late, never early, so it hides nothing a
  strategy could have known. `adjClose` is recomputed by vendor after each
  later action: factor in older files can disagree with newer load; latest
  load wins.
- Traps: free tier meters requests per hour and per day; large universe
  needs several nights or paid tier. Load is all or nothing: exit 2 writes
  nothing, rerun same command. Ticker unknown to Tiingo: `signal:` and
  skipped. Exchange column empty: set it in `universe.csv`.
