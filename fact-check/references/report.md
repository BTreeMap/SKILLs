# Report Layout and Tiered Approval

## Evidence-first layout

Per issue: source span, then evidence quotes (including counter-evidence),
then verdict and proposed correction. Evidence before verdict, so the user
judges the evidence rather than rubber-stamping a conclusion.

<report_template>
## Fact-Check Report

Checked N claims from <FILE> (claim-time: <DATE-OR-UNKNOWN>).
Branch: <parallel|sequential>; approx cost: <TOKENS-OR-NA>.
Verdicts: supported X, contradicted X, outdated X, conflicting X,
missing-context X, insufficient-evidence X, unverifiable X.

### Corrections proposed

#### c-07 (<TYPE>, confidence <BAND>) <FILE>:<LINES>
Document says:
> <EXACT SOURCE SPAN>
Evidence:
- "<VERBATIM QUOTE>" (<PUBLISHER>, published <DATE>, accessed <DATE>, <URL>)
- "<VERBATIM QUOTE>" (<SECOND INDEPENDENT SOURCE>)
Counter-evidence or caveats: <QUOTE-OR-NONE>
Verdict: <VERDICT>. Proposed replacement:
> <CORRECTION TEXT>

### Needs your judgment (conflicting / abstained)
#### c-12 ...both sources quoted, no correction proposed...

### Verified accurate
c-01, c-03, c-05 (one line each: claim, top source)

### Unverifiable / insufficient evidence
c-09: <CLAIM> (<REASON>)
</report_template>

All values above are illustrative placeholders; never copy concrete names,
numbers, or URLs from this template into a real report.

## Tiered approval

Tier by stakes times confidence; ask per tier, never one blanket yes.

| Tier | Contents | Interaction |
| --- | --- | --- |
| batch | high-confidence corrections in low-stakes prose | One list, approve/reject as a set; user may exclude items |
| item | medium-confidence, or spans in high-stakes content (published docs, legal, safety, pricing) | One question per correction, counter-evidence shown |
| never-auto | conflicting, low-confidence, abstained | Presented for information; edited only if the user dictates the text |

Rules:

- Phrase the ask neutrally ("apply, skip, or edit?"), never presume yes.
- Rejection is recorded (`user-rejected` in the state file) and respected in
  any re-run: do not re-propose a rejected correction unchanged.
- Partial approval is normal; apply exactly the approved subset.
- After edits, run the coherence pass (Workflow step 5) and list any
  secondary edits in the final summary.
