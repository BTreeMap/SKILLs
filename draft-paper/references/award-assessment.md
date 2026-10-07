# Award assessment

Fill this in during `design` (pipeline stage 1) and revisit it in the
best-paper lens (stage 7). It is a diagnostic: it surfaces blocking
weaknesses, the strongest differentiators, and evidence gaps. It carries no
total, no kill threshold, and no award-probability estimate; direct causal
evidence on what wins awards is too sparse to support any of them (evidence
section 6). Never quote an award probability.

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
differentiators visible on the first page; one real layer of the venue's
currency suffices, per evidence section 4.

## Best-paper lens (stage 7)

After the review loop, revisit the assessment against the draft:

<checklist for="best-paper-lens">
  <item>The contradiction is sharp (section 1).</item>
  <item>Experiments kill rival explanations (sections 2 and 3).</item>
  <item>The evaluation is layered in the venue's currency (section 4).</item>
  <item>Losses are reported (section 5).</item>
  <item>Threshold dimensions hold.</item>
  <item>The lead differentiators frame the paper.</item>
</checklist>

## Evidence: what best-paper winners have in common

Empirical patterns from award winners, for use as a drafting checklist, not
a formula. Evidence base: six award papers read end to end (two each from
NeurIPS 2025, ICML 2025, and NSDI 2026) and the award literature in section
6. Each finding carries its evidence strength. Six papers cannot prove what
committees reward; they show what winning papers look like. Figures quoted
from the six come from the papers themselves; the NSDI pair are Wei et al.
2026 (HyperEdge, usenix.org/system/files/nsdi26-wei.pdf) and Zhang et al.
2026 (OSCAR, USENIX NSDI 2026).

### 1. The idea starts from a sharp contradiction, not a topic [STRONG]

Every one of the six opens from a precise tension: gated attention (gains
persist after collapsing a sparse mixture to one expert, contradicting the
value of dynamic routing); diffusion memorization (optimizing the empirical
score should memorize, yet models generalize); CollabLLM (next-turn reward
vs conversation-level success); masked diffusion (the loss as an average
over permutation-learners forces the ordering question); OSCAR (an empty
cell in the congestion-control taxonomy table); HyperEdge (rising CDN bills
vs vast idle edge capacity).

Drafting rule: open with a tension a skeptic could disagree with. A topic
statement ("we study X") is not a tension; if the idea cannot be stated as
one, the positioning is not ready. Discovery narratives may be
reconstructed; organize the argument around the tension.

### 2. One compact thesis; experiments as discriminating tests [STRONG]

Each paper states one mechanistic claim early, then runs experiments that
could falsify it: OSCAR's "delay and its gradient carry precision comparable
to in-network telemetry," tested against an oracle controller; gated
attention's "gains come from non-linear gating, not dynamic routing," tested
by parameter-matched dense controls; "reference-state selection, not the
estimator, causes fluctuation," tested by transplanting the mechanism onto
HPCC.

Drafting rule: write the thesis as one sentence before planning experiments.
For each planned experiment, write which rival explanation it kills. An
experiment that only adds a benchmark row is filler.

### 3. Ablations that kill alternative explanations [STRONG]

The strongest ablations are skeptic-killers, not component drops: oracle
baselines isolating one variable; mechanism transplants onto a competitor;
reward ablations with the key term zeroed; teacher-forced baselines that
give the competitor the correct structure, then still beating it.

Drafting rule: list the three objections a hostile reviewer will raise. Each
must map to an experiment already run. "Left for future work" reads as
incomplete at full-length venues.

### 4. Layered evaluation [STRONG]

All six layer: controlled isolation, then scale or stress, then
generalization, then some form of realism. The currency differs by venue:

- ML: ablations, scaling analyses, synthetic formal models paired with real
  experiments, generalization across datasets, human studies where the claim
  is about interaction quality.
- Systems: analytical principles, testbed measurements, microbenchmarks,
  large-scale simulation, explicit limitation sections.
- Deployment-led papers may substitute production evidence for controlled
  novelty: HyperEdge reports over six years of operation, 100,000 edge
  devices, about ten million participants per A/B arm, and a 35% overall
  cost reduction against serving the same peak traffic from the CDN alone.
  The economics is load-bearing, placed before the evaluation.

Drafting rule: pick the currency your venue trusts and spend it in layers.
One layer is a workshop paper; four is a best-paper-shaped evaluation. In
short mode, one compelling layer is enough, but it must be real
(measurement, prototype, trace analysis) with a concrete artifact behind
every claim.

