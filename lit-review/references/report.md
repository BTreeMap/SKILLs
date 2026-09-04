# Report: Template, Verification, Prose Rules

The deliverable is one Markdown file, written from the extraction records
and the session state. Assemble, verify, then deliver.

## Template

Sections in order; drop bracketed ones where the level says so.

<report-template>
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
</report-template>

## Verification before delivery

1. Run the script's `verify` subcommand. It emits one object: `checked`
   (count of included papers), `broken_dois` (keys whose DOI failed to
   resolve), and `results` (one record per paper: `key`, `title`,
   `doi_resolves`, `doi_http_status`, `crossref_title_match`, or an
   `identity` note for DOI-less records). Fix broken DOIs (usually a mangled
   key: re-search the paper), or remove the citation and its dependent
   claims. A Crossref title-mismatch signal is a possible retraction or
   erratum: check the landing page before keeping the citation.
2. Run `cite-check --draft <file>`. Marker numbers come from the script's
   append-only assignment, so a late inclusion extends the table and
   existing citations stand. Fix every problem it lists (markers never
   assigned, citations of excluded or unread papers), resolve the at-risk
   findings it echoes, and rerun until clean. Unused included papers are a
   coverage question to settle deliberately.
3. Walk each report citation back to its corpus record and read level; a
   full-text-sounding claim on an abstract-level record is rewritten or
   relabeled.
4. Check the flow counts against `status` output; numbers in the report
   must equal numbers in state.

## Prose rules

The report is judged by what it pins down. Concrete subjects, plain verbs,
reported numbers with units, named papers doing named things.

- Banned vocabulary, in the report and in every intermediate note. If one
  appears in a quoted source title, it stays inside the quotation marks:

  <banned-words>
  delve, tapestry, landscape (figurative), pivotal, crucial, seminal,
  groundbreaking, cutting-edge, state-of-the-art (unless a paper claims it,
  attributed), rapidly evolving, burgeoning, holistic, robust (outside a
  statistics term), comprehensive, seamless, leverage (verb), showcase,
  underscore, highlight (verb), testament, interplay, myriad, plethora,
  paradigm shift, in the realm of, it is important to note
  </banned-words>

- No "not X but Y" framing, no forced triads, no rhetorical questions, no
  sentence that announces what the next sentence will say.
- Superlatives and firsts ("the first work to ...") only as a paper's own
  attributed claim; the corpus cannot prove priority.
- Hedge once, precisely ("on the two benchmarks tested"); one qualifier
  per claim.
- Sentence-case headings, no emoji, no bold-label bullet lists in the
  deliverable; tables carry structure.
- Recency words ("recent", "current") always bind to the method section's
  as-of date.
- Sweep the finished report with `/humanize` and its detection index
  before delivery.
