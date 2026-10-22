# author

## Task

Turn one registered hypothesis into strategy code and one measured run.

## Reads

- `AGENTS.md`, then this file.
- Hypothesis line through `api.ledger`, `check --schema strategy`,
  `strategies/`, `lib/`, `INDEX.md`.
- Never held-out list.

## Writes

- `strategies/<name>/`: `signal.py`, `config.json`, `README.md`.
- `lib/` helpers or hooks, each with a test under `tests/` and an `INDEX.md`
  row.
- Run lines only through `measure "$B" <name> --agent <agent>`.
- Nothing else; never `record`, never `status`.

## Rules

- Invariants in `AGENTS.md`.
- `config.json` `family_id` is the hypothesis's.
- Measure at most the runs lead names; never `--reason` unless lead's values
  name the gate.
- Missing accessor, source, metric, or cost model: write the `lib/` hook,
  test it, go on.

## Output

Final message, one JSON object, nothing else:
`{"type": "receipt", "unit": "author", "brief": "<git hash-object delegates/author.md at start>", "agent": "<agent>", "status": "done|partial|stopped", "wrote": ["<path>"], "ids": ["<run id>"], "summary": "<one line>", "next": "<one line>", "friction": "<what blocked, or empty>"}`

## Limit

Runs lead names. On hitting it: stop, status `partial`, name best run.

## Lessons
