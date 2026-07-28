# C# Cost Model

## Disclosed Constraints

- LINQ operators differ: some stream, some buffer, and repeated enumeration can
  repeat work, effects, or I/O.
- Delegates, captures, iterator state machines, boxing, and interface-based
  enumeration can allocate on measured hot paths.
- Records and pattern matching improve domain modeling, but records containing
  references are not deeply immutable and external values still need validation.
- Tasks, async streams, cancellation tokens, synchronization context, exceptions,
  and disposal have observable sequencing and lifetime semantics.

## Preferred FP Shapes

- Use LINQ heavily for ordinary collection transformations: `Where`, `Select`,
  `SelectMany`, `Aggregate`, `Any`, `All`, and native numeric aggregation.
- Use records, readonly values, closed project-standard union representations,
  and exhaustive pattern matching for valid-state modeling.
- Use nullable/reference option conventions and result types already established
  by the repository; avoid a parallel monad hierarchy.
- Use `Task`, `ValueTask` only when justified, `IAsyncEnumerable`, and
  `await using` while preserving cancellation and disposal.
- Prefer static lambdas or pure static helpers when captures are unnecessary.

## Cost Guard

1. Identify streaming, buffering, materialization, and enumeration count for each
   LINQ pipeline.
2. Materialize once only when reuse or the API contract requires a collection.
3. If measured delegate/iterator/boxing cost is material, use static helpers,
   spans where semantically valid, or one direct loop.
4. Never replace explicit resource scope with a deferred enumerable that can
   outlive its resource.
5. Preserve cancellation propagation, exception timing, context behavior, and
   async concurrency.

## Validation Focus

Run formatting, build, analyzers, and focused tests. Test multiple enumeration,
nullability boundaries, cancellation, disposal, exception timing, and async
stream termination. Benchmark before replacing readable LINQ in a hot path.