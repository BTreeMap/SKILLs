# JavaScript Runtime Profile

## Disclosed Constraints

- **No portable tail-call optimization.** Do not express unbounded traversals
  as recursive calls.
- **Object-shape sensitivity.** Deep wrapper objects and inconsistent property
  layouts can obstruct JIT optimization and increase allocation pressure.
- **Intermediate arrays and closures.** Native array methods are idiomatic, but
  a chain can allocate arrays and callback closures that matter on hot paths.
- **Dynamic semantics.** A refactor can change `this`, sparse-array behavior,
  mutation visibility, microtask order, and thrown-error timing.

## Preferred Shapes

- Use native `Array` and iterator APIs with named predicates/projectors for
  ordinary collection code.
- Return flat, consistently shaped objects; avoid bespoke `Pipe`, `Map`, and
  wrapper-object frameworks in performance-sensitive paths.
- Use `const`, pure helpers, and immutable replacement values where callers do
  not rely on identity or mutation.
- Use discriminated object fields and explicit result values when they clarify
  a state machine, without introducing a runtime abstraction library.

## Cost Guard and Fallback

1. Replace recursive collection traversal with iteration.
2. If native `filter` then `map` creates unacceptable intermediate arrays, use
   one native reducer or an explicit single-pass loop with a pure projection.
3. If a closure, wrapper object, or changed object shape is on a measured hot
   path, use a flat native representation or a direct loop.
4. Preserve eager mutation and callback timing when callers or event handlers
   can observe it; do not make a synchronous path lazy by accident.

## Validation Focus

Test empty and sparse arrays, object identity, error timing, asynchronous
ordering, and performance with representative input sizes when the path is hot.
