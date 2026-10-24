# bet

## Task

Answer one question lead states: one registrable hypothesis, or one no-bet
with its reason. Question may scope to one held name.

## Reads

- `AGENTS.md`, then this file; `$R`, `$U`, `$B` as its `## Commands` defines
  them.
- `$R check "$B"` (`families`: `trials_used` against `trials`),
  `$R check --schema record`, `limits.json`.
- `research/`, ledger through `api.ledger`, prices and fundamentals through
  `api.research(book)`, channel posts through `api.posts(book)`; public
  sources.
- Never held-out list.

## Writes

- `research/bets/<agent>.md`: evidence, each number with its source.
- `research/bets/<agent>.json`: one `hypotheses` batch; none for no-bet.
- Nothing else; never `record`.

## Rules

- Invariants in `AGENTS.md`.
- Hypothesis carries every field `record` requires: `kw` (two or three
  words), `strategy` (new lowercase name), `family_id` (key of
  `limits.families` with trials left), `falsifier`, `falsifier_by` (kill
  date), `counterparty`, `min_holding_days` (at least
  `limits.min_holding_days`), `odds` (`p_win`, `payoff` as gain per unit
  lost, `horizon_days`, `kelly_implied` = `p_win - (1 - p_win) / payoff`
  within 0.01, above 0).
- Add `priced` and `implied` (what market pays now, what thesis implies) and
  `capacity` at `limits.asset_cap`; `mechanism` only when stated before
  looking at returns.
- Question varying a rejected bet names prior no-bet file: read it first;
  evidence says what differs.
- No-bet when `kelly_implied` is at or below 0, edge after costs at cap is
  not above 0, or no counterparty is named: no batch file, `ids` empty,
  `summary` `no-bet: <reason>`.

## Output

Final message, one JSON object, nothing else:
`{"type": "receipt", "unit": "bet", "brief": "<git hash-object delegates/bet.md at start>", "agent": "<agent>", "status": "done|partial|stopped", "wrote": ["<path>"], "ids": [], "summary": "<one line>", "next": "<one line>", "friction": "<what blocked, or empty>"}`

## Limit

Twenty fetches. On hitting it: write what holds, status `partial`.

## Lessons
