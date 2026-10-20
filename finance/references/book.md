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
  data/manifest.json          sha256, rows, dates per stored file
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
| run | `run_id`, `hypothesis_id`, `family_id`, `strategy`, `data_snapshot`, `code_hash`, `config`, `scorecard` |

Fill from `holdings` carries `holdings: true` and `price` equal to
`cost_basis`, `null` when none given. Fill from `bin/send` carries
`approval`, the approval file's name.

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
   placeholder `signal.py`, `config.json`, `README.md`.
2. `.claude/settings.json` deny rules; existing settings kept.
3. `bin/send` (mode 755) with `RECORD` bound to this skill's realpath.
4. `preferences.json`, `limits.json` defaults, then `book.json`.
5. Held-out list: per sector, quarter of `--universe:file` names, half
   rounded up, whose salted digests sort first; without universe, empty list
   and `signal:` saying so.

## Approval file

Operator writes `approvals/<YYYY-MM-DD>.json`:

```json
{"date": "YYYY-MM-DD", "orders": [{"symbol": "...", "side": "buy|sell", "quantity": 10, "price": 12.5, "strategy": "<name>", "adv_participation": 0.004}]}
```

`bin/send` checks, in order: file resolves under `approvals/`; `date` is
today (UTC); every order's `adv_participation` at most
`limits.max_adv_participation` and strategy `status` `live` (`paper` too in
dry run); then prints order table, asks typed `yes` on terminal, calls
`submit`, records fills, moves file to `sent/`. `--dry-run` skips prompt,
fills at `price` with `dry_run: true`, moves nothing.
