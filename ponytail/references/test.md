# Ponytail Test Verb

Derive one minimal runnable check: smallest thing that fails if logic
breaks.

## Pipeline

1. Find logic that can break: branch, loop, parser, money or security path.
   Trivial one-liners get nothing.
2. Pick smallest harness that runs today: repo's runner and fixtures if
   present, else `assert`-based `demo()`/`__main__` self-check or one small
   `test_*` file. Add no framework or fixture.
3. One check per breakable behavior, through public call rather than per
   private helper, exercising real edge (empty input, boundary value,
   failure path).

## Output

Check, runnable as emitted, then one line: what it catches, how to run it.
Never delete existing passing test to satisfy minimalism: floor is one
check.
