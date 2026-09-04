# Answer: Sweep, Outline, Sections, and Markers

## The rival sweep

After gathering, sweep once for the strongest contrary account: folk belief,
older explanation, or competing mechanism. Record scope, candidates, and
survivors as a `sweeps` entry. An empty scoped sweep establishes absence;
survivors and `refuted` premises feed Rival.

## Check first

Draft from script output:

<commands for="answer">
env -u VIRTUAL_ENV uv run --project "$(realpath <skill-root>/scripts)" btm-ponder check <session>
</commands>

The check returns the marker table first (`S1` onward, with class, title,
url), then the derived sections, a scaffold holding each close's stored
premise and detail keyed by marker, violations, and hedge advisories.
Resolve violations; then the lead drafts once by transforming the
scaffold's rows.

## Sections

Render the derived sections and add Boundary when the answer flips within
scope. An absent Rival records an empty sweep.

| Section | Carries |
| --- | --- |
| Answer | The claim, first, in the question's own register |
| Chain | The reasoning path when it exceeds a few links; else it collapses into the answer's sentences |
| Rival | Every `refuted` premise and every sweep survivor, stated at its strongest |
| Boundary | Where the answer flips within scope (band, version, workload) |
| Open | Each `unresolved` leaf with what was tried or why it was passed over |
| Sources | The check's table: marker, class, title, url |

Omit `Retired` leaves.

## Marker discipline

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
