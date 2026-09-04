# Kotlin Cost Model

## Disclosed Constraints

- Derive Kotlin, JVM, multiplatform, and coroutine versions from the build.
  Backend behavior and available standard-library APIs differ by target.
- Sealed classes/interfaces model closed sums; data classes model products; value
  classes model zero/low-overhead refinements subject to boxing at generic,
  nullable, interface, and backend boundaries.
- Collection operators are eager unless using `Sequence` or `Flow`. Sequences add
  iterator/call overhead and flows add coroutine machinery; neither is
  automatically faster than a collection chain or loop.
- Kotlin's standard `Result` is exception-oriented. Prefer an explicit sealed
  domain result when typed expected errors matter. Nullable `T?` models absence.

## Preferred FP Shapes

- Use sealed variants plus exhaustive `when`, data classes with `val`, value
  classes/private constructors for refinements, and pure extension/top-level
  functions.
- Use `map`, `filter`, `mapNotNull`, `fold`, `any`, `all`, `firstOrNull`, and
  `associate` when they match the algebra. Use `Sequence` only for a beneficial
  lazy multi-stage traversal; use a loop for measured hot paths or complex
  short-circuit/resource logic.
- Use nullable values for ordinary absence and a sealed success/failure type for
  expected typed errors. Avoid `!!`, unchecked casts, and exception-based branch
  control in the functional core.
- Use `coroutineScope`/`supervisorScope`, `async`, and `awaitAll` only when the
  coroutine dependency and project conventions support them. Preserve structured
  cancellation and dispatcher choice.
- Keep platform I/O and mutable framework objects at adapters around pure domain
  values.

## Domain and Effect Constraints

- Put validation in one `parse`/`of` factory. Keep refined constructors private;
  ensure serializers and reflection cannot bypass the invariant unnoticed.
- Avoid nullable-property state bags. Use one sealed variant per valid state and
  exhaustive `when` for elimination.
- Independent effects may use bounded sibling `async`; dependent effects remain
  sequential. Do not catch `CancellationException` as an ordinary failure.
- Use `use` for closeable resources and `try/finally` for non-closeable cleanup.
  Bound channels, flows, retries, and fan-out; choose buffer/conflation semantics
  explicitly.
- Preserve transaction context, dispatcher/thread-local context, idempotency,
  logging, and tracing across suspend boundaries.

## Teaching Example

<teaching-example language="kotlin">
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
]]></teaching-example>

Taste: private value-class construction refines the integer, the sealed result
names expected failure, and exhaustive `when` eliminates both states. Check
boxing on the actual backend before calling the value class zero-cost.

## Cost Guard

1. Replace deep recursion with collection operators, sequences, or iteration.
2. Compare eager intermediates with sequence/coroutine overhead and a fused loop
   using representative data; do not infer speed from laziness.
3. Avoid boxing-heavy generic/value-class paths and repeated immutable copying in
   measured hot code.
4. Keep inline/higher-order APIs readable; inspect code size and non-local return
   behavior before adding `inline` as an optimization.
5. Preserve structured cancellation, dispatcher, resource, flow backpressure,
   transaction, and exception semantics.

## Validation Focus

Build every relevant target with the configured Kotlin version. Run formatting,
static analysis, and focused tests. Test every sealed variant, null boundary,
factory rejection, cancellation/cleanup path, flow buffering behavior, and Java
interop edge. Benchmark the actual backend before claiming sequence or value-
class gains.
