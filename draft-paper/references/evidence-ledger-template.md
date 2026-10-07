# Evidence ledger

One row per empirical claim in the draft; a claim with no row does not ship.
Fill the ledger in during the evidence stage and keep it current through
every revision.

<template for="evidence-ledger">
| Claim ID | Claim (as stated in draft) | Artifact (file path) | Location in artifact | Status |
|----------|---------------------------|----------------------|----------------------|--------|
| C1       | _example: "Method X reaches 75.4% on DeepSWE v1.1, +1.4 over the best baseline"_ | `runs/deepswe/metrics.json` | `summary.mean`, seeds 0-2 | supported |
| C2 | | | | |
</template>

## Statuses

| Status | Meaning |
| --- | --- |
| supported | The artifact backs the exact statement as written (same metric, split, baseline). |
| exploratory | Post-hoc analysis worth reporting but not confirmatory; the draft labels it as such. |
| unsupported | No artifact backs the claim. Cut the claim or run the experiment before submission. Never soften it to "plausible" in prose. |

## Rules

- Resolve numbers in prose, tables, figures, and captions to the same ledger
  row.
- Give a reduced, narrowed, or failed campaign a row describing what
  actually ran. Results sections describe what ran, not what was planned.
- A human approves the ledger before drafting and re-checks it after every
  revision that touches a number.
