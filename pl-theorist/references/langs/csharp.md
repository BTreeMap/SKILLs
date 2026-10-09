# C# Profile

## Cost Model

- LINQ operators differ: some stream, some buffer; repeated enumeration can
  repeat work, effects, or I/O.
- Delegates, captures, iterator state machines, boxing, interface-based
  enumeration can allocate on measured hot paths.
- Records containing references not deeply immutable.
- Tasks, async streams, cancellation tokens, synchronization context,
  exceptions, disposal have observable sequencing and lifetime semantics.

## Domain Shapes

- C# has records and pattern matching but no general native discriminated
  union. Use sealed record hierarchy or established project union type with
  exhaustive pattern matching; discard arm can hide newly added variant.
- Private constructors plus `TryParse`/factory methods for refined values,
  readonly values. Treat records and immutable collections per actual
  ownership.
- Nullable values for incidental absence under enabled nullability analysis;
  established `Option` only when project already standardizes it.
  Established `Result` type for expected domain failures when available;
  otherwise small closed result hierarchy or documented `TryX` pattern. No
  exceptions as ordinary branch control, no parallel monad hierarchy.
- LINQ heavily for ordinary collection transformations: `Where`, `Select`,
  `SelectMany`, `Aggregate`, `Any`, `All`, native numeric aggregation.
  Prefer static lambdas or pure static helpers when captures unnecessary.

## Effects

- `Task`, `ValueTask` only when justified, `IAsyncEnumerable`.
  `Task.WhenAll` for bounded independent work, sequential `await` for
  dependent work. Propagate `CancellationToken` through every cancellable
  call.
- Scope `IDisposable`/`IAsyncDisposable` with `using`/`await using`.
  Preserve transaction disposal and async-stream backpressure.

## Teaching Example

<example for="teaching" language="csharp">
<![CDATA[
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
]]></example>

Taste: construction validates `Email`; record hierarchy prevents
contradictory payment fields. Fallback arm still required defensively; C#
does not prove this hierarchy exhaustively like native sealed ADT.

## Cost Guard

1. Identify streaming, buffering, materialization, enumeration count for
   each LINQ pipeline.
2. Materialize once only when reuse or API contract requires collection.
3. Measured delegate/iterator/boxing cost material: static helpers, spans
   where semantically valid, or one direct loop.
4. Never replace explicit resource scope with deferred enumerable that can
   outlive its resource.
5. Preserve cancellation propagation, exception timing, context behavior,
   async concurrency, disposal, enumeration count.

## Validation

Run formatting, build, analyzers. Test multiple enumeration, nullability
boundaries, cancellation, disposal, exception timing, async stream
termination. Benchmark before replacing readable LINQ in hot path.
