# Rust Profile

## Cost Model

- No guaranteed TCO. Structural recursion unsuitable for unbounded linear
  data unless data structure or algorithm requires it and depth is bounded.
- Standard iterator adapters and `Option`/`Result` combinators usually
  compile to allocation-free loops, but "zero cost" remains claim to verify
  on hot path.
- Deep currying, captured borrows, boxed closures, trait objects can produce
  lifetime friction, dynamic dispatch, heap allocation.
- Ownership observable through consuming versus borrowing, clone behavior,
  drop order, resource lifetime.

## Domain Shapes

- Enums for closed sums, structs/tuples for products, newtypes with private
  fields plus smart constructors for refined values. Prefer standard refined
  types such as `NonZeroUsize` when they match invariant.
- `Option<T>` for absence, `Result<T, E>` for expected failure. Compose with
  combinators when chain stays clear; `?` for propagation; exhaustive
  `match` when elimination itself carries domain meaning. `map` for pure
  transformation inside `Option`/`Result`; `and_then` or `?` when next
  fallible computation depends on prior value.
- Avoid `unwrap`, indexing, `unreachable!` unless local proof is obvious and
  maintained. Encode proof in type when practical.
- Iterator adapters, chains lazy until collection is part of required output
  contract. `try_fold` for fallible accumulation and explicit early
  termination.
- Prefer generic named helpers over `Box<dyn Fn>` when static composition
  works.

## Modern Surface

Use most expressive stable syntax configured edition and MSRV permit
(`Cargo.toml` `edition` and `rust-version`, plus any `rust-toolchain.toml`),
never beyond.

- Prefer `let ... else` (stable since 1.65) for refutable bindings with
  early exit over nested `if let` pyramids.
- On edition 2024 (stabilized in Rust 1.85, February 2025): async closures
  `async |x| { ... }` stable from 1.85; let chains
  (`if let Some(a) = x && a.is_valid() && let Ok(b) = f(a)`) stable from
  1.88 on edition 2024 only, replace nested conditional ladders.
- Prefer one `match` with pattern guards and bindings
  (`Some(n) if n > limit => ...`) over `if`/`else if` ladder re-testing same
  scrutinee: compiler's exhaustiveness check is payoff; guards keep each
  arm's condition adjacent to its binding.
- Use combinators stdlib already names before writing manual branches:
  `is_some_and`/`is_ok_and`, `inspect`, `map_or_else`, `unwrap_or_default`,
  map `Entry` API (`entry(k).or_insert_with(...)`), `slice::partition_point`
  for binary search by predicate, `select_nth_unstable` for selection/top-k,
  `chunk_by` for grouping runs.
- Treat standard library's collection and iterator APIs as design exemplar
  of kernel's laws: ownership-aware signatures, total return types
  (`Option`/`Result`, `Entry`), adapters that fuse.

## Data Structures

- std first: `HashMap`/`HashSet` (SipHash by default, resistant to collision
  flooding on untrusted keys), `BTreeMap`/`BTreeSet` for ordered iteration
  and `range` queries, `BinaryHeap` for priority scheduling (max-heap; wrap
  keys in `std::cmp::Reverse` for min-heap), `VecDeque` for queues and
  monotonic-window algorithms.
- Maintained crates when std lacks shape, justified against repository's
  dependency policy: `rayon` (work-stealing data parallelism; `par_iter` for
  folds whose operation is associative), `aho-corasick` for many-pattern
  search, `regex` (guaranteed linear-time scanning, no backtracking),
  `indexmap` for insertion-ordered maps, `lru`/`moka`/ `quick_cache` for
  caches, `petgraph` for graphs. Verify candidate crate currently maintained
  before adopting it.

## Effects

- Rely on ownership and `Drop` for resource safety; hold no blocking guards
  or borrows across `.await` unless API explicitly supports it.
- Join independent async work only through established runtime's bounded,
  cancellation-aware facility. Scope spawned tasks with runtime's
  established mechanism, propagate cancellation, bound channels/fan-out.
  Dropping future is cancellation only where future and runtime document
  cancellation safety.
- `?` short-circuits but does not roll back prior effects; preserve
  transaction and retry semantics around it.

## Teaching Example

```rust
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
```

Taste: private newtype makes zero unrepresentable after construction;
`Option` models missing configuration, `Result` invalid configuration; no
allocation, dynamic dispatch, or partial unwrap required.

## Cost Guard

1. Replace structural linear recursion with iterator or loop.
2. Composition requires boxing, repeated cloning, or contorted lifetimes:
   descend to named generic helpers or direct loop.
3. Remove intermediate `collect` calls unless ownership or API boundaries
   require materialization.
4. Permit local mutable accumulator when it stays encapsulated and yields
   clearest ownership model.
5. Preserve borrowing, consumption, drop order, short-circuiting, error
   conversion, cancellation safety, bounded channels, lock lifetimes, all
   effects performed before `?` returns.

## Validation

Run Clippy when configured. Test ownership-sensitive failure paths. Use
existing benchmarks or generated-code inspection before making hot-path
zero-cost claims.
