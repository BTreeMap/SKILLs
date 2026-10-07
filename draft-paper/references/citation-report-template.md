# Citation verification report

Stage 5 deliverable; re-run it on every revision that adds a citation. One
row per citation key in the draft.

## Retrieval fallback

Fetch every BibTeX entry via API, in this order: Semantic Scholar, OpenAlex,
Crossref, arXiv API. Record which source supplied each entry in the Source
column. An entry written from memory is a fabrication.

<template for="citation-report">
| Key | Citing sentence (short) | Source | Exists | Fields match | Supports sentence | Action |
|-----|-------------------------|--------|--------|--------------|-------------------|--------|
| | | | | | | |
</template>

## Columns

| Column | Check |
| --- | --- |
| Exists | An API lookup returned the source. |
| Fields match | Authors, year, venue, and title belong to that source. Field-level errors are the most common failure after outright fabrication. |
| Supports sentence | The source backs what the citing sentence claims, not a neighboring claim. |
| Action | Keep, fix (corrected field), downgrade (weaker claim that the source supports), or cut. |

Leave an unverifiable citation as `[CITATION NEEDED]` in the draft; it ships
as an explicit placeholder, never as a plausible-looking entry.
