# Claim Inventory: Decomposition and Typing

## Atomic decomposition

Split each verifiable statement into atomic claims, each one independently
checkable proposition.

- Decontextualize: resolve pronouns, elided subjects, and relative time
  ("the new release" becomes the named release; "last year" becomes the
  absolute year derived from the document's timestamp).
- Map every claim to its exact source span: file, line range, verbatim
  quote. An approved correction later replaces that span.
- Never fragment below one proposition. A sentence bundling subject, action,
  and date ("Org O released product P in month M") is ONE claim.
- A compound sentence of independent propositions ("P has property A and
  costs B") becomes two claims, each carrying the shared subject after
  decontextualization.

## What to skip

Opinions, recommendations, tutorial instructions, architectural rationale,
rhetoric, hedged speculation ("may", "could"), and self-referential document
text. When a sentence mixes fact and opinion, extract only the factual
proposition.

## Claim types

Give each claim one type; the type selects its retrieval route in
`evidence`.

| Type | Definition |
| --- | --- |
| spec | Technical capability, limit, or parameter of a product |
| version | Version identifier or "latest release" assertion |
| date | Release, publication, or event date |
| statistic | Measured or surveyed quantity |
| computation | Value derivable from other values in the document (totals, percentages, deltas) |
| quotation | Attributed verbatim quote |
| other | Verifiable but untyped |

## Claim-time

Record each claim's claim-time: the document's timestamp, taken from the
front-matter date, the git log date of the span, or a user statement. If
none exists, note "claim-time unknown".
