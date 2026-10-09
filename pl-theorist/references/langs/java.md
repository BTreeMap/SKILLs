# Java Profile

## Cost Model

- Derive Java release and runtime from build. Records, sealed types, pattern
  matching, virtual threads, structured-concurrency APIs vary by release,
  may be preview features.
- Streams lazy but may allocate pipelines, capture lambdas, box primitives,
  retain sources, hide repeated work. Parallel streams use shared execution
  model and cost accordingly.
- Java has no native general `Result`. `Optional` models return-value
  absence; usually poor taste for fields, parameters, serialization, or
  every local.
- Exceptions, interruption, resource closure, synchronization, encounter
  order are observable behavior.

## Domain Shapes

- Sealed interfaces/classes for closed sums when supported, records for
  immutable shallow products, exhaustive pattern matching where target
  release proves it. Otherwise private constructors and controlled visitor.
  Default branch can hide missing sealed variant; prefer compiler-checked
  exhaustiveness where available.
- Validate in factory or canonical constructor so every published instance
  satisfies invariant. Raw constructors inaccessible when failure expected.
- `Optional<T>` for expected return-value absence. Project-standard result
  type or small sealed success/failure hierarchy for expected domain
  failure; never smuggle failure through `null` or unchecked exceptions.
- Immutable values and defensive copies at ownership boundaries. Records do
  not freeze referenced collections.
- Streams for readable finite transformations. Prefer `mapToInt`/other
  primitive streams, `anyMatch`, `allMatch`, `findFirst`, collectors
  matching operation. Keep loop when it owns resources, requires complex
  early exit, or avoids measured allocation/boxing.

## Effects

- Try-with-resources. Preserve interruption by restoring or propagating
  interrupt per API contract; never catch and discard it.
- `CompletableFuture` or newer concurrency facilities only per project's
  established executor and Java release. Distinguish independent future
  combination (`allOf`/`thenCombine`) from dependent composition
  (`thenCompose`). Bound executor queues and fan-out.
- Preserve transaction context, thread-local/context propagation, logging,
  tracing across asynchronous boundaries.

## Teaching Example

Sample requires Java 17. Earlier configured release: private constructors
plus project's visitor/result representation; never raise language target
merely to copy syntax.

```java
sealed interface PortResult permits ValidPort, InvalidPort {}
record ValidPort(Port value) implements PortResult {}
record InvalidPort(String reason) implements PortResult {}

final class Port {
    private final int value;
    private Port(int value) { this.value = value; }

    static PortResult parse(int value) {
        return value >= 1 && value <= 65_535
            ? new ValidPort(new Port(value))
            : new InvalidPort("port out of range");
    }

    int value() { return value; }
}
```

Taste: private construction establishes invariant; sealed result makes
expected failure explicit.

## Cost Guard

1. Replace deep recursion with streams, iteration, or direct loop.
2. Inspect stream materialization, primitive boxing, captures, encounter
   order, spliterator quality, accidental repeated traversal.
3. No parallel streams for blocking I/O or latency-sensitive shared-pool
   work. Measure representative data before parallelizing.
4. Keep immutable copying proportional; persistent collections only when
   project already accepts their dependency and cost model.
5. Preserve resource scope, interruption, executor choice, exception
   aggregation.

## Validation

Build under configured Java release. Run formatters and static analysis.
Test every sealed/result variant, null boundary, resource closure,
interrupt/cancellation path, stream ordering, transaction path, async
failure. JMH or existing benchmark before making hot-path stream claims.
