# Ponytail Test Verb

Derive the one minimal runnable check: the smallest thing that fails if
the logic breaks.

## Pipeline

1. Find the logic that can actually break: a branch, a loop, a parser, a
   money or security path. Trivial one-liners get nothing.
2. Pick the smallest harness that runs today: an `assert`-based
   `demo()`/`__main__` self-check, or one small `test_*` file on the runner
   the repo already has. No new frameworks, no fixtures.
3. One check per breakable behavior, exercising the real edge (empty
   input, the boundary value, the failure path), not a mock parade.

## Output

The check, runnable as emitted, then one line: what it catches and how to
run it.

## Boundaries

Law-derived suites (properties, invariants, per-variant coverage) route to
`/pl-theorist test`. Never delete an existing passing test to satisfy
minimalism: the floor is one check, not zero.
