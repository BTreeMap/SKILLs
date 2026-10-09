# Kotlin Profile

## Cost Model

- Derive Kotlin, JVM, multiplatform, coroutine versions from build. Backend
  behavior and available standard-library APIs differ by target.
- Value classes model zero/low-overhead refinements subject to boxing at
  generic, nullable, interface, backend boundaries.
- Collection operators eager unless using `Sequence` or `Flow`. Sequences
  add iterator/call overhead, flows add coroutine machinery; neither
  automatically faster than collection chain or loop.
- Kotlin's standard `Result` is exception-oriented.

## Domain Shapes

- Sealed classes/interfaces for closed sums with exhaustive `when`, data
  classes with `val` for products, value classes or private constructors for
  refinements. Avoid nullable-property state bags: one sealed variant per
  valid state.
- Validation in one `parse`/`of` factory. Refined constructors private;
  ensure serializers and reflection cannot bypass invariant unnoticed.
- Nullable values for ordinary absence, sealed success/failure type for
  expected typed errors. Avoid `!!`, unchecked casts, exception-based branch
  control in functional core.
- Pure extension/top-level functions and `map`, `filter`, `mapNotNull`,
  `fold`, `any`, `all`, `firstOrNull`, `associate` when they match algebra.
  `Sequence` only for beneficial lazy multi-stage traversal; loop for
  measured hot paths or complex short-circuit/resource logic.

## Effects

- `coroutineScope`/`supervisorScope`, `async`, `awaitAll` only when
  coroutine dependency and project conventions support them. Preserve
  structured cancellation and dispatcher choice. Independent effects may use
  bounded sibling `async`; dependent effects stay sequential. Never catch
  `CancellationException` as ordinary failure.
- `use` for closeable resources, `try/finally` for non-closeable cleanup.
  Bound channels, flows, retries, fan-out; choose buffer/conflation
  semantics explicitly.
- Platform I/O and mutable framework objects at adapters around pure domain
  values. Preserve transaction context, dispatcher/thread-local context,
  logging, tracing across suspend boundaries.

## Teaching Example

```kotlin
@JvmInline
value class Port private constructor(val value: Int) {
    companion object {
        fun parse(value: Int): PortResult =
            if (value in 1..65_535) PortResult.Valid(Port(value))
            else PortResult.Invalid("port out of range")
    }
}

sealed interface PortResult {
    data class Valid(val port: Port) : PortResult
    data class Invalid(val reason: String) : PortResult
}

fun describe(result: PortResult): String = when (result) {
    is PortResult.Valid -> "port ${result.port.value}"
    is PortResult.Invalid -> result.reason
}
```

Taste: private value-class construction refines integer; sealed result names
expected failure; exhaustive `when` eliminates both states. Check boxing on
actual backend before calling value class zero-cost.

## Cost Guard

1. Replace deep recursion with collection operators, sequences, or
   iteration.
2. Compare eager intermediates with sequence/coroutine overhead and fused
   loop using representative data; never infer speed from laziness.
3. Avoid boxing-heavy generic/value-class paths and repeated immutable
   copying in measured hot code.
4. Keep inline/higher-order APIs readable; inspect code size and non-local
   return behavior before adding `inline` as optimization.
5. Preserve structured cancellation, dispatcher, flow backpressure,
   exception semantics.

## Validation

Build every relevant target with configured Kotlin version. Run formatting
and static analysis. Test every sealed variant, null boundary, factory
rejection, cancellation/cleanup path, flow buffering behavior, Java interop
edge. Benchmark actual backend before claiming sequence or value-class
gains.
