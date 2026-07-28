# Rust Cost Model

## Disclosed Constraints

- No guaranteed TCO. Structural recursion is unsuitable for unbounded linear
  data unless the data structure or algorithm requires it and depth is bounded.
- Standard iterator adapters and `Option`/`Result` combinators usually compile
  to allocation-free loops, but “zero cost” remains a claim to verify on a hot
  path.
- Deep currying, captured borrows, boxed closures, and trait objects can produce
  lifetime friction, dynamic dispatch, or heap allocation.
- Ownership is observable through consuming versus borrowing, clone behavior,
  drop order, and resource lifetime.

## Preferred FP Shapes

- Use iterator adapters, enums, exhaustive matching, `Option`/`Result`
  combinators, `?`, and `async`/`await`.
- Prefer generic named helpers over `Box<dyn Fn>` when static composition works.
- Keep chains lazy until collection is part of the required output contract.
- Use `try_fold` for fallible accumulation and explicit early termination.
- Model invalid states with enums and constructors that validate invariants.

## Cost Guard

1. Replace structural linear recursion with an iterator or loop.
2. If composition requires boxing, repeated cloning, or contorted lifetimes,
   descend to named generic helpers or a direct loop.
3. Remove intermediate `collect` calls unless ownership or API boundaries require
   materialization.
4. Permit a local mutable accumulator when it remains encapsulated and yields
   the clearest ownership model.
5. Preserve borrowing, consumption, drop order, short-circuiting, and error
   conversion.

## Validation Focus

Run formatting, compilation, focused tests, and Clippy when configured. Test
ownership-sensitive failure paths. Use existing benchmarks or generated-code
inspection before making hot-path zero-cost claims.