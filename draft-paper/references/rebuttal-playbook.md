# Rebuttal playbook

Post-submission response: rebuttals, revise-and-resubmit, camera-ready tail.

Evidence base: one quantitative study of over 74,000 ICLR 2024 and 2025
reviews with before- and after-rebuttal scores (Kargaran et al. 2025,
"Insights from the ICLR Peer Review and Rebuttal Process",
arXiv:2511.15462), plus practitioner guides. Quantitative findings
correlational and ICLR-only; transfer to NeurIPS or ICML is plausible
extrapolation. Moves marked [established] recurred across sources;
[plausible] appeared in one source or a few.

## Input

User supplies reviews as text: per reviewer, quoted concerns and score, in
any readable layout, one block per reviewer:

<template for="review-input">
- Reviewer <id> (score <n>): <quoted concerns>
</template>

## Triage

1. List every reviewer concern as quoted one-liner with reviewer and score;
   `jot` each as `concern` entry; mapping below is filled from
   `recall --kind concern`.
2. Classify each concern; respond by its class:

   | Class | Response |
   | --- | --- |
   | Misunderstanding | Paper already answers it. Point to exact section or figure, add clarifying sentence. Two reviewers misreading same thing is prose failure; fix text. |
   | Missing evidence | Run it if it fits window; report numbers, whatever they show. Partial honest result beats promised one. |
   | Scope or taste disagreement | State paper's scope, name what it does not claim, let contribution stand. |
   | Reviewer factual error | Correct it first with exact pointer (section, table, line, quoted number), then move on. Practitioner consensus calls this highest-yield rebuttal content. |

3. Allocate depth by decision leverage. Score movement concentrates at
   borderline (5 to 6, then 6 to 8, most frequent changes in ICLR study):
   borderline reviewer gets deepest response. Champion still gets short,
   complete reply; ACs read whole record and neglected champion can drift.
   [established]
4. Expect silent reviewers. No reply does not mean rebuttal was ignored; AC
   reads full record, so AC-facing summary is deliverable of last resort.
   [established]

## Drafting the response

Shape:

- Open with thanks, then 3-5 bullets of what is new, not summary of paper.
- Per reviewer: quote or precisely restate concern, respond, name concrete
  change. One thread per reviewer.
- Close with AC-facing summary (mapping section below).

Moves that move scores:

- Run requested experiment, name new artifact ("new Figure R1", "Table 4
  rows 3-5"). Evidence-backed clarification is single best-supported move
  [established].
- Answer every concern, engage its technical substance, even one you believe
  wrong. Unanswered points are empirical signature of failure; evasion is
  the one documented way to move score down: brushing off technical concern
  moved score down in documented case. Low-leverage concerns: answer
  briefly, say why point would not change assessment [established].
- Clear agree/disagree stance per point, evidence doing the work around it
  [plausible].
- Replace vague wording with quoted numbers when challenged. Concede
  specific phrase, give exact figures, explain scale choice in one sentence,
  change text [plausible].
- Acknowledge co-reviewer alignment where points agree [plausible].

Rules:

- Promise only experiments you will run. Concede specific wording or
  numbers, not broad claims.
- Stay double-blind: anonymized links, no identifying phrasing.
- Tone: neutral, specific, short. Address concern, not reviewer.
- Respect venue's page or word limit; check current year's instructions.

## Discussion window

- Submit mid-window, leaving room for discussion [plausible].
- Stay in multi-turn discussion. Reply to follow-ups. In ICLR 2025 data,
  reviews whose score rose averaged 2.21 conversation turns with 95.7%
  author participation, against 1.47 turns and 65.9% for reviews whose score
  held [established].
- Confirm score updates when reviewer agrees in text to raise; agreed
  updates sometimes never land on official score [plausible].

## Response-to-reviewer mapping and AC summary

One row per concern; class is its triage class.

<template for="mapping">
| Reviewer | Concern (quoted one-liner) | Class | Response location | Change made |
|----------|----------------------------|-------|-------------------|-------------|
| | | | | |
</template>

Close rebuttal with AC-facing summary: per reviewer, score trajectory and
what changed, every accepted point mapped to its revision location.

## Revise-and-resubmit and journal revision

Some venues decide on revised manuscript, not rebuttal text. Deliverable:
tracked-changes revision plus response letter.

- Response letter: per reviewer, quote concern, state change, point to its
  exact location in revision. Same depth-by-leverage triage.
- Make every promised change in manuscript; reviewers re-read it.
  Conditional acceptances revoked when revision does not deliver what letter
  promised.
- One-shot revisions (accept-or-reject): submit marked manuscript plus
  change list; mandated changes first, then feasible remainder.
- Journal major revisions may add new reviewers; restate contribution
  briefly at top of letter to orient new reader.

## Camera-ready tail

After acceptance: de-anonymize (authors, acknowledgments, funding), restore
identity-stripped citations, add artifact and code links, re-check page
limits against current CFP (`venue-standards`), re-run citation verification
on added references. Reproducibility bundle ships with camera-ready.
