# JavaScript Profile

ES6+. React code: `react` loads beside this profile.

## Cost Model

- Assume broad ES6 availability. Do not rely on portable tail-call
  optimization.
- JIT engines favor stable, flat object shapes and native arrays. Deep
  immutable wrappers and inconsistent property layouts can inhibit
  optimization, make debugging opaque.
- `filter().map()` creates intermediate array; callbacks and captured
  closures may allocate. Matters only when scale or measurement makes it
  material.
- Refactors can change `this`, sparse-array behavior, identity, thrown-error
  timing, promise/microtask order.

## Domain Shapes

- JavaScript cannot statically close sum type. Stable discriminant fields,
  factories, module-private constructors, total eliminator functions enforce
  protocol at runtime.
- Expected absence: `null` only when project uses it consistently. Expected
  failure: prefer flat frozen `{ tag, value/error }` result object over
  exceptions inside pure core, and plain tagged result objects project
  already uses over custom `Pipe`, `Map`, `Option`, or immutable-wrapper
  frameworks.
- `const`, replacement values, flat stable objects. `Object.freeze` is
  shallow: prefer fresh flat values and disciplined ownership; never
  recursively freeze hot object graphs without evidence.
- Native array and iterator primitives with curried predicates/projectors.
  Prefer `some`/`every`/`find` and native aggregation where available.

## Effects

- Promises and `async`/`await` are native effect sequencing. Sequential
  `await`, `Promise.all`, `Promise.allSettled` are different algebras:
  `Promise.all` for independent work, sequential `await` for dependent work.
  Bound fan-out instead of creating unbounded promise array.
- Propagate `AbortSignal`; remove listeners and release resources with
  `try/finally` or native explicit-resource-management support when runtime
  target guarantees it.

## Teaching Example

```javascript
const ok = value => Object.freeze({ tag: "ok", value });
const failure = message => Object.freeze({ tag: "error", message });

const parsePort = value => {
  const port = Number(value);
  return Number.isInteger(port) && port > 0 && port <= 65535
    ? ok(port)
    : failure("invalid port");
};

const describe = result => {
  switch (result.tag) {
    case "ok": return `port ${result.value}`;
    case "error": return result.message;
    default: throw new TypeError("unknown result variant");
  }
};
```

Taste: factories admit only valid ports; tagged result makes failure data;
flat stable objects suit engine. Runtime JavaScript cannot prove no third
tag exists, so boundary validation stays mandatory.

## Cost Guard

1. Replace recursive collection traversal with native iteration.
2. Native `filter().map()` for ordinary code. Intermediate array measured as
   material: descend to one `reduce` or direct loop with pure helpers.
3. Keep output object fields present and consistently ordered where hot path
   depends on stable shapes.
4. Currying creates opaque closure towers or material allocation: named
   unary/binary helpers.
5. Preserve synchronous versus deferred effects, exact promise concurrency,
   abort propagation.

## Validation

Test empty and sparse arrays, object identity, mutation visibility,
exception timing, promise ordering, representative hot-path sizes. Claim no
V8 or SpiderMonkey optimization without measurement or engine evidence.
