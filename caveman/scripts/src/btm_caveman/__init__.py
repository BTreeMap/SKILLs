"""Deterministic guard for the caveman refactor verb.

The agent compresses prose; this package validates and copies it:
prepare, apply, replace, clean [<file>|--all]. The target is never written
until the compressed body validates against a verified copy, so it never
holds a half-valid state; content-type judgment is heuristic and surfaces
only as signal lines for the agent to weigh, never a blocking verdict.

`model` holds the closed domain, `classify` the heuristics, `sensitive` the
exact refusals, `markdown` the protected regions, `validate` the structural
comparison, `store` the copy filesystem, `accept` the parse boundary, and
`cli` the verbs.
"""
