# Evidence Ledger

One row per empirical claim in the draft. A claim with no row does not ship.
Fill in during the evidence stage; keep current through every revision.

| Claim ID | Claim (as stated in draft) | Artifact (file path) | Location in artifact | Status |
|----------|---------------------------|----------------------|----------------------|--------|
| C1       | _example: "Method X reaches 75.4% on DeepSWE v1.1, +1.4 over the best baseline"_ | `runs/deepswe/metrics.json` | `summary.mean`, seeds 0-2 | supported |
| C2 | | | | |

## Statuses

- **supported**: the artifact backs the exact statement as written (same
  metric, split, baseline).
- **exploratory**: post-hoc analysis worth reporting but not confirmatory;
  the draft labels it as such.
- **unsupported**: no artifact backs the claim. Cut the claim or run the
  experiment before submission. Never soften to "plausible" in prose.

## Rules

- Numbers in prose, tables, figures, and captions resolve to the same ledger
  row.
- A reduced, narrowed, or failed campaign gets a row describing what
  actually ran. Results sections describe what ran, not what was planned.
- A human approves the ledger before drafting and re-checks it after every
  revision that touches a number.
