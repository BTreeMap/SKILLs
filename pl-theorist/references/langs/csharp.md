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

## Domain and Effect Constraints

- C# has records and pattern matching but no general native discriminated union.
  Use a sealed record hierarchy or an established project union type; recognize
  that a discard arm can hide a newly added variant.
- Use private constructors plus `TryParse`/factory methods for refined values.
  Use nullable values for incidental absence under enabled nullability analysis;
  use an established `Option` only when the project already standardizes it.
- Use an established `Result` type for expected domain failures when available;
  otherwise use a small closed result hierarchy or documented `TryX` pattern.
  Do not add exceptions as ordinary branch control.
- Treat records and immutable collections according to actual ownership; record
  properties can still reference mutable objects.
- Use `Task.WhenAll` for bounded independent work and sequential `await` for
  dependent work. Propagate `CancellationToken` through every cancellable call.
- Scope `IDisposable`/`IAsyncDisposable` with `using`/`await using`. Preserve
  transaction disposal, retry idempotency, and async-stream backpressure.

## Teaching Example

<teaching_example language="csharp"><![CDATA[
using System;

public sealed record Email
{
    public string Value { get; }
    private Email(string value) => Value = value;

    public static Email? TryParse(string raw)
    {
        var normalized = raw.Trim().ToLowerInvariant();
        return normalized.Contains('@') ? new Email(normalized) : null;
    }
}

public abstract record PaymentState
{
  private PaymentState() { }

    public sealed record Unpaid : PaymentState;
    public sealed record Settled(string TransactionId) : PaymentState;
}

public static class PaymentDescriptions
{
  public static string Describe(PaymentState state) => state switch
  {
    PaymentState.Unpaid => "payment required",
    PaymentState.Settled settled => $"settled: {settled.TransactionId}",
    _ => throw new ArgumentOutOfRangeException(nameof(state))
  };
}
]]></teaching_example>

Taste: construction validates `Email`, and the record hierarchy prevents
contradictory payment fields. The fallback arm is still required defensively;
C# does not prove this hierarchy exhaustively like a native sealed ADT.

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
6. Preserve disposal, bounded async fan-out, transaction scope, retry
  idempotency, and enumeration count.

## Validation Focus

Run formatting, build, analyzers, and focused tests. Test multiple enumeration,
nullability boundaries, cancellation, disposal, exception timing, and async
stream termination. Benchmark before replacing readable LINQ in a hot path.
