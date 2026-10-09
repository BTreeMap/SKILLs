# Find: sources, queries, snowballing, saturation

Phase takes session with filled criteria; returns corpus of candidates.
Retrieve only through script: search bypassing log does not exist for
review.

## Source routing

| Source | Strength | Reach for it when |
| --- | --- | --- |
| openalex | Broadest index, citation counts, abstracts, snowballing | Always; run first |
| arxiv | Freshest preprints in CS, math, physics; full metadata | Field posts preprints; recency matters |
| crossref | Publisher-registered records, DOIs, non-arXiv venues | Journal-heavy fields; verifying formal publication |
| semanticscholar | Every field, own citation graph, open-access PDF links | Second graph for snowballing; OpenAlex misses paper's references |
| firecrawl | arXiv, PubMed, bioRxiv, medRxiv abstracts ranked by meaning | Biomedical or preprint fields; concept named in many vocabularies |

Use at least as many sources as level requires; basic run stopping after one
source stops after productive one. `firecrawl` returns no year, author, or
citation count in `find`, reports no match count: treat its results as
ranked sample, fill gaps from another source's record of same paper. Other
scholarly indexes join only when harness already provides authenticated
access; record such searches in log by hand with same fields script writes.

## Query design

- Decompose question into two to four concepts; for each, list synonyms and
  near terms field uses. Different communities name one idea differently;
  missing vocabulary misses its papers.
- Run pilot query per concept pair, skim top results (`--show` lists them in
  `find` envelope), refine terms, then run real queries. Pilot queries
  logged like any other.
- Plain phrases work for openalex and crossref. arXiv ranks fielded queries
  far better: wrap phrases as `all:"retrieval"`, combine with operators,
  `cat:cs.CL AND all:"retrieval"`. Script passes queries containing `:`
  through unchanged.
- Year bounds: pass `--from-year` and `--to-year`; every source but arxiv
  applies them. arxiv ignores them and script says so: apply window at
  screening.
- Script signals truncation: query too broad (narrow, rerun) or field large.
  Large field: raise `--limit` toward cap of 100, then rerun same query with
  `--offset` signal names to fetch next ranks. Stopping before upstream
  total: say in report coverage is ranked sample, with counts. Indexes page
  no further than rank 10,000 (openalex, crossref), 1,000 (semanticscholar),
  or 500 (firecrawl).

## Snowballing

Snowball citations to find papers keyword search missed, once first
screening pass has produced included papers:

- Backward (`--direction backward`): references of included paper; finds
  foundations everyone cites.
- Forward (`--direction forward`): papers citing included paper; finds newer
  work indexes rank poorly.

`--source` picks citation graph: `openalex`, default, or `semanticscholar`.
Seed from most-cited included papers first. OpenAlex lists zero references
for some arXiv-only records: snowball same seed with
`--source semanticscholar`, seed from journal-indexed record instead, or
read paper's own reference list during extract. Screen new candidates from
snowballing with same criteria as keyword results. Full: cycle covers two or
more seeds. Maximum: repeat cycles until cycle yields no new included paper.

## Saturation and stopping

Stop searching when last cycle of queries and snowballing returns only
papers corpus already holds or papers screening rejects. Before stopping,
check for misses: one query per major synonym set has run; each included
paper's references either snowballed or read. Record stopping decision with
`write`; report states it. Zero-result query is evidence: cite later as gap
probe by its log id.
