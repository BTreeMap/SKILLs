# Paper outline

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
