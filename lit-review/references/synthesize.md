# Synthesize and report: themes, gaps, deliverable

Synthesis turns extraction records into themes and gaps; report phase turns
them, notebook, session state into one Markdown file. Unit of synthesis is
theme: paragraph per paper makes annotated bibliography.

## Build themes

- Cluster records' claims into three to six themes answering parts of
  research question. Paper may appear in several themes; theme needs two
  papers; one paper is a finding.
- In each theme, write what papers collectively establish, where they
  diverge, which evidence is strongest, citing records by key.
- Order themes by relevance to question; chronology only for historical
  question.

## Rules of evidence

- **Convergence needs independence.** State literature "agrees" or
  "establishes" only when two or more included papers from different author
  groups support it. One group's repeated result is that group's position.
- **Disagreement is reported.** Records conflict: name both sides, their
  evidence, any visible cause (different datasets, metrics, definitions). Do
  not average conflicting numbers or pick majority silently. Corpus cannot
  resolve it: report says so.
- **Single-paper claims are labeled.** Write "One study reports ...".
- **Weight follows appraisal.** Read each record's `appraisal` with
  `recall --kind extraction`. Weakly appraised paper can be mentioned;
  cannot anchor theme's conclusion. Say why when weight differs.
- **Every synthesis sentence is traceable.** Each claim maps to named
  records (invariant 1); delete sentence no record supports.
- **Trends come from the corpus.** Derive what is recent, growing, or
  standard practice from corpus's year distribution and logged search dates,
  never from background knowledge. "Since 2023, four of the six included
  papers adopt X" is checkable; "the field is rapidly moving toward X" is
  not.

## Gaps

Gap is absence in this corpus; phrase it that way: "none of the N included
papers evaluates X"; "no research exists on X" overclaims. Difference is
review's own coverage limit, which report's limitations section owns.
Candidate gaps: populations or settings untested, methods never compared
head to head, results resting on one dataset, claims with only single-group
support.

## Findings and gaps as records

Promote each theme conclusion into notebook with `note`: finding carries
claim, supporting keys, read level each citation needs; gap carries absence
claimed, null-search log ids proving it, and watch: `|`-separated words a
challenger would use in title or abstract, matched literally. `brief`
re-derives their verdicts against live corpus: excluded or under-read
support flags finding at-risk; later paper matching gap's watch flags gap
challenged, cue to re-read claim written earlier. Supersede record when
field model moves. Keep forming hypotheses on pad as `map` or `open` entries
until they earn support.

## Report template

Assemble, verify, then deliver. Fill sections in order; drop bracketed ones
where level says so. Take flow counts from state: `status` gives per-status
counts and exclusions by screening stage; log gives per-search totals.
Exclusions `status` counts as `unstated` carry no stage: set it with
`update` before counting.

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

1. Run `verify`. Emits one object: `checked` (count of included papers),
   `broken_dois` (keys whose DOI failed to resolve), `results` (one record
   per paper: `key`, `title`, `doi_resolves`, `doi_http_status`,
   `crossref_title_match`, or `identity` note for DOI-less records). Fix
   broken DOI (usually mangled key: re-search paper), or remove citation and
   its dependent claims. Crossref title-mismatch signal is possible
   retraction or erratum: check landing page before keeping citation.
2. Run `cite-check --draft:file <file>`. Fix every problem it lists (markers
   never assigned, citations of excluded or unread papers), resolve at-risk
   findings it echoes, rerun until clean. Unused included papers are
   coverage question to settle deliberately.
3. Walk each report citation back to its corpus record and read level;
   rewrite or relabel full-text-sounding claim on abstract-level record.
4. Check flow counts against `status` output; numbers in report must equal
   numbers in state.

## Prose rules

Write concrete subjects, plain verbs, reported numbers with units, named
papers doing named things. Banned vocabulary in SKILL.md applies.

- No "not X but Y" framing, no forced triads, no rhetorical questions, no
  sentence announcing what next sentence will say.
- Superlatives and firsts ("the first work to ...") only as paper's own
  attributed claim; corpus cannot prove priority.
- Hedge once, precisely ("on the two benchmarks tested"); one qualifier per
  claim.
- Sentence-case headings, no emoji, no bold-label bullet lists in
  deliverable; tables carry structure.
- Recency words ("recent", "current") always bind to method section's as-of
  date.
- Sweep finished report before delivery, at level's depth:

  | Level | Sweep |
  | --- | --- |
  | lite | Mechanical only: search report for U+2014 and U+2013 dashes, `**`, Title Case headings, emoji, curly quotes, each banned word; fix every hit. |
  | full, ultra | Lite searches, then `/humanize` on report file: it scans its detection index, loads only owner files of patterns it finds. |

## Handoffs

After delivery, offer each next step whose condition holds; name sibling,
verb, artifact to pass. Invoke none unasked.

- Review feeds paper: `/draft-paper build`; pass this session's identifier
  to its `link <run> --corpus`, so corpus records need no re-retrieval.
- Paper to referee against this literature: `/peer-review`; pass this
  session's identifier to its `link <session> --corpus`.
- Question stays open past what corpus answers: `/ponder` with open
  question; its sources `cite --corpus <this session>` for corpus records.
