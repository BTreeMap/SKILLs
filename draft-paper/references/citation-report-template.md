# Citation verification report

Stage 5 deliverable; re-run on every revision adding citation. One row per
citation key in draft.

## Retrieval

Take every entry's fields (authors, year, venue, title, DOI) from retrieved
record, in this order:

1. `check`'s `citations` row with `key`: attached corpus holds record; copy
   its `record` fields, retrieve nothing.
2. Ref under `unresolved`: `cite <ref>` asks corpus, then indexes; copy
   returned record, its `source` and `retrieved` date.
3. No DOI or arXiv id: `/search-web scholar` by title, then `cite` DOI it
   returns.

Read cited passage with `/read-pdf` or `/search-web get`; corpus record
proves paper exists, never what it says.

**Template: citation-report**

```markdown
| Key | Citing sentence (short) | Source | Exists | Fields match | Supports sentence | Action |
|-----|-------------------------|--------|--------|--------------|-------------------|--------|
| | | | | | | |
```

## Columns

| Column | Check |
| --- | --- |
| Source | Record behind row: corpus key, or `cite` record's `source` index and DOI. |
| Exists | A retrieval returned record. |
| Fields match | Authors, year, venue, title belong to that record. Field-level errors are most common failure after outright fabrication. |
| Supports sentence | Source backs what citing sentence claims, not neighboring claim. |
| Action | Keep, fix (corrected field), downgrade (weaker claim source supports), or cut. |

Leave unverifiable citation as `[CITATION NEEDED]` in draft; it ships as
explicit placeholder, never as plausible-looking entry.
