# Kotlin Profile

## Cost Model

- Derive Kotlin, JVM, multiplatform, and coroutine versions from the build.
  Backend behavior and available standard-library APIs differ by target.
- Value classes model zero/low-overhead refinements subject to boxing at
  generic, nullable, interface, and backend boundaries.
- Collection operators are eager unless using `Sequence` or `Flow`.
  Sequences add iterator/call overhead and flows add coroutine machinery;
  neither is automatically faster than a collection chain or loop.
- Kotlin's standard `Result` is exception-oriented.

## Domain Shapes

- Use sealed classes/interfaces for closed sums with exhaustive `when`, data
  classes with `val` for products, and value classes or private constructors
  for refinements. Avoid nullable-property state bags: one sealed variant
  per valid state.
- Put validation in one `parse`/`of` factory. Keep refined constructors
  private; ensure serializers and reflection cannot bypass the invariant
  unnoticed.
- Use nullable values for ordinary absence and a sealed success/failure type
  for expected typed errors. Avoid `!!`, unchecked casts, and
  exception-based branch control in the functional core.
- Use pure extension/top-level functions and `map`, `filter`, `mapNotNull`,
  `fold`, `any`, `all`, `firstOrNull`, and `associate` when they match the
  algebra. Use `Sequence` only for a beneficial lazy multi-stage traversal;
  use a loop for measured hot paths or complex short-circuit/resource logic.

## Effects

- Use `coroutineScope`/`supervisorScope`, `async`, and `awaitAll` only when
  the coroutine dependency and project conventions support them. Preserve
  structured cancellation and dispatcher choice. Independent effects may use
  bounded sibling `async`; dependent effects remain sequential. Do not catch
  `CancellationException` as an ordinary failure.
- Use `use` for closeable resources and `try/finally` for non-closeable
  cleanup. Bound channels, flows, retries, and fan-out; choose
  buffer/conflation semantics explicitly.
- Keep platform I/O and mutable framework objects at adapters around pure
  domain values. Preserve transaction context, dispatcher/thread-local
  context, logging, and tracing across suspend boundaries.

## Teaching Example

<example for="teaching" language="kotlin">
<![CDATA[
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
]]></example>

Taste: private value-class construction refines the integer, the sealed
result names expected failure, and exhaustive `when` eliminates both states.
Check boxing on the actual backend before calling the value class zero-cost.

## Cost Guard

1. Replace deep recursion with collection operators, sequences, or
   iteration.
2. Compare eager intermediates with sequence/coroutine overhead and a fused
   loop using representative data; do not infer speed from laziness.
3. Avoid boxing-heavy generic/value-class paths and repeated immutable
   copying in measured hot code.
4. Keep inline/higher-order APIs readable; inspect code size and non-local
   return behavior before adding `inline` as an optimization.
5. Preserve structured cancellation, dispatcher, flow backpressure, and
   exception semantics.

## Validation

Build every relevant target with the configured Kotlin version. Run
formatting and static analysis. Test every sealed variant, null boundary,
factory rejection, cancellation/cleanup path, flow buffering behavior, and
Java interop edge. Benchmark the actual backend before claiming sequence or
value-class gains.
