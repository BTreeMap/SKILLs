# Python Cost Model

## Disclosed Constraints

- No tail-call optimization. Unbounded structural recursion consumes one frame
  per element.
- Slicing, concatenation, eager intermediates, and transient wrappers increase
  allocation and GC pressure; recursive head/tail list code can become
  quadratic.
- `map`, `filter`, and generators are lazy and single-pass. Deferral changes
  exception timing, resource lifetime, and when effects occur.
- Python's type hints cannot make runtime input valid without boundary checks.

## Preferred FP Shapes

- Prefer explicit `map` and `filter` composition over equivalent comprehension
  syntax so the filter-transform algebra remains visible. Yield only when a
  named predicate, required concrete collection, or repository convention makes
  another form materially clearer.
- Use named curried helpers through `functools.partial` when partial application
  clarifies a reusable operation.
- Prefer generators for streaming and $O(1)$ auxiliary memory.
- Prefer `sum`, `any`, `all`, `min`, `max`, and `next` over generic reduction.
- Use `functools.reduce` only for a genuine fold with an explicit accumulator
  invariant.
- Represent closed states with frozen dataclasses, enums, tagged unions, and
  exhaustive type-checker-supported matching where project tooling permits.
- Represent optional/fallible flow with established project types or explicit
  return unions. Do not introduce a runtime monad hierarchy solely for syntax.

## Cost Guard

1. Replace collection-sized recursion with an iterator or generator.
2. If the caller requires eager output, materialize exactly once at the public
   boundary.
3. If lazy conversion changes exception/effect timing or closes a resource too
   early, preserve eager evaluation inside the resource scope.
4. If a pipeline needs early exit or complex error recovery, use a native
   short-circuit primitive or a local loop with pure helpers.
5. If repeated lambdas hide domain meaning, name the predicate/projector; do not
   pursue point-free style past debuggability.

## Validation Focus

Test empty, large, one-shot iterator, and exception-producing inputs. Verify
whether callers require a list, reusable iterable, or lazy iterator. Measure
peak memory before claiming a streaming improvement.