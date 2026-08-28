"""Session engine for literature reviews over OpenAlex, arXiv, and Crossref.

The package owns the exact half of a review: session state, search logging,
identity resolution across DOI, arXiv id, and title, deduplication, decision
bookkeeping, and citation resolution checks. The invoking agent owns every
judgment call: criteria, screening, reading, synthesis. Subcommands print one
JSON document to stdout; advisory `signal:` lines go to stderr and never
block; failures print `error:` to stderr and exit 1.

`constants` fixes the vocabularies, `paper` the record and its parse
boundary, `upstream` the per-source normalization, `http` and `sources` the
network, `session` the storage, `gather`, `curate`, and `verify` the verbs,
`report` the output channels, and `cli` the argument surface.
"""
