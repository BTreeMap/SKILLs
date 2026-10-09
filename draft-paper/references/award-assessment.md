# Award assessment

Fill in during `design` (pipeline stage 1); revisit in best-paper lens
(stage 7). Carries no total, no kill threshold, no award-probability
estimate; direct causal evidence on what wins awards is too sparse to
support any of them (evidence section 6). Never quote award probability.

## Threshold dimensions: must hold before anything else

Failure here blocks submission readiness, independent of award merit. Fix
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

Rank project's strongest two; they lead title, abstract, introduction.
Ground each in retrieved literature or artifacts, not adjectives.

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

Name venue family; check project spends its currency: systems and networking
(real implementation, evidence from use, practicality, alternatives
explored); ML (insight, creativity, ablations, scaling, generalization); HCI
(contribution type's norms: empirical, artifact, methodological,
theoretical, dataset, survey, opinion). Record mismatches as evidence gaps,
not failures.

## External variance: recorded, not scored

Timing, topic fashion, committee composition, selection noise. Note what is
favorable or unfavorable. Leave unscored and out of drafting decisions; no
revision controls it.

## Decision

<template for="decision">
<![CDATA[
- Blocking weaknesses: threshold failures to fix before submission.
- Lead differentiators: the one or two dimensions the framing leads with, and where their evidence lives.
- Evidence gaps: what would strengthen the differentiators, each with failure criteria for the proposed experiment.
- Structural implication: which sections carry the differentiators; what gets cut or moved so they lead.
]]>
</template>

Paper with no clear differentiator can still be publishable; do not frame or
venue-target it as award-seeking. Short papers: make differentiators visible
on first page; one real layer of venue's currency suffices, per evidence
section 4.

## Best-paper lens (stage 7)

After review loop, revisit assessment against draft:

<checklist for="best-paper-lens">
  <item>Contradiction is sharp (section 1).</item>
  <item>Experiments kill rival explanations (sections 2 and 3).</item>
  <item>Evaluation layered in venue's currency (section 4).</item>
  <item>Losses reported (section 5).</item>
  <item>Threshold dimensions hold.</item>
  <item>Lead differentiators frame paper.</item>
</checklist>

## Evidence: what best-paper winners have in common

Empirical patterns from award winners, for use as drafting checklist, not
formula. Evidence base: six award papers read end to end (two each from
NeurIPS 2025, ICML 2025, NSDI 2026) and award literature in section 6. Each
finding carries its evidence strength. Six papers cannot prove what
committees reward; they show what winning papers look like. Figures quoted
from the six come from the papers themselves; NSDI pair are Wei et al. 2026
(HyperEdge, usenix.org/system/files/nsdi26-wei.pdf) and Zhang et al. 2026
(OSCAR, USENIX NSDI 2026).

### 1. The idea starts from a sharp contradiction, not a topic [STRONG]

Every one of the six opens from precise tension: gated attention (gains
persist after collapsing sparse mixture to one expert, contradicting value
of dynamic routing); diffusion memorization (optimizing empirical score
should memorize, yet models generalize); CollabLLM (next-turn reward vs
conversation-level success); masked diffusion (loss as average over
permutation-learners forces ordering question); OSCAR (empty cell in
congestion-control taxonomy table); HyperEdge (rising CDN bills vs vast idle
edge capacity).

Drafting rule: open with tension a skeptic could disagree with. Topic
statement ("we study X") is not tension; idea cannot be stated as one:
positioning not ready. Discovery narratives may be reconstructed; organize
argument around tension.

### 2. One compact thesis; experiments as discriminating tests [STRONG]

Each paper states one mechanistic claim early, then runs experiments that
could falsify it: OSCAR's "delay and its gradient carry precision comparable
to in-network telemetry," tested against oracle controller; gated
attention's "gains come from non-linear gating, not dynamic routing," tested
by parameter-matched dense controls; "reference-state selection, not the
estimator, causes fluctuation," tested by transplanting mechanism onto HPCC.

Drafting rule: write thesis as one sentence before planning experiments. For
each planned experiment, write which rival explanation it kills. Experiment
only adding benchmark row is filler.

### 3. Ablations that kill alternative explanations [STRONG]

Strongest ablations are skeptic-killers, not component drops: oracle
baselines isolating one variable; mechanism transplants onto competitor;
reward ablations with key term zeroed; teacher-forced baselines giving
competitor correct structure, then still beating it.

Drafting rule: list three objections hostile reviewer will raise. Each must
map to experiment already run. "Left for future work" reads as incomplete at
full-length venues.

### 4. Layered evaluation [STRONG]

All six layer: controlled isolation, then scale or stress, then
generalization, then some form of realism. Currency differs by venue:

- ML: ablations, scaling analyses, synthetic formal models paired with real
  experiments, generalization across datasets, human studies where claim is
  about interaction quality.
