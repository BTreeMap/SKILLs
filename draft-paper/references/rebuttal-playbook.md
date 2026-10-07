# Rebuttal playbook

Post-submission response: rebuttals, revise-and-resubmit, and the
camera-ready tail.

Evidence base: one quantitative study of over 74,000 ICLR 2024 and 2025
reviews with before- and after-rebuttal scores (Kargaran et al. 2025,
"Insights from the ICLR Peer Review and Rebuttal Process",
arXiv:2511.15462), plus practitioner guides. The quantitative findings are
correlational and ICLR-only; transfer to NeurIPS or ICML is plausible
extrapolation. Moves marked [established] recurred across sources;
[plausible] appeared in one source or a few.

## Input

The user supplies the reviews as text: per reviewer, the quoted concerns and
the score, in any readable layout, one block per reviewer:

<template for="review-input">
- Reviewer <id> (score <n>): <quoted concerns>
</template>

## Triage

1. List every reviewer concern as a quoted one-liner with reviewer and
   score, and `jot` each as a `concern` entry; the mapping below is filled
   from `recall --kind concern`.
2. Classify each concern and respond by its class:

   | Class | Response |
   | --- | --- |
   | Misunderstanding | The paper already answers it. Point to the exact section or figure and add a clarifying sentence. Two reviewers misreading the same thing is a prose failure; fix the text. |
   | Missing evidence | Run it if it fits the window and report the numbers, whatever they show. A partial honest result beats a promised one. |
   | Scope or taste disagreement | State the paper's scope, name what it does not claim, let the contribution stand. |
   | Reviewer factual error | Correct it first with an exact pointer (section, table, line, quoted number), then move on. Practitioner consensus calls this the highest-yield rebuttal content. |

3. Allocate depth by decision leverage. Score movement concentrates at the
   borderline (5 to 6, then 6 to 8, are the most frequent changes in the
   ICLR study): the borderline reviewer gets the deepest response. The
   champion still gets a short, complete reply; ACs read the whole record
   and a neglected champion can drift. [established]
4. Expect silent reviewers. No reply does not mean the rebuttal was ignored;
   the AC reads the full record, so the AC-facing summary is the deliverable
   of last resort. [established]

## Drafting the response

Shape:

- Open with thanks, then 3-5 bullets of what is new, not a summary of the
  paper.
- Per reviewer: quote or precisely restate the concern, respond, name the
  concrete change. One thread per reviewer.
- Close with the AC-facing summary (mapping section below).

Moves that move scores:

- Run the requested experiment and name the new artifact ("new Figure R1",
  "Table 4 rows 3-5"). Evidence-backed clarification is the single
  best-supported move [established].
- Answer every concern and engage its technical substance, even one you
  believe is wrong. Unanswered points are the empirical signature of
  failure, and evasion is the one documented way to move a score down:
  brushing off a technical concern moved a score down in a documented case.
  For low-leverage concerns, answer briefly and say why the point would not
  change the assessment [established].
- Take a clear agree/disagree stance per point, with the evidence doing the
  work around it [plausible].
- Replace vague wording with quoted numbers when challenged. Concede the
  specific phrase, give exact figures, explain the scale choice in one
  sentence, change the text [plausible].
- Acknowledge co-reviewer alignment where points agree [plausible].

Rules:

- Promise only experiments you will run. Concede specific wording or numbers
  rather than broad claims.
- Stay double-blind: anonymized links, no identifying phrasing.
- Tone: neutral, specific, short. Address the concern, not the reviewer.
- Respect the venue's page or word limit; check the current year's
  instructions.

## Discussion window

- Submit mid-window, leaving room for discussion [plausible].
- Stay in multi-turn discussion. Reply to follow-ups. In the ICLR 2025
  data, reviews whose score rose averaged 2.21 conversation turns with
  95.7% author participation, against 1.47 turns and 65.9% for reviews
  whose score held [established].
- Confirm score updates when a reviewer agrees in text to raise; agreed
  updates sometimes never land on the official score [plausible].

## Response-to-reviewer mapping and AC summary

One row per concern; the class is its triage class.

<template for="mapping">
| Reviewer | Concern (quoted one-liner) | Class | Response location | Change made |
|----------|----------------------------|-------|-------------------|-------------|
| | | | | |
</template>

Close the rebuttal with the AC-facing summary: per reviewer, the score
trajectory and what changed, with every accepted point mapped to its
revision location.

## Revise-and-resubmit and journal revision

Some venues decide on a revised manuscript, not a rebuttal text. The
deliverable is a tracked-changes revision plus a response letter.

- Response letter: per reviewer, quote the concern, state the change, point
  to its exact location in the revision. Same depth-by-leverage triage.
- Make every promised change in the manuscript; reviewers re-read it.
  Conditional acceptances are revoked when the revision does not deliver
  what the letter promised.
- One-shot revisions (accept-or-reject): submit the marked manuscript plus a
  change list; do the mandated changes first, then the feasible remainder.
- Journal major revisions may add new reviewers; restate the contribution
  briefly at the top of the letter to orient a new reader.

## Camera-ready tail

After acceptance: de-anonymize (authors, acknowledgments, funding), restore
identity-stripped citations, add artifact and code links, re-check page
limits against the current CFP (`venue-standards`), re-run citation
verification on added references. The reproducibility bundle ships with the
camera-ready.
