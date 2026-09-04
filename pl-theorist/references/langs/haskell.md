# Haskell Cost Model

## Disclosed Constraints

- Laziness supports composition and streaming but can retain input or build
  thunks, producing space leaks.
- Strictness is semantic and operational. Forcing too little harms accumulation;
  forcing too much can destroy productivity or infinite-stream behavior.
- List/stream fusion depends on exact producers, consumers, rewrite rules, and
  optimization settings; point-free syntax guarantees none of it.
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
- Use the project's existing streaming and effect abstractions over a competing
  transformer stack.

## Domain and Effect Constraints

- Use `data` for sums/products and `newtype` for zero-cost semantic distinctions.
  Hide constructors and export smart constructors when values carry invariants.
- Use `Maybe` for expected absence and `Either DomainError` for expected failure.
  Avoid `Maybe` when callers need to know why construction failed.
- Prefer applicative composition when effects are independent and monadic bind
  only when a later effect depends on an earlier value. Applicative structure
  does not itself promise parallel execution.
- Derive or define instances only when their laws hold. State `Semigroup`/`Monoid`
  identity and associativity before using `foldMap` or parallel reduction.
- Eliminate partial list functions from production paths with `NonEmpty`, total
  folds, or pattern matching at the refinement boundary.
- Use `bracket`/`finally` or the project's resource abstraction. Scope async work,
  propagate cancellation, and use bounded queues/streaming combinators.
- Keep retries and transactions in the effect interpreter; require idempotency or
  a transaction before replaying effects.

## Teaching Example

<teaching-example language="haskell">
<![CDATA[
module Port (Port, PortError(..), mkPort, configuredPort) where

newtype Port = Port Int
  deriving (Eq, Show)

data PortError = PortOutOfRange
  deriving (Eq, Show)

mkPort :: Int -> Either PortError Port
mkPort n
  | n >= 1 && n <= 65535 = Right (Port n)
  | otherwise = Left PortOutOfRange

configuredPort :: Maybe Int -> Either PortError Port
configuredPort = maybe (mkPort 8080) mkPort
]]></teaching-example>

Taste: hide `Port` outside the module, making the smart constructor the only
admission path. `Maybe` means absent configuration; `Either` preserves the reason
construction failed; `maybe` eliminates absence totally.

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
6. Preserve bracketed resources, async cancellation, boundedness, transaction
  scope, and strictness/productivity under the chosen effect interpreter.

## Validation Focus

Run the project build and focused tests. Test finite and infinite producers when
productivity is contractual. Use existing time/space profiling for strictness-
sensitive paths and inspect exception/resource behavior in `IO`.
