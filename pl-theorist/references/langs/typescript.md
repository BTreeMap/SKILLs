# TypeScript Profile

For React code, `react` loads beside this profile.

## Cost Model

- Runtime behavior is JavaScript: no portable TCO, possible intermediate
  arrays, closure allocation, identity semantics, and object-shape
  sensitivity.
- Discriminated unions, `readonly`, generics, and exhaustive checks are
  erased. They can remove representable invalid states at zero runtime
  representation cost, but they cannot validate unknown data.
- Deep conditional types and abstraction-heavy inference can impose
  substantial compiler and editor cost even when runtime cost is zero.
- Runtime `Option`/`Either` wrappers add values and allocations when a
  native discriminated union would suffice.

## Domain Shapes

- Model mutually exclusive states with `readonly` discriminated unions,
  products for fields that coexist, and no optional-property bags whose
  combinations include impossible states.
- Treat exhaustive `switch` plus a `never` assertion, consistent with
  repository conventions, as the elimination proof for eliminators and
  transition functions. Runtime decoders must reject unknown tags before the
  value enters the domain.
- Use branded/opaque types when they enforce a domain boundary without
  forcing unsafe assertions through the codebase. Keep brands and union
  constructors module-private; a brand assertion belongs only inside the
  validating smart constructor, never at call sites.
- Prefer an explicit `Option`/`Result` discriminated union when absence or
  failure is central to composition. Use `T | undefined` for local
  incidental absence; do not mix representations in one domain flow.
- Use native arrays and project-standard result unions. Use `map`, `filter`,
  `some`, `every`, `find`, and `reduce` deliberately.
- Keep complex conditional types off broad public surfaces when named unions
  provide better compiler performance and diagnostics.

## Effects

- Use promises and `async`/`await`: `Promise.all` for independent bounded
  work, sequential `await` for dependent work.
- Propagate `AbortSignal` and release listeners/resources.

## Teaching Example

<example for="teaching" language="typescript">
<![CDATA[
declare const portBrand: unique symbol;
type Port = number & { readonly [portBrand]: true };
type Result<T, E> =
  | { readonly tag: "ok"; readonly value: T }
  | { readonly tag: "error"; readonly error: E };

const parsePort = (n: number): Result<Port, string> =>
  Number.isInteger(n) && n > 0 && n <= 65535
    ? { tag: "ok", value: n as Port }
    : { tag: "error", error: "invalid port" };

const foldResult = <T, E, R>(
  result: Result<T, E>,
  onOk: (value: T) => R,
  onError: (error: E) => R,
): R => result.tag === "ok" ? onOk(result.value) : onError(result.error);
]]></example>

Taste: the sole assertion is inside validation, `Result` exposes expected
failure, and consumers eliminate both variants.

## Cost Guard

1. Replace unbounded recursion with iteration or native collection
   operations.
2. Replace a runtime monadic wrapper with an erased/native union when it
   carries no behavior unavailable from functions.
3. If a callback chain creates measured intermediate cost, fuse one level.
4. If a type-level encoding degrades compiler responsiveness or diagnostics,
   simplify to explicit named unions and functions.
5. Preserve JavaScript evaluation, identity, and async ordering semantics,
   abort propagation, and runtime decoding at external boundaries.

## Validation

Run typechecking and focused runtime tests. Test every union variant,
invalid external input, exhaustive branches, and async
rejection/cancellation behavior. A passing typecheck proves internal
consistency only.
