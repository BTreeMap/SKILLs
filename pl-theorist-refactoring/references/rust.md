# Rust Cost Model

## Disclosed Constraints

- No guaranteed TCO. Structural recursion is unsuitable for unbounded linear
  data unless the data structure or algorithm requires it and depth is bounded.
- Standard iterator adapters and `Option`/`Result` combinators usually compile
  to allocation-free loops, but “zero cost” remains a claim to verify on a hot
  path.
- Deep currying, captured borrows, boxed closures, and trait objects can produce
  lifetime friction, dynamic dispatch, or heap allocation.
- Ownership is observable through consuming versus borrowing, clone behavior,
  drop order, and resource lifetime.

## Preferred FP Shapes

- Use iterator adapters, enums, exhaustive matching, `Option`/`Result`
  combinators, `?`, and `async`/`await`.
- Prefer generic named helpers over `Box<dyn Fn>` when static composition works.
- Keep chains lazy until collection is part of the required output contract.
- Use `try_fold` for fallible accumulation and explicit early termination.
- Model invalid states with enums and constructors that validate invariants.

## Domain and Effect Constraints

- Use enums for closed sums, structs/tuples for products, and newtypes with
  private fields plus smart constructors for refined values. Prefer standard
  refined types such as `NonZeroUsize` when they match the invariant.
- Use `Option<T>` for absence and `Result<T, E>` for expected failure. Compose
  with combinators when the chain stays clear; use `?` for propagation and
  exhaustive `match` when elimination itself carries domain meaning.
- Use `map` for a pure transformation inside `Option`/`Result` and `and_then` or
  `?` when the next fallible computation depends on the prior value. Join
  independent async work only through the established runtime's bounded,
  cancellation-aware facility.
- Avoid `unwrap`, indexing, and `unreachable!` unless a local proof is obvious
  and maintained. Encode the proof in a type when practical.
- Rely on ownership and `Drop` for resource safety; do not hold blocking guards
  or borrows across `.await` unless the API explicitly supports it.
- Scope spawned tasks with the runtime's established mechanism, propagate
  cancellation, and bound channels/fan-out. Dropping a future is cancellation
  only where the future and runtime document cancellation safety.
- Preserve transaction and retry semantics; `?` short-circuits but does not roll
  back prior effects.

## Teaching Example

<teaching_example language="rust"><![CDATA[
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct Port(u16);

#[derive(Debug, PartialEq, Eq)]
enum PortError { OutOfRange }

impl Port {
    fn new(value: u16) -> Result<Self, PortError> {
        (value != 0).then_some(Self(value)).ok_or(PortError::OutOfRange)
    }

    fn get(self) -> u16 { self.0 }
}

fn configured_port(raw: Option<u16>) -> Result<Port, PortError> {
    raw.map_or_else(|| Port::new(8080), Port::new)
}
]]></teaching_example>

Taste: a private newtype makes zero unrepresentable after construction;
`Option` models missing configuration and `Result` models invalid configuration;
no allocation, dynamic dispatch, or partial unwrap is required.

## Cost Guard

1. Replace structural linear recursion with an iterator or loop.
2. If composition requires boxing, repeated cloning, or contorted lifetimes,
   descend to named generic helpers or a direct loop.
3. Remove intermediate `collect` calls unless ownership or API boundaries require
   materialization.
4. Permit a local mutable accumulator when it remains encapsulated and yields
   the clearest ownership model.
5. Preserve borrowing, consumption, drop order, short-circuiting, and error
   conversion.
6. Preserve cancellation safety, bounded channels, lock lifetimes, transaction
  scope, and all effects performed before `?` returns.

## Validation Focus

Run formatting, compilation, focused tests, and Clippy when configured. Test
ownership-sensitive failure paths. Use existing benchmarks or generated-code
inspection before making hot-path zero-cost claims.