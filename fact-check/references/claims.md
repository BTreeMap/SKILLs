# Claim Inventory: Decomposition and Type Routing

## Atomic decomposition

Split each verifiable statement into atomic claims: one independently
checkable proposition each.

- Decontextualize: resolve pronouns, elided subjects, and relative time
  ("the new release" becomes the named release; "last year" becomes the
  absolute year derived from the document's timestamp).
- Map every claim to its exact source span: file, line range, verbatim quote.
  The span is what an approved correction later replaces.
- Granularity cap: never fragment below one proposition. A sentence bundling
  subject, action, and date ("Org O released product P in month M") is ONE
  claim; over-fragmentation degrades verification.
- A compound sentence with genuinely independent propositions ("P has
  property A and costs B") becomes two claims, each carrying the shared
  subject after decontextualization.

## What to skip

Opinions, recommendations, tutorial instructions, architectural rationale,
rhetoric, hedged speculation ("may", "could"), and self-referential document
text.
When a sentence mixes fact and opinion, extract only the factual proposition.

## Claim types and retrieval routing

Type each claim; the type selects the retrieval strategy.

| Type | Definition | Route |
| --- | --- | --- |
| spec | Technical capability, limit, or parameter of a product | Vendor's official documentation for the exact product and version |
| version | Version identifier or "latest release" assertion | Package registry or the project's release page; registries beat blogs |
| date | Release, publication, or event date | Primary announcement from the owning organization |
| statistic | Measured or surveyed quantity | Original publisher of the measurement, not re-reporting |
| computation | Value derivable from other values in the document (totals, percentages, deltas) | RECOMPUTE from the document's own inputs; search only for missing external inputs |
| quotation | Attributed verbatim quote | Locate the original text; verify wording and attribution |
| other | Verifiable but untyped | Two-independent-source rule, strictest reading |

## Temporal fields

Record with each claim: claim-time (document timestamp: front-matter date,
git log date of the span, or user-stated; if none, note "claim-time unknown"
and judge only against verification-time). Evidence-time and
verification-time land in the verdict record during verification.
