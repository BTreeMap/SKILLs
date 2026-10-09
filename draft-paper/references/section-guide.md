# Outline and section guide

Outline (stage 3), then section structure and drafting rules per format.
Venue policy comes from `venue-standards`.

## Outline

Winning framing fills template below. Start writing before idea is fully
formed: writing exposes what is not yet understood. Per subsection, at most
two lines stating its purpose; per paragraph, one sentence stating its
topic. Sentence does not fit: split paragraph.

<template for="outline">
<![CDATA[
Title: _falsifiable and specific; no unbacked superlatives_

Venue and page budget: _from the venue brief, not memory_

Key insight (one sentence): _the sentence a reviewer repeats back after one read_

One-sentence contribution: _the claim a skeptic would try to refute_

## Abstract (150-250 words, one paragraph)
- Problem:
- Why it matters:
- What was done:
- Headline result (with number):
- Implication:

## 1. Introduction
- Scenario (concrete: actors, scale, workload, present failure):
- Motivation (outsider-acceptable):
- Gap in current approaches (with citations):
- Key insight (one sentence):
- Method in 3-5 sentences:
- Headline numbers:
- Contribution bullets (each checkable against Section 4): 1. 2. 3.

## 2. Related work
- Thread A (approach/facet):
- Thread B:
- Closest prior art (name it explicitly):
- Novelty paragraph (what differs):

## 3. Method
- Core idea (what is new):
- Standard machinery (cite, do not re-derive):
- Assumptions (stated explicitly):
- Notation:
- Pseudocode needed? (yes/no, for what):

## 4. Experiments
- Datasets and splits:
- Baselines (why these; tuning budget each):
- Metrics:
- Seeds, hardware, total compute:
- Table/figure per intro claim:
  - Claim -> exhibit:
- Ablations (one per moving part):
- Analysis paragraph (what the numbers teach):

## 5. Limitations
- Where it fails:
- What the experiments do not cover:
- Threats to validity:
- Negative societal impacts (if applicable):

## 6. Conclusion
- What was shown (scoped to evidence):
- What it opens up:

## Venue statements
- [ ] Only what the CFP requires (checklist / impact / LLM-use / ethics / accessibility)

## Appendix (non-load-bearing only)
- Proofs:
- Extra experiments:
- Implementation details:
]]>
</template>

Before drafting, confirm every item:

<checklist for="pre-draft">
  <item>Scenario sketch from design plan survives in introduction in concrete form; reader from field recognizes setting in first two paragraphs.</item>
  <item>Key insight reads as one sentence in introduction; cold reader can repeat it back.</item>
  <item>Every contribution bullet maps to exhibit in Section 4.</item>
  <item>Every exhibit maps to live ledger claim, or to planned experiment with failure criteria.</item>
  <item>(Measurement papers) Key graphs chosen before drafting; each graph answers stated question.</item>
  <item>Page budget fits venue limit.</item>
</checklist>

## Full-length papers

Canonical flow: abstract, introduction, related work, method, experiments
(setup, main results, ablations), limitations, conclusion, venue statements,
references, checklist, appendix. Budgets: abstract 150-250 words, one
paragraph; introduction 1-1.5 pages; related work 0.75-1 page; experiments
largest block. Adjust to venue page limit first.

### Abstract

One paragraph: problem, why it matters, what you did, key result with
number, implication. Cite nothing, define every acronym, keep every claim
traceable to main body. Name single insight in one sentence: busy reviewer
must repeat it back after one read. Signal paper type (theory, measurement,
design, deployment, position) so it reaches confident reviewers. Draft after
story freezes; writing it first can focus draft; either way it must state
idea crisply. Leave out cliches, equations, general motivation.

### Introduction

Follow arc: problem, limits of current practice, key insight in one
sentence, what you do, contributions mapped to evidence, headline results.
Before describing solution, give reader reason to care: hook non-experts in
opening, impress experts in body.

- Paragraphs 1-2: problem and why current approaches are unsatisfactory,
  with citations to retrieved literature.
- Lead with sharp contradiction, objective mismatch, deployment gap, or
  unexplained observation, concrete enough that skeptic could disagree with
  it.
- Insight sentence: one sentence stating single new idea, passing abstract's
  repeat-back test. Idea cannot be stated in one sentence: positioning not
  ready.
