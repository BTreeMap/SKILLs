# Haskell Cost Model

## Disclosed Constraints

- Laziness supports composition and streaming but can retain input or build
  thunks, producing space leaks.
- Strictness is semantic and operational. Forcing too little harms accumulation;
  forcing too much can destroy productivity or infinite-stream behavior.
- List/stream fusion depends on exact producers, consumers, rewrite rules, and
  optimization settings; it is not guaranteed by point-free syntax.
- Monad transformer stacks and generalized effects can improve composition while
  worsening inference, errors, allocation, and operational visibility.

## Preferred FP Shapes

- Use algebraic data types, total pattern matching, pure functions, currying, and
  point-free composition by default.
- Use `Maybe`, `Either`, `IO`, established project effects, applicative traversal,
  and monadic bind according to dependency structure.
- Prefer `foldMap` when a monoid states the aggregation, `traverse` when effects
  preserve shape, and `foldl'` for strict left accumulation.
- Keep exported paths free of partial functions unless the type or constructor
  proves their preconditions.
- Use the project's existing streaming and effect abstractions rather than adding
  a competing transformer stack.

## Cost Guard

1. Check whether consumers stream, retain the input spine, or build accumulator
   thunks.
2. Introduce only the narrowest strictness annotation, strict field, `foldl'`, or
   streaming fold needed.
3. If point-free composition hides sharing, strictness, or resource lifetime,
   restore named arguments and bindings.
4. If an effect stack obscures types or profiling, simplify to the established
   base effect or an explicit interpreter.
5. Require profiling evidence before asserting fusion or allocation behavior.

## Validation Focus

Run the project build and focused tests. Test finite and infinite producers when
productivity is contractual. Use existing time/space profiling for strictness-
sensitive paths and inspect exception/resource behavior in `IO`.