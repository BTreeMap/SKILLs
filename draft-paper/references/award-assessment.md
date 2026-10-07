# Award assessment

Fill this in during `design` (pipeline stage 1) and revisit it in the
best-paper lens pass (stage 7). It is a diagnostic: it surfaces blocking
weaknesses, the strongest differentiators, and evidence gaps. It carries no
total, no kill threshold, and no award-probability estimate; direct causal
evidence on what wins awards is too sparse to support any of them
(`award-patterns` 6).

## Threshold dimensions: must hold before anything else

A failure here blocks submission readiness, independent of award merit. Fix
these before polishing anything else.

<template for="threshold-dimensions">
| Dimension | Check | Status and evidence |
|---|---|---|
| Correctness | Claims, proofs, and experimental logic are right. | |
| Evidence credibility | Every load-bearing claim traces to an artifact or a verified citation. | |
| Claim calibration | The scope of each claim matches the scope of its evidence. | |
| Venue compliance | Format, limits, anonymization, and required statements per the CFP. | |
</template>

## Differentiating dimensions: what separates winners

Rank the project's strongest two; they lead the title, abstract, and
introduction. Ground each in retrieved literature or artifacts, not
adjectives.

<template for="differentiating-dimensions">
| Dimension | The project's standing |
|---|---|
| Problem importance and taste | |
| Distinctive insight | |
| Novelty or surprise | |
| Prospective reach (what this changes or opens up) | |
</template>

## Communication dimensions

<template for="communication-dimensions">
| Dimension | Check |
|---|---|
| Central coherence | One thesis organizes the paper; every section serves it. |
| Accessibility | A non-specialist in the area can follow the argument. |
| Elegance | The mechanism or argument is as simple as the claim allows. |
| Completeness | Nothing load-bearing is deferred to future work or an appendix. |
</template>

## Venue-specific evidence currency

Name the venue family and check that the project spends its currency:
systems and networking (real implementation, evidence from use,
practicality, alternatives explored); ML (insight, creativity, ablations,
scaling, generalization); HCI (the contribution type's norms: empirical,
artifact, methodological, theoretical, dataset, survey, opinion). Record
mismatches as evidence gaps, not as failures.

## External variance: recorded, not scored

Timing, topic fashion, committee composition, selection noise. Note what is
favorable or unfavorable. Leave it unscored and out of drafting decisions;
no revision controls it.

## Decision

<template for="decision">
<![CDATA[
- Blocking weaknesses: threshold failures to fix before submission.
- Lead differentiators: the one or two dimensions the framing leads with, and where their evidence lives.
- Evidence gaps: what would strengthen the differentiators, each with failure criteria for the proposed experiment.
- Structural implication: which sections carry the differentiators; what gets cut or moved so they lead.
]]>
</template>

A paper with no clear differentiator can still be publishable; it should not
be framed or venue-targeted as award-seeking. For short papers, make the
differentiators visible on the first page: one compelling layer of the
venue's currency is enough, but it must be real (measurement, prototype,
trace analysis) with a concrete artifact behind every claim.
