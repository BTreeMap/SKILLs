# Search: Sources, Queries, Snowballing, Saturation

All retrieval goes through the bundled script so every query lands in the
log with its date, parameters, and counts. A search that bypasses the log
does not exist for the review.

## Source routing

| Source | Strength | Reach for it when |
| --- | --- | --- |
| openalex | Broadest index, citation counts, abstracts, snowballing | Always; run it first |
| arxiv | Freshest preprints in CS, math, physics; full metadata | The field posts preprints; recency matters |
| crossref | Publisher-registered records, DOIs, non-arXiv venues | Journal-heavy fields; verifying formal publication |

Minimum rounds: lite may stop after one productive source; full uses at
least two; ultra uses all three. Other scholarly indexes (PubMed, Semantic
Scholar) join only when the harness already provides authenticated access;
record such searches in the log by hand with the same fields the script
writes.

## Query design

- Decompose the question into two to four concepts; for each, list the
  synonyms and near terms the field actually uses. Different communities
  name one idea differently; missing a vocabulary misses its papers.
- Run a pilot query per concept pair, skim the top results, refine terms,
  then run the real queries. Pilot queries are logged like any other.
- Plain phrases work for openalex and crossref. arXiv ranks fielded
  queries far better: wrap phrases as `all:"retrieval"` and combine with
  operators, `cat:cs.CL AND all:"retrieval"`. The script passes queries
  containing `:` through unchanged and signals when an unfielded query
  matches nothing.
- Year bounds: pass `--from-year` and `--to-year` for openalex and
  crossref; the arxiv source signals that it ignores them, so apply the
  window at screening.
- When the script signals truncation, either the query is too broad (narrow
  it and rerun) or the field is genuinely large (raise `--limit` toward the
  cap and say in the report that coverage is a ranked sample, with counts).

## Snowballing

Keyword search finds what shares your vocabulary; snowballing finds the
rest. After the first screening pass produces included papers:

- Backward (`--direction backward`): the references of an included paper;
  finds the foundations everyone cites.
- Forward (`--direction forward`): papers citing an included paper; finds
  newer work the indexes rank poorly.

Seed from the most-cited included papers first. New candidates from
snowballing are screened with the same criteria as keyword results. Full
runs at least one round over two or more seeds; ultra repeats rounds until a
round yields no new included paper.

## Saturation and stopping

Stop searching when the last round of queries and snowballing returns only
papers the corpus already holds or papers screening rejects. Before
stopping, check the misses list: one query per major synonym set has run,
and each included paper's references were either snowballed or read. Record
the stopping decision with `jot`; the report states it. A query that
returns zero results is evidence, worth citing later as a gap probe by its
log id.
