# Outline and section guide

The outline (stage 3), then section structure and drafting rules per format.
Venue policy comes from `venue-standards`.

## Outline

The winning framing fills the template below. Start writing before the idea
is fully formed: writing exposes what is not yet understood. Per subsection,
write at most two lines stating its purpose; per paragraph, one sentence
stating its topic. If the sentence does not fit, split the paragraph.

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
  <item>The scenario sketch from the design plan survives in the introduction in concrete form; a reader from the field recognizes the setting in the first two paragraphs.</item>
  <item>The key insight reads as one sentence in the introduction; a cold reader can repeat it back.</item>
  <item>Every contribution bullet maps to an exhibit in Section 4.</item>
  <item>Every exhibit maps to a live ledger claim, or to a planned experiment with failure criteria.</item>
  <item>(Measurement papers) The key graphs are chosen before drafting; each graph answers a stated question.</item>
  <item>The page budget fits the venue limit.</item>
</checklist>

## Full-length papers

Canonical flow: abstract, introduction, related work, method, experiments
(setup, main results, ablations), limitations, conclusion, venue statements,
references, checklist, appendix. Budgets: abstract 150-250 words, one
paragraph; introduction 1-1.5 pages; related work 0.75-1 page; experiments
the largest block. Adjust to the venue page limit first.

### Abstract

One paragraph: problem, why it matters, what you did, the key result with a
number, the implication. Cite nothing, define every acronym, keep every
claim traceable to the main body. Name the single insight in one sentence: a
busy reviewer must repeat it back after one read. Signal the paper type
(theory, measurement, design, deployment, position) so it reaches confident
reviewers. Draft it after the story freezes; writing it first can focus a
draft, and either way it must state the idea crisply. Leave out cliches,
equations, and general motivation.

### Introduction

Follow the arc: problem, limits of current practice, the key insight in one
sentence, what you do, contributions mapped to evidence, headline results.
Before describing the solution, give the reader the reason to care: hook
non-experts in the opening, impress experts in the body.

- Paragraphs 1-2: the problem and why current approaches are unsatisfactory,
  with citations to retrieved literature.
- Lead with a sharp contradiction, objective mismatch, deployment gap, or
  unexplained observation, concrete enough that a skeptic could disagree
  with it.
- The insight sentence: one sentence stating the single new idea, passing
  the abstract's repeat-back test. If the idea cannot be stated in one
  sentence, the positioning is not ready.
- Paragraph 3: what you do, concretely (method in 3-5 sentences).
- Paragraph 4: results, with the headline numbers.
- Contributions: 3-5 falsifiable bullets, each checkable against the
  experiments section. Common failure: bullets no experiment addresses.

### Related work

Organize by approach or problem facet, not by paper. Per thread: what it
does, what it cannot do that motivates this work, with citations. End with
an explicit novelty paragraph naming what differs and the closest prior art.
Write it so the closest competitor recognizes itself.

### Method

Enough for an expert reader to reproduce the results. Define notation once
and use it consistently. Separate the core idea (what is new) from standard
machinery (cite, do not re-derive). State assumptions explicitly; every
theorem carries its assumptions adjacent. Give pseudocode for algorithms an
implementer would otherwise guess at.

### Experiments

- Setup: datasets, splits, baselines (why these, tuned under comparable
  compute), metrics, seeds, hardware, total compute. Say what tuning was
  done; a suspected-untuned baseline is a rejection trigger.
- Main results: one table or figure per intro claim. Report variance (seeds,
  error bars). Bold best numbers only if the text explains them.
- Ablations: design each to kill a specific rival explanation: oracle
  baselines, mechanism transplants, zeroed key terms, teacher-forced
  baselines. List the three objections a hostile reviewer will raise; each
  must map to an experiment already run. Run the ablation or narrow the
  claim; "left for future work" reads as incomplete.
- Analysis: the paragraph that turns numbers into insight. Say what the
  results teach, not only what they score. Report honest losses alongside
  wins.

### Limitations

Name where the method fails, what the experiments do not cover, threats to
validity, compute or data constraints, negative societal impacts where
applicable. Make each limitation specific enough to preempt the reviewer's
harsher version.

### Conclusion

Two paragraphs: what was shown (restrained, scoped to the evidence) and what
it opens up. Add no new claims and no new numbers; your own results need no
citations. Future work is earned by the contribution: propose only
directions the reader now cares about.

### Venue statements

Placement only; what is required comes from the CFP (`venue-standards`).
ICML impact statement: unnumbered, before references. ICLR: LLM-use
disclosure; ethics and reproducibility statements (not page-counted).
NeurIPS: paper checklist with 1-2 sentence justifications.

### Appendix

Proofs, extended experiments, implementation details. Nothing load-bearing:
if removing the appendix breaks an intro claim, move the evidence into the
main body.

## Short: 6-page idea papers (HotNets / HotOS / HotStorage style)

Budget: 6 pages total including references. One idea, one memorable
sentence, one piece of evidence.

- Abstract (half column): problem, insight, evidence, ask.
- Introduction / Problem (1-1.5 pages): why this problem, why now. End with
  the insight stated as crisply as possible.
- The idea (1.5-2 pages): core mechanism or design, just enough to be
  concrete. A sketch plus the key non-obvious decision; no full system
  architecture.
- Evidence (1-1.5 pages): exactly one convincing artifact (measurement,
  prototype, trace analysis, quantitative argument). Preliminary is fine;
  hand-waving is not.
- Open questions (0.5 page): real research asks, falsifiable or buildable,
  not filler future work.
- Related work (0.5 page): "why nobody did this," closest prior art by name.
- No appendix; nothing is "left to the appendix." If it does not fit in 6
  pages, narrow the idea, not the font.

## Workshop papers (4-6 pages)

Problem and why now; tight related work; the preliminary idea or early
results; what is missing and the plan; a prototype sketch or small
measurement instead of a full evaluation. Archival-status implications go in
the cover note, not the paper.

## Journal papers

A full paper plus: expanded related work; the proofs or system details the
conference version cut; extended evaluation; a statement of what is new
relative to any prior conference version, placed where reviewers check first
(end of introduction). Write for re-reading reviewers: numbered claims and a
stable section map the revision letter can point at.

## Survey papers

No novel experiments required. Scope and methodology (search strategy,
inclusion criteria, corpus size and dates); a taxonomy organizing the field;
comparison tables across its dimensions; per-approach summaries with
strengths and limits; open problems ranked by importance; future directions.
Cite every factual claim. The contribution is the organization and the gaps
it reveals; say so in the introduction.

## Demo papers (2-4 pages)

What the attendee sees and does, step by step; a system architecture sketch;
the novel capability shown; logistics (requirements, setup, fallback if the
live system fails). A video figure is often decisive; check the CFP.
