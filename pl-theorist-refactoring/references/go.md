# Go Cost Model

## Disclosed Constraints

- No TCO. Collection-sized recursion risks stack growth.
- Higher-order callbacks, closures, interface values, and generic abstraction can
  escape or allocate; Go optimizes many direct loops more predictably.
- The language and ecosystem favor explicit control flow, simple structs, and
  visible error handling over generalized FP machinery.
- Functional options mutate a fresh configuration object; they are a controlled
  construction pattern, not mathematical purity.

## Preferred FP Shapes

- Keep a pure conceptual pipeline, but compile ordinary collection transforms to
  direct loops with named pure predicate/projector helpers.
- Use explicit `(value, error)` results, concrete value structs, and small total
  transition functions.
- Use functional options for optional construction-time configuration when the
  repository already favors the pattern. Validate before publication.
- Preallocate result slices when a sound upper bound or exact capacity is known.
- Use standard-library helpers when present; otherwise use a direct fold loop
  rather than constructing a generic HOF framework.

## Cost Guard

1. Replace recursion with iteration.
2. If a closure or interface abstraction escapes on a relevant path, use a named
   function and concrete types.
3. If a `map`/`filter` helper obscures allocation or control flow, retain the
   algebra in pure helpers and use one explicit loop.
4. Confine unavoidable mutation to a fresh local value; publish only a completed
   valid result.
5. Preserve explicit error timing and partial-result contracts.

## Validation Focus

Run formatting, package tests, and static analysis when configured. Use existing
benchmarks and escape analysis for hot paths; otherwise report closure/allocation
risk as unmeasured.