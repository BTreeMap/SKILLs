# Rust Cost Model

## Disclosed Constraints

- No guaranteed TCO. Structural recursion is unsuitable for unbounded linear
  data unless the data structure or algorithm requires it and depth is bounded.
- Standard iterator adapters and `Option`/`Result` combinators usually compile
  to allocation-free loops, but "zero cost" remains a claim to verify on a hot
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

## Modern Surface

Detect the configured edition and MSRV from `Cargo.toml` (`edition`,
`rust-version`) and any `rust-toolchain.toml`; use the most expressive stable
syntax they permit, never beyond.

- Prefer `let ... else` (stable since 1.65) for refutable bindings with early
  exit over nested `if let` pyramids.
- On edition 2024 (stabilized in Rust 1.85, February 2025): async closures
  `async |x| { ... }` are stable from 1.85; let chains
  (`if let Some(a) = x && a.is_valid() && let Ok(b) = f(a)`) are stable from
  1.88 on edition 2024 only, and replace nested conditional ladders.
- Prefer one `match` with pattern guards and bindings
  (`Some(n) if n > limit => ...`) over an `if`/`else if` ladder re-testing the
  same scrutinee: the compiler's exhaustiveness check is the payoff, and
  guards keep each arm's condition adjacent to its binding.
- Use the combinators the stdlib already names before writing manual
  branches: `is_some_and`/`is_ok_and`, `inspect`, `map_or_else`,
  `unwrap_or_default`, the map `Entry` API (`entry(k).or_insert_with(...)`),
  `slice::partition_point` for binary search by predicate,
  `select_nth_unstable` for selection/top-k, `chunk_by` for grouping runs.
- Treat the standard library's collection and iterator APIs as the design
  exemplar the kernel's laws describe: ownership-aware signatures, total
  return types (`Option`/`Result`, `Entry`), and adapters that fuse. When
  designing your own API, imitate that shape.

## Data Structures

- std first: `HashMap`/`HashSet` (SipHash by default, resistant to collision
  flooding on untrusted keys), `BTreeMap`/`BTreeSet` for ordered iteration
  and `range` queries, `BinaryHeap` for priority scheduling (max-heap; wrap
  keys in `std::cmp::Reverse` for a min-heap), `VecDeque` for queues and
  monotonic-window algorithms.
- Maintained crates when std lacks the shape, justified against the
  repository's dependency policy: `rayon` (work-stealing data parallelism;
  `par_iter` for folds whose operation is associative), `aho-corasick` for
  many-pattern search, `regex` (guaranteed linear-time scanning, no
  backtracking), `indexmap` for insertion-ordered maps, `lru`/`moka`/
  `quick_cache` for caches, `petgraph` for graphs. Verify a candidate crate
  is currently maintained before adopting it.

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

<example for="teaching" language="rust">
<![CDATA[
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
]]></example>

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
