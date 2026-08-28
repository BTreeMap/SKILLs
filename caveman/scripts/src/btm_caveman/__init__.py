"""Deterministic guard for the caveman compress mode.

The agent performs the actual prose compression; this package does everything
an LLM is bad at, deterministically:

  check <file>              report hard admissibility plus advisory signals
  prepare <file>            admit the file, write a verified out-of-tree
                            backup, emit the compressible body to a work file
  apply <file> <body-file>  validate the compressed body against the backup;
                            atomic-write the target only when validation passes
  restore <file>            undo a completed compression from its backup
  clean <file> | --all      delete one file's backup artifacts, or the whole
                            backup tree (destroys the undo)

The target file is never written until validation passes, so it never holds a
half-valid state. Output is plain ASCII.

Division of labor (neuro-symbolic): this is the symbolic half. It owns what is
exact (backup identity, atomic writes, structural equality) and refuses
(exit 1) only on invariant violations: missing/oversized/non-UTF-8/empty
files, secret-like names, backup artifacts. Content-type judgment is
heuristic, so it is never a verdict here: it is emitted as SIGNAL lines for
the compressing agent, the neuro half, to weigh. A signal never blocks; the
verified backup keeps every judgment call undoable.

`model` holds the closed domain, `classify` the heuristics, `sensitive` the
exact refusals, `markdown` the protected regions, `validate` the structural
comparison, `store` the backup filesystem, `admit` the parse boundary, and
`cli` the verbs.
"""
