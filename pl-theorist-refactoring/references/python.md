# Python Runtime Profile

## Disclosed Constraints

- **No tail-call optimization.** Recursive traversal consumes one Python frame
  per step; do not use structural recursion for unbounded inputs.
- **Allocation and GC pressure.** List slicing, list concatenation, and eager
  intermediate collections can make a linear transform quadratic or retain
  unnecessary memory.
- **Iterator timing.** Generators, `map`, and `filter` defer work and errors
  until consumed; this may differ from an eager source loop.

## Preferred Shapes

- Use generator expressions, generator functions, `map`, and `filter` for
  streaming transforms when the caller can consume lazily.
- Use a comprehension when an eager collection is required and it is the
  clearest single-pass form.
- Extract pure predicates and transformations into named functions when they
  embody a domain rule.
- Use `functools.reduce` only when a named accumulator makes the invariant
  clearer than a loop; it is not automatically more Pythonic or faster.

## Cost Guard and Fallback

1. If the candidate uses recursion over collection size, replace it with an
   iterator or generator pipeline.
2. If chaining would materialize intermediates, stream with a generator or
   use one explicit loop.
3. If deferred execution changes exception timing, resource lifetime, or
   side-effect order, retain eager evaluation deliberately.
4. If a loop provides early termination or clear error handling, keep the loop
   and isolate the pure per-item step.

## Validation Focus

Test empty inputs, large inputs, iterator inputs, exception timing, and whether
callers expect a concrete collection rather than a one-shot iterable.
