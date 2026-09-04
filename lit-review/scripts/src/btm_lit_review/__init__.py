"""Session engine for literature reviews over OpenAlex, arXiv, and Crossref.

Owns the exact half of a review: session state, search logging, identity
resolution, deduplication, decision bookkeeping, and citation checks. The
agent owns every judgment call: criteria, screening, reading, synthesis.
Subcommands print one JSON document to stdout; advisory `signal:` lines go
to stderr and never block; failures print `error:` to stderr and exit 1.

`constants` fixes the vocabularies, `paper` the record and parse boundary,
`upstream` the per-source normalization, `http` and `sources` the network,
`session` the storage, `gather`/`curate`/`verify` the verbs, `draft`/`views`
the output channels, `cli` the argument surface.
"""