- Systems: analytical principles, testbed measurements, microbenchmarks,
  large-scale simulation, explicit limitation sections.
- Deployment-led papers may substitute production evidence for controlled
  novelty: HyperEdge reports over six years of operation, 100,000 edge
  devices, about ten million participants per A/B arm, 35% overall cost
  reduction against serving same peak traffic from CDN alone. Economics is
  load-bearing, placed before evaluation.

Drafting rule: pick currency your venue trusts, spend it in layers. One
layer is workshop paper; four is best-paper-shaped evaluation. Short mode:
one compelling layer enough, but must be real (measurement, prototype, trace
analysis) with concrete artifact behind every claim.

### 5. Honest loss reporting [MODERATE]

Winners report where they lose: HyperEdge's CDN baseline has 2.89% higher
median transmission speed; OSCAR's average flow completion time for small
flows is 7.6% longer than HPCC's; CollabLLM's user-study quotes calling
model "bland"; masked-diffusion paper conceding task diversity complicates
its theory. Honest limitation discussion explicitly rewarded, buys
credibility for headline claims.

Drafting rule: name weaknesses plainly and specifically.

### 6. What the award literature says [evidence review]

Direct causal evidence on what wins best paper is sparse: no study found
regresses awards on paper-intrinsic features with controls, studies winner
seniority or affiliation at modern CS conferences, or quantifies committee
deliberation dynamics. What exists:

- Citation correlation, not causation [MODERATE]. Across 12 CS conferences,
  best paper receives more citations than non-best paper from same
  conference and year with probability 0.72 (Scopus) and 0.78 (Google
  Scholar); 51% of best papers are in their conference-year's top 10% most
  cited and 64% in top 20%, with no significant change across years (Wainer,
  Eckmann and Rocha 2015, PLoS ONE, doi:10.1371/journal.pone.0118446). At
  CHI, papers best-paper committee recognized were not cited more often than
  random sample of same-year papers (Bartneck and Hu 2009, CHI,
  doi:10.1145/1518701.1518810); disagreement unresolved. Citations cannot be
  drafted toward: context, not lever.
- Official criteria converge [STRONG as stated preference]. NeurIPS 2020:
  work that endures, new deep insights, creative and unexpected, changes how
  people think, rigorous and elegant, reproducible. CHI 2020: explicitly no
  formal criteria, holistic judgment capping best papers at top 1% of
  submissions (chi2020.acm.org/for-attendees/awards/). ACL: most explicit
  rubric (fascinating, surprising, field-changing). SOSP: significant
  problem, interesting implementation, demonstrated practicality. What
  committees say they reward: problem importance and taste, novelty and
  surprise, rigor and completeness, clarity and elegance, prospective
  lasting impact.
- Venue families differ [MODERATE]. ML rewards insight, creativity, elegance
  with enduring potential. Systems and networking reward significant
  problems attacked with real implementations or unusually strong designs,
  evidence from use, practicality, explored alternatives (Levin and Redell
  1983: effort is not novelty). HCI rewards novelty, impact, methodology,
  transparency, with no universal formal rubric.
- Selection is noisy [STRONG]. In NeurIPS 2021 consistency experiment, two
  independent committees disagreed on accept or reject for 23% of duplicated
  papers; about half the accepted list would change if review were rerun
  (Beygelzimer et al. 2023, arXiv:2306.03262). In 2014 NeurIPS experiment,
  50% of variation in reviewer quality scores was subjective; among accepted
  papers quality scores did not correlate with later citations (Cortes and
  Lawrence 2021, arXiv:2109.09774). Prestige effects exist at review: at
  WSDM 2017, single-blind reviewers recommended acceptance more often, with
  odds multipliers of 1.63 for famous authors, 1.58 for top universities,
  2.10 for top companies (Tomkins, Zhang and Heavlin 2017, PNAS,
  doi:10.1073/pnas.1707323114).
- Null predictors [MODERATE]. Being most-cited paper, reviewer scores among
  accepted papers, implementation effort alone, high scores alone,
  incremental "2% better" results without consequential insight do not
  predict awards.

Three-path framing (novel idea / industry-felt problem / solid evaluation)
not supported as distinct award archetypes; assess with dimensions above
instead. Drafting rule: lead framing with differentiating dimensions in
venue's currency.

### 7. No pattern found [ESTABLISHED as absent]

Related-work placement varies freely across winners. Prescribe function, not
position: closest competitor must recognize itself.

### Limits

- Survivorship: winners only; same traits may appear in rejected papers.
  Checklist raises ceiling without guaranteeing acceptance.
- Committees reward other things too (timeliness, taste, community service).
- Revisit after each new batch of readings; cut patterns that fail to
  replicate.
