"""Deterministic guard for the caveman compress mode.

The agent compresses prose; this package validates and backs it up:
check, prepare, apply, restore, clean <file>|--all. The target is never
written until the compressed body validates against a verified backup, so
it never holds a half-valid state; content-type judgment is heuristic and
surfaces only as SIGNAL lines for the agent to weigh, never a blocking verdict.

`model` holds the closed domain, `classify` the heuristics, `sensitive` the
exact refusals, `markdown` the protected regions, `validate` the structural
comparison, `store` the backup filesystem, `admit` the parse boundary, and
`cli` the verbs.
"""
