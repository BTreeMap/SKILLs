# Rust Runtime Profile

## Disclosed Constraints

- **No guaranteed tail-call optimization.** Avoid relying on recursive
  traversal for unbounded inputs.
- **Zero-cost iterator potential.** Standard iterator adapters and `Option` /
  `Result` combinators commonly optimize to efficient loops without allocation.
- **Borrow and lifetime friction.** Deep currying, captured borrows, and
  `Box<dyn Fn>` can complicate lifetimes or introduce dynamic dispatch and heap
  allocation.
- **Ownership is behavior.** A refactor must preserve borrowing, consuming,
  cloning, drop order, and error propagation.

## Preferred Shapes

- Prefer standard iterator adapters, `Option` / `Result` combinators, enums,
  pattern matching, and generic functions for data transformations.
- Keep closures short and non-escaping when possible; use named generic helpers
  when captures make types or lifetimes obscure.
- Use `collect` only when a collection is part of the required contract;
  otherwise maintain a lazy iterator chain.
- Use `try_fold` or a loop when fallible accumulation and early exit need an
  explicit invariant.

## Cost Guard and Fallback

1. Replace structural recursion with an iterator or an explicit loop.
2. If iterator composition needs boxed closures, complex lifetime plumbing, or
   repeated clones, drop to a named helper or direct loop.
3. If a chain collects intermediates unnecessarily, combine adapters or use a
   single pass.
4. If mutation simplifies ownership without leaking partial state, use a local
   mutable accumulator inside a narrowly scoped function.

## Validation Focus

Run formatting, compilation, and focused tests. Inspect clippy findings if it
is part of the project. Test ownership-sensitive error paths and avoid claiming
zero cost without an existing benchmark or compiler evidence.
