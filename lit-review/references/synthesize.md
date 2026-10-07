# Synthesize and report: themes, gaps, deliverable

Synthesis turns extraction records into themes and gaps; the report phase
turns them, the notebook, and the session state into one Markdown file. The
unit of synthesis is the theme: a paragraph per paper makes an annotated
bibliography.

## Build themes

- Cluster the records' claims into three to six themes that answer parts of
  the research question. A paper may appear in several themes; a theme needs
  two papers, and one paper is a finding.
- In each theme, write what the papers collectively establish, where they
  diverge, and which evidence is strongest, citing records by key.
- Order themes by relevance to the question; chronology only for a
  historical question.

## Rules of evidence

- **Convergence needs independence.** State that the literature "agrees" or
  "establishes" only when two or more included papers from different author
  groups support it. One group's repeated result is that group's position.
- **Disagreement is reported.** When records conflict, name both sides,
  their evidence, and any visible cause (different datasets, metrics,
  definitions). Do not average conflicting numbers or pick the majority
  silently. If the corpus cannot resolve it, the report says so.
- **Single-paper claims are labeled.** Write "One study reports ...".
- **Weight follows appraisal.** Read each record's `appraisal` with
  `recall --kind extraction`. A weakly appraised paper can be mentioned; it
  cannot anchor a theme's conclusion. Say why when weight differs.
- **Every synthesis sentence is traceable.** Each claim maps to named
  records (invariant 1); delete a sentence no record supports.
- **Trends come from the corpus.** Derive what is recent, growing, or
  standard practice from the corpus's year distribution and the logged
  search dates, never from background knowledge. "Since 2023, four of the
  six included papers adopt X" is checkable; "the field is rapidly moving
  toward X" is not.

## Gaps

A gap is an absence in this corpus; phrase it that way: "none of the N
included papers evaluates X"; "no research exists on X" overclaims. The
difference is the review's own coverage limit, which the report's
limitations section owns. Candidate gaps: populations or settings untested,
methods never compared head to head, results resting on one dataset, claims
with only single-group support.

## Findings and gaps as records

Promote each theme conclusion into the notebook with `note`: a finding
carries its claim, supporting keys, and the read level each citation needs;
a gap carries the absence claimed, the null-search log ids proving it, and a
watch: `|`-separated words a challenger would use in a title or abstract,
matched literally. `brief` re-derives their verdicts against the live
corpus: an excluded or under-read support flags the finding at-risk, and a
later paper matching a gap's watch flags the gap challenged, the cue to
re-read a claim written earlier. Supersede a record when the field model
moves. Keep forming hypotheses on the pad as `map` or `open` entries until
they earn support.

## Report template

Assemble, verify, then deliver. Fill sections in order and drop bracketed
ones where the level says so. Take the flow counts from state: `status`
gives per-status counts, the log gives per-search totals.

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
Rules of evidence requires.

[## Appraisal table]  (ultra: one row per included paper, six dimensions)

## Limitations of this review
Coverage limits: sources not searched, papers identified but unassessed,
abstract-only readings, truncation. Anything invariant 5 or the screening
log forced to be disclosed lands here.

## Gaps and open questions
Corpus-relative gaps, phrased as Gaps requires.

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
