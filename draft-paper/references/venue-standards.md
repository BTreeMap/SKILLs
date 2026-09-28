# Venue Standards

Owns one question: *what must be true about the venue before the paper is
outlined?* Holds the verification protocol, the CFP checklist, and
venue-family archetypes (stable structural shapes). Holds no per-venue
numbers: limits, deadlines, and policies drift between cycles, and a stale
number here would silently corrupt every draft. Section structure lives in
`section-guide`; empirical patterns in `award-patterns`; review criteria in
`reviewer-checklist`.

## Verification protocol

Venue facts come from the venue's current official pages, never from memory
and never from examples in this file. Whenever web search is available:

1. Find the current cycle's official call for papers and submission
   instructions (the conference site, not a mirror or a prior year's page).
2. Extract the checklist below into a venue brief: each answer with its
   source URL and the cycle year. File it with the evidence ledger; it is
   part of the paper's provenance.
3. Re-verify at camera-ready time; limits and artifact deadlines move
   between cycles.

When web search is unavailable, say so, fall back to the archetypes below,
and flag every venue fact in the draft as unverified.

## CFP checklist

Answer every question from the official CFP before outlining:

1. **Length.** Page or word cap? What counts (figures, tables, appendices,
   references, acknowledgments)? What happens over the limit?
2. **Anonymization.** Double-blind? What must be stripped (names,
   affiliations, acknowledgments, PDF metadata, links, self-cites)? Does it
   extend to supplements, code links, videos? Any tracks with relaxed
   anonymization?
3. **Template and mechanics.** Which template, which submission system,
   abstract vs paper deadlines, when the author list freezes.
4. **Required statements.** Ethics, human subjects, LLM/AI-use disclosure,
   accessibility, impact, reproducibility checklists. Which are desk-reject
   triggers?
5. **Post-submission model.** Rebuttal (window, word cap, new-data rules),
   revise-and-resubmit, one-shot revision, or journal-style major revision?
   Who reads the response?
6. **Artifacts.** Evaluation offered? When, blinded how, which badges, does
   it affect acceptance?
7. **Archival status** (workshops especially). Does publication preclude
   later conference submission?
8. **Camera-ready.** Allowed page delta, de-anonymization steps, artifact
   links.

## Venue-family archetypes

Stable structural shapes; details change per cycle, shapes rarely do.

- **ML conferences (NeurIPS/ICML/ICLR).** Fixed page cap on the main body;
  references and appendices outside it; double-blind; author rebuttal with a
  strict cap; area-chair structure; reproducibility checklists and impact or
  LLM-use statements. Currency: theory, ablations, scaling, generalization.
- **Networks and systems (SIGCOMM/NSDI/OSDI/SOSP/MobiCom/INFOCOM/CoNEXT).**
  Page-capped bodies; double-blind; rebuttal models vary (none, factual
  corrections only with tight word caps, one-shot revisions); shepherded
  acceptances; optional post-acceptance artifact evaluation with badges.
  Ethics subsections can be mandatory desk-reject triggers. Currency: real
  implementation, testbed measurement, deployment or production evidence,
  simulation. Built-and-measured systems outrank simulation-only claims;
  production evidence is rare and strong.
- **MLSys.** ML-conference-shaped review with systems evidence currency;
  industrial and experience tracks where novelty is not required and company
  identity may stay visible.
- **HCI (CHI/UIST/CSCW).** Word-based limits at CHI, not page-based;
  double-blind extending to supplements, videos, and external links; **no
  classic rebuttal**: two-round or rolling revise-and-resubmit with
  tracked-changes revisions and response letters; LLM-use marking and
  human-subjects ethics notes are desk-reject triggers; accessibility
  requirements apply. Currency depends on the contribution type (empirical,
  artifact, methodological, theoretical, dataset, survey, opinion); name the
  type and meet its norms.
- **Workshops.** Shorter, preliminary work welcome, lighter review, often no
  rebuttal. Confirm archival status before submitting work intended for a
  later conference.
- **Journals.** No hard cap but length must match contribution; major/minor
  revision rounds re-read by the same reviewers; extended conference
  versions need substantial new content (check the journal's threshold);
  blinding varies by journal.
- **Demo and poster tracks.** A few pages describing a live artifact; judged
  on interest and feasibility; a video figure is often decisive.
