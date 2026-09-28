# Adversarial Review Checklist

Owns review criteria. Run as a hostile reviewer: five separate passes, a
punch list per pass, revise, repeat once.

## Pass 1: Novelty and related work
- [ ] Is the closest prior art named and cited, or only gestured at? Would
  its authors recognize their work in the description?
- [ ] Is the novelty argument built from retrieved full-text literature, not
  keyword overlap? (Keyword-match checks have labeled old techniques
  "novel".)
- [ ] Does related work end with an explicit statement of what differs?
- [ ] Are citations from the last 2-3 years present where the subfield moves
  fast?
- [ ] For each "first" or "novel" claim: is there a cited reason no prior
  work did this, or is it merely unclaimed?

## Pass 2: Correctness
- [ ] Does every theorem state its assumptions adjacent to the statement?
- [ ] Does every empirical claim in the abstract and introduction trace to a
  main-body figure or table, not the appendix?
- [ ] Do prose numbers match the tables; do captions describe what the
  figures show?
- [ ] Are baselines the closest competitors, tuned under comparable compute,
  with tuning described?
- [ ] Are ablations present for each moving part, not deferred to "future
  work"?
- [ ] Are exploratory (post-hoc) analyses labeled as such, not presented as
  confirmatory?

## Pass 3: Clarity and reproducibility
- [ ] Could an expert reader reproduce the results from the method and setup
  sections alone?
- [ ] Are datasets, splits, seeds, hyperparameters (ranges plus selection
  method), hardware, and total compute all stated?
- [ ] Is variance reported (multiple seeds, error bars), not just means?
- [ ] Is code/data referenced via anonymized links, with figure-generation
  scripts in the bundle?
- [ ] Notation defined once and used consistently? Pseudocode where an
  implementer would guess?

## Pass 4: Overclaiming audit
- [ ] List every "significant", "best", "SOTA", "substantial", "dramatic".
  Each needs statistical or evidential backing or must be cut.
- [ ] Do abstract/intro claims exceed the experimental scope?
- [ ] Are generality claims supported beyond a toy or single-domain result?
- [ ] Are negative or null results reported, or only wins? (Cherry-picked
  baselines and concealed gaps are manipulation, not persuasion.)
- [ ] Does the limitations section name the weaknesses a hostile reviewer
  would raise? If you can think of a harsher one, add it.

## Pass 5: Taste

- [ ] Scenario concreteness: actors, scale, workload, present failure, and
  quantitative setting are named; a practitioner would recognize the setting
  as real.
- [ ] Mechanism understanding: the prose shows how each mechanism works,
  with a worked numerical example beside the explanation.
- [ ] Load-bearing details present: feedback model, failure model,
  measurement vs simulation, baseline tuning budgets. Anything omitted names
  its reason.

## Citation audit (runs with every pass)
- [ ] Three checks per citation: the source exists (API-verified); the
  fields belong to that source; the source supports the citing sentence.
  Field-level errors are the most common failure after outright fabrication.
- [ ] Generate every citation from a retrieval API: Semantic Scholar,
  OpenAlex, Crossref, or arXiv. The citation report records which source
  supplied each entry.
- [ ] Unverifiable citations are explicit `[CITATION NEEDED]` placeholders,
  never plausible-looking guesses.

## Integrity reminder
LLM review improves prose and structure. It does not certify integrity: in
one preprint study, LLM reviewers recommended accepting AI-fabricated
manuscripts up to 82% of the time (BadScientist, Jiang et al. 2025, arXiv,
not peer-reviewed). The integrity gate is the human-approved evidence ledger
plus provenance, not this checklist.
