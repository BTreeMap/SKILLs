# Citation Verification Report

Stage 5 deliverable; re-run on every revision that adds a citation. One row
per citation key in the draft.

## Retrieval fallback

Fetch every BibTeX entry via API, in this order: Semantic Scholar, OpenAlex,
Crossref, arXiv API. Record which source supplied each entry in the Source
column. An entry written from memory is a fabrication; every entry is
fetched.

| Key | Citing sentence (short) | Source | Exists | Fields match | Supports sentence | Action |
|-----|-------------------------|--------|--------|--------------|-------------------|--------|
| | | | | | | |

- **Exists**: an API lookup returned the source.
- **Fields match**: authors, year, venue, and title belong to that source.
  Field-level errors are the most common failure after outright fabrication.
- **Supports sentence**: the source backs what the citing sentence claims,
  not a neighboring claim.
- **Action**: keep, fix (corrected field), downgrade (weaker claim that the
  source supports), or cut.

Unverifiable citations stay `[CITATION NEEDED]` in the draft; they ship as
explicit placeholders, never as plausible-looking entries.
