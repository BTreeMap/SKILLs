# Go Runtime Profile

## Disclosed Constraints

- **No tail-call optimization.** Do not use recursion for unbounded collection
  processing.
- **Escape and allocation risk.** Closures and interface-based higher-order
  abstractions can escape to the heap; confirm costs in a hot path instead of
  assuming they are free.
- **Idiomatic directness.** Explicit loops, simple structs, and error returns
  are usually clearer and more predictable than a generic FP framework.
- **Functional options are configuration, not purity.** Applying an option
  normally mutates a local configuration value; preserve that semantics.

## Preferred Shapes

- Keep collection transforms as direct loops with pure helper functions when
  higher-order callbacks do not improve clarity or allocation behavior.
- Use value structs, explicit error returns, and small transition functions to
  keep state changes visible.
- Use functional options for optional construction-time configuration when that
  is already an idiomatic fit; validate options before exposing the result.
- Preallocate result slices when a reliable capacity is known.

## Cost Guard and Fallback

1. Replace recursion with an iterative loop.
2. If callbacks or closures escape on a measured hot path, use a direct loop
   and named functions.
3. If generic containers or interface values add allocations or obscure types,
   use a concrete slice, map, or struct.
4. If mutation must occur, confine it to a new local result and return only the
   completed value or a documented partial result with its error.

## Validation Focus

Run formatting, package tests, and static analysis when configured. Use the Go
benchmark and escape-analysis tooling already available in the repository for
hot paths; otherwise report allocation risk as unmeasured.
