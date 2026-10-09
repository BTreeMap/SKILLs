# Adversarial review checklist

Review the draft as a hostile reviewer would, in at most two rounds.

1. Round one: run the five passes below separately, `jot` each finding as a
   `punch` entry, then revise the draft against the punch list.
2. If round one found nothing, stop. Otherwise run round two: the five
   passes again on the revised draft.
3. Stop after round two: fix what it found, and list every finding left
   unfixed at the `draft` gate for the human to decide. Run no third round.

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
- [ ] Is variance reported (multiple seeds, error bars), not only means?
- [ ] Is code/data referenced via anonymized links, with figure-generation
  scripts in the bundle?
- [ ] Notation defined once and used consistently? Pseudocode where an
  implementer would guess?

## Pass 4: Overclaiming audit

- [ ] List every "significant", "best", "SOTA", "substantial", "dramatic".
  Each needs statistical or evidential backing or must be cut.
- [ ] Do abstract/intro claims exceed the experimental scope?
- [ ] Are generality claims supported beyond a toy or single-domain result?
- [ ] Are negative or null results reported, or only wins?
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
- [ ] One-sentence insight: the introduction names the single insight in one
  sentence; an unfamiliar technical colleague can state the main point and
  contributions without looking at the draft.
- [ ] Story arc: problem, limits of current practice, insight, contributions
  mapped to evidence, headline results; each important point appears in the
  abstract and introduction, the body, and the conclusion.
- [ ] Readers: at least one expert and one non-expert have read the draft;
  seek skeptics, whose objections predict the referees'.
- [ ] Topic fashion is no criterion: an unfashionable topic with outstanding
  technical work passes; buzzwords without substance fail.

## Citation audit (runs with every pass)

- [ ] Every citation added or moved since stage 5 has a row in the citation
  report, with the three checks passed: the record exists, its fields belong
  to it, and it supports the citing sentence.
- [ ] Unverifiable citations are explicit `[CITATION NEEDED]` placeholders,
  never plausible-looking guesses.

## Integrity

LLM review improves prose and structure; it does not certify integrity, and
this checklist is not the integrity gate (invariant 7). In one study, papers
fabricated by a research agent reached acceptance rates of up to 82% from
LLM reviewers (Jiang et al. 2026, "BadScientist", ACL 2026,
doi:10.18653/v1/2026.acl-long.1134).
