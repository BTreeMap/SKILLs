# Verdict Taxonomy, Confidence, and Abstention

## Verdicts

Exactly one per claim.

| Verdict | Definition |
| --- | --- |
| supported | Independent evidence confirms the claim as written |
| contradicted | Authoritative evidence shows the claim was wrong at claim-time |
| outdated | Accurate at claim-time; a later authoritative source supersedes it |
| conflicting | Comparably authoritative sources disagree; neither clearly wins |
| missing-context | Literally true but misleading without a qualifier the correction must add |
| insufficient-evidence | Verifiable in principle; retrieval found no adequate source |
| unverifiable | Not checkable in principle or in this environment (subjective, paywalled, no web access, future prediction); reason required in notes |

Distinctions:

- `contradicted` vs `outdated` is decided by claim-time, not by how wrong the
  claim is now.
- `conflicting` is reserved for peer sources. A primary publisher beats an
  aggregator: that is not a conflict.
- `insufficient-evidence` (we could not find it) is never collapsed into
  `unverifiable` (nobody could).

## Confidence

Derived from evidence agreement, not from verbal self-assessment.

| Band | Criteria |
| --- | --- |
| high | Two or more independent sources agree; at least one is top-tier for the claim type; no credible disagreement found |
| medium | One authoritative source, or independent sources with minor discrepancies (rounding, as-of dates) |
| low | Only indirect, second-hand, or partially matching evidence |

Independence: different publishing organizations, neither syndicating,
mirroring, or citing only the other.

## Abstention

- `low` confidence forces `correction: null`, whatever the verdict.
- Corrections are proposed only for `contradicted`, `outdated`, and
  `missing-context` at `medium` or `high` confidence, and require the
  two-independent-source rule.
- `conflicting` never yields a correction: present both sources and let the
  user decide; offer an as-of qualifier as the only safe edit.
- When abstaining on a claim the user flagged as important, suggest
  qualification language ("according to SOURCE as of DATE") instead of a
  factual replacement.

## Correction text rules

- Match the source's precision: an approximate source value stays marked
  approximate; never add precision the source lacks.
- Time-sensitive corrections carry an as-of qualifier with an absolute date.
  Never "latest", "current", or "recently".
- Keep the replacement minimal: change the failing span, preserve the
  sentence's voice and the document's language and formatting.
