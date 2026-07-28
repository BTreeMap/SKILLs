# TypeScript Runtime Profile

## Disclosed Constraints

- **No portable tail-call optimization.** Avoid structural recursion for
  unbounded runtime data.
- **Erased type system.** Discriminated unions, `readonly`, and exhaustive
  checks impose no runtime representation cost, but do not validate unknown
  input at runtime.
- **Runtime abstraction cost.** Custom `Option`, `Either`, and monadic wrapper
  objects can add allocations and obscure code when a native union is enough.
- **JavaScript runtime rules remain.** Apply the JavaScript profile's runtime
  concerns only when relevant to emitted code; do not load its full procedure.

## Preferred Shapes

- Model mutually exclusive domain states with discriminated unions and
  `readonly` data when state variants are closed.
- Make a state transition or rendering function total. Use an exhaustive
  `switch` with a `never`-checked unreachable branch where project conventions
  require compile-time proof.
- Preserve runtime data validation at module boundaries; narrowing a type does
  not parse or authenticate input.
- Prefer native arrays and language constructs over heavy runtime FP libraries
  unless the repository already uses them consistently.

## Cost Guard and Fallback

1. Replace unbounded recursion with iteration, a generator, or a native
   collection operation.
2. If a runtime wrapper carries only a tag and payload, use a discriminated
   union instead.
3. If a callback chain allocates intermediates on a hot path, use a fused pass
   or direct loop while retaining pure helper functions.
4. If exhaustive matching would mask externally supplied invalid data, validate
   the input before constructing the union.

## Validation Focus

Run the project's typecheck and tests. Test every union variant, the
unreachable/exhaustive branch, and invalid external input separately.
