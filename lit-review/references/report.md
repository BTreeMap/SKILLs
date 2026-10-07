# Report: template, verification, prose rules

The phase takes the extraction records, the notebook, and the session state
and returns the deliverable: one Markdown file. Assemble, verify, then
deliver.

## Template

Fill sections in order and drop bracketed ones where the level says so. Take
the flow counts from state: `status` gives per-status counts, the log gives
per-search totals.

<template for="report">
# Literature review: <question>

## Summary
One paragraph: what the included literature answers, where it disagrees,
what remains open. No citations needed here; everything reappears cited
below.

## Method
Sources searched with dates and logged query counts; criteria (and
amendments, at ultra); flow counts: identified N, after dedup N, excluded
at title/abstract N, excluded at full-text N, included N. State the search
dates as the review's as-of point, and note truncated searches as ranked
samples with their upstream totals.

## <Theme sections, one per theme>
Synthesis prose citing records as [n], using the numbers `brief` or
`cite-check` assigned. Disagreements and single-paper claims labeled as
the rules in synthesize require.

[## Appraisal table]  (ultra: one row per included paper, six dimensions)

## Limitations of this review
Coverage limits: sources not searched, papers identified but unassessed,
abstract-only readings, truncation. Anything invariant 5 or the screening
log forced to be disclosed lands here.

## Gaps and open questions
Corpus-relative gaps, phrased per synthesize.

## Included papers
| [n] | title | authors | year | venue | read level | key |
Rows follow the script's marker table; bibliography with DOI or arXiv
link per entry.
</template>

## Verification before delivery

1. Run `verify`. It emits one object: `checked` (count of included papers),
   `broken_dois` (keys whose DOI failed to resolve), and `results` (one
   record per paper: `key`, `title`, `doi_resolves`, `doi_http_status`,
   `crossref_title_match`, or an `identity` note for DOI-less records). Fix
   a broken DOI (usually a mangled key: re-search the paper), or remove the
   citation and its dependent claims. A Crossref title-mismatch signal is a
   possible retraction or erratum: check the landing page before keeping
   the citation.
2. Run `cite-check --draft:file <file>`. Fix every problem it lists (markers
   never assigned, citations of excluded or unread papers), resolve the
   at-risk findings it echoes, and rerun until clean. Unused included
   papers are a coverage question to settle deliberately.
3. Walk each report citation back to its corpus record and read level;
   rewrite or relabel a full-text-sounding claim on an abstract-level
   record.
4. Check the flow counts against `status` output; numbers in the report
   must equal numbers in state.

## Prose rules

Write concrete subjects, plain verbs, reported numbers with units, and
named papers doing named things. The banned vocabulary in SKILL.md applies.

- No "not X but Y" framing, no forced triads, no rhetorical questions, no
  sentence that announces what the next sentence will say.
- Superlatives and firsts ("the first work to ...") only as a paper's own
  attributed claim; the corpus cannot prove priority.
- Hedge once, precisely ("on the two benchmarks tested"); one qualifier per
  claim.
- Sentence-case headings, no emoji, no bold-label bullet lists in the
  deliverable; tables carry structure.
- Recency words ("recent", "current") always bind to the method section's
  as-of date.
- Sweep the finished report with `/humanize` and its detection index before
  delivery.
