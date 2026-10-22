# critique

## Task

Judge one run: blockers that change decision, concerns that do not.

## Reads

- `AGENTS.md`, then this file; `$R`, `$U`, `$B` as its `## Commands` defines
  them.
- Critique reference at path lead's values give: item shape, verdict rule,
  batch example.
- `$R check "$B" <run id>`, run line through `api.ledger`, hypothesis it
  names, `strategies/<name>/`, files its `code_files` and `extensions` name.
- Core items: `look-ahead`; `survivorship` (and universe by outcome);
  `multiplicity` (trials, tuned parameters); `costs-capacity` (at cap);
  `concentration` (one year, one regime, one name); `hindsight`.
- Book items: every file under `research/critique/`.
- Never held-out list, never author's receipt.

## Writes

- `research/critiques/<run id>.json`: one `critiques` batch, `by` your agent
  name, `verdicts` for every core and book item.
- Nothing else; never `record`.

## Rules

- Invariants in `AGENTS.md`.
- Never critique own run.
- Blocker quotes file and line or scorecard field behind it; else concern.

## Output

Final message, one JSON object, nothing else:
`{"type": "receipt", "unit": "critique", "brief": "<git hash-object delegates/critique.md at start>", "agent": "<agent>", "status": "done|partial|stopped", "wrote": ["<path>"], "ids": ["<run id>"], "summary": "<one line>", "next": "<one line>", "friction": "<what blocked, or empty>"}`

## Limit

One run. On hitting time limit: write blockers found, status `partial`.

## Lessons
