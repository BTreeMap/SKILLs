# Answer: sweep, check, draft

Load once no material question stays open, then run the steps in order.

## 1. Rival sweep

Sweep once for the strongest contrary account: folk belief, older
explanation, or competing mechanism. Record scope, candidates, and survivors
as a `sweeps` entry. An empty scoped sweep establishes absence and is a
valid result.

## 2. Check

<commands for="answer">
$R check "$S"
</commands>

At the default `draft` view, `check` returns the derived `sections`; a
`scaffold` holding each close's stored premise and detail keyed by marker;
`violations`, with lite-demoted ones under `advisories`; `hedges`; and the
`markers` table, `S1` onward, with class, title, and url. It exits 0 even
with violations: read them, and resolve every violation and every `open`
leaf before drafting. In lite mode an open leaf may remain; disclose it in
the Open section.

## 3. Draft once

The lead drafts once by transforming the scaffold's rows; reuse the premise
and detail written into closes. Render the derived sections and add Boundary
when the answer flips within scope.

| Section | Carries |
| --- | --- |
| Answer | The claim, first, in the question's own register, from `retrieved` leaves |
| Chain | The reasoning path through `retrieved` leaves when it exceeds a few links; else it collapses into the answer's sentences |
| Rival | Every `refuted` premise and every sweep survivor, stated at its strongest |
| Boundary | Where the answer flips within scope (band, version, workload) |
| Open | Each `unresolved` leaf with what was tried or why it was passed over |
| Sources | The check's table: marker, class, title, url |

Omit `retired` leaves. An absent Rival records an empty sweep.

Bind markers to the claims the answer depends on; leave connective prose
bare.

- `[Sn]` marks a claim settled by its numbered ledger source.
- `[~]` marks a conclusion composed from leaves.
- Hedge every leaf the check lists under `hedges`, and name the class by
  stating the claim as attributed evidence: "benchmarks report [S4]",
  "practitioner accounts hold [S6]".

<template for="answer">
## Answer
<claim, plainly> [S1]. <derived conclusion> [~].

## Rival
The strongest contrary account: <premise at its strongest> [S3]. It fails
because <evidence> [S1].

## Boundary
Below <threshold> the answer flips: <flipped claim> [S4].

## Open
- <unresolved leaf question>: searched <what was tried>; status unresolved.

## Sources
- S1 (constitutive): <title>, <url>
- S3 (reported): <title>, <url>
</template>
