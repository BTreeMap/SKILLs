# Venue standards

Settle what must be true about the venue before the paper is outlined. This
file holds no per-venue numbers: limits, deadlines, and policies drift
between cycles, and a stale number here would silently corrupt every draft.

## Verification protocol

Venue facts come from the venue's current official pages, never from memory
and never from examples in this file.

1. Find the current cycle's official call for papers and submission
   instructions (the conference site, not a mirror or a prior year's page).
   Search and fetch with the harness's own tools; where they are absent, use
   `/search-web` (`web` to find the page, `fetch` to read it). Read a PDF
   call with `/read-pdf`. With no retrieval available, say so, fall back to
   the archetypes below, and flag every venue fact in the draft as
   unverified.
2. Answer every question in the CFP checklist below before outlining, and
   file the answers as the venue brief, each with its source URL and the
   cycle year. The brief is part of the paper's provenance.
3. Re-verify the brief at camera-ready time; limits and artifact deadlines
   move between cycles.

## CFP checklist

1. Length: page or word cap? What counts (figures, tables, appendices,
   references, acknowledgments)? What happens over the limit?
2. Anonymization: double-blind? What must be stripped (names, affiliations,
   acknowledgments, PDF metadata, links, self-cites)? Does it extend to
   supplements, code links, videos? Any tracks with relaxed anonymization?
3. Template and mechanics: which template and version, which submission
   system, abstract vs paper deadlines, when the author list freezes.
4. Required statements: ethics, human subjects, LLM or AI-use disclosure,
   accessibility, impact, reproducibility checklists. Which are desk-reject
   triggers?
5. Post-submission model: rebuttal (window, word cap, new-data rules),
   revise-and-resubmit, one-shot revision, or journal-style major revision?
   Who reads the response?
6. Artifacts: evaluation offered? When, blinded how, which badges, does it
   affect acceptance?
7. Archival status (workshops especially): does publication preclude later
   conference submission?
8. Camera-ready: allowed page delta, de-anonymization steps, artifact links.

File the answers in this brief, one line per checklist question:

<template for="venue-brief">
<![CDATA[
- Venue and track:
- Cycle year:
- 1 Length:
- 2 Anonymization:
- 3 Template and mechanics (template version and where fetched):
- 4 Required statements:
- 5 Post-submission model:
- 6 Artifacts:
- 7 Archival status:
- 8 Camera-ready:

## Sources

- <fact>: <URL> (<cycle year>)
]]>
</template>

## Venue-family archetypes

Stable structural shapes; details change per cycle, shapes rarely do.

- ML conferences (NeurIPS/ICML/ICLR): fixed page cap on the main body;
  references and appendices outside it; double-blind; author rebuttal with a
  strict cap; area-chair structure; reproducibility checklists and impact or
  LLM-use statements. Currency: theory, ablations, scaling, generalization.
- Networks and systems (SIGCOMM/NSDI/OSDI/SOSP/MobiCom/INFOCOM/CoNEXT):
  page-capped bodies; double-blind; rebuttal models vary (none, factual
  corrections only with tight word caps, one-shot revisions); shepherded
  acceptances; optional post-acceptance artifact evaluation with badges.
  Ethics subsections can be mandatory desk-reject triggers. Currency: real
  implementation, testbed measurement, deployment or production evidence,
  simulation. Built-and-measured systems outrank simulation-only claims;
  production evidence is rare and strong.
- MLSys: ML-conference-shaped review with systems evidence currency;
  industrial and experience tracks where novelty is not required and company
  identity may stay visible.
- HCI (CHI/UIST/CSCW): word-based limits at CHI, not page-based;
  double-blind extending to supplements, videos, and external links; no
  classic rebuttal: two-round or rolling revise-and-resubmit with
  tracked-changes revisions and response letters; LLM-use marking and
  human-subjects ethics notes are desk-reject triggers; accessibility
  requirements apply. Currency depends on the contribution type (empirical,
  artifact, methodological, theoretical, dataset, survey, opinion); name the
  type and meet its norms.
- Workshops: shorter, preliminary work welcome, lighter review, often no
  rebuttal. Confirm archival status before submitting work intended for a
  later conference.
- Journals: no hard cap but length must match contribution; major/minor
  revision rounds re-read by the same reviewers; extended conference
  versions need substantial new content (check the journal's threshold);
  blinding varies by journal.
- Demo and poster tracks: a few pages describing a live artifact; judged on
  interest and feasibility; a video figure is often decisive.
