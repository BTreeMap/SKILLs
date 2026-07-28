# C# Runtime Profile

## Disclosed Constraints

- **LINQ execution varies.** Some operators stream, others buffer; multiple
  enumeration can repeat work and side effects.
- **Delegates and captures allocate.** Closures, iterator state machines, and
  interface-based enumeration can matter in measured hot paths.
- **Records and pattern matching clarify domains.** They do not replace runtime
  validation, and reference-containing records are not deeply immutable.
- **Async behavior is observable.** Refactors must preserve cancellation,
  context, exception, and disposal behavior.

## Preferred Shapes

- Use records, discriminated unions where available in local conventions, and
  exhaustive pattern matching to model closed domain states.
- Use LINQ for ordinary, readable collection code. Materialize once only when a
  collection is required or multiple traversals are intentional.
- Use pure static helpers to avoid unnecessary capture in performance-sensitive
  code.
- Keep `IDisposable`, `IAsyncDisposable`, `IEnumerable`, and
  `IAsyncEnumerable` lifetimes explicit at resource boundaries.

## Cost Guard and Fallback

1. If an enumerable pipeline performs repeated traversal or unexpected
   buffering, materialize once deliberately or use a single explicit loop.
2. If delegate or iterator allocations are measured as material, use static
   helpers, spans, or a direct loop consistent with the project's target
   framework.
3. If a refactor changes deferred evaluation, preserve the original exception
   and disposal timing instead.
4. If a functional wrapper duplicates a native result or option convention,
   use the established native/project representation.

## Validation Focus

Run the repository's formatter, build, analyzer, and focused tests. Test
multiple enumeration, cancellation, disposal, exception timing, and nullability
boundaries when those behaviors apply.
