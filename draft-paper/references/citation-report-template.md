# Citation verification report

Stage 5 deliverable; re-run it on every revision that adds a citation. One
row per citation key in the draft.

## Retrieval

Take every entry's fields (authors, year, venue, title, DOI) from a
retrieved record: the stage-1 `/lit-review` corpus, or `/search-web scholar`
by title or DOI (`--source crossref` resolves a DOI, `--source arxiv` a
preprint). Read the cited passage with `/read-pdf` or `/search-web fetch`.

<template for="citation-report">
| Key | Citing sentence (short) | Source | Exists | Fields match | Supports sentence | Action |
|-----|-------------------------|--------|--------|--------------|-------------------|--------|
| | | | | | | |
</template>

## Columns

| Column | Check |
| --- | --- |
| Source | The retrieval that returned the record: a corpus key, or the `scholar` source and DOI. |
| Exists | A retrieval returned the record. |
| Fields match | Authors, year, venue, and title belong to that record. Field-level errors are the most common failure after outright fabrication. |
| Supports sentence | The source backs what the citing sentence claims, not a neighboring claim. |
| Action | Keep, fix (corrected field), downgrade (a weaker claim the source supports), or cut. |

Leave an unverifiable citation as `[CITATION NEEDED]` in the draft; it ships
as an explicit placeholder, never as a plausible-looking entry.
