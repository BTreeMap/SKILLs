# Haskell Runtime Profile

## Disclosed Constraints

- **Laziness can retain memory.** A seemingly elegant composition may build
  thunks or retain an input spine, causing a space leak.
- **Strictness is a cost decision.** Accumulation often needs a strict fold or
  strict data field; forcing evaluation too early can change productivity.
- **Fusion is not a guarantee.** List and stream fusion depend on the exact
  operations, optimization settings, and types in use.
- **Effects remain ordered.** `IO`, resource management, exceptions, and
  concurrency must preserve their existing operational contract.

## Preferred Shapes

- Use algebraic data types, total pattern matching, and pure functions by
  default.
- Use `foldl'`, strict accumulators, strict fields, or an appropriate streaming
  library when accumulation would otherwise retain thunks.
- Prefer existing project abstractions for effects and streams; do not replace
  a simple function with a new transformer stack merely to appear abstract.
- Keep partial functions out of exported paths unless the contract proves their
  precondition.

## Cost Guard and Fallback

1. If a lazy traversal risks retaining input or building thunks, introduce the
   narrowest necessary strictness or a streaming fold.
2. If a point-free expression hides evaluation order or resource lifetime, use
   named arguments and an explicit binding.
3. If a nested abstraction stack obscures inferred types or profiling, simplify
   to the existing base abstraction or a direct recursive worker with a strict
   accumulator.
4. If the path is performance-sensitive, require profiling evidence before
   asserting fusion or allocation behavior.

## Validation Focus

Run the project's build and focused tests. Use existing profiler settings for
space-sensitive code and test both finite and potentially infinite producers
where laziness is part of the contract.