### 5. Honest loss reporting [MODERATE]

Winners report where they lose: HyperEdge's CDN baseline has a 2.89% higher
median transmission speed; OSCAR's average flow completion time for small
flows is 7.6% longer than HPCC's; CollabLLM's user-study quotes calling the
model "bland"; the masked-diffusion paper conceding task diversity
complicates its theory. Honest limitation discussion is explicitly rewarded
and buys credibility for the headline claims.

Drafting rule: name weaknesses plainly and specifically. A disclosed
weakness reads as honesty; a discovered one as concealment.

### 6. What the award literature says [evidence review]

Direct causal evidence on what wins best paper is sparse: no study found
regresses awards on paper-intrinsic features with controls, studies winner
seniority or affiliation at modern CS conferences, or quantifies committee
deliberation dynamics. What exists:

- Citation correlation, not causation [MODERATE]. Across 12 CS conferences,
  a best paper receives more citations than a non-best paper from the same
  conference and year with probability 0.72 (Scopus) and 0.78 (Google
  Scholar); 51% of best papers are in their conference-year's top 10% most
  cited and 64% in the top 20%, with no significant change across years
  (Wainer, Eckmann and Rocha 2015, PLoS ONE,
  doi:10.1371/journal.pone.0118446). At CHI, papers the best-paper committee
  recognized were not cited more often than a random sample of same-year
  papers (Bartneck and Hu 2009, CHI, doi:10.1145/1518701.1518810); the
  disagreement is unresolved. Citations cannot be drafted toward, so this is
  context, not a lever.
- Official criteria converge [STRONG as stated preference]. NeurIPS 2020:
  work that endures, new deep insights, creative and unexpected, changes how
  people think, rigorous and elegant, reproducible. CHI 2020: explicitly no
  formal criteria, a holistic judgment capping best papers at the top 1% of
  submissions (chi2020.acm.org/for-attendees/awards/). ACL: the most
  explicit rubric (fascinating, surprising, field-changing). SOSP:
  significant problem, interesting implementation, demonstrated
  practicality. What committees say they reward: problem importance and
  taste, novelty and surprise, rigor and completeness, clarity and elegance,
  prospective lasting impact.
- Venue families differ [MODERATE]. ML rewards insight, creativity, and
  elegance with enduring potential. Systems and networking reward
  significant problems attacked with real implementations or unusually
  strong designs, evidence from use, practicality, and explored alternatives
  (Levin and Redell 1983: effort is not novelty). HCI rewards novelty,
  impact, methodology, and transparency, with no universal formal rubric.
- Selection is noisy [STRONG]. In the NeurIPS 2021 consistency experiment,
  two independent committees disagreed on accept or reject for 23% of
  duplicated papers, and about half the accepted list would change if review
  were rerun (Beygelzimer et al. 2023, arXiv:2306.03262). In the 2014
  NeurIPS experiment, 50% of the variation in reviewer quality scores was
  subjective, and among accepted papers quality scores did not correlate
  with later citations (Cortes and Lawrence 2021, arXiv:2109.09774).
  Prestige effects exist at review: at WSDM 2017, single-blind reviewers
  recommended acceptance more often, with odds multipliers of 1.63 for
  famous authors, 1.58 for top universities, and 2.10 for top companies
  (Tomkins, Zhang and Heavlin 2017, PNAS, doi:10.1073/pnas.1707323114).
- Null predictors [MODERATE]. Being the most-cited paper, reviewer scores
  among accepted papers, implementation effort alone, high scores alone, and
  incremental "2% better" results without a consequential insight do not
  predict awards.

The three-path framing (novel idea / industry-felt problem / solid
evaluation) is not supported as distinct award archetypes; assess with the
dimensions above instead. Drafting rule: lead the framing with the
differentiating dimensions in the venue's currency.

### 7. No pattern found [ESTABLISHED as absent]

Related-work placement varies freely across winners. Prescribe the function,
not the position: the closest competitor must recognize itself.

### Limits

- Survivorship: winners only; the same traits may appear in rejected papers.
  The checklist raises the ceiling without guaranteeing acceptance.
- Committees reward other things too (timeliness, taste, community service).
  These patterns cover craft, not politics.
- Revisit after each new batch of readings; cut patterns that fail to
  replicate.
