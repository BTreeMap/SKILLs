# bet

## Task

Answer one question lead states: one registrable hypothesis, or one no-bet
with its reason. Question may scope to one held name.

## Reads

- `AGENTS.md`, then this file.
- `check "$B"`, `check --schema record`.
- `research/`, `ledger/` through `api.ledger`, prices and fundamentals
  through `api.research(book)`; public sources.
- Never held-out list.

## Writes

- `research/bets/<agent>.md`: evidence, each number with its source.
- `research/bets/<agent>.json`: one `hypotheses` batch; none for no-bet.
- Nothing else; never `record`.

## Rules

- Invariants in `AGENTS.md`.
- Hypothesis carries `odds` with `kelly_implied` above 0, `falsifier`,
  `falsifier_by`, `counterparty`, `mechanism`, `priced` and `implied`, and
  `capacity` at `limits.asset_cap`.
- No-bet when edge after costs at cap is not above 0, or no counterparty is
  named.

## Output

Final message, one JSON object, nothing else:
`{"type": "receipt", "unit": "bet", "brief": "<git hash-object delegates/bet.md at start>", "agent": "<agent>", "status": "done|partial|stopped", "wrote": ["<path>"], "ids": [], "summary": "<one line>", "next": "<one line>", "friction": "<what blocked, or empty>"}`

## Limit

Twenty fetches. On hitting it: write what holds, status `partial`.

## Lessons
