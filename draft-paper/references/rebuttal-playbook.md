# Rebuttal Playbook

Owns post-submission response: rebuttals, revise-and-resubmit, and the
camera-ready tail.

Evidence base [labeled]: two ICLR-scale quantitative studies (Kargaran et
al. 2025, ~73,000 before/after score records across ICLR 2024-2025; Huang et
al. 2023, 13,000+ reviews from ICLR 2022), two complete OpenReview threads,
published NeurIPS 2020 reviews, practitioner guides. All quantitative
findings are correlational; score statistics are ICLR-only, and transfer to
NeurIPS/ICML is plausible extrapolation. Moves marked [established] recurred
across studies and threads; [plausible] appeared a few times or in one
study.

## Triage

1. List every reviewer concern as a quoted one-liner with reviewer and
   score.
2. Classify each concern:
   - **Misunderstanding**: the paper already answers it. Point to the exact
     section or figure and add a clarifying sentence. Two reviewers
     misreading the same thing is a prose failure; fix the text.
   - **Missing evidence**: run it if it fits the window and report the
     numbers, whatever they show. A partial honest result beats a promised
     one.
   - **Scope or taste disagreement**: state the paper's scope, name what it
     does not claim, let the contribution stand.
   - **Reviewer factual error**: correct it first with an exact pointer
     (section, table, line, quoted number), then move on. Practitioner
     consensus calls this the highest-yield rebuttal content.
3. Allocate depth by decision leverage. Score movement concentrates at the
   borderline (5 to 6, 6 to 8 are the modal moves): the borderline reviewer
   gets the deepest response. The champion still gets a short, complete
   reply; ACs read the whole record and a neglected champion can drift.
   [established]
4. Expect silent reviewers. No reply does not mean the rebuttal was ignored;
   the AC reads the full record, so the AC-facing summary below is the
   deliverable of last resort. [established]

## Moves that move scores

- **Run the requested experiment and name the new artifact** ("new Figure
  R1", "Table 4 rows 3-5"). Evidence-backed clarification is the single
  best-supported move [established].
- **Answer every concern.** Unanswered points are the empirical signature of
  failure: brushing off a technical concern moved a score down in a
  documented case. For low-leverage concerns, answer briefly *and* say why
  the point would not change the assessment [established].
- **Stay in multi-turn discussion.** Reply to follow-ups; discussion depth
  is the strongest behavioral correlate of increases (2.21 vs 1.47 turns;
  95.7% vs 65.9% author participation) [established].
- **Take a clear agree/disagree stance per point**, with the evidence doing
  the work around it [plausible].
- **Replace vague wording with quoted numbers when challenged.** Concede the
  specific phrase, give exact figures, explain the scale choice in one
  sentence, change the text [plausible].
- **Submit mid-window**, leaving room for discussion [plausible].
- **Confirm score updates** when a reviewer agrees in text to raise; agreed
  updates sometimes never land on the official score [plausible].
- **Acknowledge co-reviewer alignment** where points agree [plausible].

## Drafting rules

- Open with thanks, then 3-5 bullets of what is *new*, not a summary of the
  paper.
- Per reviewer: quote or precisely restate the concern, respond, name the
  concrete change. One thread per reviewer.
- Close with an AC-facing summary: a per-reviewer table of score trajectory
  and what changed, mapping each accepted point to its revision location.
- Engage the technical substance of every concern, even ones you believe are
  wrong. Evasion is the one documented way to move a score down.
- Promise only experiments you will run. Concede specific wording or numbers
  rather than broad claims.
- Stay double-blind: anonymized links, no identifying phrasing.
- Tone: neutral, specific, short. Address the concern, not the reviewer.
- Respect the venue's page or word limit; check the current year's
  instructions.

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
