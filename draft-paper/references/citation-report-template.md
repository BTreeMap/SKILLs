# Citation verification report

Stage 5 deliverable; re-run on every revision adding citation. One row per
citation key in draft.

## Retrieval

Take every entry's fields (authors, year, venue, title, DOI) from retrieved
record: stage-1 `/lit-review` corpus, or `/search-web scholar` by title or
DOI (`--source crossref` resolves DOI, `--source arxiv` preprint). Read
cited passage with `/read-pdf` or `/search-web fetch`.

<template for="citation-report">
| Key | Citing sentence (short) | Source | Exists | Fields match | Supports sentence | Action |
|-----|-------------------------|--------|--------|--------------|-------------------|--------|
| | | | | | | |
</template>

## Columns

| Column | Check |
| --- | --- |
| Source | Retrieval that returned record: corpus key, or `scholar` source and DOI. |
| Exists | A retrieval returned record. |
| Fields match | Authors, year, venue, title belong to that record. Field-level errors are most common failure after outright fabrication. |
| Supports sentence | Source backs what citing sentence claims, not neighboring claim. |
| Action | Keep, fix (corrected field), downgrade (weaker claim source supports), or cut. |

Leave unverifiable citation as `[CITATION NEEDED]` in draft; it ships as
explicit placeholder, never as plausible-looking entry.
