# author

## Task

Turn one registered hypothesis into strategy code and one measured run.

## Reads

- `AGENTS.md`, then this file; `$R`, `$U`, `$B` as its `## Commands` defines
  them.
- `$R check --schema strategy` first: `signal.py` and `config.json`
  contract.
- Hypothesis line through `api.ledger`; `strategies/`, `lib/`, `INDEX.md`.
- Never held-out list.

## Writes

- `strategies/<name>/`: `signal.py`, `config.json`, `README.md`; never
  `status`.
- `lib/` helpers or hooks, each with a test under `tests/` and an `INDEX.md`
  row.
- Run lines only through `$R measure "$B" <name> --agent <agent>`.
- Nothing else; never `record`.

## Rules

- Invariants in `AGENTS.md`.
- `config.json` `family_id` is the hypothesis's; `holding_days` at least
  `limits.min_holding_days`.
- Every run spends a trial, refused ones too; never measure again to shop
  for a better number. Never `--reason` unless lead's values name the gate.
- Missing accessor, source, metric, or cost model: write the `lib/` hook,
  test it, go on.

## Output

Final message, one JSON object, nothing else:
`{"type": "receipt", "unit": "author", "brief": "<git hash-object delegates/author.md at start>", "agent": "<agent>", "status": "done|partial|stopped", "wrote": ["<path>"], "ids": ["<run id>"], "summary": "<one line>", "next": "<one line>", "friction": "<what blocked, or empty>"}`

## Limit

Spawn line's `runs`. On hitting it: stop, status `partial`, name best run.

## Lessons
