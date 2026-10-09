# Adversarial review checklist

Review draft as hostile reviewer would, in at most two rounds.

1. Round one: run five passes below separately, `jot` each finding as
   `punch` entry, then revise draft against punch list.
2. Round one found nothing: stop. Otherwise round two: five passes again on
   revised draft.
3. Stop after round two: fix what it found; list every finding left unfixed
   at `draft` gate for human to decide. Run no third round.

## Pass 1: Novelty and related work

- [ ] Closest prior art named and cited, or only gestured at? Would its
  authors recognize their work in description?
- [ ] Novelty argument built from retrieved full-text literature, not
  keyword overlap? (Keyword-match checks have labeled old techniques
  "novel".)
- [ ] Related work ends with explicit statement of what differs?
- [ ] Citations from last 2-3 years present where subfield moves fast?
- [ ] Each "first" or "novel" claim: cited reason no prior work did this, or
  merely unclaimed?

## Pass 2: Correctness

- [ ] Every theorem states its assumptions adjacent to statement?
- [ ] Every empirical claim in abstract and introduction traces to main-body
  figure or table, not appendix?
- [ ] Prose numbers match tables; captions describe what figures show?
- [ ] Baselines are closest competitors, tuned under comparable compute,
  tuning described?
- [ ] Ablations present for each moving part, not deferred to "future work"?
- [ ] Exploratory (post-hoc) analyses labeled as such, not presented as
  confirmatory?

## Pass 3: Clarity and reproducibility

- [ ] Could expert reader reproduce results from method and setup sections
  alone?
- [ ] Datasets, splits, seeds, hyperparameters (ranges plus selection
  method), hardware, total compute all stated?
- [ ] Variance reported (multiple seeds, error bars), not only means?
- [ ] Code/data referenced via anonymized links, figure-generation scripts
  in bundle?
- [ ] Notation defined once, used consistently? Pseudocode where implementer
  would guess?

## Pass 4: Overclaiming audit

- [ ] List every "significant", "best", "SOTA", "substantial", "dramatic".
  Each needs statistical or evidential backing or must be cut.
- [ ] Abstract/intro claims exceed experimental scope?
- [ ] Generality claims supported beyond toy or single-domain result?
- [ ] Negative or null results reported, or only wins?
- [ ] Limitations section names weaknesses hostile reviewer would raise? You
  can think of harsher one: add it.

## Pass 5: Taste

- [ ] Scenario concreteness: actors, scale, workload, present failure,
  quantitative setting named; practitioner would recognize setting as real.
- [ ] Mechanism understanding: prose shows how each mechanism works, with
  worked numerical example beside explanation.
- [ ] Load-bearing details present: feedback model, failure model,
  measurement vs simulation, baseline tuning budgets. Anything omitted names
  its reason.
- [ ] One-sentence insight: introduction names single insight in one
  sentence; unfamiliar technical colleague can state main point and
  contributions without looking at draft.
- [ ] Story arc: problem, limits of current practice, insight, contributions
  mapped to evidence, headline results; each important point appears in
  abstract and introduction, body, conclusion.
- [ ] Readers: at least one expert and one non-expert have read draft; seek
  skeptics, whose objections predict referees'.
- [ ] Topic fashion is no criterion: unfashionable topic with outstanding
  technical work passes; buzzwords without substance fail.

## Citation audit (runs with every pass)

- [ ] Every citation added or moved since stage 5 has row in citation
  report, three checks passed: record exists, its fields belong to it, it
  supports citing sentence.
- [ ] Unverifiable citations are explicit `[CITATION NEEDED]` placeholders,
  never plausible-looking guesses.

## Integrity

LLM review improves prose and structure; does not certify integrity; this
checklist is not integrity gate (invariant 7). In one study, papers
fabricated by research agent reached acceptance rates of up to 82% from LLM
reviewers (Jiang et al. 2026, "BadScientist", ACL 2026,
doi:10.18653/v1/2026.acl-long.1134).
