# JavaScript Profile

ES6+. For React code, `react` loads beside this profile.

## Cost Model

- Assume broad ES6 availability. Do not rely on portable tail-call
  optimization.
- JIT engines favor stable, flat object shapes and native arrays. Deep
  immutable wrappers and inconsistent property layouts can inhibit
  optimization and make debugging opaque.
- `filter().map()` creates an intermediate array; callbacks and captured
  closures may allocate. This matters only when scale or measurement makes
  it material.
- Refactors can change `this`, sparse-array behavior, identity, thrown-error
  timing, and promise/microtask order.

## Domain Shapes

- JavaScript cannot statically close a sum type. Use stable discriminant
  fields, factories, module-private constructors, and total eliminator
  functions to enforce the protocol at runtime.
- Represent expected absence with `null` only when the project uses it
  consistently. For expected failure, prefer a flat frozen
  `{ tag, value/error }` result object over exceptions inside the pure core,
  and plain tagged result objects the project already uses over custom
  `Pipe`, `Map`, `Option`, or immutable-wrapper frameworks.
- Use `const`, replacement values, and flat stable objects. `Object.freeze`
  is shallow: prefer fresh flat values and disciplined ownership; do not
  recursively freeze hot object graphs without evidence.
- Use native array and iterator primitives with curried
  predicates/projectors. Prefer `some`/`every`/`find` and native aggregation
  where available.

## Effects

- Promises and `async`/`await` are the native effect sequencing. Sequential
  `await`, `Promise.all`, and `Promise.allSettled` are different algebras:
  use `Promise.all` for independent work and sequential `await` for
  dependent work. Bound fan-out rather than creating an unbounded promise
  array.
- Propagate `AbortSignal`; remove listeners and release resources with
  `try/finally` or native explicit-resource-management support when the
  runtime target guarantees it.

## Teaching Example

<example for="teaching" language="javascript">
<![CDATA[
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
]]></example>

Taste: factories admit only valid ports, the tagged result makes failure
data, and flat stable objects suit the engine. Runtime JavaScript cannot
prove that no third tag exists, so boundary validation remains mandatory.

## Cost Guard

1. Replace recursive collection traversal with native iteration.
2. Use native `filter().map()` for ordinary code. If the intermediate array
   is measured as material, descend to one `reduce` or a direct loop with
   pure helpers.
3. Keep output object fields present and consistently ordered where the hot
   path depends on stable shapes.
4. If currying creates opaque closure towers or material allocation, use
   named unary/binary helpers.
5. Preserve synchronous versus deferred effects, exact promise concurrency,
   and abort propagation.

## Validation

Test empty and sparse arrays, object identity, mutation visibility,
exception timing, promise ordering, and representative hot-path sizes. Do
not claim V8 or SpiderMonkey optimization without measurement or engine
evidence.
