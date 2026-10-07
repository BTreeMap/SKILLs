# Search: sources, queries, snowballing, saturation

The phase takes a session with filled criteria and returns a corpus of
candidates. Retrieve only through the script: a search that bypasses the log
does not exist for the review.

## Source routing

| Source | Strength | Reach for it when |
| --- | --- | --- |
| openalex | Broadest index, citation counts, abstracts, snowballing | Always; run it first |
| arxiv | Freshest preprints in CS, math, physics; full metadata | The field posts preprints; recency matters |
| crossref | Publisher-registered records, DOIs, non-arXiv venues | Journal-heavy fields; verifying formal publication |

Use at least as many sources as the level requires; a lite run that stops
after one source stops after a productive one. Other scholarly indexes
(PubMed, Semantic Scholar) join only when the harness already provides
authenticated access; record such searches in the log by hand with the same
fields the script writes.

## Query design

- Decompose the question into two to four concepts; for each, list the
  synonyms and near terms the field uses. Different communities name one
  idea differently; missing a vocabulary misses its papers.
- Run a pilot query per concept pair, skim the top results, refine terms,
  then run the real queries. Pilot queries are logged like any other.
- Plain phrases work for openalex and crossref. arXiv ranks fielded queries
  far better: wrap phrases as `all:"retrieval"` and combine with operators,
  `cat:cs.CL AND all:"retrieval"`. The script passes queries containing `:`
  through unchanged.
- Year bounds: pass `--from-year` and `--to-year` for openalex and crossref.
  The arxiv source ignores them, so apply the window at screening.
- When the script signals truncation, either the query is too broad (narrow
  it and rerun) or the field is large (raise `--limit` toward its cap of 100
  and say in the report that coverage is a ranked sample, with counts).

## Snowballing

Snowball citations to find papers keyword search missed, once the first
screening pass has produced included papers:

- Backward (`--direction backward`): the references of an included paper;
  finds the foundations everyone cites.
- Forward (`--direction forward`): papers citing an included paper; finds
  newer work the indexes rank poorly.

Seed from the most-cited included papers first. OpenAlex lists zero
references for some arXiv-only records: seed from a journal-indexed record
instead, or read the paper's own reference list during extract. Screen new
candidates from snowballing with the same criteria as keyword results. At
full, a round covers two or more seeds; at ultra, repeat rounds until a
round yields no new included paper.

## Saturation and stopping

Stop searching when the last round of queries and snowballing returns only
papers the corpus already holds or papers screening rejects. Before
stopping, check for misses: one query per major synonym set has run, and
each included paper's references were either snowballed or read. Record the
stopping decision with `jot`; the report states it. A zero-result query is
evidence: cite it later as a gap probe by its log id.
