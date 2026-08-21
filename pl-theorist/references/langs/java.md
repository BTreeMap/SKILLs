# Java Cost Model

## Disclosed Constraints

- Derive the Java release and runtime from the build. Records, sealed types,
  pattern matching, virtual threads, and structured-concurrency APIs vary by
  release and may be preview features.
- Streams are lazy but may allocate pipelines, capture lambdas, box primitives,
  retain sources, and hide repeated work. Parallel streams use a shared execution
  model and are not a free performance switch.
- Java has no native general `Result`. `Optional` models return-value absence; it
  is usually poor taste for fields, parameters, serialization, or every local.
- Exceptions, interruption, resource closure, synchronization, and encounter
  order are observable behavior.

## Preferred FP Shapes

- Use sealed interfaces/classes for closed sums when supported, records for
  immutable shallow products, and exhaustive pattern matching where the target
  release proves it. Otherwise use private constructors and a controlled visitor.
- Use `Optional<T>` for expected return-value absence. Use a project-standard
  result type or a small sealed success/failure hierarchy for expected domain
  failure; do not smuggle failure through `null` or unchecked exceptions.
- Use streams for readable finite transformations. Prefer `mapToInt`/other
  primitive streams, `anyMatch`, `allMatch`, `findFirst`, and collectors matching
  the operation. Keep a loop when it owns resources, requires complex early exit,
  or avoids measured allocation/boxing.
- Use immutable values and defensive copies at ownership boundaries. Records do
  not freeze referenced collections.
- Use `CompletableFuture` or newer concurrency facilities only according to the
  project's established executor and Java release.

## Domain and Effect Constraints

- Validate in a factory or canonical constructor so every published instance
  satisfies its invariant. Keep raw constructors inaccessible when failure is
  expected.
- Make success/failure and state variants explicit. A default branch can hide a
  missing sealed variant; prefer compiler-checked exhaustiveness where available.
- Use try-with-resources. Preserve interruption by restoring or propagating the
  interrupt according to the API contract; do not catch and discard it.
- Distinguish independent future combination (`allOf`/`thenCombine`) from
  dependent composition (`thenCompose`). Bound executor queues and fan-out.
- Preserve transaction context, retry idempotency, thread-local/context
  propagation, logging, and tracing across asynchronous boundaries.

## Teaching Example

This sample requires Java 17. On an earlier configured release, use private
constructors plus the project's visitor/result representation; do not raise the
language target merely to copy the syntax.

<teaching_example language="java"><![CDATA[
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
]]></teaching_example>

Taste: private construction establishes the invariant, and a sealed result makes
expected failure explicit. The release constraint above applies.

## Cost Guard

1. Replace deep recursion with streams, iteration, or a direct loop.
2. Inspect stream materialization, primitive boxing, captures, encounter order,
   spliterator quality, and accidental repeated traversal.
3. Do not use parallel streams for blocking I/O or latency-sensitive shared-pool
   work. Measure representative data before parallelizing.
4. Keep immutable copying proportional; use persistent collections only when the
   project already accepts their dependency and cost model.
5. Preserve resource scope, interruption, executor choice, transaction context,
   cancellation, and exception aggregation.

## Validation Focus

Build under the configured Java release. Run formatters, static analysis, and
focused tests. Test every sealed/result variant, null boundary, resource closure,
interrupt/cancellation path, stream ordering, transaction path, and async failure.
Use JMH or an existing benchmark before making hot-path stream claims.