- Paragraph 3: what you do, concretely (method in 3-5 sentences).
- Paragraph 4: results, with headline numbers.
- Contributions: 3-5 falsifiable bullets, each checkable against experiments
  section. Common failure: bullets no experiment addresses.

### Related work

Organize by approach or problem facet, not by paper. Per thread: what it
does, what it cannot do that motivates this work, with citations. End with
explicit novelty paragraph naming what differs and closest prior art. Write
so closest competitor recognizes itself.

### Method

Enough for expert reader to reproduce results. Define notation once, use
consistently. Separate core idea (what is new) from standard machinery
(cite, do not re-derive). State assumptions explicitly; every theorem
carries its assumptions adjacent. Pseudocode for algorithms implementer
would otherwise guess at.

### Experiments

- Setup: datasets, splits, baselines (why these, tuned under comparable
  compute), metrics, seeds, hardware, total compute. Say what tuning was
  done; suspected-untuned baseline is rejection trigger.
- Main results: one table or figure per intro claim. Report variance (seeds,
  error bars). Bold best numbers only if text explains them.
- Ablations: design each to kill specific rival explanation: oracle
  baselines, mechanism transplants, zeroed key terms, teacher-forced
  baselines. List three objections hostile reviewer will raise; each must
  map to experiment already run. Run ablation or narrow claim; "left for
  future work" reads as incomplete.
- Analysis: paragraph turning numbers into insight. Say what results teach,
  not only what they score. Report honest losses alongside wins.

### Limitations

Name where method fails, what experiments do not cover, threats to validity,
compute or data constraints, negative societal impacts where applicable.
Each limitation specific enough to preempt reviewer's harsher version.

### Conclusion

Two paragraphs: what was shown (restrained, scoped to evidence) and what it
opens up. No new claims, no new numbers; own results need no citations.
Future work earned by contribution: propose only directions reader now cares
about.

### Venue statements

Placement only; what is required comes from CFP (`venue-standards`). ICML
impact statement: unnumbered, before references. ICLR: LLM-use disclosure;
ethics and reproducibility statements (not page-counted). NeurIPS: paper
checklist with 1-2 sentence justifications.

### Appendix

Proofs, extended experiments, implementation details. Nothing load-bearing:
if removing appendix breaks intro claim, move evidence into main body.

## Short: 6-page idea papers (HotNets / HotOS / HotStorage style)

Budget: 6 pages total including references. One idea, one memorable
sentence, one piece of evidence.

- Abstract (half column): problem, insight, evidence, ask.
- Introduction / Problem (1-1.5 pages): why this problem, why now. End with
  insight stated as crisply as possible.
- The idea (1.5-2 pages): core mechanism or design, just enough to be
  concrete. Sketch plus key non-obvious decision; no full system
  architecture.
- Evidence (1-1.5 pages): exactly one convincing artifact (measurement,
  prototype, trace analysis, quantitative argument). Preliminary fine;
  hand-waving not.
- Open questions (0.5 page): real research asks, falsifiable or buildable,
  not filler future work.
- Related work (0.5 page): "why nobody did this," closest prior art by name.
- No appendix; nothing "left to the appendix." Does not fit in 6 pages:
  narrow idea, not font.

## Workshop papers (4-6 pages)

Problem and why now; tight related work; preliminary idea or early results;
what is missing and plan; prototype sketch or small measurement instead of
full evaluation. Archival-status implications go in cover note, not paper.

## Journal papers

Full paper plus: expanded related work; proofs or system details conference
version cut; extended evaluation; statement of what is new relative to any
prior conference version, placed where reviewers check first (end of
introduction). Write for re-reading reviewers: numbered claims and stable
section map revision letter can point at.

## Survey papers

No novel experiments required. Scope and methodology (search strategy,
inclusion criteria, corpus size and dates); taxonomy organizing field;
comparison tables across its dimensions; per-approach summaries with
strengths and limits; open problems ranked by importance; future directions.
Cite every factual claim. Contribution is organization and gaps it reveals;
say so in introduction.

## Demo papers (2-4 pages)

What attendee sees and does, step by step; system architecture sketch; novel
capability shown; logistics (requirements, setup, fallback if live system
fails). Video figure often decisive; check CFP.
