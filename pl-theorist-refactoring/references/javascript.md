# JavaScript ES6+ Cost Model

## Disclosed Constraints

- Assume broad ES6 availability. Do not rely on portable tail-call optimization.
- JIT engines favor stable, flat object shapes and native arrays. Deep immutable
  wrappers and inconsistent property layouts can inhibit optimization and make
  debugging opaque.
- `filter().map()` creates an intermediate array; callbacks and captured
  closures may allocate. This matters only when scale or measurement makes it
  material.
- Refactors can change `this`, sparse-array behavior, identity, thrown-error
  timing, and promise/microtask order.

## Preferred FP Shapes

- Use native array and iterator primitives with curried predicates/projectors.
- Use `const`, replacement values, flat stable objects, and discriminant fields.
- Use promises and `async`/`await` as native effect sequencing. Preserve
  concurrency intentionally: sequential `await`, `Promise.all`, and
  `Promise.allSettled` are different algebras.
- Prefer `some`/`every`/`find` and native aggregation where available; otherwise
  use `reduce` with a named accumulator law.
- Prefer plain tagged result objects already used by the project over custom
  `Pipe`, `Map`, `Option`, or immutable-wrapper frameworks.

## Cost Guard

1. Replace recursive collection traversal with native iteration.
2. Use native `filter().map()` for ordinary code. If the intermediate array is
   measured as material, descend to one `reduce` or a direct loop with pure
   helpers.
3. Keep output object fields present and consistently ordered where the hot path
   depends on stable shapes.
4. If currying creates opaque closure towers or material allocation, use named
   unary/binary helpers.
5. Preserve synchronous versus deferred effects and exact promise concurrency.

## Validation Focus

Test empty and sparse arrays, object identity, mutation visibility, exception
timing, promise ordering, and representative hot-path sizes. Do not claim V8 or
SpiderMonkey optimization without measurement or engine evidence.