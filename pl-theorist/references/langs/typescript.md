# TypeScript Profile

React code: `react` loads beside this profile.

## Cost Model

- Runtime behavior is JavaScript: no portable TCO, possible intermediate
  arrays, closure allocation, identity semantics, object-shape sensitivity.
- Discriminated unions, `readonly`, generics, exhaustive checks are erased.
  They can remove representable invalid states at zero runtime
  representation cost, but cannot validate unknown data.
- Deep conditional types and abstraction-heavy inference can impose
  substantial compiler and editor cost even when runtime cost is zero.
- Runtime `Option`/`Either` wrappers add values and allocations when native
  discriminated union would suffice.

## Domain Shapes

- Model mutually exclusive states with `readonly` discriminated unions,
  products for coexisting fields, no optional-property bags whose
  combinations include impossible states.
- Exhaustive `switch` plus `never` assertion, consistent with repository
  conventions, is elimination proof for eliminators and transition
  functions. Runtime decoders must reject unknown tags before value enters
  domain.
- Branded/opaque types when they enforce domain boundary without forcing
  unsafe assertions through codebase. Keep brands and union constructors
  module-private; brand assertion belongs only inside validating smart
  constructor, never at call sites.
- Prefer explicit `Option`/`Result` discriminated union when absence or
  failure is central to composition. `T | undefined` for local incidental
  absence; never mix representations in one domain flow.
- Native arrays and project-standard result unions. Use `map`, `filter`,
  `some`, `every`, `find`, `reduce` deliberately.
- Keep complex conditional types off broad public surfaces when named unions
  give better compiler performance and diagnostics.

## Effects

- Promises and `async`/`await`: `Promise.all` for independent bounded work,
  sequential `await` for dependent work.
- Propagate `AbortSignal`; release listeners/resources.

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

Taste: sole assertion is inside validation; `Result` exposes expected
failure; consumers eliminate both variants.

## Cost Guard

1. Replace unbounded recursion with iteration or native collection
   operations.
2. Replace runtime monadic wrapper with erased/native union when it carries
   no behavior unavailable from functions.
3. Callback chain creates measured intermediate cost: fuse one level.
4. Type-level encoding degrades compiler responsiveness or diagnostics:
   simplify to explicit named unions and functions.
5. Preserve JavaScript evaluation, identity, async ordering semantics, abort
   propagation, runtime decoding at external boundaries.

## Validation

Run typechecking and focused runtime tests. Test every union variant,
invalid external input, exhaustive branches, async rejection/cancellation
behavior. Passing typecheck proves internal consistency only.
