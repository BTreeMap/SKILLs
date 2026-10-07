# Verdicts, Confidence, and Corrections

## Verdicts

Assign exactly one per claim.

| Verdict | Definition |
| --- | --- |
| supported | Independent evidence confirms the claim as written |
| contradicted | Authoritative evidence shows the claim was wrong at claim-time |
| outdated | Accurate at claim-time; a later authoritative source supersedes it |
| conflicting | Comparably authoritative sources disagree; neither clearly wins |
| missing-context | Literally true but misleading without a qualifier the correction must add |
| insufficient-evidence | Verifiable in principle; retrieval found no adequate source |
| unverifiable | Not checkable in principle or in this environment (subjective, paywalled, no web access, future prediction); reason required in notes |

`insufficient-evidence` (we could not find it) is never collapsed into
`unverifiable` (nobody could).

## Time

Distinguish claim-time (the document's timestamp), evidence-time (the
source's publication date), and verification-time (today). If claim-time is
unknown, judge only against verification-time. Claim-time alone decides
`contradicted` versus `outdated`: `outdated` requires both accuracy at
claim-time AND a later authoritative source superseding the claim.

## Conflicts

- Within one organization: the most recently published tier-1 document
  (tiers in `evidence`) wins; note superseded values in `notes`.
- Across organizations of comparable authority: verdict `conflicting`,
  quoting both. `conflicting` is reserved for such peer sources.
- Primary publisher versus aggregator: no conflict. The primary wins
  silently; the aggregator goes to `notes`.
- Evidence versus prior knowledge: evidence wins; cite it and flag the
  tension in `notes`.

## Confidence

Derive confidence from evidence agreement alone.

| Band | Criteria |
| --- | --- |
| high | Two or more independent sources agree; at least one is top-tier for the claim type; no credible disagreement found |
| medium | One authoritative source, or independent sources with minor discrepancies (rounding, as-of dates) |
| low | Only indirect, second-hand, or partially matching evidence |

Independence follows Invariant 4.

## Abstention

- `low` confidence forces `correction: null`, whatever the verdict.
- Propose a correction only for `contradicted`, `outdated`, and
  `missing-context` at `medium` or `high` confidence, and only under the
  two-independent-source rule.
- `conflicting` never yields a correction: present both sources and let the
  user decide; offer an as-of qualifier as the only safe edit.
- When abstaining on a claim the user flagged as important, suggest only
  qualification language ("according to SOURCE as of DATE").

## Correction text

- Match the source's precision: an approximate source value stays marked
  approximate; never add precision the source lacks.
- A date correction or any other time-sensitive correction carries an as-of
  qualifier with an absolute date, never "latest", "current", or "recently".
- Keep the replacement minimal: change the failing span, and preserve the
  sentence's voice and the document's language and formatting.
